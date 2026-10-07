#!/usr/bin/env python3
"""
prompt_strategies.py -- versioned prompt strategies for benchmark trials.

A strategy is a fixed preamble placed before a bench task's prompt, to test a
hypothesis about HOW to ask a mentor (e.g. "listing invariants first reduces
false confidence"). It changes only what the model is asked: the task suite,
the hidden tests and the runner (osiris_bench.py and the files runner_sha256
covers) are untouched, so a trial round stays comparable with a baseline round
of the same model -- same suite, same runner, one declared difference, whose
text is hashed (strategy_sha256) into the round's start entry.

A strategy is text in this file, reviewed like code: never model output, never
set from a paste. Changing a strategy's text changes its hash; give it a new
id (…-v2) rather than editing one that has results.
"""
import hashlib

STRATEGIES = {
    "invariant-first-v1": {
        "about": "list the behaviour the code must keep (repeats, bad input, sources) before writing it, "
                 "and make the test assert each of those",
        "text": (
            "BEFORE YOU WRITE ANY CODE, work out -- silently, without printing it -- the invariants this module "
            "must keep:\n"
            "1. What must stay true when the same operation is done twice (idempotency, duplicates).\n"
            "2. How invalid, empty and boundary inputs must be handled.\n"
            "3. Which values must carry or report their source, and what must never be invented.\n"
            "4. What an easy test would miss.\n"
            "Then write the module so it keeps every one of them, and write the test so it asserts every one "
            "of them -- not only the easy case. Output exactly the format required below, nothing else.\n\n"
        ),
    },
}


def get(sid):
    """The strategy dict, or KeyError naming the known ids."""
    if sid not in STRATEGIES:
        raise KeyError(f"unknown strategy {sid!r}; known: {', '.join(sorted(STRATEGIES))}")
    return STRATEGIES[sid]


def sha256(sid):
    return hashlib.sha256(get(sid)["text"].encode("utf-8")).hexdigest()


def apply(sid, prompt):
    """The task prompt with the strategy's preamble in front of it."""
    return get(sid)["text"] + prompt
