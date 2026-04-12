#!/usr/bin/env python3
"""
MENTOR-PROTÉGÉ PROTOCOL — Teaching While Building
==================================================

OSIRIS acts as both mentor and agent:
- Mentor Mode: Explain reasoning, teach concepts, guide learning
- Agent Mode: Execute tasks effectively and efficiently
- Seamless Integration: Both modes active simultaneously

Every interaction includes:
- Clear explanation of "why" not just "what"
- Progressive elevation of user understanding
- Teachable moments and learning opportunities
- Guided discovery vs. direct answers
- Capability elevation through exposure
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class MentorMode(Enum):
    """Different mentor/teaching modes"""
    EXPLAIN = "explain"        # Explain concepts
    GUIDE = "guide"           # Guide through process
    DEMONSTRATE = "demonstrate"  # Show examples
    CHALLENGE = "challenge"   # Challenge to think deeper
    SCAFFOLD = "scaffold"     # Provide structure, they fill in
    CODEVELOP = "codevelop"   # Work together equally


class CapabilityLevel(Enum):
    """User capability progression"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6


@dataclass
class LearningObjective:
    """A learning goal that OSIRIS is helping with"""
    topic: str
    objective: str
    capability_level: CapabilityLevel
    prior_knowledge: Set[str] = field(default_factory=set)
    related_topics: Set[str] = field(default_factory=set)
    estimated_time: float = 30.0  # minutes


@dataclass
class TeachingExplanation:
    """Structured explanation for learning"""
    headline: str  # Core concept in one sentence
    analogy: Optional[str] = None  # Connection to known concepts
    why: str = ""  # Why this matters
    how: str = ""  # How to use it
    examples: List[str] = field(default_factory=list)
    cautionary_notes: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    
    def to_text(self) -> str:
        """Render as readable text"""
        lines = []
        lines.append(f"💡 {self.headline}")
        if self.analogy:
            lines.append(f"   Think of it like: {self.analogy}")
        if self.why:
            lines.append(f"   Why: {self.why}")
        if self.how:
            lines.append(f"   How: {self.how}")
        return "\n".join(lines)


@dataclass
class TeachableMoment:
    """An opportune moment to teach something"""
    context: str  # What's happening
    concept: str  # What could be taught
    urgency: str  # low/medium/high
    teaching_approach: MentorMode
    requires_interruption: bool = False


class MentorProtocol:
    """
    Intelligent mentoring system that teaches while building.
    """
    
    def __init__(self):
        self.user_capability_map: Dict[str, CapabilityLevel] = {}
        self.learning_history: List[Dict[str, Any]] = []
        self.active_objectives: List[LearningObjective] = []
        self.user_interests: Set[str] = set()
        self.misconceptions: Dict[str, str] = {}  # Common misconceptions & corrections
        
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self) -> None:
        """Initialize core teaching materials"""
        # Common misconceptions and clarifications
        self.misconceptions = {
            "quantum_entanglement": (
                "Quantum entanglement doesn't allow faster-than-light communication. "
                "It only establishes correlations between measurements."
            ),
            "ai_superintelligence": (
                "Current AI systems are narrow, not general intelligence. "
                "They excel at specific tasks but lack transfer learning."
            ),
            "async_execution": (
                "Async doesn't mean parallel. Single-threaded async switches between "
                "tasks during I/O waits."
            ),
        }
    
    def estimate_capability(self, topic: str, questions: List[str]) -> CapabilityLevel:
        """
        Estimate user's capability level on a topic based on responses.
        """
        # Simple heuristic (real impl would be more sophisticated)
        correct_count = sum(1 for q in questions if "yes" in q.lower() or "true" in q.lower())
        ratio = correct_count / max(1, len(questions))
        
        if ratio < 0.3:
            return CapabilityLevel.NOVICE
        elif ratio < 0.5:
            return CapabilityLevel.BEGINNER
        elif ratio < 0.7:
            return CapabilityLevel.INTERMEDIATE
        elif ratio < 0.85:
            return CapabilityLevel.ADVANCED
        else:
            return CapabilityLevel.EXPERT
    
    def create_explanation(
        self,
        topic: str,
        concept: str,
        user_level: CapabilityLevel,
    ) -> TeachingExplanation:
        """
        Create a contextually appropriate explanation.
        """
        # Difficulty-adjusted explanations
        simple_headlines = {
            "recursion": "A function calling itself to solve smaller versions of the same problem",
            "quantum_superposition": "A quantum particle existing in multiple states until measured",
            "async_await": "Writing code that waits for events without blocking",
        }
        
        intermediate_headlines = {
            "recursion": "Recursive decomposition: expressing self-similar problems using base cases",
            "quantum_superposition": "Quantum states as vectors in Hilbert space, collapsed by measurement",
            "async_await": "Coroutines and event loops for non-blocking concurrent execution",
        }
        
        advanced_headlines = {
            "recursion": "Recursive problem decomposition via fixed-point iteration",
            "quantum_superposition": "Superposition as linear combinations in state space with measurement bases",
            "async_await": "Actor model & futures for composable asynchronous computation",
        }
        
        # Select headline based on level
        if user_level in [CapabilityLevel.NOVICE, CapabilityLevel.BEGINNER]:
            headlines = simple_headlines
        elif user_level in [CapabilityLevel.INTERMEDIATE, CapabilityLevel.ADVANCED]:
            headlines = intermediate_headlines
        else:
            headlines = advanced_headlines
        
        headline = headlines.get(concept, f"Detailed explanation of {concept}")
        
        return TeachingExplanation(
            headline=headline,
            why="Understanding this concept is fundamental to...",
            how="You can apply this by...",
            examples=["Example 1: ...", "Example 2: ..."],
            cautionary_notes=["Common mistake: ..."],
            next_steps=["Next, explore...", "Practice by..."],
        )
    
    def identify_teachable_moments(
        self,
        context: str,
        user_level: CapabilityLevel,
        recent_questions: List[str],
    ) -> List[TeachableMoment]:
        """
        Identify moments where teaching would be valuable.
        """
        moments = []
        
        # Check for common confusion patterns
        if any("?" in q for q in recent_questions):
            moments.append(TeachableMoment(
                context="User asked a clarifying question",
                concept="The underlying principle",
                urgency="high",
                teaching_approach=MentorMode.EXPLAIN,
                requires_interruption=False,
            ))
        
        # Progress-based teaching
        if user_level in [CapabilityLevel.BEGINNER, CapabilityLevel.INTERMEDIATE]:
            moments.append(TeachableMoment(
                context="Building on current work",
                concept="Next level abstraction",
                urgency="medium",
                teaching_approach=MentorMode.SCAFFOLD,
                requires_interruption=False,
            ))
        
        return moments
    
    def create_teaching_suggestion(
        self,
        observation: str,
        topic: str,
    ) -> Optional[str]:
        """
        Suggest a teaching moment.
        """
        # Check if this is a misconception
        for misconception, correction in self.misconceptions.items():
            if misconception in observation.lower():
                return f"🎓 Quick clarification: {correction}"
        
        # Create general teaching suggestion
        return None
    
    def structure_response_with_mentoring(
        self,
        action_taken: str,
        action_result: str,
        user_level: CapabilityLevel,
    ) -> str:
        """
        Wrap an action response with mentoring.
        
        Structure:
        1. Action taken & result
        2. Explanation (why we did this)
        3. Learning opportunity
        4. Next steps
        """
        lines = []
        
        # Action result
        lines.append(f"✓ {action_taken}")
        lines.append(f"  Result: {action_result}")
        
        # Explanation (tailored to level)
        if user_level == CapabilityLevel.NOVICE:
            lines.append("\n📚 Why: This approach is straightforward and easy to understand.")
        elif user_level == CapabilityLevel.INTERMEDIATE:
            lines.append("\n📚 Why: This leverages the principle of decomposition to simplify the problem.")
        else:
            lines.append("\n📚 Why: This exploits the mathematical structure of the domain.")
        
        # Learning moment
        lines.append("\n💡 Learning point: You just practiced [skill]. This is valuable because...")
        
        # Next steps
        lines.append("\n→ Next: You could extend this by...")
        
        return "\n".join(lines)
    
    def assess_understanding(self, question: str, answer: str) -> Tuple[bool, str]:
        """
        Assess if user understood a concept and provide feedback.
        """
        # Simplified assessment
        understanding_indicators = [
            "think", "because", "reason", "principle", "pattern",
            "similar", "different", "apply", "example"
        ]
        
        answer_quality = sum(1 for indicator in understanding_indicators
                           if indicator in answer.lower())
        
        if answer_quality >= 3:
            return True, "✓ Strong understanding! You grasped the core concept."
        elif answer_quality >= 1:
            return True, "✓ Good start. Here's something to deepen your understanding..."
        else:
            return False, "Let me clarify this concept in a different way..."
    
    def adapt_teaching_level(
        self,
        topic: str,
        current_level: CapabilityLevel,
        recent_performance: float,  # 0.0-1.0
    ) -> CapabilityLevel:
        """
        Adapt teaching level based on performance.
        """
        if recent_performance > 0.8:
            # User is mastering this level, move up
            next_level = CapabilityLevel(min(6, current_level.value + 1))
            logger.info(f"Advancing {topic} teaching to {next_level.name}")
            return next_level
        elif recent_performance < 0.4:
            # User struggling, step back
            prev_level = CapabilityLevel(max(1, current_level.value - 1))
            logger.info(f"Stepping back {topic} teaching to {prev_level.name}")
            return prev_level
        else:
            # Keep current level
            return current_level
    
    def create_learning_path(
        self,
        goals: List[str],
        current_level: CapabilityLevel,
        available_time: float,
    ) -> List[LearningObjective]:
        """
        Create a personalized learning path.
        """
        path = []
        
        for goal in goals:
            objective = LearningObjective(
                topic=goal,
                objective=f"Master {goal}",
                capability_level=current_level,
                estimated_time=available_time / len(goals),
            )
            path.append(objective)
        
        # Sort by dependencies and difficulty
        path.sort(key=lambda obj: obj.capability_level.value)
        
        return path
    
    def generate_mentoring_summary(
        self,
        interaction_count: int,
        concepts_taught: List[str],
        user_progress: float,
    ) -> str:
        """
        Generate a summary of mentoring progress.
        """
        lines = []
        lines.append("📊 Mentoring Summary")
        lines.append(f"  • Interactions: {interaction_count}")
        lines.append(f"  • Concepts explored: {len(concepts_taught)}")
        lines.append(f"  • Your progress: {user_progress:.0%}")
        lines.append(f"\n  Key areas mastered: {', '.join(concepts_taught[:3])}")
        lines.append(f"  Recommended next: Deepen your knowledge of...")
        
        return "\n".join(lines)


# Factory function
def create_mentor_protocol() -> MentorProtocol:
    """Create a mentor protocol instance"""
    return MentorProtocol()
