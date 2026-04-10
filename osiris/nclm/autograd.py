"""
Tape-based Autograd Engine — numpy only.
=========================================

Minimal reverse-mode automatic differentiation for the SovereignTransformer.
Every differentiable operation records itself on a tape; calling .backward()
propagates gradients via the chain rule.

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import contextlib
import numpy as np
from typing import List, Optional, Tuple, Callable

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_NO_GRAD = False


@contextlib.contextmanager
def no_grad():
    """Context manager to disable gradient tracking."""
    global _NO_GRAD
    prev = _NO_GRAD
    _NO_GRAD = True
    try:
        yield
    finally:
        _NO_GRAD = prev


def _is_grad_enabled() -> bool:
    return not _NO_GRAD


# ---------------------------------------------------------------------------
# Tensor
# ---------------------------------------------------------------------------

class Tensor:
    """Differentiable tensor wrapping a numpy ndarray."""

    __slots__ = ("data", "grad", "requires_grad", "_backward_fn", "_prev", "name")

    def __init__(
        self,
        data: np.ndarray,
        requires_grad: bool = False,
        name: str = "",
    ):
        if not isinstance(data, np.ndarray):
            data = np.array(data, dtype=np.float32)
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        self.data = data
        self.grad: Optional[np.ndarray] = None
        self.requires_grad = requires_grad
        self._backward_fn: Optional[Callable] = None
        self._prev: List[Tensor] = []
        self.name = name

    # -- properties ---------------------------------------------------------

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.data.shape

    @property
    def ndim(self) -> int:
        return self.data.ndim

    @property
    def dtype(self):
        return self.data.dtype

    @property
    def T(self) -> "Tensor":
        return self.transpose()

    def __repr__(self):
        g = ", grad" if self.requires_grad else ""
        n = f", name={self.name}" if self.name else ""
        return f"Tensor(shape={self.shape}{g}{n})"

    def __len__(self):
        return self.data.shape[0]

    # -- numpy interop ------------------------------------------------------

    def numpy(self) -> np.ndarray:
        return self.data

    def item(self) -> float:
        return float(self.data.item())

    def detach(self) -> "Tensor":
        return Tensor(self.data.copy(), requires_grad=False)

    def clone(self) -> "Tensor":
        t = Tensor(self.data.copy(), requires_grad=self.requires_grad)
        return t

    # -- gradient utilities -------------------------------------------------

    def zero_grad(self):
        self.grad = None

    def _ensure_grad(self):
        if self.grad is None:
            self.grad = np.zeros_like(self.data)

    # -- backward -----------------------------------------------------------

    def backward(self, grad: Optional[np.ndarray] = None):
        """Reverse-mode autodiff from this tensor."""
        if grad is None:
            assert self.data.size == 1, "backward() requires scalar output or explicit grad"
            grad = np.ones_like(self.data)

        # Topological sort
        topo: List[Tensor] = []
        visited = set()

        def _build(t: Tensor):
            if id(t) not in visited:
                visited.add(id(t))
                for p in t._prev:
                    _build(p)
                topo.append(t)

        _build(self)

        self._ensure_grad()
        self.grad = self.grad + grad

        for t in reversed(topo):
            if t._backward_fn is not None:
                t._backward_fn()

    # -- Constructors -------------------------------------------------------

    @staticmethod
    def zeros(shape, requires_grad=False):
        return Tensor(np.zeros(shape, dtype=np.float32), requires_grad=requires_grad)

    @staticmethod
    def ones(shape, requires_grad=False):
        return Tensor(np.ones(shape, dtype=np.float32), requires_grad=requires_grad)

    @staticmethod
    def randn(*shape, requires_grad=False):
        return Tensor(np.random.randn(*shape).astype(np.float32), requires_grad=requires_grad)

    @staticmethod
    def from_numpy(arr: np.ndarray, requires_grad=False):
        return Tensor(arr, requires_grad=requires_grad)

    # ===================================================================
    # Forward ops  (each records a backward closure when grad is enabled)
    # ===================================================================

    # -- addition -----------------------------------------------------------

    def __add__(self, other):
        other = _ensure_tensor(other)
        out = Tensor(self.data + other.data, requires_grad=(self.requires_grad or other.requires_grad))
        out._prev = [self, other]

        if _is_grad_enabled() and out.requires_grad:
            def _backward():
                if self.requires_grad:
                    self._ensure_grad()
                    g = _unbroadcast(out.grad, self.shape)
                    self.grad = self.grad + g
                if other.requires_grad:
                    other._ensure_grad()
                    g = _unbroadcast(out.grad, other.shape)
                    other.grad = other.grad + g
            out._backward_fn = _backward
        return out

    def __radd__(self, other):
        return self.__add__(other)

    # -- subtraction --------------------------------------------------------

    def __sub__(self, other):
        other = _ensure_tensor(other)
        out = Tensor(self.data - other.data, requires_grad=(self.requires_grad or other.requires_grad))
        out._prev = [self, other]

        if _is_grad_enabled() and out.requires_grad:
            def _backward():
                if self.requires_grad:
                    self._ensure_grad()
                    self.grad = self.grad + _unbroadcast(out.grad, self.shape)
                if other.requires_grad:
                    other._ensure_grad()
                    other.grad = other.grad - _unbroadcast(out.grad, other.shape)
            out._backward_fn = _backward
        return out

    def __rsub__(self, other):
        other = _ensure_tensor(other)
        return other.__sub__(self)

    # -- negation -----------------------------------------------------------

    def __neg__(self):
        out = Tensor(-self.data, requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad - out.grad
            out._backward_fn = _backward
        return out

    # -- element-wise multiplication ----------------------------------------

    def __mul__(self, other):
        other = _ensure_tensor(other)
        out = Tensor(self.data * other.data, requires_grad=(self.requires_grad or other.requires_grad))
        out._prev = [self, other]

        if _is_grad_enabled() and out.requires_grad:
            def _backward():
                if self.requires_grad:
                    self._ensure_grad()
                    g = _unbroadcast(out.grad * other.data, self.shape)
                    self.grad = self.grad + g
                if other.requires_grad:
                    other._ensure_grad()
                    g = _unbroadcast(out.grad * self.data, other.shape)
                    other.grad = other.grad + g
            out._backward_fn = _backward
        return out

    def __rmul__(self, other):
        return self.__mul__(other)

    # -- element-wise division ----------------------------------------------

    def __truediv__(self, other):
        other = _ensure_tensor(other)
        out = Tensor(self.data / other.data, requires_grad=(self.requires_grad or other.requires_grad))
        out._prev = [self, other]

        if _is_grad_enabled() and out.requires_grad:
            def _backward():
                if self.requires_grad:
                    self._ensure_grad()
                    g = _unbroadcast(out.grad / other.data, self.shape)
                    self.grad = self.grad + g
                if other.requires_grad:
                    other._ensure_grad()
                    g = _unbroadcast(-out.grad * self.data / (other.data ** 2), other.shape)
                    other.grad = other.grad + g
            out._backward_fn = _backward
        return out

    def __rtruediv__(self, other):
        other = _ensure_tensor(other)
        return other.__truediv__(self)

    # -- power --------------------------------------------------------------

    def __pow__(self, exp: float):
        out = Tensor(self.data ** exp, requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad * exp * (self.data ** (exp - 1))
            out._backward_fn = _backward
        return out

    # -- matmul -------------------------------------------------------------

    def matmul(self, other: "Tensor") -> "Tensor":
        out = Tensor(self.data @ other.data, requires_grad=(self.requires_grad or other.requires_grad))
        out._prev = [self, other]

        if _is_grad_enabled() and out.requires_grad:
            def _backward():
                if self.requires_grad:
                    self._ensure_grad()
                    # (..., M, K) @ (..., K, N) -> (..., M, N)
                    # dL/dA = dL/dC @ B^T
                    g = out.grad @ _swap_last_two(other.data)
                    self.grad = self.grad + g
                if other.requires_grad:
                    other._ensure_grad()
                    # dL/dB = A^T @ dL/dC
                    g = _swap_last_two(self.data) @ out.grad
                    other.grad = other.grad + g
            out._backward_fn = _backward
        return out

    def __matmul__(self, other):
        return self.matmul(_ensure_tensor(other))

    # -- transpose ----------------------------------------------------------

    def transpose(self, dim0: int = -2, dim1: int = -1) -> "Tensor":
        axes = list(range(self.ndim))
        axes[dim0], axes[dim1] = axes[dim1], axes[dim0]
        out = Tensor(np.transpose(self.data, axes), requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            inv_axes = [0] * len(axes)
            for i, a in enumerate(axes):
                inv_axes[a] = i

            def _backward():
                self._ensure_grad()
                self.grad = self.grad + np.transpose(out.grad, inv_axes)
            out._backward_fn = _backward
        return out

    # -- reshape ------------------------------------------------------------

    def reshape(self, *shape) -> "Tensor":
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            shape = tuple(shape[0])
        orig_shape = self.shape
        out = Tensor(self.data.reshape(shape), requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad.reshape(orig_shape)
            out._backward_fn = _backward
        return out

    # -- sum ----------------------------------------------------------------

    def sum(self, axis=None, keepdims=False) -> "Tensor":
        out = Tensor(
            np.sum(self.data, axis=axis, keepdims=keepdims),
            requires_grad=self.requires_grad,
        )
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                g = out.grad
                if axis is not None and not keepdims:
                    if isinstance(axis, int):
                        g = np.expand_dims(g, axis)
                    else:
                        for ax in sorted(axis):
                            g = np.expand_dims(g, ax)
                self.grad = self.grad + np.broadcast_to(g, self.shape)
            out._backward_fn = _backward
        return out

    # -- mean ---------------------------------------------------------------

    def mean(self, axis=None, keepdims=False) -> "Tensor":
        n = self.data.size if axis is None else (
            self.data.shape[axis] if isinstance(axis, int) else
            int(np.prod([self.data.shape[a] for a in axis]))
        )
        out = Tensor(
            np.mean(self.data, axis=axis, keepdims=keepdims),
            requires_grad=self.requires_grad,
        )
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                g = out.grad
                if axis is not None and not keepdims:
                    if isinstance(axis, int):
                        g = np.expand_dims(g, axis)
                    else:
                        for ax in sorted(axis):
                            g = np.expand_dims(g, ax)
                self.grad = self.grad + np.broadcast_to(g, self.shape) / n
            out._backward_fn = _backward
        return out

    # -- variance -----------------------------------------------------------

    def var(self, axis=None, keepdims=False) -> "Tensor":
        mu = np.mean(self.data, axis=axis, keepdims=True)
        n = self.data.size if axis is None else (
            self.data.shape[axis] if isinstance(axis, int) else
            int(np.prod([self.data.shape[a] for a in axis]))
        )
        out = Tensor(
            np.var(self.data, axis=axis, keepdims=keepdims),
            requires_grad=self.requires_grad,
        )
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                g = out.grad
                if axis is not None and not keepdims:
                    if isinstance(axis, int):
                        g = np.expand_dims(g, axis)
                    else:
                        for ax in sorted(axis):
                            g = np.expand_dims(g, ax)
                self.grad = self.grad + (2.0 / n) * (self.data - mu) * np.broadcast_to(g, self.shape)
            out._backward_fn = _backward
        return out

    # -- exp ----------------------------------------------------------------

    def exp(self) -> "Tensor":
        e = np.exp(np.clip(self.data, -88, 88))  # prevent overflow
        out = Tensor(e, requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad * e
            out._backward_fn = _backward
        return out

    # -- log ----------------------------------------------------------------

    def log(self) -> "Tensor":
        safe = np.clip(self.data, 1e-12, None)
        out = Tensor(np.log(safe), requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad / safe
            out._backward_fn = _backward
        return out

    # -- sqrt ---------------------------------------------------------------

    def sqrt(self) -> "Tensor":
        safe = np.clip(self.data, 1e-12, None)
        s = np.sqrt(safe)
        out = Tensor(s, requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad / (2.0 * s)
            out._backward_fn = _backward
        return out

    # -- tanh ---------------------------------------------------------------

    def tanh(self) -> "Tensor":
        t = np.tanh(self.data)
        out = Tensor(t, requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad * (1.0 - t ** 2)
            out._backward_fn = _backward
        return out

    # -- max (element-wise clamp from below) --------------------------------

    def clamp_min(self, min_val: float) -> "Tensor":
        out = Tensor(np.maximum(self.data, min_val), requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            mask = (self.data >= min_val).astype(np.float32)
            def _backward():
                self._ensure_grad()
                self.grad = self.grad + out.grad * mask
            out._backward_fn = _backward
        return out

    # -- indexing (gather for embedding lookup) -----------------------------

    def embedding_lookup(self, indices: np.ndarray) -> "Tensor":
        """self is (V, D), indices is integer array → output is (*indices.shape, D)."""
        out = Tensor(self.data[indices], requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                np.add.at(self.grad, indices, out.grad)
            out._backward_fn = _backward
        return out

    # -- slice along axis 1 (sequence dimension) ----------------------------

    def slice_seq(self, start: int, end: int) -> "Tensor":
        """Slice along axis=1: self[:, start:end, ...]."""
        out = Tensor(self.data[:, start:end], requires_grad=self.requires_grad)
        out._prev = [self]

        if _is_grad_enabled() and self.requires_grad:
            def _backward():
                self._ensure_grad()
                self.grad[:, start:end] += out.grad
            out._backward_fn = _backward
        return out

    # -- concatenation along last axis --------------------------------------

    def cat(self, other: "Tensor", axis: int = -1) -> "Tensor":
        out = Tensor(
            np.concatenate([self.data, other.data], axis=axis),
            requires_grad=(self.requires_grad or other.requires_grad),
        )
        out._prev = [self, other]

        if _is_grad_enabled() and out.requires_grad:
            split_idx = self.data.shape[axis]
            def _backward():
                parts = np.split(out.grad, [split_idx], axis=axis)
                if self.requires_grad:
                    self._ensure_grad()
                    self.grad = self.grad + parts[0]
                if other.requires_grad:
                    other._ensure_grad()
                    other.grad = other.grad + parts[1]
            out._backward_fn = _backward
        return out

    # -- max along axis (for attention masking) -----------------------------

    def max_val(self, axis: int = -1, keepdims: bool = False):
        """Max reduction — returns Tensor (no grad through argmax path)."""
        return Tensor(
            np.max(self.data, axis=axis, keepdims=keepdims),
            requires_grad=False,
        )


# ===========================================================================
# Helpers
# ===========================================================================

def _ensure_tensor(x) -> Tensor:
    if isinstance(x, Tensor):
        return x
    if isinstance(x, (int, float)):
        return Tensor(np.array(x, dtype=np.float32))
    if isinstance(x, np.ndarray):
        return Tensor(x)
    raise TypeError(f"Cannot convert {type(x)} to Tensor")


def _unbroadcast(grad: np.ndarray, shape: Tuple[int, ...]) -> np.ndarray:
    """Sum out broadcasted dimensions to match target shape."""
    if grad.shape == shape:
        return grad
    # Pad shape on the left with 1s to match grad ndim
    ndim_diff = grad.ndim - len(shape)
    padded = (1,) * ndim_diff + shape
    reduce_axes = []
    for i, (gs, ts) in enumerate(zip(grad.shape, padded)):
        if ts == 1 and gs != 1:
            reduce_axes.append(i)
    if reduce_axes:
        grad = np.sum(grad, axis=tuple(reduce_axes), keepdims=True)
    if grad.shape != shape:
        grad = grad.reshape(shape)
    return grad


def _swap_last_two(x: np.ndarray) -> np.ndarray:
    """Swap last two axes — batched transpose."""
    if x.ndim < 2:
        return x
    axes = list(range(x.ndim))
    axes[-2], axes[-1] = axes[-1], axes[-2]
    return np.transpose(x, axes)


# ===========================================================================
# Functional ops  (stateless, used by layers)
# ===========================================================================

def softmax(x: Tensor, axis: int = -1) -> Tensor:
    """Numerically stable softmax."""
    shifted = x.data - np.max(x.data, axis=axis, keepdims=True)
    e = np.exp(shifted)
    s = e / np.sum(e, axis=axis, keepdims=True)
    out = Tensor(s, requires_grad=x.requires_grad)
    out._prev = [x]

    if _is_grad_enabled() and x.requires_grad:
        def _backward():
            x._ensure_grad()
            # Jacobian-vector product for softmax
            ds = out.grad * s
            sum_ds = np.sum(ds, axis=axis, keepdims=True)
            x.grad = x.grad + ds - s * sum_ds
        out._backward_fn = _backward
    return out


def log_softmax(x: Tensor, axis: int = -1) -> Tensor:
    """Numerically stable log-softmax."""
    shifted = x.data - np.max(x.data, axis=axis, keepdims=True)
    log_sum_exp = np.log(np.sum(np.exp(shifted), axis=axis, keepdims=True))
    ls = shifted - log_sum_exp
    out = Tensor(ls, requires_grad=x.requires_grad)
    out._prev = [x]

    if _is_grad_enabled() and x.requires_grad:
        s = np.exp(ls)
        def _backward():
            x._ensure_grad()
            x.grad = x.grad + out.grad - s * np.sum(out.grad, axis=axis, keepdims=True)
        out._backward_fn = _backward
    return out


def gelu(x: Tensor) -> Tensor:
    """GELU activation: x * 0.5 * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))."""
    c = np.sqrt(2.0 / np.pi)
    inner = c * (x.data + 0.044715 * x.data ** 3)
    t = np.tanh(inner)
    out_data = 0.5 * x.data * (1.0 + t)
    out = Tensor(out_data, requires_grad=x.requires_grad)
    out._prev = [x]

    if _is_grad_enabled() and x.requires_grad:
        def _backward():
            x._ensure_grad()
            sech2 = 1.0 - t ** 2
            d_inner = c * (1.0 + 3.0 * 0.044715 * x.data ** 2)
            dx = 0.5 * (1.0 + t) + 0.5 * x.data * sech2 * d_inner
            x.grad = x.grad + out.grad * dx
        out._backward_fn = _backward
    return out


def cross_entropy_loss(logits: Tensor, targets: np.ndarray) -> Tensor:
    """Cross-entropy loss from raw logits.

    logits: (B, T, V) or (B, V)
    targets: integer array, same shape as logits minus last dim
    Returns: scalar Tensor (mean loss).
    """
    orig_shape = logits.shape
    if logits.ndim == 3:
        B, T, V = logits.shape
        logits_2d = logits.reshape(B * T, V)
        targets_flat = targets.reshape(-1)
    else:
        logits_2d = logits
        targets_flat = targets.reshape(-1)

    # log-softmax
    shifted = logits_2d.data - np.max(logits_2d.data, axis=-1, keepdims=True)
    log_sum_exp = np.log(np.sum(np.exp(shifted), axis=-1, keepdims=True))
    ls = shifted - log_sum_exp

    # NLL
    n = targets_flat.shape[0]
    nll = -ls[np.arange(n), targets_flat]
    loss_val = np.mean(nll)

    out = Tensor(np.array(loss_val, dtype=np.float32), requires_grad=logits.requires_grad)
    out._prev = [logits]

    if _is_grad_enabled() and logits.requires_grad:
        probs = np.exp(ls)
        def _backward():
            logits._ensure_grad()
            g = probs.copy()
            g[np.arange(n), targets_flat] -= 1.0
            g /= n
            if len(orig_shape) == 3:
                g = g.reshape(orig_shape)
            logits.grad = logits.grad + out.grad * g
        out._backward_fn = _backward
    return out


def clip_grad_norm(tensors: List[Tensor], max_norm: float) -> float:
    """Clip gradients by global norm. Returns the original norm."""
    total_norm_sq = 0.0
    for t in tensors:
        if t.grad is not None:
            total_norm_sq += np.sum(t.grad ** 2)
    total_norm = float(np.sqrt(total_norm_sq))
    if total_norm > max_norm:
        scale = max_norm / (total_norm + 1e-8)
        for t in tensors:
            if t.grad is not None:
                t.grad *= scale
    return total_norm
