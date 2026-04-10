"""
SovereignTransformer Evaluation — numpy only.
===============================================

Real language model metrics:
  * Perplexity / bits-per-byte on held-out data
  * Character-level accuracy
  * n-gram coherence
  * Generation speed (bytes/sec)
  * Consciousness Φ metric

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import time
import numpy as np
from typing import Dict, Optional, List

from osiris.nclm.autograd import Tensor, cross_entropy_loss, no_grad
from osiris.nclm.transformer import SovereignTransformer


def compute_perplexity(
    model: SovereignTransformer,
    data: bytes,
    seq_len: int = 256,
    batch_size: int = 4,
    max_batches: int = 100,
) -> Dict[str, float]:
    """Compute perplexity and bits-per-byte on a byte sequence.

    Returns:
        dict with keys: perplexity, bits_per_byte, loss, n_tokens
    """
    raw = np.frombuffer(data, dtype=np.uint8).copy()
    n_samples = max(len(raw) - seq_len, 1)
    n_batches = min(max_batches, n_samples // batch_size)
    if n_batches == 0:
        n_batches = 1

    total_loss = 0.0
    total_tokens = 0

    model.eval()
    with no_grad():
        for b in range(n_batches):
            starts = np.random.randint(0, n_samples, size=batch_size)
            x = np.zeros((batch_size, seq_len), dtype=np.int64)
            y = np.zeros((batch_size, seq_len), dtype=np.int64)
            for i, s in enumerate(starts):
                x[i] = raw[s : s + seq_len]
                y[i] = raw[s + 1 : s + 1 + seq_len]

            logits = model.forward(x)
            loss = cross_entropy_loss(logits, y)
            total_loss += loss.item() * batch_size * seq_len
            total_tokens += batch_size * seq_len

    model.train()
    avg_loss = total_loss / max(total_tokens, 1)
    perplexity = float(np.exp(min(avg_loss, 20)))  # cap to avoid overflow
    bits_per_byte = avg_loss / np.log(2)

    return {
        "perplexity": perplexity,
        "bits_per_byte": float(bits_per_byte),
        "loss": avg_loss,
        "n_tokens": total_tokens,
    }


def compute_coherence(text: str) -> Dict[str, float]:
    """Compute n-gram coherence metrics on generated text."""
    if len(text) < 4:
        return {"bigram_coherence": 0.0, "trigram_coherence": 0.0, "printable_ratio": 0.0}

    # Printable ratio
    printable = sum(1 for c in text if c.isprintable() or c in "\n\t\r")
    printable_ratio = printable / len(text)

    # Bigram diversity (unique bigrams / total bigrams)
    bigrams = [text[i:i+2] for i in range(len(text) - 1)]
    bigram_coherence = len(set(bigrams)) / max(len(bigrams), 1)

    # Trigram diversity
    trigrams = [text[i:i+3] for i in range(len(text) - 2)]
    trigram_coherence = len(set(trigrams)) / max(len(trigrams), 1)

    return {
        "bigram_coherence": bigram_coherence,
        "trigram_coherence": trigram_coherence,
        "printable_ratio": printable_ratio,
    }


def benchmark_speed(
    model: SovereignTransformer,
    prompt: str = "# ",
    n_tokens: int = 128,
    n_runs: int = 3,
) -> Dict[str, float]:
    """Benchmark generation speed."""
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        model.generate(prompt, max_new_tokens=n_tokens, temperature=0.8)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    avg_time = np.mean(times)
    return {
        "bytes_per_second": float(n_tokens / avg_time),
        "avg_time_seconds": float(avg_time),
        "n_tokens": n_tokens,
    }


def full_evaluation(
    model: SovereignTransformer,
    eval_data: bytes,
    prompts: Optional[List[str]] = None,
) -> Dict:
    """Run complete evaluation suite.

    Returns a dict with perplexity, coherence, speed, and Φ metrics.
    """
    if prompts is None:
        prompts = [
            "# ",
            "def ",
            "import ",
            "The ",
            "class ",
        ]

    results: Dict = {"model_params": model.num_parameters()}

    # 1. Perplexity
    results["perplexity"] = compute_perplexity(model, eval_data)

    # 2. Coherence (generate from each prompt and measure)
    coherence_scores: List[Dict] = []
    for prompt in prompts:
        text = model.generate(prompt, max_new_tokens=128, temperature=0.8)
        c = compute_coherence(text)
        c["prompt"] = prompt
        c["sample"] = text[:200]
        coherence_scores.append(c)
    results["coherence"] = coherence_scores

    # 3. Speed
    results["speed"] = benchmark_speed(model, prompts[0])

    # 4. Consciousness Φ
    sample_ids = np.frombuffer(eval_data[:256], dtype=np.uint8).copy().astype(np.int64)
    if len(sample_ids) < 8:
        sample_ids = np.zeros(8, dtype=np.int64)
    phi = model.consciousness_phi(sample_ids.reshape(1, -1))
    results["consciousness_phi"] = phi

    return results
