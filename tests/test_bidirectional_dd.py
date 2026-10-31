"""Tests for OSIRIS v5.0 Bidirectional DD Compiler."""
import unittest
from osiris_cli.quantum.bidirectional_dd import BidirectionalDDCompiler, StaggeredDDSchedule


class TestBidirectionalDD(unittest.TestCase):
    def test_bipartite_partition_kingston_lattice(self):
        kingston_qubits = [14, 15, 19, 31, 32, 33, 34, 35]
        kingston_edges = [(14, 15), (15, 19), (19, 33), (31, 32), (32, 33), (33, 34), (34, 35)]
        compiler = BidirectionalDDCompiler(heavy_hex_coupling=kingston_edges)

        sub_A, sub_B = compiler.partition_bipartite(kingston_qubits)
        set_A, set_B = set(sub_A), set(sub_B)
        self.assertTrue(set_A.isdisjoint(set_B))
        self.assertEqual(set_A.union(set_B), set(kingston_qubits))

        for u, v in kingston_edges:
            self.assertFalse(u in set_A and v in set_A, f"Edge ({u}, {v}) both in Sublattice A")
            self.assertFalse(u in set_B and v in set_B, f"Edge ({u}, {v}) both in Sublattice B")

    def test_staggered_schedule_generation(self):
        compiler = BidirectionalDDCompiler()
        sched = compiler.compile_staggered_schedule(
            qubits=[0, 1, 2, 3],
            total_delay_us=16.0,
            sequence_type="xy4_stag",
            stagger_offset_ns=100.0
        )
        self.assertIsInstance(sched, StaggeredDDSchedule)
        self.assertEqual(sched.num_pulses, 4)
        self.assertEqual(len(sched.pulse_offsets_ns), 4)
        self.assertNotEqual(sched.schedule_hash(), "")
        self.assertEqual(sched.stagger_offset_ns, 100.0)

    def test_optimize_from_feedback(self):
        compiler = BidirectionalDDCompiler()
        sched = compiler.compile_staggered_schedule([0, 1], 32.0, "xy4_stag", 120.0)
        feedback = {(0, 1): 0.18}
        updated = compiler.optimize_from_feedback(sched, feedback, learning_rate=30.0)

        self.assertGreater(updated.stagger_offset_ns, sched.stagger_offset_ns)
        self.assertEqual(len(compiler.history), 1)
        self.assertEqual(compiler.history[0]["mean_zz_residual"], 0.18)


if __name__ == "__main__":
    unittest.main()
