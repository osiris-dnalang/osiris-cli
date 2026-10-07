"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              NCLM — Non-Causal Living Model                                  ║
║              ══════════════════════════════                                  ║
║                                                                              ║
║    A living language model built from DNA::}{::lang quantum physics.         ║
║                                                                              ║
║    Core components (re-exported from existing OSIRIS modules):              ║
║    ├── QByteTextGenerator  — high-level text generation API                 ║
║    ├── NCLMEvolution       — genetic evolution with NCLM defaults           ║
║    ├── NCLMPersonality     — evolving personality via GA                    ║
║    ├── LivLM               — full living language model engine              ║
║    └── NCLMBenchmark       — benchmark harness                              ║
║                                                                              ║
║    Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC  ║
║    Licensed under OSIRIS Source-Available Dual License v1.0                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

__version__ = "1.0.0"
__author__ = "Devin Phillip Davis"

# Re-export core classes from existing modules (no duplication)
from osiris_livlm import (
    LivLM, LivLMConfig, TextEncoder, TextDecoder,
    GenerationCircuit, PhaseMemory, Corpus, LivLMFitness,
    create_livlm,
)

# NCLM-specific modules
from nclm.core.qbyte_generator import QByteTextGenerator
from nclm.core.evolution import NCLMEvolution
from nclm.core.personality import NCLMPersonalityEngine

__all__ = [
    # High-level API
    'QByteTextGenerator',
    'NCLMEvolution',
    'NCLMPersonalityEngine',
    # Underlying engine
    'LivLM', 'LivLMConfig', 'create_livlm',
    # Components
    'TextEncoder', 'TextDecoder', 'GenerationCircuit',
    'PhaseMemory', 'Corpus', 'LivLMFitness',
]
