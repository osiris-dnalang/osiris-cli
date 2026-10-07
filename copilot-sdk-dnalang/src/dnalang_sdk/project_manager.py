"""
11D-CRSM Agile Project Management Module

Implements quantum-aware agile project management with:
- Sprint management
- Backlog prioritization using consciousness metrics
- Velocity tracking
- Burndown with decoherence modeling
- Retrospectives with collective learning
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import uuid

from .swarm_organism import SwarmOrganism, OrganismRole, ConsciousnessMetrics
from .swarm_collective import SwarmCollective, SwarmTask


class StoryStatus(Enum):
    """User story status."""
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    DONE = "done"
    BLOCKED = "blocked"


class StoryPriority(Enum):
    """Story priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    NICE_TO_HAVE = 5


class SprintStatus(Enum):
    """Sprint status."""
    PLANNING = "planning"
    ACTIVE = "active"
    REVIEW = "review"
    RETROSPECTIVE = "retrospective"
    COMPLETED = "completed"


@dataclass
class UserStory:
    """A user story in the backlog."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    story_points: int = 0
    priority: StoryPriority = StoryPriority.MEDIUM
    status: StoryStatus = StoryStatus.BACKLOG
    assigned_to: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    
    # Quantum metrics
    consciousness_weight: float = 0.5  # Weight by Φ of creator
    coherence_score: float = 0.5  # Clarity of requirements
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def quantum_priority(self) -> float:
        """Calculate quantum-weighted priority."""
        base_priority = 6 - self.priority.value  # Invert so higher is better
        return base_priority * self.consciousness_weight * self.coherence_score
    
    @property
    def cycle_time(self) -> Optional[float]:
        """Calculate cycle time in hours."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() / 3600
        return None


@dataclass
class Sprint:
    """A development sprint."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    goal: str = ""
    status: SprintStatus = SprintStatus.PLANNING
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: int = 14
    
    # Stories
    stories: List[UserStory] = field(default_factory=list)
    committed_points: int = 0
    completed_points: int = 0
    
    # Metrics
    velocity: float = 0.0
    burndown_data: List[Dict] = field(default_factory=list)
    decoherence_rate: float = 0.1  # Rate at which scope/clarity decays
    
    @property
    def progress(self) -> float:
        """Calculate sprint progress."""
        if self.committed_points == 0:
            return 0.0
        return self.completed_points / self.committed_points
    
    @property
    def stories_by_status(self) -> Dict[StoryStatus, List[UserStory]]:
        """Group stories by status."""
        result = {status: [] for status in StoryStatus}
        for story in self.stories:
            result[story.status].append(story)
        return result
    
    @property
    def remaining_points(self) -> int:
        """Calculate remaining story points."""
        return sum(
            s.story_points for s in self.stories
            if s.status not in [StoryStatus.DONE]
        )
    
    def update_burndown(self) -> None:
        """Update burndown data."""
        self.burndown_data.append({
            "timestamp": datetime.now().isoformat(),
            "remaining_points": self.remaining_points,
            "completed_points": self.completed_points,
            "decoherence_factor": 1 - self.decoherence_rate,
        })


@dataclass
class RetroItem:
    """Retrospective item."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""  # went_well, to_improve, action_item
    text: str = ""
    votes: int = 0
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Retrospective:
    """Sprint retrospective."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sprint_id: str = ""
    items: List[RetroItem] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    collective_learning: Dict[str, float] = field(default_factory=dict)
    completed_at: Optional[datetime] = None
    
    @property
    def went_well(self) -> List[RetroItem]:
        return [i for i in self.items if i.category == "went_well"]
    
    @property
    def to_improve(self) -> List[RetroItem]:
        return [i for i in self.items if i.category == "to_improve"]


class QuantumProjectManager:
    """
    11D-CRSM Quantum-Aware Agile Project Manager.
    
    Features:
    - Consciousness-weighted prioritization
    - Quantum velocity prediction
    - Decoherence-aware burndown
    - Collective learning retrospectives
    - Swarm-based task assignment
    """
    
    def __init__(
        self,
        project_name: str,
        swarm: Optional[SwarmCollective] = None,
    ):
        self.id = str(uuid.uuid4())
        self.project_name = project_name
        self.swarm = swarm
        
        # Backlogs
        self.product_backlog: List[UserStory] = []
        
        # Sprints
        self.sprints: List[Sprint] = []
        self.current_sprint: Optional[Sprint] = None
        
        # Retrospectives
        self.retrospectives: List[Retrospective] = []
        
        # Team
        self.team_members: Dict[str, str] = {}  # organism_id -> role
        
        # Metrics history
        self.velocity_history: List[float] = []
        self.predictive_velocity: float = 0.0
        
        # Quantum metrics
        self.project_coherence: float = 0.5
        self.collective_consciousness: float = 0.3
        
        self.created_at = datetime.now()
    
    def add_story(
        self,
        title: str,
        description: str = "",
        story_points: int = 3,
        priority: StoryPriority = StoryPriority.MEDIUM,
        acceptance_criteria: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
    ) -> UserStory:
        """Add a story to the product backlog."""
        story = UserStory(
            title=title,
            description=description,
            story_points=story_points,
            priority=priority,
            acceptance_criteria=acceptance_criteria or [],
            labels=labels or [],
        )
        
        # Set consciousness weight based on project coherence
        story.consciousness_weight = self.collective_consciousness
        story.coherence_score = self.project_coherence
        
        self.product_backlog.append(story)
        self._reprioritize_backlog()
        
        return story
    
    def _reprioritize_backlog(self) -> None:
        """Reprioritize backlog using quantum metrics."""
        self.product_backlog.sort(key=lambda s: -s.quantum_priority)
    
    def create_sprint(
        self,
        name: str,
        goal: str,
        duration_days: int = 14,
    ) -> Sprint:
        """Create a new sprint."""
        sprint = Sprint(
            name=name,
            goal=goal,
            duration_days=duration_days,
        )
        self.sprints.append(sprint)
        return sprint
    
    def start_sprint(self, sprint: Optional[Sprint] = None) -> Sprint:
        """Start a sprint."""
        if sprint is None:
            sprint = self.sprints[-1] if self.sprints else None
        
        if sprint is None:
            raise ValueError("No sprint to start")
        
        sprint.status = SprintStatus.ACTIVE
        sprint.start_date = datetime.now()
        sprint.end_date = sprint.start_date + timedelta(days=sprint.duration_days)
        sprint.committed_points = sum(s.story_points for s in sprint.stories)
        
        self.current_sprint = sprint
        sprint.update_burndown()
        
        return sprint
    
    def add_story_to_sprint(self, story: UserStory, sprint: Optional[Sprint] = None) -> None:
        """Add a story to a sprint."""
        target_sprint = sprint or self.current_sprint
        if target_sprint is None:
            raise ValueError("No active sprint")
        
        if story in self.product_backlog:
            self.product_backlog.remove(story)
        
        story.status = StoryStatus.READY
        target_sprint.stories.append(story)
        target_sprint.committed_points += story.story_points
    
    async def assign_story(
        self,
        story: UserStory,
        organism_id: Optional[str] = None,
    ) -> bool:
        """Assign a story to an organism."""
        if self.swarm is None and organism_id is None:
            return False
        
        if organism_id:
            story.assigned_to = organism_id
        elif self.swarm:
            # Find best organism for this story
            best_organism = await self._find_best_assignee(story)
            if best_organism:
                story.assigned_to = best_organism.id
        
        story.status = StoryStatus.IN_PROGRESS
        story.started_at = datetime.now()
        return story.assigned_to is not None
    
    async def _find_best_assignee(self, story: UserStory) -> Optional[SwarmOrganism]:
        """Find the best organism to assign a story to."""
        if not self.swarm:
            return None
        
        best_score = 0
        best_organism = None
        
        for organism in self.swarm.organisms.values():
            if organism.current_task is not None:
                continue  # Skip busy organisms
            
            score = 0
            
            # Role match
            if "bug" in story.labels and organism.role == OrganismRole.TESTER:
                score += 2
            elif "feature" in story.labels and organism.role == OrganismRole.DEVELOPER:
                score += 2
            elif "review" in story.labels and organism.role == OrganismRole.REVIEWER:
                score += 2
            
            # Skill match
            for label in story.labels:
                if label in organism.skills:
                    score += organism.skills[label].level.value
            
            # Consciousness factor
            score *= organism.consciousness.lambda_coherence
            
            if score > best_score:
                best_score = score
                best_organism = organism
        
        return best_organism
    
    def complete_story(self, story: UserStory) -> None:
        """Mark a story as completed."""
        story.status = StoryStatus.DONE
        story.completed_at = datetime.now()
        
        if self.current_sprint and story in self.current_sprint.stories:
            self.current_sprint.completed_points += story.story_points
            self.current_sprint.update_burndown()
    
    def end_sprint(self, sprint: Optional[Sprint] = None) -> Sprint:
        """End a sprint."""
        target_sprint = sprint or self.current_sprint
        if target_sprint is None:
            raise ValueError("No active sprint")
        
        target_sprint.status = SprintStatus.REVIEW
        target_sprint.velocity = target_sprint.completed_points
        
        # Update velocity history
        self.velocity_history.append(target_sprint.velocity)
        self._update_predictive_velocity()
        
        # Move incomplete stories back to backlog
        for story in target_sprint.stories:
            if story.status != StoryStatus.DONE:
                story.status = StoryStatus.BACKLOG
                self.product_backlog.append(story)
        
        if self.current_sprint == target_sprint:
            self.current_sprint = None
        
        return target_sprint
    
    def _update_predictive_velocity(self) -> None:
        """Update predictive velocity using consciousness weighting."""
        if not self.velocity_history:
            self.predictive_velocity = 0
            return
        
        # Weighted average with consciousness factor
        weights = [self.collective_consciousness ** i for i in range(len(self.velocity_history))]
        weights = weights[::-1]  # Recent sprints weighted more
        
        total_weight = sum(weights)
        if total_weight > 0:
            self.predictive_velocity = sum(
                v * w for v, w in zip(self.velocity_history, weights)
            ) / total_weight
    
    async def run_retrospective(
        self,
        sprint: Optional[Sprint] = None,
    ) -> Retrospective:
        """Run a sprint retrospective."""
        target_sprint = sprint or (self.sprints[-1] if self.sprints else None)
        if target_sprint is None:
            raise ValueError("No sprint for retrospective")
        
        target_sprint.status = SprintStatus.RETROSPECTIVE
        
        retro = Retrospective(sprint_id=target_sprint.id)
        
        # Gather items from swarm organisms
        if self.swarm:
            for organism in self.swarm.organisms.values():
                # What went well
                retro.items.append(RetroItem(
                    category="went_well",
                    text=f"Good collaboration from {organism.name}",
                    created_by=organism.id,
                ))
                
                # To improve
                if organism.consciousness.gamma_decoherence > 0.3:
                    retro.items.append(RetroItem(
                        category="to_improve",
                        text=f"Reduce decoherence for {organism.name}",
                        created_by=organism.id,
                    ))
        
        # Generate action items
        retro.action_items = [
            "Improve sprint planning accuracy",
            "Reduce work-in-progress",
            "Increase pair programming",
        ]
        
        # Calculate collective learning
        retro.collective_learning = {
            "velocity_improvement": (
                target_sprint.velocity / self.predictive_velocity - 1
                if self.predictive_velocity > 0 else 0
            ),
            "decoherence_reduction": -target_sprint.decoherence_rate,
            "consciousness_growth": self.collective_consciousness,
        }
        
        retro.completed_at = datetime.now()
        target_sprint.status = SprintStatus.COMPLETED
        
        self.retrospectives.append(retro)
        
        # Update project consciousness based on learning
        self.collective_consciousness = min(1.0, self.collective_consciousness + 0.01)
        self.project_coherence = min(1.0, self.project_coherence + 0.01)
        
        return retro
    
    def get_burndown_chart_data(self, sprint: Optional[Sprint] = None) -> Dict:
        """Get burndown chart data."""
        target_sprint = sprint or self.current_sprint
        if target_sprint is None:
            return {"error": "No sprint"}
        
        return {
            "sprint_name": target_sprint.name,
            "committed_points": target_sprint.committed_points,
            "completed_points": target_sprint.completed_points,
            "remaining_points": target_sprint.remaining_points,
            "progress": target_sprint.progress,
            "data_points": target_sprint.burndown_data,
            "decoherence_factor": 1 - target_sprint.decoherence_rate,
        }
    
    def get_velocity_chart_data(self) -> Dict:
        """Get velocity chart data."""
        return {
            "history": self.velocity_history,
            "predictive": self.predictive_velocity,
            "sprint_names": [s.name for s in self.sprints if s.velocity > 0],
        }
    
    def get_kanban_board(self, sprint: Optional[Sprint] = None) -> Dict[str, List[Dict]]:
        """Get Kanban board view."""
        target_sprint = sprint or self.current_sprint
        stories = target_sprint.stories if target_sprint else self.product_backlog
        
        board = {status.value: [] for status in StoryStatus}
        
        for story in stories:
            board[story.status.value].append({
                "id": story.id,
                "title": story.title,
                "points": story.story_points,
                "priority": story.priority.name,
                "assigned_to": story.assigned_to,
                "quantum_priority": story.quantum_priority,
            })
        
        return board
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "backlog_size": len(self.product_backlog),
            "total_backlog_points": sum(s.story_points for s in self.product_backlog),
            "sprints_completed": len([s for s in self.sprints if s.status == SprintStatus.COMPLETED]),
            "current_sprint": self.current_sprint.name if self.current_sprint else None,
            "predictive_velocity": self.predictive_velocity,
            "velocity_history": self.velocity_history,
            "project_coherence": self.project_coherence,
            "collective_consciousness": self.collective_consciousness,
            "team_size": len(self.team_members),
        }
    
    def __repr__(self) -> str:
        return f"QuantumProjectManager({self.project_name}, sprints={len(self.sprints)}, Φ={self.collective_consciousness:.3f})"
