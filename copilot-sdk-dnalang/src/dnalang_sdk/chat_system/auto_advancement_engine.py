#!/usr/bin/env python3
"""
AUTO-ADVANCEMENT ENGINE — Autonomous Task Progression
=====================================================

Continuously advances tasks toward completion without explicit user commands.
Implements intelligent step-by-step progression:
- Recognizes task boundaries and milestones
- Suggests and auto-execute next logical steps
- Detects completion and validates results
- Handles errors and alternative paths
- Provides "flow state" interaction (minimal friction)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskPhase(Enum):
    """Phases of a task lifecycle"""
    INIT = "init"           # Just started
    ANALYSIS = "analysis"   # Understanding requirements
    PLANNING = "planning"   # Creating strategy
    EXECUTION = "execution" # Building/implementing
    TESTING = "testing"     # Validation
    REFINEMENT = "refinement"  # Optimization
    COMPLETION = "completion"  # Done
    REVIEW = "review"       # Post-mortem


class AutoAdvanceStrategy(Enum):
    """Advancement strategies"""
    AGGRESSIVE = "aggressive"  # Push forward as fast as possible
    BALANCED = "balanced"      # Balance speed and safety
    CONSERVATIVE = "conservative"  # Verify thoroughly before advancing
    EXPLORATORY = "exploratory"    # Try multiple paths


@dataclass
class AvailableStep:
    """A step that can be taken"""
    name: str
    description: str
    phase: TaskPhase
    prerequisite: Optional[str] = None
    estimated_duration: float = 5.0  # minutes
    success_probability: float = 0.8
    reversible: bool = True
    impact_level: str = "medium"  # low/medium/high
    
    def order_key(self) -> Tuple[int, float]:
        """Sort key (phase, then probability)"""
        phase_order = {
            TaskPhase.INIT: 0,
            TaskPhase.ANALYSIS: 1,
            TaskPhase.PLANNING: 2,
            TaskPhase.EXECUTION: 3,
            TaskPhase.TESTING: 4,
            TaskPhase.REFINEMENT: 5,
            TaskPhase.COMPLETION: 6,
            TaskPhase.REVIEW: 7,
        }
        return (phase_order.get(self.phase, 99), -self.success_probability)


@dataclass
class TaskState:
    """Current state of a task"""
    task_id: str
    goal: str
    current_phase: TaskPhase = TaskPhase.INIT
    completed_steps: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    overall_progress: float = 0.0  # 0.0-1.0
    context: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    last_action_time: Optional[datetime] = None
    
    def get_estimated_completion(self) -> float:
        """Estimate percent complete"""
        phase_progress = {
            TaskPhase.INIT: 0.05,
            TaskPhase.ANALYSIS: 0.15,
            TaskPhase.PLANNING: 0.25,
            TaskPhase.EXECUTION: 0.50,
            TaskPhase.TESTING: 0.75,
            TaskPhase.REFINEMENT: 0.90,
            TaskPhase.COMPLETION: 1.0,
            TaskPhase.REVIEW: 1.0,
        }
        return phase_progress.get(self.current_phase, 0.0)


class AutoAdvancementEngine:
    """
    Intelligent task advancement system.
    
    Continuously moves tasks forward by:
    1. Analyzing current state
    2. Identifying available next steps
    3. Selecting best step (success probability, impact)
    4. Executing step (or providing user choice)
    5. Validating result and updating state
    6. Repeating until task complete
    """
    
    def __init__(
        self,
        strategy: AutoAdvanceStrategy = AutoAdvanceStrategy.BALANCED,
        max_auto_advances: int = 5,
    ):
        self.strategy = strategy
        self.max_auto_advances = max_auto_advances
        self.tasks: Dict[str, TaskState] = {}
        self.step_registry: Dict[str, Dict[str, AvailableStep]] = {}
        self.advance_count = 0
        
        self._register_default_steps()
    
    def create_task(self, task_id: str, goal: str) -> TaskState:
        """Create a new task"""
        task = TaskState(task_id=task_id, goal=goal)
        self.tasks[task_id] = task
        return task
    
    def register_step(
        self,
        task_category: str,
        step: AvailableStep,
    ) -> None:
        """Register an available step"""
        if task_category not in self.step_registry:
            self.step_registry[task_category] = {}
        self.step_registry[task_category][step.name] = step
    
    def _register_default_steps(self) -> None:
        """Register standard task steps"""
        # Development task steps
        dev_steps = [
            AvailableStep(
                "gather_requirements", "Analyze requirements and objectives",
                TaskPhase.ANALYSIS, success_probability=0.9
            ),
            AvailableStep(
                "design_architecture", "Create high-level design/architecture",
                TaskPhase.PLANNING, prerequisite="gather_requirements",
                success_probability=0.8
            ),
            AvailableStep(
                "implement_skeleton", "Create project structure",
                TaskPhase.EXECUTION, prerequisite="design_architecture",
                success_probability=0.95
            ),
            AvailableStep(
                "implement_core", "Implement core functionality",
                TaskPhase.EXECUTION, prerequisite="implement_skeleton",
                success_probability=0.75
            ),
            AvailableStep(
                "write_tests", "Write unit/integration tests",
                TaskPhase.TESTING, prerequisite="implement_core",
                success_probability=0.8
            ),
            AvailableStep(
                "run_tests", "Execute all tests",
                TaskPhase.TESTING, prerequisite="write_tests",
                success_probability=0.85
            ),
            AvailableStep(
                "optimize_code", "Optimize performance",
                TaskPhase.REFINEMENT, prerequisite="run_tests",
                success_probability=0.7
            ),
            AvailableStep(
                "document", "Write documentation",
                TaskPhase.COMPLETION, prerequisite="optimize_code",
                success_probability=0.85
            ),
        ]
        
        for step in dev_steps:
            self.register_step("development", step)
        
        # Analysis task steps
        analysis_steps = [
            AvailableStep(
                "collect_data", "Gather and prepare data",
                TaskPhase.ANALYSIS, success_probability=0.85
            ),
            AvailableStep(
                "explore_data", "Explore data patterns",
                TaskPhase.ANALYSIS, prerequisite="collect_data",
                success_probability=0.8
            ),
            AvailableStep(
                "frame_hypothesis", "Create analysis hypothesis",
                TaskPhase.PLANNING, prerequisite="explore_data",
                success_probability=0.75
            ),
            AvailableStep(
                "run_analysis", "Execute analysis",
                TaskPhase.EXECUTION, prerequisite="frame_hypothesis",
                success_probability=0.8
            ),
            AvailableStep(
                "validate_results", "Validate analysis results",
                TaskPhase.TESTING, prerequisite="run_analysis",
                success_probability=0.75
            ),
            AvailableStep(
                "synthesize_insights", "Draw conclusions",
                TaskPhase.COMPLETION, prerequisite="validate_results",
                success_probability=0.8
            ),
        ]
        
        for step in analysis_steps:
            self.register_step("analysis", step)
    
    def get_next_steps(
        self,
        task_id: str,
        task_category: str = "development",
        limit: int = 3,
    ) -> List[AvailableStep]:
        """
        Get recommended next steps for a task.
        
        Returns steps sorted by:
        1. Prerequisites satisfied
        2. Phase progression
        3. Success probability
        """
        if task_id not in self.tasks:
            return []
        
        task = self.tasks[task_id]
        available_steps = self.step_registry.get(task_category, {})
        
        if not available_steps:
            return []
        
        candidates = []
        for step_name, step in available_steps.items():
            # Skip completed steps
            if step_name in task.completed_steps:
                continue
            
            # Check prerequisites
            if step.prerequisite and step.prerequisite not in task.completed_steps:
                continue
            
            # Check phase compatibility
            if step.phase.value < task.current_phase.value:
                continue
            
            candidates.append(step)
        
        # Sort candidates
        candidates.sort(key=lambda s: s.order_key())
        
        return candidates[:limit]
    
    def auto_advance(
        self,
        task_id: str,
        task_category: str = "development",
        callback: Optional[Callable[[AvailableStep], bool]] = None,
    ) -> List[AvailableStep]:
        """
        Automatically advance task through available steps.
        
        Args:
            task_id: Task to advance
            task_category: Type of task
            callback: Optional function to validate step execution
        
        Returns:
            List of steps that were advanced
        """
        if task_id not in self.tasks:
            return []
        
        task = self.tasks[task_id]
        advanced_steps = []
        
        for _ in range(self.max_auto_advances):
            # Get next step
            next_steps = self.get_next_steps(task_id, task_category, limit=1)
            if not next_steps:
                break
            
            next_step = next_steps[0]
            
            # Check if we should advance (based on strategy)
            if not self._should_advance(next_step):
                break
            
            # Execute step (or just record it)
            success = True
            if callback:
                success = callback(next_step)
            
            if success:
                # Update task state
                task.completed_steps.append(next_step.name)
                task.current_step = next_step.name
                task.current_phase = next_step.phase
                task.overall_progress = task.get_estimated_completion()
                task.last_action_time = datetime.now(timezone.utc)
                advanced_steps.append(next_step)
                self.advance_count += 1
            else:
                task.error_count += 1
                break
        
        return advanced_steps
    
    def _should_advance(self, step: AvailableStep) -> bool:
        """Determine if we should advance to this step based on strategy"""
        if self.strategy == AutoAdvanceStrategy.AGGRESSIVE:
            return step.success_probability > 0.6
        elif self.strategy == AutoAdvanceStrategy.BALANCED:
            return step.success_probability > 0.7
        elif self.strategy == AutoAdvanceStrategy.CONSERVATIVE:
            return step.success_probability > 0.85
        else:  # EXPLORATORY
            return True
    
    def suggest_advancement(
        self,
        task_id: str,
        task_category: str = "development",
    ) -> Optional[str]:
        """Get a suggestion for next step as plain text"""
        next_steps = self.get_next_steps(task_id, task_category, limit=1)
        if next_steps:
            step = next_steps[0]
            return f"📍 Next: {step.description.title()} (success: {step.success_probability:.0%})"
        return None
    
    def mark_step_complete(
        self,
        task_id: str,
        step_name: str,
        phase: Optional[TaskPhase] = None,
    ) -> bool:
        """Mark a step as completed"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if step_name not in task.completed_steps:
            task.completed_steps.append(step_name)
        
        if phase:
            task.current_phase = phase
        
        task.overall_progress = task.get_estimated_completion()
        return True
    
    def get_progress_summary(self, task_id: str) -> str:
        """Get human-readable progress summary"""
        if task_id not in self.tasks:
            return "Unknown task"
        
        task = self.tasks[task_id]
        completion = task.get_estimated_completion()
        phase_name = task.current_phase.name.title()
        
        return (
            f"Task: {task.goal}\n"
            f"Phase: {phase_name}\n"
            f"Progress: {completion:.0%} complete\n"
            f"Steps: {len(task.completed_steps)} completed"
        )
    
    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """Get detailed task summary"""
        if task_id not in self.tasks:
            return {}
        
        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "goal": task.goal,
            "phase": task.current_phase.value,
            "progress": task.get_estimated_completion(),
            "completed_steps": task.completed_steps,
            "current_step": task.current_step,
            "error_count": task.error_count,
        }


# Factory function
def create_advancement_engine(
    strategy: AutoAdvanceStrategy = AutoAdvanceStrategy.BALANCED,
) -> AutoAdvancementEngine:
    """Create an auto-advancement engine"""
    return AutoAdvancementEngine(strategy=strategy)
