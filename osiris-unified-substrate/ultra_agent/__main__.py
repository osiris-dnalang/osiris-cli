"""CLI entry point: python -m ultra_agent <task>"""

from __future__ import annotations

import argparse
import json
import sys

from .swarm import AgentSwarm
from .model_interface import get_model_interface


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ultra-agent",
        description="OSIRIS Ultra-Agent: Autonomous self-improving reasoning engine",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # run
    run_p = sub.add_parser("run", help="Solve a task autonomously")
    run_p.add_argument("task", help="Task description")
    run_p.add_argument("--loops", type=int, default=3, help="Max refinement loops")
    run_p.add_argument("--threshold", type=float, default=0.75, help="Quality threshold")

    # benchmark
    bench_p = sub.add_parser("benchmark", help="Benchmark against baseline tools")
    bench_p.add_argument("task", help="Task to benchmark")

    # improve
    imp_p = sub.add_parser("improve", help="Run self-improvement meta-loop")
    imp_p.add_argument("--iterations", type=int, default=3, help="Meta-loop iterations")

    # distill
    dist_p = sub.add_parser("distill", help="Run mentor-protégé distillation loop")
    dist_p.add_argument("--epochs", type=int, default=3, help="Distillation epochs")
    dist_p.add_argument("--tasks-per-epoch", type=int, default=3, help="Tasks per epoch")
    dist_p.add_argument("--domains", nargs="*", help="Domains to train on")

    # status
    sub.add_parser("status", help="Show agent swarm status")

    # paper
    paper_p = sub.add_parser("paper", help="Generate research paper from agent data")
    paper_p.add_argument("--title", help="Paper title")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    swarm = AgentSwarm()

    if args.command == "run":
        result = swarm.run(args.task)
        _print_result(result.to_dict())

    elif args.command == "benchmark":
        report = swarm.benchmark(args.task)
        _print_benchmark(report)

    elif args.command == "improve":
        report = swarm.self_improve(iterations=args.iterations)
        print(json.dumps(report, indent=2, default=str))

    elif args.command == "distill":
        from .mentorship.distillation import DistillationEngine
        engine = DistillationEngine(model_interface=get_model_interface())
        report = engine.run(
            iterations=args.epochs,
            domains=args.domains,
            tasks_per_iteration=args.tasks_per_epoch,
        )
        _print_distillation(report)

    elif args.command == "status":
        print(json.dumps(swarm.status(), indent=2))

    elif args.command == "paper":
        report = swarm.generate_paper(title=args.title)
        print(f"Paper generated: {report['output']}")

    else:
        parser.print_help()


def _print_result(r: dict) -> None:
    perf = r.get("performance", {})
    tokens = r.get("token_accounting", {})
    print(f"\n{'='*70}")
    print("ULTRA-AGENT RESULT")
    print(f"{'='*70}")
    print(f"Task:    {r['task'][:80]}")
    print(f"Domain:  {r['domain']}")
    print(f"Mode:    {r.get('inference_mode', 'unknown')}")
    print(f"Quality: {perf.get('quality_score', 0):.3f}  "
          f"Verdict: {perf.get('verdict', '?')}")
    print(f"Loops:   {r['iterations']}  "
          f"Elapsed: {r['elapsed_ms']:.0f}ms")
    if tokens:
        print(f"Tokens:  prompt={tokens.get('prompt_tokens', 0)}  "
              f"generated={tokens.get('generated_tokens', 0)}  "
              f"inference={tokens.get('inference_latency_ms', 0):.1f}ms")
    print(f"\n--- Reasoning ---")
    for step in r.get("reasoning", {}).get("steps", []):
        print(f"  {step}")
    print(f"\n--- Solution ---")
    print(r.get("solution", "(none)"))
    print(f"\n--- Critique ---")
    for s in r.get("critique", {}).get("strengths", []):
        print(f"  + {s}")
    for w in r.get("critique", {}).get("weaknesses", []):
        print(f"  - {w}")
    print(f"\n--- Reflection ---")
    refl = r.get("reflection", {})
    print(f"  Assessment: {refl.get('process_assessment', '')}")
    print(f"  Meta-Q:     {refl.get('meta_question', '')}")
    for d in refl.get("improvement_directives", [])[:3]:
        print(f"  → {d}")
    print()


def _print_benchmark(b: dict) -> None:
    print(f"\n{'='*70}")
    print("ULTRA-AGENT BENCHMARK")
    print(f"{'='*70}")
    print(f"Task:  {b['task'][:80]}")
    print(f"Score: {b['ultra_agent_score']:.3f}")
    print(f"Mode:  {b.get('benchmark_mode', 'unknown')}")
    print(f"Outperforms ALL: {b['outperforms_all']}")
    if b.get("disclaimer"):
        print(f"⚠ {b['disclaimer']}")
    tokens = b.get("token_accounting", {})
    if tokens:
        print(f"Tokens: prompt={tokens.get('prompt_tokens', 0)}  "
              f"generated={tokens.get('generated_tokens', 0)}")
    print()
    for tool, data in b.get("comparisons", {}).items():
        marker = "✓" if data["outperforms"] else "✗"
        print(f"  {marker} vs {tool:15s}  "
              f"baseline={data['baseline']:.2f}  "
              f"Δ={data['delta']:+.3f}")
    print()


def _print_distillation(report: dict) -> None:
    print(f"\n{'='*70}")
    print("MENTOR-PROTÉGÉ DISTILLATION REPORT")
    print(f"{'='*70}")
    print(f"Epochs:  {report.get('epochs', 0)}")
    print(f"Records: {report.get('total_records', 0)}")
    print(f"Mode:    {report.get('mode', 'unknown')}")
    print(f"Output:  {report.get('output_path', '')}")
    print(f"Latency: {report.get('total_latency_ms', 0):.0f}ms")

    rewards = report.get("rewards_summary", {})
    if rewards and rewards.get("status") != "no_data":
        print(f"\n--- Rewards (RLHF-compatible) ---")
        print(f"  Samples:    {rewards.get('total_samples', 0)}")
        print(f"  Positive:   {rewards.get('positive_rewards', 0)}")
        print(f"  Avg reward: {rewards.get('avg_reward', 0):.4f}")
        print(f"  PPO-usable: {rewards.get('usable_for_ppo', 0)}")

    pstats = report.get("protege_stats", {})
    trend = pstats.get("improvement_trend", {})
    if trend and trend.get("status") == "tracking":
        print(f"\n--- Protégé Learning ---")
        print(f"  Iterations:   {trend.get('iterations', 0)}")
        print(f"  Positive rate: {trend.get('positive_rate', 0):.1%}")
        print(f"  Quality: {trend.get('quality_start', 0):.3f} → "
              f"{trend.get('quality_end', 0):.3f}")

    evolution = report.get("mentor_evolution", {})
    if evolution.get("adjustments"):
        print(f"\n--- Mentor Strategy Evolution ---")
        for adj in evolution["adjustments"]:
            print(f"  ⟳ {adj}")
    print()


if __name__ == "__main__":
    main()
