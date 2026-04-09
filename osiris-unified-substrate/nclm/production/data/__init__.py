"""CLI entry for auto dataset generation: python -m nclm.production.data.autogen"""

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="OSIRIS NCLM Automatic Dataset Generator")
    parser.add_argument("--output", default="data/dataset.jsonl", help="Output path for SFT data")
    parser.add_argument("--preference-output", default=None, help="Output path for preference data")
    parser.add_argument("--count", type=int, default=200, help="Number of SFT samples")
    parser.add_argument("--preference-count", type=int, default=100, help="Number of preference pairs")
    parser.add_argument("--domains", nargs="*", default=None, help="Domains: math qa code reasoning")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--full-metadata", action="store_true", help="Include full metadata per sample")
    args = parser.parse_args()

    from .autogen import (
        generate_dataset, generate_preference_dataset,
        save_sft_jsonl, save_full_jsonl, save_preference_jsonl,
    )

    print(f"Generating {args.count} SFT samples...")
    samples = generate_dataset(count=args.count, domains=args.domains, seed=args.seed)

    if args.full_metadata:
        path = save_full_jsonl(samples, args.output)
    else:
        path = save_sft_jsonl(samples, args.output)
    print(f"  SFT data saved to {path} ({len(samples)} samples)")

    # Domain breakdown
    domains = {}
    for s in samples:
        domains[s.domain] = domains.get(s.domain, 0) + 1
    print(f"  Domains: {json.dumps(domains)}")

    if args.preference_output:
        print(f"Generating {args.preference_count} preference pairs...")
        pairs = generate_preference_dataset(count=args.preference_count, seed=args.seed)
        ppath = save_preference_jsonl(pairs, args.preference_output)
        print(f"  Preference data saved to {ppath} ({len(pairs)} pairs)")

    print("Done.")


if __name__ == "__main__":
    main()
