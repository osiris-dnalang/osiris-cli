#!/usr/bin/env python3
"""
research.py -- the Research Lab: sources, a cross-field concept map,
hypotheses, and outcomes proven only by verified evidence.

The operator pastes papers, notes, chat logs and sessions, or gives a URL,
and wants OSIRIS to connect research across fields, ground it, generate
hypotheses, prove or disprove them, and grow OSIRIS from what is proven.
Every step here is code, with no model:

  source      pasted or fetched text, stored with its SHA-256 and a trust
              label -- external_reference (paper, URL), operator_note, or
              untrusted_reference (chat log, terminal session). Data only:
              nothing in a source runs, and no source changes anything.
  concepts    fixed vocabularies per field (DOMAINS). A concept found in a
              source keeps the line it came from, so every link on the map
              cites where it is grounded.
  map         concepts shared between sources, and cross-field links:
              concepts of two different fields in the same source.
  hypothesis  question, prediction, what is varied, metric, controls, what
              would refute it, and the sources it rests on. A draft until an
              outcome is recorded.
  outcome     supported / refuted / inconclusive -- accepted only with an
              evidence id the caller's verifier confirms (a sprint run the
              genome ledger vouches for, a completed bench round). The
              evidence's hash is kept with the outcome.
  to_dna      everything above as a DNA::}AI{::Lang 0.1 document: sources as
              untrusted_reference evidence, hypotheses as hypothesis
              evidence, proven outcomes as verified_observation evidence,
              each pointing at content hashes. Validated by dna_lang.
"""
import hashlib
import html
import json
import os
import re
import time

import paste_digest

ROOT = os.path.join(os.path.expanduser("~"), ".osiris", "research")
INDEX = os.path.join(ROOT, "research.json")
MAX_SOURCE_CHARS = 400_000
KINDS = ("paper", "url", "note", "chat_log", "session_log")
TRUST = {"paper": "external_reference", "url": "external_reference", "note": "operator_note",
         "chat_log": "untrusted_reference", "session_log": "untrusted_reference"}
OUTCOMES = ("supported", "refuted", "inconclusive")

# field -> concept -> regex. Plain vocabulary, no model: a concept is on the
# map only if one of these patterns occurs in a source.
DOMAINS = {
    "quantum": {
        "qubit": r"qubits?", "entanglement": r"entangle\w*", "decoherence": r"decoheren\w*",
        "noise model": r"noise models?|depolari[sz]\w*", "error mitigation": r"error[- ]mitigation|mitigat\w+ error",
        "error correction": r"error[- ]correct\w*|surface codes?", "dynamical decoupling": r"dynamical decoupling",
        "zero-noise extrapolation": r"zero[- ]noise extrapolation|\bzne\b", "fidelity": r"fidelit(y|ies)",
        "circuit depth": r"circuit depth|\bdepth\b", "hamiltonian": r"hamiltonians?", "variational": r"variational|\bvqe\b|\bqaoa\b",
        "measurement": r"measurements?", "superposition": r"superposition",
        "quantum computing": r"quantum comput\w*", "quantum machine learning":
            r"quantum machine learning|\bqml\b|quantum neural networks?",
        "quantum optimization": r"quantum optimi[sz]\w*|quantum annealing",
        "quantum embedding": r"quantum (feature maps?|embeddings?)|neural quantum embedding",
        "trace distance": r"trace distance", "state discrimination": r"state discrimination",
        "quantum hardware": r"quantum hardware|quantum processors?|\bnisq\b|\bnmr\b",
        "dqc1": r"\bdqc1\b|one clean qubit",
    },
    "software engineering": {
        "testing": r"\btests?\b|\btesting\b|unit tests?", "hidden tests": r"hidden tests?",
        # "regression" alone is also a kind of ML model: only regression TESTING is this field's concept.
        "idempotency": r"idempoten\w*", "regression testing": r"regression test\w*", "sandbox": r"sandbox\w*",
        "refactoring": r"refactor\w*", "api": r"\bapis?\b", "specification": r"specifications?|\bspec\b",
        "invariant": r"invariants?", "provenance": r"provenance", "reproducibility": r"reproducib\w*|replicat\w*",
        "requirements engineering": r"requirements? engineering|requirements? (analysis|elicitation)",
        "debugging": r"debug\w*",
        "test optimization": r"test[- ]case (optimi[sz]\w*|prioriti[sz]\w*|selection)|test suite (optimi[sz]\w*|minimi[sz]\w*)",
    },
    "AI / language models": {
        "language model": r"language models?|\bllms?\b", "prompting": r"prompts?|prompting",
        "fine-tuning": r"fine[- ]tun\w*", "benchmark": r"benchmarks?", "hallucination": r"hallucinat\w*",
        "false confidence": r"false confidence|overconfiden\w*|calibrat\w*", "agent": r"\bagents?\b",
        "retrieval": r"retrieval|\brag\b", "transformer": r"transformers?|self-attention|attention (mechanism|heads?|layers?)",
        "machine learning": r"machine learning", "classification": r"classif\w*",
        "representation learning": r"representation learning|(learned|data) representations?|embeddings?",
        "generalization": r"generali[sz]ation", "margin": r"margin[- ]based|margin distributions?|classification margins?", "neural network": r"neural networks?",
        "AI for software engineering": r"ai for software engineering|\bai4se\b",
    },
    "artificial life / genomes": {
        "genome": r"genomes?", "mutation": r"mutat\w*", "evolution": r"evolv\w*|evolution\w*",
        "fitness": r"fitness", "gene regulatory network": r"gene regulatory|\bgrn\b", "organism": r"organisms?",
        "selection": r"\bselection\b",
    },
    "research method": {
        "hypothesis": r"hypothes[ie]s", "control": r"\bcontrols?\b|control (group|condition)",
        "baseline": r"baselines?", "metric": r"metrics?", "falsification": r"falsif\w*|refut\w*",
        "experiment": r"experiments?", "uncertainty": r"uncertaint\w*|confidence intervals?|error bars?",
        "seed": r"\bseeds?\b",
    },
    "OSIRIS": {
        "dna-lang": r"dna[:\s-]*}?ai{?[:\s-]*lang|dna-?lang", "ledger": r"ledgers?", "run record": r"run records?",
        "mentor": r"mentors?", "capability gap": r"capability gaps?", "metamorphosis": r"metamorphos[ie]s",
    },
}
_COMPILED = {d: {c: re.compile(r"\b(?:" + p + r")", re.IGNORECASE) for c, p in cs.items()}
             for d, cs in DOMAINS.items()}


# ------------------------------------------------------------------ storage

def _load():
    try:
        with open(INDEX, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("sources"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"next_source": 1, "next_hypothesis": 1, "sources": [], "hypotheses": []}


def _save(data):
    os.makedirs(ROOT, exist_ok=True)
    tmp = INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, INDEX)


def _text_path(sid):
    return os.path.join(ROOT, "sources", f"{sid}.txt")


def sources():
    return _load()["sources"]


def hypotheses():
    return _load()["hypotheses"]


def source_text(sid):
    """The stored text of a source, or None if missing or no longer matching its hash."""
    s = next((x for x in sources() if x["id"] == sid), None)
    try:
        with open(_text_path(sid), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    if s is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != s["sha256"]:
        return None
    return text


# ------------------------------------------------------------------ sources

def guess_kind(text):
    """paper / chat_log / session_log / note, from the text's shape."""
    if paste_digest.looks_like_session(text):
        return "session_log"
    head = text[:4000]
    if re.search(r"\babstract\b|arxiv|\bdoi\b|\bet al\.|^references$|\bintroduction\b", head,
                 re.IGNORECASE | re.MULTILINE):
        return "paper"
    lines = text.splitlines()
    speakers = sum(1 for l in lines if re.match(r"\s*(user|assistant|you said|chatgpt|claude|gemini|perplexity)\s*:",
                                                l, re.IGNORECASE))
    headings = sum(1 for l in lines if re.match(r"#{2,3} \S", l))
    if speakers >= 2 or (headings >= 2 and any(l.strip() == "Citations:" for l in lines)):
        return "chat_log"
    return "note"


def _title(text, kind, uri):
    lines = text.splitlines()
    arxiv = re.search(r"arXiv:(\d{4}\.\d{4,5})", text)
    for i, line in enumerate(lines):
        # A pasted arXiv abstract page: the title is the first line after "[Submitted on ...]".
        if arxiv and line.strip().startswith("[Submitted on"):
            title = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
            if title:
                return f"arXiv:{arxiv.group(1)} {title}"[:100]
    for line in lines:
        line = " ".join(line.split()).strip("#*> ")
        # A real title has words: not box-drawing rules or a "#!/usr/bin/env" line
        # (on-device titles "╰────" and "!/usr/bin/env python3").
        if len(re.findall(r"[A-Za-z]{2,}", line)) >= 2 and not line.startswith(("!/", "/")):
            return line[:100]
    return (uri or kind)[:100]


def add_source(text, kind=None, uri=None, title=None):
    """Stores one source; the same text again returns the existing record
    (with "duplicate": True). Raises ValueError on empty or oversize text."""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("nothing to import: the text is empty")
    if len(text) > MAX_SOURCE_CHARS:
        raise ValueError(f"source is {len(text)} characters; the limit is {MAX_SOURCE_CHARS}")
    kind = kind or guess_kind(text)
    if kind not in KINDS:
        raise ValueError(f"unknown source kind {kind!r}")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    data = _load()
    same = next((s for s in data["sources"] if s["sha256"] == sha), None)
    if same:
        return dict(same, duplicate=True)
    sid = f"src-{data['next_source']}"
    os.makedirs(os.path.dirname(_text_path(sid)), exist_ok=True)
    with open(_text_path(sid), "w", encoding="utf-8") as f:
        f.write(text)
    rec = {"id": sid, "kind": kind, "trust": TRUST[kind], "title": title or _title(text, kind, uri),
           "uri": uri, "sha256": sha, "chars": len(text), "added": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "fields": sorted(concepts(text))}
    data["sources"].append(rec)
    data["next_source"] += 1
    _save(data)
    return rec


def title_of(s):
    """A source's stored title, or one recomputed from its text when the stored
    one has no words (titles stored before the _title fix: "╰────")."""
    if len(re.findall(r"[A-Za-z]{2,}", s.get("title") or "")) >= 2:
        return s["title"]
    return _title(source_text(s["id"]) or "", s.get("kind"), s.get("uri"))


def html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style|nav|footer|header)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return "\n".join(" ".join(l.split()) for l in text.splitlines() if l.strip())


def fetch_url(url, timeout=20, max_bytes=2_000_000):
    """(text, title) of an http(s) page, as plain text. Raises ValueError/OSError.
    An arxiv.org/abs|pdf link is fetched as its abstract page."""
    if not re.match(r"https?://", url):
        raise ValueError("only http(s) links can be imported")
    m = re.match(r"https?://arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$", url)
    if m:
        url = f"https://arxiv.org/abs/{m.group(1)}"
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "osiris-research-lab/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get("Content-Type", "")
        raw = r.read(max_bytes + 1)[:max_bytes]
    if "pdf" in ctype.lower():
        raise ValueError("that link is a PDF; paste its text, or link its abstract page instead")
    page = raw.decode("utf-8", errors="replace")
    t = re.search(r"(?is)<title[^>]*>(.*?)</title>", page)
    return html_to_text(page), (" ".join(html.unescape(t.group(1)).split())[:100] if t else None)


# ------------------------------------------------------------------ concepts and the map

MIN_EVIDENCE_WORDS = 4  # shorter lines are headings or page furniture ("Replicate Toggle", "HTML (experimental)")
BACKGROUND_SHARE = 0.5  # a concept in more than this share of 4+ sources says nothing about any one link


def concepts(text):
    """{field: {concept: the first line it occurs on}} for one text. Only
    lines of MIN_EVIDENCE_WORDS+ words count: on-device the map quoted an
    arXiv page's "Replicate Toggle" as evidence of reproducibility."""
    found = {}
    lines = [l for l in text.splitlines() if len(l.split()) >= MIN_EVIDENCE_WORDS]
    for field, cs in _COMPILED.items():
        for concept, rx in cs.items():
            for line in lines:
                if rx.search(line):
                    found.setdefault(field, {})[concept] = " ".join(line.split())[:120]
                    break
    return found


def concept_map(srcs=None):
    """The map over all (or the given) sources whose text still verifies:
    {"concepts": {(field, concept): [(source id, line), ...]},
     "shared":   [(field, concept, [source ids])]    -- in 2+ sources,
     "bridges":  [(field, concept, [source ids], [fields joined])] -- a
                 shared concept whose sources come from different fields:
                 the interdisciplinary connections,
     "links":    [(fieldA, conceptA, fieldB, conceptB, [source ids])] -- two
                 fields meeting in the same source(s), most-sourced first,
     "skipped":  [source ids whose stored text no longer matches its hash]}"""
    grounded, skipped = {}, []
    srcs = srcs if srcs is not None else sources()
    untrusted = {s["id"] for s in srcs if s.get("trust") == "untrusted_reference"}
    for s in srcs:
        text = source_text(s["id"])
        if text is None:
            skipped.append(s["id"])
            continue
        for field, cs in concepts(text).items():
            for concept, line in cs.items():
                grounded.setdefault((field, concept), []).append((s["id"], line))
    # A concept in most sources (on-device: "experiment" in 11 of 12) links
    # everything and so says nothing: it is background, kept out of the links,
    # which are ranked rarest first -- the specific connections.
    n = len({sid for v in grounded.values() for sid, _ in v})
    background = sorted(((f, c, len(v)) for (f, c), v in grounded.items()
                         if n >= 4 and len(v) > BACKGROUND_SHARE * n), key=lambda x: (-x[2], x[0], x[1]))
    bg = {(f, c) for f, c, _k in background}
    grounded_fg = {k: v for k, v in grounded.items() if k not in bg}
    # Rank: links grounded in papers and the operator's own notes before links
    # resting on untrusted chat logs (on-device the top links were all pasted
    # AI answers), then rarest first.
    shared = sorted(((f, c, [sid for sid, _ in v]) for (f, c), v in grounded_fg.items() if len(v) >= 2),
                    key=lambda x: (sum(sid in untrusted for sid in x[2]) / len(x[2]), len(x[2]), x[0], x[1]))
    by_source = {}
    for (f, c), v in grounded_fg.items():
        for sid, _ in v:
            by_source.setdefault(sid, []).append((f, c))
    links = {}
    for sid, fc in by_source.items():
        for i, (f1, c1) in enumerate(sorted(fc)):
            for f2, c2 in sorted(fc)[i + 1:]:
                if f1 != f2:
                    links.setdefault((f1, c1, f2, c2), []).append(sid)
    links = sorted(((a, b, c, d, sids) for (a, b, c, d), sids in links.items() if len(sids) >= 2),
                   key=lambda x: (len(x[4]), x[0], x[1], x[2], x[3]))
    fields_of = {sid: {f for f, _ in fc} for sid, fc in by_source.items()}
    bridges = []
    for f, c, sids in shared:
        others = [fields_of[sid] - {f} for sid in sids]
        joined = sorted(set().union(*others) - set.intersection(*others)) if others else []
        if joined:
            bridges.append((f, c, sids, joined))
    fields_all = {}
    for (f, c), v in grounded.items():
        for sid, _ in v:
            fields_all.setdefault(sid, set()).add(f)
    return {"concepts": grounded, "shared": shared, "bridges": bridges, "links": links, "skipped": skipped,
            "background": background, "fields": {sid: sorted(fs) for sid, fs in fields_all.items()}}


# ------------------------------------------------------------------ hypotheses

RULES = {
    "question": (lambda h: len(h["question"].split()) >= 6, "Question: what is being tested, in a sentence (6+ words)."),
    "prediction": (lambda h: len(h["prediction"].split()) >= 6,
                   "Prediction: the outcome you expect, specific enough to be wrong (6+ words)."),
    "variable": (lambda h: len(h["variable"]) >= 3, "Varied: name what changes between conditions."),
    "metric": (lambda h: len(h["metric"]) >= 3, "Metric: name how the outcome is measured."),
    "controls": (lambda h: bool(h["controls"]), "Controls: name at least one thing held fixed."),
    "refuted_if": (lambda h: len(h["refuted_if"].split()) >= 4,
                   "Refuted if: the result that would show the prediction is wrong (4+ words)."),
}
EXAMPLES = {
    "question": "Does listing invariants before coding reduce mentor false confidence?",
    "prediction": "Invariant-first prompts cut false-confidence events versus the baseline prompt on the same tasks.",
    "variable": "prompt strategy: baseline vs. invariant-first",
    "metric": "hidden-test pass rate and false-confidence count",
    "controls": "same model -- then same 3 bench tasks -- then k=1",
    "refuted_if": "false confidence is equal or higher with invariant-first prompts",
}


def new_hypothesis(question="", prediction="", variable="", metric="", controls=(), refuted_if="", sources=()):
    clean = lambda s: " ".join(str(s).split())
    return {"question": clean(question), "prediction": clean(prediction), "variable": clean(variable),
            "metric": clean(metric), "controls": [clean(c) for c in controls if str(c).strip()],
            "refuted_if": clean(refuted_if), "sources": [s for s in sources if s]}


def problems(h):
    return [msg for check, msg in RULES.values() if not check(h)]


def field_problem(field, value):
    check, msg = RULES[field]
    return None if check(new_hypothesis(**{field: value})) else msg


FIELD_LABELS = {"question": "Question", "prediction": "Prediction", "variable": "Varied", "metric": "Metric",
                "controls": "Controls", "refuted_if": "Refuted if"}
# Claims a model drafted on-device that no local run could back (2026-09-24).
OVERCLAIM = re.compile(r"qubit capabilit|(ollama|llama|language model)\W+(\w+\W+){0,2}(qubit|quantum)|quantum advantage|"
                       r"conscious|new physics|novel genome|revolutioni[sz]", re.IGNORECASE)


def parse_drafts(text, known_sources=()):
    """Model-written hypotheses in the requested format ("HYPOTHESIS n" then
    one "Label: value" line per field) -> [{"hypothesis": new_hypothesis(...),
    "problems": [...]}]. Problems are the RULES a field fails, plus any
    overclaim. Source ids are kept only if they exist. Code decides; the
    model's text is never trusted as complete."""
    out = []
    for block in re.split(r"(?im)^[\s#*]*hypothesis\s*\d+\b.*$", text)[1:]:
        vals = {}
        for field, label in FIELD_LABELS.items():
            m = re.search(rf"(?im)^[\s*\-]*\**{re.escape(label)}\**\s*:\**\s*(.+)$", block)
            vals[field] = m.group(1).strip(" *") if m else ""
        raw = vals.pop("controls")  # "a; b" as asked; commas only when no semicolon ("same tasks, k=1" is one)
        controls = [c.strip() for c in (raw.split(";") if ";" in raw else re.split(r",(?![^()]*\))", raw)) if c.strip()]
        srcs = [x for x in dict.fromkeys(re.findall(r"src-\d+", block)) if x in known_sources]
        h = new_hypothesis(controls=controls, sources=srcs, **vals)
        probs = problems(h)
        bad = OVERCLAIM.search(block)
        if bad:
            probs.append(f"Overclaim: \"{bad.group(0)}\" -- nothing local can test that.")
        if not srcs:
            probs.append("Sources: names no source from the lab, so it is not grounded.")
        if any(h[f] for f in ("question", "prediction")):
            out.append({"hypothesis": h, "problems": probs})
    return out


def save_hypothesis(h):
    data = _load()
    known = {s["id"] for s in data["sources"]}
    unknown = [s for s in h["sources"] if s not in known]
    if unknown:
        raise ValueError(f"no such source(s): {', '.join(unknown)}")
    h = dict(h, id=f"hyp-{data['next_hypothesis']}", status="draft", outcome=None,
             created=time.strftime("%Y-%m-%dT%H:%M:%S"))
    data["hypotheses"].append(h)
    data["next_hypothesis"] += 1
    _save(data)
    return h


def record_outcome(hid, outcome, evidence_id, verify):
    """Marks hypothesis hid supported / refuted / inconclusive -- only if
    verify(evidence_id) returns (True, description, sha256). The outcome is
    stored with the evidence id, its description and hash. A hypothesis
    already decided cannot be decided again (a new hypothesis can be drafted).
    Raises ValueError, naming why, otherwise."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)}")
    data = _load()
    h = next((x for x in data["hypotheses"] if x["id"] == hid), None)
    if h is None:
        raise ValueError(f"no hypothesis {hid}")
    if h.get("outcome"):
        raise ValueError(f"{hid} is already {h['outcome']['result']} (evidence {h['outcome']['evidence']}); "
                         f"draft a new hypothesis to test it again")
    ok, description, sha = verify(evidence_id)
    if not ok:
        raise ValueError(f"evidence {evidence_id} does not verify: {description}")
    h["outcome"] = {"result": outcome, "evidence": evidence_id, "evidence_sha256": sha,
                    "evidence_description": description, "recorded": time.strftime("%Y-%m-%dT%H:%M:%S")}
    h["status"] = outcome
    _save(data)
    return h


# ------------------------------------------------------------------ DNA::}AI{::Lang

def to_dna(genome):
    """The lab as a DNA::}AI{::Lang 0.1 IR dict (validate with dna_lang.validate_ir)."""
    data = _load()
    by_id = {s["id"]: s for s in data["sources"]}
    ref = lambda sha: f"dna:sha256:{sha}"
    evidence = {}
    for s in data["sources"]:
        evidence[s["id"]] = {"kind": "untrusted_reference", "refs": [ref(s["sha256"])],
                             "statement": f"{s['kind']} ({s['trust']}): {s['title']}"}
    for h in data["hypotheses"]:
        b = h.get("bridge")
        bridge = (f" Bridge ({' / '.join(b['fields'])}): {b['mechanism']} Permits: {b['permitted_inference']} "
                  f"Does not show: {'; '.join(b['forbidden_inferences'])}." if b else "")
        evidence[h["id"]] = {"kind": "hypothesis", "refs": sorted({ref(by_id[s]["sha256"]) for s in h["sources"]}),
                             "statement": f"{h['prediction']} Refuted if: {h['refuted_if']}{bridge}"}
        if h.get("outcome"):
            o = h["outcome"]
            evidence[f"{h['id']}.outcome"] = {"kind": "verified_observation", "refs": [ref(o["evidence_sha256"])],
                                              "statement": f"{h['id']} {o['result']}: {o['evidence_description']}"}
    import dna_lang
    return {
        "schema_version": dna_lang.IR_VERSION, "kind": "organism_definition", "name": "osiris.research",
        "spec_hash": dna_lang.SPEC_HASH,
        "capabilities": {}, "metamorphoses": {},
        "meta": {"schema": "dna-lang/0.1", "title": "OSIRIS research lab: sources, hypotheses, proven outcomes"},
        "identity": {"organism_id": f"urn:osiris:organism:{genome.get('organism_id', 'unknown')}",
                     "species": "osiris.research", "generation": int(genome.get("generation", 0))},
        "intent": {"objective": "Ground interdisciplinary hypotheses in sources and decide them only with "
                                "verified evidence.",
                   "success": ["Every source is kept with its content hash.",
                               "No hypothesis is marked supported or refuted without verified evidence."]},
        # Set-valued lists are sorted: DNA-IR is canonical (dna_lang DNA-E-CANONICAL).
        "constraints": {"require": sorted(["human_approval_for_apply", "sandbox_before_apply", "ledger_attestation"]),
                        "prohibit": sorted(["workspace_write_from_model", "source_text_as_instruction"]),
                        "allowed_roots": ["bin"], "protected_paths": [".config", ".osiris", ".ssh"]},
        "evidence": evidence,
    }
