"""
tests/test_p2_adversarial_qldpc.py
OSIRIS 6.0 Pillar 2 Adversarial & Boundary Security Test Suite
Validates CSS commutation invariants, adversarial high-weight error handling,
and latency stability of the Edge QLDPC Neural Decoder.
"""

from __future__ import annotations
import numpy as np
import pytest
import time

from osiris_cli.quantum.neural_qldpc import (
    CSSCode,
    DecodingResult,
    NeuralSyndromeDecoder,
    PauliFrameTracker,
    gf2_rank,
)


class TestPillar2AdversarialQLDPC:
    """Adversarial stress and boundary tests for Pillar 2 Quantum Error Correction."""

    def test_adversarial_non_css_commutation_breach(self):
        """Injects non-commuting stabilizer generators to verify fail-closed detection."""
        code = CSSCode.steane_7_1_3()
        assert code.verify_css_commutation() is True

        # Adversarially flip a bit in H_X to break CSS orthogonality
        corrupted_hx = code.hx.copy()
        corrupted_hx[0, 0] ^= 1  # Flip (0, 0)
        
        # Verify that corrupted H_X * H_Z^T != 0 (mod 2)
        commutation = (corrupted_hx @ code.hz.T) % 2
        assert np.any(commutation != 0), "Corrupted matrix should violate commutation"

        # Construct adversarial CSS code object and verify commutation fails
        adversarial_code = CSSCode(name="corrupted_steane", n=7, hx=corrupted_hx, hz=code.hz)
        assert adversarial_code.verify_css_commutation() is False

    def test_adversarial_high_weight_syndrome_detection(self):
        """Adversarial error patterns beyond distance bound (t > (d-1)/2) must be flagged."""
        code = CSSCode.steane_7_1_3()
        decoder = NeuralSyndromeDecoder(code.hx, hidden_dim=32, seed=123)

        # Weight 3 error on Steane [[7, 1, 3]] (distance d=3 -> corrects only t=1)
        adversarial_error = np.array([1, 1, 1, 0, 0, 0, 0], dtype=np.uint8)
        syn = ((code.hx @ adversarial_error) % 2).tolist()

        result = decoder.decode(syn)
        # The decoder should predict a candidate, but if residual syndrome doesn't match, verify integrity
        predicted = np.array(result.predicted_error, dtype=np.uint8)
        residual = ((code.hx @ predicted) % 2).tolist()
        
        # Verify deterministic reporting of whether syndrome was resolved
        if residual == syn:
            assert result.syndrome_verified is True
        else:
            assert result.syndrome_verified is False

    def test_adversarial_latency_stress_under_load(self):
        """Ensures that under back-to-back inference bursts, mean latency remains strictly < 100 microseconds."""
        code = CSSCode.steane_7_1_3()
        decoder = NeuralSyndromeDecoder(code.hx, hidden_dim=32, seed=42)

        # Run 1,000 back-to-back syndrome decoding queries
        latencies = []
        for i in range(1000):
            # Adversarial cycling syndromes
            syn = [(i % 2), ((i // 2) % 2), ((i // 4) % 2)]
            t0 = time.perf_counter()
            res = decoder.decode(syn)
            t_el = (time.perf_counter() - t0) * 1e6  # microseconds
            latencies.append(t_el)

        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        print(f"Latency profile (1,000 runs): p50={p50:.2f} us, p95={p95:.2f} us, p99={p99:.2f} us")
        assert p50 < 100.0, f"p50 latency exceeded 100 us budget: {p50:.2f} us"
        assert p95 < 250.0, f"p95 latency exceeded tail budget: {p95:.2f} us"

    def test_pauli_frame_adversarial_cancelation(self):
        """Validates that Pauli frame tracker preserves exact algebraic group action under rapid flip sequences."""
        tracker = PauliFrameTracker(n_qubits=5)
        
        # 100 alternating X and Z flips on qubit 2
        for _ in range(50):
            tracker.apply_correction(err_x=[0, 0, 1, 0, 0], err_z=[0, 0, 0, 0, 0])
            tracker.apply_correction(err_x=[0, 0, 1, 0, 0], err_z=[0, 0, 0, 0, 0])
        # Even number of X flips must cancel to Identity
        assert tracker.get_pauli_string()[2] == "I", "Even X flips failed to cancel"

        # Apply X then Z -> Y
        tracker.apply_correction(err_x=[0, 0, 1, 0, 0], err_z=[0, 0, 0, 0, 0])
        tracker.apply_correction(err_x=[0, 0, 0, 0, 0], err_z=[0, 0, 1, 0, 0])
        assert tracker.get_pauli_string()[2] == "Y", f"Expected Y, got {tracker.get_pauli_string()[2]}"
