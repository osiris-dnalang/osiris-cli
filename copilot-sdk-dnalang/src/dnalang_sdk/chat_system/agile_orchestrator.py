#!/usr/bin/env python3
"""
AGILE ORCHESTRATOR — Project Management Integration
====================================================

Built-in agile workflow system:
- Automatic task decomposition (user goals → task breakdown)
- Sprint planning and management
- Progress tracking and burndown
- Backlog prioritization using consciousness metrics
- Team coordination with agent swarm
- Retrospectives and learnings
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status in workflow"""
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(Enum):
    """Task priority"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Task:
    """Individual task"""
    task_id: str
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.BACKLOG
    story_points: int = 3
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    subtasks: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)


@dataclass
class Sprint:
    """Sprint/iteration"""
    sprint_id: str
    name: str
    start_date: datetime
    end_date: datetime
    goal: str
    tasks: List[str] = field(default_factory=list)
    velocity: int = 0
    completed_points: int = 0
    is_active: bool = False
    
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days
    
    def progress(self) -> float:
        """Calculate sprint progress"""
        total = sum(1 for t in self.tasks)
        if total == 0:
            return 0.0
        completed = sum(1 for t in self.tasks if "done" in t.lower())
        return completed / total


@dataclass
class Backlog:
    """Product backlog"""
    items: List[Task] = field(default_factory=list)
    
    def add_task(self, task: Task) -> None:
        self.items.append(task)
    
    def prioritize(self) -> List[Task]:
        """Get prioritized backlog"""
        return sorted(self.items, key=lambda t: (t.priority.value, -t.created_at.timestamp()))


class AgilityMetrics:
    """Team agility metrics"""
    
    def __init__(self):
        self.velocity_history: List[int] = []
        self.cycle_time_history: List[float] = []
        self.completion_rate_history: List[float] = []
    
    def average_velocity(self, last_n: int = 5) -> float:
        """Average velocity over last N sprints"""
        recent = self.velocity_history[-last_n:]
        return sum(recent) / len(recent) if recent else 0
    
    def average_cycle_time(self) -> float:
        """Average time from start to done"""
        return sum(self.cycle_time_history) / len(self.cycle_time_history) \
               if self.cycle_time_history else 0


class AgileOrchestrator:
    """
    Orchestrates agile workflow including:
    - Task decomposition
    - Sprint management
    - Progress tracking
    - Team coordination
    """
    
    def __init__(self):
        self.backlog = Backlog()
        self.sprints: Dict[str, Sprint] = {}
        self.tasks: Dict[str, Task] = {}
        self.metrics = AgilityMetrics()
        self.current_sprint: Optional[str] = None
    
    def decompose_goal_into_tasks(
        self,
        goal: str,
        sub_goals: List[str],
    ) -> List[Task]:
        """
        Decompose a user goal into actionable tasks.
        """
        tasks = []
        
        for i, sub_goal in enumerate(sub_goals):
            task = Task(
                task_id=f"task-{len(self.tasks) + i}",
                title=sub_goal,
                description=f"Part of: {goal}",
                priority=Priority.HIGH if i == 0 else Priority.MEDIUM,
                story_points=3 + (i % 3),
            )
            
            self.tasks[task.task_id] = task
            self.backlog.add_task(task)
            tasks.append(task)
        
        return tasks
    
    def create_sprint(
        self,
        sprint_id: str,
        name: str,
        goal: str,
        duration_days: int = 14,
    ) -> Sprint:
        """
        Create a new sprint.
        """
        now = datetime.now(timezone.utc)
        sprint = Sprint(
            sprint_id=sprint_id,
            name=name,
            goal=goal,
            start_date=now,
            end_date=now + timedelta(days=duration_days),
        )
        
        self.sprints[sprint_id] = sprint
        return sprint
    
    def plan_sprint(
        self,
        sprint_id: str,
        available_velocity: int = 20,
    ) -> List[Task]:
        """
        Plan tasks for a sprint.
        """
        if sprint_id not in self.sprints:
            return []
        
        sprint = self.sprints[sprint_id]
        
        # Get prioritized backlog
        prioritized = self.backlog.prioritize()
        
        # Select tasks up to velocity
        selected_tasks = []
        total_points = 0
        
        for task in prioritized:
            if task.status == TaskStatus.BACKLOG:
                if total_points + task.story_points <= available_velocity:
                    task.status = TaskStatus.READY
                    selected_tasks.append(task)
                    sprint.tasks.append(task.task_id)
                    total_points += task.story_points
        
        sprint.velocity = available_velocity
        self.current_sprint = sprint_id
        sprint.is_active = True
        
        return selected_tasks
    
    def start_sprint(self, sprint_id: str) -> bool:
        """Start a sprint"""
        if sprint_id not in self.sprints:
            return False
        
        self.current_sprint = sprint_id
        self.sprints[sprint_id].is_active = True
        
        # Mark tasks as in progress
        for task_id in self.sprints[sprint_id].tasks:
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.IN_PROGRESS
                self.tasks[task_id].start_date = datetime.now(timezone.utc)
        
        return True
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as done"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.DONE
        
        # Update sprint progress
        if self.current_sprint and self.current_sprint in self.sprints:
            sprint = self.sprints[self.current_sprint]
            if task_id in sprint.tasks:
                sprint.completed_points += task.story_points
        
        return True
    
    def get_sprint_summary(self, sprint_id: Optional[str] = None) -> Dict[str, Any]:
        """Get sprint summary"""
        sprint_id = sprint_id or self.current_sprint
        if not sprint_id or sprint_id not in self.sprints:
            return {}
        
        sprint = self.sprints[sprint_id]
        total_points = sum(self.tasks[t].story_points for t in sprint.tasks
                          if t in self.tasks)
        
        return {
            "sprint_id": sprint_id,
            "name": sprint.name,
            "goal": sprint.goal,
            "duration_days": sprint.duration_days(),
            "total_points": total_points,
            "completed_points": sprint.completed_points,
            "progress": sprint.progress(),
            "velocity": sprint.velocity,
        }
    
    def get_backlog_summary(self) -> Dict[str, Any]:
        """Get backlog overview"""
        tasks_by_status = {}
        total_points = 0
        
        for task in self.tasks.values():
            status = task.status.value
            if status not in tasks_by_status:
                tasks_by_status[status] = 0
            tasks_by_status[status] += 1
            total_points += task.story_points
        
        return {
            "total_tasks": len(self.tasks),
            "total_points": total_points,
            "tasks_by_status": tasks_by_status,
            "in_progress": sum(1 for t in self.tasks.values() 
                              if t.status == TaskStatus.IN_PROGRESS),
            "blocked": sum(1 for t in self.tasks.values() 
                          if t.status == TaskStatus.BLOCKED),
        }
    
    def get_team_metrics(self) -> Dict[str, Any]:
        """Get team metrics"""
        return {
            "average_velocity": self.metrics.average_velocity(),
            "average_cycle_time_days": self.metrics.average_cycle_time(),
            "sprints_completed": len([s for s in self.sprints.values() 
                                     if not s.is_active]),
            "active_sprints": len([s for s in self.sprints.values() 
                                  if s.is_active]),
        }
    
    def generate_standup_report(self) -> str:
        """Generate daily standup report"""
        lines = []
        lines.append("📊 Daily Standup Report")
        lines.append("")
        
        # Current sprint
        if self.current_sprint:
            summary = self.get_sprint_summary(self.current_sprint)
            lines.append(f"Current Sprint: {summary.get('name', 'Unknown')}")
            lines.append(f"Progress: {summary.get('progress', 0):.0%} complete")
            lines.append("")
        
        # Tasks status
        in_progress = [t for t in self.tasks.values() 
                      if t.status == TaskStatus.IN_PROGRESS]
        if in_progress:
            lines.append("In Progress:")
            for task in in_progress[:5]:
                lines.append(f"  • {task.title}")
        
        # Blockers
        blocked = [t for t in self.tasks.values() 
                  if t.status == TaskStatus.BLOCKED]
        if blocked:
            lines.append("\nBlocked:")
            for task in blocked:
                lines.append(f"  ⚠ {task.title}")
                if task.blockers:
                    for blocker in task.blockers:
                        lines.append(f"    └ {blocker}")
        
        return "\n".join(lines)
    
    def get_high_priority_items(self, limit: int = 5) -> List[Task]:
        """Get top priority items"""
        backlog_ready = [t for t in self.backlog.prioritize()
                        if t.status in [TaskStatus.BACKLOG, TaskStatus.READY]]
        return backlog_ready[:limit]


# Factory function
def create_agile_orchestrator() -> AgileOrchestrator:
    """Create an agile orchestrator"""
    return AgileOrchestrator()
