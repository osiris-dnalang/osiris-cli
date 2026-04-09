"""
OSIRIS Swarm Brain — Genetic Algorithm Strategy Evolution Engine.

Layer 3 of the Sovereign Development Organism:
  L1  Interface     (TUI / CLI)
  L2  Orchestrator  (ShadowSwarm)
  L3  Meta-Brain    (SwarmBrain)   ← THIS FILE
  L4  Learning      (Apprentice)

The SwarmBrain evolves StrategyGenomes that determine HOW the swarm
orchestrates agents: role order, retry thresholds, cycle budget, and
per-agent performance weights.

Evolution algorithm: Genetic Algorithm with elitism + mutation selection.
  - Population: 6–10 genomes
  - Selection: keep best (elitism) + mutate rest
  - No crossover (single-lineage evolution, referencing CODES framework)
  - Containment: max 5 cycles, max 3 generations/session

CODES framework integration:
  coherence_integrity  = Λ / (Γ + ε)   (maps to fitness proxy)
  phase-lock bonus     applied to genomes whose agent_order begins with
                       high-coherence roles (complete → harden → test)
  resonance encoding   agent_weights encoded as Γ/Λ normalised values

Fdna formula (from DNA-Lang Fidelity paper):
  Fdna = (Γ × Λ) × Φ × e^(−Γ_critical × (τ_circuit mod ϕ8))
  Lower Fdna → higher swarm urgency (more decoherence, needs recovery).

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone

# ── Physical constants (CODES / CRSM) ─────────────────────────────────────────

_PHI8  = 1.6180339887          # Golden ratio ϕ
_GAMMA_CRITICAL = 0.0731       # Critical decoherence threshold
_LAMBDA_PHI = 2.176435e-8      # Coherence coupling constant
_THETA_LOCK = 51.843           # Phase-lock angle (degrees)
_EPSILON = 1e-9                # Numerical stability guard

_HOME        = os.path.expanduser("~")
_BRAIN_DIR   = os.path.join(_HOME, ".osiris")
_GENOME_FILE = os.path.join(_BRAIN_DIR, "strategy_genomes.json")
_LINEAGE_LOG = os.path.join(_BRAIN_DIR, "genome_lineage.jsonl")

# ANSI
_R  = "\033[0m"
_H  = "\033[1m"
_D  = "\033[2m"
_CY = "\033[96m"
_MG = "\033[95m"
_GR = "\033[92m"
_YE = "\033[93m"
_RD = "\033[91m"

# All known swarm roles in canonical ordering (phase-lock reference)
_CANONICAL_ROLES = ["complete", "harden", "document", "test", "integrate"]


# ══════════════════════════════════════════════════════════════════════════════
# ██  CRSM METRICS                                                            ██
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CRSMMetrics:
    """
    Coherent Resonance State Manifold metrics for a file or session.

    Λ  = coherence (0–1)
    Γ  = decoherence rate (0–1, lower is better)
    Φ  = consciousness / integrated information (0–1)
    θ_lock = phase-lock angle (degrees, target 51.843°)
    τ_circuit = circuit runtime / complexity proxy (arbitrary units)
    """
    lambda_coherence: float = 0.5
    gamma_decoherence: float = 0.1
    phi_consciousness: float = 0.5
    theta_lock: float = _THETA_LOCK
    tau_circuit: float = 1.0
    source: str = ""      # file path or session id

    def coherence_integrity(self) -> float:
        """CODES metric: Λ / (Γ + ε).  Higher = healthier."""
        return self.lambda_coherence / (self.gamma_decoherence + _EPSILON)

    def phase_deviation(self) -> float:
        """Absolute deviation from ideal θ_lock (degrees)."""
        return abs(self.theta_lock - _THETA_LOCK)

    def is_phase_locked(self) -> bool:
        return self.phase_deviation() < 2.0


def compute_fdna(crsm: CRSMMetrics) -> float:
    """
    Compute DNA-Lang Fidelity score for a file.

    Fdna = (Γ × Λ) × Φ × e^(−Γ_critical × (τ_circuit mod ϕ8))

    Lower Fdna means more decoherence degradation and higher swarm urgency.
    """
    gamma_lambda = crsm.gamma_decoherence * crsm.lambda_coherence
    tau_mod = crsm.tau_circuit % _PHI8
    exponent = -_GAMMA_CRITICAL * tau_mod
    fdna = gamma_lambda * crsm.phi_consciousness * math.exp(exponent)
    return max(0.0, fdna)


def crsm_from_file(file_path: str) -> CRSMMetrics:
    """
    Derive CRSMMetrics heuristically from a Python file's structure.

    Real measurement would come from quantum circuit execution; this
    provides a code-quality proxy for terrestrial use.
    """
    m = CRSMMetrics(source=file_path)
    try:
        text = Path(file_path).read_text()
        lines = text.splitlines()
        n = max(len(lines), 1)

        import re

        # Λ coherence proxy: fraction of lines that are code (not blank/comment)
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        m.lambda_coherence = min(1.0, len(code_lines) / n)

        # Γ decoherence proxy: fraction of TODO/pass/stub lines
        stubs = sum(1 for l in lines if re.search(
            r'^\s*pass\s*$|raise NotImplementedError|#\s*TODO', l))
        m.gamma_decoherence = min(1.0, stubs / max(n, 1))

        # Φ consciousness proxy: complexity = (classes + defs) / total lines
        symbols = len(re.findall(r'^\s*(def |class )\w+', text, re.MULTILINE))
        m.phi_consciousness = min(1.0, symbols / max(n / 5, 1))

        # τ_circuit proxy: file size in KB
        m.tau_circuit = os.path.getsize(file_path) / 1024.0

        # θ_lock: harmonic of code/comment ratio vs golden ratio
        comment_lines = [l for l in lines if l.strip().startswith("#")]
        ratio = len(code_lines) / max(len(comment_lines), 1)
        m.theta_lock = 51.843 * (ratio / _PHI8) % 90.0

    except Exception:
        pass

    return m


# ══════════════════════════════════════════════════════════════════════════════
# ██  STRATEGY GENOME                                                         ██
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyGenome:
    """
    Genome encoding a swarm orchestration strategy.

    agent_order      : permutation of roles — determines execution sequence
    max_cycles       : how many full passes to allow (1–5)
    retry_threshold  : min DoD score before re-queuing (0.80–0.95)
    agent_weights    : per-role performance multiplier (0.80–1.20)
    genome_id        : unique identifier
    parent_id        : parent genome (for lineage tracking)
    generation       : which GA generation produced this
    fitness          : evaluated fitness score (0–1)
    coherence_sig    : CODES resonance signature (hash of weights)
    frozen           : if True, mutation is disabled
    """
    agent_order: List[str] = field(
        default_factory=lambda: list(_CANONICAL_ROLES))
    max_cycles: int = 2
    retry_threshold: float = 0.85
    agent_weights: Dict[str, float] = field(default_factory=lambda: {
        r: 1.0 for r in _CANONICAL_ROLES})
    genome_id: str = field(
        default_factory=lambda: f"g{int(time.time()*1000) % 100000:05d}")
    parent_id: str = ""
    generation: int = 0
    fitness: float = 0.0
    coherence_sig: str = ""
    frozen: bool = False

    def __post_init__(self):
        # Ensure agent_order only contains known roles
        known = set(_CANONICAL_ROLES)
        self.agent_order = [r for r in self.agent_order if r in known]
        for r in _CANONICAL_ROLES:
            if r not in self.agent_order:
                self.agent_order.append(r)
        # Ensure all weights present
        for r in _CANONICAL_ROLES:
            if r not in self.agent_weights:
                self.agent_weights[r] = 1.0
        # Compute coherence signature
        self.coherence_sig = self._compute_sig()

    def _compute_sig(self) -> str:
        """CODES resonance signature: normalised weight vector as hex."""
        total = sum(self.agent_weights.values()) or 1.0
        normed = [self.agent_weights.get(r, 1.0) / total
                  for r in _CANONICAL_ROLES]
        # Map to 4-digit hex per weight
        return "".join(f"{int(v * 0xFFFF):04x}" for v in normed)

    def phase_lock_bonus(self) -> float:
        """
        CODES phase-lock bonus: reward genomes whose first two roles match
        the canonical coherence sequence (complete → harden).
        """
        if len(self.agent_order) >= 2:
            if (self.agent_order[0] == "complete" and
                    self.agent_order[1] == "harden"):
                return 0.05
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyGenome":
        d.pop("coherence_sig", None)  # will recompute
        return cls(**d)


# ══════════════════════════════════════════════════════════════════════════════
# ██  FITNESS EVALUATOR                                                       ██
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FitnessResult:
    """
    Weighted fitness breakdown for a StrategyGenome.

    F = 0.35·DoD + 0.20·convergence + 0.15·test_pass + 0.15·security
      + 0.10·diff_stability + 0.05·syntax_integrity
      - penalties
    """
    dod_score: float = 0.0
    convergence_speed: float = 0.0
    test_pass_rate: float = 0.0
    security_score: float = 0.0
    diff_stability: float = 0.0
    syntax_integrity: float = 1.0
    coherence_bonus: float = 0.0
    penalty: float = 0.0
    fitness: float = 0.0

    _WEIGHTS = {
        "dod":          0.35,
        "convergence":  0.20,
        "test_pass":    0.15,
        "security":     0.15,
        "diff_stable":  0.10,
        "syntax":       0.05,
    }

    def compute(self) -> float:
        w = self._WEIGHTS
        raw = (
            w["dod"]        * self.dod_score +
            w["convergence"]* self.convergence_speed +
            w["test_pass"]  * self.test_pass_rate +
            w["security"]   * self.security_score +
            w["diff_stable"]* self.diff_stability +
            w["syntax"]     * self.syntax_integrity +
            self.coherence_bonus
        )
        self.fitness = max(0.0, min(1.0, raw - self.penalty))
        return self.fitness


class FitnessEvaluator:
    """
    Evaluates a StrategyGenome against the swarm's task history.

    Uses real DoD scores, syntax validation results, and CRSM metrics
    to compute a grounded fitness signal.
    """

    def evaluate(self,
                 genome: StrategyGenome,
                 task_history: List[Dict[str, Any]],
                 crsm: Optional[CRSMMetrics] = None) -> FitnessResult:
        """
        Score a genome using completed task records.

        task_history entries expected:
          {role, file, status, dod_before, dod_after, duration_s,
           syntax_ok, has_security_checks}
        """
        result = FitnessResult()
        if not task_history:
            # No evidence — assign neutral baseline
            result.dod_score = 0.5
            result.syntax_integrity = 1.0
            result.fitness = 0.5 + genome.phase_lock_bonus()
            return result

        relevant = [t for t in task_history
                    if t.get("role") in genome.agent_order]
        if not relevant:
            relevant = task_history

        n = len(relevant)

        # DoD improvement delta
        dod_deltas = [t.get("dod_after", 0) - t.get("dod_before", 0)
                      for t in relevant]
        result.dod_score = min(1.0, max(0.0,
            0.5 + sum(dod_deltas) / max(n, 1)))

        # Convergence speed: tasks that completed within one cycle
        one_cycle = [t for t in relevant if t.get("cycles_used", 1) == 1]
        result.convergence_speed = len(one_cycle) / n

        # Test pass rate
        test_tasks = [t for t in relevant if t.get("role") == "test"]
        if test_tasks:
            passed = sum(1 for t in test_tasks
                         if t.get("status") == "done")
            result.test_pass_rate = passed / len(test_tasks)
        else:
            result.test_pass_rate = 0.5  # unknown — neutral

        # Security score: fraction of hardened tasks with security checks
        harden_tasks = [t for t in relevant if t.get("role") == "harden"]
        if harden_tasks:
            sec = sum(1 for t in harden_tasks
                      if t.get("has_security_checks", False))
            result.security_score = sec / len(harden_tasks)
        else:
            result.security_score = 0.5

        # Diff stability: fraction of tasks whose file wasn't re-queued
        re_queued = sum(1 for t in relevant
                        if t.get("re_queued", False))
        result.diff_stability = 1.0 - re_queued / n

        # Syntax integrity: fraction of tasks with syntax_ok
        syntax_ok = sum(1 for t in relevant
                        if t.get("syntax_ok", True))
        result.syntax_integrity = syntax_ok / n

        # CODES coherence bonus
        if crsm is not None:
            ci = crsm.coherence_integrity()
            # Normalise: CI of 5.0 → 0.05 bonus
            result.coherence_bonus = min(0.1, ci / 100.0)
        result.coherence_bonus += genome.phase_lock_bonus()

        # Penalties
        # Regression: if any task made DoD worse
        regressions = sum(1 for d in dod_deltas if d < -0.1)
        result.penalty += regressions * 0.05

        # Syntax fail: hard penalty
        syntax_fails = n - syntax_ok
        result.penalty += syntax_fails * 0.10

        result.compute()
        return result


# ══════════════════════════════════════════════════════════════════════════════
# ██  MUTATION ENGINE                                                         ██
# ══════════════════════════════════════════════════════════════════════════════

def _mutate_genome(genome: StrategyGenome, rng: random.Random) -> StrategyGenome:
    """
    Produce a mutated child genome.

    Three mutation operators (any subset may fire):
      1. Adjacent swap   — safe permutation mutation on agent_order
      2. Parameter drift — ±1 cycle, ±0.02 threshold
      3. Weight nudge    — multiply each weight by 0.97–1.03
    """
    if genome.frozen:
        return copy.deepcopy(genome)

    child = copy.deepcopy(genome)
    child.parent_id = genome.genome_id
    child.generation = genome.generation + 1
    child.genome_id = f"g{int(time.time()*1000) % 100000:05d}"
    child.fitness = 0.0

    # 1. Adjacent swap (60% chance)
    if rng.random() < 0.60 and len(child.agent_order) >= 2:
        i = rng.randint(0, len(child.agent_order) - 2)
        child.agent_order[i], child.agent_order[i + 1] = \
            child.agent_order[i + 1], child.agent_order[i]

    # 2. Parameter drift (50% chance each)
    if rng.random() < 0.50:
        child.max_cycles = max(1, min(5, child.max_cycles + rng.choice([-1, 1])))

    if rng.random() < 0.50:
        drift = rng.uniform(-0.02, 0.02)
        child.retry_threshold = max(0.80, min(0.95, child.retry_threshold + drift))

    # 3. Weight nudge (40% chance per weight)
    for role in _CANONICAL_ROLES:
        if rng.random() < 0.40:
            nudge = rng.uniform(0.97, 1.03)
            child.agent_weights[role] = max(
                0.80, min(1.20, child.agent_weights[role] * nudge))

    # Recompute resonance signature
    child.coherence_sig = child._compute_sig()
    return child


# ══════════════════════════════════════════════════════════════════════════════
# ██  SWARM BRAIN                                                             ██
# ══════════════════════════════════════════════════════════════════════════════

class SwarmBrain:
    """
    Genetic Algorithm orchestration brain for the OSIRIS Shadow Swarm.

    Maintains a population of StrategyGenomes and evolves them each session
    based on observed swarm task outcomes (DoD, syntax integrity, test pass).

    Containment invariants:
      - max_cycles ≤ 5 per genome
      - population ≤ 10
      - generations ≤ 3 per session
      - kill_switch() immediately freezes all evolution
    """

    POP_SIZE_MIN  = 6
    POP_SIZE_MAX  = 10
    MAX_GENS      = 3       # generations per session
    MIN_TASKS_TO_EVOLVE = 4  # minimum task history before first evolution

    def __init__(self):
        self._lock = threading.Lock()
        self._rng = random.Random(int(time.time()))
        self._population: List[StrategyGenome] = []
        self._task_history: List[Dict[str, Any]] = []
        self._generation: int = 0
        self._killed: bool = False
        self._frozen: bool = False
        self._evaluator = FitnessEvaluator()
        os.makedirs(_BRAIN_DIR, exist_ok=True)
        self._load()
        if not self._population:
            self._seed_population()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_active_genome(self) -> StrategyGenome:
        """Return the best genome (elite) for use by the swarm."""
        with self._lock:
            if not self._population:
                self._seed_population()
            ranked = sorted(self._population,
                            key=lambda g: g.fitness, reverse=True)
            return ranked[0]

    def record_task_outcome(self,
                            role: str,
                            file_path: str,
                            status: str,
                            dod_before: float = 0.5,
                            dod_after: float = 0.5,
                            duration_s: float = 0.0,
                            syntax_ok: bool = True,
                            has_security_checks: bool = False,
                            cycles_used: int = 1,
                            re_queued: bool = False):
        """
        Record a completed swarm task for fitness evaluation.
        Triggers evolution if enough evidence has accumulated.
        """
        record = {
            "role": role, "file": file_path, "status": status,
            "dod_before": dod_before, "dod_after": dod_after,
            "duration_s": duration_s, "syntax_ok": syntax_ok,
            "has_security_checks": has_security_checks,
            "cycles_used": cycles_used, "re_queued": re_queued,
            "ts": time.time(),
        }
        with self._lock:
            self._task_history.append(record)
            if len(self._task_history) > 200:
                self._task_history = self._task_history[-200:]

        # Check if we should evolve
        if (not self._killed and
                not self._frozen and
                len(self._task_history) >= self.MIN_TASKS_TO_EVOLVE and
                len(self._task_history) % self.MIN_TASKS_TO_EVOLVE == 0 and
                self._generation < self.MAX_GENS):
            threading.Thread(
                target=self._evolve_step,
                daemon=True, name="osiris-ga"
            ).start()

    def strategy_freeze(self):
        """Freeze evolution — current best genome is locked in."""
        with self._lock:
            self._frozen = True
            best = self.get_active_genome()
            best.frozen = True
        self._log_event("freeze", {"genome_id": best.genome_id})

    def kill_switch(self):
        """Emergency stop — halt all GA evolution immediately."""
        with self._lock:
            self._killed = True
            self._frozen = True
        self._log_event("kill_switch", {"generation": self._generation})

    def reset_evolution(self):
        """Unfreeze and reset generation counter for a new session."""
        with self._lock:
            self._killed = False
            self._frozen = False
            self._generation = 0
            for g in self._population:
                g.frozen = False
        self._log_event("reset", {"population": len(self._population)})

    def lineage(self, max_entries: int = 20) -> str:
        """Return formatted evolution lineage report."""
        lines = [f"  {_H}SwarmBrain Genome Lineage{_R}",
                 f"  Generation: {self._generation}/{self.MAX_GENS}  "
                 f"Population: {len(self._population)}  "
                 f"Task history: {len(self._task_history)}",
                 f"  Frozen: {self._frozen}  Killed: {self._killed}"]

        with self._lock:
            ranked = sorted(self._population,
                            key=lambda g: g.fitness, reverse=True)

        lines.append(f"\n  {_YE}Current Population (ranked):{_R}")
        for i, g in enumerate(ranked[:5]):
            sig = g.coherence_sig[:12] if g.coherence_sig else "?"
            lock = _GR + "❄" + _R if g.frozen else " "
            lines.append(
                f"  {lock} #{i+1} [{g.genome_id}] "
                f"F={g.fitness:.3f} gen={g.generation} "
                f"order={','.join(g.agent_order[:3])}.. "
                f"cycles={g.max_cycles} thresh={g.retry_threshold:.2f} "
                f"sig={sig}"
            )

        # Read lineage log
        try:
            entries = []
            with open(_LINEAGE_LOG) as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
            recent = entries[-max_entries:]
            if recent:
                lines.append(f"\n  {_CY}Recent evolution events:{_R}")
                for e in reversed(recent[-10:]):
                    ts = datetime.fromtimestamp(e.get("ts", 0)).strftime("%H:%M:%S")
                    lines.append(f"    [{ts}] {e.get('event','?')} "
                                 f"{json.dumps(e.get('data', {}))[:60]}")
        except Exception:
            pass

        return "\n".join(lines)

    def stats_dict(self) -> Dict[str, Any]:
        """Return brain stats for TUI display."""
        best = self.get_active_genome()
        return {
            "generation": self._generation,
            "max_gens": self.MAX_GENS,
            "population": len(self._population),
            "best_fitness": best.fitness,
            "best_order": best.agent_order,
            "best_cycles": best.max_cycles,
            "best_thresh": best.retry_threshold,
            "best_sig": best.coherence_sig[:12] if best.coherence_sig else "",
            "tasks_observed": len(self._task_history),
            "frozen": self._frozen,
            "killed": self._killed,
        }

    # ── GA Core ────────────────────────────────────────────────────────────────

    def _seed_population(self):
        """Create initial population with diverse role orderings."""
        orderings = [
            list(_CANONICAL_ROLES),                          # canonical
            ["complete", "test", "document", "harden", "integrate"],
            ["harden", "complete", "test", "document", "integrate"],
            ["document", "complete", "harden", "test", "integrate"],
            ["complete", "harden", "test", "document", "integrate"],
            ["test", "complete", "harden", "document", "integrate"],
        ]
        for i, order in enumerate(orderings):
            g = StrategyGenome(
                agent_order=order,
                max_cycles=self._rng.randint(1, 3),
                retry_threshold=round(self._rng.uniform(0.80, 0.92), 2),
                generation=0,
            )
            self._population.append(g)
        self._log_event("seed", {"population": len(self._population)})

    def _evolve_step(self):
        """One generation of evolution: evaluate → rank → select → mutate."""
        with self._lock:
            if self._killed or self._frozen:
                return
            if self._generation >= self.MAX_GENS:
                return

            history_snapshot = list(self._task_history)

        # Evaluate fitness of all genomes
        crsm = self._session_crsm()
        scored: List[Tuple[float, StrategyGenome]] = []
        for genome in self._population:
            fr = self._evaluator.evaluate(genome, history_snapshot, crsm)
            genome.fitness = fr.fitness
            scored.append((fr.fitness, genome))

        # Rank
        scored.sort(key=lambda x: -x[0])
        elite_count = max(1, len(scored) // 3)
        elites = [g for _, g in scored[:elite_count]]

        # Mutate rest to fill population
        new_pop = list(elites)
        attempts = 0
        while len(new_pop) < self.POP_SIZE_MIN and attempts < 50:
            parent = self._rng.choice(elites)
            child = _mutate_genome(parent, self._rng)
            new_pop.append(child)
            attempts += 1

        # Trim to max size
        with self._lock:
            self._population = new_pop[:self.POP_SIZE_MAX]
            self._generation += 1

        best = elites[0]
        self._log_event("evolve", {
            "generation": self._generation,
            "best_fitness": best.fitness,
            "best_genome": best.genome_id,
            "population": len(self._population),
        })
        self._save()

    def _session_crsm(self) -> CRSMMetrics:
        """
        Aggregate CRSMMetrics from task history as a session-level signal.
        """
        m = CRSMMetrics()
        if not self._task_history:
            return m
        # Phi proxy: average dod_after
        dod_vals = [t.get("dod_after", 0.5) for t in self._task_history]
        m.phi_consciousness = sum(dod_vals) / len(dod_vals)
        # Gamma: fraction of failed tasks
        fails = sum(1 for t in self._task_history
                    if t.get("status") == "failed")
        m.gamma_decoherence = fails / len(self._task_history)
        # Lambda: 1 - gamma
        m.lambda_coherence = 1.0 - m.gamma_decoherence
        # Tau: session duration in virtual circuit units
        if len(self._task_history) >= 2:
            span = (self._task_history[-1].get("ts", time.time()) -
                    self._task_history[0].get("ts", time.time()))
            m.tau_circuit = span / 60.0  # minutes
        return m

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self):
        try:
            data = {
                "generation": self._generation,
                "population": [g.to_dict() for g in self._population],
                "task_history": self._task_history[-50:],
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(_GENOME_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            if not os.path.exists(_GENOME_FILE):
                return
            with open(_GENOME_FILE) as f:
                data = json.load(f)
            self._generation = min(data.get("generation", 0), self.MAX_GENS)
            self._population = [
                StrategyGenome.from_dict(d)
                for d in data.get("population", [])
            ]
            self._task_history = data.get("task_history", [])
        except Exception:
            self._population = []
            self._task_history = []

    def _log_event(self, event: str, data: Dict[str, Any]):
        record = {"ts": time.time(), "event": event, "data": data}
        try:
            with open(_LINEAGE_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# ██  SINGLETON                                                               ██
# ══════════════════════════════════════════════════════════════════════════════

_brain: Optional[SwarmBrain] = None
_brain_lock = threading.Lock()


def get_brain() -> SwarmBrain:
    """Get the singleton SwarmBrain."""
    global _brain
    with _brain_lock:
        if _brain is None:
            _brain = SwarmBrain()
    return _brain
