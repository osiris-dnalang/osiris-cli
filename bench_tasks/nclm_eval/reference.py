#!/usr/bin/env python3
"""
nclm_eval.py -- held-out evaluation of Engine 3 (osiris.nclm) against a
unigram byte baseline. This is the measurement behind Living Language Model
level L1 ("learns"): until held-out NCLM loss beats this baseline, the
NCLM gets no influence over anything.

All losses are mean negative log-likelihood per byte in NATS (natural log),
the same unit osiris.nclm's cross_entropy_loss reports. The story #20
version (commit 7df018a) scored the baseline in bits but the NCLM in nats,
which inflated the baseline 1.44x in the NCLM's favor, and returned an NCLM
loss of 0.0 -- a perfect score -- when no model was supplied at all.
"""
import math
from typing import Callable, Dict, List, Union


def compute_unigram_probs(train_bytes: bytes, smoothing: float = 1.0) -> Dict[int, float]:
    """Laplace-smoothed byte frequencies; every byte gets nonzero mass."""
    counts = [0] * 256
    for b in train_bytes:
        counts[b] += 1
    total = len(train_bytes) + smoothing * 256
    return {b: (counts[b] + smoothing) / total for b in range(256)}


def compute_unigram_loss(
    train_data: Union[bytes, List[bytes]],
    test_data: Union[bytes, List[bytes]],
    smoothing: float = 1.0,
) -> float:
    """Mean NLL per byte of test_data under a unigram model fit on
    train_data, in nats. Raises ValueError on an empty test set -- a loss of
    0.0 would read as a perfect score."""
    train_bytes = b"".join(train_data) if isinstance(train_data, list) else train_data
    test_bytes = b"".join(test_data) if isinstance(test_data, list) else test_data
    if not test_bytes:
        raise ValueError("empty test set: there is nothing to evaluate")

    probs = compute_unigram_probs(train_bytes, smoothing=smoothing)
    total_neg_log_prob = 0.0
    for b in test_bytes:
        total_neg_log_prob -= math.log(probs[b])
    return total_neg_log_prob / len(test_bytes)


def evaluate_held_out(
    exchanges: List[bytes],
    nclm_eval_fn: Callable[[bytes, bytes], float],
    split_ratio: float = 0.8,
) -> Dict[str, float]:
    """Fixed, order-preserving split: the first split_ratio of exchanges is
    train, the rest held out. nclm_eval_fn(train_bytes, test_bytes) must
    return the NCLM's mean NLL per held-out byte IN NATS. It is required --
    there is no meaningful comparison without a model."""
    if nclm_eval_fn is None:
        raise ValueError("nclm_eval_fn is required: an evaluation with no model has no NCLM loss")
    split_idx = int(len(exchanges) * split_ratio)
    train_bytes = b"".join(exchanges[:split_idx])
    test_bytes = b"".join(exchanges[split_idx:])

    unigram_loss = compute_unigram_loss(train_bytes, test_bytes)
    nclm_loss = float(nclm_eval_fn(train_bytes, test_bytes))
    if not math.isfinite(nclm_loss) or nclm_loss < 0:
        raise ValueError(f"nclm_eval_fn returned an invalid loss: {nclm_loss!r}")

    return {
        "unit": "nats_per_byte",
        "unigram_loss": unigram_loss,
        "nclm_loss": nclm_loss,
        # Positive means the NCLM beat the baseline.
        "nclm_advantage": unigram_loss - nclm_loss,
        "uniform_loss": math.log(256),
        "train_size_bytes": float(len(train_bytes)),
        "test_size_bytes": float(len(test_bytes)),
    }
