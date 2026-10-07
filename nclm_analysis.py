#!/usr/bin/env python3
"""
NCLM-1 Analysis & Monitoring Pipeline
======================================

Monitors manual OSIRIS interactions:
  1. Queries Neon Postgres for exchanges (with embeddings)
  2. Extracts BPB metrics from local ledger
  3. Generates learning curves
  4. Tracks memory retrieval effectiveness
  5. Produces real-time reports

Run in background while using `osiris` manually:
  python3 nclm_analysis.py --watch
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class NeonConnector:
    """Query Neon Postgres for exchange metrics."""

    def __init__(self):
        self.pg_url = os.environ.get('OSIRIS_PG_URL')
        self.conn = None

    async def connect(self):
        """Async connect to Neon."""
        if not self.pg_url:
            logger.warning("OSIRIS_PG_URL not set; Neon disabled")
            return False

        try:
            import asyncpg
            self.conn = await asyncpg.connect(self.pg_url, timeout=10)
            logger.info("Connected to Neon Postgres")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neon: {e}")
            return False

    async def get_exchanges(self, limit: int = 1000) -> List[Dict]:
        """Fetch recent exchanges from Neon."""
        if not self.conn:
            return []

        try:
            rows = await self.conn.fetch(
                """
                SELECT id, exchange_index, role, content, metadata, created_at,
                       1 - (embedding <=> (SELECT embedding FROM exchanges LIMIT 1)) as similarity
                FROM exchanges
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to query exchanges: {e}")
            return []

    async def get_hypotheses(self) -> List[Dict]:
        """Fetch hypotheses from Neon."""
        if not self.conn:
            return []

        try:
            rows = await self.conn.fetch(
                """
                SELECT id, hypothesis, status, outcome, confidence, created_at
                FROM hypotheses
                ORDER BY created_at DESC
                LIMIT 50
                """
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to query hypotheses: {e}")
            return []

    async def close(self):
        """Close connection."""
        if self.conn:
            await self.conn.close()


class LedgerAnalyzer:
    """Extract metrics from local OSIRIS ledger."""

    LEDGER_PATH = Path.home() / '.osiris' / 'living' / 'exchanges.jsonl'

    @classmethod
    def load_exchanges(cls) -> List[Dict]:
        """Load exchanges from ledger."""
        if not cls.LEDGER_PATH.exists():
            logger.warning(f"Ledger not found: {cls.LEDGER_PATH}")
            return []

        exchanges = []
        try:
            with open(cls.LEDGER_PATH) as f:
                for line in f:
                    if line.strip():
                        exchanges.append(json.loads(line))
            logger.info(f"Loaded {len(exchanges)} exchanges from ledger")
            return exchanges
        except Exception as e:
            logger.error(f"Failed to load ledger: {e}")
            return []

    STATS_PATH = Path.home() / '.osiris' / 'living' / 'stats.json'

    @classmethod
    def extract_bpb(cls, exchanges: List[Dict]) -> List[tuple]:
        """Extract BPB metrics by exchange."""
        bpb_values = []
        stats = {}
        if cls.STATS_PATH.exists():
            try:
                with open(cls.STATS_PATH) as f:
                    stats = json.load(f)
            except Exception:
                pass
        heldout_scores = stats.get("heldout_scores", {})
        # stats.json keys are full 64-hex exchange hashes; ledger rows carry a 40-hex prefix.
        by_hash = {h: score for h, score in heldout_scores.items() if isinstance(score, list) and score}

        for i, exch in enumerate(exchanges):
            h = exch.get('hash') or ''
            score = next((v for k, v in by_hash.items() if h and k.startswith(h)), None)
            if score is not None:
                bpb_values.append((int(exch.get('index', i)), float(score[0]), exch.get('t', '')))

        return bpb_values

    @classmethod
    def compute_learning_curve(cls, bpb_values: List[tuple]) -> Dict:
        """Compute learning curve statistics."""
        if not bpb_values:
            return {}

        bpbs = [v[1] for v in bpb_values]
        last_5 = bpbs[-5:]
        try:
            with open(cls.STATS_PATH.parent / 'unigram_baseline.json') as f:
                baseline = float(json.load(f)['bits_per_byte'])
        except (OSError, ValueError, KeyError):
            baseline = float('nan')

        return {
            'heldout_scored': len(bpbs),
            'mean_bpb': sum(bpbs) / len(bpbs),
            'min_bpb': min(bpbs),
            'max_bpb': max(bpbs),
            'last_5_mean': sum(last_5) / len(last_5),
            'baseline': baseline,
            'gate_status': 'decided only by NCLM-1_v1_evaluate.py (registered, Amendment 4); run it for the verdict',
        }


class ReportGenerator:
    """Generate evaluation reports."""

    @staticmethod
    def save_csv(exchanges: List[Dict], bpb_values: List[tuple], output_path: str):
        """Save results to CSV."""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['exchange_index', 'core_bpb', 't'])
            for index, bpb, t in bpb_values:
                writer.writerow([index, bpb, t])
        logger.info(f"Saved CSV: {output_path}")

    @staticmethod
    def print_report(stats: Dict, neon_count: int = 0):
        """Print formatted report."""
        if not stats:
            print("No metrics available yet")
            return

        print(f"""
╔════════════════════════════════════════════════════════════════════╗
║              NCLM-1 EVALUATION PROGRESS REPORT                     ║
╚════════════════════════════════════════════════════════════════════╝

📊 HELD-OUT ROWS
  • Scored: {stats['heldout_scored']} of 30 required
  • Neon stored: {neon_count} (with embeddings)

📈 CORE BITS/BYTE (held-out rows)
  • Mean: {stats['mean_bpb']:.3f}
  • Range: {stats['min_bpb']:.3f} - {stats['max_bpb']:.3f}
  • Last 5 mean: {stats['last_5_mean']:.3f}
  • Frozen corpus unigram (pre-registered): {stats['baseline']:.4f}

🎯 GATE
  • Verdict: {stats['gate_status']}
  • Target: 30-row mean ≤ 2.0, below both unigrams, last-5 mean ≤ 2.5

📅 WINDOW
  • NCLM-1 v1b closes 2026-10-08 23:59:59 UTC

╚════════════════════════════════════════════════════════════════════╝
""")


async def watch_evaluation(interval: int = 30):
    """Continuously monitor evaluation progress."""
    neon = NeonConnector()
    await neon.connect()

    print("📊 Watching NCLM-1 evaluation... (Ctrl+C to exit)")
    print(f"   Update interval: {interval}s")
    print()

    try:
        while True:
            # Get exchanges from ledger
            exchanges = LedgerAnalyzer.load_exchanges()
            bpb_values = LedgerAnalyzer.extract_bpb(exchanges)

            # Get count from Neon
            neon_exchanges = await neon.get_exchanges(limit=1)
            neon_count = len(neon_exchanges)

            # Compute stats
            stats = LedgerAnalyzer.compute_learning_curve(bpb_values)

            # Print report
            ReportGenerator.print_report(stats, neon_count)

            # Wait for next update
            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped")
    finally:
        await neon.close()


def generate_report(output_csv: str = None):
    """Generate final evaluation report."""
    exchanges = LedgerAnalyzer.load_exchanges()
    bpb_values = LedgerAnalyzer.extract_bpb(exchanges)
    stats = LedgerAnalyzer.compute_learning_curve(bpb_values)

    # Print report
    ReportGenerator.print_report(stats)

    # Save CSV
    if output_csv:
        ReportGenerator.save_csv(exchanges, bpb_values, output_csv)
    else:
        default_csv = '/root/osiris-cli/nclm_final_report.csv'
        ReportGenerator.save_csv(exchanges, bpb_values, default_csv)
        print(f"\n✅ Report saved: {default_csv}")

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description='NCLM-1 Analysis & Monitoring Pipeline'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Continuously monitor evaluation progress'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Update interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate final report and exit'
    )
    parser.add_argument(
        '--csv',
        type=str,
        help='Output CSV path (for --report)'
    )

    args = parser.parse_args()

    if args.watch:
        await watch_evaluation(args.interval)
    elif args.report:
        generate_report(args.csv)
    else:
        # Show current status
        generate_report()


if __name__ == '__main__':
    asyncio.run(main())
