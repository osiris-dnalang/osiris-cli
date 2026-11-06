#!/usr/bin/env python3
"""
OSIRIS Benchmarks Master Entrypoint
===================================
One-command clean-room execution and independent verification.
Usage:
  python run_benchmark.py --verify-all
  python run_benchmark.py --track gov
"""

import argparse
import subprocess
import sys
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parent


def run_verify_all():
    cmd = [sys.executable, str(BENCH_ROOT / "verify_results.py")]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


def run_track(track_name: str):
    if track_name == "gov":
        cmd = [sys.executable, str(BENCH_ROOT / "gov_bench" / "run_gov_bench.py")]
        res = subprocess.run(cmd)
        sys.exit(res.returncode)
    else:
        print(f"Track '{track_name}' not yet staged or requires specific runner.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="OSIRIS Benchmarks Runner")
    parser.add_argument("--verify-all", action="store_true", help="Deterministically verify all benchmark outputs from raw data")
    parser.add_argument("--track", type=str, choices=["gov", "science", "edge", "qctrl"], help="Execute specific benchmark track")

    args = parser.parse_args()
    if args.verify_all:
        run_verify_all()
    elif args.track:
        run_track(args.track)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
