"""
Autopoietic Lab Loop — Continuous Observe → Evaluate → Evolve → Heal → Log
============================================================================

A self-sustaining evolutionary cycle that:
1. Scans the habitat (filesystem) for organisms / .dna files
2. Evaluates fitness via genome expression
3. Evolves the population through genetic operators
4. Heals decoherent organisms via LazarusProtocol
5. Logs every event immutably to CHRONOS

Zero external dependencies.  Runs entirely inside the OSIRIS runtime.
"""

from typing import Any, Callable, Dict, List, Optional
import time
import json
import os

from osiris.organisms.gene import Gene
from osiris.organisms.genome import Genome
from osiris.organisms.organism import Organism
from osiris.organisms.evolution import EvolutionEngine
from osiris.agents.chronos import CHRONOS
from osiris.agents.lazarus import LazarusProtocol, VitalSigns


class AutopoieticLoop:
    """Self-sustaining observe→evaluate→evolve→heal→log cycle."""

    def __init__(
        self,
        population_size: int = 30,
        mutation_rate: float = 0.12,
        crossover_rate: float = 0.7,
        selection: str = "tournament",
        phi_heal_threshold: float = 0.5,
        fitness_fn: Optional[Callable[[Organism], float]] = None,
    ):
        self.engine = EvolutionEngine(
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            selection=selection,
            elitism=max(2, population_size // 10),
        )
        self.chronos = CHRONOS()
        self.lazarus = LazarusProtocol()
        self.phi_heal_threshold = phi_heal_threshold
        self.fitness_fn = fitness_fn
        self.population: List[Organism] = []
        self.cycle = 0
        self.telemetry: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Phase 1 — Observe: seed population from habitat
    # ------------------------------------------------------------------
    def seed_from_habitat(self, habitat_dir: str) -> int:
        """Scan *habitat_dir* for .dna / .json organism descriptors."""
        seeded = 0
        if not os.path.isdir(habitat_dir):
            return seeded
        for fname in sorted(os.listdir(habitat_dir)):
            path = os.path.join(habitat_dir, fname)
            if fname.endswith(".json"):
                org = self._load_json_organism(path)
            elif fname.endswith(".dna"):
                org = self._load_dna_organism(path)
            else:
                continue
            if org:
                self.population.append(org)
                self.chronos.record("seed", org.name, {"source": path})
                seeded += 1
        return seeded

    def seed_default(self, n: int = 10, domain: str = "quantum") -> int:
        """Create *n* random organisms when no habitat files exist."""
        import random
        for i in range(n):
            genes = [
                Gene(name=f"g{j}", expression=random.uniform(0.2, 1.0))
                for j in range(random.randint(4, 12))
            ]
            genome = Genome(genes)
            org = Organism(
                name=f"auto_{i}",
                genome=genome,
                domain=domain,
                purpose="autopoietic",
            )
            self.population.append(org)
            self.chronos.record("seed_default", org.name, {"genes": len(genes)})
        return n

    # ------------------------------------------------------------------
    # Phase 2 — Evaluate + Evolve
    # ------------------------------------------------------------------
    def step(self) -> Dict[str, Any]:
        """Run one observe→evaluate→evolve→heal→log cycle."""
        self.cycle += 1
        t0 = time.time()

        # Evaluate fitness before evolution
        pre_fitness = [
            (self.fitness_fn(o) if self.fitness_fn else o.genome.fitness())
            for o in self.population
        ]

        # Evolve
        self.population = self.engine.evolve_population(
            self.population, fitness_fn=self.fitness_fn, generations=1,
        )

        # Phase 3 — Heal decoherent organisms
        heals = 0
        resurrections = 0
        for org in self.population:
            # Self-heal weak genes
            if org.self_heal(self.phi_heal_threshold):
                heals += 1
                self.chronos.record("self_heal", org.name, {"threshold": self.phi_heal_threshold})
            # Lazarus resurrection check
            vitals = VitalSigns(
                phi=org.phi,
                gamma=org.gamma,
                ccce=org.genome.fitness(),
                xi=org.xi,
            )
            record = self.lazarus.monitor(vitals)
            if record and record.success:
                resurrections += 1
                org._phi = record.vitals_after.phi
                org._gamma = record.vitals_after.gamma
                self.chronos.record("resurrect", org.name, {
                    "trigger": record.trigger,
                    "phi_after": record.vitals_after.phi,
                })

        # Post fitness
        post_fitness = [
            (self.fitness_fn(o) if self.fitness_fn else o.genome.fitness())
            for o in self.population
        ]

        snapshot = {
            "cycle": self.cycle,
            "generation": self.engine.generation,
            "population": len(self.population),
            "best_fitness": max(post_fitness) if post_fitness else 0.0,
            "avg_fitness": sum(post_fitness) / len(post_fitness) if post_fitness else 0.0,
            "delta_fitness": (
                (sum(post_fitness) / len(post_fitness))
                - (sum(pre_fitness) / len(pre_fitness))
            ) if pre_fitness else 0.0,
            "heals": heals,
            "resurrections": resurrections,
            "lazarus_state": self.lazarus.state.value,
            "chronos_entries": len(self.chronos.ledger),
            "duration_s": round(time.time() - t0, 4),
        }

        self.chronos.record("cycle_complete", "loop", snapshot)
        self.telemetry.append(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Phase 4 — Run N cycles
    # ------------------------------------------------------------------
    def run(
        self,
        generations: int = 50,
        interval: float = 0.0,
        verbose: bool = True,
        on_cycle: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Run the autopoietic loop for *generations* cycles."""
        if not self.population:
            self.seed_default()

        for _ in range(generations):
            snap = self.step()
            if verbose:
                print(
                    f"  cycle {snap['cycle']:>4d} | "
                    f"gen {snap['generation']:>4d} | "
                    f"best {snap['best_fitness']:.4f} | "
                    f"avg {snap['avg_fitness']:.4f} | "
                    f"Δ {snap['delta_fitness']:+.4f} | "
                    f"heals {snap['heals']} | "
                    f"res {snap['resurrections']}"
                )
            if on_cycle:
                on_cycle(snap)
            if interval > 0:
                time.sleep(interval)

        return self.telemetry

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        chain_valid = self.chronos.verify_chain()
        best_org = max(self.population, key=lambda o: o.genome.fitness()) if self.population else None
        return {
            "total_cycles": self.cycle,
            "population_size": len(self.population),
            "best_organism": best_org.to_dict() if best_org else None,
            "chronos_chain_valid": chain_valid,
            "chronos_entries": len(self.chronos.ledger),
            "lazarus_resurrections": self.lazarus.resurrection_count,
            "lazarus_state": self.lazarus.state.value,
            "telemetry_length": len(self.telemetry),
        }

    def save_telemetry(self, path: str):
        with open(path, "w") as f:
            json.dump({
                "summary": self.summary(),
                "telemetry": self.telemetry,
            }, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_json_organism(self, path: str) -> Optional[Organism]:
        try:
            with open(path) as f:
                data = json.load(f)
            genes = [Gene.from_dict(g) for g in data.get("genes", data.get("genome", {}).get("genes", []))]
            if not genes:
                return None
            return Organism(
                name=data.get("name", os.path.splitext(os.path.basename(path))[0]),
                genome=Genome(genes),
                domain=data.get("domain", "quantum"),
                purpose=data.get("purpose", "autopoietic"),
            )
        except Exception:
            return None

    def _load_dna_organism(self, path: str) -> Optional[Organism]:
        try:
            with open(path) as f:
                content = f.read()
            # Each non-empty line → gene
            genes = []
            for i, line in enumerate(content.strip().splitlines()):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                genes.append(Gene(name=f"dna_{i}", expression=0.5 + 0.01 * (hash(line) % 50)))
            if not genes:
                return None
            return Organism(
                name=os.path.splitext(os.path.basename(path))[0],
                genome=Genome(genes),
                domain="dna_lang",
                purpose="autopoietic",
            )
        except Exception:
            return None
