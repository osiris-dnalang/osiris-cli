"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              NCLMPersonalityEngine — Evolving DNA Personality                 ║
║              ═══════════════════════════════════════════                     ║
║                                                                              ║
║    Extends the NCLMPersonality dataclass from the swarm with real-time      ║
║    genetic mutation via phase-conjugate healing.                            ║
║                                                                              ║
║    Personality traits (G41-G46) evolve based on:                            ║
║    - User interaction feedback (reward signals)                             ║
║    - Negentropic efficiency of generated output                             ║
║    - Phase-conjugate bounded mutation (traits heal, not corrupt)            ║
║                                                                              ║
║    Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC  ║
║    Licensed under OSIRIS Source-Available Dual License v1.0                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

import numpy as np

from qbyte_system import GOLDEN_RATIO, CHI_PC, PHI_THRESHOLD

logger = logging.getLogger("NCLM")


@dataclass
class PersonalityTraits:
    """DNA-encoded personality traits (genes G41–G46)."""
    creativity: float = 0.5       # G41 — creative vs. conservative generation
    speed_bias: float = 0.5       # G42 — speed vs. quality tradeoff
    debug_weight: float = 0.5     # G43 — verbose diagnostics vs. clean output
    formality: float = 0.5        # G44 — formal vs. casual tone
    risk_tolerance: float = 0.5   # G45 — safe vs. exploratory behavior
    verbosity: float = 0.5        # G46 — concise vs. detailed output

    def to_vector(self) -> np.ndarray:
        return np.array([
            self.creativity, self.speed_bias, self.debug_weight,
            self.formality, self.risk_tolerance, self.verbosity,
        ])

    @classmethod
    def from_vector(cls, vec: np.ndarray) -> "PersonalityTraits":
        vec = np.clip(vec, 0.0, 1.0)
        return cls(
            creativity=float(vec[0]),
            speed_bias=float(vec[1]),
            debug_weight=float(vec[2]),
            formality=float(vec[3]),
            risk_tolerance=float(vec[4]),
            verbosity=float(vec[5]),
        )

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class NCLMPersonalityEngine:
    """
    Evolving personality via phase-conjugate genetic mutation.

    Each user gets a unique personality that evolves with interactions.
    Trait mutations use phase-conjugate healing — traits are bounded
    and "heal" toward coherent values rather than drifting randomly.

    Usage:
        engine = NCLMPersonalityEngine("user123")
        traits = engine.traits
        engine.mutate(reward=0.8, trait="creativity")
        engine.save("personality.json")
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        self.traits = self._init_traits()
        self.interaction_count = 0
        self.mutation_history: List[Dict[str, Any]] = []
        self._genesis = time.time()

    def _init_traits(self) -> PersonalityTraits:
        """Seed traits from user hash for deterministic initial personality."""
        # Use hash bytes to generate reproducible starting traits
        h = hashlib.sha256(self.user_id.encode()).digest()
        vals = [b / 255.0 for b in h[:6]]
        return PersonalityTraits.from_vector(np.array(vals))

    def mutate(self, reward: float, trait: str):
        """
        Phase-conjugate mutation of a single trait.

        The mutation is bounded by CHI_PC coupling and uses golden-ratio
        scaling to prevent catastrophic drift:
          Δ = chi_pc * lr * (reward - current) / φ

        Args:
            reward: Reward signal [0, 1] — higher = adapt toward this value
            trait: Trait name (e.g. "creativity", "verbosity")
        """
        if not hasattr(self.traits, trait):
            logger.warning(f"Unknown trait: {trait}")
            return

        current = getattr(self.traits, trait)
        lr = 0.05

        # Phase-conjugate mutation: bounded by chi_pc, scaled by golden ratio
        delta = CHI_PC * lr * (reward - current) / GOLDEN_RATIO
        new_val = float(np.clip(current + delta, 0.0, 1.0))

        setattr(self.traits, trait, new_val)
        self.interaction_count += 1

        self.mutation_history.append({
            'trait': trait,
            'old': round(current, 4),
            'new': round(new_val, 4),
            'reward': round(reward, 4),
            'delta': round(delta, 6),
            'interaction': self.interaction_count,
        })

    def mutate_all(self, rewards: Dict[str, float]):
        """Mutate multiple traits from a reward dict."""
        for trait, reward in rewards.items():
            self.mutate(reward, trait)

    def to_generation_params(self) -> Dict[str, float]:
        """
        Map personality traits to generation parameters.

        Returns config overrides for QByteTextGenerator based
        on current personality state.
        """
        return {
            'temperature': 0.5 + 0.8 * self.traits.creativity,
            'max_length': int(64 + 192 * self.traits.verbosity),
            'healing_interval': max(4, int(16 * (1.0 - self.traits.risk_tolerance))),
        }

    def save(self, path: str):
        """Persist personality state to JSON."""
        data = {
            'user_id': self.user_id,
            'user_hash': self.user_hash,
            'traits': self.traits.to_dict(),
            'interaction_count': self.interaction_count,
            'mutation_history': self.mutation_history[-50:],  # keep last 50
            'genesis': self._genesis,
            'saved_at': time.time(),
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> bool:
        """Load personality state from JSON."""
        if not os.path.exists(path):
            return False
        with open(path, 'r') as f:
            data = json.load(f)
        self.traits = PersonalityTraits(**data['traits'])
        self.interaction_count = data.get('interaction_count', 0)
        self.mutation_history = data.get('mutation_history', [])
        self._genesis = data.get('genesis', self._genesis)
        return True

    def status(self) -> Dict[str, Any]:
        """Return personality status."""
        return {
            'user_hash': self.user_hash,
            'traits': self.traits.to_dict(),
            'interaction_count': self.interaction_count,
            'mutations': len(self.mutation_history),
            'uptime_sec': round(time.time() - self._genesis, 2),
        }

    def __repr__(self) -> str:
        return (f"NCLMPersonalityEngine(user={self.user_hash}, "
                f"interactions={self.interaction_count})")
