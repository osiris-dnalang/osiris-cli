"""What OSIRIS knows about its own project, read from Devin's files.

The mentor model has no idea what OSIRIS is or what has been measured; asked
"what do you know" it can only produce pleasantries (2026-09-29 transcript).
This module gives it two things, both read from disk, never written by a model:

  brief     a short, stable summary: the organism_sim scorecard verdicts (a
            generated, test-guarded table) and one line per project. Goes in
            the system prompt, which stays byte-identical between turns so
            Ollama can reuse its cached prefix.
  lookup    per-message retrieval (BM25 over paragraphs of the sources below),
            returned with file paths so answers can cite where a fact came from.

Sources are ~/.osiris/living/knowledge.json {"sources": [...]} when present,
otherwise DEFAULT_SOURCES. The osiris-cli README is left out on purpose: it
frames staggered DD as "quantum advantage", which the audits do not support.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional

HOME = os.path.expanduser("~")
LIVING_HOME = os.path.join(HOME, ".osiris", "living")

DEFAULT_SOURCES = [
    "docs/HONEST_ASSESSMENT.md",
    "docs/FORENSIC_AUDIT.md",
    "docs/NISQ_PATHWAYS.md",
    "docs/FLYWHEEL_ASSESSMENT.md",
    "docs/DNALANG_SALVAGE.md",
    "organism_sim/README.md",
    "organism_sim/docs/PROGRAM.md",
    "dnalang-core/README.md",
    "bridge/README.md",
]
SCORECARD_SOURCE = "organism_sim/README.md"

PROJECTS = """\
- organism_sim: rule-evolving ALife agents (XCS classifier systems) with pre-registered experiments.
- dnalang-core: dnalang 0.2, a from-scratch rewrite of the dna::}{::lang circuit language (Qiskit, OpenQASM 3, hash-chained ledger).
- bridge: an organism controller over dnalang's dynamical-decoupling search space, compared budget-matched with a GA.
- osiris-cli: this console; your core (osiris.nclm) trains on every conversation and speaks only after passing a held-out gate.
- Hardware: IBM Heron runs of GHZ witnesses and staggered dynamical decoupling, logged in a write-ahead ledger."""

CHUNK_CHARS = 900
STOP = frozenset("""a an and are as at be but by can did do does for from has have how i if in is it its
me my of on or so that the their them then there these this to was we were what when where which who
why will with you your about tell know yourself osiris""".split())


def _tokens(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", text.lower()) if w not in STOP]


def _sources(living_home: str, base: str) -> List[str]:
    try:
        with open(os.path.join(living_home, "knowledge.json"), encoding="utf-8") as f:
            listed = json.load(f).get("sources") or DEFAULT_SOURCES
    except (OSError, ValueError):
        listed = DEFAULT_SOURCES
    return [p if os.path.isabs(p) else os.path.join(base, p) for p in listed]


def chunk_markdown(text: str) -> List[tuple]:
    """(heading, text) pieces of at most ~CHUNK_CHARS, split on headings then paragraphs."""
    out, heading, buf = [], "", ""
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para or para.startswith("<!--"):
            continue
        m = re.match(r"(#{1,4})\s+(.*)", para)
        if m and "\n" not in para:
            if buf:
                out.append((heading, buf))
            heading, buf = m.group(2).strip(), ""
            continue
        if buf and len(buf) + len(para) > CHUNK_CHARS:
            out.append((heading, buf))
            buf = ""
        buf = (buf + "\n\n" + para).strip() if buf else para[: CHUNK_CHARS * 2]
    if buf:
        out.append((heading, buf))
    return out


def scorecard_verdicts(readme_text: str) -> List[str]:
    """'experiment: VERDICT' for each row between the scorecard markers."""
    m = re.search(r"<!-- scorecard:start -->(.*?)<!-- scorecard:end -->", readme_text, re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] not in ("experiment", "") and not set(cells[0]) <= set("-"):
            rows.append(f"{cells[0]}: {cells[1]}")
    return rows


class Knowledge:
    def __init__(self, living_home: str = LIVING_HOME, base: str = HOME,
                 sources: Optional[List[str]] = None):
        self.base = base
        paths = sources if sources is not None else _sources(living_home, base)
        self.texts: Dict[str, str] = {}
        for p in paths:
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    self.texts[os.path.relpath(p, base)] = f.read()
            except OSError:
                continue
        self.chunks = [(src, h, t) for src, text in self.texts.items() for h, t in chunk_markdown(text)]
        self._tf = [Counter(_tokens(h + " " + t)) for _, h, t in self.chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = (sum(self._len) / len(self._len)) if self._len else 1.0
        df = Counter(w for tf in self._tf for w in tf)
        n = len(self.chunks)
        self._idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def brief(self) -> str:
        parts = ["Devin's projects:\n" + PROJECTS]
        for src in sorted(self.texts, key=lambda k: k != SCORECARD_SOURCE):
            verdicts = scorecard_verdicts(self.texts[src])
            if verdicts:
                parts.append(f"Pre-registered results so far (from {src}, generated from "
                             "results/ and test-guarded):\n" + "\n".join("- " + v for v in verdicts))
                break
        return "\n\n".join(parts)

    def lookup(self, query: str, k: int = 3, per_source: int = 2) -> List[dict]:
        q = set(_tokens(query))
        if not q or not self.chunks:
            return []
        scored = []
        for i, tf in enumerate(self._tf):
            s = 0.0
            for w in q:
                f = tf.get(w)
                if f:
                    s += self._idf[w] * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * self._len[i] / self._avg))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        out, used = [], Counter()
        for s, i in scored:
            src, h, t = self.chunks[i]
            if used[src] >= per_source:
                continue
            used[src] += 1
            out.append({"source": src, "heading": h, "text": t, "score": round(s, 2)})
            if len(out) >= k:
                break
        return out

    @staticmethod
    def format_notes(hits: List[dict]) -> str:
        return "\n\n".join(f"[{h['source']}" + (f" § {h['heading']}" if h["heading"] else "") + "]\n"
                           + h["text"] for h in hits)
