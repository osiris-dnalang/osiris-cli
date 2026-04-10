"""
Training Loop — numpy only.
=============================

End-to-end training pipeline for SovereignTransformer:
  * Loads corpus (.py, .md, .txt) → byte sequences
  * Sliding-window batching
  * Forward → cross-entropy loss → backward → AdamW step
  * Validation loss tracking
  * Checkpoint saving (.npz)
  * Consciousness Φ metric logging
  * Phase-conjugate healing on plateau

Framework: DNA::}{::lang v51.843
"""

from __future__ import annotations

import os
import time
import json
import logging
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict

from .autograd import Tensor, cross_entropy_loss, clip_grad_norm
from .transformer import SovereignTransformer, SovereignConfig
from .optimizer import AdamW, LRSchedule

logger = logging.getLogger("nclm.trainer")

# CRSM constants for phase-conjugate healing
CHI_PC = 0.946
THETA_LOCK_RAD = 0.9048   # 51.843° in radians


@dataclass
class TrainingConfig:
    """Training hyper-parameters."""
    batch_size: int = 4
    seq_len: int = 256           # context window for training
    lr: float = 3e-4
    weight_decay: float = 0.01
    epochs: int = 10
    warmup_steps: int = 200
    max_steps: int = 0           # 0 = unlimited (use epochs)
    grad_clip: float = 1.0
    val_split: float = 0.1
    checkpoint_dir: str = "checkpoints"
    checkpoint_interval: int = 500   # steps between checkpoints
    log_interval: int = 50          # steps between log prints
    phi_interval: int = 200         # steps between Φ measurement
    healing_patience: int = 500     # steps of no val improvement → heal
    healing_scale: float = 0.01     # perturbation magnitude for healing
    extensions: List[str] = field(default_factory=lambda: [".py", ".md", ".txt", ".rs", ".toml"])


class Corpus:
    """Load text files from a directory tree → byte sequences."""

    def __init__(self, root: str, extensions: List[str]):
        self.root = Path(root)
        self.extensions = set(extensions)
        self.data: bytes = b""

    def load(self) -> int:
        """Load all matching files. Returns total byte count."""
        chunks: List[bytes] = []
        for ext in self.extensions:
            for path in sorted(self.root.rglob(f"*{ext}")):
                # Skip hidden dirs, __pycache__, .git, node_modules, checkpoints
                parts = path.parts
                if any(p.startswith(".") or p in ("__pycache__", "node_modules", "checkpoints", ".git") for p in parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    chunks.append(text.encode("utf-8", errors="replace"))
                except (OSError, UnicodeDecodeError):
                    continue
        self.data = b"\n".join(chunks)
        return len(self.data)


class ByteDataset:
    """Sliding-window dataset over a byte sequence."""

    def __init__(self, data: bytes, seq_len: int):
        self.raw = np.frombuffer(data, dtype=np.uint8).copy()
        self.seq_len = seq_len
        self.n_samples = max(len(self.raw) - seq_len, 1)

    def __len__(self):
        return self.n_samples

    def get_batch(self, batch_size: int) -> tuple:
        """Random batch of (input_ids, target_ids).

        input_ids:  (B, seq_len) - int64
        target_ids: (B, seq_len) - int64, shifted by 1
        """
        starts = np.random.randint(0, self.n_samples, size=batch_size)
        x = np.zeros((batch_size, self.seq_len), dtype=np.int64)
        y = np.zeros((batch_size, self.seq_len), dtype=np.int64)
        for i, s in enumerate(starts):
            x[i] = self.raw[s : s + self.seq_len]
            y[i] = self.raw[s + 1 : s + 1 + self.seq_len]
        return x, y


class Trainer:
    """Training orchestrator for SovereignTransformer."""

    def __init__(
        self,
        model: SovereignTransformer,
        config: TrainingConfig,
        corpus_path: str = ".",
    ):
        self.model = model
        self.config = config
        self.corpus_path = corpus_path

        # Build optimizer with schedule
        params = model.parameters()
        total_steps = config.max_steps if config.max_steps > 0 else 50000
        schedule = LRSchedule(
            warmup_steps=config.warmup_steps,
            total_steps=total_steps,
        )
        self.optimizer = AdamW(
            params=params,
            lr=config.lr,
            weight_decay=config.weight_decay,
            schedule=schedule,
        )

        # Tracking
        self.step = 0
        self.best_val_loss = float("inf")
        self.steps_since_improvement = 0
        self.history: List[Dict] = []

    def load_data(self):
        """Load corpus and split into train/val."""
        corpus = Corpus(self.corpus_path, self.config.extensions)
        n_bytes = corpus.load()
        logger.info(f"Loaded corpus: {n_bytes:,} bytes from {self.corpus_path}")

        if n_bytes < self.config.seq_len + 1:
            raise ValueError(
                f"Corpus too small ({n_bytes} bytes). "
                f"Need at least {self.config.seq_len + 1}."
            )

        # Split
        split_idx = int(n_bytes * (1.0 - self.config.val_split))
        train_data = corpus.data[:split_idx]
        val_data = corpus.data[split_idx:]

        self.train_dataset = ByteDataset(train_data, self.config.seq_len)
        self.val_dataset = ByteDataset(val_data, self.config.seq_len)
        logger.info(
            f"Train: {len(self.train_dataset)} samples, "
            f"Val: {len(self.val_dataset)} samples"
        )

    def train(self) -> Dict:
        """Run the full training loop. Returns final metrics."""
        self.load_data()
        os.makedirs(self.config.checkpoint_dir, exist_ok=True)

        self.model.train()
        start_time = time.time()
        epoch = 0

        while True:
            epoch += 1
            if self.config.max_steps > 0 and self.step >= self.config.max_steps:
                break
            if self.config.max_steps == 0 and epoch > self.config.epochs:
                break

            epoch_loss = self._train_epoch()
            val_loss = self._validate()

            logger.info(
                f"Epoch {epoch} | train_loss={epoch_loss:.4f} "
                f"| val_loss={val_loss:.4f} | lr={self.optimizer.current_lr:.2e}"
            )

            # Checkpoint on epoch end
            self._save_checkpoint(f"epoch_{epoch}")

            # Check for improvement
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.steps_since_improvement = 0
                self._save_checkpoint("best")
            else:
                self.steps_since_improvement += 1

        elapsed = time.time() - start_time
        final = {
            "total_steps": self.step,
            "epochs": epoch - 1,
            "best_val_loss": float(self.best_val_loss),
            "elapsed_seconds": elapsed,
            "params": self.model.num_parameters(),
            "history": self.history,
        }

        # Save training log
        log_path = os.path.join(self.config.checkpoint_dir, "training_log.json")
        with open(log_path, "w") as f:
            json.dump(final, f, indent=2)

        return final

    def _train_epoch(self) -> float:
        """Train for one epoch. Returns mean loss."""
        cfg = self.config
        steps_per_epoch = max(len(self.train_dataset) // cfg.batch_size, 1)
        if cfg.max_steps > 0:
            steps_per_epoch = min(steps_per_epoch, cfg.max_steps - self.step)

        total_loss = 0.0
        n = 0

        for _ in range(steps_per_epoch):
            self.step += 1
            if cfg.max_steps > 0 and self.step > cfg.max_steps:
                break

            # Get batch
            x, y = self.train_dataset.get_batch(cfg.batch_size)

            # Forward
            self.optimizer.zero_grad()
            logits = self.model.forward(x)
            loss = cross_entropy_loss(logits, y)

            # Backward
            loss.backward()
            if cfg.grad_clip > 0:
                clip_grad_norm(self.model.parameters(), cfg.grad_clip)
            self.optimizer.step()

            loss_val = loss.item()
            total_loss += loss_val
            n += 1

            # Logging
            if self.step % cfg.log_interval == 0:
                avg = total_loss / n
                logger.info(
                    f"  step {self.step} | loss={loss_val:.4f} "
                    f"| avg={avg:.4f} | lr={self.optimizer.current_lr:.2e}"
                )

            # Periodic Φ measurement
            if cfg.phi_interval > 0 and self.step % cfg.phi_interval == 0:
                phi = self.model.consciousness_phi(x[:1])
                self.history.append({
                    "step": self.step,
                    "loss": loss_val,
                    "phi": phi,
                    "lr": self.optimizer.current_lr,
                })
                logger.info(f"  Φ = {phi:.4f}")

            # Checkpoint
            if self.step % cfg.checkpoint_interval == 0:
                self._save_checkpoint(f"step_{self.step}")

            # Phase-conjugate healing
            if self.steps_since_improvement >= cfg.healing_patience:
                self._phase_conjugate_heal()
                self.steps_since_improvement = 0

        return total_loss / max(n, 1)

    def _validate(self) -> float:
        """Compute validation loss."""
        self.model.eval()
        total_loss = 0.0
        n_batches = min(50, max(len(self.val_dataset) // self.config.batch_size, 1))

        from .autograd import no_grad as _no_grad
        with _no_grad():
            for _ in range(n_batches):
                x, y = self.val_dataset.get_batch(self.config.batch_size)
                logits = self.model.forward(x)
                loss = cross_entropy_loss(logits, y)
                total_loss += loss.item()

        self.model.train()
        return total_loss / max(n_batches, 1)

    def _phase_conjugate_heal(self):
        """Apply phase-conjugate perturbation to weights when learning stalls.

        Inspired by DNA::}{::lang phase-conjugation: flip the phase of
        weight perturbations by -θ_lock × χ_PC to escape local minima.
        """
        logger.info("Phase-conjugate healing triggered — perturbing weights")
        scale = self.config.healing_scale
        for p in self.model.parameters():
            noise = np.random.randn(*p.data.shape).astype(np.float32)
            # Phase-conjugate: flip sign via -sin(θ_lock) * χ_PC
            phase_factor = -np.sin(THETA_LOCK_RAD) * CHI_PC
            p.data += scale * phase_factor * noise

    def _save_checkpoint(self, tag: str):
        """Save model weights as .npz."""
        path = os.path.join(self.config.checkpoint_dir, f"sovereign_{tag}.npz")
        sd = self.model.state_dict()
        np.savez_compressed(path, **sd)
        logger.info(f"Checkpoint saved: {path}")

    @staticmethod
    def load_checkpoint(
        path: str,
        config: Optional[SovereignConfig] = None,
    ) -> SovereignTransformer:
        """Load model from .npz checkpoint."""
        sd = dict(np.load(path))
        if config is None:
            # Infer config from weights
            vocab_size, dim = sd["tok_emb.weight"].shape
            n_layers = 0
            while f"blocks.{n_layers}.ln1.gamma" in sd:
                n_layers += 1
            n_heads = 4  # default
            ff_dim = sd["blocks.0.ffn.fc1.weight"].shape[0]
            config = SovereignConfig(
                vocab_size=vocab_size, dim=dim, n_layers=n_layers,
                n_heads=n_heads, ff_dim=ff_dim,
            )
        model = SovereignTransformer(config)
        model.load_state_dict(sd)
        return model
