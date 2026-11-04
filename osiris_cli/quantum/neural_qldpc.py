#!/usr/bin/env python3
"""
OSIRIS v5.0: Neural Quantum LDPC (QLDPC) Syndrome Decoder & Pauli Frame Tracker
================================================================================
Implements ultra-low-latency neural syndrome decoding and real-time Pauli frame tracking
for CSS and Quantum LDPC error-correcting codes on sovereign edge nodes (Node Beta / Node Alpha).

Physics and Algorithmic Grounding:
- CSS Code Invariant: H_X @ H_Z.T = 0 (mod 2) ensures X and Z stabilizers commute.
- Syndrome Extraction: s_Z = H_X @ e_X (mod 2), s_X = H_Z @ e_Z (mod 2).
- Neural Feed-Forward Decoding: Single-pass matrix-vector mapping s -> e_hat in < 100 µs,
  circumventing iterative belief-propagation trapping sets.
- In-Memory Pauli Frame: Real-time update P_frame = P_frame ^ e_hat without pausing
  cryogenic QPU pulse trains.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def gf2_rank(matrix: np.ndarray) -> int:
    """Computes the matrix rank over GF(2) using Gaussian elimination."""
    m = matrix.copy() % 2
    rows, cols = m.shape
    rank = 0
    for c in range(cols):
        pivot = -1
        for r in range(rank, rows):
            if m[r, c] == 1:
                pivot = r
                break
        if pivot == -1:
            continue
        if pivot != rank:
            m[[rank, pivot]] = m[[pivot, rank]]
        for r in range(rows):
            if r != rank and m[r, c] == 1:
                m[r] = (m[r] + m[rank]) % 2
        rank += 1
        if rank == rows:
            break
    return rank


@dataclass
class CSSCode:
    """
    Calderbank-Shor-Steane (CSS) Quantum Code representation.
    
    Parameters:
        name: Name of the code.
        n: Number of physical qubits.
        hx: Parity-check matrix for X errors (shape m_x, n).
        hz: Parity-check matrix for Z errors (shape m_z, n).
    """
    name: str
    n: int
    hx: np.ndarray
    hz: np.ndarray

    def __post_init__(self):
        self.hx = np.asarray(self.hx, dtype=np.uint8) % 2
        self.hz = np.asarray(self.hz, dtype=np.uint8) % 2
        assert self.hx.shape[1] == self.n, f"hx cols ({self.hx.shape[1]}) != n ({self.n})"
        assert self.hz.shape[1] == self.n, f"hz cols ({self.hz.shape[1]}) != n ({self.n})"

    @property
    def mx(self) -> int:
        return self.hx.shape[0]

    @property
    def mz(self) -> int:
        return self.hz.shape[0]

    def verify_css_commutation(self) -> bool:
        """Verifies H_X @ H_Z.T = 0 (mod 2)."""
        comm = (self.hx @ self.hz.T) % 2
        return bool(np.all(comm == 0))

    def logical_qubits_k(self) -> int:
        """Computes k = n - rank(Hx) - rank(Hz)."""
        rx = gf2_rank(self.hx)
        rz = gf2_rank(self.hz)
        return self.n - rx - rz

    def check_weights(self) -> Dict[str, Tuple[int, int]]:
        """Returns max and min row check weights for Hx and Hz."""
        wx = np.sum(self.hx, axis=1)
        wz = np.sum(self.hz, axis=1)
        return {
            "hx": (int(np.min(wx)), int(np.max(wx))),
            "hz": (int(np.min(wz)), int(np.max(wz))),
        }

    @classmethod
    def steane_7_1_3(cls) -> CSSCode:
        """Canonical [[7, 1, 3]] Steane Code."""
        h = np.array([
            [1, 0, 0, 1, 0, 1, 1],
            [0, 1, 0, 1, 1, 0, 1],
            [0, 0, 1, 0, 1, 1, 1],
        ], dtype=np.uint8)
        return cls(name="Steane_7_1_3", n=7, hx=h.copy(), hz=h.copy())

    @classmethod
    def shor_9_1_3(cls) -> CSSCode:
        """Canonical [[9, 1, 3]] Shor Code."""
        # 8 checks: 2 X-checks comparing 3-qubit blocks, 6 Z-checks comparing neighbors
        hx = np.zeros((2, 9), dtype=np.uint8)
        hx[0, 0:6] = 1
        hx[1, 3:9] = 1
        hz = np.zeros((6, 9), dtype=np.uint8)
        hz[0, [0, 1]] = 1
        hz[1, [1, 2]] = 1
        hz[2, [3, 4]] = 1
        hz[3, [4, 5]] = 1
        hz[4, [6, 7]] = 1
        hz[5, [7, 8]] = 1
        return cls(name="Shor_9_1_3", n=9, hx=hx, hz=hz)


@dataclass
class DecodingResult:
    """Result of a neural syndrome decoding step."""
    syndrome: List[int]
    predicted_error: List[int]
    syndrome_verified: bool
    residual_syndrome: List[int]
    latency_microseconds: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeuralSyndromeDecoder:
    """
    Sub-100-microsecond feed-forward neural syndrome decoder.
    Maps syndrome s in {0, 1}^m -> predicted error e_hat in {0, 1}^n.
    """

    def __init__(
        self,
        parity_matrix: np.ndarray,
        hidden_dim: int = 64,
        seed: int = 42,
    ):
        self.h = np.asarray(parity_matrix, dtype=np.uint8) % 2
        self.m, self.n = self.h.shape
        self.hidden_dim = hidden_dim
        
        # Initialize deterministic weights
        rng = np.random.RandomState(seed)
        # Layer 1: syndrome (m) -> hidden
        self.w1 = rng.randn(self.m, hidden_dim).astype(np.float32) * np.sqrt(2.0 / self.m)
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        # Layer 2: hidden -> error probabilities (n)
        self.w2 = rng.randn(hidden_dim, self.n).astype(np.float32) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(self.n, dtype=np.float32)

        # Build an exact single-bit syndrome lookup table for guaranteed single-qubit recovery
        self.single_qubit_lookup: Dict[Tuple[int, ...], int] = {}
        for q in range(self.n):
            syn = tuple(((self.h[:, q]) % 2).tolist())
            if syn not in self.single_qubit_lookup and any(syn):
                self.single_qubit_lookup[syn] = q

    def fit_synthetic_errors(self, p_error: float = 0.05, n_samples: int = 2000, epochs: int = 15):
        """Fits neural decoder weights on synthetic independent Pauli errors."""
        rng = np.random.RandomState(1337)
        # Generate random errors
        errors = (rng.rand(n_samples, self.n) < p_error).astype(np.float32)
        # Ensure single qubit errors are included
        for q in range(self.n):
            single = np.zeros((1, self.n), dtype=np.float32)
            single[0, q] = 1.0
            errors = np.vstack([errors, np.repeat(single, 50, axis=0)])
        
        syndromes = (errors @ self.h.T) % 2

        lr = 0.05
        for _ in range(epochs):
            # Forward pass
            h1 = np.maximum(0.0, syndromes @ self.w1 + self.b1)  # ReLU
            logits = h1 @ self.w2 + self.b2
            probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -15.0, 15.0)))  # Sigmoid

            # Backward pass (BCE loss gradient)
            d_logits = (probs - errors) / errors.shape[0]
            d_w2 = h1.T @ d_logits
            d_b2 = np.sum(d_logits, axis=0)

            d_h1 = d_logits @ self.w2.T * (h1 > 0)
            d_w1 = syndromes.T @ d_h1
            d_b1 = np.sum(d_h1, axis=0)

            self.w1 -= lr * d_w1
            self.b1 -= lr * d_b1
            self.w2 -= lr * d_w2
            self.b2 -= lr * d_b2

    def decode(self, syndrome: Sequence[int], threshold: float = 0.5) -> DecodingResult:
        """
        Executes sub-100-microsecond decoding for an extracted syndrome vector.
        """
        t0 = time.perf_counter_ns()
        s_arr = np.asarray(syndrome, dtype=np.float32).reshape(1, -1)
        s_tuple = tuple(int(x) for x in syndrome)

        # Check trivial zero syndrome
        if not any(s_tuple):
            t_elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
            return DecodingResult(
                syndrome=list(syndrome),
                predicted_error=[0] * self.n,
                syndrome_verified=True,
                residual_syndrome=[0] * self.m,
                latency_microseconds=t_elapsed_us,
                confidence=1.0,
            )

        # 1. Fast path: Direct single-qubit lookup
        if s_tuple in self.single_qubit_lookup:
            q_err = self.single_qubit_lookup[s_tuple]
            e_hat = np.zeros(self.n, dtype=np.uint8)
            e_hat[q_err] = 1
            t_elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
            return DecodingResult(
                syndrome=list(syndrome),
                predicted_error=e_hat.tolist(),
                syndrome_verified=True,
                residual_syndrome=[0] * self.m,
                latency_microseconds=t_elapsed_us,
                confidence=0.99,
            )

        # 2. Neural feed-forward pass
        h1 = np.maximum(0.0, s_arr @ self.w1 + self.b1)
        logits = h1 @ self.w2 + self.b2
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -15.0, 15.0)))[0]

        e_hat = (probs >= threshold).astype(np.uint8)

        # Verify syndrome consistency: H @ e_hat == s (mod 2)
        calc_s = (self.h @ e_hat) % 2
        residual = (calc_s ^ np.asarray(syndrome, dtype=np.uint8)) % 2
        verified = bool(np.all(residual == 0))

        # If not verified and multi-bit error detected, greedy flip optimization
        if not verified:
            # Sort candidate bits by marginal probability
            ranked_bits = np.argsort(probs)[::-1]
            for bit in ranked_bits[:4]:
                trial_e = e_hat.copy()
                trial_e[bit] ^= 1
                if np.all((self.h @ trial_e) % 2 == np.asarray(syndrome, dtype=np.uint8)):
                    e_hat = trial_e
                    residual = np.zeros(self.m, dtype=np.uint8)
                    verified = True
                    break

        t_elapsed_us = (time.perf_counter_ns() - t0) / 1000.0

        return DecodingResult(
            syndrome=list(syndrome),
            predicted_error=e_hat.tolist(),
            syndrome_verified=verified,
            residual_syndrome=residual.tolist(),
            latency_microseconds=t_elapsed_us,
            confidence=float(np.mean(np.where(e_hat == 1, probs, 1.0 - probs))),
        )


@dataclass
class PauliFrameTracker:
    """
    Maintains the classical Pauli frame in memory during QPU pulse execution.
    Tracks physical bit flips (X) and phase flips (Z) across all qubits.
    """
    n_qubits: int
    frame_x: np.ndarray = field(init=False)
    frame_z: np.ndarray = field(init=False)
    update_count: int = field(default=0, init=False)

    def __post_init__(self):
        self.frame_x = np.zeros(self.n_qubits, dtype=np.uint8)
        self.frame_z = np.zeros(self.n_qubits, dtype=np.uint8)

    def apply_correction(self, err_x: Optional[Sequence[int]] = None, err_z: Optional[Sequence[int]] = None):
        """Updates frame: frame = frame ^ correction."""
        if err_x is not None:
            self.frame_x ^= np.asarray(err_x, dtype=np.uint8)
        if err_z is not None:
            self.frame_z ^= np.asarray(err_z, dtype=np.uint8)
        self.update_count += 1

    def get_pauli_string(self) -> str:
        """Returns string representation of current Pauli frame (e.g. 'IXZIIYI')."""
        labels = []
        for q in range(self.n_qubits):
            x = self.frame_x[q]
            z = self.frame_z[q]
            if x == 0 and z == 0:
                labels.append("I")
            elif x == 1 and z == 0:
                labels.append("X")
            elif x == 0 and z == 1:
                labels.append("Z")
            else:
                labels.append("Y")
        return "".join(labels)

    def reset(self):
        """Resets frame to identity."""
        self.frame_x.fill(0)
        self.frame_z.fill(0)
        self.update_count = 0
