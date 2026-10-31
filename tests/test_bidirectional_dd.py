"""
Unit tests for OSIRIS v5.0 Bidirectional Dynamical Decoupling Compiler.
"""

from __future__ import annotations

import unittest
from osiris_cli.quantum.bidirectional_dd import (
    BidirectionalDDCompiler,
    StaggeredDDSchedule,
)


class TestBidirectionalDDCompiler(unittest.TestCase):
    """Test suite for BidirectionalDDCompiler and StaggeredDDSchedule."""

    def setUp(self):
        self.kingston_qubits = [14, 15, 19, 31, 32, 33, 34, 35]
        self.kingston_edges = [
            (14, 15), (15, 19), (19, 33), (31, 32), (32, 33), (33, 34), (34, 35)
        ]
        self.compiler = BidirectionalDDCompiler(heavy_hex_coupling=self.kingston_edges)

    def test_bipartite_partitioning_path_graph(self):
        """Test bipartite 2-coloring on a simple 4-qubit line graph."""
        qubits = [0, 1, 2, 3]
        edges = [(0, 1), (1, 2), (2, 3)]
        sub_A, sub_B = self.compiler.partition_bipartite(qubits, coupling=edges)

        self.assertEqual(len(sub_A) + len(sub_B), 4)
        # Adjacent qubits cannot be in the same sublattice
        for u, v in edges:
            self.assertFalse(u in sub_A and v in sub_A, f"Edge ({u}, {v}) both in sub_A")
            self.assertFalse(u in sub_B and v in sub_B, f"Edge ({u}, {v}) both in sub_B")

    def test_bipartite_partitioning_heavy_hex(self):
        """Test bipartite partitioning on IBM Kingston heavy-hex layout."""
        sub_A, sub_B = self.compiler.partition_bipartite(self.kingston_qubits)
        self.assertEqual(len(sub_A) + len(sub_B), len(self.kingston_qubits))
        for u, v in self.kingston_edges:
            self.assertFalse(u in sub_A and v in sub_A)
            self.assertFalse(u in sub_B and v in sub_B)

    def test_bipartite_partitioning_disconnected(self):
        """Test fallback balancing on fully disconnected qubits."""
        qubits = [10, 20, 30, 40]
        sub_A, sub_B = self.compiler.partition_bipartite(qubits, coupling=[])
        self.assertEqual(len(sub_A), 2)
        self.assertEqual(len(sub_B), 2)
        self.assertEqual(set(sub_A + sub_B), set(qubits))

    def test_compile_staggered_schedule_xy4(self):
        """Test XY4 staggered schedule compilation."""
        sched = self.compiler.compile_staggered_schedule(
            qubits=self.kingston_qubits,
            total_delay_us=32.0,
            sequence_type="xy4_stag",
            stagger_offset_ns=160.0
        )
        self.assertEqual(sched.num_pulses, 4)
        self.assertEqual(sched.total_delay_us, 32.0)
        self.assertEqual(sched.stagger_offset_ns, 160.0)
        self.assertEqual(len(sched.pulse_offsets_ns), len(self.kingston_qubits))

        # Check that sublattice B offsets are shifted by stagger_offset_ns relative to sublattice A
        ref_A = sched.pulse_offsets_ns[sched.sublattice_A[0]]
        ref_B = sched.pulse_offsets_ns[sched.sublattice_B[0]]
        for t_a, t_b in zip(ref_A, ref_B):
            self.assertAlmostEqual(t_b - t_a, 160.0, places=1)

    def test_compile_staggered_schedule_xy8(self):
        """Test XY8 staggered schedule compilation (8 pulses)."""
        sched = self.compiler.compile_staggered_schedule(
            qubits=[0, 1],
            total_delay_us=16.0,
            sequence_type="xy8_ortho_stag",
            stagger_offset_ns=100.0
        )
        self.assertEqual(sched.num_pulses, 8)
        self.assertEqual(len(sched.pulse_offsets_ns[0]), 8)

    def test_schedule_hash_deterministic(self):
        """Test that schedule hashes are deterministic and content-addressed."""
        sched1 = self.compiler.compile_staggered_schedule([0, 1], 16.0, "xy4_stag", 120.0)
        sched2 = self.compiler.compile_staggered_schedule([0, 1], 16.0, "xy4_stag", 120.0)
        sched3 = self.compiler.compile_staggered_schedule([0, 1], 16.0, "xy4_stag", 140.0)

        self.assertEqual(sched1.schedule_hash(), sched2.schedule_hash())
        self.assertNotEqual(sched1.schedule_hash(), sched3.schedule_hash())

    def test_optimize_from_feedback_gradient(self):
        """Test closed-loop parameter mutation from empirical QPU parity feedback."""
        sched = self.compiler.compile_staggered_schedule([0, 1], 32.0, "xy4_stag", 160.0)
        high_residual_feedback = {(0, 1): 0.15}
        optimized_step1 = self.compiler.optimize_from_feedback(sched, high_residual_feedback, learning_rate=20.0)
        self.assertGreater(optimized_step1.stagger_offset_ns, sched.stagger_offset_ns)

        low_residual_feedback = {(0, 1): 0.02}
        optimized_step2 = self.compiler.optimize_from_feedback(optimized_step1, low_residual_feedback, learning_rate=10.0)
        self.assertLess(optimized_step2.stagger_offset_ns, optimized_step1.stagger_offset_ns)

    def test_schedule_to_dict_roundtrip(self):
        """Test dictionary serialization of StaggeredDDSchedule."""
        sched = self.compiler.compile_staggered_schedule([0, 1], 16.0, "xy4_stag", 100.0)
        d = sched.to_dict()
        self.assertIn("schedule_id", d)
        self.assertIn("pulse_offsets_ns", d)
        self.assertEqual(d["stagger_offset_ns"], 100.0)


if __name__ == "__main__":
    unittest.main()
