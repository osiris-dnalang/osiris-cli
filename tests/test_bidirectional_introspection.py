"""
Tests for OSIRIS v5.0 Bidirectional Attention & Epistemic Introspection Engine.
"""

import numpy as np
import pytest

from osiris.nclm.autograd import Tensor, no_grad
from osiris.nclm.bidirectional import (
    BidirectionalAttention,
    OnlineNegentropicTracker,
    IntrospectiveGovernor,
    GovernorAction,
    AnomalyReceipt,
    EpistemicIntrospector,
    IntrospectionProfile,
)
from osiris.nclm.transformer import SovereignTransformer, SovereignConfig


class TestBidirectionalAttention:
    """Verify bidirectional dual-stream attention mechanics."""

    def test_forward_pass_shape(self):
        attn = BidirectionalAttention(dim=64, n_heads=4, dropout=0.0)
        x = Tensor(np.random.randn(2, 8, 64).astype(np.float32))
        out = attn(x)
        assert out.shape == (2, 8, 64)
        assert isinstance(out, Tensor)

    def test_metrics_and_coherence_bounded(self):
        attn = BidirectionalAttention(dim=32, n_heads=2)
        x = Tensor(np.random.randn(1, 10, 32).astype(np.float32))
        out, metrics = attn(x, return_metrics=True)
        assert "coherence" in metrics
        assert 0.0 <= metrics["coherence"] <= 1.0
        assert metrics["fwd_energy"] > 0.0
        assert metrics["bwd_energy"] > 0.0

    def test_gradient_flow_through_dual_streams(self):
        attn = BidirectionalAttention(dim=32, n_heads=2)
        x = Tensor(np.random.randn(1, 6, 32).astype(np.float32), requires_grad=True)
        out = attn(x)
        loss = out.sum()
        loss.backward()
        assert x.grad is not None
        assert not np.isnan(x.grad).any()
        assert attn.q_proj.weight.grad is not None
        assert attn.conjugate_proj.weight.grad is not None
        assert attn.coupling_fwd.grad is not None
        assert attn.coupling_bwd.grad is not None


class TestOnlineNegentropicTracker:
    """Verify layer-by-layer entropy and information metrics."""

    def test_analyze_layer_metrics(self):
        x_in = np.random.randn(2, 16, 64).astype(np.float32)
        x_out = np.random.randn(2, 16, 64).astype(np.float32) * 1.5

        telem = OnlineNegentropicTracker.analyze_layer(0, x_in, x_out)
        assert telem.layer_index == 0
        assert -500.0 <= telem.negentropy_xi <= 500.0
        assert 0.0 <= telem.decoherence_gamma <= 1.0
        assert isinstance(telem.delta_s, float)
        assert telem.thermal_variance > 0.0

    def test_shannon_entropy_calculation(self):
        uniform = np.linspace(-1, 1, 1000).astype(np.float32)
        ent = OnlineNegentropicTracker.shannon_entropy(uniform)
        assert ent > 0.0

        empty = np.array([], dtype=np.float32)
        assert OnlineNegentropicTracker.shannon_entropy(empty) == 0.0


class TestIntrospectiveGovernor:
    """Verify automated rollback and early-stopping governor under SYS-021."""

    def test_normal_learning_progression(self):
        gov = IntrospectiveGovernor(threshold_delta_bpb=0.05, patience_windows=3)

        action, receipt = gov.evaluate(100, 3.50)
        assert action == GovernorAction.CONTINUE
        assert receipt is None
        assert gov.best_bpb == 3.50

        action, receipt = gov.evaluate(200, 3.20)
        assert action == GovernorAction.CONTINUE
        assert gov.best_bpb == 3.20

        action, receipt = gov.evaluate(300, 3.10)
        assert action == GovernorAction.CONTINUE
        assert gov.best_bpb == 3.10

    def test_divergence_triggers_quarantine_rollback(self, tmp_path):
        receipts_log = tmp_path / "rollback_receipts.jsonl"
        gov = IntrospectiveGovernor(
            threshold_delta_bpb=0.05,
            patience_windows=3,
            receipts_log_path=str(receipts_log),
        )

        # Baseline optimal step
        gov.evaluate(step=500, held_out_bpb=2.50)
        assert gov.best_bpb == 2.50

        # Window 1 divergence: +0.08
        action, receipt = gov.evaluate(step=600, held_out_bpb=2.58)
        assert action == GovernorAction.WARNING
        assert receipt is None
        assert gov.consecutive_divergences == 1

        # Window 2 divergence: +0.10
        action, receipt = gov.evaluate(step=700, held_out_bpb=2.60)
        assert action == GovernorAction.WARNING
        assert gov.consecutive_divergences == 2

        # Window 3 divergence: +0.15 -> TRIGGERS ROLLBACK
        dummy_weights = b"sample_model_weights_bytes_for_testing"
        action, receipt = gov.evaluate(
            step=800,
            held_out_bpb=2.65,
            model_weights_bytes=dummy_weights,
        )
        assert action == GovernorAction.ROLLBACK
        assert receipt is not None
        assert isinstance(receipt, AnomalyReceipt)
        assert receipt.trigger_step == 800
        assert receipt.best_bpb == 2.50
        assert receipt.current_bpb == 2.65
        assert receipt.delta_bpb == pytest.approx(0.15)
        assert receipt.consecutive_divergences == 3
        assert len(receipt.weights_sha256) == 64
        assert len(receipt.payload_receipt_hash) == 64

        # Check receipt persistence
        assert receipts_log.exists()
        content = receipts_log.read_text()
        assert "ROLLBACK" in content
        assert receipt.payload_receipt_hash in content


class TestEpistemicIntrospector:
    """Verify high-level model introspection."""

    def test_introspect_text_on_transformer(self):
        cfg = SovereignConfig(
            vocab_size=256,
            dim=64,
            n_layers=2,
            n_heads=2,
            ff_dim=128,
            max_seq_len=64,
            dropout=0.0,
            torsion_lock=True,
            phase_conjugate=True,
        )
        model = SovereignTransformer(cfg)

        prompt = "osiris sovereign verification test"
        profile = EpistemicIntrospector.introspect_text(model, prompt)

        assert isinstance(profile, IntrospectionProfile)
        assert profile.n_tokens == len(prompt)
        assert len(profile.layers) == 2
        assert len(profile.token_saliency) == len(prompt)
        assert -500.0 <= profile.mean_negentropy_xi <= 500.0
        assert 0.0 <= profile.mean_decoherence_gamma <= 1.0

        summary = profile.summary()
        assert "IntrospectionProfile" in summary
        assert "Xi=" in summary
        assert "C_bidir=" in summary
