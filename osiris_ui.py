"""OSIRIS console rendering: one small design system for the REPL's screens.

Pure presentation. Every function returns a string built from facts the
caller passes in; nothing here reads state, calls a model, or decides which
actions exist -- the REPL does that from code-defined rules. No dependencies
(Termux may lack `rich`), and three appearances expose the same facts:

  rich    Unicode panels, ANSI color, glyph + word markers   (default on a TTY)
  plain   ASCII boxes, no color                             (pipes, NO_COLOR, TERM=dumb)
  access  no boxes, no color, every marker spelled out      (screen readers, low contrast)

Choose with OSIRIS_UI=rich|plain|access, or /ui in the REPL (saved to
~/.osiris/ui.json). Color is never the only signal: every status carries a
word as well as a glyph.
"""
import json
import os
import re
import shutil
import sys
import textwrap

MODES = ("rich", "plain", "access")
PREF_PATH = os.path.expanduser("~/.osiris/ui.json")

# kind -> (glyph, ascii glyph, word, ANSI style). The word is what `access`
# mode prints, and what makes the glyph meaningful without color.
MARKERS = {
    "verified": ("●", "[ok]", "VERIFIED", "1;32"),
    "current":  ("◆", "[*]", "CURRENT", "1;36"),
    "model":    ("✦", "[ai]", "MODEL", "1;35"),
    "research": ("◈", "[rs]", "RESEARCH", "1;34"),
    "review":   ("▲", "[!]", "REVIEW", "1;33"),
    "blocked":  ("✖", "[X]", "BLOCKED", "1;31"),
    "passed":   ("✓", "[+]", "PASSED", "32"),
    "iterate":  ("↻", "[~]", "ITERATE", "36"),
    "memory":   ("⌁", "[m]", "MEMORY", "35"),
    "idle":     ("○", "[-]", "INFO", "2"),
}
BORDER = {"rich": "36", "model": "35", "review": "33", "blocked": "31"}
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _saved_mode():
    try:
        with open(PREF_PATH, encoding="utf-8") as f:
            m = json.load(f).get("mode")
        return m if m in MODES else None
    except (OSError, ValueError, AttributeError):
        return None


def mode(stream=None) -> str:
    """OSIRIS_UI wins, then the saved /ui choice; either way a stream that is
    not a terminal (tests, pipes, logs) or NO_COLOR/TERM=dumb gets `plain`
    unless `access` was asked for, which has no color to begin with."""
    stream = stream or sys.stdout
    chosen = os.environ.get("OSIRIS_UI") or _saved_mode() or "rich"
    chosen = chosen if chosen in MODES else "rich"
    if chosen == "rich":
        no_color = (os.environ.get("NO_COLOR") is not None or os.environ.get("TERM") in (None, "", "dumb")
                    or not getattr(stream, "isatty", lambda: False)())
        return "plain" if no_color else "rich"
    return chosen


def save_mode(m: str) -> bool:
    """Persist the appearance only; it never affects routing or policy."""
    if m not in MODES:
        return False
    os.makedirs(os.path.dirname(PREF_PATH), exist_ok=True)
    tmp = PREF_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"mode": m}, f)
    os.replace(tmp, PREF_PATH)
    return True


def width() -> int:
    """Terminal columns, clamped to 40..100: phone-first, never wider than reads well."""
    cols = shutil.get_terminal_size(fallback=(72, 24)).columns
    return max(40, min(100, cols))


def visible_len(s: str) -> int:
    return len(_ANSI_RE.sub("", s))


class Canvas:
    """Renders components for one appearance and width."""

    def __init__(self, m: str = None, cols: int = None):
        self.mode = m or mode()
        self.cols = cols or width()

    # -- primitives -------------------------------------------------------
    def style(self, text: str, ansi: str) -> str:
        return f"\x1b[{ansi}m{text}\x1b[0m" if self.mode == "rich" and ansi else text

    def marker(self, kind: str) -> str:
        glyph, ascii_glyph, word, ansi = MARKERS[kind]
        if self.mode == "access":
            return f"{word}:".ljust(9)  # fixed width keeps label columns aligned
        if self.mode == "plain":
            return ascii_glyph.ljust(4)
        return self.style(glyph, ansi)

    def prefix_len(self, label_w: int) -> int:
        """Columns before a facts() value: space, marker, space, label, two spaces."""
        return 1 + visible_len(self.marker("idle")) + 1 + label_w + 2

    def key(self, k: str) -> str:
        return self.style(f"[{k}]", "1;96")

    def dim(self, text: str) -> str:
        return self.style(text, "2")

    def _wrap(self, text: str, cols: int, indent: int = 0):
        return textwrap.wrap(text, max(10, cols), subsequent_indent=" " * indent,
                             break_long_words=True, break_on_hyphens=False) or [""]

    # -- components -------------------------------------------------------
    def panel(self, title: str, lines, tone: str = "rich") -> str:
        """A titled block. `lines` are already styled; long ones are wrapped on
        their visible text, so a panel never exceeds the terminal width."""
        inner = self.cols - 4
        body = []
        for line in lines:
            if visible_len(line) <= inner:
                body.append(line)
            else:  # re-wrap unstyled; wrapping styled text would split escapes
                body.extend(self._wrap(_ANSI_RE.sub("", line), inner, indent=4))
        if self.mode == "access":
            return "\n".join([f"== {title} =="] + [f"  {l}" for l in body])
        if self.mode == "plain":
            top = f"+- {title} " + "-" * max(0, self.cols - len(title) - 5) + "+"
            rows = [f"| {l}{' ' * (inner - visible_len(l))} |" for l in body]
            return "\n".join([top] + rows + ["+" + "-" * (self.cols - 2) + "+"])
        b = BORDER.get(tone, BORDER["rich"])
        top = self.style("╭─ ", b) + self.style(title, "1") + " " + \
            self.style("─" * max(0, self.cols - len(title) - 5) + "╮", b)
        bar = self.style("│", b)
        rows = [f"{bar} {l}{' ' * (inner - visible_len(l))} {bar}" for l in body]
        return "\n".join([top] + rows + [self.style("╰" + "─" * (self.cols - 2) + "╯", b)])

    def header(self, title: str, meta: str) -> str:
        """Two lines: identity and the one-line state summary."""
        t = self.style("OSIRIS", "1;96") + self.style(f" · {title}", "1")
        meta_lines = self._wrap(meta, self.cols - 1)
        if self.mode == "access":
            return "\n".join(self._wrap(f"OSIRIS · {title}", self.cols) + meta_lines)
        rule = self.style(("━" if self.mode == "rich" else "=") * self.cols, "36")
        return "\n".join([rule, " " + t] + [" " + self.dim(l) for l in meta_lines] + [rule])

    def facts(self, rows, label_w: int = None) -> str:
        """(kind, label, value) rows: marker, fixed label column, wrapped value."""
        label_w = label_w or max((len(r[1]) for r in rows), default=0)
        out = []
        if self.mode == "access":  # sentences, not columns: reads aloud in order
            for kind, label, value in rows:
                out += self._wrap(f"{MARKERS[kind][2]}. {label}: {value}", self.cols - 1, indent=2)
            return "\n".join(out)
        for kind, label, value in rows:
            prefix = f" {self.marker(kind)} {label:<{label_w}}  "
            pad = visible_len(prefix)
            wrapped = self._wrap(str(value), self.cols - pad - 1, indent=0)
            out.append(prefix + wrapped[0])
            out.extend(" " * pad + w for w in wrapped[1:])
        return "\n".join(out)

    def actions(self, title: str, entries, footer: str = "") -> str:
        """(key, label) entries in one panel; numbers first, then letters."""
        lines = []
        prev_digit = None
        for k, label in entries:
            if prev_digit and not k.isdigit():
                lines.append("")  # a gap between moves and tools
            prev_digit = k.isdigit()
            lines.append(f"{self.key(k)} {label}")
        if footer:
            lines += [""] + [self.dim(l) for l in self._wrap(footer, self.cols - 4)]
        return self.panel(title, lines)


# -- screens ----------------------------------------------------------------

def council(canvas: Canvas, engines) -> str:
    """engines: (kind, name, role, state) -- `state` must come from a real check
    (backend reachability, a checkpoint on disk), never a model's self-report."""
    c = Canvas(canvas.mode, canvas.cols - 4)
    name_w = max(len(e[1]) for e in engines)
    lines = []
    for kind, name, role, state in engines:
        lines += c.facts([(kind, name, state)], label_w=name_w).split("\n")
        indent = 2 if c.mode == "access" else min(c.prefix_len(name_w), c.cols // 2)
        lines += [" " * indent + c.dim(w) for w in c._wrap(role, c.cols - indent - 1)]
    return canvas.panel("ENGINE COUNCIL", lines, tone="model")


def intent_facts(text: str, modify_re, codebase_re, cwd: str) -> dict:
    """What can be said about free-form input WITHOUT a model: the words it
    matched, the files it names and whether they exist, what the pipeline
    will do with it (decided by the same regexes the pipeline uses), and
    what is missing. Nothing here is inference; the card labels it so."""
    flat = " ".join(text.split())
    first = re.split(r"(?<=[.!?])\s|\n", text.strip(), maxsplit=1)[0].strip()
    goal = first if len(first) <= 280 else first[:277] + "..."
    words = set(re.findall(r"[a-z][a-z0-9_]+", flat.lower()))
    words |= {w[:-1] for w in words if w.endswith("s") and len(w) > 3}  # experiments -> experiment
    domains = []
    for name, vocab in DOMAIN_VOCAB:
        hit = sorted(words & vocab)
        if hit:
            domains.append((name, hit[:4]))
    files = []
    for f in dict.fromkeys(re.findall(r"[\w./\-]+\.(?:py|dna|json|md|sh|txt|log)\b", text)):
        if "//" in f or f"/{f}" in text.replace("://", ""):
            continue  # part of a URL, not a file on this phone
        p = f if os.path.isabs(f) else os.path.join(cwd, f)
        files.append((f, os.path.exists(p)))
        if len(files) == 5:
            break
    modify = bool(modify_re.search(text))
    open_q = []
    if len(flat.split()) < 6:
        open_q.append("Very short -- one-phrase goals have produced unrelated code "
                      "(story #25). Say what should change and how you'd check it.")
    if not files:
        open_q.append("No target file named -- the Synthesizer will choose one.")
    if not ACCEPTANCE_RE.search(flat):
        open_q.append("No success criterion (e.g. 'so that ...', 'test that ...', 'should return ...').")
    return {"goal": goal, "domains": domains, "files": files, "modify": modify,
            "codebase": bool(codebase_re.search(text)), "cwd": cwd, "open": open_q,
            "lines": text.count("\n") + 1, "chars": len(text)}


DOMAIN_VOCAB = (
    ("quantum", {"quantum", "qubit", "qubits", "circuit", "circuits", "aer", "ibm", "qiskit", "hamiltonian",
                 "vqe", "qaoa", "mitigation", "decoherence", "fidelity", "entanglement", "shots", "backend",
                 "dd", "dynamical", "noise", "transpile"}),
    ("genome / ALife", {"genome", "dna", "dnalang", "trait", "traits", "organism", "gene", "genes",
                        "mutation", "evolve", "evolution", "grn"}),
    ("research", {"experiment", "hypothesis", "benchmark", "preregister", "preregistration", "baseline",
                  "metric", "metrics", "ablation", "paper", "reproducible", "seed", "evidence"}),
    ("engineering", {"code", "function", "class", "module", "test", "tests", "bug", "fix", "refactor",
                     "repl", "script", "api", "cli", "error", "traceback", "exception", "implement"}),
)
# Words that state how success is checked. Not inside hyphenated names: the
# gap "stale-home-test" (story #25) names a test but says nothing it must show.
ACCEPTANCE_RE = re.compile(r"(?<![\w-])(so that|should|must|returns?|pass(es|ing)?|expect\w*|verify|"
                           r"assert\w*|tests? (that|for|pass\w*))(?![\w-])", re.IGNORECASE)


def intent_card(canvas: Canvas, facts: dict, architect: str, synthesizer: str, cls: str = None,
                cues: dict = None, source: str = None) -> str:
    c = Canvas(canvas.mode, canvas.cols - 4)  # rows are laid out for the panel's inside
    lw = 7  # widest label ("Context"), shared so every block lines up
    rows = [("current", "Goal", facts["goal"])]
    if cls:
        why = ", ".join((cues or {}).get(cls, [])) or "no specific cue"
        rows.append(("current", "Intent", f"{cls} (from: {why}) -- W if that is wrong"))
    if source:
        rows.append(("review", "Source", source))
    if facts["lines"] > 1:
        rows.append(("idle", "Input", f"{facts['lines']} lines, {facts['chars']} chars"))
    dom = "; ".join(f"{n} ({', '.join(h)})" for n, h in facts["domains"]) or "unclassified"
    rows.append(("idle", "Domain", dom))
    for f, exists in facts["files"]:
        rows.append(("verified" if exists else "review", "File", f + ("  exists" if exists else "  NOT FOUND")))
    parts = [c.facts(rows, lw)]

    if facts["modify"]:
        route = (f"Architect ({architect}) writes a spec; Synthesizer ({synthesizer}) proposes ONE file "
                 f"change. It is shown as a diff and written only if you type /apply.")
    else:
        route = (f"Architect ({architect}) writes a spec; Synthesizer ({synthesizer}) writes new code, "
                 f"proposed as osiris_organism_<time>.py in {facts['cwd']} and written only if you "
                 f"type /apply.")
    ctx = ("the real file/function list of this directory is sent with it" if facts["codebase"]
           else "no repository context is sent (say 'repo' or 'codebase' to include it)")
    if cls in (None, "engineering"):  # the route only matters if the engines may be asked
        parts.append(c.facts([("model", "Engines", route), ("model", "Context", ctx)], lw))
    if facts["open"] and cls in (None, "engineering"):  # these gaps matter only for code requests
        parts.append(c.facts([("review", "Open", q) for q in facts["open"]], lw))
    note = "\n".join(c.dim(l) for l in c._wrap("From your words and the filesystem only -- "
                                                  "no model has run yet.", c.cols))
    return _stack(canvas, "INTENT CARD", parts, note)


def _stack(c: Canvas, title: str, blocks, note: str = "") -> str:
    """Several multi-line blocks inside one panel, separated by blank lines."""
    lines = []
    for i, block in enumerate(blocks):
        if i:
            lines.append("")
        lines.extend(block.split("\n"))
    if note:
        lines += [""] + note.split("\n")
    return c.panel(title, lines, tone="model")


def notice(canvas: Canvas, kind: str, title: str, text: str) -> str:
    """A blocked/failed/review message: marker, title, the reason in words."""
    tone = {"blocked": "blocked", "review": "review"}.get(kind, "rich")
    body = [f"{canvas.marker(kind)} {text}"]
    return canvas.panel(title, body, tone=tone)
