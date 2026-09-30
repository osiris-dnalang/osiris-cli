#!/usr/bin/env python3
"""
sprint_manager.py -- structured Agile backlog for OSIRIS's on-demand sprint
loop (/sprint plan, /sprint execute, /sprint review).

Backlog lives at ~/.osiris/sprint_backlog.json -- a single JSON object with
a story list, NOT the same thing as the timestamped sprint_backlog_<ts>.json
files the older hallucination-era organism-synthesis path already writes;
those are a separate, unrelated legacy mechanism from earlier in this
project and this module never touches them.

Story parsing is real parsing of real model output, not a placeholder: the
model (Gemini via vision_indexer, or Engine 1 elsewhere) is asked to emit
lines in the format "STORY: <text> | COMPLEXITY: <1-3>", and
parse_digest_to_stories() extracts exactly that with a regex -- same
convention this REPL already uses for /suggest's "SUGGESTION N: <text>"
format, not a new fragile prose-parsing scheme.
"""
import json
import os
import re
import time

SPRINT_BACKLOG_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "sprint_backlog.json")
# Sources whose stories may become sprint work (/sprint plan, /sprint execute):
#   ignite  -- from a structured gap the operator activated (gaps.py checks);
#   manual  -- written into the backlog by the operator outside OSIRIS
#              (no OSIRIS code path creates it).
# "vision" (a model's screenshot digest) and "suggest" (model output) are
# untrusted reference material: they stay visible but never become work.
PLANNABLE_SOURCES = {"ignite", "manual"}
STORY_RE = re.compile(r"STORY:\s*(.+?)\s*\|\s*COMPLEXITY:\s*([123])\b", re.IGNORECASE)


def _load_backlog():
    if not os.path.exists(SPRINT_BACKLOG_PATH):
        return {"stories": [], "next_id": 1}
    try:
        with open(SPRINT_BACKLOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("stories", [])
            data.setdefault("next_id", 1)
            return data
    except Exception:
        return {"stories": [], "next_id": 1}


def _save_backlog(backlog):
    os.makedirs(os.path.dirname(SPRINT_BACKLOG_PATH), exist_ok=True)
    tmp = SPRINT_BACKLOG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(backlog, f, indent=2)
    os.replace(tmp, SPRINT_BACKLOG_PATH)


def add_story(text, complexity, source):
    backlog = _load_backlog()
    story = {
        "id": backlog["next_id"],
        "text": text.strip(),
        "complexity": int(complexity),
        "status": "backlog",  # backlog -> active -> proposed -> done | failed
        "source": source,     # "vision" | "suggest" | "manual" | "ignite"
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    backlog["stories"].append(story)
    backlog["next_id"] += 1
    _save_backlog(backlog)
    return story


def plannable(story):
    """Whether a story may become sprint work: its source, not its status."""
    return story.get("source") in PLANNABLE_SOURCES


def parse_digest(digest_text):
    """[(text, complexity)] from a model digest's STORY:/COMPLEXITY: lines.
    Saves nothing: a digest is untrusted reference, not backlog."""
    return [(m.group(1).strip(), int(m.group(2))) for m in STORY_RE.finditer(digest_text or "")]


def parse_digest_to_stories(digest_text, source):
    """Extracts every real STORY:/COMPLEXITY: line from digest_text and adds
    each as a backlog entry. Returns the list of newly added story dicts (in
    the order they appeared) -- empty if the model didn't emit the expected
    format, which is reported honestly by the caller, not hidden."""
    added = []
    for match in STORY_RE.finditer(digest_text or ""):
        text, complexity = match.group(1), match.group(2)
        added.append(add_story(text, complexity, source))
    return added


def get_backlog():
    return _load_backlog()


def set_status(story_id, status):
    backlog = _load_backlog()
    for s in backlog["stories"]:
        if s["id"] == story_id:
            s["status"] = status
    _save_backlog(backlog)


def top_priority(n=3, status="backlog", plannable_only=False):
    """Deterministic priority: lowest complexity first (fastest real wins),
    then insertion order. No model call needed for this -- a heuristic over
    a number already on each story is more reliable than asking a small
    local model to re-derive the same ranking, consistent with this
    project's established preference for deterministic logic where it's a
    real option (e.g. the algorithmic DD-sequence generator over neural
    generation)."""
    backlog = _load_backlog()
    candidates = [s for s in backlog["stories"] if s["status"] == status and (plannable(s) or not plannable_only)]
    candidates.sort(key=lambda s: (s["complexity"], s["id"]))
    return candidates[:n]


def summary():
    backlog = _load_backlog()
    counts = {}
    for s in backlog["stories"]:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return counts, backlog["stories"]
