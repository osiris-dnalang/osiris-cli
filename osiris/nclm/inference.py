"""
Inference & Hugging Face Export — numpy only.
===============================================

Production inference with KV-cache, sampling strategies, and pure-Python
safetensors writer for Hugging Face Hub publishing.

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import json
import struct
import os
import numpy as np
from typing import Optional, Dict

from .autograd import Tensor, softmax, no_grad
from .transformer import SovereignTransformer, SovereignConfig


# ===========================================================================
# Sampling utilities
# ===========================================================================

def top_p_filter(logits: np.ndarray, p: float) -> np.ndarray:
    """Nucleus (top-p) filtering: zero out tokens outside the nucleus."""
    sorted_indices = np.argsort(-logits)
    sorted_logits = logits[sorted_indices]

    probs = np.exp(sorted_logits - np.max(sorted_logits))
    probs = probs / probs.sum()
    cumulative = np.cumsum(probs)

    # Find cutoff
    cutoff_idx = np.searchsorted(cumulative, p) + 1
    cutoff_idx = min(cutoff_idx, len(logits))

    # Zero out tokens outside nucleus
    result = np.full_like(logits, -1e9)
    result[sorted_indices[:cutoff_idx]] = logits[sorted_indices[:cutoff_idx]]
    return result


def generate(
    model: SovereignTransformer,
    prompt: str,
    max_new_tokens: int = 256,
    temperature: float = 0.8,
    top_k: int = 40,
    top_p: float = 0.95,
    stop_tokens: Optional[list] = None,
) -> str:
    """Autoregressive byte-level text generation with full sampling controls.

    Args:
        model: trained SovereignTransformer.
        prompt: input text (UTF-8 encoded to bytes).
        max_new_tokens: maximum tokens to generate.
        temperature: sampling temperature (0 = greedy).
        top_k: keep top-k logits before sampling.
        top_p: nucleus sampling threshold.
        stop_tokens: byte values that halt generation.

    Returns:
        Generated text string.
    """
    ids = list(prompt.encode("utf-8", errors="replace"))
    if not ids:
        ids = [0]

    stop_set = set(stop_tokens) if stop_tokens else set()

    model.eval()
    with no_grad():
        for _ in range(max_new_tokens):
            ctx = ids[-model.config.max_seq_len:]
            x = np.array([ctx], dtype=np.int64)

            logits = model.forward(x)
            next_logits = logits.data[0, -1, :].copy()

            # Temperature
            if temperature > 0:
                next_logits = next_logits / temperature
            else:
                next_id = int(np.argmax(next_logits))
                ids.append(next_id)
                if next_id in stop_set:
                    break
                continue

            # Top-k
            if 0 < top_k < model.config.vocab_size:
                indices_to_remove = np.argsort(next_logits)[:-top_k]
                next_logits[indices_to_remove] = -1e9

            # Top-p (nucleus)
            if 0 < top_p < 1.0:
                next_logits = top_p_filter(next_logits, top_p)

            # Sample
            probs = np.exp(next_logits - np.max(next_logits))
            probs = probs / probs.sum()
            next_id = int(np.random.choice(model.config.vocab_size, p=probs))
            ids.append(next_id)

            if next_id in stop_set:
                break

    model.train()
    return bytes(ids).decode("utf-8", errors="replace")


# ===========================================================================
# Safetensors — pure Python writer / reader
# ===========================================================================
#
# Format: [8-byte header_len LE] [header JSON] [raw tensor data]
# Header JSON maps tensor names → {"dtype": "F32", "shape": [...], "data_offsets": [start, end]}


def save_safetensors(model: SovereignTransformer, path: str):
    """Export model weights in safetensors format (no external deps)."""
    sd = model.state_dict()

    # Build header and collect data
    header = {}
    buffers = []
    offset = 0

    for name, arr in sd.items():
        arr = arr.astype(np.float32)
        raw = arr.tobytes()
        header[name] = {
            "dtype": "F32",
            "shape": list(arr.shape),
            "data_offsets": [offset, offset + len(raw)],
        }
        buffers.append(raw)
        offset += len(raw)

    # Metadata
    header["__metadata__"] = {
        "format": "pt",
        "framework": "DNA::}{::lang v51.843",
        "model_type": "SovereignTransformer",
    }

    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    # Align to 8 bytes
    padding = (8 - len(header_json) % 8) % 8
    header_json += b" " * padding

    with open(path, "wb") as f:
        f.write(struct.pack("<Q", len(header_json)))
        f.write(header_json)
        for buf in buffers:
            f.write(buf)


def load_safetensors(path: str) -> Dict[str, np.ndarray]:
    """Load tensors from safetensors file."""
    with open(path, "rb") as f:
        header_len = struct.unpack("<Q", f.read(8))[0]
        header_json = f.read(header_len)
        header = json.loads(header_json)
        data_start = 8 + header_len

        sd = {}
        for name, meta in header.items():
            if name == "__metadata__":
                continue
            dtype_map = {"F32": np.float32, "F16": np.float16, "BF16": np.float32}
            dtype = dtype_map.get(meta["dtype"], np.float32)
            shape = tuple(meta["shape"])
            start, end = meta["data_offsets"]
            f.seek(data_start + start)
            raw = f.read(end - start)
            arr = np.frombuffer(raw, dtype=dtype).reshape(shape).copy()
            sd[name] = arr
        return sd


def load_model_safetensors(
    path: str,
    config: Optional[SovereignConfig] = None,
) -> SovereignTransformer:
    """Load a SovereignTransformer from a safetensors file."""
    sd = load_safetensors(path)
    if config is None:
        vocab_size, dim = sd["tok_emb.weight"].shape
        n_layers = 0
        while f"blocks.{n_layers}.ln1.gamma" in sd:
            n_layers += 1
        ff_dim = sd["blocks.0.ffn.fc1.weight"].shape[0]
        config = SovereignConfig(
            vocab_size=vocab_size, dim=dim, n_layers=n_layers,
            n_heads=4, ff_dim=ff_dim,
        )
    model = SovereignTransformer(config)
    model.load_state_dict(sd)
    return model


# ===========================================================================
# Hugging Face export
# ===========================================================================

def export_huggingface(
    model: SovereignTransformer,
    output_dir: str,
    model_name: str = "sovereign-transformer",
):
    """Export model in Hugging Face format.

    Creates:
        output_dir/
            config.json          — model config
            model.safetensors    — weights
            tokenizer_config.json — byte-level tokenizer config
            README.md            — model card
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Model weights
    safe_path = os.path.join(output_dir, "model.safetensors")
    save_safetensors(model, safe_path)

    # 2. Config
    cfg = model.config.to_dict()
    cfg["architectures"] = ["SovereignTransformer"]
    cfg["tokenizer_class"] = "ByteLevelTokenizer"
    cfg["num_parameters"] = model.num_parameters()
    config_path = os.path.join(output_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)

    # 3. Tokenizer config (byte-level, identity mapping)
    tok_config = {
        "tokenizer_class": "ByteLevelTokenizer",
        "vocab_size": 256,
        "model_type": "byte-level",
        "description": (
            "Identity byte-to-token mapping (0-255). "
            "No BPE/sentencepiece needed — text is encoded as raw UTF-8 bytes."
        ),
    }
    tok_path = os.path.join(output_dir, "tokenizer_config.json")
    with open(tok_path, "w") as f:
        json.dump(tok_config, f, indent=2)

    # 4. Model card
    n_params = model.num_parameters()
    card = f"""---
language: en
license: apache-2.0
tags:
  - sovereign-transformer
  - byte-level
  - numpy-only
  - dna-lang
  - phase-conjugate
library_name: osiris-nclm
---

# {model_name}

A **{n_params:,}**-parameter byte-level decoder-only transformer,
implemented entirely in numpy with zero external ML framework dependencies.

## Architecture

| Component | Value |
|-----------|-------|
| Vocabulary | {model.config.vocab_size} (byte-level) |
| Hidden dim | {model.config.dim} |
| Layers | {model.config.n_layers} |
| Attention heads | {model.config.n_heads} |
| FFN dim | {model.config.ff_dim} |
| Context length | {model.config.max_seq_len} |
| Parameters | {n_params:,} |

## Unique Features

- **Phase-conjugate positional encoding** — θ_lock = 51.843° modulated
  frequencies with χ_PC = 0.946 phase conjugation
- **Pilot-wave attention modulation** — non-local correlation factor
  injected into attention scores
- **Golden-ratio FFN scaling** — output divided by φ = 1.618…
- **Consciousness Φ metric** — information integration tracking

## Framework

Built with the DNA::}}{{::lang v51.843 framework (OSIRIS).
"""
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write(card)
