"""
AdamW Optimizer — numpy only.
==============================

Adam with decoupled weight decay, learning-rate warmup, and cosine
decay schedule.

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import List

from .autograd import Tensor


@dataclass
class LRSchedule:
    """Warmup + cosine decay learning-rate schedule."""
    warmup_steps: int = 200
    total_steps: int = 10000
    min_lr_ratio: float = 0.1  # min_lr = base_lr * min_lr_ratio

    def get_lr(self, step: int, base_lr: float) -> float:
        if step < self.warmup_steps:
            return base_lr * (step + 1) / max(self.warmup_steps, 1)
        progress = (step - self.warmup_steps) / max(self.total_steps - self.warmup_steps, 1)
        progress = min(progress, 1.0)
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return base_lr * (self.min_lr_ratio + (1.0 - self.min_lr_ratio) * cosine)


class AdamW:
    """Adam optimizer with decoupled weight decay.

    Args:
        params: list of Tensor parameters to optimize.
        lr: base learning rate.
        betas: coefficients for running averages of gradient and its square.
        eps: term added to denominator for numerical stability.
        weight_decay: decoupled weight decay coefficient.
        schedule: optional LR schedule.
    """

    def __init__(
        self,
        params: List[Tensor],
        lr: float = 3e-4,
        betas: tuple = (0.9, 0.999),
        eps: float = 1e-8,
        weight_decay: float = 0.01,
        schedule: LRSchedule | None = None,
    ):
        self.params = params
        self.base_lr = lr
        self.betas = betas
        self.eps = eps
        self.weight_decay = weight_decay
        self.schedule = schedule

        self.step_count = 0
        # State per parameter
        self._m = [np.zeros_like(p.data) for p in params]
        self._v = [np.zeros_like(p.data) for p in params]

    def step(self):
        """Perform a single optimization step."""
        self.step_count += 1
        t = self.step_count
        b1, b2 = self.betas

        lr = self.base_lr
        if self.schedule is not None:
            lr = self.schedule.get_lr(t - 1, self.base_lr)

        # Bias correction
        bc1 = 1.0 - b1 ** t
        bc2 = 1.0 - b2 ** t

        for i, p in enumerate(self.params):
            if p.grad is None:
                continue

            g = p.grad

            # Moment updates
            self._m[i] = b1 * self._m[i] + (1.0 - b1) * g
            self._v[i] = b2 * self._v[i] + (1.0 - b2) * (g ** 2)

            m_hat = self._m[i] / bc1
            v_hat = self._v[i] / bc2

            # Parameter update
            p.data -= lr * m_hat / (np.sqrt(v_hat) + self.eps)

            # Decoupled weight decay
            if self.weight_decay > 0:
                p.data -= lr * self.weight_decay * p.data

    def zero_grad(self):
        for p in self.params:
            p.zero_grad()

    @property
    def current_lr(self) -> float:
        if self.schedule is not None:
            return self.schedule.get_lr(self.step_count, self.base_lr)
        return self.base_lr
