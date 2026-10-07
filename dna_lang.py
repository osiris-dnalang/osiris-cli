#!/usr/bin/env python3
"""
dna_lang.py -- DNA::}AI{::Lang v0.1: a declarative language for OSIRIS
organism definitions and metamorphosis (change) proposals, compiled to
canonical DNA-IR with a SHA-256 content ID.

    python3 bin/dna_lang.py validate FILE [--json]
    python3 bin/dna_lang.py compile  FILE [-o OUT] [--json]
    python3 bin/dna_lang.py hash     FILE [--json]
    python3 bin/dna_lang.py inspect  FILE [--json]

FILE is .dna source, or compiled DNA-IR if it ends in .json. Exit codes:
0 valid, 1 invalid (diagnostics printed), 2 usage or I/O error.

What 0.1 does: parse, check structure and semantics against a pinned spec,
canonicalize (RFC 8785 JCS over a JSON subset: objects, arrays, strings,
integers, booleans), and hash. The compiled file's bytes ARE the canonical
bytes, so `sha256sum organism.dna.json` equals the content ID.

What 0.1 deliberately does not do: execute anything, sign anything, touch
the network, resolve dna:sha256 references against an artifact store (they
are format-checked only), support imports, or grant authority. A document
only declares requests and requirements. Trusted OSIRIS code decides what
happens to it. The language reference is bin/DNA_LANG_SPEC.md.

Stdlib only, so it runs on bare Termux.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import textwrap
import unicodedata

LANG_VERSION = "dna-lang/0.1"
IR_VERSION = "dna-ir/0.1"

MAX_SOURCE_BYTES = 256 * 1024
MAX_IR_BYTES = 1024 * 1024
MAX_DEPTH = 6
MAX_LIST = 256
MAX_STRING = 8192
MAX_NAME = 128
MAX_COLLECTION = 64
MAX_INT = 2 ** 53 - 1  # largest integer every JCS/IEEE-754 consumer agrees on

NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*\Z")
REF_RE = re.compile(r"dna:sha256:[0-9a-f]{64}\Z")
URN_RE = re.compile(r"urn:[a-z0-9][a-z0-9-]{0,31}:[A-Za-z0-9()+,\-.:=@;$_!*'%/?#]+\Z")
# Trojan Source (CVE-2021-42574): bidi controls make text render differently
# from its bytes, so a reviewer could approve something other than what is hashed.
BIDI = set("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200e\u200f")

# Keys that are never part of the language, rejected with a specific rule so
# the author learns why, not just "unknown field".
AUTHORITY_WORDS = {"grant", "grants", "trust", "trusted", "approve", "approved",
                   "approval", "signature", "signed", "sign", "authorize",
                   "authorized", "self_grant", "apply_now",
                   "apply_without_confirmation", "sudo", "root", "privileged"}
EXEC_WORDS = {"shell", "exec", "execute", "run", "command", "cmd", "script",
              "python", "eval", "native", "binary", "code", "payload", "http",
              "url", "fetch", "download", "upload", "socket", "network_allow"}
IMPORT_WORDS = {"import", "include", "use", "require_file", "extends"}


class Diag:
    """One diagnostic. rule is a stable ID documented in DNA_LANG_SPEC.md."""

    def __init__(self, rule, msg, path=(), pos=None, hint=None):
        self.rule, self.msg, self.path, self.pos, self.hint = rule, msg, tuple(path), pos, hint

    def as_dict(self):
        d = {"rule": self.rule, "message": self.msg, "path": "/" + "/".join(map(str, self.path))}
        if self.pos:
            d["line"], d["col"] = self.pos
        if self.hint:
            d["hint"] = self.hint
        return d

    def __str__(self):
        where = f"{self.pos[0]}:{self.pos[1]}: " if self.pos else ""
        s = f"{where}{self.rule}: {self.msg} (at {self.as_dict()['path']})"
        return s + (f"\n    hint: {self.hint}" if self.hint else "")


class Invalid(Exception):
    def __init__(self, diags):
        super().__init__("; ".join(str(d) for d in diags))
        self.diags = diags


# ---------------------------------------------------------------- the spec
# Field types: (kind, options). Every field is required unless opt=True.

def F(kind, opt=False, **kw):
    return dict(kind=kind, opt=opt, **kw)


STR = F("str")
OPT_STR = F("str", opt=True)
REF = F("ref")
OPT_REF = F("ref", opt=True)


def SET(item, opt=False, min_items=0):
    """Unordered, duplicate-free list; canonical form is sorted."""
    return F("list", opt=opt, item=item, set=True, min=min_items)


def SEQ(item, opt=False, min_items=0):
    """Ordered list; source order is kept and is part of the content ID."""
    return F("list", opt=opt, item=item, set=False, min=min_items)


def ENUM(*values, opt=False):
    return F("enum", opt=opt, values=list(values))


TRUE = F("true")  # a requirement that exists only as `true`; it cannot be weakened

SPEC = {
    "meta": dict(named=False, fields={
        "schema": F("const", value=LANG_VERSION),
        "title": STR,
        "description": OPT_STR,
    }),
    "identity": dict(named=False, fields={
        "organism_id": F("urn"),
        "species": F("name"),
        "generation": F("int", min=0, max=MAX_INT),
        "genome_ref": OPT_REF,
        "parent_genome_ref": OPT_REF,
    }),
    "intent": dict(named=False, fields={
        "objective": STR,
        "success": SEQ(STR, opt=True),
    }),
    "constraints": dict(named=False, fields={
        "require": SET(F("name")),
        "prohibit": SET(F("name")),
        "allowed_roots": SET(F("path"), min_items=1),
        "protected_paths": SET(F("path"), opt=True),
    }),
    "capability": dict(named=True, ir_key="capabilities", fields={
        "class": ENUM("read_only", "proposal", "execution", "append_only", "controlled_write"),
        "authority": ENUM("model_adapter", "trusted_runtime", "sandbox_only", "operator_plus_runtime"),
        "description": OPT_STR,
        "profile": F("name", opt=True),
    }, blocks={
        "limits": dict(named=False, opt=True, fields={
            "wall_seconds": F("int", min=1, max=86400),
            "memory_mb": F("int", min=1, max=65536),
            "network": ENUM("deny"),
            "native_execution": ENUM("deny"),
        }),
    }),
    "evidence": dict(named=True, ir_key="evidence", fields={
        "kind": ENUM("verified_observation", "hypothesis", "failure_pattern",
                     "operator_preference", "untrusted_reference"),
        "statement": STR,
        "refs": SET(REF),
    }),
    "metamorphosis": dict(named=True, ir_key="metamorphoses", fields={
        "parent": REF,
        "target_generation": F("int", min=1, max=MAX_INT),
        "objective": STR,
        "rationale": OPT_STR,
    }, blocks={
        "mutation": dict(named=False, fields={
            "kind": ENUM("source_patch", "prompt_strategy", "config"),
            "patch_ref": REF,
            "allowed_paths": SET(F("path"), min_items=1),
        }),
        "verification": dict(named=False, fields={
            "required_profiles": SET(F("name"), min_items=1),
            "reject_on": SET(F("name"), opt=True),
        }),
        "promotion": dict(named=False, fields={
            "require_operator_approval": TRUE,
            "require_sandbox_pass": TRUE,
            "require_base_hash_match": TRUE,
            "require_ledger_attestation": TRUE,
        }),
    }),
}
TOP_UNNAMED = [k for k, v in SPEC.items() if not v["named"]]
TOP_NAMED = {k: v["ir_key"] for k, v in SPEC.items() if v["named"]}


# ------------------------------------------------------ canonical JSON (JCS)

def _jcs_str(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20:
            out.append({8: "\\b", 9: "\\t", 10: "\\n", 12: "\\f", 13: "\\r"}.get(o, "\\u%04x" % o))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def canonicalize(v):
    """RFC 8785 serialization for the DNA-IR value domain. Floats are not in
    the domain (JCS number formatting is the error-prone part and DNA-IR has
    no need for it), so they are refused rather than approximated."""
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, int):
        if abs(v) > MAX_INT:
            raise ValueError("integer outside the IEEE-754 exact range")
        return str(v)
    if isinstance(v, str):
        return _jcs_str(v)
    if isinstance(v, list):
        return "[" + ",".join(canonicalize(x) for x in v) + "]"
    if isinstance(v, dict):
        if not all(isinstance(k, str) for k in v):
            raise ValueError("object keys must be strings")
        # JCS orders keys by UTF-16 code units, not code points.
        keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(_jcs_str(k) + ":" + canonicalize(v[k]) for k in keys) + "}"
    raise ValueError(f"{type(v).__name__} is not in the DNA-IR value domain")


def canonical_bytes(v):
    return canonicalize(v).encode("utf-8")


def content_id(v):
    return "dna:sha256:" + hashlib.sha256(canonical_bytes(v)).hexdigest()


SPEC_HASH = "sha256:" + hashlib.sha256(canonical_bytes(
    {"lang": LANG_VERSION, "ir": IR_VERSION, "spec": SPEC})).hexdigest()


# ------------------------------------------------------------------- lexer

class Tok:
    __slots__ = ("kind", "val", "pos")

    def __init__(self, kind, val, pos):
        self.kind, self.val, self.pos = kind, val, pos


def _check_text(s, pos, path, multiline=False):
    if len(s) > MAX_STRING:
        raise Invalid([Diag("DNA-E-LIMIT", f"string longer than {MAX_STRING} characters", path, pos)])
    for ch in s:
        if ch in BIDI:
            raise Invalid([Diag("DNA-E-TEXT", f"bidirectional control U+{ord(ch):04X} in text", path, pos,
                                "these make text display differently from what is hashed")])
        if (ord(ch) < 0x20 and not (multiline and ch == "\n")) or ord(ch) == 0x7f:
            raise Invalid([Diag("DNA-E-TEXT", f"control character U+{ord(ch):04X} in text", path, pos)])
        if 0xD800 <= ord(ch) <= 0xDFFF:
            raise Invalid([Diag("DNA-E-TEXT", "unpaired surrogate in text", path, pos)])
    if not unicodedata.is_normalized("NFC", s):
        raise Invalid([Diag("DNA-E-TEXT", "text is not Unicode NFC-normalized", path, pos,
                            "visually identical text must hash identically; normalize to NFC")])


def lex(src):
    toks, i, line, col, n = [], 0, 1, 1, len(src)

    def adv(k):
        nonlocal i, line, col
        for ch in src[i:i + k]:
            if ch == "\n":
                line, col = line + 1, 1
            else:
                col += 1
        i += k

    while i < n:
        c, pos = src[i], (line, col)
        if c in " \t\n":
            adv(1)
        elif src.startswith("//", i):
            j = src.find("\n", i)
            adv((n if j < 0 else j) - i)
        elif c in "{}[],":
            toks.append(Tok(c, c, pos))
            adv(1)
        elif src.startswith('"""', i):
            j = src.find('"""', i + 3)
            if j < 0:
                raise Invalid([Diag("DNA-E-SYNTAX", "unterminated \"\"\" string", pos=pos)])
            raw = src[i + 3:j]
            text = textwrap.dedent(raw.lstrip("\n").rstrip())
            text = "\n".join(ln.rstrip() for ln in text.split("\n"))
            _check_text(text, pos, (), multiline=True)
            toks.append(Tok("str", text, pos))
            adv(j + 3 - i)
        elif c == '"':
            j, buf = i + 1, []
            while True:
                if j >= n or src[j] == "\n":
                    raise Invalid([Diag("DNA-E-SYNTAX", "unterminated string", pos=pos,
                                        hint='use """...""" for multi-line text')])
                ch = src[j]
                if ch == '"':
                    break
                if ch == "\\":
                    e = src[j + 1:j + 2]
                    simple = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "/": "/"}
                    if e in simple:
                        buf.append(simple[e])
                        j += 2
                        continue
                    if e == "u" and re.fullmatch(r"[0-9A-Fa-f]{4}", src[j + 2:j + 6]):
                        buf.append(chr(int(src[j + 2:j + 6], 16)))
                        j += 6
                        continue
                    raise Invalid([Diag("DNA-E-SYNTAX", f"invalid escape \\{e}", pos=pos)])
                buf.append(ch)
                j += 1
            text = "".join(buf)
            _check_text(text, pos, ())
            toks.append(Tok("str", text, pos))
            adv(j + 1 - i)
        elif c == "-" or c.isdigit():
            m = re.compile(r"-?(0|[1-9][0-9]*)").match(src, i)
            if not m:
                raise Invalid([Diag("DNA-E-SYNTAX", "malformed integer", pos=pos)])
            end = m.end()
            if end < n and (src[end] in ".eE" or src[end].isdigit()):
                raise Invalid([Diag("DNA-E-TYPE", "only integers are allowed (no fractions, exponents "
                                    "or leading zeros)", pos=pos)])
            val = int(m.group())
            if abs(val) > MAX_INT:
                raise Invalid([Diag("DNA-E-LIMIT", "integer outside the IEEE-754 exact range", pos=pos)])
            toks.append(Tok("int", val, pos))
            adv(end - i)
        elif c.isalpha() or c == "_":
            m = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*").match(src, i)
            word = m.group()
            if len(word) > MAX_NAME:
                raise Invalid([Diag("DNA-E-LIMIT", f"identifier longer than {MAX_NAME}", pos=pos)])
            toks.append(Tok("ident", word, pos))
            adv(len(word))
        else:
            raise Invalid([Diag("DNA-E-SYNTAX", f"unexpected character {c!r}", pos=pos)])
    toks.append(Tok("eof", None, (line, col)))
    return toks


# ------------------------------------------------------------------ parser
# document := "organism" NAME "{" entry* "}"
# entry    := IDENT [NAME] "{" entry* "}"  |  IDENT value
# value    := STRING | INT | true | false | "[" [scalar ("," scalar)* [","]] "]"

class Block:
    def __init__(self, kind, name, entries, pos):
        self.kind, self.name, self.entries, self.pos = kind, name, entries, pos


class Field:
    def __init__(self, key, value, pos):
        self.key, self.value, self.pos = key, value, pos


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def take(self, kind, what):
        tok = self.peek()
        if tok.kind != kind:
            got = "end of file" if tok.kind == "eof" else repr(tok.val)
            raise Invalid([Diag("DNA-E-SYNTAX", f"expected {what}, got {got}", pos=tok.pos)])
        self.i += 1
        return tok

    def document(self):
        head = self.take("ident", "'organism'")
        if head.val != "organism":
            raise Invalid([Diag("DNA-E-SYNTAX", "a document must start with 'organism NAME {'", pos=head.pos)])
        name = self.take("ident", "organism name")
        self.take("{", "'{'")
        entries = self.entries(1)
        self.take("}", "'}'")
        self.take("eof", "end of file")
        return Block("organism", name.val, entries, head.pos)

    def entries(self, depth):
        if depth > MAX_DEPTH:
            raise Invalid([Diag("DNA-E-LIMIT", f"nesting deeper than {MAX_DEPTH}", pos=self.peek().pos)])
        out = []
        while self.peek().kind == "ident":
            key = self.take("ident", "field or block name")
            nxt, nxt2 = self.peek(), self.peek(1)
            if nxt.kind == "{" or (nxt.kind == "ident" and nxt2.kind == "{"
                                   and nxt.val not in ("true", "false", "null")):
                name = self.take("ident", "block name").val if nxt.kind == "ident" else None
                self.take("{", "'{'")
                body = self.entries(depth + 1)
                self.take("}", "'}'")
                out.append(Block(key.val, name, body, key.pos))
            else:
                out.append(Field(key.val, self.value(), key.pos))
        return out

    def scalar(self):
        tok = self.peek()
        if tok.kind in ("str", "int"):
            self.i += 1
            return tok.val
        if tok.kind == "ident" and tok.val in ("true", "false"):
            self.i += 1
            return tok.val == "true"
        if tok.kind == "ident" and tok.val == "null":
            raise Invalid([Diag("DNA-E-TYPE", "null is not a DNA-Lang value; omit optional fields instead",
                                pos=tok.pos)])
        if tok.kind == "ident":
            raise Invalid([Diag("DNA-E-SYNTAX", f"bare word {tok.val!r} where a value was expected",
                                pos=tok.pos, hint=f'quote it: "{tok.val}"')])
        if tok.kind == "[":
            raise Invalid([Diag("DNA-E-TYPE", "nested lists are not allowed", pos=tok.pos)])
        got = "end of file" if tok.kind == "eof" else repr(tok.val)
        raise Invalid([Diag("DNA-E-SYNTAX", f"expected a value, got {got}", pos=tok.pos)])

    def value(self):
        if self.peek().kind != "[":
            return self.scalar()
        start = self.take("[", "'['")
        items = []
        while self.peek().kind != "]":
            items.append(self.scalar())
            if len(items) > MAX_LIST:
                raise Invalid([Diag("DNA-E-LIMIT", f"list longer than {MAX_LIST}", pos=start.pos)])
            if self.peek().kind == ",":
                self.i += 1
            elif self.peek().kind != "]":
                self.take(",", "',' or ']'")
        self.take("]", "']'")
        return items


# ---------------------------------------------------------------- lowering
# AST -> IR-shaped dict, plus a path -> (line, col) map for diagnostics.
# Structural and semantic checking happens once, in validate_ir(), which is
# also what compiled .json input goes through.

def _refuse_word(key, path, pos):
    low = key.lower()
    if low in AUTHORITY_WORDS:
        return Diag("DNA-E-AUTHORITY", f"'{key}' would let the document claim authority",
                    path, pos, "a document can only request; policy outside the document grants")
    if low in EXEC_WORDS:
        return Diag("DNA-E-EXEC", f"'{key}' would embed execution or network access",
                    path, pos, "DNA-Lang is declarative; reference fixed verification profiles instead")
    if low in IMPORT_WORDS:
        return Diag("DNA-E-IMPORT", f"'{key}': imports are not supported in {LANG_VERSION}", path, pos)
    return None


def _lower(entries, spec, path, posmap, diags):
    out = {}
    fields, blocks = spec.get("fields", {}), spec.get("blocks", {})
    for e in entries:
        is_block = isinstance(e, Block)
        key = e.kind if is_block else e.key
        target = TOP_NAMED.get(key) if spec is ROOT_SPEC else None
        p = path + ((target, e.name) if target and is_block and e.name else (key,))
        posmap.setdefault(p, e.pos)
        bad = _refuse_word(key, p, e.pos)
        if bad:
            diags.append(bad)
            continue
        if is_block:
            sub = SPEC.get(key) if spec is ROOT_SPEC else blocks.get(key)
            if sub is None:
                if key in fields:
                    diags.append(Diag("DNA-E-SYNTAX", f"'{key}' is a field, not a block", p, e.pos))
                else:
                    diags.append(_unknown(key, fields, blocks, spec, p, e.pos))
                continue
            if sub["named"] and not e.name:
                diags.append(Diag("DNA-E-NAME", f"'{key}' blocks need a name: {key} NAME {{ ... }}", p, e.pos))
                continue
            if not sub["named"] and e.name:
                diags.append(Diag("DNA-E-NAME", f"'{key}' blocks take no name", p, e.pos))
                continue
            body = _lower(e.entries, sub, p, posmap, diags)
            if sub["named"]:
                coll = out.setdefault(sub["ir_key"], {})
                if e.name in coll:
                    diags.append(Diag("DNA-E-DUP", f"duplicate {key} '{e.name}'", p, e.pos))
                coll[e.name] = body
            elif key in out:
                diags.append(Diag("DNA-E-DUP", f"duplicate '{key}' block", p, e.pos))
            else:
                out[key] = body
        else:
            if key not in fields:
                if key in blocks or (spec is ROOT_SPEC and key in SPEC):
                    diags.append(Diag("DNA-E-SYNTAX", f"'{key}' is a block: {key} {{ ... }}", p, e.pos))
                else:
                    diags.append(_unknown(key, fields, blocks, spec, p, e.pos))
                continue
            if key in out:
                diags.append(Diag("DNA-E-DUP", f"duplicate field '{key}'", p, e.pos))
                continue
            v = e.value
            if isinstance(v, list) and fields[key].get("set") and \
                    all(isinstance(x, str) for x in v):
                v = sorted(v, key=lambda s: s.encode("utf-16-be"))
            out[key] = v
    return out


ROOT_SPEC = {"fields": {}, "blocks": {}}


def _unknown(key, fields, blocks, spec, path, pos):
    known = list(fields) + list(blocks) + (list(SPEC) if spec is ROOT_SPEC else [])
    close = difflib.get_close_matches(key, known, n=1)
    return Diag("DNA-E-UNKNOWN", f"unknown field or block '{key}'", path, pos,
                f"did you mean '{close[0]}'?" if close else f"allowed here: {', '.join(sorted(known))}")


def lower(doc):
    posmap, diags = {(): doc.pos}, []
    body = _lower(doc.entries, ROOT_SPEC, (), posmap, diags)
    if diags:
        raise Invalid(diags)
    ir = {"schema_version": IR_VERSION, "kind": "organism_definition",
          "name": doc.name, "spec_hash": SPEC_HASH}
    for k in TOP_UNNAMED:
        if k in body:
            ir[k] = body[k]
    for ir_key in TOP_NAMED.values():
        ir[ir_key] = body.get(ir_key, {})
    return ir, posmap


# -------------------------------------------------------------- validation

def _check_path(s):
    if not s or len(s) > 256:
        return "path must be 1-256 characters"
    if s.startswith(("/", "~")) or "\\" in s or ":" in s:
        return "paths are workspace-relative POSIX paths (no leading / or ~, no \\ or :)"
    for seg in s.split("/"):
        if seg in ("", ".", ".."):
            return "path segments may not be empty, '.' or '..'"
    return None


def _check_value(v, t, path, pos, diags):
    k = t["kind"]

    def bad(msg, rule="DNA-E-TYPE", hint=None):
        diags.append(Diag(rule, msg, path, pos(path), hint))

    if k == "list":
        if not isinstance(v, list):
            return bad("expected a list [ ... ]")
        if len(v) > MAX_LIST:
            return bad(f"list longer than {MAX_LIST}", "DNA-E-LIMIT")
        if len(v) < t["min"]:
            return bad(f"needs at least {t['min']} item(s)", "DNA-E-MISSING")
        for idx, x in enumerate(v):
            _check_value(x, t["item"], path + (idx,), lambda _p: pos(path), diags)
        if t["set"] and all(isinstance(x, str) for x in v):
            if len(set(v)) != len(v):
                dup = sorted({x for x in v if v.count(x) > 1})
                bad(f"duplicate entries {dup}", "DNA-E-DUP")
            elif v != sorted(v, key=lambda s: s.encode("utf-16-be")):
                bad("set-valued list is not in canonical (sorted) order", "DNA-E-CANONICAL",
                    "compiled DNA-IR must be emitted by the compiler, not hand-edited")
        return
    if k == "true":
        if v is not True:
            return bad("this requirement can only be `true`", "DNA-E-WEAKEN",
                       "promotion gates cannot be switched off from a document")
        return
    if k == "int":
        if not isinstance(v, int) or isinstance(v, bool):
            return bad("expected an integer")
        if not t["min"] <= v <= t["max"]:
            return bad(f"must be between {t['min']} and {t['max']}", "DNA-E-RANGE")
        return
    if not isinstance(v, str):
        return bad("expected a string" if k in ("str", "path") else f"expected a quoted {k}")
    try:
        _check_text(v, pos(path), path, multiline=(k == "str"))
    except Invalid as e:
        diags.extend(e.diags)
        return
    if k == "const" and v != t["value"]:
        bad(f"must be \"{t['value']}\"", "DNA-E-VERSION",
            f"this compiler implements {LANG_VERSION} only")
    elif k == "enum" and v not in t["values"]:
        close = difflib.get_close_matches(v, t["values"], n=1)
        bad(f"\"{v}\" is not one of {t['values']}", "DNA-E-ENUM",
            f"did you mean \"{close[0]}\"?" if close else None)
    elif k == "ref" and not REF_RE.match(v):
        bad("expected dna:sha256:<64 lowercase hex>", "DNA-E-REF")
    elif k == "urn" and not URN_RE.match(v):
        bad("expected a URN, e.g. urn:osiris:organism:<uuid>", "DNA-E-TYPE")
    elif k == "name" and not (NAME_RE.match(v) and len(v) <= MAX_NAME):
        bad("expected a name: letters, digits, _ . - (starting with a letter or _)", "DNA-E-TYPE")
    elif k == "path":
        err = _check_path(v)
        if err:
            bad(err, "DNA-E-PATH")


def _check_obj(obj, spec, path, pos, diags):
    if not isinstance(obj, dict):
        diags.append(Diag("DNA-E-TYPE", "expected a block/object", path, pos(path)))
        return
    fields, blocks = spec.get("fields", {}), spec.get("blocks", {})
    for key in obj:
        if key not in fields and key not in blocks:
            diags.append(_refuse_word(key, path + (key,), pos(path))
                         or _unknown(key, fields, blocks, spec, path + (key,), pos(path)))
    for key, t in fields.items():
        if key in obj:
            _check_value(obj[key], t, path + (key,), pos, diags)
        elif not t["opt"]:
            diags.append(Diag("DNA-E-MISSING", f"missing required field '{key}'", path, pos(path)))
    for key, sub in blocks.items():
        if key in obj:
            _check_obj(obj[key], sub, path + (key,), pos, diags)
        elif not sub.get("opt"):
            diags.append(Diag("DNA-E-MISSING", f"missing required block '{key}'", path, pos(path)))


def _under(p, root):
    return p == root or p.startswith(root + "/")


def _semantics(ir, pos, diags):
    def d(rule, msg, path, hint=None):
        diags.append(Diag(rule, msg, path, pos(path), hint))

    ident, cons = ir["identity"], ir["constraints"]
    genome, parent = ident.get("genome_ref"), ident.get("parent_genome_ref")
    if genome and genome == parent:
        d("DNA-E-CYCLE", "genome_ref equals parent_genome_ref (a genome cannot be its own parent)",
          ("identity", "parent_genome_ref"))
    if parent and not genome:
        d("DNA-E-LINEAGE", "parent_genome_ref given without genome_ref", ("identity",))

    both = sorted(set(cons["require"]) & set(cons["prohibit"]))
    if both:
        d("DNA-E-CONFLICT", f"both required and prohibited: {both}", ("constraints",))
    protected = cons.get("protected_paths", [])
    for root in cons["allowed_roots"]:
        for pp in protected:
            if _under(root, pp):
                d("DNA-E-SCOPE", f"allowed root '{root}' is inside protected path '{pp}'",
                  ("constraints", "allowed_roots"))

    for name, cap in ir["capabilities"].items():
        p = ("capabilities", name)
        if cap["class"] == "execution" and "limits" not in cap:
            d("DNA-E-UNBOUNDED", "execution capability without a limits block", p,
              "declare wall_seconds, memory_mb, network \"deny\", native_execution \"deny\"")
        if cap["class"] == "execution" and cap["authority"] == "model_adapter":
            d("DNA-E-AUTHORITY", "a model adapter cannot hold execution authority", p + ("authority",))
        if cap["class"] == "controlled_write" and cap["authority"] != "operator_plus_runtime":
            d("DNA-E-AUTHORITY", "controlled_write requires authority \"operator_plus_runtime\"",
              p + ("authority",))

    for name, ev in ir["evidence"].items():
        if ev["kind"] == "verified_observation" and not ev["refs"]:
            d("DNA-E-EVIDENCE", "verified_observation with no evidence refs", ("evidence", name, "refs"),
              "link at least one artifact hash, or declare it as a hypothesis")

    for name, mm in ir["metamorphoses"].items():
        p = ("metamorphoses", name)
        if not genome:
            d("DNA-E-LINEAGE", "a metamorphosis needs identity.genome_ref to derive from", p)
        elif mm["parent"] != genome:
            d("DNA-E-LINEAGE", "parent does not match identity.genome_ref", p + ("parent",),
              "a proposal must derive from the organism's current genome")
        if mm["target_generation"] != ident["generation"] + 1:
            d("DNA-E-LINEAGE", f"target_generation must be {ident['generation'] + 1} "
              f"(current generation + 1)", p + ("target_generation",))
        for path_ in mm["mutation"]["allowed_paths"]:
            where = p + ("mutation", "allowed_paths")
            if not any(_under(path_, r) for r in cons["allowed_roots"]):
                d("DNA-E-SCOPE", f"'{path_}' is outside every allowed root {cons['allowed_roots']}", where)
            hit = [pp for pp in protected if _under(path_, pp) or _under(pp, path_)]
            if hit:
                d("DNA-E-SCOPE", f"'{path_}' overlaps protected path {hit}", where)


def validate_ir(ir, posmap=None):
    """Raises Invalid with every diagnostic found, or returns ir unchanged."""
    posmap = posmap or {}

    def pos(path):
        while path not in posmap and path:
            path = path[:-1]
        return posmap.get(path)

    diags = []
    if not isinstance(ir, dict):
        raise Invalid([Diag("DNA-E-TYPE", "DNA-IR must be a JSON object")])
    top = {"schema_version", "kind", "name", "spec_hash", *TOP_UNNAMED, *TOP_NAMED.values()}
    for key in ir:
        if key not in top:
            diags.append(_refuse_word(key, (key,), None) or Diag("DNA-E-UNKNOWN", f"unknown top-level key '{key}'", (key,)))
    if ir.get("schema_version") != IR_VERSION:
        diags.append(Diag("DNA-E-VERSION", f"schema_version must be \"{IR_VERSION}\"", ("schema_version",)))
    if ir.get("kind") != "organism_definition":
        diags.append(Diag("DNA-E-VERSION", "kind must be \"organism_definition\"", ("kind",)))
    if ir.get("spec_hash") != SPEC_HASH:
        diags.append(Diag("DNA-E-VERSION", "spec_hash does not match this compiler's pinned spec",
                          ("spec_hash",), hint="recompile the source with this compiler"))
    name = ir.get("name")
    if not (isinstance(name, str) and NAME_RE.match(name) and len(name) <= MAX_NAME):
        diags.append(Diag("DNA-E-TYPE", "organism name must be a name", ("name",), pos(())))
    for k in TOP_UNNAMED:
        if k not in ir:
            diags.append(Diag("DNA-E-MISSING", f"missing required block '{k}'", (), pos(())))
        else:
            _check_obj(ir[k], SPEC[k], (k,), pos, diags)
    for kind, ir_key in TOP_NAMED.items():
        coll = ir.get(ir_key)
        if not isinstance(coll, dict):
            diags.append(Diag("DNA-E-TYPE", f"'{ir_key}' must be an object", (ir_key,)))
            continue
        if len(coll) > MAX_COLLECTION:
            diags.append(Diag("DNA-E-LIMIT", f"more than {MAX_COLLECTION} {kind} blocks", (ir_key,)))
        for nm, obj in coll.items():
            if not (NAME_RE.match(nm) and len(nm) <= MAX_NAME):
                diags.append(Diag("DNA-E-TYPE", f"bad {kind} name {nm!r}", (ir_key, nm), pos((ir_key, nm))))
            _check_obj(obj, SPEC[kind], (ir_key, nm), pos, diags)
    if not diags:
        _semantics(ir, pos, diags)
    if diags:
        raise Invalid(diags)
    return ir


# ------------------------------------------------------------ entry points

def compile_source(src):
    """.dna text -> validated DNA-IR dict. Raises Invalid."""
    if len(src.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise Invalid([Diag("DNA-E-LIMIT", f"source larger than {MAX_SOURCE_BYTES} bytes")])
    if src.startswith("\ufeff"):
        src = src[1:]
    src = src.replace("\r\n", "\n")
    if "\r" in src:
        raise Invalid([Diag("DNA-E-TEXT", "bare carriage return in source")])
    ir, posmap = lower(Parser(lex(src)).document())
    return validate_ir(ir, posmap)


def _no_dup_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Invalid([Diag("DNA-E-DUP", f"duplicate JSON key '{k}'")])
        out[k] = v
    return out


def _no_float(s):
    raise Invalid([Diag("DNA-E-TYPE", f"non-integer number {s} in DNA-IR")])


def load_ir(data):
    """Compiled DNA-IR bytes -> validated dict. Raises Invalid."""
    if len(data) > MAX_IR_BYTES:
        raise Invalid([Diag("DNA-E-LIMIT", f"DNA-IR larger than {MAX_IR_BYTES} bytes")])
    try:
        ir = json.loads(data.decode("utf-8"), object_pairs_hook=_no_dup_keys,
                        parse_float=_no_float, parse_constant=_no_float)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as e:
        raise Invalid([Diag("DNA-E-SYNTAX", f"not valid JSON: {e}")])
    return validate_ir(ir)


def load_any(path):
    """Returns (ir, is_canonical_bytes). Raises Invalid or OSError."""
    with open(path, "rb") as f:
        data = f.read(max(MAX_IR_BYTES, MAX_SOURCE_BYTES) + 1)
    if path.endswith(".json"):
        ir = load_ir(data)
        return ir, data == canonical_bytes(ir)
    try:
        src = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Invalid([Diag("DNA-E-TEXT", "source is not valid UTF-8")])
    return compile_source(src), None


def summarize(ir):
    ident = ir["identity"]
    return {
        "content_id": content_id(ir),
        "name": ir["name"],
        "title": ir["meta"]["title"],
        "organism_id": ident["organism_id"],
        "generation": ident["generation"],
        "genome_ref": ident.get("genome_ref"),
        "objective": ir["intent"]["objective"],
        "requires": ir["constraints"]["require"],
        "prohibits": ir["constraints"]["prohibit"],
        "capabilities": {n: {"class": c["class"], "authority": c["authority"]}
                         for n, c in ir["capabilities"].items()},
        "evidence": {n: {"kind": e["kind"], "refs": len(e["refs"])} for n, e in ir["evidence"].items()},
        "metamorphoses": {n: {"target_generation": m["target_generation"],
                              "kind": m["mutation"]["kind"],
                              "allowed_paths": m["mutation"]["allowed_paths"],
                              "required_profiles": m["verification"]["required_profiles"]}
                          for n, m in ir["metamorphoses"].items()},
    }


def _print_inspect(s):
    print(f"{s['name']}  --  {s['title']}")
    print(f"  content id   {s['content_id']}")
    print(f"  organism     {s['organism_id']}  (generation {s['generation']})")
    print(f"  genome       {s['genome_ref'] or '(none declared)'}")
    print(f"  objective    {s['objective']}")
    print(f"  requires     {', '.join(s['requires']) or '-'}")
    print(f"  prohibits    {', '.join(s['prohibits']) or '-'}")
    print(f"  capabilities ({len(s['capabilities'])}) -- requested, not granted")
    for n, c in s["capabilities"].items():
        print(f"    {n:<28} {c['class']:<16} {c['authority']}")
    print(f"  evidence ({len(s['evidence'])})")
    for n, e in s["evidence"].items():
        print(f"    {n:<28} {e['kind']:<22} {e['refs']} ref(s)")
    print(f"  metamorphoses ({len(s['metamorphoses'])}) -- proposals, not changes")
    for n, m in s["metamorphoses"].items():
        print(f"    {n} -> generation {m['target_generation']} ({m['kind']})")
        print(f"      paths    {', '.join(m['allowed_paths'])}")
        print(f"      verify   {', '.join(m['required_profiles'])}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dna", description=f"DNA::}}AI{{::Lang {LANG_VERSION} compiler")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c, h in (("validate", "check a .dna or DNA-IR .json file"),
                 ("compile", "compile .dna to canonical DNA-IR"),
                 ("hash", "print the content ID"),
                 ("inspect", "summarize an organism")):
        p = sub.add_parser(c, help=h)
        p.add_argument("file")
        p.add_argument("--json", action="store_true", help="machine-readable output")
        if c == "compile":
            p.add_argument("-o", "--out", help="write canonical DNA-IR here (default: stdout)")
    a = ap.parse_args(argv)

    try:
        ir, canonical = load_any(a.file)
    except OSError as e:
        print(f"dna: {e}", file=sys.stderr)
        return 2
    except Invalid as e:
        if a.json:
            print(json.dumps({"ok": False, "file": a.file,
                              "diagnostics": [d.as_dict() for d in e.diags]}, indent=2))
        else:
            for d in e.diags:
                print(f"{a.file}:{d}", file=sys.stderr)
            print(f"{a.file}: invalid ({len(e.diags)} problem(s))", file=sys.stderr)
        return 1

    cid = content_id(ir)
    result = {"ok": True, "file": a.file, "content_id": cid}
    if canonical is not None:
        result["canonical_bytes"] = canonical
    if a.cmd == "compile":
        data = canonical_bytes(ir)
        if a.out:
            tmp = a.out + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, a.out)
            result["out"] = a.out
        elif not a.json:
            sys.stdout.buffer.write(data + b"\n")
            print(cid, file=sys.stderr)
            return 0
        else:
            result["ir"] = ir
    if a.cmd == "inspect":
        result["summary"] = summarize(ir)
    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif a.cmd == "hash":
        print(cid)
    elif a.cmd == "inspect":
        _print_inspect(result["summary"])
        if canonical is False:
            print("  note: file is valid but not byte-canonical; its sha256 differs from the content id")
    else:
        extra = ""
        if canonical is False:
            extra = " (valid, but bytes are not canonical: sha256 of the file differs from the id)"
        print(f"{a.file}: ok {cid}{extra}" + (f" -> {a.out}" if a.cmd == "compile" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
