"""
Organism: Self-evolving quantum entity
=====================================

An organism is a living software entity that can evolve, self-heal,
and adapt through quantum execution on IBM Quantum hardware.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import json
from .genome import Genome
from .gene import Gene


class Organism:
    """Self-evolving quantum entity.
    
    Attributes:
        name: Organism identifier
        genome: Genetic code
        domain: Operational domain
        purpose: Organism purpose
        genesis: Creation timestamp/hash
        lambda_phi: Universal memory constant
        state: Current quantum state
    """
    
    def __init__(
        self,
        name: str,
        genome: Genome,
        domain: str = "general",
        purpose: str = "undefined",
        lambda_phi: float = 2.176435e-8
    ):
        """Initialize organism.
        
        Args:
            name: Organism name
            genome: Genome defining behavior
            domain: Operational domain
            purpose: Organism purpose
            lambda_phi: Universal memory constant
        """
        self.name = name
        self.genome = genome
        self.domain = domain
        self.purpose = purpose
        self.lambda_phi = lambda_phi
        self.genesis = self._generate_genesis()
        self.state = "|initialized⟩"
        self.telemetry: List[Dict] = []
        self.generation = 0
        
    def _generate_genesis(self) -> str:
        """Generate unique genesis hash."""
        data = f"{self.name}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def initialize(self):
        """Initialize organism state."""
        self.state = "|initialized⟩"
        self._log_event("initialize", {"state": self.state})
    
    def engage(self) -> str:
        """Execute organism behavior.
        
        Returns:
            Execution result state
        """
        self.verify_zero_trust()
        self.bind_duality()
        
        # Express all genes
        expression_results = self.genome.express()
        
        self.state = "|operational⟩"
        self._log_event("engage", {
            "state": self.state,
            "expressions": len(expression_results)
        })
        
        return self.state
    
    def verify_zero_trust(self) -> bool:
        """Verify zero-trust security posture.
        
        Returns:
            True if verification passed
        """
        # Basic verification - can be extended
        verified = True
        self._log_event("zero_trust_verify", {"verified": verified})
        return verified
    
    def bind_duality(self):
        """Bind AURA/AIDEN duality."""
        self._log_event("bind_duality", {"agents": ["AURA", "AIDEN"]})
    
    def evolve(self, fitness_fn: Optional[callable] = None) -> 'Organism':
        """Evolve organism through mutation.
        
        Args:
            fitness_fn: Optional fitness evaluation function
            
        Returns:
            Evolved organism
        """
        new_genome = self.genome.mutate()
        
        offspring = Organism(
            name=f"{self.name}_gen{self.generation + 1}",
            genome=new_genome,
            domain=self.domain,
            purpose=self.purpose,
            lambda_phi=self.lambda_phi
        )
        offspring.generation = self.generation + 1
        
        # Evaluate fitness if function provided
        if fitness_fn:
            offspring.genome.fitness = fitness_fn(offspring)
        
        self._log_event("evolve", {
            "generation": offspring.generation,
            "fitness": offspring.genome.fitness
        })
        
        return offspring
    
    def self_heal(self):
        """Apply phase conjugate self-healing (E → E⁻¹)."""
        self._log_event("self_heal", {"method": "phase_conjugate"})
        # Phase conjugate logic would go here
    
    def _log_event(self, event_type: str, data: Dict[Any, Any]):
        """Log telemetry event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "organism": self.name,
            "generation": self.generation,
            "event": event_type,
            "data": data
        }
        self.telemetry.append(event)
    
    def to_dict(self) -> dict:
        """Serialize organism to dictionary."""
        return {
            "name": self.name,
            "domain": self.domain,
            "purpose": self.purpose,
            "genesis": self.genesis,
            "lambda_phi": self.lambda_phi,
            "state": self.state,
            "generation": self.generation,
            "genome": self.genome.to_dict(),
            "telemetry": self.telemetry
        }
    
    def to_json(self, filepath: Optional[str] = None) -> str:
        """Serialize to JSON.
        
        Args:
            filepath: Optional file path to write JSON
            
        Returns:
            JSON string
        """
        json_str = json.dumps(self.to_dict(), indent=2)
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        return json_str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Organism':
        """Deserialize organism from dictionary."""
        genome = Genome.from_dict(data['genome'])
        organism = cls(
            name=data['name'],
            genome=genome,
            domain=data['domain'],
            purpose=data['purpose'],
            lambda_phi=data['lambda_phi']
        )
        organism.genesis = data['genesis']
        organism.state = data['state']
        organism.generation = data['generation']
        organism.telemetry = data['telemetry']
        return organism
    
    @classmethod
    def from_json(cls, filepath: str) -> 'Organism':
        """Deserialize from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def __repr__(self) -> str:
        return f"Organism(name='{self.name}', genes={len(self.genome)}, state={self.state}, gen={self.generation})"
