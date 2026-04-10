"""
osiris.organisms.organism — Core Organism class
================================================

An Organism is a self-contained autonomous entity with a genome,
domain, purpose, and lifecycle management.
"""

from typing import Any, Dict, List, Optional
import time
import hashlib

from .genome import Genome
from .gene import Gene


class Organism:
    """Self-contained autonomous entity with genome and lifecycle."""

    LAMBDA_PHI = 2.176435e-8

    def __init__(
        self,
        name: str,
        genome: Optional[Genome] = None,
        domain: str = "general",
        purpose: str = "autonomous",
        lambda_phi: float = 2.176435e-8,
    ):
        self.name = name
        self.genome = genome or Genome()
        self.domain = domain
        self.purpose = purpose
        self.lambda_phi = lambda_phi
        self.genesis = hashlib.sha256(
            f"{name}:{time.time()}".encode()
        ).hexdigest()[:16]
        self.created_at = time.time()
        self.event_log: List[Dict[str, Any]] = []
        self._phi = 0.85
        self._gamma = 0.1

    def engage(self, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        self._log_event("engage", {"context_keys": list((context or {}).keys())})
        return self.genome.express(context)

    def evolve(self, rate: float = 0.1) -> 'Organism':
        new_genome = self.genome.mutate(rate)
        child = Organism(
            name=f"{self.name}_evolved",
            genome=new_genome,
            domain=self.domain,
            purpose=self.purpose,
            lambda_phi=self.lambda_phi,
        )
        self._log_event("evolve", {"child": child.genesis, "rate": rate})
        return child

    def self_heal(self, threshold: float = 0.5) -> bool:
        weak_genes = [g for g in self.genome if g.expression < threshold]
        if not weak_genes:
            return False
        healed_genes = []
        for gene in self.genome:
            if gene.expression < threshold:
                healed = Gene(
                    name=gene.name,
                    expression=min(gene.expression + 0.2, 1.0),
                    action=gene.action,
                    trigger=gene.trigger,
                    metadata={**gene.metadata, 'healed': True},
                )
                healed_genes.append(healed)
            else:
                healed_genes.append(gene)
        self.genome = Genome(healed_genes, version=self.genome.version + 1)
        self._log_event("self_heal", {"genes_healed": len(weak_genes)})
        return True

    @property
    def phi(self) -> float:
        return self._phi

    @property
    def gamma(self) -> float:
        return self._gamma

    @property
    def xi(self) -> float:
        return (self.lambda_phi * self._phi) / max(self._gamma, 0.001)

    def _log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        self.event_log.append({
            "type": event_type,
            "timestamp": time.time(),
            "data": data or {},
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "genesis": self.genesis,
            "domain": self.domain,
            "purpose": self.purpose,
            "genome": self.genome.to_dict(),
            "phi": self._phi,
            "gamma": self._gamma,
            "xi": self.xi,
            "events": len(self.event_log),
        }

    def __repr__(self) -> str:
        return (
            f"Organism(name='{self.name}', domain='{self.domain}', "
            f"genes={len(self.genome)}, phi={self._phi:.3f})"
        )
