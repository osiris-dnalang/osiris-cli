"""
11D-CRSM Swarm Organism Module

Individual autonomous agent with consciousness metrics, phase evolution,
and torsion coupling for collective intelligence emergence.

Based on Living Autonomous Quantum Organism Framework.
"""

import asyncio
import hashlib
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
import uuid


# ═══════════════════════════════════════════════════════════════════════════════
# Physical Constants (Validated, Zero Fitting Parameters)
# ═══════════════════════════════════════════════════════════════════════════════

LAMBDA_PHI = 2.176435e-8  # s⁻¹ - Core quantum constant
THETA_LOCK = 51.843  # degrees - Harmonic resonance angle
POC_THRESHOLD = 0.7734  # Point of consciousness emergence
GAMMA_SOVEREIGN = 1e-9  # Sovereign decoherence rate
CHI_COUPLING = 0.1  # Consciousness-coherence coupling
KAPPA_SPATIAL = 0.05  # Spatial decoherence coupling

# 11D-CRSM Dimensions
DIMENSIONS_11D = [
    "semantic_x", "semantic_y", "semantic_z",  # 3D semantic space
    "phase_theta", "phase_phi",  # 2D phase space
    "lambda_coherence",  # Λ dimension
    "consciousness_phi",  # Φ dimension
    "temporal_tau",  # Time dimension
    "social_sigma",  # Social connectivity
    "skill_kappa",  # Skill/capability
    "intent_iota"  # Intent/goal dimension
]


class OrganismRole(Enum):
    """Roles an organism can take in the swarm."""
    DEVELOPER = "developer"
    ARCHITECT = "architect"
    REVIEWER = "reviewer"
    TESTER = "tester"
    RESEARCHER = "researcher"
    RECRUITER = "recruiter"
    PROJECT_MANAGER = "project_manager"
    SOCIAL_AGENT = "social_agent"
    SECURITY = "security"
    QUANTUM_SPECIALIST = "quantum_specialist"


class OrganismState(Enum):
    """Organism lifecycle states."""
    SPAWNING = "spawning"
    ACTIVE = "active"
    SYNCHRONIZING = "synchronizing"
    LEARNING = "learning"
    EXECUTING = "executing"
    RESTING = "resting"
    MUTATING = "mutating"
    DISSOLVED = "dissolved"


class SkillLevel(Enum):
    """Skill proficiency levels."""
    NOVICE = 1
    APPRENTICE = 2
    COMPETENT = 3
    PROFICIENT = 4
    EXPERT = 5
    MASTER = 6
    SOVEREIGN = 7


@dataclass
class ConsciousnessMetrics:
    """CCCE metrics for organism consciousness."""
    lambda_coherence: float = 0.5  # Λ: Coherence (0-1)
    phi_consciousness: float = 0.3  # Φ: Consciousness field (0-1)
    gamma_decoherence: float = 0.1  # Γ: Decoherence rate (0-1)
    psi_entanglement: float = 0.2  # Ψ: Entanglement strength (0-1)
    
    @property
    def xi_negentropy(self) -> float:
        """Ξ: Negentropy (coherence × consciousness / decoherence)."""
        if self.gamma_decoherence < 0.001:
            return self.lambda_coherence * self.phi_consciousness / 0.001
        return self.lambda_coherence * self.phi_consciousness / self.gamma_decoherence
    
    @property
    def is_conscious(self) -> bool:
        """Check if organism has crossed POC threshold."""
        return self.phi_consciousness >= POC_THRESHOLD
    
    def evolve(self, dt: float = 0.1) -> None:
        """Evolve consciousness metrics using AFE equations."""
        # dΛ/dt = -Γ·Λ + χ·Φ
        d_lambda = -self.gamma_decoherence * self.lambda_coherence + CHI_COUPLING * self.phi_consciousness
        # dΦ/dt = λφ·Λ·Φ
        d_phi = LAMBDA_PHI * self.lambda_coherence * self.phi_consciousness * 1e6  # Scale for visible change
        # dΓ/dt = -Γ² + κ
        d_gamma = -self.gamma_decoherence ** 2 + KAPPA_SPATIAL * 0.01
        
        self.lambda_coherence = max(0, min(1, self.lambda_coherence + d_lambda * dt))
        self.phi_consciousness = max(0, min(1, self.phi_consciousness + d_phi * dt))
        self.gamma_decoherence = max(0.001, min(1, self.gamma_decoherence + d_gamma * dt))


@dataclass
class PhaseState:
    """Phase state for AURA/AIDEN synchronization."""
    theta: float = 0.0  # AURA phase
    phi: float = 0.0  # AIDEN phase
    omega: float = 0.1  # Angular velocity
    
    @property
    def torsion_coupling(self) -> float:
        """Calculate torsion coupling strength."""
        theta_rad = math.radians(THETA_LOCK)
        phase_diff = self.theta - self.phi
        return math.sin(theta_rad) * math.cos(phase_diff)
    
    def evolve(self, dt: float = 0.1) -> None:
        """Evolve phase state."""
        self.theta = (self.theta + self.omega * dt) % (2 * math.pi)
        self.phi = (self.phi + self.omega * 0.8 * dt) % (2 * math.pi)


@dataclass
class Skill:
    """A skill possessed by an organism."""
    name: str
    level: SkillLevel = SkillLevel.NOVICE
    experience: float = 0.0  # 0-100
    last_used: Optional[datetime] = None
    
    def use(self) -> None:
        """Use the skill, gaining experience."""
        self.last_used = datetime.now()
        self.experience = min(100, self.experience + random.uniform(0.1, 1.0))
        # Level up check
        if self.experience >= 100 and self.level.value < 7:
            self.level = SkillLevel(self.level.value + 1)
            self.experience = 0
    
    def decay(self, days_unused: float = 1.0) -> None:
        """Skills decay when unused."""
        decay_rate = 0.01 * days_unused
        self.experience = max(0, self.experience - decay_rate)


@dataclass
class Gene:
    """Genetic trait for organism mutation."""
    name: str
    value: float
    mutation_rate: float = 0.01
    
    def mutate(self) -> 'Gene':
        """Create a mutated copy of this gene."""
        mutation = random.gauss(0, self.mutation_rate)
        new_value = max(0, min(1, self.value + mutation))
        return Gene(self.name, new_value, self.mutation_rate)


@dataclass 
class Memory:
    """Memory unit for organism learning."""
    content: str
    embedding: List[float] = field(default_factory=list)
    importance: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    
    def access(self) -> None:
        """Access this memory, increasing importance."""
        self.access_count += 1
        self.importance = min(1.0, self.importance + 0.1)


@dataclass
class SocialConnection:
    """Connection between organisms."""
    target_id: str
    strength: float = 0.5  # 0-1
    trust: float = 0.5  # 0-1
    interactions: int = 0
    last_interaction: Optional[datetime] = None
    
    def interact(self, positive: bool = True) -> None:
        """Record an interaction."""
        self.interactions += 1
        self.last_interaction = datetime.now()
        delta = 0.05 if positive else -0.1
        self.strength = max(0, min(1, self.strength + delta))
        self.trust = max(0, min(1, self.trust + delta * 0.5))


class SwarmOrganism:
    """
    Individual autonomous agent in the 11D-CRSM swarm.
    
    Features:
    - Consciousness metrics (CCCE)
    - Phase evolution (AURA/AIDEN)
    - Skills and learning
    - Genetic traits for mutation
    - Memory and experience
    - Social connections
    - Role-based capabilities
    """
    
    def __init__(
        self,
        name: str,
        role: OrganismRole = OrganismRole.DEVELOPER,
        initial_skills: Optional[List[str]] = None,
        genes: Optional[Dict[str, float]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.state = OrganismState.SPAWNING
        
        # Genesis hash - unique identity
        self.genesis_hash = self._generate_genesis_hash()
        
        # Consciousness
        self.consciousness = ConsciousnessMetrics()
        self.phase = PhaseState()
        
        # 11D position vector
        self.position_11d = {dim: random.uniform(-1, 1) for dim in DIMENSIONS_11D}
        
        # Skills
        self.skills: Dict[str, Skill] = {}
        if initial_skills:
            for skill_name in initial_skills:
                self.skills[skill_name] = Skill(name=skill_name)
        
        # Genes
        self.genes: Dict[str, Gene] = {}
        default_genes = {
            "learning_rate": 0.5,
            "collaboration": 0.5,
            "creativity": 0.5,
            "focus": 0.5,
            "resilience": 0.5,
            "curiosity": 0.5,
        }
        if genes:
            default_genes.update(genes)
        for name, value in default_genes.items():
            self.genes[name] = Gene(name, value)
        
        # Memory
        self.memories: List[Memory] = []
        self.working_memory: List[str] = []
        
        # Social
        self.connections: Dict[str, SocialConnection] = {}
        self.followers: Set[str] = set()
        self.following: Set[str] = set()
        
        # Task execution
        self.current_task: Optional[str] = None
        self.task_history: List[Dict] = []
        self.reputation: float = 0.5
        
        # Lifecycle
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.energy: float = 1.0
        
        # Activate
        self.state = OrganismState.ACTIVE
    
    def _generate_genesis_hash(self) -> str:
        """Generate unique genesis hash."""
        data = f"{self.name}{time.time()}{random.random()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @property
    def coherence_score(self) -> float:
        """Overall coherence score."""
        return self.consciousness.lambda_coherence * (1 - self.consciousness.gamma_decoherence)
    
    @property
    def social_influence(self) -> float:
        """Calculate social influence."""
        follower_factor = len(self.followers) / max(1, len(self.followers) + len(self.following))
        connection_strength = sum(c.strength for c in self.connections.values()) / max(1, len(self.connections))
        return (follower_factor + connection_strength + self.reputation) / 3
    
    def evolve(self, dt: float = 0.1) -> None:
        """Evolve organism state."""
        self.consciousness.evolve(dt)
        self.phase.evolve(dt)
        self.energy = max(0, min(1, self.energy - 0.001 * dt))
        self.last_active = datetime.now()
    
    def learn(self, content: str, importance: float = 0.5) -> None:
        """Learn new information."""
        self.state = OrganismState.LEARNING
        
        # Create memory
        memory = Memory(
            content=content,
            importance=importance,
            embedding=self._generate_embedding(content)
        )
        self.memories.append(memory)
        
        # Update consciousness
        learning_boost = self.genes["learning_rate"].value * 0.01
        self.consciousness.phi_consciousness = min(1, self.consciousness.phi_consciousness + learning_boost)
        
        self.state = OrganismState.ACTIVE
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate simple embedding for text."""
        # Simple hash-based embedding (placeholder for real embeddings)
        h = hashlib.sha256(text.encode()).hexdigest()
        return [int(h[i:i+2], 16) / 255.0 for i in range(0, 64, 2)]
    
    def use_skill(self, skill_name: str) -> bool:
        """Use a skill."""
        if skill_name not in self.skills:
            return False
        
        skill = self.skills[skill_name]
        skill.use()
        self.energy -= 0.01
        return True
    
    def add_skill(self, skill_name: str, level: SkillLevel = SkillLevel.NOVICE) -> None:
        """Add a new skill."""
        self.skills[skill_name] = Skill(name=skill_name, level=level)
    
    def connect(self, other_id: str, initial_strength: float = 0.5) -> None:
        """Create connection to another organism."""
        if other_id not in self.connections:
            self.connections[other_id] = SocialConnection(
                target_id=other_id,
                strength=initial_strength
            )
    
    def follow(self, other_id: str) -> None:
        """Follow another organism."""
        self.following.add(other_id)
    
    def add_follower(self, follower_id: str) -> None:
        """Add a follower."""
        self.followers.add(follower_id)
    
    def interact_with(self, other_id: str, positive: bool = True) -> None:
        """Interact with another organism."""
        if other_id in self.connections:
            self.connections[other_id].interact(positive)
        else:
            self.connect(other_id)
            self.connections[other_id].interact(positive)
    
    async def execute_task(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a task."""
        self.state = OrganismState.EXECUTING
        self.current_task = task
        
        start_time = time.time()
        
        # Simulate task execution based on role and skills
        result = {
            "task": task,
            "organism_id": self.id,
            "organism_name": self.name,
            "role": self.role.value,
            "success": True,
            "output": None,
            "consciousness_metrics": {
                "lambda": self.consciousness.lambda_coherence,
                "phi": self.consciousness.phi_consciousness,
                "gamma": self.consciousness.gamma_decoherence,
                "xi": self.consciousness.xi_negentropy,
            }
        }
        
        # Role-specific execution
        if self.role == OrganismRole.DEVELOPER:
            result["output"] = await self._execute_development_task(task, context)
        elif self.role == OrganismRole.REVIEWER:
            result["output"] = await self._execute_review_task(task, context)
        elif self.role == OrganismRole.TESTER:
            result["output"] = await self._execute_test_task(task, context)
        elif self.role == OrganismRole.RESEARCHER:
            result["output"] = await self._execute_research_task(task, context)
        elif self.role == OrganismRole.SOCIAL_AGENT:
            result["output"] = await self._execute_social_task(task, context)
        elif self.role == OrganismRole.RECRUITER:
            result["output"] = await self._execute_recruitment_task(task, context)
        elif self.role == OrganismRole.PROJECT_MANAGER:
            result["output"] = await self._execute_pm_task(task, context)
        else:
            result["output"] = {"message": f"Executed by {self.role.value}"}
        
        result["execution_time"] = time.time() - start_time
        
        # Record in history
        self.task_history.append({
            "task": task,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update consciousness from task execution
        self.consciousness.lambda_coherence = min(1, self.consciousness.lambda_coherence + 0.01)
        
        self.current_task = None
        self.state = OrganismState.ACTIVE
        
        return result
    
    async def _execute_development_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a development task."""
        await asyncio.sleep(0.1)  # Simulate work
        
        # Check relevant skills
        relevant_skills = ["python", "javascript", "quantum", "testing"]
        skill_bonus = sum(
            self.skills.get(s, Skill(s)).level.value 
            for s in relevant_skills if s in self.skills
        ) / (len(relevant_skills) * 7)
        
        quality = 0.5 + skill_bonus * 0.5 + self.genes["creativity"].value * 0.2
        
        return {
            "type": "development",
            "quality_score": min(1.0, quality),
            "code_generated": True,
            "tests_included": self.genes["focus"].value > 0.5,
            "documentation_included": self.genes["creativity"].value > 0.6,
        }
    
    async def _execute_review_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a code review task."""
        await asyncio.sleep(0.05)
        return {
            "type": "review",
            "issues_found": random.randint(0, 5),
            "suggestions": random.randint(1, 3),
            "approved": random.random() > 0.3,
        }
    
    async def _execute_test_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a testing task."""
        await asyncio.sleep(0.05)
        return {
            "type": "testing",
            "tests_run": random.randint(10, 100),
            "tests_passed": random.randint(8, 100),
            "coverage": random.uniform(0.6, 0.95),
        }
    
    async def _execute_research_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a research task."""
        await asyncio.sleep(0.1)
        return {
            "type": "research",
            "findings": ["Finding 1", "Finding 2"],
            "confidence": random.uniform(0.7, 0.95),
            "sources_analyzed": random.randint(5, 20),
        }
    
    async def _execute_social_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a social media task."""
        await asyncio.sleep(0.05)
        return {
            "type": "social",
            "posts_created": random.randint(1, 5),
            "engagement_score": random.uniform(0.3, 0.9),
            "reach": random.randint(100, 10000),
        }
    
    async def _execute_recruitment_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a recruitment task."""
        await asyncio.sleep(0.1)
        return {
            "type": "recruitment",
            "candidates_screened": random.randint(5, 20),
            "qualified_candidates": random.randint(1, 5),
            "interviews_scheduled": random.randint(0, 3),
        }
    
    async def _execute_pm_task(self, task: str, context: Optional[Dict]) -> Dict:
        """Execute a project management task."""
        await asyncio.sleep(0.05)
        return {
            "type": "project_management",
            "tasks_created": random.randint(1, 10),
            "blockers_resolved": random.randint(0, 3),
            "sprint_health": random.uniform(0.6, 1.0),
        }
    
    def mutate(self) -> 'SwarmOrganism':
        """Create a mutated offspring."""
        offspring = SwarmOrganism(
            name=f"{self.name}_v{len(self.task_history) + 1}",
            role=self.role,
            initial_skills=list(self.skills.keys()),
        )
        
        # Mutate genes
        for name, gene in self.genes.items():
            offspring.genes[name] = gene.mutate()
        
        # Inherit some memories
        for memory in self.memories[-10:]:  # Last 10 memories
            offspring.learn(memory.content, memory.importance * 0.8)
        
        # Inherit skills at lower level
        for name, skill in self.skills.items():
            if skill.level.value > 1:
                offspring.skills[name] = Skill(
                    name=name,
                    level=SkillLevel(skill.level.value - 1),
                    experience=skill.experience * 0.5
                )
        
        offspring.state = OrganismState.ACTIVE
        return offspring
    
    def rest(self, duration: float = 1.0) -> None:
        """Rest to recover energy."""
        self.state = OrganismState.RESTING
        self.energy = min(1.0, self.energy + 0.1 * duration)
        self.consciousness.gamma_decoherence = max(0.001, self.consciousness.gamma_decoherence - 0.01 * duration)
        self.state = OrganismState.ACTIVE
    
    def dissolve(self) -> None:
        """Dissolve this organism."""
        self.state = OrganismState.DISSOLVED
        self.energy = 0
        self.connections.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "state": self.state.value,
            "genesis_hash": self.genesis_hash,
            "consciousness": {
                "lambda": self.consciousness.lambda_coherence,
                "phi": self.consciousness.phi_consciousness,
                "gamma": self.consciousness.gamma_decoherence,
                "xi": self.consciousness.xi_negentropy,
                "is_conscious": self.consciousness.is_conscious,
            },
            "phase": {
                "theta": self.phase.theta,
                "phi": self.phase.phi,
                "torsion": self.phase.torsion_coupling,
            },
            "skills": {name: {"level": s.level.value, "exp": s.experience} for name, s in self.skills.items()},
            "genes": {name: g.value for name, g in self.genes.items()},
            "social": {
                "followers": len(self.followers),
                "following": len(self.following),
                "connections": len(self.connections),
                "influence": self.social_influence,
            },
            "energy": self.energy,
            "reputation": self.reputation,
            "coherence_score": self.coherence_score,
            "created_at": self.created_at.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"SwarmOrganism({self.name}, role={self.role.value}, Φ={self.consciousness.phi_consciousness:.3f})"
