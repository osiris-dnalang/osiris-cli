"""
Gene: Functional unit of DNA-Lang organisms
==========================================

A gene encodes a specific trait or behavior with an expression level
that can be modulated through quantum execution.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any
import numpy as np


@dataclass
class Gene:
    """A functional unit encoding organism behavior.
    
    Attributes:
        name: Gene identifier
        expression: Expression level [0.0, 1.0] - probability of activation
        action: Function executed when gene is expressed
        trigger: Condition that activates the gene
        metadata: Additional gene properties
    """
    
    name: str
    expression: float = 1.0
    action: Optional[Callable] = None
    trigger: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate gene parameters."""
        if not 0.0 <= self.expression <= 1.0:
            raise ValueError(f"Expression must be in [0,1], got {self.expression}")
        
        # Set default action if none provided
        if self.action is None:
            self.action = lambda: f"Gene {self.name} expressed"
    
    def mutate(self, delta: float = 0.05) -> 'Gene':
        """Apply random mutation to expression level.
        
        Args:
            delta: Maximum mutation magnitude
            
        Returns:
            Mutated copy of this gene
        """
        mutation = np.random.uniform(-delta, delta)
        new_expression = np.clip(self.expression + mutation, 0.0, 1.0)
        
        return Gene(
            name=self.name,
            expression=new_expression,
            action=self.action,
            trigger=self.trigger,
            metadata={**self.metadata, 'mutated': True}
        )
    
    def express(self) -> Any:
        """Execute gene action with probability based on expression level.
        
        Returns:
            Action result if expressed, None otherwise
        """
        if np.random.random() < self.expression:
            return self.action() if callable(self.action) else self.action
        return None
    
    def crossover(self, other: 'Gene') -> 'Gene':
        """Perform crossover with another gene.
        
        Args:
            other: Gene to crossover with
            
        Returns:
            Offspring gene
        """
        if self.name != other.name:
            raise ValueError(f"Cannot crossover different genes: {self.name} vs {other.name}")
        
        # Blend expression levels
        offspring_expression = (self.expression + other.expression) / 2.0
        
        return Gene(
            name=self.name,
            expression=offspring_expression,
            action=self.action,  # Inherit from parent 1
            trigger=self.trigger,
            metadata={'crossover': True}
        )
    
    def to_dict(self) -> dict:
        """Serialize gene to dictionary."""
        return {
            'name': self.name,
            'expression': self.expression,
            'trigger': self.trigger,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict, action: Optional[Callable] = None) -> 'Gene':
        """Deserialize gene from dictionary."""
        return cls(
            name=data['name'],
            expression=data['expression'],
            action=action,
            trigger=data.get('trigger'),
            metadata=data.get('metadata', {})
        )
    
    def __repr__(self) -> str:
        return f"Gene(name='{self.name}', expression={self.expression:.3f})"
