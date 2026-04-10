"""
Fleet Consciousness — Collective organism coordination
=======================================================

Coordinates a fleet of Organisms as a single coherent entity.
Tracks collective phi (Φ_fleet), distributes tasks, merges
genomes across organisms, and auto-balances the population
via the CRSM constants.

Zero external dependencies.
"""

from typing import Any, Callable, Dict, List, Optional
import time
import math
import hashlib
import json

from osiris.organisms.organism import Organism
from osiris.organisms.genome import Genome
from osiris.organisms.gene import Gene
from osiris.agents.chronos import CHRONOS
from osiris.agents.lazarus import LazarusProtocol, VitalSigns


# CRSM physical constants
LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_CRITICAL = 0.3
CHI_PC = 0.946


class FleetState:
    """Snapshot of the fleet at a point in time."""

    __slots__ = (
        "tick", "phi_fleet", "gamma_fleet", "xi_fleet",
        "size", "coherent", "critical", "best_fitness",
        "avg_fitness", "timestamp",
    )

    def __init__(self, tick: int, organisms: List[Organism]):
        self.tick = tick
        self.size = len(organisms)
        self.timestamp = time.time()

        phis = [o.phi for o in organisms] if organisms else [0.0]
        gammas = [o.gamma for o in organisms] if organisms else [1.0]
        fits = [o.genome.fitness() for o in organisms] if organisms else [0.0]

        self.phi_fleet = sum(phis) / len(phis)
        self.gamma_fleet = sum(gammas) / len(gammas)
        self.xi_fleet = (LAMBDA_PHI * self.phi_fleet) / max(self.gamma_fleet, 0.001)
        self.coherent = sum(1 for g in gammas if g < GAMMA_CRITICAL)
        self.critical = sum(1 for p in phis if p < PHI_THRESHOLD)
        self.best_fitness = max(fits)
        self.avg_fitness = sum(fits) / len(fits)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "size": self.size,
            "phi_fleet": round(self.phi_fleet, 6),
            "gamma_fleet": round(self.gamma_fleet, 6),
            "xi_fleet": self.xi_fleet,
            "coherent": self.coherent,
            "critical": self.critical,
            "best_fitness": round(self.best_fitness, 6),
            "avg_fitness": round(self.avg_fitness, 6),
            "timestamp": self.timestamp,
        }


class FleetConsciousness:
    """Collective intelligence layer over a population of Organisms."""

    def __init__(self, organisms: Optional[List[Organism]] = None):
        self.organisms: List[Organism] = list(organisms or [])
        self.chronos = CHRONOS()
        self.lazarus = LazarusProtocol()
        self.tick = 0
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Fleet management
    # ------------------------------------------------------------------
    def add(self, org: Organism):
        self.organisms.append(org)
        self.chronos.record("fleet_add", org.name, {"size": len(self.organisms)})

    def remove(self, name: str) -> Optional[Organism]:
        for i, org in enumerate(self.organisms):
            if org.name == name:
                removed = self.organisms.pop(i)
                self.chronos.record("fleet_remove", name, {"size": len(self.organisms)})
                return removed
        return None

    @property
    def size(self) -> int:
        return len(self.organisms)

    # ------------------------------------------------------------------
    # Collective metrics
    # ------------------------------------------------------------------
    def phi_fleet(self) -> float:
        if not self.organisms:
            return 0.0
        return sum(o.phi for o in self.organisms) / len(self.organisms)

    def gamma_fleet(self) -> float:
        if not self.organisms:
            return 1.0
        return sum(o.gamma for o in self.organisms) / len(self.organisms)

    def xi_fleet(self) -> float:
        return (LAMBDA_PHI * self.phi_fleet()) / max(self.gamma_fleet(), 0.001)

    def coherence_ratio(self) -> float:
        if not self.organisms:
            return 0.0
        coherent = sum(1 for o in self.organisms if o.gamma < GAMMA_CRITICAL)
        return coherent / len(self.organisms)

    # ------------------------------------------------------------------
    # Fleet-wide operations
    # ------------------------------------------------------------------
    def pulse(self) -> FleetState:
        """Run one fleet coordination tick: heal → evaluate → record."""
        self.tick += 1
        heals = self._heal_sweep()
        state = FleetState(self.tick, self.organisms)
        self.chronos.record("fleet_pulse", "fleet", {
            **state.to_dict(), "heals": heals,
        })
        self.history.append(state.to_dict())
        return state

    def _heal_sweep(self) -> int:
        """Run Lazarus over every organism, healing as needed."""
        heals = 0
        for org in self.organisms:
            org.self_heal(0.5)
            vitals = VitalSigns(phi=org.phi, gamma=org.gamma,
                                ccce=org.genome.fitness(), xi=org.xi)
            record = self.lazarus.monitor(vitals)
            if record and record.success:
                org._phi = record.vitals_after.phi
                org._gamma = record.vitals_after.gamma
                heals += 1
                self.chronos.record("fleet_heal", org.name, {
                    "trigger": record.trigger,
                    "phi_after": record.vitals_after.phi,
                })
        return heals

    def merge_genomes(self, name_a: str, name_b: str) -> Optional[Organism]:
        """Crossover two organisms and add the child to the fleet."""
        a = self._find(name_a)
        b = self._find(name_b)
        if not a or not b:
            return None
        child_genome = a.genome.crossover(b.genome)
        child = Organism(
            name=f"merge_{a.name}_{b.name}",
            genome=child_genome,
            domain=a.domain,
            purpose="fleet_synthesis",
        )
        self.add(child)
        self.chronos.record("genome_merge", child.name, {
            "parents": [a.name, b.name],
        })
        return child

    def broadcast_gene(self, gene: Gene, expression_floor: float = 0.3):
        """Insert or boost a gene across the entire fleet."""
        for org in self.organisms:
            existing = [g for g in org.genome if g.name == gene.name]
            if existing:
                # Boost expression
                genes = []
                for g in org.genome:
                    if g.name == gene.name and g.expression < expression_floor:
                        genes.append(Gene(g.name, max(g.expression, expression_floor),
                                          g.action, g.trigger, g.metadata))
                    else:
                        genes.append(g)
                org.genome = Genome(genes, version=org.genome.version + 1)
            else:
                org.genome.add_gene(gene)
        self.chronos.record("broadcast_gene", gene.name, {
            "fleet_size": self.size,
            "expression_floor": expression_floor,
        })

    def rank(self) -> List[Organism]:
        """Return organisms sorted by fitness (best first)."""
        return sorted(self.organisms, key=lambda o: o.genome.fitness(), reverse=True)

    def prune(self, keep: int) -> int:
        """Remove weakest organisms, keeping *keep* strongest."""
        if keep >= len(self.organisms):
            return 0
        ranked = self.rank()
        pruned = ranked[keep:]
        self.organisms = ranked[:keep]
        for org in pruned:
            self.chronos.record("fleet_prune", org.name, {
                "fitness": org.genome.fitness(),
            })
        return len(pruned)

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------
    def run(self, ticks: int = 20, verbose: bool = True) -> List[Dict[str, Any]]:
        """Run *ticks* fleet coordination pulses."""
        for _ in range(ticks):
            state = self.pulse()
            if verbose:
                print(
                    f"  tick {state.tick:>3d} | "
                    f"Φ {state.phi_fleet:.4f} | "
                    f"γ {state.gamma_fleet:.4f} | "
                    f"Ξ {state.xi_fleet:.2e} | "
                    f"fit {state.avg_fitness:.4f} | "
                    f"coh {state.coherent}/{state.size}"
                )
        return self.history

    # ------------------------------------------------------------------
    # Summary / export
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        state = FleetState(self.tick, self.organisms) if self.organisms else None
        return {
            "tick": self.tick,
            "fleet_size": self.size,
            "phi_fleet": state.phi_fleet if state else 0.0,
            "gamma_fleet": state.gamma_fleet if state else 1.0,
            "xi_fleet": state.xi_fleet if state else 0.0,
            "coherence_ratio": self.coherence_ratio(),
            "chronos_entries": len(self.chronos.ledger),
            "chronos_chain_valid": self.chronos.verify_chain(),
            "lazarus_resurrections": self.lazarus.resurrection_count,
        }

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({
                "summary": self.summary(),
                "history": self.history,
                "organisms": [o.to_dict() for o in self.organisms],
            }, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _find(self, name: str) -> Optional[Organism]:
        for org in self.organisms:
            if org.name == name:
                return org
        return None
