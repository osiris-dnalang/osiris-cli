"""
osiris.organisms.gene — Gene data unit
======================================

A Gene is the atomic unit of an Organism's genome.
Each gene has a name, expression level, action callback, and trigger condition.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import random


@dataclass
class Gene:
    """Atomic unit of an Organism's genome."""

    name: str
    expression: float = 0.5
    action: Optional[Callable] = None
    trigger: Optional[Callable[..., bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mutate(self, rate: float = 0.1) -> 'Gene':
        delta = random.gauss(0, rate)
        new_expr = max(0.0, min(1.0, self.expression + delta))
        return Gene(
            name=self.name,
            expression=new_expr,
            action=self.action,
            trigger=self.trigger,
            metadata={**self.metadata, 'mutated': True, 'mutation_delta': delta},
        )

    def express(self, context: Optional[Dict[str, Any]] = None) -> Any:
        if self.trigger and context:
            if not self.trigger(context):
                return None
        if self.action:
            return self.action(self.expression, context or {})
        return self.expression

    def crossover(self, other: 'Gene') -> 'Gene':
        alpha = random.random()
        new_expr = alpha * self.expression + (1 - alpha) * other.expression
        return Gene(
            name=self.name,
            expression=new_expr,
            action=self.action,
            trigger=self.trigger,
            metadata={'crossover_from': [self.name, other.name]},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'expression': self.expression,
            'has_action': self.action is not None,
            'has_trigger': self.trigger is not None,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Gene':
        return cls(
            name=data['name'],
            expression=data.get('expression', 0.5),
            metadata=data.get('metadata', {}),
        )
