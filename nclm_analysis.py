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
        hash_to_bpb = {h: score[0] for h, score in heldout_scores.items() if isinstance(score, list) and len(score) > 0}
        idx_to_bpb = {score[3]: score[0] for score in heldout_scores.values() if isinstance(score, list) and len(score) > 3}

        for i, exch in enumerate(exchanges):
            # Extract BPB from metadata if available
            metadata = exch.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    pass

            bpb = metadata.get('bpb') if isinstance(metadata, dict) else None
            if bpb is None:
                h = exch.get('hash')
                if h in hash_to_bpb:
                    bpb = hash_to_bpb[h]
                elif i in idx_to_bpb:
                    bpb = idx_to_bpb[i]

            if bpb is not None:
                bpb_values.append((i + 1, float(bpb)))

        return bpb_values

    @classmethod
    def compute_learning_curve(cls, bpb_values: List[tuple]) -> Dict:
        """Compute learning curve statistics."""
        if not bpb_values:
            return {}

        exchange_ids = [v[0] for v in bpb_values]
        bpbs = [v[1] for v in bpb_values]

        # Compute stats
        mean_bpb = sum(bpbs) / len(bpbs)
        min_bpb = min(bpbs)
        max_bpb = max(bpbs)

        # Last 5 exchanges
        last_5 = bpbs[-5:] if len(bpbs) >= 5 else bpbs
        last_5_mean = sum(last_5) / len(last_5)

        # Improvement from baseline (7.60)
        baseline = 7.60
        improvement = baseline - mean_bpb

        return {
            'total_exchanges': len(bpbs),
            'mean_bpb': mean_bpb,
            'min_bpb': min_bpb,
            'max_bpb': max_bpb,
            'last_5_mean': last_5_mean,
            'baseline': baseline,
            'improvement': improvement,
            'improvement_pct': (improvement / baseline) * 100,
            'gate_status': 'PASS' if mean_bpb <= 2.0 else 'FAIL' if mean_bpb > 5.0 else 'IN_PROGRESS',
        }


class ReportGenerator:
    """Generate evaluation reports."""

    @staticmethod
    def save_csv(exchanges: List[Dict], bpb_values: List[tuple], output_path: str):
        """Save results to CSV."""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['exchange_id', 'bpb', 'timestamp'])
            for exch_id, bpb in bpb_values:
                timestamp = exchanges[exch_id - 1].get('timestamp', '')
                writer.writerow([exch_id, bpb, timestamp])
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

📊 EXCHANGES COLLECTED
  • Total: {stats['total_exchanges']} exchanges
  • Neon stored: {neon_count} (with embeddings)
  • Status: {"✅ On track" if stats['total_exchanges'] >= 30 else "⏳ Collecting..."}

📈 BPB METRICS
  • Mean: {stats['mean_bpb']:.3f} bits/byte
  • Range: {stats['min_bpb']:.3f} - {stats['max_bpb']:.3f}
  • Baseline: {stats['baseline']:.3f}
  • Improvement: {stats['improvement']:.3f} ({stats['improvement_pct']:.1f}%)
  • Last 5 mean: {stats['last_5_mean']:.3f}

🎯 GATE STATUS
  • Current: {stats['gate_status']}
  • Target: ≤ 2.0 bits/byte
  • Progress: {min(100, (stats['baseline'] - stats['mean_bpb']) / (stats['baseline'] - 2.0) * 100):.1f}%

📅 TIMELINE
  • Deadline: Oct 7, 2026 (today)
  • Phase: Exploratory (collect 150+ exchanges)
  • Next: Measure learning curves, optimize, publish

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
