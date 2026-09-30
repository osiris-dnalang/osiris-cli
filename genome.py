#!/usr/bin/env python3
"""
genome.py -- OSIRIS's machine-readable self-description (~/.osiris/genome.json).

Tracks what the organism actually is right now (active_traits, a real
generation counter) and what it knows it still needs (dormant_traits,
recorded only by the operator's explicit /gap command -- never invented,
never harvested from free text). /ignite (in bin/osiris) reads this
to pick structural targets for the sprint backlog, using the SAME
sprint_manager/sandbox/`/apply` pipeline every other story already goes
through -- this module only tracks state, it never writes source files or
bypasses a gate itself.

A generation bump happens ONLY in _apply_pending_write() (bin/osiris),
once a structural story's code has genuinely landed on disk -- not merely
passed the sandbox test -- so genome.json can never claim an evolutionary
leap that hasn't actually shipped.

Provenance on dormant_traits: each entry is {"text": ..., "source": ...}.
Only source == CAPABILITY_GAP_SOURCE is eligible for /ignite promotion
(pick_ignite_targets). This closes a real incident (2026-09-23): something
wrote fabricated trait names directly into genome.json, bypassing this
module's API entirely, and /ignite promoted one into an active sprint
story with no way to tell it apart from a genuinely-scanned one.

Trusted source (changed 2026-09-23): traits used to be harvested from ANY
logged prompt containing the phrase "capability gap" -- pasted AI text and
Gemini vision digests included, which is how an unsourced "0.9728 parity"
figure and a typed "[PROVENANCE: VERIFIED_LOGIC]" tag became a trusted
trait. Now the only trusted source is record_gap(), called by the REPL's
one-line /gap command; the phrase anywhere else is ignored. Entries from the
old scanner (source "capability_gap_scan") stay visible but inert. A bare
string from an older genome.json is migrated to source=None (untrusted,
inert, but visible) on load, not silently trusted.
"""
import json
import os
import re
import time
import uuid

GENOME_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "genome.json")
PROMPT_LIBRARY_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "prompt_library.json")

DEFAULT_MUTATION_RATE = 0.34  # fraction of dormant_traits one /ignite call promotes
MAX_IGNITE_TARGETS = 3        # hard cap so one call can't dump the whole dormant list in at once
FRAMEWORK = "dna::}AI{::lang"  # identity tag for the REPL's own genome, not dnalang-core's grammar

CAPABILITY_GAP_SOURCE = "operator_gap_command"  # the only source pick_ignite_targets() trusts
MAX_GAP_CHARS = 300



def _normalize_dormant_traits(genome):
    """Migrates any legacy bare-string dormant_traits entries to
    {"text": ..., "source": None} -- untrusted (never eligible for
    promotion) but preserved and visible, not silently dropped or
    silently trusted. Returns True if the in-memory dict changed (caller
    should _save())."""
    changed = False
    normalized = []
    for entry in genome.get("dormant_traits", []):
        if isinstance(entry, str):
            normalized.append({"text": entry, "source": None})
            changed = True
        else:
            normalized.append(entry)
    genome["dormant_traits"] = normalized
    return changed


def _load():
    if not os.path.exists(GENOME_PATH):
        return None
    try:
        with open(GENOME_PATH, encoding="utf-8") as f:
            genome = json.load(f)
    except Exception:
        return None
    if _normalize_dormant_traits(genome):
        _save(genome)
    return genome


def _save(genome):
    os.makedirs(os.path.dirname(GENOME_PATH), exist_ok=True)
    tmp = GENOME_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(genome, f, indent=2)
    os.replace(tmp, GENOME_PATH)


def init_if_missing(active_traits, mutation_rate=DEFAULT_MUTATION_RATE):
    """Creates genome.json on first call only -- never overwrites an
    existing one, so calling this again after real generations have
    shipped can't silently reset the organism's own history."""
    genome = _load()
    if genome is not None:
        return genome
    genome = {
        "organism_id": str(uuid.uuid4()),
        "framework": FRAMEWORK,
        "generation": 1,
        "active_traits": sorted(set(active_traits)),
        "dormant_traits": [],
        "mutation_rate": mutation_rate,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_metamorphosis_at": None,
    }
    _save(genome)
    return genome


def get():
    genome = _load()
    if genome is None:
        raise FileNotFoundError(f"{GENOME_PATH} does not exist -- run /ignite once to initialize it.")
    return genome


def _recorded_gaps():
    """Gaps already recorded by /gap but not necessarily scanned into the genome yet."""
    gaps = set()
    if os.path.exists(PROMPT_LIBRARY_PATH):
        with open(PROMPT_LIBRARY_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("source") == CAPABILITY_GAP_SOURCE and not entry.get("redacted"):
                    gaps.add(entry.get("gap"))
    return gaps


def record_gap(text):
    """Records one operator-stated capability gap in prompt_library.json with
    source=CAPABILITY_GAP_SOURCE. Returns (ok, message). Refuses empty or
    multi-line text, anything over MAX_GAP_CHARS, typed provenance tags (the
    0.9728 incident carried "[PROVENANCE: VERIFIED_LOGIC]" as plain text), and
    gaps already dormant or active."""
    gap = (text or "").strip().rstrip(".").strip()
    if not gap:
        return False, "empty gap -- usage: /gap <capability OSIRIS is missing>"
    if "\n" in gap:
        return False, "a gap is one line"
    if len(gap) > MAX_GAP_CHARS:
        return False, f"gap is {len(gap)} characters; keep it under {MAX_GAP_CHARS}"
    if re.search(r"\[\s*PROVENANCE\s*:", gap, re.IGNORECASE):
        return False, "provenance tags are assigned by OSIRIS, not typed into a gap"
    genome = get()
    if gap in genome["active_traits"] or any(e["text"] == gap for e in genome["dormant_traits"]) \
            or gap in _recorded_gaps():
        return False, "that gap is already recorded"
    os.makedirs(os.path.dirname(PROMPT_LIBRARY_PATH), exist_ok=True)
    with open(PROMPT_LIBRARY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "prompt": f"/gap {gap}",
                            "gap": gap, "source": CAPABILITY_GAP_SOURCE}) + "\n")
    return True, gap


def refresh_dormant_traits():
    """Adds a dormant trait for every record_gap() entry in prompt_library.json
    not already dormant or active. Only entries with source ==
    CAPABILITY_GAP_SOURCE and a "gap" field count; the words "capability gap"
    in any other logged text (pasted transcripts, vision digests, model output)
    are ignored. Returns the newly added trait texts."""
    genome = get()
    known = {e["text"] for e in genome["dormant_traits"]} | set(genome["active_traits"])
    found = []
    if os.path.exists(PROMPT_LIBRARY_PATH):
        with open(PROMPT_LIBRARY_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("redacted") or entry.get("source") != CAPABILITY_GAP_SOURCE:
                    continue
                gap = entry.get("gap")
                if not isinstance(gap, str) or not gap or gap in known:
                    continue
                genome["dormant_traits"].append({"text": gap, "source": CAPABILITY_GAP_SOURCE})
                known.add(gap)
                found.append(gap)
    if found:
        _save(genome)
    return found


def pick_ignite_targets(exclude=()):
    """How many dormant traits one /ignite call promotes: mutation_rate
    scales aggressiveness, bounded to [1, MAX_IGNITE_TARGETS] (when any
    exist) so a single call can never flood the backlog. Only entries with
    source == CAPABILITY_GAP_SOURCE are eligible -- an untrusted/legacy
    entry sits inert in dormant_traits until refresh_dormant_traits()
    independently reconfirms it. Traits in `exclude` (already queued or
    done in the backlog) are skipped so repeat calls can't duplicate them."""
    genome = get()
    trusted = [e["text"] for e in genome["dormant_traits"]
               if e.get("source") == CAPABILITY_GAP_SOURCE and e["text"] not in exclude]
    if not trusted:
        return []
    n = max(1, round(genome["mutation_rate"] * len(trusted)))
    n = min(n, MAX_IGNITE_TARGETS, len(trusted))
    return trusted[:n]


def untrusted_dormant_count():
    """How many dormant_traits entries exist but aren't eligible for
    promotion -- surfaced by /ignite so contamination like the 2026-09-23
    incident is visible immediately instead of silently sitting there."""
    genome = get()
    return sum(1 for e in genome["dormant_traits"] if e.get("source") != CAPABILITY_GAP_SOURCE)


def complete_metamorphosis(trait_text):
    """Called only from _apply_pending_write() after a structural story's
    code has actually landed on disk. Moves the trait dormant -> active and
    returns the new generation int."""
    genome = get()
    genome["dormant_traits"] = [e for e in genome["dormant_traits"] if e.get("text") != trait_text]
    if trait_text not in genome["active_traits"]:
        genome["active_traits"].append(trait_text)
    genome["generation"] += 1
    genome["last_metamorphosis_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _save(genome)
    return genome["generation"]


def summary():
    return get()
