"""
intent_router.py -- what free-form operator text is FOR, decided by code.

Before this, every non-command message went to the code-generation
pipeline: on 2026-09-24 "hello osiris" produced an invented OSIRISSystems
class ("linear algebra, calculus") saved as osiris_organism_*.py. Now each
message gets one fixed class from word cues, and each class has a fixed,
code-defined action list. No model chooses the class or the actions; a
model only ever answers, plans or drafts inside an action the operator
picked (or, for read-only answers, one this module marks auto_answer).

  conversation  greetings, thanks, chit-chat          -> answered at once (read-only)
  question      why/what/how/?, "explain", "show me"  -> answered at once (read-only)
  status        "status", "what are you doing"        -> answered at once (read-only)
  benchmark     evaluate/benchmark/compare models     -> bench or mentor evidence
  research      quantum/experiment/hypothesis/...     -> experiment brief, design, arXiv
  engineering   build/add/fix/make/implement/...      -> gap draft, plan, or engines
  session_log   a pasted terminal session             -> read-only digest of what happened
                (paste_digest.looks_like_session: prompts, Termux banner, panels)

A single token of 1-3 characters that is no greeting ("l3", "abc", "??")
returns UNCLEAR, which is not a class: it gets "did you mean", no answer.

Ties: research > engineering > benchmark > status > question > conversation.
"build an experiment" is research; "can you add X to the bench?" is a build
request (engineering), not a benchmark run; a question ABOUT a research or
benchmark topic ("what is dynamical decoupling?") stays a question. Text
with no cues is answered (a short line is conversation).
"""
import re

import paste_digest

CLASSES = ("conversation", "question", "status", "benchmark", "research", "engineering", "session_log")
UNCLEAR = "unclear"  # returned by classify(), deliberately not a class: nothing is answered or offered

_CUES = {
    "benchmark": r"\b(bench(mark)?s?|evaluate|evaluation|score|scorecard|mentors?|which model|compare (the )?models?|"
                 r"qwen|deepseek|llama|gemini)\b",
    "research": r"\b(quantum|qubits?|circuits?|experiments?|hypothes[ie]s|simulat(or|ion|e)|noise|mitigation|"
                r"decoherence|fidelity|entangle\w*|hamiltonian|vqe|qaoa|aer|qiskit|dynamical decoupling|"
                r"research|arxiv|paper)\b",
    "engineering": r"\b(build|add|fix|make|implement|create|write|refactor|change|improve|enhance|support|"
                   r"modify|patch|update|remove|rename)\b",
    "status": r"\b(status|what are you doing|what('s| is) (osiris )?doing|what('s| is) (pending|running|next)|"
              r"where are we|progress|state of)\b",
    "question": r"(\?\s*$|^\s*(why|what|how|when|where|which|who|is|are|does|do|did|can|could|should|explain|"
                r"tell me|show me|describe)\b)",
    "conversation": r"^\s*(hi|hello|hey|yo|thanks|thank you|good (morning|afternoon|evening|night)|gm|ok|okay|"
                    r"cool|nice|great)\b",
}
_ORDER = ("research", "engineering", "benchmark", "status", "question", "conversation")

# Fixed actions per class: (label, command). Commands are REPL commands owned
# by code; {text} is the operator's own words (never model output).
ACTIONS = {
    "conversation": [("Ask a follow-up (just type it)", None), ("Full status", "/status"),
                     ("Capture a capability gap", "/gap"), ("Draft an experiment brief", "/experiment")],
    "question": [("Full status (every fact)", "/status"), ("Mentor evidence", "/mentors"),
                 ("Capture it as a capability gap", "/gap {text}")],
    "status": [("Full status (every fact)", "/status"), ("Check everything", "/check"),
               ("Mentor evidence", "/mentors")],
    "benchmark": [("Benchmark qwen2.5-coder:7b on 3 tasks (local)", "/bench"),
                  ("Mentor evidence so far", "/mentors"), ("Ask OSIRIS about it", "/ask {text}")],
    "research": [("Draft an experiment brief (guided, simulator first)", "/experiment {text}"),
                 ("Ask the Architect for an experiment design (text only)", "/plan {text}"),
                 ("Fetch recent arXiv abstracts on it", "/research {text}")],
    "engineering": [("Capture it as a capability gap (guided draft)", "/gap {text}"),
                    ("Ask the Architect for a plan (text only, no files)", "/plan {text}"),
                    ("Send to the engines (proposes a file you /apply)", "/engage")],
    "session_log": [("What happened, again: commands, results, problems", "/digest"),
                    ("Full status now, to compare with the log", "/status"),
                    ("Capture a capability gap (guided draft)", "/gap")],
}
AUTO_ANSWER = {"conversation", "question", "status"}

# Questions about OSIRIS ITSELF are answered by code from verified state, never
# by a model: on 2026-09-24 both llama3.2:1b and qwen2.5-coder:7b, given the
# facts, still asserted things they did not say ("has been benchmarked", "the
# best model is deepseek-coder"). Models answer only knowledge questions.
_ABOUT_OSIRIS = re.compile(
    r"\b(osiris|you|your|yourself|gaps?|stor(y|ies)|sprints?|backlog|bench(mark)?s?|mentors?|scorecard|pending|"
    r"apply|ledger|runs?|status|next|genome|generation|briefs?|which model|best model|models? (is|are) best|"
    r"what can (you|i) do|help)\b", re.IGNORECASE)


# OSIRIS's own terms: their meaning here, and the data behind them, come from OSIRIS.
_OSIRIS_TERMS = re.compile(r"\b(false confidence|hidden tests?|own tests?|integrity exclusions?)\b", re.IGNORECASE)
# "why did it fail?" -- a pronoun plus an outcome verb asks about something that just happened here.
_PRONOUN = re.compile(r"\b(it|that|this|they|them)\b", re.IGNORECASE)
_OUTCOME = re.compile(r"\b(fail\w*|stop\w*|pass\w*|break\w*|broke|happen\w*|go wrong|went wrong|score\w*)\b",
                      re.IGNORECASE)


def about_osiris(text):
    """True when the message asks about OSIRIS's own state, work, models or
    terms -- including "why did it fail?" right after a round."""
    return bool(_ABOUT_OSIRIS.search(text) or _OSIRIS_TERMS.search(text)
                or (_PRONOUN.search(text) and _OUTCOME.search(text)))


def classify(text):
    """(class, {class: [matched cues]}). Deterministic; no model.

    A long pasted block (more than 5 lines) is classified by its FIRST line --
    the operator's framing -- not by every word in it: on 2026-09-24 a pasted
    462-line design note on ledger reconciliation routed as research because
    its body mentioned "dynamical decoupling" and "experiment" in passing. A
    research, benchmark or build first line keeps that class; anything else
    (a question, a title) makes the block material to work on: engineering."""
    if paste_digest.looks_like_session(text):
        # A pasted terminal session is a record of what happened, not a request:
        # on-device a paste opening "Welcome to Termux" became an engineering
        # goal of that name (2026-09-24).
        return "session_log", {"session_log": ["pasted terminal session"]}
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) > 5:
        head, head_hits = classify(lines[0])
        if head in ("research", "benchmark", "engineering"):
            return head, {head: head_hits.get(head, []) + ["first line of a pasted block"]}
        return "engineering", {"engineering": [f"pasted block of {len(lines)} lines"]}
    flat = " ".join(text.split()).lower()
    hits = {}
    for cls, pattern in _CUES.items():
        found = [m.group(0).strip() for m in re.finditer(pattern, flat)]
        if found:
            hits[cls] = sorted(set(found))[:4]
    if re.fullmatch(r"\S{1,3}", flat) and "conversation" not in hits:
        # "l3" got a full status answer on-device: a stray fragment is no request.
        return UNCLEAR, {UNCLEAR: [f"'{flat}' is no command, menu key or sentence"]}
    if "\n" in text.strip() and len(text.strip().splitlines()) > 3:
        # A pasted block (log, traceback, notes) is material to work on, not a chat line.
        hits.setdefault("engineering", ["pasted block"])
    if "conversation" in hits and len(flat.split()) <= 5 and not ({"engineering", "research", "benchmark"} & set(hits)):
        return "conversation", hits  # "hey osiris, you there?" is a greeting, not a question
    for cls in _ORDER:
        if cls in hits:
            # A question ABOUT a topic stays a question unless it asks for work.
            if cls in ("benchmark", "research") and "question" in hits and "engineering" not in hits \
                    and not re.search(r"\b(run|start|do|design|draft|plan|compare)\b", flat) \
                    and not re.search(r"\b(benchmark|evaluate|score|test) (them|it|all|the models?|"
                                      r"qwen|deepseek|llama|gemini)\b", flat):
                return "question", hits
            return cls, hits
    return "conversation" if len(flat.split()) <= 3 else "question", hits


def actions_for(cls, text):
    """The fixed actions for a class, with the operator's words filled in."""
    words = " ".join(text.split())[:240]
    return [(label, cmd.replace("{text}", words) if cmd else None) for label, cmd in ACTIONS[cls]]
