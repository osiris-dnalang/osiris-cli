"""
Unit tests for OSIRIS v5.0 IBM Heron r2 Closed-Loop Spectator Crosstalk Benchmark.
"""

from __future__ import annotations

import unittest
from osiris_cli.quantum.heron_staggered_benchmark import (
    HERON_KINGSTON_QUBITS,
    HERON_KINGSTON_EDGES,
    HeronBenchmarkEngine,
    ClosedLoopBenchmarkReport,
    BenchmarkTrialResult,
)


class TestHeronStaggeredBenchmark(unittest.TestCase):
    """Test suite validating the IBM Heron r2 closed-loop refocusing benchmark."""

    def setUp(self):
        self.engine = HeronBenchmarkEngine(
            qubits=HERON_KINGSTON_QUBITS,
            coupling_edges=HERON_KINGSTON_EDGES,
            j_zz_khz=60.0,
            total_delay_us=32.0,
            shots=1000  # fast unit test execution
        )

    def test_heron_cluster_geometry(self):
        """Verify 8-qubit heavy-hex coupling and bipartite partitioning."""
        self.assertEqual(len(self.engine.qubits), 8)
        self.assertEqual(len(self.engine.coupling), 7)
        self.assertEqual(len(self.engine.sub_A), 4)
        self.assertEqual(len(self.engine.sub_B), 4)
        self.assertTrue(set(self.engine.sub_A).isdisjoint(set(self.engine.sub_B)))

    def test_run_trial_baseline_sync(self):
        """Verify that synchronized baseline trial executes and produces expected metrics."""
        sched = self.engine.compiler.compile_staggered_schedule(
            qubits=self.engine.qubits,
            total_delay_us=self.engine.total_delay_us,
            sequence_type="xy4_stag",
            stagger_offset_ns=0.0
        )
        trial = self.engine.run_trial(sched, step_name="Test Baseline")
        self.assertIsInstance(trial, BenchmarkTrialResult)
        self.assertEqual(trial.stagger_offset_ns, 0.0)
        self.assertGreater(trial.mean_zz_residual, 0.0)
        self.assertGreater(trial.mean_plus_survival, 0.0)
        self.assertEqual(trial.suppression_ratio_vs_sync, 0.0)

    def test_closed_loop_benchmark_progression(self):
        """Verify that multi-stage closed-loop benchmark runs across iterations."""
        report = self.engine.run_closed_loop_benchmark(
            iterations=2,
            initial_stagger_ns=160.0,
            learning_rate=20.0
        )
        self.assertIsInstance(report, ClosedLoopBenchmarkReport)
        self.assertTrue(report.benchmark_id.startswith("BENCH-HERON-STAG-R2-"))
        self.assertEqual(len(report.trials), 4)  # Sync + Initial + 2 Opt iterations
        self.assertEqual(len(report.merkle_receipt), 64)

        # Confirm that at least one staggered trial achieves ZZ crosstalk suppression
        best_suppression = report.best_zz_suppression_pct
        self.assertGreater(best_suppression, 0.0)

        # Confirm dictionary export integrity
        d = report.to_dict()
        self.assertIn("trials", d)
        self.assertIn("merkle_receipt", d)
        self.assertEqual(d["optimal_stagger_ns"], report.optimal_stagger_ns)

    def test_summary_markdown_structure(self):
        """Verify markdown summary report generation."""
        report = self.engine.run_closed_loop_benchmark(iterations=1)
        md = report.summary_markdown()
        self.assertIn("IBM Heron r2", md)
        self.assertIn("Mean |ZZ| Residual", md)
        self.assertIn("Optimal Stagger Offset", md)
        self.assertIn("Merkle Receipt", md)


if __name__ == "__main__":
    unittest.main()
