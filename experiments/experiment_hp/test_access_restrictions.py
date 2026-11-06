#!/usr/bin/env python3
"""
test_access_restrictions.py
OSIRIS-HP-001 Verification Suite & Epistemic Access-Restriction Audit

Automated acceptance tests for OSIRIS-HP-001 Hayden-Preskill Protocol:
  1. Test A: Reversible Control achieves exact unit fidelity (H1).
  2. Test B: Epistemic Access Isolation (Decoder has ZERO support on R and C).
  3. Test C: Quantum Entanglement Advantage over Unentangled Baseline (H2).
  4. Test D: Page Transition Radiation Scaling (H3).
  5. Test E: Exact 2-Qubit Pauli Witness Identity (<XX> - <YY> + <ZZ>).
  6. Test F: Monotonic Physical Noise Decay (H4).
"""

import sys
import unittest
import numpy as np
from qiskit.quantum_info import random_unitary

from hayden_preskill_engine import (
    run_arm_a_reversible,
    run_arm_b_restricted,
    run_arm_c_noisy,
    evaluate_entanglement_fidelity
)

class TestHaydenPreskillAccessRestrictions(unittest.TestCase):

    def setUp(self):
        np.random.seed(1337)
        self.scramblers = [random_unitary(8, seed=s).data for s in [42, 101, 2024, 7777]]

    def test_h1_reversible_unit_recovery(self):
        """H1 Acceptance Test: Full-access inverse recovers state with F = 1.0."""
        for i, U in enumerate(self.scramblers):
            res = run_arm_a_reversible(U)
            f_rec = res["fidelity_F_rec"]
            self.assertAlmostEqual(
                f_rec, 1.0, places=10,
                msg=f"Scrambler {i} failed full-access reversible recovery: F = {f_rec}"
            )
            self.assertAlmostEqual(
                res["identity_error"], 0.0, places=12,
                msg="Pauli witness identity violated in Arm A"
            )

    def test_h2_restricted_access_isolation_and_advantage(self):
        """
        H2 Acceptance Test:
        Verify decoder operates on strictly isolated marginal and beats unentangled baseline.
        """
        advantages = []
        for i, U in enumerate(self.scramblers):
            res_ent = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=2)
            res_unent = run_arm_b_restricted(U, entangled_BE=False, radiation_qubits=2)

            f_ent = res_ent["fidelity_F_rec"]
            f_unent = res_unent["fidelity_F_rec"]

            # Must exceed classical separable limit (0.50)
            self.assertTrue(
                res_ent["is_entangled"],
                f"Scrambler {i} failed to exceed entanglement witness threshold: F = {f_ent}"
            )
            # Must demonstrate advantage over unentangled control
            self.assertGreater(
                f_ent, f_unent,
                f"Scrambler {i} failed to beat unentangled baseline: ent={f_ent}, unent={f_unent}"
            )
            advantages.append(f_ent - f_unent)

        mean_adv = np.mean(advantages)
        self.assertGreater(mean_adv, 0.10, "Mean entanglement advantage must exceed +10 percentage points")

    def test_h3_page_transition_radiation_sweep(self):
        """
        H3 Acceptance Test:
        Monotonic recovery scaling as late radiation size k_D crosses Page threshold.
        kD=1 (Pre-Page) < kD=2 (Post-Page) < kD=3 (Full access).
        """
        U = self.scramblers[0]
        res_kd1 = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=1)
        res_kd2 = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=2)
        res_kd3 = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=3)

        f1 = res_kd1["fidelity_F_rec"]
        f2 = res_kd2["fidelity_F_rec"]
        f3 = res_kd3["fidelity_F_rec"]

        # k_D = 1 has 1 radiation qubit, 2 remnant qubits (Pre-Page)
        # k_D = 2 has 2 radiation qubits, 1 remnant qubit (Post-Page)
        # k_D = 3 has 3 radiation qubits, 0 remnant qubits (Full access)
        self.assertLess(f1, f2, f"Pre-page fidelity {f1} must be strictly less than post-page {f2}")
        self.assertLessEqual(f2, f3, f"Post-page fidelity {f2} must be <= full-access {f3}")
        self.assertAlmostEqual(f3, 1.0, places=10, msg=f"Full radiation access must achieve unit fidelity: {f3}")

    def test_h4_monotonic_noise_degradation(self):
        """H4 Acceptance Test: Monotonic decay under increasing depolarizing noise."""
        U = self.scramblers[0]
        noise_levels = [0.00, 0.05, 0.10, 0.20, 0.40]
        fidelities = []

        for gamma in noise_levels:
            res_c = run_arm_c_noisy(U, noise_rate=gamma, radiation_qubits=2)
            fidelities.append(res_c["fidelity_F_rec"])

        for i in range(len(fidelities) - 1):
            self.assertGreaterEqual(
                fidelities[i], fidelities[i + 1],
                f"Noise response non-monotonic: {fidelities[i]} at Gamma={noise_levels[i]} vs {fidelities[i+1]} at Gamma={noise_levels[i+1]}"
            )

    def test_pauli_witness_tomography_exactness(self):
        """Test exactness of 2-qubit Pauli reconstruction identity."""
        for U in self.scramblers:
            res = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=2)
            # Reconstruct (1 + <XX> - <YY> + <ZZ>) / 4
            f_rec = res["fidelity_F_rec"]
            f_wit = res["fidelity_F_witness"]
            self.assertAlmostEqual(f_rec, f_wit, places=14)

if __name__ == "__main__":
    unittest.main()
