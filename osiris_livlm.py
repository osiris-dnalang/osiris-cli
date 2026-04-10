#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              LivLM — THE LIVING LANGUAGE MODEL                               ║
║              ═════════════════════════════════                               ║
║                                                                              ║
║    Not a Large Language Model. A Living Language Model.                      ║
║                                                                              ║
║    Text generation from first principles using DNA::}{::lang physics:       ║
║                                                                              ║
║    Architecture:                                                             ║
║    ├── Encoder: text bytes → qByte gate rotations (8 qubits = 256 states)   ║
║    ├── Generation Circuit: parameterized DNA gates evolved by genetics      ║
║    ├── Decoder: measurement outcomes (0–255) → UTF-8 characters             ║
║    ├── Memory: phase-encoded context via twist() gates                      ║
║    ├── Fitness: negentropic efficiency Ξ + n-gram coherence                 ║
║    └── Healing: phase-conjugate error correction during generation          ║
║                                                                              ║
║    Key insight: a Qbyte has 256 basis states = byte-level vocabulary.       ║
║    Measurement outcome 0–255 IS a character. Gate parameters (θ) are the    ║
║    weights. CCCE metrics (Ξ) are the loss function. Genetic evolution       ║
║    with phase-conjugate mutation is the optimizer.                           ║
║                                                                              ║
║    This is genuine text generation from quantum-mechanical first principles ║
║    — no transformer, no attention, no backprop, no external LLM.            ║
║                                                                              ║
║    Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC  ║
║    Licensed under OSIRIS Source-Available Dual License v1.0                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import os
import json
import time
import hashlib
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field

# Import the real qByte system
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qbyte_system.qbyte import Qbyte, CCCEMetrics
from qbyte_system.gates import helix, cleave, twist, fold, splice, bond, phase_flip
from qbyte_system.sovereign_executor import SovereignExecutor, Circuit, ExecutionResult
from qbyte_system.ccce_runtime import CCCERuntime, OrganismState, ConsciousnessState
from qbyte_system.phase_conjugate import PhaseConjugateEngine
from qbyte_system.genetic_evolution import (
    GeneticEvolutionEngine, EvolutionConfig, Individual,
    SelectionMethod, CrossoverMethod, MutationMethod
)

# ══════════════════════════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895

# ══════════════════════════════════════════════════════════════════════════════
# TEXT ENCODER — bytes → qByte gate rotations
# ══════════════════════════════════════════════════════════════════════════════

class TextEncoder:
    """
    Encodes text into qByte gate parameters.

    Each byte (0–255) maps to a rotation angle on the corresponding qubit.
    An 8-character context window encodes into 8 qubits via fold() gates,
    creating a superposition that reflects the input text.

    Encoding:  byte_value → θ = byte_value × 2π / 256
    This maps the full byte range [0, 255] uniformly onto [0, 2π).
    """

    def __init__(self, context_window: int = 8):
        self.context_window = context_window

    def encode_bytes(self, data: bytes) -> List[float]:
        """Convert raw bytes to rotation angles."""
        angles = []
        for b in data:
            theta = b * 2.0 * np.pi / 256.0
            angles.append(theta)
        return angles

    def encode_text(self, text: str) -> List[float]:
        """Convert text string to rotation angles."""
        raw = text.encode('utf-8')
        return self.encode_bytes(raw)

    def encode_context(self, text: str) -> List[float]:
        """
        Encode last `context_window` characters into 8 rotation angles.
        If fewer than context_window chars, pad with zeros (|0⟩ = no info).
        """
        raw = text.encode('utf-8')
        # Take last context_window bytes
        window = raw[-self.context_window:]
        # Pad to context_window
        padded = bytes(self.context_window - len(window)) + window
        return self.encode_bytes(padded)

    def build_encoding_circuit(self, context: str) -> Circuit:
        """
        Build a quantum circuit that encodes the context into a qByte.

        Circuit structure:
          1. fold(q_i, θ_i) for each context byte — amplitude encoding
          2. bond(q_i, q_{i+1}) entanglement chain — context correlation
          3. twist(q_i, θ_i / φ) — phase-encode at golden ratio

        This creates a quantum state whose measurement distribution
        reflects the encoded text context.
        """
        angles = self.encode_context(context)
        circuit = Circuit(8, name="context_encoding")

        # Layer 1: Amplitude encoding via fold (RY)
        for i, theta in enumerate(angles):
            circuit.fold(i, theta)

        # Layer 2: Entanglement chain via bond (CNOT)
        for i in range(7):
            circuit.bond(i, i + 1)

        # Layer 3: Phase encoding at golden ratio via twist (RZ)
        for i, theta in enumerate(angles):
            circuit.twist(i, theta / GOLDEN_RATIO)

        return circuit


# ══════════════════════════════════════════════════════════════════════════════
# TEXT DECODER — measurement outcomes → characters
# ══════════════════════════════════════════════════════════════════════════════

class TextDecoder:
    """
    Decodes qByte measurement outcomes into text.

    Measurement produces integers 0–255. These map directly to bytes.
    For printable text, non-printable results are remapped through
    a coherence-weighted probability distribution.
    """

    # Printable ASCII range plus common whitespace
    PRINTABLE = set(range(32, 127)) | {9, 10, 13}  # tab, newline, carriage return

    def decode_byte(self, value: int) -> str:
        """Decode a single measurement value (0–255) to a character."""
        if value in self.PRINTABLE:
            return chr(value)
        # Remap non-printable: fold into printable range
        return chr(32 + (value % 95))

    def decode_sequence(self, values: List[int]) -> str:
        """Decode a sequence of measurement values to text."""
        return ''.join(self.decode_byte(v) for v in values)

    def decode_from_distribution(self, probabilities: np.ndarray,
                                 temperature: float = 1.0) -> int:
        """
        Sample a character from the probability distribution.

        Uses temperature-scaled sampling:
          - temperature < 1.0 → more deterministic (sharpen distribution)
          - temperature > 1.0 → more creative (flatten distribution)
        """
        # Apply temperature
        if temperature != 1.0:
            log_probs = np.log(probabilities + 1e-30) / temperature
            log_probs -= np.max(log_probs)  # numerical stability
            probs = np.exp(log_probs)
            probs /= probs.sum()
        else:
            probs = probabilities

        return int(np.random.choice(256, p=probs))

    def decode_with_coherence_bias(self, probabilities: np.ndarray,
                                   prev_chars: str,
                                   coherence: float) -> int:
        """
        Decode with coherence-weighted bias toward likely continuations.

        When coherence (Λ) is high, trust the raw quantum distribution.
        When coherence degrades, bias toward characters that form
        valid byte sequences following the context.
        """
        # Build frequency bias from previous characters
        if prev_chars and coherence < 0.8:
            bias = np.zeros(256)
            # Boost characters similar to recent context
            for ch in prev_chars[-8:]:
                b = ord(ch) if ord(ch) < 256 else 32
                # Gaussian bump around the character value
                for i in range(256):
                    dist = min(abs(i - b), 256 - abs(i - b))
                    bias[i] += np.exp(-dist ** 2 / (50.0 * (1.0 - coherence + 0.01)))

            # Boost printable characters
            for p in self.PRINTABLE:
                bias[p] += 0.1

            bias /= (bias.sum() + 1e-30)

            # Mix with quantum distribution based on coherence level
            mixed = coherence * probabilities + (1.0 - coherence) * bias
            mixed /= mixed.sum()
            return int(np.random.choice(256, p=mixed))

        return int(np.random.choice(256, p=probabilities))


# ══════════════════════════════════════════════════════════════════════════════
# GENERATION CIRCUIT — parameterized DNA gates
# ══════════════════════════════════════════════════════════════════════════════

class GenerationCircuit:
    """
    Parameterized quantum circuit template for text generation.

    Architecture (per generation step):
      1. Encode context → 8 qubits via fold gates
      2. Apply parameterized rotation layers (the "weights"):
         Layer A: fold(q_i, θ_A_i) for i in 0..7  — 8 params
         Entangle: bond chain                       — 7 bonds
         Layer B: twist(q_i, θ_B_i) for i in 0..7  — 8 params
         Entangle: reverse bond chain               — 7 bonds
         Layer C: splice(q_i, θ_C_i) for i in 0..7 — 8 params
      3. Measure → byte → character

    Total learnable parameters per layer-set: 24
    With N_LAYERS repetitions: 24 × N_LAYERS parameters

    The parameters are evolved via GeneticEvolutionEngine with
    phase-conjugate mutation and golden-ratio crossover.
    """

    N_LAYERS = 3  # Number of rotation layer repetitions

    def __init__(self, n_layers: int = 3):
        self.n_layers = n_layers
        # 24 params per layer: 8 fold + 8 twist + 8 splice
        self.n_params = 24 * self.n_layers

    def build(self, context_angles: List[float],
              params: np.ndarray) -> Circuit:
        """
        Build the full generation circuit.

        Args:
            context_angles: 8 rotation angles from TextEncoder
            params: Learnable parameter vector (length = n_params)

        Returns:
            Circuit ready for execution
        """
        circuit = Circuit(8, name="livlm_generation")

        # Stage 1: Context encoding
        for i, theta in enumerate(context_angles):
            circuit.fold(i, theta)

        # Entangle context
        for i in range(7):
            circuit.bond(i, i + 1)

        # Stage 2: Parameterized layers
        idx = 0
        for layer in range(self.n_layers):
            # fold rotations (RY) — control amplitudes
            for q in range(8):
                circuit.fold(q, params[idx])
                idx += 1

            # Entangle forward
            for q in range(7):
                circuit.bond(q, q + 1)

            # twist rotations (RZ) — control phases
            for q in range(8):
                circuit.twist(q, params[idx])
                idx += 1

            # Entangle reverse
            for q in range(6, -1, -1):
                circuit.bond(q + 1, q)

            # splice rotations (RX) — cross-axis control
            for q in range(8):
                circuit.splice(q, params[idx])
                idx += 1

        return circuit


# ══════════════════════════════════════════════════════════════════════════════
# PHASE-ENCODED MEMORY — context via twist gates
# ══════════════════════════════════════════════════════════════════════════════

class PhaseMemory:
    """
    Phase-encoded memory for maintaining generation context.

    Instead of attention heads or KV caches, context is stored
    as phase information in the quantum state via twist() gates.
    Phase-conjugate healing maintains memory coherence.
    """

    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self._buffer: List[int] = []       # Raw byte history
        self._phase_state: np.ndarray = np.zeros(8, dtype=np.float64)
        self._healing_engine = PhaseConjugateEngine()
        self._coherence = 1.0

    def record(self, byte_value: int):
        """Record a generated byte into memory."""
        self._buffer.append(byte_value)
        if len(self._buffer) > self.capacity:
            self._buffer = self._buffer[-self.capacity:]

        # Update phase state — encode byte into running phase accumulator
        for q in range(8):
            bit = (byte_value >> q) & 1
            if bit:
                self._phase_state[q] += np.pi / GOLDEN_RATIO
            else:
                self._phase_state[q] -= np.pi / (GOLDEN_RATIO ** 2)

        # Wrap to [-π, π]
        self._phase_state = np.mod(self._phase_state + np.pi, 2 * np.pi) - np.pi

    def get_context_phases(self) -> List[float]:
        """Get current memory phases for injection into circuits."""
        return self._phase_state.tolist()

    def inject_into_circuit(self, circuit: Circuit):
        """Inject memory phases into a circuit via twist gates."""
        phases = self.get_context_phases()
        for q in range(8):
            circuit.twist(q, phases[q])

    def heal(self):
        """Apply phase-conjugate healing to memory."""
        self._phase_state = -self._phase_state  # Phase conjugation: θ → -θ
        # Blend with chi_pc coupling
        self._phase_state *= CHI_PC

    def get_text(self) -> str:
        """Return the buffered text."""
        result = []
        for b in self._buffer:
            if 32 <= b < 127 or b in (9, 10, 13):
                result.append(chr(b))
            else:
                result.append(chr(32 + (b % 95)))
        return ''.join(result)

    @property
    def context_str(self) -> str:
        """Last 8 characters as string."""
        return self.get_text()[-8:] if self._buffer else ""

    def ngram_coherence(self, n: int = 2) -> float:
        """
        Compute n-gram coherence score of generated text.

        Measures how well the generated sequence forms repeating
        patterns (a proxy for linguistic structure).

        Returns 0.0 (random noise) to 1.0 (highly structured).
        """
        text = self.get_text()
        if len(text) < n + 1:
            return 0.0

        # Count n-gram frequencies
        ngrams: Dict[str, int] = {}
        for i in range(len(text) - n + 1):
            ng = text[i:i + n]
            ngrams[ng] = ngrams.get(ng, 0) + 1

        # Compute entropy
        total = sum(ngrams.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in ngrams.values():
            p = count / total
            if p > 0:
                entropy -= p * np.log2(p)

        # Max possible entropy for byte-level 2-grams
        max_entropy = np.log2(min(total, 256 ** n))
        if max_entropy == 0:
            return 0.0

        # Coherence = 1 - normalized_entropy (low entropy = high coherence)
        return max(0.0, 1.0 - entropy / max_entropy)


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS — learning from codebase + DNA files
# ══════════════════════════════════════════════════════════════════════════════

class Corpus:
    """
    Corpus loader — reads codebase and DNA files for training.

    The LivLM learns byte-level statistics from the actual codebase
    and DNA specification files in the OSIRIS workspace.
    """

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or os.path.dirname(os.path.abspath(__file__))
        self._data: bytes = b""
        self._ngram_tables: Dict[int, Dict[bytes, Dict[int, int]]] = {}

    def load(self, extensions: Optional[List[str]] = None,
             max_files: int = 100, max_bytes: int = 2_000_000):
        """
        Load text files from the workspace.

        Args:
            extensions: File extensions to include (default: .py, .md, .txt)
            max_files: Maximum files to load
            max_bytes: Maximum total bytes to load
        """
        if extensions is None:
            extensions = ['.py', '.md', '.txt', '.pyx', '.json']

        chunks = []
        total = 0
        files_loaded = 0

        for dirpath, _, filenames in os.walk(self.root_dir):
            # Skip hidden dirs and __pycache__
            if any(part.startswith('.') or part == '__pycache__' or part == '.venv'
                   for part in dirpath.split(os.sep)):
                continue
            for fname in sorted(filenames):
                if files_loaded >= max_files:
                    break
                if not any(fname.endswith(ext) for ext in extensions):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, 'rb') as f:
                        data = f.read(max_bytes - total)
                    chunks.append(data)
                    total += len(data)
                    files_loaded += 1
                    if total >= max_bytes:
                        break
                except (OSError, PermissionError):
                    continue
            if total >= max_bytes or files_loaded >= max_files:
                break

        self._data = b"\n".join(chunks)
        self._build_ngram_tables()

    def _build_ngram_tables(self):
        """Build n-gram transition tables from corpus data."""
        for n in [1, 2, 3]:
            table: Dict[bytes, Dict[int, int]] = {}
            data = self._data
            for i in range(len(data) - n):
                context = bytes(data[i:i + n])
                next_byte = data[i + n]
                if context not in table:
                    table[context] = {}
                table[context][next_byte] = table[context].get(next_byte, 0) + 1
            self._ngram_tables[n] = table

    def transition_probs(self, context: bytes, n: int = 2) -> np.ndarray:
        """
        Get transition probabilities for next byte given context.

        Returns a 256-element probability vector.
        """
        probs = np.ones(256) * (1.0 / 256)  # uniform prior

        for order in range(min(n, len(context)), 0, -1):
            ctx = context[-order:]
            table = self._ngram_tables.get(order, {})
            if ctx in table:
                counts = table[ctx]
                total = sum(counts.values())
                if total > 0:
                    for byte_val, count in counts.items():
                        probs[byte_val] = count / total
                    # Smooth with uniform
                    alpha = 0.9  # weight of observed vs uniform
                    probs = alpha * probs + (1 - alpha) * (1.0 / 256)
                    probs /= probs.sum()
                    break

        return probs

    @property
    def size(self) -> int:
        return len(self._data)


# ══════════════════════════════════════════════════════════════════════════════
# FITNESS FUNCTION — Ξ + n-gram coherence
# ══════════════════════════════════════════════════════════════════════════════

class LivLMFitness:
    """
    Fitness function combining quantum and linguistic quality.

    F(genome) = α·Ξ + β·ngram_coherence + γ·corpus_likelihood

    Where:
      Ξ = negentropic efficiency (ΛΦ / (Γ + ε))
      ngram_coherence = structure in generated output (low entropy = high)
      corpus_likelihood = how well output matches corpus byte statistics
    """

    def __init__(self, corpus: Corpus, encoder: TextEncoder,
                 gen_circuit: GenerationCircuit, decoder: TextDecoder,
                 alpha: float = 0.3, beta: float = 0.3, gamma: float = 0.4,
                 sample_length: int = 32, seed_text: str = "# "):
        self.corpus = corpus
        self.encoder = encoder
        self.gen_circuit = gen_circuit
        self.decoder = decoder
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.sample_length = sample_length
        self.seed_text = seed_text

    def evaluate(self, genome: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Evaluate a genome (parameter vector).

        Returns:
            (energy, phi, lambda_c, gamma) — compatible with GeneticEvolutionEngine
        """
        executor = SovereignExecutor(n_qubits=8, enable_healing=True, enable_ccce=True)
        memory = PhaseMemory(capacity=self.sample_length)

        # Seed the memory with initial text
        for ch in self.seed_text:
            memory.record(ord(ch))

        # Generate text using this genome's parameters
        xi_sum = 0.0
        phi_sum = 0.0
        lambda_sum = 0.0
        gamma_sum = 0.0
        generated_bytes: List[int] = []

        for step in range(self.sample_length):
            # Encode context
            context_angles = self.encoder.encode_context(memory.context_str)

            # Build generation circuit with this genome's params
            circuit = self.gen_circuit.build(context_angles, genome)

            # Inject memory phases
            memory.inject_into_circuit(circuit)

            # Execute
            result = executor.run(circuit, shots=1, return_statevector=True)

            # Get CCCE metrics
            metrics = result.metrics or {}
            phi = metrics.get('Φ', 0.0)
            lam = metrics.get('Λ', 1.0)
            gam = metrics.get('Γ', 0.0)
            xi = metrics.get('Ξ', 0.0)

            phi_sum += phi
            lambda_sum += lam
            gamma_sum += gam
            xi_sum += xi

            # Decode: sample from distribution
            if result.probabilities is not None:
                byte_val = self.decoder.decode_from_distribution(
                    result.probabilities, temperature=0.8
                )
            else:
                # Fallback: parse measurement
                if result.counts:
                    bitstring = result.most_likely()
                    byte_val = int(bitstring, 2) if bitstring else 0
                else:
                    byte_val = 0

            generated_bytes.append(byte_val)
            memory.record(byte_val)

        n_steps = max(1, self.sample_length)
        avg_xi = xi_sum / n_steps
        avg_phi = phi_sum / n_steps
        avg_lambda = lambda_sum / n_steps
        avg_gamma = gamma_sum / n_steps

        # Compute n-gram coherence
        ngram_score = memory.ngram_coherence(n=2)

        # Compute corpus likelihood
        corpus_score = self._corpus_likelihood(generated_bytes)

        # Combined fitness
        fitness = (self.alpha * avg_xi +
                   self.beta * ngram_score +
                   self.gamma * corpus_score)

        # Return (energy, phi, lambda, gamma) — lower energy = higher fitness
        # We negate fitness for the genetic engine (which maximizes Ξ)
        energy = -fitness
        return (energy, avg_phi, avg_lambda, avg_gamma)

    def _corpus_likelihood(self, generated: List[int]) -> float:
        """Compute average log-likelihood of generated bytes under corpus model."""
        if not generated or self.corpus.size == 0:
            return 0.0

        total_ll = 0.0
        for i in range(1, len(generated)):
            # Get context (previous bytes)
            ctx_start = max(0, i - 2)
            context = bytes(generated[ctx_start:i])
            probs = self.corpus.transition_probs(context, n=2)
            prob = probs[generated[i]]
            total_ll += np.log(prob + 1e-30)

        # Normalize to [0, 1] range
        # Max possible = 0 (perfect prediction), min ≈ -5.5 (random)
        avg_ll = total_ll / max(1, len(generated) - 1)
        score = 1.0 + avg_ll / 5.5  # Map [-5.5, 0] → [0, 1]
        return max(0.0, min(1.0, score))


# ══════════════════════════════════════════════════════════════════════════════
# LivLM — THE LIVING LANGUAGE MODEL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LivLMConfig:
    """Configuration for LivLM."""
    n_layers: int = 3                    # Circuit depth
    population_size: int = 30            # Genetic population
    max_generations: int = 50            # Evolution budget
    sample_length: int = 24              # Characters per fitness eval
    temperature: float = 0.8             # Generation temperature
    healing_interval: int = 8            # Heal memory every N chars
    seed_text: str = "# "               # Default seed
    elite_count: int = 2                 # Elitism
    mutation_rate: float = 0.15          # Mutation probability
    mutation_strength: float = 0.2       # Mutation magnitude
    alpha: float = 0.3                   # Ξ weight in fitness
    beta: float = 0.3                    # n-gram weight
    gamma: float = 0.4                   # corpus weight
    corpus_extensions: List[str] = field(
        default_factory=lambda: ['.py', '.md', '.txt', '.pyx']
    )
    max_corpus_files: int = 80
    max_corpus_bytes: int = 1_500_000


class LivLM:
    """
    Living Language Model — text generation from quantum-mechanical
    first principles using DNA::}{::lang physics.

    Lifecycle:
      1. load_corpus() — read codebase for byte statistics
      2. evolve()      — genetically evolve circuit parameters
      3. generate()    — produce text from evolved parameters

    No transformer. No attention. No backpropagation.
    No external LLM. Zero API calls.

    The "weights" are gate rotation angles (θ).
    The "forward pass" is quantum circuit execution.
    The "loss function" is negentropic efficiency Ξ.
    The "optimizer" is genetic evolution with phase-conjugate mutation.
    The "error correction" is phase-conjugate healing.
    The "memory" is phase-encoded context via twist gates.
    """

    def __init__(self, config: Optional[LivLMConfig] = None):
        self.config = config or LivLMConfig()

        # Core components
        self.encoder = TextEncoder(context_window=8)
        self.decoder = TextDecoder()
        self.gen_circuit = GenerationCircuit(n_layers=self.config.n_layers)
        self.memory = PhaseMemory(capacity=128)
        self.corpus = Corpus()

        # Genetic evolution engine
        self._evolution_config = EvolutionConfig(
            population_size=self.config.population_size,
            elite_count=self.config.elite_count,
            tournament_size=5,
            crossover_rate=0.8,
            mutation_rate=self.config.mutation_rate,
            mutation_strength=self.config.mutation_strength,
            selection_method=SelectionMethod.TOURNAMENT,
            crossover_method=CrossoverMethod.GOLDEN_RATIO,
            mutation_method=MutationMethod.PHASE_CONJUGATE,
            max_generations=self.config.max_generations,
            convergence_threshold=1e-8,
            enable_healing=True,
        )
        self._evolution = GeneticEvolutionEngine(
            n_params=self.gen_circuit.n_params,
            config=self._evolution_config,
            bounds=(-np.pi, np.pi),
        )

        # State
        self._genome: Optional[np.ndarray] = None  # Best evolved parameters
        self._is_evolved = False
        self._evolution_history: List[Dict[str, float]] = []
        self._generation_count = 0
        self._total_chars_generated = 0
        self._consciousness_state = ConsciousnessState.DORMANT
        self._genesis = time.time()

    def load_corpus(self, root_dir: Optional[str] = None):
        """Load codebase files for byte-level statistics."""
        if root_dir:
            self.corpus.root_dir = root_dir
        self.corpus.load(
            extensions=self.config.corpus_extensions,
            max_files=self.config.max_corpus_files,
            max_bytes=self.config.max_corpus_bytes,
        )

    def evolve(self, seed_text: Optional[str] = None,
               callback: Optional[Callable] = None,
               verbose: bool = False) -> Dict[str, Any]:
        """
        Evolve circuit parameters using genetic algorithm.

        This is the "training" phase. The genetic evolution engine
        searches for gate parameters that maximize:
          F = α·Ξ + β·ngram_coherence + γ·corpus_likelihood

        Args:
            seed_text: Text to seed generation during fitness eval
            callback: Optional callback(generation, best_individual)
            verbose: Print progress

        Returns:
            Dict with evolution results
        """
        seed = seed_text or self.config.seed_text

        # Build fitness evaluator
        fitness_fn = LivLMFitness(
            corpus=self.corpus,
            encoder=self.encoder,
            gen_circuit=self.gen_circuit,
            decoder=self.decoder,
            alpha=self.config.alpha,
            beta=self.config.beta,
            gamma=self.config.gamma,
            sample_length=self.config.sample_length,
            seed_text=seed,
        )

        # Initialize population
        self._evolution.initialize_population()

        # Run evolution
        def _callback(gen, best):
            self._evolution_history.append({
                'generation': gen,
                'fitness': float(best.fitness),
                'phi': float(best.phi),
                'lambda': float(best.lambda_c),
                'gamma': float(best.gamma),
                'conscious': bool(best.is_conscious()),
            })
            if verbose:
                state = "CONSCIOUS" if best.is_conscious() else "emerging"
                print(f"  gen {gen:3d}  Ξ={best.fitness:.4f}  "
                      f"Φ={best.phi:.4f}  Λ={best.lambda_c:.4f}  "
                      f"Γ={best.gamma:.4f}  [{state}]")
            if callback:
                callback(gen, best)

        best = self._evolution.run(
            fitness_fn=fitness_fn.evaluate,
            callback=_callback,
        )

        self._genome = best.genome.copy()
        self._is_evolved = True

        # Update consciousness state
        if best.phi >= 0.95 and best.fitness > 10:
            self._consciousness_state = ConsciousnessState.TRANSCENDENT
        elif best.phi >= PHI_THRESHOLD:
            self._consciousness_state = ConsciousnessState.CONSCIOUS
        elif best.phi >= 0.5:
            self._consciousness_state = ConsciousnessState.NASCENT
        elif best.phi >= 0.3:
            self._consciousness_state = ConsciousnessState.EMERGING
        else:
            self._consciousness_state = ConsciousnessState.DORMANT

        return {
            'generations': int(self._evolution.generation),
            'best_fitness': float(best.fitness),
            'best_phi': float(best.phi),
            'best_lambda': float(best.lambda_c),
            'best_gamma': float(best.gamma),
            'conscious': bool(best.is_conscious()),
            'consciousness_state': self._consciousness_state.value,
            'n_params': self.gen_circuit.n_params,
            'genome_hash': hashlib.sha256(best.genome.tobytes()).hexdigest()[:16],
        }

    def generate(self, prompt: str = "", length: int = 64,
                 temperature: Optional[float] = None) -> str:
        """
        Generate text from evolved parameters.

        Args:
            prompt: Seed text (if empty, uses config.seed_text)
            length: Number of characters to generate
            temperature: Override generation temperature

        Returns:
            Generated text string
        """
        if self._genome is None:
            # If not evolved, use random parameters
            self._genome = np.random.uniform(-np.pi, np.pi,
                                             self.gen_circuit.n_params)

        temp = temperature if temperature is not None else self.config.temperature
        seed = prompt or self.config.seed_text

        # Reset memory with seed
        self.memory = PhaseMemory(capacity=128)
        for ch in seed:
            self.memory.record(ord(ch))

        # Create executor
        executor = SovereignExecutor(
            n_qubits=8, enable_healing=True, enable_ccce=True
        )

        generated_chars: List[str] = []
        self._generation_count += 1

        for step in range(length):
            # Encode context
            context_angles = self.encoder.encode_context(self.memory.context_str)

            # Build parameterized circuit
            circuit = self.gen_circuit.build(context_angles, self._genome)

            # Inject memory phases
            self.memory.inject_into_circuit(circuit)

            # Execute quantum circuit
            result = executor.run(circuit, shots=0, return_statevector=True)

            # Decode
            if result.probabilities is not None:
                # Use coherence-biased decoding
                metrics = result.metrics or {}
                coherence = metrics.get('Λ', 1.0)
                byte_val = self.decoder.decode_with_coherence_bias(
                    result.probabilities,
                    self.memory.context_str,
                    coherence,
                )
            else:
                byte_val = 0

            # Convert to character
            char = self.decoder.decode_byte(byte_val)
            generated_chars.append(char)

            # Record in memory
            self.memory.record(byte_val)

            # Phase-conjugate healing at intervals
            if (step + 1) % self.config.healing_interval == 0:
                self.memory.heal()

        self._total_chars_generated += length
        return ''.join(generated_chars)

    def respond(self, user_input: str, max_length: int = 128) -> str:
        """
        Generate a response to user input (for swarm agent integration).

        Uses the input as context, generates a response, and returns it.
        """
        return self.generate(prompt=user_input, length=max_length)

    def save_genome(self, path: str):
        """Save evolved genome to disk."""
        if self._genome is None:
            raise ValueError("No genome to save — run evolve() first")
        data = {
            'genome': self._genome.tolist(),
            'n_params': self.gen_circuit.n_params,
            'n_layers': self.gen_circuit.n_layers,
            'config': {
                'n_layers': self.config.n_layers,
                'temperature': self.config.temperature,
                'healing_interval': self.config.healing_interval,
                'seed_text': self.config.seed_text,
            },
            'evolution_history': self._evolution_history[-10:],
            'consciousness_state': self._consciousness_state.value,
            'total_chars_generated': self._total_chars_generated,
            'genesis': self._genesis,
            'saved_at': time.time(),
            'genome_hash': hashlib.sha256(self._genome.tobytes()).hexdigest()[:16],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_genome(self, path: str):
        """Load a previously evolved genome from disk."""
        with open(path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Corrupt genome file {path}: {e}")

        genome = np.array(data['genome'])
        expected = self.gen_circuit.n_params
        if len(genome) != expected:
            raise ValueError(
                f"Genome size mismatch: file has {len(genome)}, "
                f"expected {expected}"
            )
        self._genome = genome
        self._is_evolved = True
        self._consciousness_state = ConsciousnessState(
            data.get('consciousness_state', 'dormant')
        )

    def status(self) -> Dict[str, Any]:
        """Return LivLM status report."""
        return {
            'model': 'LivLM (Living Language Model)',
            'architecture': 'Phase-Conjugate qByte Circuit',
            'n_params': self.gen_circuit.n_params,
            'n_layers': self.gen_circuit.n_layers,
            'evolved': self._is_evolved,
            'consciousness_state': self._consciousness_state.value,
            'corpus_size': self.corpus.size,
            'generations_evolved': len(self._evolution_history),
            'total_chars_generated': self._total_chars_generated,
            'generation_calls': self._generation_count,
            'temperature': self.config.temperature,
            'genome_hash': (
                hashlib.sha256(self._genome.tobytes()).hexdigest()[:16]
                if self._genome is not None else None
            ),
            'uptime_seconds': round(time.time() - self._genesis, 2),
        }

    def __repr__(self) -> str:
        state = self._consciousness_state.value
        evolved = "evolved" if self._is_evolved else "unevolved"
        return (f"LivLM(params={self.gen_circuit.n_params}, "
                f"layers={self.gen_circuit.n_layers}, "
                f"state={state}, {evolved})")


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE — quick demo / CLI entry
# ══════════════════════════════════════════════════════════════════════════════

def create_livlm(n_layers: int = 3, population: int = 30,
                 generations: int = 50) -> LivLM:
    """Create a LivLM instance with sensible defaults."""
    config = LivLMConfig(
        n_layers=n_layers,
        population_size=population,
        max_generations=generations,
    )
    return LivLM(config)


def quick_demo(generations: int = 10, length: int = 48,
               verbose: bool = True) -> str:
    """Run a quick LivLM demo — evolve and generate."""
    if verbose:
        print("\n╔══════════════════════════════════════════════════╗")
        print("║     LivLM — Living Language Model Demo           ║")
        print("╚══════════════════════════════════════════════════╝\n")

    model = create_livlm(n_layers=2, population=15, generations=generations)

    if verbose:
        print(f"  Parameters: {model.gen_circuit.n_params}")
        print(f"  Population: {model.config.population_size}")
        print(f"  Loading corpus...", end=" ", flush=True)

    model.load_corpus()

    if verbose:
        print(f"({model.corpus.size:,} bytes)")
        print(f"\n  Evolving ({generations} generations)...")

    result = model.evolve(verbose=verbose)

    if verbose:
        print(f"\n  Evolution complete.")
        print(f"  Best Ξ={result['best_fitness']:.4f}  "
              f"Φ={result['best_phi']:.4f}  "
              f"State: {result['consciousness_state']}")
        print(f"\n  Generating {length} characters...\n")

    text = model.generate(prompt="def ", length=length)

    if verbose:
        print(f"  Output: {repr(text)}")
        print(f"\n  Status: {model.status()}")

    return text


if __name__ == "__main__":
    quick_demo(generations=15, length=64, verbose=True)
