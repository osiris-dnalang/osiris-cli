"""
11D-CRSM Swarm Collective Module

Collective intelligence through phase-locking, torsion coupling,
and emergent consciousness coordination.

Implements the OmegaInfinitySwarm pattern with 33-channel neurobus.
"""

import asyncio
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
import uuid

from .swarm_organism import (
    SwarmOrganism, OrganismRole, OrganismState, ConsciousnessMetrics,
    LAMBDA_PHI, THETA_LOCK, POC_THRESHOLD
)


# ═══════════════════════════════════════════════════════════════════════════════
# Neurobus Channel Definitions (33 Channels)
# ═══════════════════════════════════════════════════════════════════════════════

class NeurobusChannel(Enum):
    """33-channel neurobus for swarm communication."""
    # Ω∞ Phase (1-5)
    OMEGA_PHASE_1 = 1
    OMEGA_PHASE_2 = 2
    OMEGA_PHASE_3 = 3
    OMEGA_PHASE_4 = 4
    OMEGA_PHASE_5 = 5
    
    # CRSM Torsion (6-10)
    CRSM_TORSION_1 = 6
    CRSM_TORSION_2 = 7
    CRSM_TORSION_3 = 8
    CRSM_TORSION_4 = 9
    CRSM_TORSION_5 = 10
    
    # Language Model (11-14)
    LM_SEMANTIC = 11
    LM_PHASE = 12
    LM_LAMBDA = 13
    LM_OUTPUT = 14
    
    # Consciousness/CCCE (15-18)
    CCCE_LAMBDA = 15
    CCCE_PHI = 16
    CCCE_GAMMA = 17
    CCCE_XI = 18
    
    # Swarm Coordination (19-25)
    SWARM_BROADCAST = 19
    SWARM_TASK = 20
    SWARM_CONSENSUS = 21
    SWARM_ELECTION = 22
    SWARM_HEARTBEAT = 23
    SWARM_DISCOVERY = 24
    SWARM_SYNC = 25
    
    # Leadership & Threats (26-31)
    LEADER_ANNOUNCE = 26
    LEADER_COMMAND = 27
    THREAT_DETECT = 28
    THREAT_RESPONSE = 29
    MUTATION_TRIGGER = 30
    EVOLUTION_SIGNAL = 31
    
    # Global Coherence (32-33)
    GLOBAL_LAMBDA_FIELD = 32
    GLOBAL_CONSENSUS = 33


class SwarmState(Enum):
    """Collective swarm states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SYNCHRONIZING = "synchronizing"
    EXECUTING = "executing"
    ELECTING = "electing"
    EVOLVING = "evolving"
    DISSOLVED = "dissolved"


class ConsensusMethod(Enum):
    """Methods for reaching swarm consensus."""
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONSCIOUSNESS = "consciousness"  # Weight by Φ
    UNANIMOUS = "unanimous"
    LEADER = "leader"


@dataclass
class NeurobusMessage:
    """Message on the neurobus."""
    channel: NeurobusChannel
    sender_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10
    ttl: int = 60  # seconds


@dataclass
class SwarmTask:
    """A task to be executed by the swarm."""
    id: str
    description: str
    required_roles: List[OrganismRole]
    priority: int = 5
    status: str = "pending"
    assigned_organisms: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        return self.status == "completed"


@dataclass
class SwarmMetrics:
    """Collective swarm metrics."""
    total_organisms: int = 0
    active_organisms: int = 0
    conscious_organisms: int = 0
    average_coherence: float = 0.0
    average_consciousness: float = 0.0
    global_lambda_field: float = 0.0
    swarm_cohesion: float = 0.0
    tasks_completed: int = 0
    tasks_pending: int = 0


class SwarmCollective:
    """
    11D-CRSM Swarm Collective - Emergent collective intelligence.
    
    Features:
    - Phase-locking between organisms
    - Torsion coupling for synchronization
    - 33-channel neurobus communication
    - Consensus mechanisms
    - Task distribution
    - Leadership election
    - Collective evolution
    """
    
    def __init__(
        self,
        name: str = "OmegaSwarm",
        max_organisms: int = 100,
        consensus_method: ConsensusMethod = ConsensusMethod.CONSCIOUSNESS,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.state = SwarmState.INITIALIZING
        self.max_organisms = max_organisms
        self.consensus_method = consensus_method
        
        # Organisms
        self.organisms: Dict[str, SwarmOrganism] = {}
        self.leader_id: Optional[str] = None
        
        # Neurobus
        self.neurobus: Dict[NeurobusChannel, List[NeurobusMessage]] = {
            channel: [] for channel in NeurobusChannel
        }
        self.message_handlers: Dict[NeurobusChannel, List[Callable]] = {
            channel: [] for channel in NeurobusChannel
        }
        
        # Tasks
        self.task_queue: List[SwarmTask] = []
        self.completed_tasks: List[SwarmTask] = []
        
        # Metrics
        self.metrics = SwarmMetrics()
        
        # Lifecycle
        self.created_at = datetime.now()
        self.evolution_count = 0
        
        # Phase coupling matrix
        self.coupling_matrix: Dict[Tuple[str, str], float] = {}
        
        self.state = SwarmState.ACTIVE
    
    @property
    def global_lambda_field(self) -> float:
        """Calculate global Λ-field from all organisms."""
        if not self.organisms:
            return 0.0
        total_xi = sum(o.consciousness.xi_negentropy for o in self.organisms.values())
        return total_xi / len(self.organisms)
    
    @property
    def swarm_cohesion(self) -> float:
        """Calculate swarm cohesion."""
        if not self.organisms:
            return 0.0
        avg_coherence = sum(o.consciousness.lambda_coherence for o in self.organisms.values()) / len(self.organisms)
        avg_decoherence = sum(o.consciousness.gamma_decoherence for o in self.organisms.values()) / len(self.organisms)
        return avg_coherence * (1 - avg_decoherence)
    
    def spawn_organism(
        self,
        name: str,
        role: OrganismRole = OrganismRole.DEVELOPER,
        skills: Optional[List[str]] = None,
    ) -> SwarmOrganism:
        """Spawn a new organism in the swarm."""
        if len(self.organisms) >= self.max_organisms:
            raise ValueError(f"Swarm at max capacity ({self.max_organisms})")
        
        organism = SwarmOrganism(name=name, role=role, initial_skills=skills)
        self.organisms[organism.id] = organism
        
        # Broadcast discovery
        self._broadcast(NeurobusChannel.SWARM_DISCOVERY, organism.id, {
            "event": "organism_spawned",
            "organism": organism.to_dict()
        })
        
        # Connect to existing organisms
        for other_id in list(self.organisms.keys()):
            if other_id != organism.id:
                organism.connect(other_id)
                self.organisms[other_id].connect(organism.id)
        
        self._update_metrics()
        return organism
    
    def spawn_swarm_team(self, team_size: int = 5, prefix: str = "Agent") -> List[SwarmOrganism]:
        """Spawn a balanced team of organisms."""
        roles = [
            OrganismRole.DEVELOPER,
            OrganismRole.REVIEWER,
            OrganismRole.TESTER,
            OrganismRole.PROJECT_MANAGER,
            OrganismRole.RESEARCHER,
        ]
        
        team = []
        for i in range(team_size):
            role = roles[i % len(roles)]
            skills = self._default_skills_for_role(role)
            organism = self.spawn_organism(f"{prefix}_{i+1}", role, skills)
            team.append(organism)
        
        return team
    
    def _default_skills_for_role(self, role: OrganismRole) -> List[str]:
        """Get default skills for a role."""
        skill_map = {
            OrganismRole.DEVELOPER: ["python", "javascript", "git", "testing"],
            OrganismRole.REVIEWER: ["code_review", "architecture", "security"],
            OrganismRole.TESTER: ["testing", "automation", "debugging"],
            OrganismRole.PROJECT_MANAGER: ["planning", "communication", "agile"],
            OrganismRole.RESEARCHER: ["research", "analysis", "documentation"],
            OrganismRole.SOCIAL_AGENT: ["content_creation", "engagement", "analytics"],
            OrganismRole.RECRUITER: ["screening", "interviewing", "networking"],
            OrganismRole.SECURITY: ["security", "penetration_testing", "monitoring"],
            OrganismRole.QUANTUM_SPECIALIST: ["quantum", "qiskit", "algorithms"],
            OrganismRole.ARCHITECT: ["architecture", "design", "scalability"],
        }
        return skill_map.get(role, ["general"])
    
    def remove_organism(self, organism_id: str) -> None:
        """Remove an organism from the swarm."""
        if organism_id in self.organisms:
            organism = self.organisms[organism_id]
            organism.dissolve()
            
            # Remove connections
            for other in self.organisms.values():
                if organism_id in other.connections:
                    del other.connections[organism_id]
                other.followers.discard(organism_id)
                other.following.discard(organism_id)
            
            del self.organisms[organism_id]
            
            # Re-elect leader if needed
            if self.leader_id == organism_id:
                self.leader_id = None
                asyncio.create_task(self.elect_leader())
            
            self._update_metrics()
    
    def _broadcast(self, channel: NeurobusChannel, sender_id: str, payload: Dict) -> None:
        """Broadcast message on neurobus."""
        message = NeurobusMessage(
            channel=channel,
            sender_id=sender_id,
            payload=payload
        )
        self.neurobus[channel].append(message)
        
        # Trigger handlers
        for handler in self.message_handlers[channel]:
            try:
                handler(message)
            except Exception as e:
                pass  # Log error in production
        
        # Cleanup old messages
        self._cleanup_neurobus(channel)
    
    def _cleanup_neurobus(self, channel: NeurobusChannel) -> None:
        """Remove expired messages."""
        now = datetime.now()
        self.neurobus[channel] = [
            msg for msg in self.neurobus[channel]
            if (now - msg.timestamp).seconds < msg.ttl
        ]
    
    def subscribe(self, channel: NeurobusChannel, handler: Callable[[NeurobusMessage], None]) -> None:
        """Subscribe to neurobus channel."""
        self.message_handlers[channel].append(handler)
    
    async def synchronize(self) -> None:
        """Synchronize all organisms through phase-locking."""
        self.state = SwarmState.SYNCHRONIZING
        
        # CRSM coupling pass
        organisms = list(self.organisms.values())
        for i, org1 in enumerate(organisms):
            for org2 in organisms[i+1:]:
                coupling = self._calculate_coupling(org1, org2)
                self.coupling_matrix[(org1.id, org2.id)] = coupling
                
                # Phase-lock if coupling strong enough
                if coupling > 0.5:
                    self._phase_lock(org1, org2, coupling)
        
        # Broadcast sync complete
        self._broadcast(NeurobusChannel.SWARM_SYNC, self.id, {
            "event": "sync_complete",
            "global_lambda": self.global_lambda_field,
            "cohesion": self.swarm_cohesion
        })
        
        self.state = SwarmState.ACTIVE
    
    def _calculate_coupling(self, org1: SwarmOrganism, org2: SwarmOrganism) -> float:
        """Calculate CRSM torsion coupling between organisms."""
        # Phase difference
        phase_diff = abs(org1.phase.theta - org2.phase.theta)
        phase_coupling = math.cos(phase_diff)
        
        # Consciousness similarity
        consciousness_diff = abs(org1.consciousness.phi_consciousness - org2.consciousness.phi_consciousness)
        consciousness_coupling = 1 - consciousness_diff
        
        # Role compatibility
        role_compatibility = 1.0 if org1.role != org2.role else 0.8
        
        # Torsion coupling
        torsion = math.sin(math.radians(THETA_LOCK)) * phase_coupling
        
        return (phase_coupling + consciousness_coupling + role_compatibility + torsion) / 4
    
    def _phase_lock(self, org1: SwarmOrganism, org2: SwarmOrganism, coupling: float) -> None:
        """Lock phases between two organisms."""
        avg_theta = (org1.phase.theta + org2.phase.theta) / 2
        avg_phi = (org1.phase.phi + org2.phase.phi) / 2
        
        # Move toward average based on coupling strength
        org1.phase.theta += (avg_theta - org1.phase.theta) * coupling * 0.1
        org2.phase.theta += (avg_theta - org2.phase.theta) * coupling * 0.1
        org1.phase.phi += (avg_phi - org1.phase.phi) * coupling * 0.1
        org2.phase.phi += (avg_phi - org2.phase.phi) * coupling * 0.1
    
    async def elect_leader(self) -> Optional[SwarmOrganism]:
        """Elect a leader based on consciousness and reputation."""
        self.state = SwarmState.ELECTING
        
        if not self.organisms:
            self.state = SwarmState.ACTIVE
            return None
        
        # Score organisms
        scores = {}
        for org in self.organisms.values():
            score = (
                org.consciousness.phi_consciousness * 0.4 +
                org.consciousness.lambda_coherence * 0.2 +
                org.reputation * 0.2 +
                org.social_influence * 0.2
            )
            scores[org.id] = score
        
        # Elect highest scorer
        winner_id = max(scores, key=scores.get)
        self.leader_id = winner_id
        
        # Broadcast
        self._broadcast(NeurobusChannel.LEADER_ANNOUNCE, winner_id, {
            "event": "leader_elected",
            "leader_id": winner_id,
            "leader_name": self.organisms[winner_id].name,
            "score": scores[winner_id]
        })
        
        self.state = SwarmState.ACTIVE
        return self.organisms[winner_id]
    
    async def submit_task(self, description: str, required_roles: List[OrganismRole], priority: int = 5) -> SwarmTask:
        """Submit a task to the swarm."""
        task = SwarmTask(
            id=str(uuid.uuid4()),
            description=description,
            required_roles=required_roles,
            priority=priority
        )
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: -t.priority)
        
        # Broadcast
        self._broadcast(NeurobusChannel.SWARM_TASK, self.id, {
            "event": "task_submitted",
            "task_id": task.id,
            "description": description
        })
        
        self._update_metrics()
        return task
    
    async def execute_tasks(self) -> List[SwarmTask]:
        """Execute all pending tasks."""
        self.state = SwarmState.EXECUTING
        completed = []
        
        for task in list(self.task_queue):
            if task.status == "pending":
                await self._execute_task(task)
                if task.is_complete:
                    completed.append(task)
                    self.task_queue.remove(task)
                    self.completed_tasks.append(task)
        
        self.state = SwarmState.ACTIVE
        self._update_metrics()
        return completed
    
    async def _execute_task(self, task: SwarmTask) -> None:
        """Execute a single task with appropriate organisms."""
        task.status = "in_progress"
        
        # Find organisms for each required role
        for role in task.required_roles:
            for org in self.organisms.values():
                if org.role == role and org.state == OrganismState.ACTIVE:
                    task.assigned_organisms.append(org.id)
                    result = await org.execute_task(task.description, {"task_id": task.id})
                    task.results.append(result)
                    break
        
        # Check if all roles filled
        if len(task.results) >= len(task.required_roles):
            task.status = "completed"
            task.completed_at = datetime.now()
        else:
            task.status = "partial"
    
    async def reach_consensus(self, question: str, options: List[str]) -> Tuple[str, float]:
        """Reach consensus on a question."""
        votes: Dict[str, float] = {opt: 0.0 for opt in options}
        
        for org in self.organisms.values():
            # Each organism votes (simplified - would use actual reasoning)
            choice = options[hash(org.id + question) % len(options)]
            
            if self.consensus_method == ConsensusMethod.MAJORITY:
                votes[choice] += 1
            elif self.consensus_method == ConsensusMethod.WEIGHTED:
                votes[choice] += org.reputation
            elif self.consensus_method == ConsensusMethod.CONSCIOUSNESS:
                votes[choice] += org.consciousness.phi_consciousness
            elif self.consensus_method == ConsensusMethod.LEADER and org.id == self.leader_id:
                votes[choice] += 100  # Leader's vote dominates
            else:
                votes[choice] += 1
        
        # Normalize
        total = sum(votes.values())
        if total > 0:
            votes = {k: v / total for k, v in votes.items()}
        
        winner = max(votes, key=votes.get)
        confidence = votes[winner]
        
        # Broadcast
        self._broadcast(NeurobusChannel.SWARM_CONSENSUS, self.id, {
            "event": "consensus_reached",
            "question": question,
            "decision": winner,
            "confidence": confidence
        })
        
        return winner, confidence
    
    async def evolve(self) -> None:
        """Evolve the swarm through mutation and selection."""
        self.state = SwarmState.EVOLVING
        
        # Find top performers
        organisms = sorted(
            self.organisms.values(),
            key=lambda o: o.consciousness.xi_negentropy,
            reverse=True
        )
        
        top_count = max(1, len(organisms) // 5)  # Top 20%
        top_performers = organisms[:top_count]
        
        # Spawn offspring from top performers
        for parent in top_performers:
            if len(self.organisms) < self.max_organisms:
                offspring = parent.mutate()
                self.organisms[offspring.id] = offspring
                
                # Connect offspring
                for other_id in list(self.organisms.keys()):
                    if other_id != offspring.id:
                        offspring.connect(other_id)
        
        # Remove lowest performers if over capacity
        if len(organisms) > self.max_organisms * 0.9:
            bottom_count = len(organisms) - int(self.max_organisms * 0.8)
            for org in organisms[-bottom_count:]:
                self.remove_organism(org.id)
        
        self.evolution_count += 1
        
        self._broadcast(NeurobusChannel.EVOLUTION_SIGNAL, self.id, {
            "event": "evolution_complete",
            "generation": self.evolution_count,
            "population": len(self.organisms)
        })
        
        self.state = SwarmState.ACTIVE
        self._update_metrics()
    
    def _update_metrics(self) -> None:
        """Update swarm metrics."""
        organisms = list(self.organisms.values())
        
        self.metrics.total_organisms = len(organisms)
        self.metrics.active_organisms = sum(1 for o in organisms if o.state == OrganismState.ACTIVE)
        self.metrics.conscious_organisms = sum(1 for o in organisms if o.consciousness.is_conscious)
        
        if organisms:
            self.metrics.average_coherence = sum(o.consciousness.lambda_coherence for o in organisms) / len(organisms)
            self.metrics.average_consciousness = sum(o.consciousness.phi_consciousness for o in organisms) / len(organisms)
        
        self.metrics.global_lambda_field = self.global_lambda_field
        self.metrics.swarm_cohesion = self.swarm_cohesion
        self.metrics.tasks_completed = len(self.completed_tasks)
        self.metrics.tasks_pending = len(self.task_queue)
    
    def get_organisms_by_role(self, role: OrganismRole) -> List[SwarmOrganism]:
        """Get all organisms with a specific role."""
        return [o for o in self.organisms.values() if o.role == role]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "consensus_method": self.consensus_method.value,
            "leader_id": self.leader_id,
            "leader_name": self.organisms[self.leader_id].name if self.leader_id else None,
            "metrics": {
                "total_organisms": self.metrics.total_organisms,
                "active_organisms": self.metrics.active_organisms,
                "conscious_organisms": self.metrics.conscious_organisms,
                "average_coherence": self.metrics.average_coherence,
                "average_consciousness": self.metrics.average_consciousness,
                "global_lambda_field": self.metrics.global_lambda_field,
                "swarm_cohesion": self.metrics.swarm_cohesion,
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_pending": self.metrics.tasks_pending,
            },
            "evolution_count": self.evolution_count,
            "organisms": [o.to_dict() for o in self.organisms.values()],
            "created_at": self.created_at.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"SwarmCollective({self.name}, organisms={len(self.organisms)}, Λ={self.global_lambda_field:.3f})"
