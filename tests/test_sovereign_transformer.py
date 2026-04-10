"""
Tests for the SovereignTransformer and all supporting modules.
================================================================

Covers:
  * Autograd: numerical gradient checking for every op
  * Layers: Embedding, Linear, LayerNorm, GELU, Dropout
  * Positions: phase-conjugate PE shape and properties
  * Transformer: forward pass shapes, generate, state_dict round-trip
  * Optimizer: AdamW + LR schedule
  * Trainer: corpus loading, batch creation
  * Inference: safetensors round-trip, top-p filter
  * Cross-entropy loss
  * Consciousness Φ metric

Framework: DNA::}{::lang v51.843
"""

import os
import sys
import tempfile
import numpy as np

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ===========================================================================
# Autograd tests
# ===========================================================================

class TestAutograd:
    """Numerical gradient checking for autograd operations."""

    def _check_grad(self, f, x_data, eps=1e-4, rtol=1e-3, atol=1e-5):
        """Check autograd gradient against finite differences."""
        from osiris.nclm.autograd import Tensor

        x = Tensor(x_data.copy(), requires_grad=True)
        y = f(x)
        if y.data.size > 1:
            y = y.sum()
        y.backward()
        analytic = x.grad.copy()

        # Finite differences
        numerical = np.zeros_like(x_data)
        for idx in np.ndindex(x_data.shape):
            x_plus = x_data.copy()
            x_minus = x_data.copy()
            x_plus[idx] += eps
            x_minus[idx] -= eps

            y_plus = f(Tensor(x_plus)).data
            y_minus = f(Tensor(x_minus)).data

            if y_plus.size > 1:
                y_plus = y_plus.sum()
                y_minus = y_minus.sum()
            else:
                y_plus = float(y_plus)
                y_minus = float(y_minus)

            numerical[idx] = (y_plus - y_minus) / (2 * eps)

        np.testing.assert_allclose(analytic, numerical, rtol=rtol, atol=atol)

    def test_add(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t + t * 0.5, x)

    def test_sub(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t - t * 0.3, x)

    def test_mul(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t * t, x)

    def test_div(self):
        x = np.random.randn(3, 4).astype(np.float32) + 2.0
        self._check_grad(lambda t: t / (t + 1.0), x)

    def test_pow(self):
        x = np.abs(np.random.randn(3, 4).astype(np.float32)) + 0.5
        self._check_grad(lambda t: t ** 2.0, x)

    def test_exp(self):
        x = np.random.randn(3, 4).astype(np.float32) * 0.5
        self._check_grad(lambda t: t.exp(), x)

    def test_log(self):
        x = np.abs(np.random.randn(3, 4).astype(np.float32)) + 0.5
        self._check_grad(lambda t: t.log(), x)

    def test_tanh(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t.tanh(), x)

    def test_sqrt(self):
        x = np.abs(np.random.randn(3, 4).astype(np.float32)) + 0.5
        self._check_grad(lambda t: t.sqrt(), x)

    def test_sum(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t.sum(axis=1), x)

    def test_mean(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t.mean(axis=-1), x)

    def test_matmul(self):
        from osiris.nclm.autograd import Tensor
        x_data = np.random.randn(3, 4).astype(np.float32)
        w_data = np.random.randn(4, 5).astype(np.float32)
        w = Tensor(w_data, requires_grad=False)
        self._check_grad(lambda t: t.matmul(w), x_data)

    def test_transpose(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t.transpose(0, 1), x)

    def test_reshape(self):
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: t.reshape(12), x)

    def test_softmax(self):
        from osiris.nclm.autograd import softmax
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: softmax(t, axis=-1), x)

    def test_gelu(self):
        from osiris.nclm.autograd import gelu
        x = np.random.randn(3, 4).astype(np.float32)
        self._check_grad(lambda t: gelu(t), x)

    def test_no_grad(self):
        from osiris.nclm.autograd import Tensor, no_grad
        x = Tensor(np.array([1.0, 2.0, 3.0]), requires_grad=True)
        with no_grad():
            y = x * 2.0
        assert y._backward_fn is None

    def test_embedding_lookup(self):
        from osiris.nclm.autograd import Tensor
        weight = Tensor(np.random.randn(10, 4).astype(np.float32), requires_grad=True)
        indices = np.array([0, 3, 5, 3])
        out = weight.embedding_lookup(indices)
        assert out.shape == (4, 4)
        loss = out.sum()
        loss.backward()
        assert weight.grad is not None
        # Gradient should be non-zero at accessed indices
        assert weight.grad[0].sum() != 0
        assert weight.grad[3].sum() != 0

    def test_cross_entropy(self):
        from osiris.nclm.autograd import Tensor, cross_entropy_loss
        logits = Tensor(np.random.randn(2, 5).astype(np.float32), requires_grad=True)
        targets = np.array([1, 3])
        loss = cross_entropy_loss(logits, targets)
        assert loss.data.size == 1
        loss.backward()
        assert logits.grad is not None

    def test_cross_entropy_3d(self):
        from osiris.nclm.autograd import Tensor, cross_entropy_loss
        logits = Tensor(np.random.randn(2, 3, 256).astype(np.float32), requires_grad=True)
        targets = np.random.randint(0, 256, (2, 3))
        loss = cross_entropy_loss(logits, targets)
        assert loss.data.size == 1
        loss.backward()
        assert logits.grad.shape == (2, 3, 256)

    def test_grad_clip(self):
        from osiris.nclm.autograd import Tensor, clip_grad_norm
        t1 = Tensor(np.zeros(10, dtype=np.float32), requires_grad=True)
        t1.grad = np.ones(10, dtype=np.float32) * 10.0
        t2 = Tensor(np.zeros(10, dtype=np.float32), requires_grad=True)
        t2.grad = np.ones(10, dtype=np.float32) * 10.0
        norm = clip_grad_norm([t1, t2], max_norm=1.0)
        assert norm > 1.0
        new_norm = float(np.sqrt(np.sum(t1.grad ** 2) + np.sum(t2.grad ** 2)))
        np.testing.assert_allclose(new_norm, 1.0, atol=1e-5)


# ===========================================================================
# Layer tests
# ===========================================================================

class TestLayers:
    def test_embedding(self):
        from osiris.nclm.layers import Embedding
        emb = Embedding(256, 32)
        indices = np.array([0, 10, 255, 128])
        out = emb(indices)
        assert out.shape == (4, 32)

    def test_linear(self):
        from osiris.nclm.layers import Linear
        from osiris.nclm.autograd import Tensor
        lin = Linear(16, 8)
        x = Tensor(np.random.randn(2, 16).astype(np.float32), requires_grad=True)
        y = lin(x)
        assert y.shape == (2, 8)
        loss = y.sum()
        loss.backward()
        assert lin.weight.grad is not None

    def test_layernorm(self):
        from osiris.nclm.layers import LayerNorm
        from osiris.nclm.autograd import Tensor
        ln = LayerNorm(16)
        x = Tensor(np.random.randn(2, 3, 16).astype(np.float32), requires_grad=True)
        y = ln(x)
        assert y.shape == (2, 3, 16)
        # Normalized output should have ~zero mean and ~unit variance
        np.testing.assert_allclose(y.data.mean(axis=-1), 0.0, atol=1e-5)
        np.testing.assert_allclose(y.data.var(axis=-1), 1.0, atol=1e-2)

    def test_gelu_layer(self):
        from osiris.nclm.layers import GELU
        from osiris.nclm.autograd import Tensor
        g = GELU()
        x = Tensor(np.array([-1.0, 0.0, 1.0, 2.0], dtype=np.float32))
        y = g(x)
        assert y.shape == (4,)
        # GELU(0) ≈ 0
        np.testing.assert_allclose(y.data[1], 0.0, atol=1e-6)

    def test_dropout_training(self):
        from osiris.nclm.layers import Dropout
        from osiris.nclm.autograd import Tensor
        d = Dropout(0.5)
        d.train()
        x = Tensor(np.ones((100,), dtype=np.float32), requires_grad=True)
        y = d(x)
        # Some values should be zeroed
        assert np.any(y.data == 0.0)

    def test_dropout_eval(self):
        from osiris.nclm.layers import Dropout
        from osiris.nclm.autograd import Tensor
        d = Dropout(0.5)
        d.eval()
        x = Tensor(np.ones((100,), dtype=np.float32))
        y = d(x)
        # No values zeroed in eval mode
        np.testing.assert_array_equal(y.data, x.data)

    def test_module_parameters(self):
        from osiris.nclm.layers import Linear
        lin = Linear(16, 8, bias=True)
        params = lin.parameters()
        assert len(params) == 2  # weight + bias


# ===========================================================================
# Positional encoding tests
# ===========================================================================

class TestPositions:
    def test_shape(self):
        from osiris.nclm.positions import phase_conjugate_positional_encoding
        pe = phase_conjugate_positional_encoding(512, 256)
        assert pe.shape == (512, 256)

    def test_first_position_nonzero(self):
        from osiris.nclm.positions import phase_conjugate_positional_encoding
        pe = phase_conjugate_positional_encoding(10, 32)
        # Position 0 should be all zeros (sin(0)=0, cos(0)=1 for some dims)
        # but position 1 should have variation
        assert np.std(pe.data[1]) > 0.01

    def test_distinct_positions(self):
        from osiris.nclm.positions import phase_conjugate_positional_encoding
        pe = phase_conjugate_positional_encoding(100, 64)
        # Adjacent positions should be different
        diff = np.linalg.norm(pe.data[0] - pe.data[1])
        assert diff > 0.01


# ===========================================================================
# Transformer tests
# ===========================================================================

class TestTransformer:
    def _small_config(self):
        from osiris.nclm.transformer import SovereignConfig
        return SovereignConfig(
            vocab_size=256, dim=32, n_layers=2, n_heads=2,
            ff_dim=64, max_seq_len=64, dropout=0.0,
        )

    def test_forward_shape(self):
        from osiris.nclm.transformer import SovereignTransformer
        cfg = self._small_config()
        model = SovereignTransformer(cfg)
        x = np.array([[0, 1, 2, 3, 4]], dtype=np.int64)
        logits = model.forward(x)
        assert logits.shape == (1, 5, 256)

    def test_forward_backward(self):
        from osiris.nclm.transformer import SovereignTransformer
        from osiris.nclm.autograd import cross_entropy_loss
        cfg = self._small_config()
        model = SovereignTransformer(cfg)
        x = np.array([[10, 20, 30, 40]], dtype=np.int64)
        y = np.array([[20, 30, 40, 50]], dtype=np.int64)
        logits = model.forward(x)
        loss = cross_entropy_loss(logits, y)
        loss.backward()
        # Every parameter should have a gradient
        for p in model.parameters():
            assert p.grad is not None, f"No gradient for param {p.name}"

    def test_generate(self):
        from osiris.nclm.transformer import SovereignTransformer
        cfg = self._small_config()
        model = SovereignTransformer(cfg)
        text = model.generate("hello", max_new_tokens=10, temperature=1.0)
        assert len(text) >= 5  # at least the prompt

    def test_state_dict_roundtrip(self):
        from osiris.nclm.transformer import SovereignTransformer
        cfg = self._small_config()
        model1 = SovereignTransformer(cfg)
        sd = model1.state_dict()

        model2 = SovereignTransformer(cfg)
        model2.load_state_dict(sd)

        x = np.array([[1, 2, 3]], dtype=np.int64)
        from osiris.nclm.autograd import no_grad
        with no_grad():
            out1 = model1.forward(x).data
            out2 = model2.forward(x).data
        np.testing.assert_array_equal(out1, out2)

    def test_param_count(self):
        from osiris.nclm.transformer import SovereignTransformer, SovereignConfig
        cfg = SovereignConfig()
        model = SovereignTransformer(cfg)
        n = model.num_parameters()
        # Expected ~5M for default config
        assert 1_000_000 < n < 10_000_000, f"Param count {n} outside 1-10M range"

    def test_consciousness_phi(self):
        from osiris.nclm.transformer import SovereignTransformer
        cfg = self._small_config()
        model = SovereignTransformer(cfg)
        ids = np.arange(16, dtype=np.int64).reshape(1, 16)
        phi = model.consciousness_phi(ids)
        assert 0.0 <= phi <= 1.0

    def test_causal_mask(self):
        from osiris.nclm.transformer import SovereignTransformer
        mask = SovereignTransformer._build_causal_mask(4)
        # Position 0 can attend to itself only
        assert mask[0, 0, 0, 0] == 0.0
        assert mask[0, 0, 0, 1] < -1e8
        # Position 3 can attend to all
        assert mask[0, 0, 3, 0] == 0.0
        assert mask[0, 0, 3, 3] == 0.0


# ===========================================================================
# Optimizer tests
# ===========================================================================

class TestOptimizer:
    def test_adamw_step(self):
        from osiris.nclm.autograd import Tensor
        from osiris.nclm.optimizer import AdamW
        p = Tensor(np.array([1.0, 2.0, 3.0], dtype=np.float32), requires_grad=True)
        p.grad = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        optimizer = AdamW([p], lr=0.01)
        old_data = p.data.copy()
        optimizer.step()
        # Parameters should have changed
        assert not np.array_equal(p.data, old_data)

    def test_lr_schedule(self):
        from osiris.nclm.optimizer import LRSchedule
        schedule = LRSchedule(warmup_steps=10, total_steps=100)
        # Warmup: LR should increase
        lr0 = schedule.get_lr(0, 1.0)
        lr5 = schedule.get_lr(5, 1.0)
        assert lr5 > lr0
        # After warmup: LR should decrease
        lr20 = schedule.get_lr(20, 1.0)
        lr80 = schedule.get_lr(80, 1.0)
        assert lr80 < lr20

    def test_zero_grad(self):
        from osiris.nclm.autograd import Tensor
        from osiris.nclm.optimizer import AdamW
        p = Tensor(np.ones(5, dtype=np.float32), requires_grad=True)
        p.grad = np.ones(5, dtype=np.float32)
        opt = AdamW([p], lr=0.01)
        opt.zero_grad()
        assert p.grad is None


# ===========================================================================
# Trainer tests
# ===========================================================================

class TestTrainer:
    def test_byte_dataset(self):
        from osiris.nclm.trainer import ByteDataset
        data = b"Hello, world! This is a test corpus for training."
        ds = ByteDataset(data, seq_len=8)
        assert len(ds) > 0
        x, y = ds.get_batch(2)
        assert x.shape == (2, 8)
        assert y.shape == (2, 8)
        # y should be x shifted by 1
        raw = np.frombuffer(data, dtype=np.uint8).copy()
        for i in range(2):
            for j in range(8):
                start = int(np.where(raw == x[i, 0])[0][0]) if x[i, 0] in raw else -1
                if start >= 0:
                    assert y[i, j] == raw[start + j + 1]
                    break

    def test_corpus_load(self):
        from osiris.nclm.trainer import Corpus
        with tempfile.TemporaryDirectory() as d:
            # Create some test files
            with open(os.path.join(d, "test.py"), "w") as f:
                f.write("print('hello')\n")
            with open(os.path.join(d, "readme.md"), "w") as f:
                f.write("# Test\n")
            corpus = Corpus(d, [".py", ".md"])
            n = corpus.load()
            assert n > 0
            assert b"hello" in corpus.data


# ===========================================================================
# Inference tests
# ===========================================================================

class TestInference:
    def test_top_p_filter(self):
        from osiris.nclm.inference import top_p_filter
        logits = np.array([10.0, 5.0, 1.0, 0.5, 0.1], dtype=np.float32)
        filtered = top_p_filter(logits, 0.9)
        # Highest logit should survive
        assert filtered[0] == logits[0]
        # Lowest should be masked
        assert filtered[-1] < -1e8

    def test_safetensors_roundtrip(self):
        from osiris.nclm.transformer import SovereignTransformer, SovereignConfig
        from osiris.nclm.inference import save_safetensors, load_safetensors
        from osiris.nclm.autograd import no_grad

        cfg = SovereignConfig(dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32)
        model = SovereignTransformer(cfg)

        with tempfile.NamedTemporaryFile(suffix=".safetensors", delete=False) as f:
            path = f.name

        try:
            save_safetensors(model, path)
            sd_loaded = load_safetensors(path)

            sd_orig = model.state_dict()
            for key in sd_orig:
                np.testing.assert_array_equal(sd_orig[key], sd_loaded[key])
        finally:
            os.unlink(path)

    def test_generate_function(self):
        from osiris.nclm.transformer import SovereignTransformer, SovereignConfig
        from osiris.nclm.inference import generate

        cfg = SovereignConfig(dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32)
        model = SovereignTransformer(cfg)

        text = generate(model, "ab", max_new_tokens=5, temperature=1.0, top_k=10, top_p=0.9)
        assert len(text) >= 2  # at least prompt

    def test_export_huggingface(self):
        from osiris.nclm.transformer import SovereignTransformer, SovereignConfig
        from osiris.nclm.inference import export_huggingface

        cfg = SovereignConfig(dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32)
        model = SovereignTransformer(cfg)

        with tempfile.TemporaryDirectory() as d:
            export_huggingface(model, d)
            assert os.path.exists(os.path.join(d, "model.safetensors"))
            assert os.path.exists(os.path.join(d, "config.json"))
            assert os.path.exists(os.path.join(d, "tokenizer_config.json"))
            assert os.path.exists(os.path.join(d, "README.md"))


# ===========================================================================
# Integration: training convergence smoke test
# ===========================================================================

class TestTrainingConvergence:
    def test_loss_decreases(self):
        """Verify that loss decreases over a few steps on a tiny corpus."""
        from osiris.nclm.transformer import SovereignTransformer, SovereignConfig
        from osiris.nclm.autograd import cross_entropy_loss
        from osiris.nclm.optimizer import AdamW

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64,
            max_seq_len=32, dropout=0.0,
        )
        model = SovereignTransformer(cfg)
        model.train()
        optimizer = AdamW(model.parameters(), lr=1e-3)

        # Tiny repeating corpus
        text = b"Hello World! " * 100
        raw = np.frombuffer(text, dtype=np.uint8).copy()
        seq_len = 16

        losses = []
        for step in range(20):
            start = np.random.randint(0, len(raw) - seq_len - 1, size=2)
            x = np.array([raw[s:s+seq_len] for s in start], dtype=np.int64)
            y = np.array([raw[s+1:s+1+seq_len] for s in start], dtype=np.int64)

            optimizer.zero_grad()
            logits = model.forward(x)
            loss = cross_entropy_loss(logits, y)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        # Loss at end should be lower than loss at start (averaged)
        avg_first = np.mean(losses[:5])
        avg_last = np.mean(losses[-5:])
        assert avg_last < avg_first, (
            f"Loss did not decrease: first={avg_first:.4f}, last={avg_last:.4f}"
        )


# ===========================================================================
# Checkpoint round-trip test
# ===========================================================================

class TestCheckpoint:
    def test_npz_roundtrip(self):
        from osiris.nclm.transformer import SovereignTransformer, SovereignConfig
        from osiris.nclm.trainer import Trainer
        from osiris.nclm.autograd import no_grad

        cfg = SovereignConfig(dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32)
        model = SovereignTransformer(cfg)

        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name

        try:
            sd = model.state_dict()
            np.savez_compressed(path, **sd)

            model2 = Trainer.load_checkpoint(path, config=cfg)

            x = np.array([[1, 2, 3, 4]], dtype=np.int64)
            with no_grad():
                out1 = model.forward(x).data
                out2 = model2.forward(x).data
            np.testing.assert_array_equal(out1, out2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ===========================================================================
# 11D-CRSM Sovereign Mechanics tests
# ===========================================================================

class TestSovereignMechanics:
    """Tests for TorsionLockedAttention, PhaseConjugateCorrector,
    FractalAntennaEmbedding, SovereignBlock, NegentropicTracker,
    and SovereignTransformerV2."""

    # --- TorsionLockedAttention ---

    def test_torsion_locked_attention_shapes(self):
        from osiris.nclm.sovereign_mechanics import TorsionLockedAttention
        from osiris.nclm.autograd import Tensor, no_grad

        attn = TorsionLockedAttention(dim=32, n_heads=2, dropout=0.0)
        x = Tensor(np.random.randn(1, 8, 32).astype(np.float32))
        with no_grad():
            out = attn(x)
        assert out.shape == (1, 8, 32)

    def test_torsion_locked_attention_backward(self):
        from osiris.nclm.sovereign_mechanics import TorsionLockedAttention
        from osiris.nclm.autograd import Tensor

        attn = TorsionLockedAttention(dim=32, n_heads=2, dropout=0.0)
        x = Tensor(np.random.randn(1, 4, 32).astype(np.float32), requires_grad=True)
        out = attn(x)
        loss = out.sum()
        loss.backward()
        # Gradients should flow through tlock params
        assert attn.tlock_alpha.grad is not None
        assert attn.tlock_beta.grad is not None
        assert x.grad is not None

    def test_torsion_locked_attention_with_mask(self):
        from osiris.nclm.sovereign_mechanics import TorsionLockedAttention
        from osiris.nclm.autograd import Tensor, no_grad

        attn = TorsionLockedAttention(dim=32, n_heads=2, dropout=0.0)
        x = Tensor(np.random.randn(1, 8, 32).astype(np.float32))
        mask = np.full((1, 1, 8, 8), -1e9, dtype=np.float32)
        mask = np.triu(mask, k=1)
        with no_grad():
            out = attn(x, mask=mask)
        assert out.shape == (1, 8, 32)

    # --- PhaseConjugateCorrector ---

    def test_phase_conjugate_low_gamma_passthrough(self):
        from osiris.nclm.sovereign_mechanics import PhaseConjugateCorrector
        from osiris.nclm.autograd import Tensor

        pc = PhaseConjugateCorrector(dim=32)
        # Small variance -> Gamma < 0.3 -> passthrough
        x = Tensor(np.random.randn(1, 4, 32).astype(np.float32) * 0.01)
        out = pc(x)
        # Should return same tensor (passthrough)
        np.testing.assert_array_equal(out.data, x.data)

    def test_phase_conjugate_high_gamma_correction(self):
        from osiris.nclm.sovereign_mechanics import PhaseConjugateCorrector
        from osiris.nclm.autograd import Tensor

        pc = PhaseConjugateCorrector(dim=32)
        # Large variance -> Gamma > 0.3 -> correction applied
        x = Tensor(
            np.random.randn(1, 4, 32).astype(np.float32) * 10.0,
            requires_grad=True,
        )
        out = pc(x)
        # Output should differ from input (correction applied)
        assert not np.allclose(out.data, x.data, atol=1e-6)

    def test_phase_conjugate_decoherence_gamma(self):
        from osiris.nclm.sovereign_mechanics import PhaseConjugateCorrector
        from osiris.nclm.autograd import Tensor

        pc = PhaseConjugateCorrector(dim=32)
        x = Tensor(np.random.randn(1, 4, 32).astype(np.float32) * 5.0)
        gamma = pc.decoherence_gamma(x)
        assert 0.0 <= gamma <= 1.0

    # --- FractalAntennaEmbedding ---

    def test_fractal_embedding_shapes(self):
        from osiris.nclm.sovereign_mechanics import FractalAntennaEmbedding
        from osiris.nclm.autograd import no_grad

        emb = FractalAntennaEmbedding(vocab_size=256, dim=32, n_modes=133)
        indices = np.array([[1, 2, 3, 4]], dtype=np.int64)
        with no_grad():
            out = emb(indices)
        assert out.shape == (1, 4, 32)

    def test_fractal_embedding_133_modes(self):
        from osiris.nclm.sovereign_mechanics import FractalAntennaEmbedding

        emb = FractalAntennaEmbedding(vocab_size=256, dim=64, n_modes=133)
        assert emb.resonance_in.shape == (133, 64)
        assert emb.resonance_out.shape == (64, 133)
        assert emb.omega.shape == (133,)

    def test_fractal_embedding_frequencies(self):
        from osiris.nclm.sovereign_mechanics import FractalAntennaEmbedding

        omega = FractalAntennaEmbedding._compute_fractal_frequencies(133)
        assert omega.shape == (133,)
        assert float(omega.min()) >= 0.09  # ~0.1
        assert float(omega.max()) <= 2.01  # ~2.0

    # --- SovereignBlock ---

    def test_sovereign_block_forward(self):
        from osiris.nclm.sovereign_mechanics import SovereignBlock
        from osiris.nclm.autograd import Tensor, no_grad

        block = SovereignBlock(dim=32, n_heads=2, ff_dim=64, dropout=0.0)
        x = Tensor(np.random.randn(1, 8, 32).astype(np.float32))
        with no_grad():
            out = block(x)
        assert out.shape == (1, 8, 32)

    def test_sovereign_block_backward(self):
        from osiris.nclm.sovereign_mechanics import SovereignBlock
        from osiris.nclm.autograd import Tensor

        block = SovereignBlock(dim=32, n_heads=2, ff_dim=64, dropout=0.0)
        x = Tensor(np.random.randn(1, 4, 32).astype(np.float32), requires_grad=True)
        out = block(x)
        loss = out.sum()
        loss.backward()
        assert x.grad is not None
        assert x.grad.shape == (1, 4, 32)

    # --- NegentropicTracker ---

    def test_negentropic_tracker_metrics(self):
        from osiris.nclm.sovereign_mechanics import NegentropicTracker

        tracker = NegentropicTracker()
        x_in = np.random.randn(1, 4, 32).astype(np.float32)
        x_out = np.random.randn(1, 4, 32).astype(np.float32) * 0.5
        m = tracker.measure(x_in, x_out)
        assert "xi" in m
        assert "phi" in m
        assert "gamma" in m
        assert "lambda_phi" in m
        assert "negentropic" in m
        assert isinstance(m["negentropic"], bool)

    def test_negentropic_tracker_summary(self):
        from osiris.nclm.sovereign_mechanics import NegentropicTracker

        tracker = NegentropicTracker()
        for _ in range(5):
            x_in = np.random.randn(1, 4, 32).astype(np.float32)
            x_out = np.random.randn(1, 4, 32).astype(np.float32) * 0.1
            tracker.measure(x_in, x_out)
        s = tracker.summary()
        assert s["n_measurements"] == 5
        assert "mean_xi" in s
        assert "negentropic_ratio" in s

    # --- SovereignTransformerV2 ---

    def test_v2_forward_shape(self):
        from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig
        from osiris.nclm.autograd import no_grad

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32,
            torsion_lock=True, phase_conjugate=True, fractal_embedding=True,
        )
        model = SovereignTransformerV2(cfg)
        x = np.array([[1, 2, 3, 4]], dtype=np.int64)
        with no_grad():
            logits = model.forward(x)
        assert logits.shape == (1, 4, 256)

    def test_v2_backward(self):
        from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig
        from osiris.nclm.autograd import cross_entropy_loss

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32,
            torsion_lock=True, phase_conjugate=True, fractal_embedding=True,
            dropout=0.0,
        )
        model = SovereignTransformerV2(cfg)
        x = np.array([[1, 2, 3, 4]], dtype=np.int64)
        targets = np.array([[2, 3, 4, 5]], dtype=np.int64)
        logits = model.forward(x)
        loss = cross_entropy_loss(logits, targets)
        loss.backward()
        # Check at least some params got gradients
        params_with_grad = [p for p in model.parameters() if p.grad is not None]
        assert len(params_with_grad) > 0

    def test_v2_state_dict_roundtrip(self):
        from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig
        from osiris.nclm.autograd import no_grad

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32,
            torsion_lock=True, phase_conjugate=True, fractal_embedding=True,
        )
        model = SovereignTransformerV2(cfg)
        sd = model.state_dict()

        model2 = SovereignTransformerV2(cfg)
        model2.load_state_dict(sd)

        x = np.array([[1, 2, 3, 4]], dtype=np.int64)
        with no_grad():
            out1 = model.forward(x).data
            out2 = model2.forward(x).data
        np.testing.assert_array_almost_equal(out1, out2, decimal=5)

    def test_v2_backward_compat(self):
        """V2 with all flags False should behave like V1."""
        from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig
        from osiris.nclm.autograd import no_grad

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32,
        )
        model = SovereignTransformerV2(cfg)
        x = np.array([[1, 2, 3, 4]], dtype=np.int64)
        with no_grad():
            logits = model.forward(x)
        assert logits.shape == (1, 4, 256)
        # state_dict should use standard key names
        sd = model.state_dict()
        assert "tok_emb.weight" in sd
        assert "blocks.0.attn.q_proj.weight" in sd

    def test_v2_generate(self):
        from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32,
            torsion_lock=True, fractal_embedding=True,
        )
        model = SovereignTransformerV2(cfg)
        text = model.generate("hi", max_new_tokens=5, temperature=1.0)
        assert isinstance(text, str)
        assert len(text) >= 2  # at least the prompt

    def test_v2_consciousness_phi(self):
        from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig

        cfg = SovereignConfig(
            dim=32, n_layers=1, n_heads=2, ff_dim=64, max_seq_len=32,
            torsion_lock=True, phase_conjugate=True,
        )
        model = SovereignTransformerV2(cfg)
        x = np.array([[1, 2, 3, 4]], dtype=np.int64)
        phi = model.consciousness_phi(x)
        assert 0.0 <= phi <= 2.0

    def test_v2_param_count_larger_than_v1(self):
        from osiris.nclm.transformer import (
            SovereignTransformer, SovereignTransformerV2, SovereignConfig,
        )

        base_cfg = SovereignConfig(dim=64, n_layers=2, n_heads=2, ff_dim=128, max_seq_len=32)
        v1 = SovereignTransformer(base_cfg)

        v2_cfg = SovereignConfig(
            dim=64, n_layers=2, n_heads=2, ff_dim=128, max_seq_len=32,
            torsion_lock=True, phase_conjugate=True, fractal_embedding=True,
        )
        v2 = SovereignTransformerV2(v2_cfg)

        assert v2.num_parameters() > v1.num_parameters()
