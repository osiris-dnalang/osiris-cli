#!/usr/bin/env python3
"""
osiris_bench.py -- a frozen benchmark for Engine 2, scored by tests the model
never sees.

Until now a sandbox "pass" meant the model's OWN test passed: nclm_eval.py
(story #20) passed while scoring bits against nats, and genome_ledger.py
(story #22) passed while rewriting its "append-only" file. Here each task
(bin/bench_tasks/<id>/) has:
  task.json       the spec -- with existing.py, the only thing the model sees
  existing.py     (modify tasks only) the current module the story changes
  acceptance.py   hand-written invariant test, run in the same proot sandbox
  reference.py    a solution that must pass (checked by --check)
  known_bad.py    a plausible wrong solution that must fail -- for nclm_eval
                  and genome_ledger, OSIRIS's own applied versions

Each task runs the SAME loop as /sprint execute (verify_loop.first_passing):
up to k candidates, each verified by the placeholder gate, the API-
preservation check and the candidate's OWN test in the sandbox, failures fed
back into the next attempt. The hidden acceptance test then scores every
candidate. Reported per run:
  pass@1            candidate 1 passes the hidden test
  delivered         the candidate the loop would propose passes the hidden test
  oracle@k          any of the k candidates passes the hidden test
  false_confidence  candidates whose own test passed but the hidden test failed

Every run appends one entry to a hash-chained results ledger (dnalang-core's
Ledger) with the commit, backend, model, k and a hash of the task suite --
results are only comparable under the same suite_sha256, backend and model.

Usage:
  python3 ~/bin/osiris_bench.py --check                     # validate the suite; no model calls
  python3 ~/bin/osiris_bench.py                             # Engine 2's normal fallback chain
  python3 ~/bin/osiris_bench.py --backend gemini --k 3
  python3 ~/bin/osiris_bench.py --backend ollama --model qwen2.5-coder:7b --tasks gaps,claims
Exit code: 0 ran (or suite valid), 1 suite invalid / setup failure, 2 bad args,
3 the proot sandbox cannot run here (e.g. inside proot-distro) -- nothing scored
or recorded.
"""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import time

BIN = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.dirname(BIN)
TASKS_DIR = os.path.join(BIN, "bench_tasks")
DEFAULT_OUT = os.path.join(HOME_DIR, ".osiris", "bench")
from genome_ledger import LEDGER_SRC  # noqa: E402  one resolver for dnalang-core's ledger.py
BACKENDS = ("auto", "gateway", "gemini", "ollama")

sys.path.insert(0, BIN)
import payload_gate  # noqa: E402
import structured_proposal  # noqa: E402
import verify_loop  # noqa: E402

_osiris = None


def _load_osiris():
    """bin/osiris or osiris_termux_console.py as a module; main() is not run."""
    global _osiris
    if _osiris is None:
        target = os.path.join(BIN, "osiris_termux_console.py")
        if not os.path.isfile(target):
            target = os.path.join(BIN, "osiris")
        loader = importlib.machinery.SourceFileLoader("osiris_repl", target)
        spec = importlib.util.spec_from_loader("osiris_repl", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        _osiris = module
    return _osiris


def load_tasks(ids=None):
    names = sorted(d for d in os.listdir(TASKS_DIR) if os.path.isdir(os.path.join(TASKS_DIR, d)))
    if ids:
        unknown = set(ids) - set(names)
        if unknown:
            raise ValueError(f"unknown task(s): {sorted(unknown)}; available: {names}")
        names = [n for n in names if n in ids]
    tasks = []
    for n in names:
        d = os.path.join(TASKS_DIR, n)
        with open(os.path.join(d, "task.json"), encoding="utf-8") as f:
            task = json.load(f)
        for part in ("acceptance", "reference", "known_bad"):
            with open(os.path.join(d, f"{part}.py"), encoding="utf-8") as f:
                task[part] = f.read()
        existing = os.path.join(d, "existing.py")
        task["existing"] = None
        if os.path.exists(existing):
            with open(existing, encoding="utf-8") as f:
                task["existing"] = f.read()
        tasks.append(task)
    return tasks


def suite_sha256() -> str:
    """Hash of every task file, so results from a changed suite are never compared."""
    h = hashlib.sha256()
    for root, _dirs, files in sorted(os.walk(TASKS_DIR)):
        for fn in sorted(files):
            if fn.endswith((".py", ".json")):
                path = os.path.join(root, fn)
                h.update(os.path.relpath(path, TASKS_DIR).encode())
                with open(path, "rb") as f:
                    h.update(f.read())
    return h.hexdigest()


RUNNER_FILES = ("osiris_bench.py", "structured_proposal.py", "verify_loop.py", "payload_gate.py")


def runner_sha256() -> str:
    """Hash of the code that builds prompts, runs the candidate loop and gates
    candidates. With suite_sha256 it defines comparability: the suite hash
    covers task specs and hidden tests, this covers how they are posed and
    judged. (The backend call itself, osiris._synthesize, is not covered;
    backend and model are recorded per run, and each attempt's exact prompt
    bytes by prompt_sha256.)"""
    h = hashlib.sha256()
    for fn in RUNNER_FILES:
        h.update(fn.encode())
        with open(os.path.join(BIN, fn), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


EVENT_PREFIX = "@@OSIRIS_EVENT "
_events = {"on": False}


def emit(kind, **data):
    """One machine-readable progress line (only with --events): the REPL's
    /bench draws its live card from these instead of scraping log text."""
    if _events["on"]:
        print(EVENT_PREFIX + json.dumps(dict(kind=kind, **data)), flush=True)


def _default_run():
    return _load_osiris()._run_sandboxed_test


def _gates(task, module_source):
    """The checks /sprint execute applies before running any test. Returns a reason or None."""
    gate = payload_gate.check_payload(module_source)
    if gate:
        return f"placeholder gate: {gate}"
    if task["existing"] is not None:
        dropped = _load_osiris()._public_names(task["existing"]) - _load_osiris()._public_names(module_source)
        if dropped:
            return f"drops existing public name(s) {sorted(dropped)}"
    return None


def _tail(output):
    lines = [l for l in output.strip().splitlines() if l.strip() and not l.startswith("SANDBOX_")]
    return (lines[-1] if lines else "sandbox failure")[:200]


def score(task, module_source, run=None):
    """(passed, reason) against the task's HIDDEN acceptance test."""
    reason = _gates(task, module_source)
    if reason:
        return False, reason
    passed, output = (run or _default_run())(f"{task['module']}.py", module_source, task["acceptance"])
    return (True, "pass") if passed else (False, _tail(output))


def prompt_for(task) -> str:
    current = ""
    if task["existing"] is not None:
        current = (f"\nCURRENT CONTENT OF {task['module']}.py (modify THIS file; output the COMPLETE "
                   f"updated file, preserving every existing public function unless the story requires "
                   f"changing it):\n{task['existing']}\n")
    return (f"You are OSIRIS Sovereign Synthesizer. Write the Python module described below, exactly as "
            f"specified, AND a discrete test that proves it works.\n\nSPEC: {task['spec']}\n{current}\n"
            + structured_proposal.instructions(f"{task['module']}.py", task["module"]))


def run_task(task, k=1, backend="auto", model=None, synthesize=None, run=None):
    """One task through the /sprint execute loop, then hidden scoring."""
    run = run or _default_run()
    osiris = None
    if synthesize is None:
        osiris = _load_osiris()
        synthesize = osiris._synthesize
    only = None if backend == "auto" else backend
    used, prompts = [], []

    def generate(feedback):
        prompt = prompt_for(task) + (verify_loop.feedback_block(feedback) if feedback else "")
        raw = synthesize(prompt, structured=True, only=only, ollama_model=model)
        name = osiris._last_backend["name"] if osiris else "injected"
        used.append(name)
        prompts.append(prompt)
        proposal = structured_proposal.parse_proposal(raw)
        if proposal is None:
            err = osiris._last_backend.get("error") if osiris else None
            return None, f"no usable proposal (empty or malformed){f' ({err})' if err else ''}"
        return proposal, ""

    def verify(proposal):
        reason = _gates(task, proposal["module"])
        if reason:
            return False, reason
        ok, output = run(f"{task['module']}.py", proposal["module"], proposal["test"])
        return (True, "own test passed") if ok else (False, output)

    def on_attempt(a):
        print(f"[bench] {task['id']} candidate {a['n']}/{k}: own check "
              f"{'pass' if a['ok'] else 'fail -- ' + _tail(a['reason'])}")
        emit("attempt", task=task["id"], n=a["n"], k=k, own_ok=bool(a["ok"]))

    winner, attempts = verify_loop.first_passing(generate, verify, k, on_attempt)
    rows, texts = [], {}
    for a, name, prompt in zip(attempts, used, prompts):
        row = {"n": a["n"], "backend": name, "own_ok": a["ok"]}
        # Keep what the mentor was asked and what it wrote, by hash: a verdict
        # with no candidate cannot teach anything (protege.py distill).
        row["prompt_sha256"] = _keep(texts, prompt)
        if a["candidate"] is None:
            hidden_ok, hidden_reason = False, a["reason"]
        else:
            hidden_ok, hidden_reason = score(task, a["candidate"]["module"], run)
            row["module_sha256"] = _keep(texts, a["candidate"]["module"])
            row["test_sha256"] = _keep(texts, a["candidate"]["test"])
        row.update(hidden_ok=hidden_ok, hidden_reason=hidden_reason)
        rows.append(row)
    delivered = bool(winner) and rows[-1]["hidden_ok"]
    result = {
        "pass_at_1": rows[0]["hidden_ok"],
        "delivered": delivered,
        "oracle_at_k": any(r["hidden_ok"] for r in rows),
        "false_confidence": sum(1 for r in rows if r["own_ok"] and not r["hidden_ok"]),
        "attempts": rows,
        "_texts": texts,  # sha256 -> text; record() stores these as artifacts, not in the ledger
    }
    status = "PASS" if delivered else ("NOTHING PROPOSED" if not winner else "FAIL (own test passed)")
    print(f"[bench] {task['id']}: delivered {status}"
          + ("" if delivered else f" -- hidden: {rows[-1]['hidden_reason'][:150]}"))
    return result


def _keep(texts, text):
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    texts[h] = text
    return h


def store_artifacts(results, out_dir):
    """Writes every result's _texts to out_dir/artifacts/<sha256>.txt (write-once:
    an existing file must already hold exactly those bytes) and removes _texts.
    Owner-only permissions: prompts carry project source."""
    art = os.path.join(out_dir, "artifacts")
    os.makedirs(art, mode=0o700, exist_ok=True)
    os.chmod(art, 0o700)
    for r in results.values():
        for h, text in r.pop("_texts", {}).items():
            path = os.path.join(art, h + ".txt")
            data = text.encode("utf-8")
            if os.path.exists(path):
                with open(path, "rb") as f:
                    if hashlib.sha256(f.read()).hexdigest() != h:
                        raise OSError(f"artifact {path} does not match its hash -- not overwritten")
                continue
            tmp = path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
    _fsync_dir(art)


def _fsync_dir(path):
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass  # some filesystems (e.g. Android FUSE) refuse directory fsync
    finally:
        os.close(fd)


def check_suite(tasks, run=None):
    """Every reference must pass, every known-bad must fail, and for modify
    tasks the unchanged existing module must fail. Returns problems."""
    problems = []
    for t in tasks:
        ok, why = score(t, t["reference"], run)
        if not ok:
            problems.append(f"{t['id']}: reference FAILS ({why})")
        bad_ok, _ = score(t, t["known_bad"], run)
        if bad_ok:
            problems.append(f"{t['id']}: known_bad PASSES -- the acceptance test is too weak")
        unchanged = ""
        if t["existing"] is not None:
            # Returning the file untouched must not count as solving the story.
            same_ok, _ = score(t, t["existing"], run)
            if same_ok:
                problems.append(f"{t['id']}: the UNCHANGED existing module passes")
            unchanged = f"   unchanged {'PASS (!)' if same_ok else 'fail'}"
        kind = "modify" if t["existing"] is not None else "new"
        print(f"  {t['id']:<16} {kind:<7} reference {'pass' if ok else 'FAIL'}   "
              f"known_bad {'PASS (!)' if bad_ok else 'fail'}{unchanged}")
    return problems


def run_suite(tasks, k=1, backend="auto", model=None, runner=None, on_task=None):
    """Runs tasks in order. Each finished task is handed to on_task (which
    persists it) BEFORE the next one starts. Ctrl-C while a task runs stops
    the suite: returns (results of the finished tasks, id of the task that
    was cut off, or None). The cut-off task's attempts are discarded, never
    scored. An on_task failure propagates -- nothing is claimed stored.
    result["seconds"]: monotonic time from the task's start to its verdict,
    before persistence."""
    runner = runner or run_task
    results = {}
    for i, t in enumerate(tasks, start=1):
        print(f"[bench] task {i}/{len(tasks)}: {t['id']}")
        emit("task_start", task=t["id"], i=i, n=len(tasks))
        start = time.monotonic()
        try:
            r = runner(t, k, backend, model)
        except KeyboardInterrupt:
            print(f"\n[bench] interrupted during {t['id']} -- its attempts are discarded; "
                  f"{len(results)} finished task(s) are already recorded")
            return results, t["id"]
        r["seconds"] = round(time.monotonic() - start, 1)
        if on_task:
            on_task(t["id"], r)
        results[t["id"]] = r
        last = r["attempts"][-1] if r["attempts"] else {}
        # Sent only after on_task returned: "saved" means the ledger entry exists.
        emit("task_done", task=t["id"], delivered=r["delivered"], false_confidence=r["false_confidence"],
             own_ok=bool(last.get("own_ok")), proposed=any(a.get("own_ok") for a in r["attempts"]),
             attempts=len(r["attempts"]), seconds=r["seconds"], saved=on_task is not None,
             hidden_reason=None if r["delivered"] else str(last.get("hidden_reason", ""))[:160])
    return results, None


def _load_ledger(out_dir):
    if not os.path.exists(LEDGER_SRC):
        raise FileNotFoundError(f"dnalang-core ledger not found at {LEDGER_SRC}")
    spec = importlib.util.spec_from_file_location("_bench_ledger", LEDGER_SRC)
    ledger_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger_mod)
    os.makedirs(out_dir, exist_ok=True)
    return ledger_mod.Ledger(os.path.join(out_dir, "results.ledger.jsonl"))


def _append_durably(ledger, kind, payload):
    entry = ledger.append(kind, payload)
    with open(ledger.path, "rb") as f:
        os.fsync(f.fileno())
    return entry


class RunLog:
    """Write-ahead run record in the results ledger:
      bench_run_start  before any model call: run_id, suite, runner, backend, model, k, planned tasks
      bench_task       one per finished task, appended (and fsynced) as soon as it is scored,
                       after its artifacts are on disk
      bench_run_end    status complete|partial, completed/planned, interrupted_during, summary
    A run killed without warning (SIGKILL, Android, battery) has no end entry;
    its bench_task entries still stand. bench_task entries are the record of
    what finished; the end entry only summarizes."""

    def __init__(self, out_dir, tasks, k, backend, model):
        self.out_dir, self.ledger = out_dir, _load_ledger(out_dir)
        self.run_id = "bench-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + os.urandom(3).hex()
        self.planned = [t["id"] for t in tasks]
        self.start = _append_durably(self.ledger, "bench_run_start", {
            "run_id": self.run_id,
            "commit": _git("rev-parse", "HEAD") or None,
            "dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
            "suite_sha256": suite_sha256(), "runner_sha256": runner_sha256(),
            "backend": backend, "model": model, "k": k, "planned": self.planned})

    def task(self, task_id, result):
        store_artifacts({task_id: result}, self.out_dir)  # files first: a ledgered hash always has its file
        return _append_durably(self.ledger, "bench_task", {"run_id": self.run_id, "task": task_id,
                                                           "result": result})

    def end(self, results, cut):
        return _append_durably(self.ledger, "bench_run_end", {
            "run_id": self.run_id, "status": "partial" if cut else "complete",
            "completed": len(results), "planned": len(self.planned), "interrupted_during": cut,
            "summary": summarize(results)})


def summarize(results) -> dict:
    n = len(results)
    return {m: sum(bool(r[m]) for r in results.values()) for m in ("pass_at_1", "delivered", "oracle_at_k")} | \
        {"false_confidence": sum(r["false_confidence"] for r in results.values()), "tasks": n}


def _git(*args):
    try:
        return subprocess.run(["git", "-C", HOME_DIR, *args], capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def record(results, k, backend, model, out_dir):
    """Appends a whole run as ONE bench_run entry (the format before RunLog;
    kept for callers that score in memory). main() uses RunLog."""
    ledger = _load_ledger(out_dir)
    store_artifacts(results, out_dir)  # before the entry: a ledgered hash always has its file
    return _append_durably(ledger, "bench_run", {
        "commit": _git("rev-parse", "HEAD") or None,
        "dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "suite_sha256": suite_sha256(),
        "runner_sha256": runner_sha256(),
        "backend": backend, "model": model, "k": k,
        "summary": summarize(results),
        "tasks": results,
    })


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Frozen Engine 2 benchmark with hidden acceptance tests.")
    ap.add_argument("--check", action="store_true", help="validate the suite itself (no model calls)")
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
    ap.add_argument("--k", type=int, default=1, help="candidates per task, as /sprint execute --k")
    ap.add_argument("--backend", default="auto", choices=BACKENDS,
                    help="auto = Engine 2's normal fallback chain; otherwise that backend alone")
    ap.add_argument("--model", default=None, help="Ollama model for --backend ollama (default: CODE_MODEL)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="results ledger directory")
    ap.add_argument("--events", action="store_true", help="also print machine-readable progress events")
    args = ap.parse_args(argv)
    _events["on"] = args.events
    if args.k < 1:
        print("[!] --k must be >= 1", file=sys.stderr)
        return 2
    if args.model and args.backend != "ollama":
        print("[!] --model only applies to --backend ollama", file=sys.stderr)
        return 2
    try:
        tasks = load_tasks([t for t in args.tasks.split(",") if t] or None)
    except ValueError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 2

    print(f"Suite {suite_sha256()[:12]} -- {len(tasks)} task(s)")
    # Without a working sandbox every candidate fails, references included:
    # --check would call the suite invalid and a run would record 0/N.
    unavailable = _load_osiris()._sandbox_probe()
    if unavailable:
        print(f"[!] Sandbox unavailable in this environment: {unavailable}")
        print("Environment unsupported -- nothing scored. Run from a native Termux shell, "
              "not inside proot-distro.")
        return 3
    if args.check:
        problems = check_suite(tasks)
        for p in problems:
            print(f"[!] {p}")
        print("Suite valid." if not problems else "Suite INVALID.")
        return 1 if problems else 0

    model = args.model
    if args.backend == "ollama" and model is None:
        model = _load_osiris().CODE_MODEL
    print(f"Backend {args.backend}{f' ({model})' if model else ''}, k={args.k}")
    try:
        log = RunLog(args.out, tasks, args.k, args.backend, model)
        print(f"Run {log.run_id}: each task is recorded as soon as it finishes")
        emit("run_start", run_id=log.run_id, backend=args.backend, model=model, k=args.k,
             tasks=[t["id"] for t in tasks])
        results, cut = run_suite(tasks, args.k, args.backend, model, on_task=log.task)
        log.end(results, cut)
        emit("run_end", status="partial" if cut else "complete", completed=len(results), planned=len(tasks),
             interrupted_during=cut)
    except OSError as e:
        # Fail closed: tasks recorded before this point stand; nothing after is claimed.
        print(f"[!] Recording failed: {e} -- run left without an end entry", file=sys.stderr)
        return 1
    s = summarize(results)
    n = s["tasks"]
    print(f"\npass@1 {s['pass_at_1']}/{n}   delivered {s['delivered']}/{n}   oracle@{args.k} "
          f"{s['oracle_at_k']}/{n}   false confidence {s['false_confidence']}")
    print(f"Recorded: {os.path.join(args.out, 'results.ledger.jsonl')} -- "
          + (f"PARTIAL: {len(results)}/{len(tasks)} tasks, interrupted during {cut}" if cut else "complete"))
    return 130 if cut else 0


if __name__ == "__main__":
    sys.exit(main())
