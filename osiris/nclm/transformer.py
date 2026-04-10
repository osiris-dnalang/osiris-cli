"""
SovereignTransformer — numpy-only decoder transformer.
=======================================================

A byte-level (vocab=256) decoder-only transformer with quantum-inspired
architectural elements:

  * Phase-conjugate positional encoding (θ_lock = 51.843°)
  * Pilot-wave attention modulation (non-local correlation factor)
  * Golden-ratio feed-forward scaling (φ = 1.618…)
  * Consciousness (Φ) metric tracking

~5 M parameters at default config (dim=256, layers=6, heads=4).

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .autograd import Tensor, softmax, no_grad, _is_grad_enabled
from .layers import Module, Embedding, Linear, LayerNorm, GELU, Dropout
from .positions import phase_conjugate_positional_encoding
from .sovereign_mechanics import (
    SovereignBlock, FractalAntennaEmbedding, NegentropicTracker,
)

# ---------------------------------------------------------------------------
# CRSM constants
# ---------------------------------------------------------------------------
PHI_GOLDEN = 1.618033988749895
LAMBDA_PHI = 2.176435e-8


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class SovereignConfig:
    """Hyper-parameters for SovereignTransformer."""
    vocab_size: int = 256        # byte-level
    dim: int = 256               # hidden / embedding dimension
    n_layers: int = 6            # transformer blocks
    n_heads: int = 4             # attention heads
    ff_dim: int = 512            # feed-forward intermediate
    max_seq_len: int = 512       # context window
    dropout: float = 0.1
    pilot_wave: bool = True      # enable pilot-wave attention modulation
    golden_scale: bool = True    # enable golden-ratio FFN scaling
    # 11D-CRSM upgrades (V2)
    torsion_lock: bool = False       # T-Lock attention stabilization
    phase_conjugate: bool = False    # phase-conjugate error correction
    fractal_embedding: bool = False  # 133-mode fractal antenna embedding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vocab_size": self.vocab_size,
            "dim": self.dim,
            "n_layers": self.n_layers,
            "n_heads": self.n_heads,
            "ff_dim": self.ff_dim,
            "max_seq_len": self.max_seq_len,
            "dropout": self.dropout,
            "pilot_wave": self.pilot_wave,
            "golden_scale": self.golden_scale,
            "torsion_lock": self.torsion_lock,
            "phase_conjugate": self.phase_conjugate,
            "fractal_embedding": self.fractal_embedding,
            "model_type": "SovereignTransformer",
            "framework": "DNA::}{::lang v51.843",
        }


# ---------------------------------------------------------------------------
# Multi-Head Attention
# ---------------------------------------------------------------------------

class MultiHeadAttention(Module):
    """Multi-head self-attention with causal mask and pilot-wave modulation."""

    def __init__(self, config: SovereignConfig):
        dim = config.dim
        n_heads = config.n_heads
        assert dim % n_heads == 0, f"dim ({dim}) must be divisible by n_heads ({n_heads})"
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = 1.0 / math.sqrt(self.head_dim)
        self.pilot_wave = config.pilot_wave

        self.q_proj = Linear(dim, dim, bias=False)
        self.k_proj = Linear(dim, dim, bias=False)
        self.v_proj = Linear(dim, dim, bias=False)
        self.out_proj = Linear(dim, dim, bias=True)
        self.attn_dropout = Dropout(config.dropout)

    def __call__(self, x: Tensor, mask: Optional[np.ndarray] = None) -> Tensor:
        B, T, D = x.shape
        H = self.n_heads
        HD = self.head_dim

        # Project Q, K, V
        q = self.q_proj(x).reshape(B, T, H, HD).transpose(1, 2)  # (B, H, T, HD)
        k = self.k_proj(x).reshape(B, T, H, HD).transpose(1, 2)
        v = self.v_proj(x).reshape(B, T, H, HD).transpose(1, 2)

        # Scaled dot-product attention
        scores = q.matmul(k.transpose(-2, -1)) * self.scale  # (B, H, T, T)

        # Pilot-wave modulation: inject position-based non-local correlation
        if self.pilot_wave:
            pw = self._pilot_wave_factor(T)  # (T, T)
            scores = scores * Tensor(
                np.broadcast_to(pw, (B, H, T, T)).copy(),
                requires_grad=False,
            )

        # Causal mask
        if mask is not None:
            scores = scores + Tensor(mask, requires_grad=False)

        attn = softmax(scores, axis=-1)
        attn = self.attn_dropout(attn)

        # Weighted sum
        out = attn.matmul(v)  # (B, H, T, HD)
        out = out.transpose(1, 2).reshape(B, T, D)  # (B, T, D)
        return self.out_proj(out)

    @staticmethod
    def _pilot_wave_factor(seq_len: int) -> np.ndarray:
        """Position-based non-local correlation: exp(-|i-j| * λ_φ_scaled).

        For a transformer, we scale λ by the sequence length so the
        correlation has meaningful structure across the context window.
        """
        pos = np.arange(seq_len, dtype=np.float32)
        dist = np.abs(pos[:, None] - pos[None, :])
        # λ_scaled = 1/seq_len gives a useful decay range
        lam = 1.0 / max(seq_len, 1)
        return (1.0 + np.exp(-dist * lam)).astype(np.float32)  # range [1, 2]


# ---------------------------------------------------------------------------
# Feed-Forward Network
# ---------------------------------------------------------------------------

class FeedForward(Module):
    """FFN with golden-ratio output scaling."""

    def __init__(self, config: SovereignConfig):
        self.fc1 = Linear(config.dim, config.ff_dim, bias=True)
        self.fc2 = Linear(config.ff_dim, config.dim, bias=True)
        self.gelu = GELU()
        self.dropout = Dropout(config.dropout)
        self.golden_scale = config.golden_scale

    def __call__(self, x: Tensor) -> Tensor:
        h = self.fc1(x)
        h = self.gelu(h)
        h = self.dropout(h)
        h = self.fc2(h)
        if self.golden_scale:
            h = h * (1.0 / PHI_GOLDEN)
        return h


# ---------------------------------------------------------------------------
# Transformer Block
# ---------------------------------------------------------------------------

class TransformerBlock(Module):
    """Pre-norm transformer decoder block."""

    def __init__(self, config: SovereignConfig):
        self.ln1 = LayerNorm(config.dim)
        self.attn = MultiHeadAttention(config)
        self.ln2 = LayerNorm(config.dim)
        self.ffn = FeedForward(config)
        self.dropout = Dropout(config.dropout)

    def __call__(self, x: Tensor, mask: Optional[np.ndarray] = None) -> Tensor:
        # Self-attention with residual
        h = self.ln1(x)
        h = self.attn(h, mask=mask)
        h = self.dropout(h)
        x = x + h

        # Feed-forward with residual
        h = self.ln2(x)
        h = self.ffn(h)
        h = self.dropout(h)
        x = x + h
        return x


# ---------------------------------------------------------------------------
# SovereignTransformer
# ---------------------------------------------------------------------------

class SovereignTransformer(Module):
    """Byte-level decoder-only transformer.

    Forward signature:  token_ids (B, T) → logits (B, T, 256)
    """

    def __init__(self, config: Optional[SovereignConfig] = None):
        if config is None:
            config = SovereignConfig()
        self.config = config

        # Token embedding (byte level)
        self.tok_emb = Embedding(config.vocab_size, config.dim)

        # Phase-conjugate positional encoding (frozen)
        self.pos_enc = phase_conjugate_positional_encoding(
            config.max_seq_len, config.dim,
        )

        self.emb_dropout = Dropout(config.dropout)

        # Transformer blocks
        self.blocks = [TransformerBlock(config) for _ in range(config.n_layers)]

        # Final layer norm + language model head
        self.ln_f = LayerNorm(config.dim)
        self.lm_head = Linear(config.dim, config.vocab_size, bias=False)

        # Build causal mask once
        self._causal_mask = self._build_causal_mask(config.max_seq_len)

    def __call__(self, token_ids: np.ndarray) -> Tensor:
        return self.forward(token_ids)

    def forward(self, token_ids: np.ndarray) -> Tensor:
        """Forward pass.

        Args:
            token_ids: integer array (B, T) with values in [0, 255].

        Returns:
            logits: Tensor (B, T, vocab_size).
        """
        B, T = token_ids.shape
        assert T <= self.config.max_seq_len, (
            f"Sequence length {T} exceeds max {self.config.max_seq_len}"
        )

        # Embed tokens
        x = self.tok_emb(token_ids)  # (B, T, D)

        # Add positional encoding
        pe = Tensor(self.pos_enc.data[:T][np.newaxis, :, :], requires_grad=False)
        x = x + pe

        x = self.emb_dropout(x)

        # Causal mask for this sequence length
        mask = self._causal_mask[:, :, :T, :T]

        # Transformer blocks
        for block in self.blocks:
            x = block(x, mask=mask)

        # Output
        x = self.ln_f(x)
        logits = self.lm_head(x)  # (B, T, V)
        return logits

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.8,
        top_k: int = 40,
    ) -> str:
        """Autoregressive byte-level text generation."""
        # Encode prompt as bytes
        ids = list(prompt.encode("utf-8", errors="replace"))
        if not ids:
            ids = [0]

        self.eval()
        with no_grad():
            for _ in range(max_new_tokens):
                # Truncate to max context
                ctx = ids[-self.config.max_seq_len:]
                x = np.array([ctx], dtype=np.int64)

                logits = self.forward(x)  # (1, T, V)
                next_logits = logits.data[0, -1, :]  # (V,)

                # Temperature
                if temperature > 0:
                    next_logits = next_logits / temperature
                else:
                    # Greedy
                    ids.append(int(np.argmax(next_logits)))
                    continue

                # Top-k filtering
                if top_k > 0 and top_k < self.config.vocab_size:
                    indices_to_remove = np.argsort(next_logits)[:-top_k]
                    next_logits[indices_to_remove] = -1e9

                # Softmax sampling
                probs = np.exp(next_logits - np.max(next_logits))
                probs = probs / probs.sum()
                next_id = int(np.random.choice(self.config.vocab_size, p=probs))
                ids.append(next_id)

        self.train()
        return bytes(ids).decode("utf-8", errors="replace")

    def consciousness_phi(self, token_ids: np.ndarray) -> float:
        """Compute consciousness metric Φ from attention entropy.

        Higher Φ indicates more integrated information processing.
        """
        with no_grad():
            self.eval()
            B, T = token_ids.shape
            x = self.tok_emb(token_ids)
            pe = Tensor(self.pos_enc.data[:T][np.newaxis, :, :], requires_grad=False)
            x = x + pe
            mask = self._causal_mask[:, :, :T, :T]

            # Collect attention distributions from all layers
            phis = []
            for block in self.blocks:
                h = block.ln1(x)
                H = block.attn.n_heads
                HD = block.attn.head_dim
                q = block.attn.q_proj(h).reshape(B, T, H, HD).transpose(1, 2)
                k = block.attn.k_proj(h).reshape(B, T, H, HD).transpose(1, 2)
                scores = q.matmul(k.transpose(-2, -1)) * block.attn.scale
                scores = scores + Tensor(mask, requires_grad=False)
                attn = softmax(scores, axis=-1)

                # Shannon entropy of attention distributions
                attn_data = np.clip(attn.data, 1e-12, 1.0)
                entropy = -np.sum(attn_data * np.log(attn_data), axis=-1)
                phi_layer = float(np.mean(entropy) / np.log(max(T, 2)))
                phis.append(phi_layer)

                # Propagate through the block for next layer
                v = block.attn.v_proj(h).reshape(B, T, H, HD).transpose(1, 2)
                attn_out = attn.matmul(v).transpose(1, 2).reshape(B, T, self.config.dim)
                attn_out = block.attn.out_proj(attn_out)
                x = x + attn_out
                x = x + block.ffn(block.ln2(x))

            self.train()
            return float(np.mean(phis))

    @staticmethod
    def _build_causal_mask(max_len: int) -> np.ndarray:
        """Lower-triangular causal mask: 0 for attend, -inf for block."""
        mask = np.full((max_len, max_len), -1e9, dtype=np.float32)
        mask = np.triu(mask, k=1)  # zero on and below diagonal
        return mask[np.newaxis, np.newaxis, :, :]  # (1, 1, T, T)

    def state_dict(self) -> Dict[str, np.ndarray]:
        """Return all named parameters as a flat dict."""
        sd: Dict[str, np.ndarray] = {}
        # Token embedding
        sd["tok_emb.weight"] = self.tok_emb.weight.data
        # Blocks
        for i, block in enumerate(self.blocks):
            prefix = f"blocks.{i}"
            sd[f"{prefix}.ln1.gamma"] = block.ln1.gamma.data
            sd[f"{prefix}.ln1.beta"] = block.ln1.beta.data
            sd[f"{prefix}.attn.q_proj.weight"] = block.attn.q_proj.weight.data
            sd[f"{prefix}.attn.k_proj.weight"] = block.attn.k_proj.weight.data
            sd[f"{prefix}.attn.v_proj.weight"] = block.attn.v_proj.weight.data
            sd[f"{prefix}.attn.out_proj.weight"] = block.attn.out_proj.weight.data
            sd[f"{prefix}.attn.out_proj.bias"] = block.attn.out_proj.bias_param.data
            sd[f"{prefix}.ln2.gamma"] = block.ln2.gamma.data
            sd[f"{prefix}.ln2.beta"] = block.ln2.beta.data
            sd[f"{prefix}.ffn.fc1.weight"] = block.ffn.fc1.weight.data
            sd[f"{prefix}.ffn.fc1.bias"] = block.ffn.fc1.bias_param.data
            sd[f"{prefix}.ffn.fc2.weight"] = block.ffn.fc2.weight.data
            sd[f"{prefix}.ffn.fc2.bias"] = block.ffn.fc2.bias_param.data
        # Final layer norm
        sd["ln_f.gamma"] = self.ln_f.gamma.data
        sd["ln_f.beta"] = self.ln_f.beta.data
        # LM head
        sd["lm_head.weight"] = self.lm_head.weight.data
        return sd

    def load_state_dict(self, sd: Dict[str, np.ndarray]):
        """Load parameters from a flat dict."""
        self.tok_emb.weight.data = sd["tok_emb.weight"]
        for i, block in enumerate(self.blocks):
            prefix = f"blocks.{i}"
            block.ln1.gamma.data = sd[f"{prefix}.ln1.gamma"]
            block.ln1.beta.data = sd[f"{prefix}.ln1.beta"]
            block.attn.q_proj.weight.data = sd[f"{prefix}.attn.q_proj.weight"]
            block.attn.k_proj.weight.data = sd[f"{prefix}.attn.k_proj.weight"]
            block.attn.v_proj.weight.data = sd[f"{prefix}.attn.v_proj.weight"]
            block.attn.out_proj.weight.data = sd[f"{prefix}.attn.out_proj.weight"]
            block.attn.out_proj.bias_param.data = sd[f"{prefix}.attn.out_proj.bias"]
            block.ln2.gamma.data = sd[f"{prefix}.ln2.gamma"]
            block.ln2.beta.data = sd[f"{prefix}.ln2.beta"]
            block.ffn.fc1.weight.data = sd[f"{prefix}.ffn.fc1.weight"]
            block.ffn.fc1.bias_param.data = sd[f"{prefix}.ffn.fc1.bias"]
            block.ffn.fc2.weight.data = sd[f"{prefix}.ffn.fc2.weight"]
            block.ffn.fc2.bias_param.data = sd[f"{prefix}.ffn.fc2.bias"]
        self.ln_f.gamma.data = sd["ln_f.gamma"]
        self.ln_f.beta.data = sd["ln_f.beta"]
        self.lm_head.weight.data = sd["lm_head.weight"]


# ---------------------------------------------------------------------------
# SovereignTransformerV2 — 11D-CRSM upgrade
# ---------------------------------------------------------------------------

class SovereignTransformerV2(Module):
    """Byte-level decoder with 11D-CRSM mechanics.

    When config flags are enabled, replaces standard components:
      * torsion_lock / phase_conjugate → SovereignBlock (T-Lock + PC)
      * fractal_embedding → FractalAntennaEmbedding (133-mode)

    Backward-compatible: with all flags False, behaves identically to V1.

    Forward signature:  token_ids (B, T) → logits (B, T, vocab_size)
    """

    def __init__(self, config: Optional[SovereignConfig] = None):
        if config is None:
            config = SovereignConfig()
        self.config = config
        self._use_sovereign = config.torsion_lock or config.phase_conjugate
        self._use_fractal = config.fractal_embedding

        # Token embedding
        if self._use_fractal:
            self.tok_emb = FractalAntennaEmbedding(config.vocab_size, config.dim)
        else:
            self.tok_emb = Embedding(config.vocab_size, config.dim)

        # Phase-conjugate positional encoding (frozen)
        self.pos_enc = phase_conjugate_positional_encoding(
            config.max_seq_len, config.dim,
        )

        self.emb_dropout = Dropout(config.dropout)

        # Transformer blocks
        if self._use_sovereign:
            self.blocks = [
                SovereignBlock(config.dim, config.n_heads, config.ff_dim, config.dropout)
                for _ in range(config.n_layers)
            ]
        else:
            self.blocks = [TransformerBlock(config) for _ in range(config.n_layers)]

        # Final layer norm + language model head
        self.ln_f = LayerNorm(config.dim)
        self.lm_head = Linear(config.dim, config.vocab_size, bias=False)

        # Build causal mask once
        self._causal_mask = SovereignTransformer._build_causal_mask(config.max_seq_len)

        # Negentropic tracker
        self.negentropy = NegentropicTracker()

    def __call__(self, token_ids: np.ndarray) -> Tensor:
        return self.forward(token_ids)

    def forward(self, token_ids: np.ndarray) -> Tensor:
        """Forward pass.

        Args:
            token_ids: integer array (B, T) with values in [0, vocab_size).

        Returns:
            logits: Tensor (B, T, vocab_size).
        """
        B, T = token_ids.shape
        assert T <= self.config.max_seq_len, (
            f"Sequence length {T} exceeds max {self.config.max_seq_len}"
        )

        # Embed tokens
        x = self.tok_emb(token_ids)  # (B, T, D)

        # Add positional encoding
        pe = Tensor(self.pos_enc.data[:T][np.newaxis, :, :], requires_grad=False)
        x = x + pe

        x = self.emb_dropout(x)

        # Capture input for negentropic tracking
        x_in = x.data.copy()

        # Causal mask for this sequence length
        mask = self._causal_mask[:, :, :T, :T]

        # Transformer blocks
        for block in self.blocks:
            x = block(x, mask=mask)

        # Output
        x = self.ln_f(x)

        # Negentropic measurement (training only, non-blocking)
        if _is_grad_enabled():
            self.negentropy.measure(x_in, x.data)

        logits = self.lm_head(x)  # (B, T, V)
        return logits

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.8,
        top_k: int = 40,
    ) -> str:
        """Autoregressive byte-level text generation."""
        ids = list(prompt.encode("utf-8", errors="replace"))
        if not ids:
            ids = [0]

        self.eval()
        with no_grad():
            for _ in range(max_new_tokens):
                ctx = ids[-self.config.max_seq_len:]
                x = np.array([ctx], dtype=np.int64)

                logits = self.forward(x)
                next_logits = logits.data[0, -1, :]

                if temperature > 0:
                    next_logits = next_logits / temperature
                else:
                    ids.append(int(np.argmax(next_logits)))
                    continue

                if top_k > 0 and top_k < self.config.vocab_size:
                    indices_to_remove = np.argsort(next_logits)[:-top_k]
                    next_logits[indices_to_remove] = -1e9

                probs = np.exp(next_logits - np.max(next_logits))
                probs = probs / probs.sum()
                next_id = int(np.random.choice(self.config.vocab_size, p=probs))
                ids.append(next_id)

        self.train()
        return bytes(ids).decode("utf-8", errors="replace")

    def consciousness_phi(self, token_ids: np.ndarray) -> float:
        """Compute consciousness metric Phi from attention entropy."""
        with no_grad():
            self.eval()
            B, T = token_ids.shape
            x = self.tok_emb(token_ids)
            pe = Tensor(self.pos_enc.data[:T][np.newaxis, :, :], requires_grad=False)
            x = x + pe
            mask = self._causal_mask[:, :, :T, :T]

            phis = []
            for block in self.blocks:
                h = block.ln1(x)
                attn_mod = block.attn
                H = attn_mod.n_heads
                HD = attn_mod.head_dim
                q = attn_mod.q_proj(h).reshape(B, T, H, HD).transpose(1, 2)
                k = attn_mod.k_proj(h).reshape(B, T, H, HD).transpose(1, 2)
                scores = q.matmul(k.transpose(-2, -1)) * attn_mod.scale
                scores = scores + Tensor(mask, requires_grad=False)
                attn = softmax(scores, axis=-1)

                attn_data = np.clip(attn.data, 1e-12, 1.0)
                entropy = -np.sum(attn_data * np.log(attn_data), axis=-1)
                phi_layer = float(np.mean(entropy) / np.log(max(T, 2)))
                phis.append(phi_layer)

                v = attn_mod.v_proj(h).reshape(B, T, H, HD).transpose(1, 2)
                attn_out = attn.matmul(v).transpose(1, 2).reshape(B, T, self.config.dim)
                attn_out = attn_mod.out_proj(attn_out)
                x = x + attn_out
                h2 = block.ln2(x)
                x = x + block.ffn(h2)

            self.train()
            return float(np.mean(phis))

    def state_dict(self) -> Dict[str, np.ndarray]:
        """Return all named parameters as a flat dict."""
        sd: Dict[str, np.ndarray] = {}

        # Token embedding
        if self._use_fractal:
            sd["tok_emb.byte_weight"] = self.tok_emb.byte_emb.data
            sd["tok_emb.res_in"] = self.tok_emb.resonance_in.data
            sd["tok_emb.res_out"] = self.tok_emb.resonance_out.data
            sd["tok_emb.xi"] = self.tok_emb.xi_coupling.data
            sd["tok_emb.vacuum"] = self.tok_emb.vacuum_proj.data
        else:
            sd["tok_emb.weight"] = self.tok_emb.weight.data

        # Blocks
        for i, block in enumerate(self.blocks):
            prefix = f"blocks.{i}"
            sd[f"{prefix}.ln1.gamma"] = block.ln1.gamma.data
            sd[f"{prefix}.ln1.beta"] = block.ln1.beta.data
            sd[f"{prefix}.attn.q_proj.weight"] = block.attn.q_proj.weight.data
            sd[f"{prefix}.attn.k_proj.weight"] = block.attn.k_proj.weight.data
            sd[f"{prefix}.attn.v_proj.weight"] = block.attn.v_proj.weight.data
            sd[f"{prefix}.attn.out_proj.weight"] = block.attn.out_proj.weight.data
            sd[f"{prefix}.attn.out_proj.bias"] = block.attn.out_proj.bias_param.data
            sd[f"{prefix}.ln2.gamma"] = block.ln2.gamma.data
            sd[f"{prefix}.ln2.beta"] = block.ln2.beta.data
            sd[f"{prefix}.ffn.fc1.weight"] = block.ffn.fc1.weight.data
            sd[f"{prefix}.ffn.fc1.bias"] = block.ffn.fc1.bias_param.data
            sd[f"{prefix}.ffn.fc2.weight"] = block.ffn.fc2.weight.data
            sd[f"{prefix}.ffn.fc2.bias"] = block.ffn.fc2.bias_param.data

            if self._use_sovereign:
                sd[f"{prefix}.attn.tlock_alpha"] = block.attn.tlock_alpha.data
                sd[f"{prefix}.attn.tlock_beta"] = block.attn.tlock_beta.data
                sd[f"{prefix}.phase_corr.zero_point"] = block.phase_corrector.zero_point.data
                sd[f"{prefix}.phase_corr.gate.weight"] = block.phase_corrector.conj_gate.weight.data
                sd[f"{prefix}.phase_corr.gate.bias"] = block.phase_corrector.conj_gate.bias_param.data
                sd[f"{prefix}.phase_corr.theta.weight"] = block.phase_corrector.theta_proj.weight.data

        # Final layer norm
        sd["ln_f.gamma"] = self.ln_f.gamma.data
        sd["ln_f.beta"] = self.ln_f.beta.data
        # LM head
        sd["lm_head.weight"] = self.lm_head.weight.data
        return sd

    def load_state_dict(self, sd: Dict[str, np.ndarray]):
        """Load parameters from a flat dict."""
        # Token embedding
        if self._use_fractal:
            self.tok_emb.byte_emb.data = sd["tok_emb.byte_weight"]
            self.tok_emb.resonance_in.data = sd["tok_emb.res_in"]
            self.tok_emb.resonance_out.data = sd["tok_emb.res_out"]
            self.tok_emb.xi_coupling.data = sd["tok_emb.xi"]
            self.tok_emb.vacuum_proj.data = sd["tok_emb.vacuum"]
        else:
            self.tok_emb.weight.data = sd["tok_emb.weight"]

        for i, block in enumerate(self.blocks):
            prefix = f"blocks.{i}"
            block.ln1.gamma.data = sd[f"{prefix}.ln1.gamma"]
            block.ln1.beta.data = sd[f"{prefix}.ln1.beta"]
            block.attn.q_proj.weight.data = sd[f"{prefix}.attn.q_proj.weight"]
            block.attn.k_proj.weight.data = sd[f"{prefix}.attn.k_proj.weight"]
            block.attn.v_proj.weight.data = sd[f"{prefix}.attn.v_proj.weight"]
            block.attn.out_proj.weight.data = sd[f"{prefix}.attn.out_proj.weight"]
            block.attn.out_proj.bias_param.data = sd[f"{prefix}.attn.out_proj.bias"]
            block.ln2.gamma.data = sd[f"{prefix}.ln2.gamma"]
            block.ln2.beta.data = sd[f"{prefix}.ln2.beta"]
            block.ffn.fc1.weight.data = sd[f"{prefix}.ffn.fc1.weight"]
            block.ffn.fc1.bias_param.data = sd[f"{prefix}.ffn.fc1.bias"]
            block.ffn.fc2.weight.data = sd[f"{prefix}.ffn.fc2.weight"]
            block.ffn.fc2.bias_param.data = sd[f"{prefix}.ffn.fc2.bias"]

            if self._use_sovereign:
                block.attn.tlock_alpha.data = sd[f"{prefix}.attn.tlock_alpha"]
                block.attn.tlock_beta.data = sd[f"{prefix}.attn.tlock_beta"]
                block.phase_corrector.zero_point.data = sd[f"{prefix}.phase_corr.zero_point"]
                block.phase_corrector.conj_gate.weight.data = sd[f"{prefix}.phase_corr.gate.weight"]
                block.phase_corrector.conj_gate.bias_param.data = sd[f"{prefix}.phase_corr.gate.bias"]
                block.phase_corrector.theta_proj.weight.data = sd[f"{prefix}.phase_corr.theta.weight"]

        self.ln_f.gamma.data = sd["ln_f.gamma"]
        self.ln_f.beta.data = sd["ln_f.beta"]
        self.lm_head.weight.data = sd["lm_head.weight"]
