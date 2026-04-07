#!/usr/bin/env python3
"""
HOTKEY ACTION ENGINE — Dynamic Context-Aware Hotkey Generator
==============================================================

Generates adaptive, context-aware hotkey bindings based on:
- Current intent and goals
- Available actions
- User's trajectory (discovery → implementation → validation)
- Success probability and impact
- Progressive complexity (basic → advanced)

Every response includes a dynamic hotkey list for single-keypress advancement.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class HotkeyPriority(Enum):
    """Priority levels for hotkey actions"""
    CRITICAL = 1  # Must present (e.g., quit)
    PRIMARY = 2   # Main path forward
    SECONDARY = 3 # Alternative paths
    ADVANCED = 4  # Expert/optimization options
    EXPLORATORY = 5  # Learning/discovery


class ActionType(Enum):
    """Types of actions"""
    ADVANCE = "advance"  # Move to next step
    EXECUTE = "execute"  # Run current task
    ANALYZE = "analyze"  # Deeper analysis
    REFINE = "refine"    # Improve current output
    ALTERNATE = "alternate"  # Try different approach
    EXPLORE = "explore"  # Go deeper into topic
    HELP = "help"        # Get guidance
    PAUSE = "pause"      # Take a break
    QUIT = "quit"        # Exit


@dataclass
class HotkeyAction:
    """Definition of a single hotkey action"""
    key: str  # Single character: 'a', 's', 'd', etc.
    description: str  # User-facing description
    action_type: ActionType  # Type of action
    callback: Optional[Callable] = None  # Function to execute
    priority: HotkeyPriority = HotkeyPriority.PRIMARY
    context_requirement: Optional[str] = None  # Required context
    params: Dict[str, Any] = field(default_factory=dict)
    success_probability: float = 0.8  # Estimated success rate
    impact_level: str = "medium"  # low/medium/high
    
    def to_display(self) -> str:
        """Format for user display"""
        prob_indicator = "✓" if self.success_probability > 0.7 else "~"
        impact_emoji = {"low": "○", "medium": "◎", "high": "●"}.get(self.impact_level, "•")
        return f"[{self.key.upper()}] {self.description} {prob_indicator}{impact_emoji}"
    
    def __hash__(self):
        return hash(self.key)
    
    def __eq__(self, other):
        if isinstance(other, HotkeyAction):
            return self.key == other.key
        return False


class HotkeyEngine:
    """
    Dynamic hotkey generation engine.
    
    Generates context-aware hotkey sets based on:
    - Current task/intent
    - Available next actions
    - User trajectory and preferences
    - Success probability
    """
    
    def __init__(self, max_hotkeys: int = 8):
        self.max_hotkeys = max_hotkeys
        self.available_keys = list("asdfghjkl")  # QWERTY home row + extended
        self.action_registry: Dict[str, HotkeyAction] = {}
        self.history: List[str] = []
        
        self._register_default_actions()
    
    def _register_default_actions(self) -> None:
        """Register standard actions"""
        # Standard actions always available
        self.register_action(HotkeyAction(
            key="q", description="Quit OSIRIS", 
            action_type=ActionType.QUIT,
            priority=HotkeyPriority.CRITICAL, success_probability=1.0
        ))
        
        self.register_action(HotkeyAction(
            key="?", description="Show help", 
            action_type=ActionType.HELP,
            priority=HotkeyPriority.CRITICAL, success_probability=1.0
        ))
    
    def register_action(self, action: HotkeyAction) -> None:
        """Register a hotkey action"""
        self.action_registry[action.key] = action
    
    def generate_hotkeys(
        self,
        intent_goal: str,
        suggested_actions: List[str],
        current_trajectory: str = "discovery",
        intent_graph: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        available_context: Optional[Set[str]] = None,
    ) -> List[HotkeyAction]:
        """
        Generate context-aware hotkeys for current situation.

        Args:
            intent_goal: Current primary goal
            suggested_actions: List of suggested next actions
            current_trajectory: discovery/implementation/validation/optimization
            intent_graph: Live intent graph frontier
            user_preferences: User preferences for action types
            available_context: Available context from system state

        Returns:
            List of HotkeyAction objects, sorted by priority
        """
        user_preferences = user_preferences or {}
        available_context = available_context or set()
        intent_graph = intent_graph or {}

        hotkeys = []
        used_keys = set()

        # 1. Generate frontier actions from the intent graph
        frontier_actions = self._extract_frontier_actions(intent_graph)
        for descriptor in frontier_actions:
            if len(hotkeys) >= self.max_hotkeys:
                break
            action = self._describe_hotkey_action(descriptor, current_trajectory)
            key = self._preferred_key_for_action(action)
            if key in used_keys:
                key = self._assign_key(used_keys)
            action.key = key
            hotkeys.append(action)
            used_keys.add(action.key)

        # 2. Use suggested actions from intent processor as a fallback
        if len(hotkeys) < self.max_hotkeys:
            primary_actions = self._generate_primary_actions(
                intent_goal, suggested_actions, current_trajectory
            )
            for action in primary_actions:
                if len(hotkeys) >= self.max_hotkeys:
                    break
                if action.key in used_keys:
                    action.key = self._assign_key(used_keys)
                hotkeys.append(action)
                used_keys.add(action.key)

        # 3. Add secondary/alternative paths
        if len(hotkeys) < self.max_hotkeys:
            secondary_actions = self._generate_secondary_actions(
                intent_goal, current_trajectory
            )
            for action in secondary_actions:
                if len(hotkeys) >= self.max_hotkeys:
                    break
                if action.key in used_keys:
                    action.key = self._assign_key(used_keys)
                hotkeys.append(action)
                used_keys.add(action.key)

        # 4. Add advanced/optimization options (if appropriate)
        if current_trajectory in ["implementation", "validation", "optimization"]:
            advanced_actions = self._generate_advanced_actions(intent_goal)
            for action in advanced_actions:
                if len(hotkeys) >= self.max_hotkeys:
                    break
                if action.key in used_keys:
                    action.key = self._assign_key(used_keys)
                hotkeys.append(action)
                used_keys.add(action.key)

        # 5. Add utility actions
        utility_actions = self._generate_utility_actions()
        for action in utility_actions:
            if len(hotkeys) >= self.max_hotkeys:
                break
            if action.key not in used_keys:
                hotkeys.append(action)
                used_keys.add(action.key)

        # Sort by priority
        hotkeys.sort(key=lambda a: (a.priority.value, -a.success_probability))

        # Record usage
        for action in hotkeys:
            self.history.append(action.key)

        return hotkeys[:self.max_hotkeys]
    
    def _generate_primary_actions(
        self,
        goal: str,
        suggested_actions: List[str],
        trajectory: str,
    ) -> List[HotkeyAction]:
        """Generate primary action set based on goal and trajectory"""
        actions = []
        
        goal_action_map = {
            "create": [
                HotkeyAction(
                    "a", "Auto-advance: Start implementation",
                    ActionType.ADVANCE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.9, impact_level="high"
                ),
                HotkeyAction(
                    "s", "Suggest architecture",
                    ActionType.ANALYZE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.85, impact_level="high"
                ),
            ],
            "debug": [
                HotkeyAction(
                    "a", "Auto-advance: Analyze error",
                    ActionType.ADVANCE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.8, impact_level="high"
                ),
                HotkeyAction(
                    "s", "Show error trace",
                    ActionType.ANALYZE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.95, impact_level="medium"
                ),
            ],
            "analyze": [
                HotkeyAction(
                    "a", "Deep analysis",
                    ActionType.ANALYZE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.85, impact_level="high"
                ),
                HotkeyAction(
                    "s", "Summarize findings",
                    ActionType.REFINE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.8, impact_level="medium"
                ),
            ],
            "optimize": [
                HotkeyAction(
                    "a", "Profile & optimize",
                    ActionType.EXECUTE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.75, impact_level="high"
                ),
                HotkeyAction(
                    "s", "Benchmark results",
                    ActionType.ANALYZE, priority=HotkeyPriority.PRIMARY,
                    success_probability=0.8, impact_level="medium"
                ),
            ],
        }
        
        actions = goal_action_map.get(goal, [
            HotkeyAction(
                "a", "Auto-advance",
                ActionType.ADVANCE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.75, impact_level="medium"
            ),
            HotkeyAction(
                "s", "Show suggestions",
                ActionType.ANALYZE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.85, impact_level="low"
            ),
        ])
        
        return actions
    
    def _generate_secondary_actions(
        self,
        goal: str,
        trajectory: str,
    ) -> List[HotkeyAction]:
        """Generate alternative/secondary action paths"""
        actions = []
        
        if trajectory == "discovery":
            actions = [
                HotkeyAction(
                    "e", "Explore examples",
                    ActionType.EXPLORE, priority=HotkeyPriority.SECONDARY,
                    success_probability=0.8, impact_level="medium"
                ),
                HotkeyAction(
                    "r", "Review resources",
                    ActionType.EXPLORE, priority=HotkeyPriority.SECONDARY,
                    success_probability=0.75, impact_level="low"
                ),
            ]
        else:
            actions = [
                HotkeyAction(
                    "e", "Execute current task",
                    ActionType.EXECUTE, priority=HotkeyPriority.SECONDARY,
                    success_probability=0.8, impact_level="high"
                ),
                HotkeyAction(
                    "r", "Refine output",
                    ActionType.REFINE, priority=HotkeyPriority.SECONDARY,
                    success_probability=0.75, impact_level="medium"
                ),
            ]
        
        return actions
    
    def _generate_advanced_actions(self, goal: str) -> List[HotkeyAction]:
        """Generate advanced/expert actions"""
        return [
            HotkeyAction(
                "x", "Expert mode: Custom command",
                ActionType.ALTERNATE, priority=HotkeyPriority.ADVANCED,
                success_probability=0.6, impact_level="high"
            ),
            HotkeyAction(
                "m", "Show metrics & telemetry",
                ActionType.ANALYZE, priority=HotkeyPriority.ADVANCED,
                success_probability=0.9, impact_level="low"
            ),
        ]
    
    def _generate_utility_actions(self) -> List[HotkeyAction]:
        """Generate utility actions"""
        return [
            HotkeyAction(
                "h", "Show context/history",
                ActionType.HELP, priority=HotkeyPriority.SECONDARY,
                success_probability=1.0, impact_level="low"
            ),
            HotkeyAction(
                "p", "Pause/take a break",
                ActionType.PAUSE, priority=HotkeyPriority.SECONDARY,
                success_probability=1.0, impact_level="low"
            ),
        ]

    def _extract_frontier_actions(self, intent_graph: Dict[str, Any]) -> List[str]:
        """Extract top frontier actions from the intent graph."""
        if not intent_graph:
            return []
        nodes = intent_graph.get("nodes", [])
        action_nodes = [n for n in nodes if n.get("type") == "action"]
        action_nodes.sort(key=lambda n: (-n.get("score", 0.0), n.get("label", "")))
        return [n.get("label", "") for n in action_nodes[:4]]

    def _describe_hotkey_action(self, descriptor: str, trajectory: str) -> HotkeyAction:
        """Create a hotkey action based on descriptor semantics."""
        descriptor_lower = descriptor.lower()
        if "analyze" in descriptor_lower or "inspect" in descriptor_lower:
            return HotkeyAction(
                "s", "Simulate / analyze outcome",
                ActionType.ANALYZE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.85, impact_level="high"
            )
        if "develop" in descriptor_lower or "implement" in descriptor_lower or "build" in descriptor_lower:
            return HotkeyAction(
                "a", "Execute next best step",
                ActionType.EXECUTE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.9, impact_level="high"
            )
        if "optimize" in descriptor_lower or "refine" in descriptor_lower or "improve" in descriptor_lower:
            return HotkeyAction(
                "w", "Optimize current solution",
                ActionType.REFINE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.8, impact_level="high"
            )
        if "explain" in descriptor_lower or "teach" in descriptor_lower or "educate" in descriptor_lower:
            return HotkeyAction(
                "e", "Explain reasoning",
                ActionType.HELP, priority=HotkeyPriority.PRIMARY,
                success_probability=0.9, impact_level="medium"
            )
        if "spawn" in descriptor_lower or "agent" in descriptor_lower:
            return HotkeyAction(
                "f", "Spawn agent swarm",
                ActionType.EXPLORE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.8, impact_level="high"
            )
        if "test" in descriptor_lower or "validate" in descriptor_lower:
            return HotkeyAction(
                "t", "Run tests / validation",
                ActionType.EXECUTE, priority=HotkeyPriority.PRIMARY,
                success_probability=0.85, impact_level="high"
            )
        if "discover" in descriptor_lower or "explore" in descriptor_lower:
            return HotkeyAction(
                "x", "Explore alternative strategies",
                ActionType.EXPLORE, priority=HotkeyPriority.EXPLORATORY,
                success_probability=0.75, impact_level="medium"
            )
        if "decompose" in descriptor_lower or "break" in descriptor_lower or "plan" in descriptor_lower:
            return HotkeyAction(
                "d", "Decompose into subtasks",
                ActionType.ADVANCE, priority=HotkeyPriority.SECONDARY,
                success_probability=0.8, impact_level="medium"
            )

        return HotkeyAction(
            "a", f"Execute: {descriptor}",
            ActionType.ADVANCE, priority=HotkeyPriority.SECONDARY,
            success_probability=0.75, impact_level="medium"
        )

    def _preferred_key_for_action(self, action: HotkeyAction) -> str:
        """Choose a consistent key for an action."""
        mapping = {
            ActionType.ADVANCE: "a",
            ActionType.ANALYZE: "s",
            ActionType.EXECUTE: "a",
            ActionType.REFINE: "w",
            ActionType.ALTERNATE: "x",
            ActionType.EXPLORE: "x",
            ActionType.HELP: "e",
            ActionType.PAUSE: "p",
            ActionType.QUIT: "q",
        }
        return mapping.get(action.action_type, action.key)
    
    def _assign_key(self, used_keys: Set[str]) -> str:
        """Assign next available key"""
        for key in self.available_keys:
            if key not in used_keys:
                return key
        # Fallback to numbers if we run out
        for i in range(10):
            if str(i) not in used_keys:
                return str(i)
        return "?"
    
    def render_hotkeys(self, hotkeys: List[HotkeyAction], width: int = 80) -> str:
        """Render hotkey list for display"""
        lines = []
        lines.append("╔═══ HOTKEY ACTIONS ═══╗")
        
        # Group by priority
        by_priority = {}
        for action in hotkeys:
            if action.priority not in by_priority:
                by_priority[action.priority] = []
            by_priority[action.priority].append(action)
        
        # Render each group
        priority_order = [
            HotkeyPriority.PRIMARY,
            HotkeyPriority.SECONDARY,
            HotkeyPriority.ADVANCED,
            HotkeyPriority.EXPLORATORY,
            HotkeyPriority.CRITICAL,
        ]
        
        for priority in priority_order:
            if priority in by_priority:
                if priority != HotkeyPriority.CRITICAL:
                    section_name = priority.name.title()
                    lines.append(f"\n• {section_name}:")
                
                for action in by_priority[priority]:
                    lines.append(f"  {action.to_display()}")
        
        # Add critical actions at bottom
        if HotkeyPriority.CRITICAL in by_priority:
            lines.append("\n• Always available:")
            for action in by_priority[HotkeyPriority.CRITICAL]:
                lines.append(f"  {action.to_display()}")
        
        lines.append("\n╚════════════════════════╝")
        return "\n".join(lines)
    
    def process_hotkey(self, key: str) -> Optional[HotkeyAction]:
        """Process a pressed hotkey"""
        for action in self.action_registry.values():
            if action.key == key:
                return action
        return None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about hotkey usage"""
        from collections import Counter
        counts = Counter(self.history)
        return {
            "total_presses": len(self.history),
            "unique_keys": len(counts),
            "most_popular": counts.most_common(5) if counts else [],
        }


# Factory function
def create_hotkey_engine(max_hotkeys: int = 8) -> HotkeyEngine:
    """Create a hotkey engine"""
    return HotkeyEngine(max_hotkeys=max_hotkeys)
