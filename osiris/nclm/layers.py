"""
Neural Network Layers — numpy only.
=====================================

Building blocks for the SovereignTransformer, implemented atop the
autograd engine.  Every layer exposes a ``parameters()`` list for
the optimizer and a ``__call__`` forward path.

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import numpy as np
from typing import List

from .autograd import Tensor, gelu as _gelu, _is_grad_enabled


# ---------------------------------------------------------------------------
# Base Module
# ---------------------------------------------------------------------------

class Module:
    """Base class — provides parameter collection and train/eval modes."""

    _training: bool = True

    def parameters(self) -> List[Tensor]:
        params: List[Tensor] = []
        for v in self.__dict__.values():
            if isinstance(v, Tensor) and v.requires_grad:
                params.append(v)
            elif isinstance(v, Module):
                params.extend(v.parameters())
            elif isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, Module):
                        params.extend(item.parameters())
                    elif isinstance(item, Tensor) and item.requires_grad:
                        params.append(item)
        return params

    def train(self):
        self._training = True
        for v in self.__dict__.values():
            if isinstance(v, Module):
                v.train()
            elif isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, Module):
                        item.train()

    def eval(self):
        self._training = False
        for v in self.__dict__.values():
            if isinstance(v, Module):
                v.eval()
            elif isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, Module):
                        item.eval()

    def zero_grad(self):
        for p in self.parameters():
            p.zero_grad()

    def num_parameters(self) -> int:
        return sum(p.data.size for p in self.parameters())


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

class Embedding(Module):
    """Learnable lookup table: (vocab_size, dim)."""

    def __init__(self, vocab_size: int, dim: int):
        self.weight = Tensor(
            (np.random.randn(vocab_size, dim) * 0.02).astype(np.float32),
            requires_grad=True,
            name="embedding.weight",
        )
        self.vocab_size = vocab_size
        self.dim = dim

    def __call__(self, indices: np.ndarray) -> Tensor:
        """indices: integer array of any shape → (*shape, dim)."""
        return self.weight.embedding_lookup(indices)


# ---------------------------------------------------------------------------
# Linear
# ---------------------------------------------------------------------------

class Linear(Module):
    """Fully-connected layer: y = x @ W^T + b."""

    def __init__(self, in_dim: int, out_dim: int, bias: bool = True):
        # Kaiming / He init
        scale = np.sqrt(2.0 / in_dim)
        self.weight = Tensor(
            (np.random.randn(out_dim, in_dim) * scale).astype(np.float32),
            requires_grad=True,
            name="linear.weight",
        )
        self.bias_param = None
        if bias:
            self.bias_param = Tensor(
                np.zeros(out_dim, dtype=np.float32),
                requires_grad=True,
                name="linear.bias",
            )

    def __call__(self, x: Tensor) -> Tensor:
        # x: (..., in_dim) → (..., out_dim)
        out = x.matmul(self.weight.transpose(0, 1))
        if self.bias_param is not None:
            out = out + self.bias_param
        return out


# ---------------------------------------------------------------------------
# LayerNorm
# ---------------------------------------------------------------------------

class LayerNorm(Module):
    """Layer normalization over the last dimension."""

    def __init__(self, dim: int, eps: float = 1e-5):
        self.gamma = Tensor(
            np.ones(dim, dtype=np.float32),
            requires_grad=True,
            name="layernorm.gamma",
        )
        self.beta = Tensor(
            np.zeros(dim, dtype=np.float32),
            requires_grad=True,
            name="layernorm.beta",
        )
        self.eps = eps
        self.dim = dim

    def __call__(self, x: Tensor) -> Tensor:
        mean = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        x_norm = (x - mean) / (var + self.eps).sqrt()
        return x_norm * self.gamma + self.beta


# ---------------------------------------------------------------------------
# GELU
# ---------------------------------------------------------------------------

class GELU(Module):
    """GELU activation (approximate)."""

    def __call__(self, x: Tensor) -> Tensor:
        return _gelu(x)


# ---------------------------------------------------------------------------
# Dropout
# ---------------------------------------------------------------------------

class Dropout(Module):
    """Dropout — zeroes elements with probability `rate` during training."""

    def __init__(self, rate: float = 0.1):
        self.rate = rate

    def __call__(self, x: Tensor) -> Tensor:
        if not self._training or self.rate == 0.0 or not _is_grad_enabled():
            return x
        mask = (np.random.rand(*x.shape) > self.rate).astype(np.float32)
        scale = 1.0 / (1.0 - self.rate)
        out = Tensor(x.data * mask * scale, requires_grad=x.requires_grad)
        out._prev = [x]

        if x.requires_grad:
            def _backward():
                x._ensure_grad()
                x.grad = x.grad + out.grad * mask * scale
            out._backward_fn = _backward
        return out
