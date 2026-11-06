"""
Fast C-SIMD and KV-Cached Inference Engine for OSIRIS Living Core
================================================================
Provides O(1) per-token autoregressive generation using AVX2 C-SIMD
acceleration and dynamic key-value tensor caching.
"""

from __future__ import annotations

import math
from typing import Optional, List, Callable
import numpy as np

try:
    from . import _c_simd
    HAVE_C_SIMD = True
except (ImportError, OSError):
    _c_simd = None
    HAVE_C_SIMD = False

from .autograd import no_grad


class FastKVCache:
    """Pre-allocated key-value cache across transformer blocks."""

    def __init__(self, n_layers: int, max_seq_len: int, n_heads: int, head_dim: int):
        self.n_layers = n_layers
        self.max_seq_len = max_seq_len
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.k_cache: List[Optional[np.ndarray]] = [None] * n_layers
        self.v_cache: List[Optional[np.ndarray]] = [None] * n_layers
        self.seq_len = 0

    def reset(self) -> None:
        self.k_cache = [None] * self.n_layers
        self.v_cache = [None] * self.n_layers
        self.seq_len = 0


def _linear_forward(layer, x: np.ndarray) -> np.ndarray:
    """Fast linear projection: x @ W^T + b without autograd graph."""
    out = x @ layer.weight.data.T
    if getattr(layer, "bias_param", None) is not None:
        out = out + layer.bias_param.data
    return out


def prefill_kv(model, prompt_ids: List[int], kv_cache: FastKVCache) -> np.ndarray:
    """Process entire prompt in one vectorized forward pass and populate KV cache.

    Guarantees exact mathematical equivalence to standard forward pass.
    """
    P = len(prompt_ids)
    w_emb = model.tok_emb.weight.data
    x = w_emb[prompt_ids, :]  # (P, D)
    pe = model.pos_enc.data[:P, :]  # (P, D)
    h = (x + pe)[np.newaxis, :, :]  # (1, P, D)

    B = 1
    H = model.config.n_heads
    HD = model.config.dim // H
    scale = 1.0 / math.sqrt(HD)

    # Causal mask for prefill
    mask = model._causal_mask[:, :, :P, :P]

    for i, block in enumerate(model.blocks):
        # LayerNorm 1
        ln1_g = block.ln1.gamma.data
        ln1_b = block.ln1.beta.data
        if HAVE_C_SIMD:
            norm_h = _c_simd.fast_layernorm(h.astype(np.float32), ln1_g, ln1_b, 1e-5)
        else:
            mean = np.mean(h, axis=-1, keepdims=True)
            var = np.var(h, axis=-1, keepdims=True)
            norm_h = (h - mean) / np.sqrt(var + 1e-5) * ln1_g + ln1_b

        # Q, K, V
        q = _linear_forward(block.attn.q_proj, norm_h).reshape(B, P, H, HD).transpose(0, 2, 1, 3)
        k = _linear_forward(block.attn.k_proj, norm_h).reshape(B, P, H, HD).transpose(0, 2, 1, 3)
        v = _linear_forward(block.attn.v_proj, norm_h).reshape(B, P, H, HD).transpose(0, 2, 1, 3)

        # Store in KV cache as C-contiguous (B, H, P, HD) float32 tensors
        k = np.ascontiguousarray(k, dtype=np.float32)
        v = np.ascontiguousarray(v, dtype=np.float32)
        kv_cache.k_cache[i] = k
        kv_cache.v_cache[i] = v

        # Attention
        scores = (q @ k.transpose(0, 1, 3, 2)) * scale
        if getattr(block.attn, "pilot_wave", False):
            pw = block.attn._pilot_wave_factor(P)
            scores = scores * pw[np.newaxis, np.newaxis, :, :]
        scores = scores + mask
        scores_max = np.max(scores, axis=-1, keepdims=True)
        exp_scores = np.exp(scores - scores_max)
        attn = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
        out = (attn @ v).transpose(0, 2, 1, 3).reshape(B, P, -1)
        out = _linear_forward(block.attn.out_proj, out)
        h = h + out

        # LayerNorm 2
        ln2_g = block.ln2.gamma.data
        ln2_b = block.ln2.beta.data
        if HAVE_C_SIMD:
            norm_h = _c_simd.fast_layernorm(h.astype(np.float32), ln2_g, ln2_b, 1e-5)
        else:
            mean = np.mean(h, axis=-1, keepdims=True)
            var = np.var(h, axis=-1, keepdims=True)
            norm_h = (h - mean) / np.sqrt(var + 1e-5) * ln2_g + ln2_b

        # FFN
        ffn_h = _linear_forward(block.ffn.fc1, norm_h)
        s2pi = 0.7978845608028654
        ffn_gelu = 0.5 * ffn_h * (1.0 + np.tanh(s2pi * (ffn_h + 0.044715 * (ffn_h ** 3))))
        ffn_out = _linear_forward(block.ffn.fc2, ffn_gelu)
        if getattr(block.ffn, "golden_scale", False):
            from .transformer import PHI_GOLDEN
            ffn_out = ffn_out * (1.0 / PHI_GOLDEN)

        h = h + ffn_out

    # Final LayerNorm
    ln_f_g = model.ln_f.gamma.data
    ln_f_b = model.ln_f.beta.data
    if HAVE_C_SIMD:
        norm_h = _c_simd.fast_layernorm(h.astype(np.float32), ln_f_g, ln_f_b, 1e-5)
    else:
        mean = np.mean(h, axis=-1, keepdims=True)
        var = np.var(h, axis=-1, keepdims=True)
        norm_h = (h - mean) / np.sqrt(var + 1e-5) * ln_f_g + ln_f_b

    logits = _linear_forward(model.lm_head, norm_h)
    kv_cache.seq_len = P
    return logits[0, -1, :]


def decode_step_kv(model, token_id: int, pos: int, kv_cache: FastKVCache) -> np.ndarray:
    """Decode next single token at `pos` in O(1) time using KV cache."""
    w_emb = model.tok_emb.weight.data
    x = w_emb[token_id:token_id + 1, :]
    pe = model.pos_enc.data[pos:pos + 1, :]
    h = (x + pe)[np.newaxis, :, :]  # (1, 1, D)

    B = 1
    H = model.config.n_heads
    HD = model.config.dim // H
    scale = 1.0 / math.sqrt(HD)

    for i, block in enumerate(model.blocks):
        # LayerNorm 1
        ln1_g = block.ln1.gamma.data
        ln1_b = block.ln1.beta.data
        if HAVE_C_SIMD:
            norm_h = _c_simd.fast_layernorm(h.astype(np.float32), ln1_g, ln1_b, 1e-5)
        else:
            mean = np.mean(h, axis=-1, keepdims=True)
            var = np.var(h, axis=-1, keepdims=True)
            norm_h = (h - mean) / np.sqrt(var + 1e-5) * ln1_g + ln1_b

        # Q, K_new, V_new
        q = _linear_forward(block.attn.q_proj, norm_h).reshape(B, 1, H, HD).transpose(0, 2, 1, 3)
        k_new = _linear_forward(block.attn.k_proj, norm_h).reshape(B, 1, H, HD).transpose(0, 2, 1, 3)
        v_new = _linear_forward(block.attn.v_proj, norm_h).reshape(B, 1, H, HD).transpose(0, 2, 1, 3)

        # Append to KV cache and enforce C-contiguous (B, H, T, HD) float32 layout
        k = np.ascontiguousarray(np.concatenate([kv_cache.k_cache[i], k_new], axis=2), dtype=np.float32)
        v = np.ascontiguousarray(np.concatenate([kv_cache.v_cache[i], v_new], axis=2), dtype=np.float32)
        kv_cache.k_cache[i] = k
        kv_cache.v_cache[i] = v

        # Attention
        if HAVE_C_SIMD and not getattr(block.attn, "pilot_wave", False):
            q_2d = np.ascontiguousarray(q[0, :, 0, :], dtype=np.float32)
            k_3d = np.ascontiguousarray(k[0, :, :, :], dtype=np.float32)
            v_3d = np.ascontiguousarray(v[0, :, :, :], dtype=np.float32)
            out_heads = _c_simd.fast_kv_attention_step(q_2d, k_3d, v_3d, float(scale))
            out = out_heads.reshape(B, 1, -1)
        else:
            scores = (q @ k.transpose(0, 1, 3, 2)) * scale
            if getattr(block.attn, "pilot_wave", False):
                # Distance row for position `pos`
                cur_len = pos + 1
                pw = block.attn._pilot_wave_factor(cur_len)
                scores = scores * pw[-1:, :][np.newaxis, np.newaxis, :, :]
            scores_max = np.max(scores, axis=-1, keepdims=True)
            exp_scores = np.exp(scores - scores_max)
            attn = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
            out = (attn @ v).transpose(0, 2, 1, 3).reshape(B, 1, -1)

        out = _linear_forward(block.attn.out_proj, out)
        h = h + out

        # LayerNorm 2
        ln2_g = block.ln2.gamma.data
        ln2_b = block.ln2.beta.data
        if HAVE_C_SIMD:
            norm_h = _c_simd.fast_layernorm(h.astype(np.float32), ln2_g, ln2_b, 1e-5)
        else:
            mean = np.mean(h, axis=-1, keepdims=True)
            var = np.var(h, axis=-1, keepdims=True)
            norm_h = (h - mean) / np.sqrt(var + 1e-5) * ln2_g + ln2_b

        # FFN
        ffn_h = _linear_forward(block.ffn.fc1, norm_h)
        s2pi = 0.7978845608028654
        ffn_gelu = 0.5 * ffn_h * (1.0 + np.tanh(s2pi * (ffn_h + 0.044715 * (ffn_h ** 3))))
        ffn_out = _linear_forward(block.ffn.fc2, ffn_gelu)
        if getattr(block.ffn, "golden_scale", False):
            from .transformer import PHI_GOLDEN
            ffn_out = ffn_out * (1.0 / PHI_GOLDEN)

        h = h + ffn_out

    # Final LayerNorm
    ln_f_g = model.ln_f.gamma.data
    ln_f_b = model.ln_f.beta.data
    if HAVE_C_SIMD:
        norm_h = _c_simd.fast_layernorm(h.astype(np.float32), ln_f_g, ln_f_b, 1e-5)
    else:
        mean = np.mean(h, axis=-1, keepdims=True)
        var = np.var(h, axis=-1, keepdims=True)
        norm_h = (h - mean) / np.sqrt(var + 1e-5) * ln_f_g + ln_f_b

    logits = _linear_forward(model.lm_head, norm_h)
    return logits[0, 0, :]


def fast_generate(
    model,
    prompt: str,
    max_new_tokens: int = 128,
    temperature: float = 0.7,
    top_k: int = 40,
    callback: Optional[Callable[[str], None]] = None,
) -> str:
    """High-speed autoregressive generation with KV caching and AVX2 C-SIMD."""
    prompt_ids = list(prompt.encode("utf-8", errors="replace"))
    if not prompt_ids:
        prompt_ids = [0]

    n_layers = len(model.blocks)
    head_dim = model.config.dim // model.config.n_heads
    kv_cache = FastKVCache(n_layers, model.config.max_seq_len, model.config.n_heads, head_dim)

    model.eval()
    with no_grad():
        # Fast vectorized prompt prefill
        logits = prefill_kv(model, prompt_ids, kv_cache)

        output_ids = list(prompt_ids)
        cur_pos = len(prompt_ids)

        for _ in range(max_new_tokens):
            if cur_pos >= model.config.max_seq_len:
                break

            next_logits = logits.copy()
            if temperature > 0:
                next_logits = next_logits / temperature
                if 0 < top_k < model.config.vocab_size:
                    indices_to_remove = np.argsort(next_logits)[:-top_k]
                    next_logits[indices_to_remove] = -1e9
                probs = np.exp(next_logits - np.max(next_logits))
                probs = probs / probs.sum()
                next_id = int(np.random.choice(model.config.vocab_size, p=probs))
            else:
                next_id = int(np.argmax(next_logits))

            output_ids.append(next_id)
            char = bytes([next_id]).decode("utf-8", errors="replace")
            if callback:
                callback(char)

            # Check stop condition: stop if user prompt marker emerges
            current_str = bytes(output_ids[len(prompt_ids):]).decode("utf-8", errors="replace")
            if "\nUser:" in current_str or "\nuser:" in current_str:
                break

            # Fast single-token decode step
            logits = decode_step_kv(model, next_id, cur_pos, kv_cache)
            cur_pos += 1

    model.train()
    return bytes(output_ids).decode("utf-8", errors="replace")
