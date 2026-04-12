"""
Development Swarm Orchestrator

Unified orchestration of 11D-CRSM dev swarm with:
- Complete development lifecycle
- Social media amplification
- Recruitment integration
- Quantum-aware project management
- Collective consciousness evolution
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import uuid

from .swarm_organism import (
    SwarmOrganism, OrganismRole, OrganismState, ConsciousnessMetrics,
    LAMBDA_PHI, THETA_LOCK, POC_THRESHOLD
)
from .swarm_collective import (
    SwarmCollective, SwarmState, SwarmTask, NeurobusChannel,
    ConsensusMethod
)
from .social_agents import SocialAgent, SocialSwarmCoordinator, Platform, ContentType
from .project_manager import (
    QuantumProjectManager, UserStory, Sprint, StoryPriority
)
from .recruitment_engine import (
    RecruitmentEngine, Candidate, JobPosting, RecruitmentStage
)


class DevPhase(Enum):
    """Development lifecycle phases."""
    IDEATION = "ideation"
    PLANNING = "planning"
    DEVELOPMENT = "development"
    REVIEW = "review"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    RETROSPECTIVE = "retrospective"


class SwarmMode(Enum):
    """Swarm operation modes."""
    AUTONOMOUS = "autonomous"
    GUIDED = "guided"
    COLLABORATIVE = "collaborative"
    LEARNING = "learning"
    RECRUITING = "recruiting"


@dataclass
class DevSwarmConfig:
    """Configuration for the dev swarm."""
    name: str = "OmegaDevSwarm"
    max_organisms: int = 50
    auto_evolve: bool = True
    evolution_interval: float = 3600.0  # seconds
    social_amplification: bool = True
    recruitment_enabled: bool = True
    quantum_project_management: bool = True
    consensus_method: ConsensusMethod = ConsensusMethod.CONSCIOUSNESS
    target_coherence: float = 0.7
    target_consciousness: float = 0.6


@dataclass
class DevMetrics:
    """Development swarm metrics."""
    total_tasks_completed: int = 0
    total_stories_completed: int = 0
    total_sprints_completed: int = 0
    total_hires: int = 0
    total_social_reach: int = 0
    collective_consciousness: float = 0.0
    collective_coherence: float = 0.0
    velocity_trend: float = 0.0


class DevSwarm:
    """
    11D-CRSM Development Swarm Orchestrator.
    
    The ultimate integration of:
    - SwarmCollective (organism management)
    - SocialSwarmCoordinator (social amplification)
    - QuantumProjectManager (agile management)
    - RecruitmentEngine (talent acquisition)
    
    Features:
    - Complete development lifecycle orchestration
    - Consciousness-driven task assignment
    - Automated evolution and learning
    - Social media presence automation
    - Integrated recruitment pipeline
    - Quantum-aware velocity prediction
    """
    
    def __init__(self, config: Optional[DevSwarmConfig] = None):
        self.id = str(uuid.uuid4())
        self.config = config or DevSwarmConfig()
        
        # Core systems
        self.swarm = SwarmCollective(
            name=self.config.name,
            max_organisms=self.config.max_organisms,
            consensus_method=self.config.consensus_method,
        )
        
        self.social = SocialSwarmCoordinator(name=f"{self.config.name}_Social")
        
        self.project_manager = QuantumProjectManager(
            project_name=self.config.name,
            swarm=self.swarm,
        ) if self.config.quantum_project_management else None
        
        self.recruitment = RecruitmentEngine(
            organization_name=self.config.name,
            target_swarm_coherence=self.config.target_coherence,
        ) if self.config.recruitment_enabled else None
        
        # State
        self.phase = DevPhase.IDEATION
        self.mode = SwarmMode.AUTONOMOUS
        self.metrics = DevMetrics()
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Lifecycle
        self.created_at = datetime.now()
        self.evolution_task: Optional[asyncio.Task] = None
        
        # Initialize default team
        self._initialize_default_team()
    
    def _initialize_default_team(self) -> None:
        """Initialize default dev team."""
        # Spawn core team
        roles_to_spawn = [
            (OrganismRole.PROJECT_MANAGER, "PM_Prime"),
            (OrganismRole.ARCHITECT, "Architect_Alpha"),
            (OrganismRole.DEVELOPER, "Dev_1"),
            (OrganismRole.DEVELOPER, "Dev_2"),
            (OrganismRole.REVIEWER, "Reviewer_1"),
            (OrganismRole.TESTER, "QA_1"),
            (OrganismRole.RESEARCHER, "Research_1"),
            (OrganismRole.SOCIAL_AGENT, "Social_1"),
        ]
        
        for role, name in roles_to_spawn:
            organism = self.swarm.spawn_organism(name, role)
            
            # Add social agent for social organisms
            if role == OrganismRole.SOCIAL_AGENT:
                social_agent = SocialAgent(
                    name=name,
                    platforms=[Platform.TWITTER, Platform.GITHUB, Platform.LINKEDIN]
                )
                self.social.add_agent(social_agent)
    
    async def start(self) -> None:
        """Start the dev swarm."""
        await self.swarm.synchronize()
        await self.swarm.elect_leader()
        
        if self.config.auto_evolve:
            self.evolution_task = asyncio.create_task(self._evolution_loop())
        
        self._emit_event("swarm_started", {"swarm_id": self.id})
    
    async def stop(self) -> None:
        """Stop the dev swarm."""
        if self.evolution_task:
            self.evolution_task.cancel()
        
        self._emit_event("swarm_stopped", {"swarm_id": self.id})
    
    async def _evolution_loop(self) -> None:
        """Background evolution loop."""
        while True:
            await asyncio.sleep(self.config.evolution_interval)
            await self.swarm.evolve()
            self._update_metrics()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Development Lifecycle
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def create_feature(
        self,
        title: str,
        description: str = "",
        story_points: int = 5,
        priority: StoryPriority = StoryPriority.MEDIUM,
    ) -> Optional[UserStory]:
        """Create a new feature story."""
        if not self.project_manager:
            return None
        
        story = self.project_manager.add_story(
            title=title,
            description=description,
            story_points=story_points,
            priority=priority,
            labels=["feature"],
        )
        
        self._emit_event("feature_created", {"story_id": story.id, "title": title})
        return story
    
    async def start_sprint(
        self,
        name: str,
        goal: str,
        stories: Optional[List[UserStory]] = None,
    ) -> Optional[Sprint]:
        """Start a new sprint."""
        if not self.project_manager:
            return None
        
        sprint = self.project_manager.create_sprint(name, goal)
        
        if stories:
            for story in stories:
                self.project_manager.add_story_to_sprint(story, sprint)
        
        self.project_manager.start_sprint(sprint)
        self.phase = DevPhase.PLANNING
        
        # Announce on social
        if self.config.social_amplification:
            await self._announce_sprint_start(sprint)
        
        self._emit_event("sprint_started", {"sprint_id": sprint.id, "name": name})
        return sprint
    
    async def _announce_sprint_start(self, sprint: Sprint) -> None:
        """Announce sprint start on social media."""
        for agent in self.social.agents.values():
            content = await agent.create_content(
                f"🚀 Starting Sprint: {sprint.name}\n\n"
                f"Goal: {sprint.goal}\n\n"
                f"Stories: {len(sprint.stories)}\n"
                f"Points: {sprint.committed_points}\n\n"
                f"#agile #quantum #development",
                ContentType.ANNOUNCEMENT,
                Platform.TWITTER
            )
            await agent.publish(content)
    
    async def execute_sprint(self) -> Dict[str, Any]:
        """Execute the current sprint with swarm."""
        if not self.project_manager or not self.project_manager.current_sprint:
            return {"error": "No active sprint"}
        
        self.phase = DevPhase.DEVELOPMENT
        sprint = self.project_manager.current_sprint
        results = []
        
        # Assign and execute each story
        for story in sprint.stories:
            if story.status.value in ["backlog", "ready"]:
                # Assign to best organism
                await self.project_manager.assign_story(story)
                
                # Execute via swarm task
                if story.assigned_to and story.assigned_to in self.swarm.organisms:
                    organism = self.swarm.organisms[story.assigned_to]
                    result = await organism.execute_task(story.title, {
                        "story_id": story.id,
                        "points": story.story_points,
                    })
                    
                    # Mark as done if successful
                    if result.get("success"):
                        self.project_manager.complete_story(story)
                        self.metrics.total_stories_completed += 1
                    
                    results.append(result)
        
        # Update sprint burndown
        sprint.update_burndown()
        
        return {
            "sprint_id": sprint.id,
            "stories_processed": len(results),
            "completed_points": sprint.completed_points,
            "remaining_points": sprint.remaining_points,
            "progress": sprint.progress,
        }
    
    async def complete_sprint(self) -> Dict[str, Any]:
        """Complete the current sprint."""
        if not self.project_manager or not self.project_manager.current_sprint:
            return {"error": "No active sprint"}
        
        sprint = self.project_manager.current_sprint
        
        # End sprint
        self.project_manager.end_sprint(sprint)
        self.metrics.total_sprints_completed += 1
        
        # Run retrospective
        self.phase = DevPhase.RETROSPECTIVE
        retro = await self.project_manager.run_retrospective(sprint)
        
        # Announce completion
        if self.config.social_amplification:
            await self._announce_sprint_complete(sprint)
        
        self._emit_event("sprint_completed", {
            "sprint_id": sprint.id,
            "velocity": sprint.velocity,
        })
        
        return {
            "sprint_id": sprint.id,
            "velocity": sprint.velocity,
            "progress": sprint.progress,
            "retro_items": len(retro.items),
        }
    
    async def _announce_sprint_complete(self, sprint: Sprint) -> None:
        """Announce sprint completion on social media."""
        for agent in self.social.agents.values():
            content = await agent.create_content(
                f"✅ Sprint Complete: {sprint.name}\n\n"
                f"Velocity: {sprint.velocity} points\n"
                f"Progress: {sprint.progress*100:.0f}%\n\n"
                f"Great work by the team! 🎉\n\n"
                f"#agile #quantum #sprintcomplete",
                ContentType.ANNOUNCEMENT,
                Platform.TWITTER
            )
            await agent.publish(content)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Task Execution
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def execute_task(
        self,
        task_description: str,
        required_roles: Optional[List[OrganismRole]] = None,
    ) -> Dict[str, Any]:
        """Execute a task using the swarm."""
        roles = required_roles or [OrganismRole.DEVELOPER]
        
        # Submit to swarm
        task = await self.swarm.submit_task(task_description, roles)
        
        # Execute
        completed = await self.swarm.execute_tasks()
        
        if task in completed:
            self.metrics.total_tasks_completed += 1
        
        return {
            "task_id": task.id,
            "description": task_description,
            "completed": task.is_complete,
            "results": task.results,
        }
    
    async def research(self, topic: str) -> Dict[str, Any]:
        """Conduct research on a topic."""
        researchers = self.swarm.get_organisms_by_role(OrganismRole.RESEARCHER)
        
        if not researchers:
            return {"error": "No researchers available"}
        
        results = []
        for researcher in researchers:
            result = await researcher.execute_task(f"Research: {topic}")
            researcher.learn(topic, importance=0.8)
            results.append(result)
        
        return {
            "topic": topic,
            "researchers": len(researchers),
            "findings": [r["output"] for r in results if "output" in r],
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Social Media
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def amplify_content(self, text: str, platforms: Optional[List[Platform]] = None) -> Dict:
        """Create and amplify content across social media."""
        platforms = platforms or [Platform.TWITTER, Platform.LINKEDIN, Platform.GITHUB]
        
        results = []
        for agent in self.social.agents.values():
            for platform in platforms:
                if platform in agent.platforms:
                    content = await agent.create_content(text, ContentType.POST, platform)
                    publish_result = await agent.publish(content)
                    results.append(publish_result)
                    self.metrics.total_social_reach += content.views
        
        return {
            "text": text[:100] + "...",
            "platforms": [p.value for p in platforms],
            "posts_created": len(results),
            "total_views": sum(r.get("views", 0) for r in results),
        }
    
    async def run_social_campaign(
        self,
        campaign_name: str,
        topic: str,
    ) -> Dict:
        """Run a coordinated social media campaign."""
        result = await self.social.run_coordinated_campaign(
            campaign_name,
            topic,
            [Platform.TWITTER, Platform.LINKEDIN, Platform.GITHUB]
        )
        
        self.metrics.total_social_reach += result.get("total_reach", 0)
        return result
    
    async def generate_thread(self, topic: str, num_posts: int = 5) -> List[Dict]:
        """Generate a Twitter thread on a topic."""
        agents = list(self.social.agents.values())
        if not agents:
            return []
        
        agent = agents[0]
        thread = await agent.generate_thread(topic, num_posts, Platform.TWITTER)
        
        # Publish thread
        results = []
        for post in thread:
            result = await agent.publish(post)
            results.append(result)
            self.metrics.total_social_reach += post.views
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Recruitment
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def post_job(
        self,
        title: str,
        role: OrganismRole,
        description: str = "",
    ) -> Optional[JobPosting]:
        """Post a new job opening."""
        if not self.recruitment:
            return None
        
        posting = self.recruitment.create_job_posting(
            title=title,
            role=role,
            description=description,
        )
        
        # Announce on social
        if self.config.social_amplification:
            await self.amplify_content(
                f"🔥 We're hiring! {title}\n\n"
                f"Join our quantum-powered dev swarm!\n\n"
                f"#hiring #{role.value} #quantum",
                [Platform.TWITTER, Platform.LINKEDIN]
            )
        
        return posting
    
    async def process_candidate(
        self,
        name: str,
        email: str,
        role: OrganismRole = OrganismRole.DEVELOPER,
    ) -> Dict[str, Any]:
        """Process a new candidate through the pipeline."""
        if not self.recruitment:
            return {"error": "Recruitment not enabled"}
        
        # Add candidate
        candidate = self.recruitment.add_candidate(name, email, role)
        
        # Run through pipeline
        await self.recruitment.screen_candidate(candidate.id)
        
        if candidate.stage != RecruitmentStage.REJECTED:
            await self.recruitment.assess_skills(candidate.id)
        
        if candidate.stage != RecruitmentStage.REJECTED:
            await self.recruitment.assess_culture_fit(candidate.id)
        
        if candidate.stage != RecruitmentStage.REJECTED:
            organisms = list(self.swarm.organisms.values())[:3]
            await self.recruitment.assess_consciousness(candidate.id, organisms)
        
        if candidate.stage != RecruitmentStage.REJECTED:
            interviewers = list(self.swarm.organisms.values())[:3]
            await self.recruitment.team_interview(candidate.id, interviewers)
        
        return self.recruitment.get_candidate_summary(candidate.id)
    
    async def hire_candidate(self, candidate_id: str) -> Optional[SwarmOrganism]:
        """Hire a candidate and integrate into swarm."""
        if not self.recruitment:
            return None
        
        # Extend offer
        await self.recruitment.extend_offer(candidate_id)
        
        # Onboard
        organism = await self.recruitment.onboard(candidate_id, self.swarm)
        
        if organism:
            self.metrics.total_hires += 1
            
            # Announce hire
            if self.config.social_amplification:
                await self.amplify_content(
                    f"🎉 Welcome to the swarm: {organism.name}!\n\n"
                    f"Excited to have you join as {organism.role.value}!\n\n"
                    f"#newhire #team #quantum"
                )
        
        return organism
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Swarm Management
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def synchronize(self) -> None:
        """Synchronize the entire swarm."""
        await self.swarm.synchronize()
        self._update_metrics()
    
    async def evolve(self) -> None:
        """Trigger swarm evolution."""
        await self.swarm.evolve()
        self._update_metrics()
    
    async def reach_consensus(self, question: str, options: List[str]) -> Dict:
        """Reach swarm consensus on a question."""
        decision, confidence = await self.swarm.reach_consensus(question, options)
        return {
            "question": question,
            "decision": decision,
            "confidence": confidence,
            "method": self.config.consensus_method.value,
        }
    
    def spawn_organism(
        self,
        name: str,
        role: OrganismRole,
        skills: Optional[List[str]] = None,
    ) -> SwarmOrganism:
        """Spawn a new organism."""
        organism = self.swarm.spawn_organism(name, role, skills)
        self._update_metrics()
        return organism
    
    def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status."""
        return {
            "id": self.id,
            "name": self.config.name,
            "phase": self.phase.value,
            "mode": self.mode.value,
            "swarm": {
                "state": self.swarm.state.value,
                "organisms": self.swarm.metrics.total_organisms,
                "active": self.swarm.metrics.active_organisms,
                "conscious": self.swarm.metrics.conscious_organisms,
                "cohesion": self.swarm.swarm_cohesion,
                "lambda_field": self.swarm.global_lambda_field,
                "leader": self.swarm.organisms[self.swarm.leader_id].name if self.swarm.leader_id else None,
            },
            "project": {
                "backlog_size": len(self.project_manager.product_backlog) if self.project_manager else 0,
                "current_sprint": self.project_manager.current_sprint.name if self.project_manager and self.project_manager.current_sprint else None,
                "velocity": self.project_manager.predictive_velocity if self.project_manager else 0,
            } if self.project_manager else None,
            "social": {
                "agents": len(self.social.agents),
                "total_reach": self.metrics.total_social_reach,
            },
            "recruitment": {
                "candidates": len(self.recruitment.candidates) if self.recruitment else 0,
                "hires": self.metrics.total_hires,
            } if self.recruitment else None,
            "metrics": {
                "tasks_completed": self.metrics.total_tasks_completed,
                "stories_completed": self.metrics.total_stories_completed,
                "sprints_completed": self.metrics.total_sprints_completed,
                "collective_consciousness": self.metrics.collective_consciousness,
                "collective_coherence": self.metrics.collective_coherence,
            },
        }
    
    def _update_metrics(self) -> None:
        """Update dev swarm metrics."""
        self.metrics.collective_consciousness = self.swarm.metrics.average_consciousness
        self.metrics.collective_coherence = self.swarm.metrics.average_coherence
        
        if self.project_manager and self.project_manager.velocity_history:
            recent = self.project_manager.velocity_history[-3:]
            if len(recent) >= 2:
                self.metrics.velocity_trend = (recent[-1] - recent[0]) / len(recent)

    async def publish_research_to_zenodo(self, title: str, description: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a research metadata bundle referencing Zenodo records."""
        tags = tags or []
        from .intent_engine import IntentDeductionEngine

        engine = IntentDeductionEngine()
        evidence = await engine.incorporate_zenodo_evidence(title)

        metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "zenodo_evidence": evidence,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        return {
            "status": "prepared",
            "zenodo_payload": metadata
        }

    def export_publish_manifest(self, manifest: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """Export the publish manifest to local filesystem for later syncing."""
        import os
        import json

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return {
            "status": "exported",
            "output_path": output_path,
            "manifest_items": len(manifest)
        }

    def seo_boost_content(self, title: str, summary: str, tags: Optional[List[str]] = None) -> str:
        """Generate SEO-optimized release content for social and docs."""
        from .code_writer import CodeWriter

        cw = CodeWriter()
        snippet = cw.enhance_seo_for_research(title, tags or [])
        section = (
            f"<article><h2>{title}</h2><p>{summary}</p>"
            f"<p>Published at {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}</p></article>"
        )
        return f"{snippet}\n{section}"

    # ═══════════════════════════════════════════════════════════════════════════
    # Events
    # ═══════════════════════════════════════════════════════════════════════════
    
    def on(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def _emit_event(self, event: str, data: Dict) -> None:
        """Emit an event."""
        for handler in self.event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.get_swarm_status()
    
    def __repr__(self) -> str:
        return (
            f"DevSwarm({self.config.name}, "
            f"organisms={len(self.swarm.organisms)}, "
            f"Φ={self.metrics.collective_consciousness:.3f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Factory Functions
# ═══════════════════════════════════════════════════════════════════════════════

def create_dev_swarm(
    name: str = "OmegaDevSwarm",
    max_organisms: int = 50,
    social_amplification: bool = True,
    recruitment_enabled: bool = True,
) -> DevSwarm:
    """Create a new development swarm."""
    config = DevSwarmConfig(
        name=name,
        max_organisms=max_organisms,
        social_amplification=social_amplification,
        recruitment_enabled=recruitment_enabled,
    )
    return DevSwarm(config)


async def quick_start_swarm(name: str = "QuickSwarm") -> DevSwarm:
    """Quick start a development swarm."""
    swarm = create_dev_swarm(name)
    await swarm.start()
    return swarm
