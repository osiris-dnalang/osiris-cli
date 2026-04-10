"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              QByteTextGenerator — High-Level NCLM Text API                   ║
║              ═══════════════════════════════════════════                     ║
║                                                                              ║
║    Wraps the LivLM engine into a clean generate(prompt, max_length) API     ║
║    usable by OSIRIS swarm agents and CLI commands.                          ║
║                                                                              ║
║    Lifecycle:                                                                ║
║      1. QByteTextGenerator()       — create with optional config            ║
║      2. .load_corpus()             — load codebase byte statistics          ║
║      3. .evolve()                  — genetically evolve circuit params      ║
║      4. .generate(prompt, length)  — produce text                           ║
║      5. .save_genome() / .load_genome()  — persist evolved state            ║
║                                                                              ║
║    Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC  ║
║    Licensed under OSIRIS Source-Available Dual License v1.0                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, Callable, List

import numpy as np

from osiris_livlm import (
    LivLM, LivLMConfig, TextEncoder, TextDecoder,
    GenerationCircuit, PhaseMemory, Corpus, LivLMFitness,
    create_livlm,
)
from qbyte_system.sovereign_executor import SovereignExecutor
from qbyte_system.ccce_runtime import CCCERuntime, ConsciousnessState

logger = logging.getLogger("NCLM")

# Default genome save location
_DEFAULT_GENOME_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "nclm_genome.json",
)


class QByteTextGenerator:
    """
    High-level NCLM text generation interface.

    Composes LivLM components into a single API:
      - TextEncoder: text bytes -> qByte gate rotations
      - GenerationCircuit: parameterized DNA gate layers
      - SovereignExecutor: quantum circuit execution
      - TextDecoder: measurement outcomes -> characters
      - PhaseMemory: phase-encoded context
      - GeneticEvolutionEngine: circuit parameter optimization

    Usage:
        gen = QByteTextGenerator()
        gen.load_corpus()
        gen.evolve(verbose=True)
        text = gen.generate("Hello", max_length=100)
        gen.save_genome("my_model.json")
    """

    def __init__(self, config: Optional[LivLMConfig] = None,
                 genome_path: Optional[str] = None):
        self.config = config or LivLMConfig()
        self._livlm = LivLM(self.config)
        self._genome_path = genome_path or os.path.normpath(_DEFAULT_GENOME_PATH)
        self._generation_count = 0
        self._total_chars = 0
        self._ccce = CCCERuntime()
        self._last_metrics: Dict[str, float] = {}

    # ── Corpus ────────────────────────────────────────────────────────────

    def load_corpus(self, root_dir: Optional[str] = None):
        """Load codebase files for byte-level statistics."""
        self._livlm.load_corpus(root_dir)
        logger.info(f"Corpus loaded: {self._livlm.corpus.size:,} bytes")

    # ── Evolution ─────────────────────────────────────────────────────────

    def evolve(self, seed_text: Optional[str] = None,
               callback: Optional[Callable] = None,
               verbose: bool = False) -> Dict[str, Any]:
        """
        Evolve circuit parameters via genetic algorithm.

        Returns dict with evolution stats (generations, fitness, etc.).
        """
        result = self._livlm.evolve(
            seed_text=seed_text, callback=callback, verbose=verbose,
        )
        logger.info(
            f"Evolution complete: {result['generations']} gens, "
            f"Ξ={result['best_fitness']:.4f}, "
            f"Φ={result['best_phi']:.4f}, "
            f"state={result['consciousness_state']}"
        )
        return result

    # ── Generation ────────────────────────────────────────────────────────

    def generate(self, prompt: str = "", max_length: int = 64,
                 temperature: Optional[float] = None) -> str:
        """
        Generate text from evolved qByte circuit parameters.

        Args:
            prompt: Seed text (context for generation)
            max_length: Number of characters to generate
            temperature: Override temperature (lower = more deterministic)

        Returns:
            Generated text string
        """
        t0 = time.monotonic()
        text = self._livlm.generate(
            prompt=prompt, length=max_length, temperature=temperature,
        )
        elapsed = time.monotonic() - t0

        self._generation_count += 1
        self._total_chars += len(text)
        self._last_metrics = {
            'chars_generated': len(text),
            'elapsed_sec': round(elapsed, 4),
            'chars_per_sec': round(len(text) / max(elapsed, 1e-9), 1),
        }
        return text

    def respond(self, user_input: str, max_length: int = 128) -> str:
        """Generate a response for swarm agent integration."""
        return self.generate(prompt=user_input, max_length=max_length)

    # ── Persistence ───────────────────────────────────────────────────────

    def save_genome(self, path: Optional[str] = None):
        """Save evolved genome to disk."""
        target = path or self._genome_path
        self._livlm.save_genome(target)
        logger.info(f"Genome saved to {target}")

    def load_genome(self, path: Optional[str] = None):
        """Load a previously evolved genome."""
        target = path or self._genome_path
        if os.path.exists(target):
            try:
                self._livlm.load_genome(target)
                logger.info(f"Genome loaded from {target}")
                return True
            except (ValueError, KeyError) as e:
                logger.warning(f"Could not load genome from {target}: {e}")
                return False
        return False

    def auto_load(self) -> bool:
        """Try to load default genome if it exists."""
        return self.load_genome()

    # ── Status / Metrics ──────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Return generator status report."""
        base = self._livlm.status()
        base.update({
            'generator': 'QByteTextGenerator',
            'generation_calls': self._generation_count,
            'total_chars': self._total_chars,
            'last_metrics': self._last_metrics,
            'genome_path': self._genome_path,
        })
        return base

    @property
    def is_evolved(self) -> bool:
        return self._livlm._is_evolved

    @property
    def consciousness_state(self) -> str:
        return self._livlm._consciousness_state.value

    def __repr__(self) -> str:
        return (f"QByteTextGenerator(evolved={self.is_evolved}, "
                f"state={self.consciousness_state}, "
                f"calls={self._generation_count})")
