"""Run the meta-loop: python -m nclm.production.meta_loop [--iterations 5] [--objective ...]"""
import argparse
import json
from .meta_loop import run_meta_loop

def main():
    parser = argparse.ArgumentParser(description="OSIRIS NCLM Self-Improving Meta-Loop")
    parser.add_argument("--objective", default="Improve OSIRIS NCLM benchmark scores",
                        help="High-level objective for the meta-loop")
    parser.add_argument("--iterations", type=int, default=5, help="Maximum meta-loop iterations")
    parser.add_argument("--output", default="artifacts/meta_loop_state.json", help="State output path")
    args = parser.parse_args()

    result = run_meta_loop(objective=args.objective, max_iterations=args.iterations)

    print(f"\n{'='*50}")
    print("META-LOOP COMPLETE")
    print("=" * 50)
    print(f"  Iterations: {len(result['history'])}")
    print(f"  Converged:  {result['converged']}")
    print(f"  Data generated: {result['total_data_generated']}")
    print(f"  Best scores: {json.dumps(result['best_scores'], indent=2)}")

if __name__ == "__main__":
    main()
