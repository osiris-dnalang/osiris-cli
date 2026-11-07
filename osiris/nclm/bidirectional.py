"""
OSIRIS v5.0 Bidirectional Attention & Epistemic Introspection Engine.
====================================================================

Pillar I & Pillar II Implementation:
  I.  Bidirectional Attention (Dual-Stream Causal & Phase-Conjugate Anti-Causal)
      Couples forward causal stream with time-reversed phase-conjugate reflection
      under theta_lock = 51.843° to quantify representation coherence.

  II. Online Negentropic Tracking
      Layer-by-layer entropy S(l) and information efficiency Xi(l):
      Xi = -Delta_S_info / Delta_S_thermal * 100%

 III. Introspective Governor (Automated Rollback & Early-Stopping)
      Monitors Delta BPB_held_out = BPB(t) - min_{tau < t} BPB(tau).
      If Delta BPB > 0.05 for 3 consecutive windows, halts gradient divergence,
      snapshots the anomaly, and triggers verified rollback to best weights.

Framework: DNA::}{::lang v51.843 / OSIRIS v5.0 Sovereign Horizon
Governance: SYS-021 (Payload-Bound Grants), SYS-023 (Merkle Ledger)
"""

from __future__ import annotations

import math
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple, Union

import numpy as np

from .autograd import Tensor, softmax, _is_grad_enabled
from .layers import Module, Linear, Dropout
from .sovereign_mechanics import THETA_LOCK_RAD, CHI_PC


# ===========================================================================
# I. Bidirectional Attention
# ===========================================================================

class BidirectionalAttention(Module):
    """Dual-stream bidirectional attention with phase-conjugate cross-projection.

    Standard causal attention is unidirectional (j <= i), leaving future
    context and semantic drift unverified.

    BidirectionalAttention evaluates:
      1. Forward Causal Stream: A_fwd with causal mask (j <= i)
      2. Anti-Causal Backward Stream: A_bwd with reverse mask (j >= i)
      3. Phase-Conjugate Projection: Theta(O_bwd)* negates odd dimensions,
         simulating time-reversal reflection back to the present token.
      4. Relational Blend under theta_lock = 51.843°:
         O = cos(theta_lock) * O_fwd + sin(theta_lock) * Theta(O_bwd)*
    """

    def __init__(self, dim: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        assert dim % n_heads == 0, f"dim {dim} must be divisible by n_heads {n_heads}"
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = 1.0 / math.sqrt(self.head_dim)

        # Forward & Backward projections
        self.q_proj = Linear(dim, dim, bias=False)
        self.k_proj = Linear(dim, dim, bias=False)
        self.v_proj = Linear(dim, dim, bias=False)
        self.out_proj = Linear(dim, dim, bias=True)
        self.conjugate_proj = Linear(dim, dim, bias=False)
        self.dropout = Dropout(dropout)

        # Learnable phase coupling initialized at theta_lock
        self.coupling_fwd = Tensor(
            np.array([math.cos(THETA_LOCK_RAD)], dtype=np.float32),
            requires_grad=True,
            name="bidir.coupling_fwd",
        )
        self.coupling_bwd = Tensor(
            np.array([math.sin(THETA_LOCK_RAD) * CHI_PC], dtype=np.float32),
            requires_grad=True,
            name="bidir.coupling_bwd",
        )

        # Internal coherence cache
        self.last_coherence: float = 1.0

    def __call__(
        self,
        x: Tensor,
        mask: Optional[np.ndarray] = None,
        return_metrics: bool = False,
    ) -> Union[Tensor, Tuple[Tensor, Dict[str, float]]]:
        B, T, D = x.shape
        H = self.n_heads
        HD = self.head_dim

        q = self.q_proj(x).reshape(B, T, H, HD).transpose(1, 2)
        k = self.k_proj(x).reshape(B, T, H, HD).transpose(1, 2)
        v = self.v_proj(x).reshape(B, T, H, HD).transpose(1, 2)

        raw_scores = q.matmul(k.transpose(-2, -1)) * self.scale  # (B, H, T, T)

        # 1. Forward causal mask (j <= i)
        causal_mask = np.triu(np.full((T, T), -1e9, dtype=np.float32), k=1)
        scores_fwd = raw_scores + Tensor(causal_mask[np.newaxis, np.newaxis, :, :], requires_grad=False)
        if mask is not None:
            scores_fwd = scores_fwd + Tensor(mask, requires_grad=False)
        attn_fwd = softmax(scores_fwd, axis=-1)
        attn_fwd = self.dropout(attn_fwd)
        out_fwd = attn_fwd.matmul(v).transpose(1, 2).reshape(B, T, D)

        # 2. Anti-causal backward stream (j >= i)
        anti_causal_mask = np.tril(np.full((T, T), -1e9, dtype=np.float32), k=-1)
        scores_bwd = raw_scores + Tensor(anti_causal_mask[np.newaxis, np.newaxis, :, :], requires_grad=False)
        attn_bwd = softmax(scores_bwd, axis=-1)
        attn_bwd = self.dropout(attn_bwd)
        out_bwd = attn_bwd.matmul(v).transpose(1, 2).reshape(B, T, D)

        # 3. Phase-conjugate time-reversal reflection: negate odd feature dims
        bwd_data = out_bwd.data.copy()
        bwd_data[:, :, 1::2] *= -1.0
        track = _is_grad_enabled() and out_bwd.requires_grad
        out_bwd_conj = Tensor(bwd_data, requires_grad=track)
        if track:
            out_bwd_conj._prev = [out_bwd]

            def _backward():
                out_bwd._ensure_grad()
                g = (
                    out_bwd_conj.grad.copy()
                    if out_bwd_conj.grad is not None
                    else np.zeros_like(out_bwd.data)
                )
                g[:, :, 1::2] *= -1.0
                out_bwd.grad = out_bwd.grad + g

            out_bwd_conj._backward_fn = _backward

        projected_bwd = self.conjugate_proj(out_bwd_conj)

        # 4. Relational blend
        fwd_blend = out_fwd * self.coupling_fwd
        bwd_blend = projected_bwd * self.coupling_bwd
        combined = fwd_blend + bwd_blend
        out = self.out_proj(combined)

        # 5. Compute bidirectional coherence metric
        # C_bidir = normalized dot product between forward and backward streams
        fwd_norm = np.linalg.norm(out_fwd.data, axis=-1, keepdims=True) + 1e-9
        bwd_norm = np.linalg.norm(out_bwd.data, axis=-1, keepdims=True) + 1e-9
        cos_sim = np.sum((out_fwd.data / fwd_norm) * (out_bwd.data / bwd_norm), axis=-1)
        coherence = float(np.clip((np.mean(cos_sim) + 1.0) / 2.0, 0.0, 1.0))
        self.last_coherence = coherence

        if return_metrics:
            return out, {"coherence": coherence, "fwd_energy": float(np.mean(fwd_norm)), "bwd_energy": float(np.mean(bwd_norm))}
        return out


# ===========================================================================
# II. Online Negentropic Tracking & Introspection
# ===========================================================================

@dataclass
class LayerTelemetry:
    """Telemetry recorded for a single transformer layer during introspection."""
    layer_index: int
    entropy_in: float
    entropy_out: float
    delta_s: float
    thermal_variance: float
    negentropy_xi: float
    decoherence_gamma: float


@dataclass
class IntrospectionProfile:
    """Complete epistemic introspection report for a model forward pass."""
    text_snippet: str
    n_tokens: int
    layers: List[LayerTelemetry]
    mean_negentropy_xi: float
    bidirectional_coherence: float
    mean_decoherence_gamma: float
    token_saliency: List[Tuple[str, float]]
    timestamp: float = field(default_factory=time.time)

    def summary(self) -> str:
        saliency_top = ", ".join([f"'{t}': {s:.3f}" for t, s in self.token_saliency[:5]])
        return (
            f"IntrospectionProfile(tokens={self.n_tokens}, "
            f"Xi={self.mean_negentropy_xi:+.1f}%, "
            f"C_bidir={self.bidirectional_coherence:.4f}, "
            f"Gamma={self.mean_decoherence_gamma:.4f}, "
            f"top_salient=[{saliency_top}])"
        )


class OnlineNegentropicTracker:
    """Real-time tracking of entropy and information creation across layers."""

    @staticmethod
    def shannon_entropy(x: np.ndarray, bins: int = 64) -> float:
        """Compute empirical Shannon entropy across activation values."""
        flat = x.ravel()
        if len(flat) == 0:
            return 0.0
        hist, _ = np.histogram(flat, bins=bins, density=True)
        hist = hist[hist > 0]
        # Normalize to probability distribution
        p = hist / np.sum(hist)
        return float(-np.sum(p * np.log2(p + 1e-12)))

    @classmethod
    def analyze_layer(cls, layer_idx: int, x_in: np.ndarray, x_out: np.ndarray) -> LayerTelemetry:
        """Compute layer-level thermodynamic and informational metrics."""
        s_in = cls.shannon_entropy(x_in)
        s_out = cls.shannon_entropy(x_out)
        delta_s = s_out - s_in

        var_in = float(np.var(x_in))
        var_out = float(np.var(x_out))
        delta_var = abs(var_out - var_in) + 1e-12

        # Xi = -Delta_S_info / Delta_S_thermal * 100%
        xi = float(np.clip((-delta_s / delta_var) * 100.0, -500.0, 500.0))

        gamma = float(
            np.clip(
                np.mean(np.var(x_out, axis=-1))
                / (np.mean(np.var(x_out, axis=-1)) + 1.0),
                0.0,
                1.0,
            )
        )

        return LayerTelemetry(
            layer_index=layer_idx,
            entropy_in=s_in,
            entropy_out=s_out,
            delta_s=delta_s,
            thermal_variance=var_out,
            negentropy_xi=xi,
            decoherence_gamma=gamma,
        )


# ===========================================================================
# III. Introspective Governor (Automated Rollback & Anomaly Quarantine)
# ===========================================================================

class GovernorAction(str, Enum):
    CONTINUE = "CONTINUE"
    WARNING = "WARNING"
    ROLLBACK = "ROLLBACK"


@dataclass
class AnomalyReceipt:
    """Immutable audit receipt recorded when the governor aborts divergence."""
    timestamp: float
    trigger_step: int
    best_bpb: float
    current_bpb: float
    delta_bpb: float
    consecutive_divergences: int
    weights_sha256: str
    action: str
    payload_receipt_hash: str


class IntrospectiveGovernor:
    """Automated early-stopping, divergence quarantine, and safe rollback.

    From Section 2.1 of OSIRIS v5.0 Specification:
      Delta BPB_held_out = BPB(t) - min_{tau < t} BPB(tau)
      If Delta BPB > 0.05 for 3 consecutive evaluation windows:
        1. Halt current gradient step
        2. Record cryptographic anomaly receipt (SYS-021)
        3. Trigger verified rollback to save_best()
    """

    def __init__(
        self,
        threshold_delta_bpb: float = 0.05,
        patience_windows: int = 3,
        receipts_log_path: Optional[str] = None,
    ):
        self.threshold = threshold_delta_bpb
        self.patience = patience_windows
        self.receipts_path = receipts_log_path

        self.best_bpb: float = float("inf")
        self.best_step: int = 0
        self.consecutive_divergences: int = 0
        self.history: List[Tuple[int, float]] = []
        self.receipts: List[AnomalyReceipt] = []

    def evaluate(
        self,
        step: int,
        held_out_bpb: float,
        model_weights_bytes: Optional[bytes] = None,
    ) -> Tuple[GovernorAction, Optional[AnomalyReceipt]]:
        """Evaluate current evaluation window against historical best."""
        self.history.append((step, held_out_bpb))

        # Check for new historical best
        if held_out_bpb < self.best_bpb:
            self.best_bpb = held_out_bpb
            self.best_step = step
            self.consecutive_divergences = 0
            return GovernorAction.CONTINUE, None

        # Measure drift relative to historical best
        delta = held_out_bpb - self.best_bpb

        if delta > self.threshold:
            self.consecutive_divergences += 1
        else:
            self.consecutive_divergences = 0

        # Check rollback threshold condition
        if self.consecutive_divergences >= self.patience:
            weights_hash = (
                hashlib.sha256(model_weights_bytes).hexdigest()
                if model_weights_bytes
                else "unhashed_memory_state"
            )
            receipt_payload = {
                "step": step,
                "best_step": self.best_step,
                "best_bpb": self.best_bpb,
                "current_bpb": held_out_bpb,
                "delta_bpb": delta,
                "consecutive": self.consecutive_divergences,
                "weights_hash": weights_hash,
            }
            receipt_hash = hashlib.sha256(
                json.dumps(receipt_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()

            receipt = AnomalyReceipt(
                timestamp=time.time(),
                trigger_step=step,
                best_bpb=self.best_bpb,
                current_bpb=held_out_bpb,
                delta_bpb=delta,
                consecutive_divergences=self.consecutive_divergences,
                weights_sha256=weights_hash,
                action=GovernorAction.ROLLBACK.value,
                payload_receipt_hash=receipt_hash,
            )
            self.receipts.append(receipt)
            self._persist_receipt(receipt)
            return GovernorAction.ROLLBACK, receipt

        elif self.consecutive_divergences > 0:
            return GovernorAction.WARNING, None

        return GovernorAction.CONTINUE, None

    def _persist_receipt(self, receipt: AnomalyReceipt) -> None:
        if not self.receipts_path:
            return
        try:
            with open(self.receipts_path, "a", encoding="utf-8") as f:
                rec_dict = {
                    "timestamp": receipt.timestamp,
                    "trigger_step": receipt.trigger_step,
                    "best_bpb": receipt.best_bpb,
                    "current_bpb": receipt.current_bpb,
                    "delta_bpb": receipt.delta_bpb,
                    "consecutive_divergences": receipt.consecutive_divergences,
                    "weights_sha256": receipt.weights_sha256,
                    "action": receipt.action,
                    "payload_receipt_hash": receipt.payload_receipt_hash,
                }
                f.write(json.dumps(rec_dict) + "\n")
        except OSError:
            pass


# ===========================================================================
# IV. High-Level Epistemic Introspector
# ===========================================================================

class EpistemicIntrospector:
    """High-level inspection harness for extracting explainable model representations."""

    @staticmethod
    def introspect_text(model, text: str) -> IntrospectionProfile:
        """Perform comprehensive introspection over input text."""
        raw_bytes = text.encode("utf-8")
        tokens = [chr(b) if 32 <= b < 127 else f"\\x{b:02x}" for b in raw_bytes]
        input_ids = np.array([[b for b in raw_bytes]], dtype=np.int32)
        x = Tensor(input_ids)

        layers_telemetry: List[LayerTelemetry] = []

        # Run through embedding
        if hasattr(model, "tok_emb"):
            h = model.tok_emb(input_ids)
        else:
            h = model.blocks[0].attn.q_proj(x)

        # Track layer activations
        for idx, block in enumerate(getattr(model, "blocks", [])):
            h_prev = h.data.copy()
            h = block(h)
            h_curr = h.data.copy()
            telem = OnlineNegentropicTracker.analyze_layer(idx, h_prev, h_curr)
            layers_telemetry.append(telem)

        # Token saliency calculation based on final representation variance across features
        var_per_token = np.var(h.data[0], axis=-1)
        norm_saliency = var_per_token / (np.sum(var_per_token) + 1e-9)
        token_saliency = [(tokens[i], float(norm_saliency[i])) for i in range(len(tokens))]
        # Sort top salient tokens descending
        token_saliency_sorted = sorted(token_saliency, key=lambda kv: kv[1], reverse=True)

        mean_xi = float(np.mean([t.negentropy_xi for t in layers_telemetry])) if layers_telemetry else 0.0
        mean_gamma = float(np.mean([t.decoherence_gamma for t in layers_telemetry])) if layers_telemetry else 0.0

        # Extract coherence if bidirectional attention exists in any block
        coherences = [
            b.attn.last_coherence
            for b in getattr(model, "blocks", [])
            if hasattr(b, "attn") and hasattr(b.attn, "last_coherence")
        ]
        mean_coherence = float(np.mean(coherences)) if coherences else 1.0

        return IntrospectionProfile(
            text_snippet=text[:64] + ("..." if len(text) > 64 else ""),
            n_tokens=len(tokens),
            layers=layers_telemetry,
            mean_negentropy_xi=mean_xi,
            bidirectional_coherence=mean_coherence,
            mean_decoherence_gamma=mean_gamma,
            token_saliency=token_saliency_sorted,
        )
