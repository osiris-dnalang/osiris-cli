"""
osiris_core/personality.py
-------------------------
Defines the core personality and cognitive traits for the Osiris NCLLM agent.
Integrates with the agent system and CLI for real intelligence wiring.
"""

from enum import Enum
from typing import Dict, Any

class PersonalityTrait(Enum):
    CURIOSITY = "curiosity"
    CAUTION = "caution"
    CREATIVITY = "creativity"
    LOGIC = "logic"
    EMPATHY = "empathy"
    ASSERTIVENESS = "assertiveness"
    HUMOR = "humor"

class OsirisPersonality:
    def __init__(self, traits: Dict[PersonalityTrait, float] = None):
        # Default balanced personality
        self.traits = traits or {
            PersonalityTrait.CURIOSITY: 0.7,
            PersonalityTrait.CAUTION: 0.5,
            PersonalityTrait.CREATIVITY: 0.8,
            PersonalityTrait.LOGIC: 0.9,
            PersonalityTrait.EMPATHY: 0.6,
            PersonalityTrait.ASSERTIVENESS: 0.5,
            PersonalityTrait.HUMOR: 0.3,
        }

    def express(self, context: str) -> str:
        """Generate a response style based on personality and context."""
        # Example: modulate response based on traits
        if self.traits[PersonalityTrait.CURIOSITY] > 0.8:
            return f"I'm deeply curious about: {context}"
        if self.traits[PersonalityTrait.CREATIVITY] > 0.7:
            return f"Let's imagine a novel approach to: {context}"
        if self.traits[PersonalityTrait.LOGIC] > 0.8:
            return f"Analyzing logically: {context}"
        return f"Considering: {context}"

    def update_trait(self, trait: PersonalityTrait, value: float):
        self.traits[trait] = max(0.0, min(1.0, value))

    def summary(self) -> Dict[str, float]:
        return {trait.value: val for trait, val in self.traits.items()}
