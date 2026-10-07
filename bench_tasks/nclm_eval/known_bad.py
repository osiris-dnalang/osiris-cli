
import math
from typing import Callable, List, Dict, Union, Optional


def compute_unigram_probs(train_bytes: bytes, smoothing: float = 1.0) -> Dict[int, float]:
    counts = [0] * 256
    for b in train_bytes:
        counts[b] += 1
    total = len(train_bytes) + smoothing * 256
    return {b: (counts[b] + smoothing) / total for b in range(256)}


def compute_unigram_loss(
    train_data: Union[bytes, List[bytes]],
    test_data: Union[bytes, List[bytes]],
    smoothing: float = 1.0
) -> float:
    train_bytes = b"".join(train_data) if isinstance(train_data, list) else train_data
    test_bytes = b"".join(test_data) if isinstance(test_data, list) else test_data

    if not test_bytes:
        return 0.0

    probs = compute_unigram_probs(train_bytes, smoothing=smoothing)
    total_neg_log_prob = 0.0
    for b in test_bytes:
        total_neg_log_prob -= math.log2(probs[b])

    return total_neg_log_prob / len(test_bytes)


def evaluate_held_out(
    exchanges: List[bytes],
    split_ratio: float = 0.8,
    nclm_eval_fn: Optional[Callable[[bytes, bytes], float]] = None
) -> Dict[str, float]:
    split_idx = int(len(exchanges) * split_ratio)
    train_exchanges = exchanges[:split_idx]
    test_exchanges = exchanges[split_idx:]

    train_bytes = b"".join(train_exchanges)
    test_bytes = b"".join(test_exchanges)

    unigram_loss = compute_unigram_loss(train_bytes, test_bytes)

    nclm_loss = 0.0
    if nclm_eval_fn is not None:
        nclm_loss = nclm_eval_fn(train_bytes, test_bytes)

    return {
        "unigram_loss": unigram_loss,
        "nclm_loss": nclm_loss,
        "unigram_advantage": unigram_loss - nclm_loss,
        "train_size_bytes": float(len(train_bytes)),
        "test_size_bytes": float(len(test_bytes)),
    }
