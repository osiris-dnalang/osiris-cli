"""
Tests for OSIRIS v5.0 Milestone 3: Closed-Loop Spectator Dynamical Decoupling Refocussing.
"""

import unittest
from osiris.quantum.bidirectional_dd import (
    BidirectionalDDCompiler,
    StaggeredDDSchedule,
    SpectatorTomography,
    ClosedLoopRefocuser,
    CrosstalkResidual,
    ClosedLoopResult,
)


try:
    import qiskit  # noqa: F401
    import qiskit_aer  # noqa: F401
    HAS_QISKIT = True
except ImportError:  # optional extra; the CI core install has no qiskit
    HAS_QISKIT = False


class TestClosedLoopDD(unittest.TestCase):
    """Test suite for closed-loop spectator crosstalk optimization under SYS-021."""

    def setUp(self):
        # 8-qubit heavy-hex test chain from ibm_marrakesh
        self.qubits = [14, 15, 19, 31, 32, 33, 34, 35]
        self.edges = [(14, 15), (15, 19), (19, 35), (35, 34), (34, 33), (33, 32), (32, 31)]
        self.refocuser = ClosedLoopRefocuser(
            qubits=self.qubits,
            edges=self.edges,
            total_delay_us=32.0,
            sequence_type="xy8_ortho_stag",
        )

    def test_spectator_tomography_correlations(self):
        """Verify parity correlation computation from bitstrings."""
        # Qubit 0 and 1 are identical in all shots
        counts_even = {"00000000": 800, "11111111": 200}
        corrs = SpectatorTomography.compute_edge_correlations(counts_even, [(14, 15)], self.qubits)
        self.assertAlmostEqual(corrs[(14, 15)], 1.0, places=3)

        # Qubit 0 and 1 are opposite in all shots
        counts_odd = {"00000001": 500, "11111110": 500}
        # In Qiskit bitstring order, last bit is qubit 14, second to last is qubit 15
        corrs_odd = SpectatorTomography.compute_edge_correlations(counts_odd, [(14, 15)], self.qubits)
        self.assertAlmostEqual(corrs_odd[(14, 15)], -1.0, places=3)

    @unittest.skipUnless(HAS_QISKIT, "qiskit and qiskit_aer are optional extras")
    def test_closed_loop_simulator_convergence(self):
        """Test end-to-end closed-loop optimization with synthetic crosstalk gradient."""
        result = self.refocuser.optimize_with_simulator(
            initial_stagger_ns=60.0,
            max_iterations=4,
            target_residual=0.03,
            learning_rate=30.0,
        )

        self.assertIsInstance(result, ClosedLoopResult)
        self.assertTrue(result.converged)
        self.assertLess(result.final_error, result.initial_error)
        self.assertGreater(result.error_reduction_pct, 0.0)
        self.assertEqual(len(result.history), result.iterations_run)

        # Verify SYS-021 cryptographic receipt
        receipt = result.cryptographic_receipt
        self.assertEqual(receipt["protocol"], "OSIRIS-SYS021-CLOSED-LOOP-DD")
        self.assertEqual(receipt["operator"], "Devin Phillip Davis / Enki")
        self.assertEqual(receipt["payload_sha256"], result.final_schedule.schedule_hash())
        self.assertIn("ledger_nonce", receipt)
        self.assertEqual(len(receipt["ledger_nonce"]), 16)

    @unittest.skipUnless(HAS_QISKIT, "qiskit and qiskit_aer are optional extras")
    def test_circuit_compilation_with_qiskit(self):
        """Verify Qiskit compilation of optimized schedule."""
        sched = self.refocuser.compiler.compile_staggered_schedule(
            self.qubits,
            total_delay_us=16.0,
            sequence_type="xy4_stag",
            stagger_offset_ns=160.0,
        )
        qc = self.refocuser.compiler.compile_qiskit(
            self.qubits,
            total_delay_us=16.0,
            sequence_type="xy4_stag",
            stagger_offset_ns=160.0,
            state_prep="plus",
            measure=True,
        )
        self.assertEqual(qc.num_qubits, max(self.qubits) + 1)
        self.assertEqual(qc.num_clbits, len(self.qubits))


if __name__ == "__main__":
    unittest.main()
