"""
gaps.py -- structured capability-gap drafts.

Story #25 came from the one-line gap "stale-home-test": /ignite made it a
structural story, the sandbox passed an unrelated timestamp utility, and it
was applied. A gap now starts as a DRAFT with fields a reviewer (and the
Synthesizer) can check:

  outcome      what must become true -- a sentence, not an identifier
  area         one of AREAS
  acceptance   how OSIRIS will check it (at least one criterion)
  scope        target paths; activation needs at least one .py file
               (unknown scope can be saved as a draft, never activated)
  constraints  what it must not change (optional)

Drafts live in ~/.osiris/gap_drafts.json and are inert: nothing reads them
except /gaps. Only activate() -- an explicit operator step in the REPL --
turns a VALID draft into a trusted dormant trait, through the same
genome.record_gap() checks as before (no provenance tags, no duplicates,
one line, length limit). The trait text carries the target module first,
so /ignite's story targets it, and the acceptance criteria, so the
Synthesizer's prompt contains them.
"""
import json
import os
import re
import time

STORE = os.path.join(os.path.expanduser("~"), ".osiris", "gap_drafts.json")
AREAS = ("REPL routing and menus", "Console UI", "Benchmark and mentors", "DNA-Lang",
         "Sandbox and verification", "Ledger and evidence", "Research workflow", "Other")
# Text no field may carry: authority lives in typed commands, not in a gap.
FORBIDDEN_RE = re.compile(r"--allow-self-modify|\[\s*PROVENANCE\s*:|(^|\s)/apply\b", re.IGNORECASE)
PATH_RE = re.compile(r"[A-Za-z0-9_.\-]+(/[A-Za-z0-9_.\-]+)*")
MAX_TRAIT_CHARS = 300  # genome.MAX_GAP_CHARS


def _load():
    try:
        with open(STORE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("drafts"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"next_id": 1, "drafts": []}


def _save(data):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, STORE)


def new_draft(outcome="", area=None, acceptance=(), scope=(), constraints=()):
    return {"outcome": " ".join(outcome.split()), "area": area,
            "acceptance": [" ".join(a.split()) for a in acceptance if a.strip()],
            "scope": [s.strip() for s in scope if s.strip()],
            "constraints": [" ".join(c.split()) for c in constraints if c.strip()]}


def target_module(d):
    """The first .py file in scope, as /ignite's target resolver will read it."""
    for s in d["scope"]:
        if s.endswith(".py"):
            return os.path.basename(s)
    return None


def trait_text(d):
    """One line for genome.record_gap(): target first (ignite targets the first
    .py it sees), then the outcome, then the acceptance criteria."""
    target = target_module(d)
    head = f"{target}: " if target else ""
    return f"{head}{d['outcome'].rstrip('.')} | accept: {'; '.join(a.rstrip('.') for a in d['acceptance'])}"


def problems(d):
    """Why a draft cannot be activated yet ([] = it can)."""
    out = []
    words = d["outcome"].split()
    if len(words) < 6 or re.fullmatch(r"[\w./\-]+", d["outcome"] or "x"):
        out.append("Outcome: say what must become true in a sentence (6+ words), not a name "
                   "like 'stale-home-test'.")
    if d["area"] not in AREAS:
        out.append("Area: pick one.")
    if not d["acceptance"]:
        out.append("Acceptance: add at least one way OSIRIS can check it.")
    elif any(len(a.split()) < 4 for a in d["acceptance"]):
        out.append("Acceptance: each criterion needs 4+ words (what is checked, and the expected result).")
    if not target_module(d):
        out.append("Scope: name at least one .py file to change. With no .py target, /ignite would hand the "
                   "Synthesizer a scratch file and free rein; bin/osiris itself is protected from sprints. "
                   "Keep it as a draft until the target is known.")
    for s in d["scope"]:
        if not PATH_RE.fullmatch(s) or s.startswith(("/", "~")) or ".." in s.split("/"):
            out.append(f"Scope: {s!r} is not a workspace-relative path.")
    fields = [d["outcome"], *d["acceptance"], *d["scope"], *d["constraints"]]
    if any(FORBIDDEN_RE.search(f) for f in fields):
        out.append("No field may carry --allow-self-modify, /apply or a provenance tag.")
    if any("\n" in f for f in fields):
        out.append("Each field is one line.")
    n = len(trait_text(d))
    if n > MAX_TRAIT_CHARS:
        out.append(f"Too long for a gap: {n}/{MAX_TRAIT_CHARS} characters -- shorten the outcome or criteria.")
    return out


def save(d):
    data = _load()
    d = dict(d, id=data["next_id"], status="draft", created=time.strftime("%Y-%m-%dT%H:%M:%S"))
    data["drafts"].append(d)
    data["next_id"] += 1
    _save(data)
    return d


def drafts():
    return _load()["drafts"]


def get(draft_id):
    return next((d for d in drafts() if d["id"] == draft_id), None)


def delete(draft_id):
    data = _load()
    before = len(data["drafts"])
    data["drafts"] = [d for d in data["drafts"] if not (d["id"] == draft_id and d["status"] == "draft")]
    _save(data)
    return len(data["drafts"]) < before


def activate(draft_id, record_gap):
    """The operator's explicit step: a valid draft becomes a trusted dormant
    trait via record_gap (genome.record_gap). Returns (ok, message)."""
    data = _load()
    d = next((x for x in data["drafts"] if x["id"] == draft_id), None)
    if d is None:
        return False, f"no gap draft #{draft_id}"
    if d["status"] != "draft":
        return False, f"gap #{draft_id} is already {d['status']}"
    probs = problems(d)
    if probs:
        return False, "not ready: " + " ".join(probs)
    ok, message = record_gap(trait_text(d))
    if not ok:
        return False, message
    d.update(status="active", trait=message, activated=time.strftime("%Y-%m-%dT%H:%M:%S"))
    _save(data)
    return True, message
