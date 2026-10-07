#!/usr/bin/env python3
"""
protege.py -- the Living Language Model's mentor -> protege layer.

The mentors are the code models OSIRIS can call (Ollama qwen2.5-coder:7b,
deepseek-coder, llama3.2:1b; Gemini; the AI Gateway). The protege learns
from them ONLY through verified outcomes: osiris_bench.py runs each mentor on
a frozen task suite and scores every candidate with a hidden acceptance test
the mentor never sees. A mentor's own confidence -- its own test passing --
is recorded as a separate number, never as success.

    python3 ~/bin/protege.py verify               # ledger chain + every stored artifact against its hash
    python3 ~/bin/protege.py scorecard            # per mentor: candidates, verified, false confidence
    python3 ~/bin/protege.py route                # per task: best mentor, or "insufficient evidence"
    python3 ~/bin/protege.py lessons [-o F.dna]   # the scorecard as a DNA::}AI{::Lang document
    python3 ~/bin/protege.py distill -o F.jsonl [--pairs]
                                                  # training data for a local protege model
                                                  # (--pairs: candidate ranking pairs)

What is learned, and where it goes:
  scorecard/route  which mentor to ask for which task. A recommendation, not
                   a switch: nothing here changes _synthesize()'s order.
  lessons          the same facts as DNA-Lang `evidence` blocks whose refs
                   are the ledger entries that support them, validated by
                   dna_lang.py -- so what the protege "knows" is content-
                   addressed and checkable, not free text.
  distill          (prompt, candidate) pairs whose candidate passed the
                   hidden test; --pairs gives candidate ranking pairs (one
                   passed, one failed) that answered the SAME prompt bytes
                   of the same task on the same suite. Only candidates
                   whose stored text still hashes to the ledgered hash. The
                   files are raw material: no consumer format, privacy
                   filter or held-out split is defined yet.

Why the scorecard does not require artifacts: a verdict is evidence because
its ledger entry is hash-chained; a mentor that returned nothing has no
artifact but did fail. Artifacts gate only what is built FROM candidate
text (distill), and `verify` reports any that are missing or altered.

Terms: "own test" is the test the mentor wrote for its own candidate;
"false confidence" (the bench's field name) counts candidates whose own
test passed while the hidden test failed. It is not a model's stated
confidence, which OSIRIS does not record.

Reads ~/.osiris/bench (results.ledger.jsonl + artifacts/). Refuses to use a
ledger whose hash chain does not verify. Writes nothing except -o files.
Exit codes: 0 ok, 1 no usable evidence / ledger broken, 2 usage.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

BIN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BIN)

BENCH_DIR = os.path.join(os.path.expanduser("~"), ".osiris", "bench")
GENESIS = "0" * 64
MIN_TASK_CANDIDATES = 3    # below this, a mentor has no standing on a task
MIN_MENTOR_CANDIDATES = 9  # ... or overall
Z95 = 1.959964


# ------------------------------------------------------------------ evidence

def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_ledger(bench_dir=BENCH_DIR):
    """Entries of the bench results ledger, re-verified here with the same
    rule as dnalang-core's Ledger.verify(). Returns (entries, problem)."""
    path = os.path.join(bench_dir, "results.ledger.jsonl")
    if not os.path.exists(path):
        return [], "no benchmark has been run yet (" + path + " does not exist)"
    entries, prev = [], GENESIS
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(l for l in f if l.strip()):
            try:
                e = json.loads(line)
            except ValueError:
                return [], f"entry {i}: not JSON"
            body = {k: v for k, v in e.items() if k not in ("prev", "hash")}
            if e.get("prev") != prev or \
                    e.get("hash") != hashlib.sha256((prev + _canon(body)).encode()).hexdigest():
                return [], f"entry {i}: hash chain broken -- nothing in this ledger is used"
            prev = e["hash"]
            entries.append(e)
    return entries, None


def mentor_of(entry, row):
    """Who wrote a candidate: the run's backend/model, or -- for an 'auto'
    run that fell through the chain -- the backend that answered."""
    if entry.get("backend") in (None, "auto"):
        return row.get("backend") or "unknown"
    return entry["backend"] + (f"/{entry['model']}" if entry.get("model") else "")


def candidates(entries, suite=None, runner=None, bench_dir=BENCH_DIR):
    """One flat record per scored attempt, from runs on `suite` posed by
    `runner` (either unchecked if None). Returns (records, skipped_runs).

    Each record is classified: no_output (the mentor produced no usable
    candidate -- a verified failure) or integrity (a hash the ledger names
    has no matching artifact -- an evidence defect, not a model failure)."""
    out, skipped = [], 0
    headers, seen = {}, set()

    def add(entry_hash, header, task, res):
        for row in res.get("attempts", []):
            c = {"entry": entry_hash, "run": header.get("run_id") or header.get("hash"),
                 "suite": header.get("suite_sha256"), "task": task,
                 "mentor": mentor_of(header, row), "n": row.get("n"),
                 "own_ok": bool(row.get("own_ok")), "hidden_ok": bool(row.get("hidden_ok")),
                 "prompt_sha256": row.get("prompt_sha256"),
                 "module_sha256": row.get("module_sha256"), "test_sha256": row.get("test_sha256")}
            c["no_output"] = c["module_sha256"] is None
            c["integrity"] = any(c[k] is not None and _artifact(bench_dir, c[k]) is None
                                 for k in ("prompt_sha256", "module_sha256", "test_sha256"))
            out.append(c)

    def comparable(header):
        # A prompt-strategy trial (bench_trial.py) poses tasks differently on purpose:
        # it is judged against its control by trials.py, never pooled into a mentor's score.
        return not ((suite and header.get("suite_sha256") != suite) or
                    (runner and header.get("runner_sha256") != runner) or header.get("strategy"))

    for e in entries:
        kind = e.get("kind")
        if kind == "bench_run":  # one entry per whole run (before RunLog)
            if not comparable(e):
                skipped += 1
                continue
            for task, res in (e.get("tasks") or {}).items():
                add(e["hash"], e, task, res)
        elif kind == "bench_run_start":
            headers[e.get("run_id")] = e
            if not comparable(e) and not e.get("strategy"):
                skipped += 1
        elif kind == "bench_task":
            header = headers.get(e.get("run_id"))
            key = (e.get("run_id"), e.get("task"))
            if header is None or key in seen or not comparable(header):
                continue  # no start entry, a duplicate, or not comparable: never scored twice or blind
            seen.add(key)
            add(e["hash"], header, e.get("task"), e.get("result") or {})
    return out, skipped


def latest_round(entries):
    """The most recent write-ahead round, for plain-English reporting:
    {run_id, mentor, started, status, tasks: [{task, delivered, own_ok,
    proposed, false_confidence, hidden_reason, seconds}]} or None."""
    starts = [e for e in entries if e.get("kind") == "bench_run_start" and not e.get("strategy")]
    if not starts:
        return None
    head = starts[-1]
    rid = head.get("run_id")
    ends = [e for e in entries if e.get("kind") == "bench_run_end" and e.get("run_id") == rid]
    tasks, seen = [], set()
    for e in entries:
        if e.get("kind") != "bench_task" or e.get("run_id") != rid or e.get("task") in seen:
            continue
        seen.add(e.get("task"))
        res = e.get("result") or {}
        rows = res.get("attempts") or [{}]
        tasks.append({"task": e.get("task"), "delivered": bool(res.get("delivered")),
                      "own_ok": bool(rows[-1].get("own_ok")), "proposed": any(r.get("own_ok") for r in rows),
                      "false_confidence": int(res.get("false_confidence") or 0),
                      "hidden_reason": None if res.get("delivered") else str(rows[-1].get("hidden_reason") or ""),
                      "seconds": res.get("seconds")})
    return {"run_id": rid, "mentor": mentor_of(head, {}), "started": head.get("ts"),
            "status": ends[-1].get("status") if ends else "unterminated", "planned": head.get("planned") or [],
            "tasks": tasks}


def run_status(entries):
    """{"complete": n, "partial": n, "unterminated": n} for write-ahead runs;
    unterminated = started but no end entry (killed, or still running)."""
    started = [e.get("run_id") for e in entries if e.get("kind") == "bench_run_start"]
    ended = {e.get("run_id"): e.get("status") for e in entries if e.get("kind") == "bench_run_end"}
    out = {"complete": 0, "partial": 0, "unterminated": 0}
    for r in started:
        out[ended.get(r) if ended.get(r) in ("complete", "partial") else "unterminated"] += 1
    return out


def wilson(k, n, z=Z95):
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def scorecard(cands):
    """mentor -> {candidates, verified, false_confidence, runs, tasks: {task: [verified, n]}, ci}"""
    card = {}
    for c in cands:
        m = card.setdefault(c["mentor"], {"candidates": 0, "verified": 0, "false_confidence": 0,
                                          "no_output": 0, "integrity_excluded": 0,
                                          "entries": set(), "runs": set(), "tasks": {}})
        if c.get("integrity"):
            # Reported, never scored: a vanished or altered artifact says
            # nothing about the mentor until the evidence is reconciled.
            m["integrity_excluded"] += 1
            continue
        m["candidates"] += 1
        m["no_output"] += c.get("no_output", False)
        m["verified"] += c["hidden_ok"]
        m["false_confidence"] += c["own_ok"] and not c["hidden_ok"]
        m["entries"].add(c["entry"])
        m["runs"].add(c.get("run") or c["entry"])
        t = m["tasks"].setdefault(c["task"], [0, 0])
        t[0] += c["hidden_ok"]
        t[1] += 1
    for m in card.values():
        m["ci"] = wilson(m["verified"], m["candidates"])
        m["entries"] = sorted(m["entries"])
        m["runs"] = sorted(m["runs"])
    return card


def route(card):
    """task -> (mentor, lower bound, verified, n) for the mentor with the
    highest Wilson lower bound among those with >= MIN_TASK_CANDIDATES on the
    task; (None, reason) when no mentor has standing. Plus an overall pick."""
    tasks = sorted({t for m in card.values() for t in m["tasks"]})
    picks = {}
    for t in tasks:
        best = None
        for name, m in card.items():
            k, n = m["tasks"].get(t, (0, 0))
            if n >= MIN_TASK_CANDIDATES:
                lo = wilson(k, n)[0]
                if best is None or lo > best[1]:
                    best = (name, lo, k, n)
        picks[t] = best or (None, f"insufficient evidence: no mentor has {MIN_TASK_CANDIDATES}+ "
                                  f"scored candidates on this task")
    eligible = [(m["ci"][0], name) for name, m in card.items() if m["candidates"] >= MIN_MENTOR_CANDIDATES]
    overall = max(eligible)[1] if eligible and max(eligible)[0] > 0 else None
    return picks, overall


# ------------------------------------------------------------------ rendering

def format_scorecard(card, skipped=0, suite=None):
    if not card:
        return ("No scored candidates" + (f" on suite {suite[:12]}" if suite else "") +
                (f" ({skipped} run(s) on other suites skipped)" if skipped else "") + ".")
    lines = []
    for name, m in sorted(card.items(), key=lambda kv: -kv[1]["ci"][0]):
        lo, hi = m["ci"]
        lines += [name,
                  f"  hidden-test pass       {m['verified']}/{m['candidates']}   Wilson 95% {lo:.2f}-{hi:.2f}",
                  f"  own pass, hidden fail  {m['false_confidence']}",
                  f"  no output              {m['no_output']}   (counted as fails)",
                  f"  integrity exclusions   {m['integrity_excluded']}   (missing/altered evidence; not scored)",
                  f"  runs                   {len(m['runs'])}"]
    lines.append("Only runs on the current task suite AND benchmark runner are counted.")
    if skipped:
        lines.append(f"{skipped} run(s) on a different task suite were not counted (not comparable).")
    return "\n".join(lines)


def format_route(card):
    picks, overall = route(card)
    if not picks:
        return "No tasks scored yet -- nothing to route."
    lines = []
    for t, p in picks.items():
        if p[0] is None:
            lines.append(f"  {t:<16} -- {p[1]}")
        else:
            lines.append(f"  {t:<16} {p[0]}  ({p[2]}/{p[3]} verified, lower bound {p[1]:.2f})")
    lines.append(f"Overall: {overall}" if overall else
                 f"Overall: insufficient evidence (needs {MIN_MENTOR_CANDIDATES}+ candidates and a "
                 f"lower bound above 0)")
    lines.append("Status: advisory only -- no backend routing has been changed.")
    return "\n".join(lines)


def _name(s):
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", s).strip("._-") or "unknown"


def _q(s):
    return json.dumps(s, ensure_ascii=False)


def lessons_source(card, suite):
    """The scorecard as a DNA-Lang 0.1 organism: one evidence block per
    mentor. A mentor with a verified candidate is a verified_observation
    whose refs are the ledger entries holding its runs; below the evidence
    thresholds it is only a hypothesis."""
    ev = []
    for name, m in sorted(card.items()):
        lo, hi = m["ci"]
        claim = (f"{name} delivered {m['verified']} of {m['candidates']} candidates that passed the hidden "
                 f"acceptance test on suite {suite[:12]} (Wilson 95% interval {lo:.2f}-{hi:.2f}); "
                 f"{m['false_confidence']} passed only their own test; "
                 f"{m['no_output']} produced no candidate.")
        enough = m["candidates"] >= MIN_MENTOR_CANDIDATES
        refs = ", ".join(_q("dna:sha256:" + h) for h in m["entries"]) if enough else ""
        kind = "verified_observation" if enough else "hypothesis"
        if not enough:
            claim += f" Fewer than {MIN_MENTOR_CANDIDATES} candidates: not yet evidence."
        ev.append(f"  evidence mentor.{_name(name)} {{\n    kind {_q(kind)}\n    statement {_q(claim)}\n"
                  f"    refs [{refs}]\n  }}\n")
    return ("// Generated by protege.py lessons from the verified bench ledger. Do not edit:\n"
            "// regenerate. refs are bench ledger entry hashes.\n"
            "organism osiris.protege {\n"
            "  meta {\n    schema \"dna-lang/0.1\"\n    title \"OSIRIS protege: what the mentors have shown\"\n  }\n"
            "  identity {\n    organism_id \"urn:osiris:organism:protege\"\n    species \"osiris.protege\"\n"
            "    generation 0\n  }\n"
            "  intent {\n    objective \"Learn which mentor to ask for which task, only from hidden-test outcomes.\"\n"
            "  }\n"
            "  constraints {\n    require [\"hidden_test_verdicts_only\", \"ledger_chain_verified\"]\n"
            "    prohibit [\"model_self_report_as_evidence\", \"routing_change_without_operator\"]\n"
            "    allowed_roots [\"bin\"]\n  }\n" + "".join(ev) + "}\n")


# ------------------------------------------------------------------ distill

def _artifact(bench_dir, h):
    """The stored text for hash h, or None if missing or not matching it."""
    if not h or not re.fullmatch(r"[0-9a-f]{64}", h):
        return None
    try:
        with open(os.path.join(bench_dir, "artifacts", h + ".txt"), "rb") as f:
            data = f.read()
    except OSError:
        return None
    return data.decode("utf-8") if hashlib.sha256(data).hexdigest() == h else None


def verify_artifacts(cands, bench_dir=BENCH_DIR):
    """(checked, problems): every hash a candidate names must have its file,
    and the file must still hash to it."""
    checked, problems = 0, []
    for c in cands:
        for key in ("prompt_sha256", "module_sha256", "test_sha256"):
            h = c.get(key)
            if h is None:
                continue  # no candidate text (e.g. the mentor returned nothing)
            checked += 1
            if _artifact(bench_dir, h) is None:
                problems.append(f"{c['task']} attempt {c['n']} ({c['mentor']}): {key} {h[:12]} "
                                f"missing or altered")
    return checked, problems


def distill(cands, bench_dir=BENCH_DIR, pairs=False):
    """Training records. SFT: prompt -> completion for each verified candidate.
    pairs: for each task prompt, every (verified, failed) pair of candidates
    -- chosen/rejected -- for preference tuning. Candidates whose artifacts are
    missing or altered are dropped and counted."""
    rows, dropped = [], 0
    usable = []
    for c in cands:
        if c.get("integrity"):
            dropped += 1
            continue
        prompt, module, test = (_artifact(bench_dir, c[k]) for k in ("prompt_sha256", "module_sha256", "test_sha256"))
        if prompt is None or module is None or test is None:
            dropped += 1
            continue
        completion = json.dumps({"path": f"{c['task']}.py", "module": module, "test": test}, ensure_ascii=False)
        usable.append((c, prompt, completion))
    if not pairs:
        for c, prompt, completion in usable:
            if c["hidden_ok"]:
                rows.append({"prompt": prompt, "completion": completion, "task": c["task"],
                             "mentor": c["mentor"], "evidence": "dna:sha256:" + c["entry"]})
        return rows, dropped
    by_prompt = {}
    for c, prompt, completion in usable:
        by_prompt.setdefault((c["task"], c["prompt_sha256"]), []).append((c, prompt, completion))
    for (_task, _p), group in sorted(by_prompt.items()):
        good = [g for g in group if g[0]["hidden_ok"]]
        bad = [g for g in group if not g[0]["hidden_ok"]]
        for g in good:
            for b in bad:
                rows.append({"prompt": g[1], "chosen": g[2], "rejected": b[2], "task": g[0]["task"],
                             "chosen_mentor": g[0]["mentor"], "rejected_mentor": b[0]["mentor"],
                             "rejected_false_confidence": b[0]["own_ok"],
                             "evidence": sorted({"dna:sha256:" + g[0]["entry"], "dna:sha256:" + b[0]["entry"]})})
    return rows, dropped


# ------------------------------------------------------------------ CLI

def current_suite():
    try:
        import osiris_bench
        return osiris_bench.suite_sha256()
    except Exception:
        return None


def current_runner():
    try:
        import osiris_bench
        return osiris_bench.runner_sha256()
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mentor -> protege learning from verified bench outcomes.")
    ap.add_argument("cmd", choices=("verify", "scorecard", "route", "lessons", "distill"))
    ap.add_argument("--bench-dir", default=BENCH_DIR)
    ap.add_argument("--all-suites", action="store_true", help="count runs on any task suite (not comparable)")
    ap.add_argument("--pairs", action="store_true", help="distill: candidate ranking pairs (one pass, one fail)")
    ap.add_argument("-o", "--out", help="lessons/distill output file")
    args = ap.parse_args(argv)
    if args.cmd == "distill" and not args.out:
        ap.error("distill needs -o FILE.jsonl")

    entries, problem = load_ledger(args.bench_dir)
    if problem:
        print(f"[!] {problem}")
        if not entries:
            print("    Build evidence from a native Termux shell (the sandbox does not run in proot-distro):\n"
                  "    sh ~/bin/mentor_round.sh")
        return 1
    suite = None if args.all_suites else current_suite()
    runner = None if args.all_suites else current_runner()
    cands, skipped = candidates(entries, suite, runner, args.bench_dir)
    card = scorecard(cands)
    if args.cmd == "verify":
        checked, problems = verify_artifacts(cands, args.bench_dir)
        print(f"Ledger: {len(entries)} entries, hash chain intact. Artifacts: {checked} checked, "
              f"{len(problems)} missing or altered.")
        for p in problems:
            print("  [!] " + p)
        return 1 if problems else 0
    if args.cmd == "scorecard":
        print(format_scorecard(card, skipped, suite))
        st = run_status(entries)
        if any(st.values()):
            print(f"Runs: {st['complete']} complete, {st['partial']} partial (Ctrl-C), {st['unterminated']} "
                  f"unterminated (killed or still running) -- finished tasks count in all three.")
    elif args.cmd == "route":
        print(format_route(card))
    elif args.cmd == "lessons":
        import dna_lang
        src = lessons_source(card, suite or "any-suite")
        ir = dna_lang.compile_source(src)  # raises Invalid: a lesson that is not valid DNA-Lang is not kept
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(src)
            print(f"Wrote {args.out} -- content id {dna_lang.content_id(ir)}")
        else:
            print(src, end="")
    else:
        rows, dropped = distill(cands, args.bench_dir, args.pairs)
        tmp = args.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, args.out)
        print(f"Wrote {len(rows)} {'ranking pair' if args.pairs else 'example'}(s) to {args.out}"
              + (f"; {dropped} candidate(s) dropped (artifact missing or altered)" if dropped else ""))
    return 0 if card else 1


if __name__ == "__main__":
    sys.exit(main())
