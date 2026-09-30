"""
session_state.py -- what OSIRIS remembers about the operator's session,
all of it display or feedback, none of it authority:

  focus        what the operator is working on (~/.osiris/focus.json). Set by
               saving a gap or brief, asking for a plan, or /focus. Shown on
               /home; never runs anything.
  corrections  operator re-routes of a message (~/.osiris/intent_feedback.jsonl),
               appended as feedback for evaluating the intent router. Never
               applied to routing automatically.
  digest       counts of real state saved at startup (~/.osiris/last_session.json)
               so the next startup can say what changed since.
"""
import json
import os
import time

OSIRIS_DIR = os.path.join(os.path.expanduser("~"), ".osiris")
FOCUS = os.path.join(OSIRIS_DIR, "focus.json")
FEEDBACK = os.path.join(OSIRIS_DIR, "intent_feedback.jsonl")
LAST = os.path.join(OSIRIS_DIR, "last_session.json")


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


FOCUS_MAX_WORDS = 25


def focus_ok(goal) -> bool:
    """A focus is a short goal on one line: on-device (2026-09-24) a pasted
    Perplexity answer became the focus ("How does the Architect role use
    llama3 2 1b in OSIRIS The Architect uses the local ...")."""
    goal = str(goal or "").strip()
    return bool(goal) and "\n" not in goal and len(goal.split()) <= FOCUS_MAX_WORDS


def get_focus():
    f = _read_json(FOCUS)
    # A stored focus that fails the gate (set before it existed) is not shown.
    return f if isinstance(f, dict) and focus_ok(f.get("goal")) else None


def set_focus(goal, kind, source):
    """Returns the new focus, or None -- leaving the old one -- when goal is
    not a short one-line goal (focus_ok)."""
    if not focus_ok(goal):
        return None
    goal = " ".join(str(goal).split())[:160]
    f = {"goal": goal, "kind": kind, "source": source, "since": time.strftime("%Y-%m-%d %H:%M")}
    _write_json(FOCUS, f)
    return f


def clear_focus():
    try:
        os.remove(FOCUS)
        return True
    except OSError:
        return False


def record_correction(text, original, corrected):
    """Appends one operator re-route. Feedback only: nothing reads it to route."""
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": " ".join(text.split())[:300],
             "original": original, "corrected": corrected, "source": "operator"}
    os.makedirs(OSIRIS_DIR, exist_ok=True)
    with open(FEEDBACK, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def corrections():
    out = []
    try:
        with open(FEEDBACK, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


LABELS = {"generation": "genome generation", "active_stories": "active sprint stories",
          "backlog_stories": "backlog stories", "gap_drafts": "gap drafts", "active_gaps": "active gaps",
          "briefs": "experiment briefs", "bench_candidates": "scored mentor candidates",
          "bench_runs": "mentor benchmark runs", "corrections": "routing corrections", "focus": "focus"}


def digest(current):
    """Changes since the last saved snapshot, as sentences; saves `current`.
    Returns None on the very first session (nothing to compare)."""
    previous = _read_json(LAST)
    _write_json(LAST, dict(current, saved=time.strftime("%Y-%m-%d %H:%M")))
    if not isinstance(previous, dict):
        return None
    changes = []
    for key, label in LABELS.items():
        old, new = previous.get(key), current.get(key)
        if old == new or new is None:
            continue
        if isinstance(new, int) and isinstance(old, int):
            changes.append(f"{label}: {old} -> {new}")
        else:
            changes.append(f"{label}: {new}" if new else f"{label} cleared")
    return {"since": previous.get("saved", "?"), "changes": changes}
