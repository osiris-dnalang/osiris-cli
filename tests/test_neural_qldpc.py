#!/usr/bin/env python3
"""
Unit tests for OSIRIS v5.0 Neural QLDPC Syndrome Decoder and Pauli Frame Tracker.
"""

import time
import numpy as np
import pytest

from osiris_cli.quantum.neural_qldpc import (
    CSSCode,
    DecodingResult,
    NeuralSyndromeDecoder,
    PauliFrameTracker,
    gf2_rank,
)


class TestNeuralQLDPC:
    def test_gf2_rank(self):
        # Identity has full rank
        eye = np.eye(4, dtype=np.uint8)
        assert gf2_rank(eye) == 4

        # Linear combination in GF(2)
        m = np.array([
            [1, 0, 1],
            [0, 1, 1],
            [1, 1, 0],  # row 0 + row 1 = row 2 in GF(2)
        ], dtype=np.uint8)
        assert gf2_rank(m) == 2

    def test_css_code_steane(self):
        code = CSSCode.steane_7_1_3()
        assert code.n == 7
        assert code.mx == 3
        assert code.mz == 3
        assert code.verify_css_commutation() is True
        assert code.logical_qubits_k() == 1
        weights = code.check_weights()
        assert weights["hx"] == (4, 4)
        assert weights["hz"] == (4, 4)

    def test_css_code_shor(self):
        code = CSSCode.shor_9_1_3()
        assert code.n == 9
        assert code.mx == 2
        assert code.mz == 6
        assert code.verify_css_commutation() is True
        assert code.logical_qubits_k() == 1

    def test_neural_decoder_steane_single_qubits(self):
        code = CSSCode.steane_7_1_3()
        decoder = NeuralSyndromeDecoder(code.hx, hidden_dim=32, seed=123)

        # Test zero error
        res0 = decoder.decode([0, 0, 0])
        assert res0.predicted_error == [0] * 7
        assert res0.syndrome_verified is True
        assert res0.residual_syndrome == [0, 0, 0]

        # Test every single qubit error (7 physical qubits)
        for q in range(7):
            e = np.zeros(7, dtype=np.uint8)
            e[q] = 1
            syn = ((code.hx @ e) % 2).tolist()
            res = decoder.decode(syn)
            assert res.predicted_error == e.tolist(), f"Failed for qubit {q}"
            assert res.syndrome_verified is True
            assert res.residual_syndrome == [0, 0, 0]

    def test_neural_decoder_training_and_latency(self):
        code = CSSCode.steane_7_1_3()
        decoder = NeuralSyndromeDecoder(code.hx, hidden_dim=32, seed=42)
        decoder.fit_synthetic_errors(p_error=0.08, n_samples=500, epochs=10)

        # Measure 100 decoding operations
        latencies = []
        for _ in range(100):
            syn = [1, 0, 1]
            res = decoder.decode(syn)
            latencies.append(res.latency_microseconds)

        mean_latency = np.mean(latencies)
        # Verify sub-100 microsecond latency requirement
        assert mean_latency < 100.0, f"Latency too high: {mean_latency:.2f} µs"

    def test_pauli_frame_tracker(self):
        tracker = PauliFrameTracker(n_qubits=7)
        assert tracker.get_pauli_string() == "IIIIIII"
        assert tracker.update_count == 0

        # Apply X flip on qubit 1 and Z flip on qubit 3
        err_x = [0, 1, 0, 0, 0, 0, 0]
        err_z = [0, 0, 0, 1, 0, 0, 0]
        tracker.apply_correction(err_x=err_x, err_z=err_z)
        assert tracker.get_pauli_string() == "IXIZIII"
        assert tracker.update_count == 1

        # Apply Y flip on qubit 1 (X and Z) -> cancels X, leaves Z
        tracker.apply_correction(err_x=[0, 1, 0, 0, 0, 0, 0], err_z=[0, 1, 0, 0, 0, 0, 0])
        assert tracker.get_pauli_string() == "IZIZIII"
        assert tracker.update_count == 2

        # Reset
        tracker.reset()
        assert tracker.get_pauli_string() == "IIIIIII"
        assert tracker.update_count == 0
