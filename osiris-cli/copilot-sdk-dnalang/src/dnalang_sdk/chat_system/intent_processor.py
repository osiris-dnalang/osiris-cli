#!/usr/bin/env python3
"""
INTENT PROCESSOR — Advanced NLP Intent Deduction Engine
========================================================

Continuously infers user intent from context, history, and free-form input.
Supports multi-domain understanding beyond quantum computing.

Architecture:
  - Semantic analysis (what the user wants)
  - Context evolution (learning from interaction history)
  - Autonomous suggestion engine (next best actions)
  - Trajectory inference (project arc understanding)
"""

from __future__ import annotations
import re
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path

from .memory_graph import MemoryGraph, create_memory_graph

logger = logging.getLogger(__name__)

# Keywords mapped to intent categories
INTENT_KEYWORDS = {
    # Development/Engineering
    "build": ["development", "implementation", "creation"],
    "write": ["development", "coding"],
    "debug": ["troubleshooting", "analysis"],
    "fix": ["troubleshooting", "maintenance"],
    "optimize": ["performance", "refinement"],
    "refactor": ["quality", "cleanup"],
    "test": ["validation", "qa"],
    "deploy": ["devops", "release"],
    
    # Analysis/Research
    "analyze": ["analysis", "research"],
    "research": ["research", "investigation"],
    "explain": ["education", "documentation"],
    "understand": ["education", "research"],
    "summarize": ["synthesis", "documentation"],
    
    # Quantum/Physics
    "quantum": ["quantum", "physics"],
    "circuit": ["quantum", "implementation"],
    "consciousness": ["consciousness", "measurement"],
    "simulation": ["quantum", "analysis"],
    
    # Data/Learning
    "data": ["data", "analysis"],
    "model": ["ml", "analysis"],
    "train": ["ml", "development"],
    "predict": ["ml", "analysis"],
    
    # Project Management
    "project": ["management", "planning"],
    "sprint": ["management", "agile"],
    "task": ["management", "execution"],
    "team": ["collaboration", "management"],
}

# Domain categories
DOMAINS = [
    "quantum",
    "development",
    "ml",
    "data",
    "devops",
    "research",
    "education",
    "analysis",
    "management",
    "collaboration",
    "troubleshooting",
    "performance",
]

class IntentConfidence(Enum):
    """Confidence levels for intent deduction"""
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.2


@dataclass
class IntentAction:
    """Represents a deduced user action or goal"""
    action: str  # e.g., "write_code", "analyze_data", "create_task"
    domain: str  # e.g., "development", "quantum", "data"
    confidence: float  # 0.0-1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "domain": self.domain,
            "confidence": self.confidence,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
        }


@dataclass
class IntentGraphNode:
    """Node in the intent graph"""
    node_id: str
    label: str
    node_type: str
    score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "type": self.node_type,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class IntentGraphEdge:
    """Edge in the intent graph"""
    source: str
    target: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
        }


@dataclass
class UserIntent:
    """Complete user intent representation"""
    primary_goal: str  # What user ultimately wants
    actions: List[IntentAction] = field(default_factory=list)
    domains: Set[str] = field(default_factory=set)
    intent_graph: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    trajectory: str = "discovery"  # discovery, implementation, validation, optimization
    previous_intents: List[str] = field(default_factory=list)
    suggested_next_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_goal": self.primary_goal,
            "actions": [a.to_dict() for a in self.actions],
            "domains": list(self.domains),
            "intent_graph": self.intent_graph,
            "context": self.context,
            "confidence": self.confidence,
            "trajectory": self.trajectory,
            "previous_intents": self.previous_intents,
            "suggested_next_steps": self.suggested_next_steps,
        }


class IntentProcessor:
    """
    Advanced intent deduction engine supporting:
    - Free-form natural language input
    - Multi-domain understanding
    - Context evolution across interactions
    - Autonomous suggestion of next steps
    - Progressive goal refinement
    """
    
    def __init__(
        self,
        context_window_size: int = 20,
        enable_learning: bool = True,
        state_dir: Optional[Path] = None,
    ):
        self.context_window_size = context_window_size
        self.enable_learning = enable_learning
        self.state_dir = Path(state_dir) if state_dir else Path.home() / ".osiris" / "intent"
        self.state_dir.mkdir(exist_ok=True, parents=True)
        
        # Interaction history
        self.interaction_history: List[Dict[str, Any]] = []
        self.previous_intents: List[str] = []
        
        # Learned patterns
        self.learned_patterns: Dict[str, List[str]] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.memory_graph = create_memory_graph(state_dir=self.state_dir / "memory_graph")
        
        self._load_state()
    
    def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> UserIntent:
        """
        Process free-form user input and deduce intent.
        
        Args:
            user_input: Raw user text (natural language)
            context: Optional contextual information (previous work, env state, etc.)
        
        Returns:
            UserIntent object with deduced goals and actions
        """
        context = context or {}
        
        # Clean and normalize input
        cleaned_input = self._normalize_input(user_input)
        
        # Extract keywords and domains
        keywords = self._extract_keywords(cleaned_input)
        detected_domains = self._detect_domains(keywords, cleaned_input)
        
        # Deduce primary goal
        primary_goal = self._deduce_primary_goal(cleaned_input, keywords, context)
        # Extract constraints, skill level, urgency
        constraints = self._extract_constraints(cleaned_input)
        skill_level = self._estimate_skill_level(cleaned_input)
        urgency = self._estimate_urgency(cleaned_input)
        
        # Generate actions
        actions = self._generate_actions(primary_goal, keywords, detected_domains)
        
        # Build an intent graph for the current input
        intent_graph = self._build_intent_graph(
            primary_goal, actions, keywords, detected_domains, constraints
        )
        
        # Determine trajectory
        trajectory = self._determine_trajectory(primary_goal, context, self.previous_intents)
        
        # Generate suggestions for next steps
        next_steps = self._suggest_next_steps(primary_goal, actions, trajectory)
        
        # Build intent object
        intent = UserIntent(
            primary_goal=primary_goal,
            actions=actions,
            domains=detected_domains,
            intent_graph=intent_graph,
            context={
                "constraints": constraints,
                "skill_level": skill_level,
                "urgency": urgency,
                **context,
            },
            confidence=self._calculate_confidence(keywords, actions, constraints, urgency),
            trajectory=trajectory,
            previous_intents=self.previous_intents[-5:],  # Last 5 intents
            suggested_next_steps=next_steps,
        )
        
        # Update history and learn
        self._record_interaction(user_input, intent)
        if self.enable_learning:
            self._learn_from_interaction(cleaned_input, intent)
            self._update_memory_graph(
            self._learn_from_interaction(cleaned_input, intent)
        
            return intent
    
    def _normalize_input(self, text: str) -> str:
        """Normalize user input"""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract action keywords from text"""
        keywords = set()
        for keyword in INTENT_KEYWORDS.keys():
            if keyword in text:
                keywords.add(keyword)
        
        # Extract noun phrases (simplified)
        words = text.split()
        for word in words:
            if len(word) > 3:  # Simple heuristic
                keywords.add(word.strip(".,!?"))
        
        return keywords
    
    def _detect_domains(self, keywords: Set[str], text: str) -> Set[str]:
        """Detect applicable domains"""
        domains = set()
        
        for keyword, associated_domains in INTENT_KEYWORDS.items():
            if keyword in keywords:
                domains.update(associated_domains)
        
        # Domain-specific detection
        if any(w in text for w in ["quantum", "qiskit", "cirq", "qubit", "circuit"]):
            domains.add("quantum")
        if any(w in text for w in ["code", "function", "class", "module", "script"]):
            domains.add("development")
        if any(w in text for w in ["model", "train", "predict", "dataset", "ml"]):
            domains.add("ml")
        if any(w in text for w in ["task", "sprint", "backlog", "story", "milestone"]):
            domains.add("management")
        if any(w in text for w in ["debug", "error", "issue", "break", "fail"]):
            domains.add("troubleshooting")
        
        return domains if domains else {"general"}
    
    def _deduce_primary_goal(
        self,
        text: str,
        keywords: Set[str],
        context: Dict[str, Any],
    ) -> str:
        """Deduce the primary goal from input"""
        # Check for explicit goals
        goal_patterns = [
            (r"(?:create|build|write|make).*?(?:for|to|that)", "create"),
            (r"(?:debug|fix|troubleshoot).*?(?:with|that|is)", "debug"),
            (r"(?:analyze|examine|understand).*?(?:the|my|this)", "analyze"),
            (r"(?:optimize|improve|speed up).*?(?:the|my|this)", "optimize"),
            (r"(?:test|validate|check).*?(?:the|my|this)", "validate"),
            (r"(?:explain|teach|show me).*?(?:how|about|what)", "educate"),
        ]
        
        for pattern, goal_type in goal_patterns:
            if re.search(pattern, text):
                return goal_type
        
        # Fallback: infer from keywords
        if "build" in keywords or "write" in keywords or "create" in keywords:
            return "create"
        elif "debug" in keywords or "fix" in keywords:
            return "debug"
        elif "analyze" in keywords or "research" in keywords:
            return "analyze"
        elif "optimize" in keywords or "improve" in keywords:
            return "optimize"
        elif "explain" in keywords or "understand" in keywords:
            return "educate"
        
        # Check context for continuation
        if context.get("previous_goal"):
            return "continue_" + context.get("previous_goal", "create")
        
        # Default
        return "discover"
    
    def _generate_actions(
        self,
        goal: str,
        keywords: Set[str],
        domains: Set[str],
    ) -> List[IntentAction]:
        """Generate specific actions for the goal"""
        actions = []
        
        # Map goal to actions
        goal_action_map = {
            "create": [
                IntentAction("analyze_requirements", "general", 0.9),
                IntentAction("design_solution", "general", 0.85),
                IntentAction("implement", "development", 0.8),
                IntentAction("test", "qa", 0.75),
            ],
            "debug": [
                IntentAction("reproduce_issue", "troubleshooting", 0.9),
                IntentAction("analyze_cause", "analysis", 0.85),
                IntentAction("implement_fix", "development", 0.8),
                IntentAction("validate_fix", "qa", 0.75),
            ],
            "analyze": [
                IntentAction("gather_data", "data", 0.9),
                IntentAction("structure_data", "data", 0.85),
                IntentAction("perform_analysis", "analysis", 0.8),
                IntentAction("synthesize_insights", "research", 0.75),
            ],
            "optimize": [
                IntentAction("profile_performance", "performance", 0.9),
                IntentAction("identify_bottlenecks", "analysis", 0.85),
                IntentAction("improve_code", "development", 0.8),
                IntentAction("benchmark_results", "qa", 0.75),
            ],
            "educate": [
                IntentAction("gather_context", "research", 0.9),
                IntentAction("structure_explanation", "education", 0.85),
                IntentAction("provide_examples", "education", 0.8),
                IntentAction("offer_resources", "research", 0.75),
            ],
            "discover": [
                IntentAction("gather_information", "research", 0.85),
                IntentAction("explore_domain", "research", 0.8),
                IntentAction("synthesize_knowledge", "analysis", 0.75),
                IntentAction("generate_insights", "research", 0.7),
            ],
        }
        
        # Get base actions
        base_actions = goal_action_map.get(goal, goal_action_map["discover"])
        actions.extend(base_actions)
        
        # Refine based on domains
        for action in actions:
            if "quantum" in domains:
                action.domain = "quantum"
            elif "ml" in domains:
                action.domain = "ml"
            elif "management" in domains:
                action.domain = "management"
        
        return actions
    
    def _determine_trajectory(
        self,
        goal: str,
        context: Dict[str, Any],
        history: List[str],
    ) -> str:
        """Determine where user is in the project lifecycle"""
        # Early stage: discovery
        if len(history) < 3:
            return "discovery"
        
        # Check context
        if context.get("stage"):
            return context["stage"]
        
        # Check goal pattern
        recent_goals = history[-5:]
        if goal in recent_goals or len(set(recent_goals)) == 1:
            return "implementation"
        
        if any("optimize" in g or "improve" in g for g in recent_goals):
            return "optimization"
        
        if any("validate" in g or "test" in g for g in recent_goals):
            return "validation"
        
        return "implementation"
    
    def _suggest_next_steps(
        self,
        goal: str,
        actions: List[IntentAction],
        trajectory: str,
    ) -> List[str]:
        """Suggest logical next steps"""
        suggestions = []
        
        # Based on goal progression
        if self._detect_drift():
            return [
                "Pause and clarify the core objective",
                "Refocus on the most important constraint",
                "Review prior steps for consistency",
                "Identify the single highest-impact next move",
            ]

        if trajectory == "discovery":
            suggestions = [
                "Define core requirements",
                "Sketch architecture",
                "Identify key decisions",
                "Gather examples",
            ]
        elif trajectory == "implementation":
            suggestions = [
                "Start with MVP",
                "Write tests first",
                "Build core components",
                "Integrate subsystems",
                "Run full test suite",
            ]
        self,
        keywords: Set[str],
        actions: List[IntentAction],
        constraints: Dict[str, Any],
        urgency: str,
    ) -> float:
        """Calculate overall confidence in intent deduction"""
        if not keywords:
            return 0.25
        
        keyword_confidence = min(1.0, len(keywords) / 6.0)
        action_confidence = sum(a.confidence for a in actions) / max(1, len(actions))
        constraint_penalty = 0.0 if not constraints else 0.05
        urgency_bonus = 0.05 if urgency in ["high", "critical"] else 0.0
        
        return max(0.2, min(1.0, (keyword_confidence + action_confidence + urgency_bonus - constraint_penalty) / 2.0))
            suggestions = [
                "Profile bottlenecks",
                "Refactor hot paths",
                "Benchmark improvements",
                "Document learnings",
            ]
        
        return suggestions[:4]  # Return top 4 suggestions
    
    def _calculate_confidence(self, keywords: Set[str], actions: List[IntentAction]) -> float:
        """Calculate overall confidence in intent deduction"""
        if not keywords:
            return 0.3
        
        keyword_confidence = min(1.0, len(keywords) / 5.0)
        action_confidence = sum(a.confidence for a in actions) / max(1, len(actions))
        
        return (keyword_confidence + action_confidence) / 2.0
    
    def _record_interaction(self, user_input: str, intent: UserIntent) -> None:
        """Record interaction in history"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": user_input,
            "intent": intent.to_dict(),
        }
        self.interaction_history.append(entry)
        self.previous_intents.append(intent.primary_goal)
        
        # Keep history bounded
        if len(self.interaction_history) > self.context_window_size:
            self.interaction_history.pop(0)
        if len(self.previous_intents) > 10:
            self.previous_intents.pop(0)
    
    def _learn_from_interaction(self, text: str, intent: UserIntent) -> None:
        """Learn patterns from interaction"""
        goal = intent.primary_goal
        if goal not in self.learned_patterns:
            self.learned_patterns[goal] = []
        
        # Store pattern
        self.learned_patterns[goal].append(text[:100])
        
        # Limit storage
        if len(self.learned_patterns[goal]) > 50:
            self.learned_patterns[goal].pop(0)

    def _update_memory_graph(self, intent: UserIntent) -> None:
        """Update the memory graph with recent decision context"""
        root = self.memory_graph.add_node(intent.primary_goal, category="goal", weight=intent.confidence)
        domain_nodes = []
        for domain in intent.domains:
            domain_node = self.memory_graph.add_node(domain, category="domain", weight=0.7)
            self.memory_graph.add_edge(root.node_id, domain_node.node_id, relation="belongs_to", weight=0.8)
            domain_nodes.append(domain_node)

        for action in intent.actions:
            action_node = self.memory_graph.add_node(action.action, category="action", weight=action.confidence)
            self.memory_graph.add_edge(root.node_id, action_node.node_id, relation="supports", weight=action.confidence)
            for domain_node in domain_nodes:
                self.memory_graph.add_edge(action_node.node_id, domain_node.node_id, relation="serves", weight=0.6)

        for keyword in self._extract_keywords(intent.primary_goal):
            keyword_node = self.memory_graph.add_node(keyword, category="keyword", weight=0.5)
            self.memory_graph.add_edge(root.node_id, keyword_node.node_id, relation="mentions", weight=0.5)
        self.memory_graph.save_state()

    def _build_intent_graph(
        self,
        primary_goal: str,
        actions: List[IntentAction],
        keywords: Set[str],
        domains: Set[str],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a lightweight intent graph representation."""
        nodes = [
            IntentGraphNode(
                node_id=f"goal:{primary_goal}",
                label=primary_goal,
                node_type="goal",
                score=1.0,
                metadata={"constraints": constraints},
            )
        ]
        edges = []
        for action in actions:
            action_score = action.confidence * (1.0 + (0.1 if action.domain in domains else 0.0))
            node = IntentGraphNode(
                node_id=f"action:{action.action}",
                label=action.action,
                node_type="action",
                score=action_score,
                metadata={"domain": action.domain, "reasoning": action.reasoning},
            )
            nodes.append(node)
            edges.append(IntentGraphEdge(
                source=f"goal:{primary_goal}",
                target=node.node_id,
                relation="suggests",
                weight=action_score,
            ))

        for keyword in keywords:
            keyword_node = IntentGraphNode(
                node_id=f"keyword:{keyword}",
                label=keyword,
                node_type="keyword",
                score=0.5,
                metadata={},
            )
            nodes.append(keyword_node)
            edges.append(IntentGraphEdge(
                source=keyword_node.node_id,
                target=f"goal:{primary_goal}",
                relation="supports",
                weight=0.5,
            ))

        # Add latent goals / constraints as hidden nodes
        for latent in self._extract_latent_goals(primary_goal):
            latent_node = IntentGraphNode(
                node_id=f"latent:{latent}",
                label=latent,
                node_type="latent_goal",
                score=0.6,
                metadata={"origin": "latent"},
            )
            nodes.append(latent_node)
            edges.append(IntentGraphEdge(
                source=f"goal:{primary_goal}",
                target=latent_node.node_id,
                relation="implies",
                weight=0.6,
            ))

        return {
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
        }

    def _extract_constraints(self, text: str) -> Dict[str, Any]:
        """Extract constraint signals from user input."""
        constraints = {}
        if any(token in text for token in ["fast", "quick", "asap", "urgent", "immediately"]):
            constraints["time"] = "high"
        if any(token in text for token in ["secure", "safe", "encrypted", "compliant"]):
            constraints["security"] = True
        if any(token in text for token in ["cheap", "low cost", "budget"]):
            constraints["cost"] = "low"
        if any(token in text for token in ["scalable", "robust", "reliable"]):
            constraints["quality"] = "high"
        return constraints

    def _estimate_skill_level(self, text: str) -> str:
        """Estimate user skill level from phrasing."""
        if any(token in text for token in ["beginner", "novice", "new", "simple", "explain"]):
            return "novice"
        if any(token in text for token in ["intermediate", "help me", "guide"]):
            return "intermediate"
        if any(token in text for token in ["advanced", "expert", "optimize", "refactor"]):
            return "advanced"
        return "unknown"

    def _estimate_urgency(self, text: str) -> str:
        """Estimate relative urgency from user input."""
        if any(token in text for token in ["asap", "urgent", "immediately", "now"]):
            return "high"
        if any(token in text for token in ["soon", "shortly", "plan"]):
            return "medium"
        return "low"

    def _extract_latent_goals(self, goal: str) -> List[str]:
        """Map explicit goals to latent goal candidates."""
        latent_map = {
            "create": ["maintainability", "scalability", "deployment"],
            "debug": ["stability", "reliability", "confidence"],
            "analyze": ["insight", "explainability", "risk"],
            "optimize": ["performance", "efficiency", "cost"],
            "educate": ["clarity", "context", "intuition"],
            "discover": ["possibilities", "risks", "value"],
        }
        return latent_map.get(goal, [])

    def _detect_drift(self) -> bool:
        """Detect intent drift across recent interactions."""
        if len(self.previous_intents) < 4:
            return False
        recent = self.previous_intents[-5:]
        return len(set(recent)) > 3

    def _load_state(self) -> None:
        """Load saved state"""
        state_file = self.state_dir / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    self.learned_patterns = state.get("patterns", {})
                    self.user_preferences = state.get("preferences", {})
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
    
    def save_state(self) -> None:
        """Save learned patterns and preferences"""
        state_file = self.state_dir / "state.json"
        try:
            with open(state_file, "w") as f:
                json.dump({
                    "patterns": self.learned_patterns,
                    "preferences": self.user_preferences,
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context"""
        return {
            "interaction_count": len(self.interaction_history),
            "last_goals": self.previous_intents[-3:],
            "learned_patterns_count": len(self.learned_patterns),
            "preferences": self.user_preferences,
        }


# Convenience function
def create_intent_processor(state_dir: Optional[Path] = None) -> IntentProcessor:
    """Factory function to create intent processor"""
    return IntentProcessor(state_dir=state_dir)
