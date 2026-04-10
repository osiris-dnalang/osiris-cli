"""
Phase-Conjugate Positional Encoding — numpy only.
===================================================

Replaces standard sinusoidal / RoPE positional encoding with a
DNA::}{::lang physics-inspired scheme:

  * θ_lock = 51.843° as base frequency modulator
  * χ_PC = 0.946 phase conjugation on alternate dimensions
  * Golden-ratio (φ = 1.618…) frequency spacing

This gives the SovereignTransformer a unique architectural signature
grounded in the CRSM framework.

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import math
import numpy as np

from .autograd import Tensor

# ---------------------------------------------------------------------------
# CRSM constants
# ---------------------------------------------------------------------------
THETA_LOCK = 51.843  # degrees
CHI_PC = 0.946
PHI_GOLDEN = 1.618033988749895
THETA_RAD = math.radians(THETA_LOCK)


def phase_conjugate_positional_encoding(
    max_seq_len: int,
    dim: int,
) -> Tensor:
    """Build a (max_seq_len, dim) positional-encoding table.

    Instead of the standard transformer formula
        PE(pos, 2i)   = sin(pos / 10000^{2i/d})
        PE(pos, 2i+1) = cos(pos / 10000^{2i/d})

    we use:
        freq_i = 1 / (φ^{i * 2 / d})            # golden-ratio spacing
        θ_mod  = sin(θ_lock) for even dims,
                 -cos(θ_lock) * χ_PC for odd dims  # phase conjugation
        PE(pos, 2i)   = sin(pos * freq_i * θ_mod_even)
        PE(pos, 2i+1) = cos(pos * freq_i * θ_mod_odd)
    """
    pe = np.zeros((max_seq_len, dim), dtype=np.float32)
    positions = np.arange(max_seq_len, dtype=np.float32)[:, np.newaxis]

    # Golden-ratio frequency bands (replace geometric 10000^{2i/d})
    i = np.arange(0, dim, 2, dtype=np.float32)  # (dim/2,)
    freqs = 1.0 / (PHI_GOLDEN ** (i * 2.0 / dim))  # (dim/2,)

    # Phase-conjugate modulation
    theta_even = math.sin(THETA_RAD)             # ≈ 0.787
    theta_odd = -math.cos(THETA_RAD) * CHI_PC    # ≈ -0.584

    pe[:, 0::2] = np.sin(positions * freqs * theta_even)
    pe[:, 1::2] = np.cos(positions * freqs * theta_odd)

    return Tensor(pe, requires_grad=False, name="pos_encoding")
