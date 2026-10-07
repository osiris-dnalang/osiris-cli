#!/usr/bin/env python3
"""
paste_digest.py -- what a pasted terminal session says happened, read by code.

The operator works from a phone and pastes whole Termux sessions (often with
an AI review appended) back into OSIRIS. Routed as a request, a paste starting
"Welcome to Termux" became an engineering goal named "Welcome to Termux"
(on-device, 2026-09-24). A session log is not a request: it is a record. This
module recognizes one by its shape and pulls out, with fixed patterns and no
model, the commands typed, the results, the problems and the ids mentioned.
Everything in it stays reference material; nothing here runs or records it.
"""
import re

_PROMPT = re.compile(r"^\s*(osiris>|~ \$|\$ )\s*(.*)$")
_BOX = re.compile(r"^\s*[╭│╰]")
_RUN_ID = re.compile(r"\brun-\d{8}T\d{6}Z-[0-9a-f]{6}\b")
_BENCH_ID = re.compile(r"\bbench-\d{8}T\d{6}Z-[0-9a-f]{6}\b")
_PROBLEM = re.compile(r"(\[!\]|Traceback \(most recent call last\)|\b\w*Error\b|\berror:|No such file|"
                      r"\brefused\b|\bFAILED\b|\bINVALID\b|\bnot recorded\b)")
_OUTCOME = re.compile(r"(✅|\bPASS(ED)?\b|Applied and recorded|Run recorded|Suite valid|Discarded|"
                      r"Gap recorded|Re-routed as|verified in ledger)")


def looks_like_session(text: str) -> bool:
    """A pasted terminal session: 6+ lines with two or more shell/osiris
    prompts, or a Termux banner plus a prompt, or 3+ lines of OSIRIS panels."""
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 6:
        return False
    prompts = sum(1 for l in lines if _PROMPT.match(l))
    banner = any("Welcome to Termux" in l for l in lines)
    boxes = sum(1 for l in lines if _BOX.match(l))
    return prompts >= 2 or (banner and prompts >= 1) or (boxes >= 3 and prompts >= 1)


def _unique(items, limit):
    out = []
    for x in items:
        x = " ".join(x.split())[:110]
        if x and x not in out:
            out.append(x)
    return out[:limit], max(0, len(dict.fromkeys(" ".join(i.split())[:110] for i in items)) - limit)


def digest(text: str) -> dict:
    """Facts read from a session paste: sessions (Termux banners), commands
    typed at osiris> and at the shell, result lines, problem lines, run and
    bench ids, and whether an AI-written review is appended (markdown
    headings or a Citations: list). Each list is de-duplicated and capped."""
    lines = text.splitlines()
    osiris_cmds, shell_cmds, results, problems = [], [], [], []
    for l in lines:
        m = _PROMPT.match(l)
        if m and m.group(2).strip():
            (osiris_cmds if m.group(1) == "osiris>" else shell_cmds).append(m.group(2))
            continue
        if _PROBLEM.search(l):
            problems.append(l.strip(" │"))
        elif _OUTCOME.search(l):
            results.append(l.strip(" │"))
    review_sections = sum(1 for l in lines if re.match(r"^#{2,3} \S", l))
    cited = any(l.strip() == "Citations:" for l in lines)
    oc, oc_more = _unique(osiris_cmds, 12)
    sc, sc_more = _unique(shell_cmds, 6)
    rs, rs_more = _unique(results, 8)
    pr, pr_more = _unique(problems, 8)
    return {
        "lines": len(lines),
        "sessions": sum(1 for l in lines if "Welcome to Termux" in l),
        "osiris_commands": oc, "osiris_more": oc_more,
        "shell_commands": sc, "shell_more": sc_more,
        "results": rs, "results_more": rs_more,
        "problems": pr, "problems_more": pr_more,
        "run_ids": sorted(set(_RUN_ID.findall(text))),
        "bench_ids": sorted(set(_BENCH_ID.findall(text))),
        "review": review_sections > 0 or cited,
        "review_sections": review_sections,
    }
