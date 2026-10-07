#!/usr/bin/env python3
"""
bench_trial.py -- one benchmark round under a declared prompt strategy.

    python3 ~/bin/bench_trial.py --strategy invariant-first-v1 --backend ollama \
        --model qwen2.5-coder:7b --tasks backlog,claims,gaps [--k 1] [--events]

The same round osiris_bench.py runs -- same tasks, hidden tests, candidate
loop, gates, sandbox, write-ahead ledger and artifacts -- with one declared
difference: each task prompt starts with the strategy's fixed preamble
(prompt_strategies.py). osiris_bench.py itself is not modified, so
runner_sha256 is unchanged and the round stays comparable with a baseline
round of the same model. The start entry records strategy and
strategy_sha256; protege.py keeps strategy rounds out of the mentor
scorecard, and trials.py compares them with their control. Exit codes as
osiris_bench.py (0 ran, 1 recording failed, 2 bad args, 3 no sandbox,
130 interrupted).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osiris_bench as bench  # noqa: E402
import prompt_strategies  # noqa: E402


class TrialRunLog(bench.RunLog):
    """RunLog whose start entry also declares the strategy."""

    def __init__(self, out_dir, tasks, k, backend, model, strategy):
        self.out_dir, self.ledger = out_dir, bench._load_ledger(out_dir)
        self.run_id = "bench-" + bench.time.strftime("%Y%m%dT%H%M%SZ", bench.time.gmtime()) + "-" + os.urandom(3).hex()
        self.planned = [t["id"] for t in tasks]
        self.start = bench._append_durably(self.ledger, "bench_run_start", {
            "run_id": self.run_id,
            "commit": bench._git("rev-parse", "HEAD") or None,
            "dirty": bool(bench._git("status", "--porcelain", "--untracked-files=no")),
            "suite_sha256": bench.suite_sha256(), "runner_sha256": bench.runner_sha256(),
            "backend": backend, "model": model, "k": k, "planned": self.planned,
            "strategy": strategy, "strategy_sha256": prompt_strategies.sha256(strategy)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One benchmark round under a declared prompt strategy.")
    ap.add_argument("--strategy", required=True, help=f"one of: {', '.join(sorted(prompt_strategies.STRATEGIES))}")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--backend", default="ollama", choices=bench.BACKENDS)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=bench.DEFAULT_OUT)
    ap.add_argument("--events", action="store_true")
    args = ap.parse_args(argv)
    bench._events["on"] = args.events
    try:
        prompt_strategies.get(args.strategy)
        tasks = bench.load_tasks([t for t in args.tasks.split(",") if t] or None)
    except (KeyError, ValueError) as e:
        print(f"[!] {e}", file=sys.stderr)
        return 2
    if args.k < 1 or (args.model and args.backend != "ollama"):
        print("[!] --k must be >= 1; --model only applies to --backend ollama", file=sys.stderr)
        return 2
    unavailable = bench._load_osiris()._sandbox_probe()
    if unavailable:
        print(f"[!] Sandbox unavailable in this environment: {unavailable}")
        return 3
    model = args.model or (bench._load_osiris().CODE_MODEL if args.backend == "ollama" else None)
    baseline_prompt = bench.prompt_for
    bench.prompt_for = lambda task: prompt_strategies.apply(args.strategy, baseline_prompt(task))
    print(f"Trial: strategy {args.strategy} ({prompt_strategies.sha256(args.strategy)[:12]}) · "
          f"{args.backend}{f' ({model})' if model else ''} · k={args.k}")
    try:
        log = TrialRunLog(args.out, tasks, args.k, args.backend, model, args.strategy)
        print(f"Run {log.run_id}: each task is recorded as soon as it finishes")
        bench.emit("run_start", run_id=log.run_id, backend=args.backend, model=model, k=args.k,
                   tasks=[t["id"] for t in tasks], strategy=args.strategy)
        results, cut = bench.run_suite(tasks, args.k, args.backend, model, on_task=log.task)
        log.end(results, cut)
        bench.emit("run_end", status="partial" if cut else "complete", completed=len(results),
                   planned=len(tasks), interrupted_during=cut)
    except OSError as e:
        print(f"[!] Recording failed: {e} -- run left without an end entry", file=sys.stderr)
        return 1
    s = bench.summarize(results)
    print(f"\ndelivered {s['delivered']}/{s['tasks']}   false confidence {s['false_confidence']}   "
          f"({args.strategy}) -- {'PARTIAL' if cut else 'complete'}: {log.run_id}")
    return 130 if cut else 0


if __name__ == "__main__":
    sys.exit(main())
