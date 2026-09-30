#!/usr/bin/env python3
"""
run_record.py -- one immutable record per story /sprint execute works on.

Before this, a /sprint execute left behind only the winning candidate (in
memory, until /apply or discard) and a sandbox log per attempt: which
candidates were tried, what each was verified against and why the losers
lost could not be reconstructed. /candidates, /diff, an /apply bound to one
exact candidate and /replay all need that.

Layout, under ~/.osiris/runs/<run_id>/ (every file created with O_EXCL and
fsynced -- a run directory is written once and never modified):
  prompt.txt              the exact prompt for attempt 1 (later attempts add
                          verify_loop.feedback_block(previous reason))
  base.txt                the target's text when the run was recorded, if it
                          existed (runs recorded before 2026-09-24 lack it)
  cand-<n>.module.py      candidate n's module, as returned
  cand-<n>.test.py        candidate n's own test
  run.json                the record: story, target base hash, k, one row
                          per attempt (backend, stage, verdict, reason,
                          artifact hashes), outcome

run.json's SHA-256 over canonical JSON (sorted keys, compact, UTF-8 -- not
RFC 8785) is what osiris appends to the genome ledger as a "sprint_run"
entry, so the ledger vouches for the record and the record for each artifact
(verify() re-checks both hops that are local). A run whose ledger append
failed keeps its directory, with no ledger entry: an orphan, never a record
the ledger claims but that does not exist.
"""
import difflib
import hashlib
from collections import Counter
import json
import os
import secrets
import time

SCHEMA = "osiris-run/1"
RUNS_DIR = os.path.join(os.path.expanduser("~"), ".osiris", "runs")
RECORD_NAME = "run.json"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def new_run_id() -> str:
    return f"run-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(3)}"


def _write_once(path: str, data: bytes):
    """Creates path (fails if it exists), writes, fsyncs."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


class RunWriter:
    def __init__(self, run_id: str = None, runs_dir: str = None):
        self.run_id = run_id or new_run_id()
        self.dir = os.path.join(runs_dir or RUNS_DIR, self.run_id)
        os.makedirs(os.path.dirname(self.dir), exist_ok=True)
        os.mkdir(self.dir)  # FileExistsError on a reused id: records are never extended

    def artifact(self, name: str, text: str) -> str:
        """Writes one artifact file and returns its SHA-256."""
        if os.sep in name or name in (RECORD_NAME, "", ".", ".."):
            raise ValueError(f"bad artifact name {name!r}")
        _write_once(os.path.join(self.dir, name), text.encode("utf-8"))
        return sha256_text(text)

    def finish(self, record: dict) -> str:
        """Writes run.json and returns its canonical SHA-256. Call once."""
        record = {"schema": SCHEMA, "run_id": self.run_id, **record}
        data = canonical(record)
        _write_once(os.path.join(self.dir, RECORD_NAME), data)
        return hashlib.sha256(data).hexdigest()


def load(run_id: str, runs_dir: str = None) -> dict:
    with open(os.path.join(runs_dir or RUNS_DIR, run_id, RECORD_NAME), encoding="utf-8") as f:
        return json.load(f)


def orphans(ledger_entries, runs_dir: str = None) -> list:
    """Run ids on disk with no "sprint_run" ledger entry naming them -- a
    record or ledger append that failed part-way. Never valid input for
    /apply or /replay; kept, not deleted, as evidence of what was tried."""
    d = runs_dir or RUNS_DIR
    try:
        on_disk = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    except FileNotFoundError:
        return []
    known = {(e.get("payload") or {}).get("run_id") for e in ledger_entries if e.get("kind") == "sprint_run"}
    return [r for r in on_disk if r not in known]


def verify(run_id: str, record_sha256: str = None, runs_dir: str = None):
    """None if run.json matches record_sha256 (when given, e.g. from the
    ledger) and every artifact it names matches its recorded hash; else a
    description of the first mismatch."""
    d = os.path.join(runs_dir or RUNS_DIR, run_id)
    try:
        with open(os.path.join(d, RECORD_NAME), "rb") as f:
            raw = f.read()
        record = json.loads(raw)
    except (OSError, ValueError) as e:
        return f"{run_id}: unreadable record: {type(e).__name__}: {e}"
    if raw != canonical(record):
        return f"{run_id}: run.json is not in canonical form"
    if record_sha256 and hashlib.sha256(raw).hexdigest() != record_sha256:
        return f"{run_id}: run.json does not match the ledger's hash"
    expected = {"prompt.txt": record["prompt_sha256"]} if record.get("prompt_sha256") else {}
    if record.get("base_text_sha256"):
        expected["base.txt"] = record["base_text_sha256"]
    for a in record.get("attempts", []):
        for kind in ("module", "test"):
            if a.get(f"{kind}_sha256"):
                expected[f"cand-{a['n']}.{kind}.py"] = a[f"{kind}_sha256"]
    for name, sha in expected.items():
        try:
            with open(os.path.join(d, name), "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return f"{run_id}: {name} missing"
        if actual != sha:
            return f"{run_id}: {name} does not match its recorded hash"
    return None


def resolve(ref: str = None, runs_dir: str = None) -> str:
    """The run id for ref: the newest run when ref is empty, else the exact id
    or the one id containing ref (e.g. its last 6 characters). LookupError
    otherwise."""
    d = runs_dir or RUNS_DIR
    try:
        ids = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    except FileNotFoundError:
        ids = []
    if not ids:
        raise LookupError("no runs recorded yet -- /sprint execute records one per story")
    if not ref:
        return ids[-1]
    if ref in ids:
        return ref
    matches = [i for i in ids if ref in i]
    if len(matches) == 1:
        return matches[0]
    raise LookupError(f"no run matches {ref!r}" if not matches else
                      f"{ref!r} matches {len(matches)} runs: {', '.join(matches[-3:])}")


def _read(d, name):
    try:
        with open(os.path.join(d, name), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _delta(old: str, new: str):
    added = removed = 0
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0):
        if line.startswith(("+++", "---", "@@")):
            continue
        added += line.startswith("+")
        removed += line.startswith("-")
    return added, removed


def show(run_id: str, ledger_entries, candidate: int = None, root: str = None, runs_dir: str = None) -> str:
    """A phone-width, read-only summary of one run, built only from its files
    and the ledger: whether the ledger vouches for it and it verifies, the
    story, target, outcome, whether it was applied, and one line per
    candidate (backend/model, stage reached, verdict, +/- lines, reason).
    With candidate=n, that candidate's module and test in full. root is the
    directory the target path is relative to (osiris's cwd)."""
    d = os.path.join(runs_dir or RUNS_DIR, run_id)
    try:
        record = load(run_id, runs_dir)
    except (OSError, ValueError) as e:
        return f"[!] {run_id}: unreadable run record ({type(e).__name__}: {e})"
    payloads = [(e.get("kind"), e.get("payload") or {}) for e in ledger_entries]
    vouch = next((p for k, p in payloads if k == "sprint_run" and p.get("run_id") == run_id), None)
    applied = next((p for k, p in payloads if k == "file_change" and p.get("run_id") == run_id), None)
    if vouch is None:
        trust = "NOT in the ledger (unattested) -- evidence only"
    else:
        problem = verify(run_id, vouch.get("record_sha256"), runs_dir)
        trust = "verified in ledger" if problem is None else f"VERIFICATION FAILED: {problem}"

    target = record.get("target") or {}
    base = _read(d, "base.txt") if record.get("base_text_sha256") else None
    if base is None and target.get("base_sha256") is None:
        base = ""  # a new file: every line is added
    if base is None and target.get("path"):
        path = os.path.join(root or os.getcwd(), target["path"])
        try:
            with open(path, "rb") as f:
                raw = f.read()
            if hashlib.sha256(raw).hexdigest() == target["base_sha256"]:
                base = raw.decode("utf-8", errors="replace")
        except OSError:
            pass
    story = record.get("story") or {}
    attempts = record.get("attempts") or []
    lines = ["─" * 50, f" 🔎 {run_id}", f"    {trust}", "─" * 50,
             f"  Story    #{story.get('id')} {str(story.get('text', ''))[:60]}",
             f"  Target   {target.get('path')} ({'new file' if target.get('base_sha256') is None else 'modify'})",
             f"  Ran      {record.get('command')} · k={record.get('k')} · {record.get('started_at')}",
             f"  Code     {(record.get('code') or {}).get('commit')}"
             f"{' (uncommitted changes)' if (record.get('code') or {}).get('dirty') else ''}",
             f"  Outcome  {record.get('outcome')}"
             + (f" · candidate {record['proposed_candidate']}" if record.get("proposed_candidate") else ""),
             f"  Applied  " + (f"yes -- file sha256 {applied.get('sha256_after', '')[:12]}" if applied else "no")]
    if base is None and target.get("base_sha256"):
        lines.append("  (base text not stored and the target has changed: line counts unavailable)")
    for a in attempts:
        module = _read(d, f"cand-{a['n']}.module.py") if a.get("module_sha256") else None
        delta = "" if module is None or base is None else "+%d/-%d" % _delta(base, module)
        who = "/".join(x for x in (a.get("backend"), a.get("model_requested")) if x) or "?"
        verdict = "PASS" if a.get("ok") else "FAIL"
        lines.append(f"  [{a['n']}] {verdict:<4} {a.get('stage', '?'):<8} {delta:<9} {who}")
        if not a.get("ok") and a.get("reason"):
            lines.append(f"       {a['reason'].strip().splitlines()[-1][:60]}")
    if candidate is None:
        lines.append(f"  /run show {run_id[-6:]} <n> shows candidate n's code and test.")
        return "\n".join(lines)

    a = next((x for x in attempts if x.get("n") == candidate), None)
    if a is None:
        return "\n".join(lines + [f"[!] no candidate {candidate} in this run"])
    module = _read(d, f"cand-{candidate}.module.py")
    test = _read(d, f"cand-{candidate}.test.py")
    if module is None:
        return "\n".join(lines + [f"[!] candidate {candidate} produced no code ({a.get('reason', '')[:80]})"])
    lines += [f"── candidate {candidate} module ({a.get('module_sha256', '')[:12]}) ──", module.rstrip(),
              f"── candidate {candidate} test ──", (test or "").rstrip()]
    if a.get("reason"):
        lines += ["── verifier said ──", a["reason"].strip()]
    return "\n".join(lines)


STAGE_MEANING = {"generate": "no usable proposal", "path": "wrong file path",
                 "api": "dropped existing functions", "sandbox": "failed its own test"}
RANK_MIN_RUNS = 10  # below this, stats() says the counts are too few to compare models


def stats(ledger_entries, runs_dir: str = None) -> str:
    """Counts over every run the ledger vouches for AND that still verifies
    -- others are only counted as skipped: outcomes, how many proposals were
    applied, which candidate passed, per backend/model passed/tried, and the
    stage failed candidates stopped at. Raw counts, no percentages or ranking
    below RANK_MIN_RUNS runs. Read-only."""
    payloads = [(e.get("kind"), e.get("payload") or {}) for e in ledger_entries]
    vouched = {p["run_id"]: p.get("record_sha256") for k, p in payloads if k == "sprint_run" and p.get("run_id")}
    applied = {p.get("run_id") for k, p in payloads if k == "file_change" and p.get("run_id")}
    used, bad = [], []
    for run_id in sorted(vouched):
        if verify(run_id, vouched[run_id], runs_dir) is None:
            used.append(load(run_id, runs_dir))
        else:
            bad.append(run_id)
    lost = orphans(ledger_entries, runs_dir)
    skipped = ", ".join(x for x in (f"{len(bad)} failing verification" if bad else "",
                                    f"{len(lost)} not in the ledger" if lost else "") if x)
    head = f" 📊 Runs: {len(used)} verified" + (f" (skipped: {skipped})" if skipped else "")
    if not used:
        return head + "\n  No verified runs yet -- /sprint execute records one per story."

    outcomes = Counter(r.get("outcome") for r in used)
    proposed = [r for r in used if r.get("outcome") == "proposed"]
    needed = Counter(r.get("proposed_candidate") for r in proposed)
    first = sum(1 for r in used if (r.get("attempts") or [{}])[0].get("ok"))
    by_model, stages = {}, Counter()
    for r in used:
        for a in r.get("attempts") or []:
            key = "/".join(x for x in (a.get("backend"), a.get("model_requested")) if x) or "unknown"
            tried_passed = by_model.setdefault(key, [0, 0])
            tried_passed[0] += 1
            tried_passed[1] += bool(a.get("ok"))
            if not a.get("ok"):
                stages[a.get("stage") or "?"] += 1
    tried = sum(t for t, _ in by_model.values())
    lines = ["─" * 50, head, "─" * 50,
             "  Outcomes   " + " · ".join(f"{o.replace('_', ' ')} {n}" for o, n in outcomes.most_common()),
             f"  Applied    {sum(1 for r in proposed if r['run_id'] in applied)} of {len(proposed)} proposals",
             f"  First try  {first} of {len(used)} runs passed with candidate 1",
             "  Passed on  " + (" · ".join(f"candidate {n}: {c}" for n, c in sorted(needed.items())) or "-"),
             f"  Candidates {tried} tried, {sum(p for _, p in by_model.values())} passed",
             "  By model (passed/tried):"]
    for key, (t, p) in sorted(by_model.items(), key=lambda kv: (-kv[1][0], kv[0])):
        lines.append(f"    {p}/{t}  {key}")
    if stages:
        lines.append("  Failed at:")
        for stage, n in stages.most_common():
            lines.append(f"    {n}  {stage} ({STAGE_MEANING.get(stage, 'unknown stage')})")
    if len(used) < RANK_MIN_RUNS:
        lines.append(f"  Counts only: {len(used)} run{'s' if len(used) != 1 else ''} is too few to compare "
                     f"models (needs {RANK_MIN_RUNS}+).")
    return "\n".join(lines)


def main() -> int:
    """python3 ~/bin/run_record.py -- checks the genome ledger, every run it
    vouches for, and lists orphan runs. Read-only. Exit 0 only if all hold.
    python3 ~/bin/run_record.py show [run] [n] -- the /run show view.
    python3 ~/bin/run_record.py stats -- the /runs stats view."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import genome_ledger
    if sys.argv[1:2] == ["stats"]:
        led = genome_ledger.GenomeLedger() if os.path.exists(genome_ledger.DEFAULT_PATH) else None
        print(stats(led.chain if led else []))
        return 0
    if sys.argv[1:2] == ["show"]:
        args = sys.argv[2:]
        led = genome_ledger.GenomeLedger() if os.path.exists(genome_ledger.DEFAULT_PATH) else None
        try:
            run_id = resolve(args[0] if args else None)
        except LookupError as e:
            print(f"[!] {e}")
            return 1
        print(show(run_id, led.chain if led else [], int(args[1]) if len(args) > 1 and args[1].isdigit() else None,
                   root=os.path.expanduser("~")))
        return 0
    if not os.path.exists(genome_ledger.DEFAULT_PATH):
        print(f"no genome ledger yet ({genome_ledger.DEFAULT_PATH})")
        entries = []
    else:
        led = genome_ledger.GenomeLedger()
        entries = led.chain
        problem = led.problem()
        print(f"ledger: {len(entries)} entries, " + ("valid" if problem is None else f"BROKEN: {problem}"))
        if problem is not None:
            return 1
    bad = 0
    runs = [e["payload"] for e in entries if e.get("kind") == "sprint_run"]
    for p in runs:
        problem = verify(p["run_id"], p["record_sha256"])
        bad += problem is not None
        print(f"  {p['run_id']}  {p.get('outcome', '?'):<20} {problem or 'OK'}")
    lost = orphans(entries)
    print(f"runs in ledger: {len(runs)}, failing verification: {bad}, orphans (not in ledger): {len(lost)}")
    for r in lost:
        print(f"  orphan: {r}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
