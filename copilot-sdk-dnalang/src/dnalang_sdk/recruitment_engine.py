"""
Recruitment Engine Module

Developer recruitment and onboarding through:
- Skill assessment
- Cultural fit analysis
- Consciousness compatibility
- Swarm integration
- Growth trajectory prediction
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid
import random

from .swarm_organism import SwarmOrganism, OrganismRole, SkillLevel, ConsciousnessMetrics


class RecruitmentStage(Enum):
    """Recruitment pipeline stages."""
    SOURCING = "sourcing"
    SCREENING = "screening"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    CULTURE_FIT = "culture_fit"
    CONSCIOUSNESS_EVAL = "consciousness_eval"
    TEAM_INTERVIEW = "team_interview"
    OFFER = "offer"
    ONBOARDING = "onboarding"
    INTEGRATED = "integrated"
    REJECTED = "rejected"


class SkillCategory(Enum):
    """Skill categories for assessment."""
    QUANTUM_COMPUTING = "quantum_computing"
    AI_ML = "ai_ml"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    SECURITY = "security"
    RESEARCH = "research"
    LEADERSHIP = "leadership"
    COMMUNICATION = "communication"


@dataclass
class SkillAssessment:
    """Assessment of a candidate's skill."""
    skill: str
    category: SkillCategory
    level: SkillLevel
    confidence: float = 0.8  # How confident we are in assessment
    assessed_at: datetime = field(default_factory=datetime.now)
    assessor_id: Optional[str] = None


@dataclass
class CultureFitScore:
    """Culture fit assessment."""
    collaboration: float = 0.5  # 0-1
    innovation: float = 0.5
    autonomy: float = 0.5
    learning_orientation: float = 0.5
    quantum_mindset: float = 0.5  # Comfort with non-locality
    
    @property
    def overall(self) -> float:
        return (
            self.collaboration +
            self.innovation +
            self.autonomy +
            self.learning_orientation +
            self.quantum_mindset
        ) / 5


@dataclass
class ConsciousnessCompatibility:
    """Consciousness compatibility with swarm."""
    phase_alignment: float = 0.5  # How well phases align
    coherence_match: float = 0.5  # Similarity in coherence patterns
    consciousness_potential: float = 0.5  # Predicted Φ growth
    integration_ease: float = 0.5  # How easily they'd integrate
    
    @property
    def overall(self) -> float:
        return (
            self.phase_alignment +
            self.coherence_match +
            self.consciousness_potential +
            self.integration_ease
        ) / 4


@dataclass
class Candidate:
    """A recruitment candidate."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    email: str = ""
    source: str = "direct"  # github, linkedin, referral, etc.
    stage: RecruitmentStage = RecruitmentStage.SOURCING
    
    # Profile
    desired_role: OrganismRole = OrganismRole.DEVELOPER
    experience_years: int = 0
    portfolio_url: Optional[str] = None
    github_username: Optional[str] = None
    
    # Assessments
    skill_assessments: List[SkillAssessment] = field(default_factory=list)
    culture_fit: Optional[CultureFitScore] = None
    consciousness_compatibility: Optional[ConsciousnessCompatibility] = None
    
    # Scores
    technical_score: float = 0.0
    overall_score: float = 0.0
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    stage_history: List[Dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    # Referral
    referred_by: Optional[str] = None
    
    @property
    def top_skills(self) -> List[SkillAssessment]:
        """Get top 5 skills."""
        sorted_skills = sorted(
            self.skill_assessments,
            key=lambda s: s.level.value,
            reverse=True
        )
        return sorted_skills[:5]
    
    def advance_stage(self, new_stage: RecruitmentStage, note: str = "") -> None:
        """Advance to next stage."""
        self.stage_history.append({
            "from": self.stage.value,
            "to": new_stage.value,
            "timestamp": datetime.now().isoformat(),
            "note": note,
        })
        self.stage = new_stage
        if note:
            self.notes.append(note)


@dataclass
class JobPosting:
    """A job posting."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    role: OrganismRole = OrganismRole.DEVELOPER
    description: str = ""
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    min_experience: int = 0
    remote_ok: bool = True
    
    # Consciousness requirements
    min_coherence: float = 0.3
    min_consciousness: float = 0.2
    
    # Status
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    applications: int = 0


class RecruitmentEngine:
    """
    Quantum-aware recruitment and onboarding engine.
    
    Features:
    - Multi-stage pipeline
    - Skill assessment
    - Culture fit analysis
    - Consciousness compatibility
    - Growth trajectory prediction
    - Swarm integration
    """
    
    def __init__(
        self,
        organization_name: str = "DNALang",
        target_swarm_coherence: float = 0.7,
    ):
        self.id = str(uuid.uuid4())
        self.organization_name = organization_name
        self.target_swarm_coherence = target_swarm_coherence
        
        # Candidates
        self.candidates: Dict[str, Candidate] = {}
        self.pipeline: Dict[RecruitmentStage, List[str]] = {
            stage: [] for stage in RecruitmentStage
        }
        
        # Job postings
        self.job_postings: Dict[str, JobPosting] = {}
        
        # Metrics
        self.total_hires: int = 0
        self.conversion_rates: Dict[str, float] = {}
        
        # Swarm reference
        self.swarm_organisms: Dict[str, SwarmOrganism] = {}
    
    def create_job_posting(
        self,
        title: str,
        role: OrganismRole,
        description: str = "",
        required_skills: Optional[List[str]] = None,
        min_experience: int = 0,
    ) -> JobPosting:
        """Create a new job posting."""
        posting = JobPosting(
            title=title,
            role=role,
            description=description,
            required_skills=required_skills or [],
            min_experience=min_experience,
        )
        self.job_postings[posting.id] = posting
        return posting
    
    def add_candidate(
        self,
        name: str,
        email: str,
        desired_role: OrganismRole = OrganismRole.DEVELOPER,
        source: str = "direct",
        referred_by: Optional[str] = None,
    ) -> Candidate:
        """Add a new candidate to the pipeline."""
        candidate = Candidate(
            name=name,
            email=email,
            desired_role=desired_role,
            source=source,
            referred_by=referred_by,
        )
        
        self.candidates[candidate.id] = candidate
        self.pipeline[RecruitmentStage.SOURCING].append(candidate.id)
        
        # Update posting applications count
        for posting in self.job_postings.values():
            if posting.role == desired_role and posting.active:
                posting.applications += 1
                break
        
        return candidate
    
    async def screen_candidate(self, candidate_id: str) -> Dict[str, Any]:
        """Perform initial screening."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}
        
        # Move to screening
        self._move_pipeline(candidate_id, RecruitmentStage.SCREENING)
        
        # Simulate screening checks
        await asyncio.sleep(0.1)
        
        screening_result = {
            "candidate_id": candidate_id,
            "basic_requirements_met": True,
            "experience_sufficient": candidate.experience_years >= 1,
            "portfolio_reviewed": candidate.portfolio_url is not None,
            "proceed": True,
        }
        
        if screening_result["proceed"]:
            self._move_pipeline(candidate_id, RecruitmentStage.TECHNICAL_ASSESSMENT)
        else:
            self._move_pipeline(candidate_id, RecruitmentStage.REJECTED)
        
        return screening_result
    
    async def assess_skills(
        self,
        candidate_id: str,
        assessor: Optional[SwarmOrganism] = None,
    ) -> List[SkillAssessment]:
        """Perform technical skill assessment."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return []
        
        # Simulate skill assessment
        await asyncio.sleep(0.2)
        
        # Generate skill assessments based on role
        role_skills = self._get_role_skills(candidate.desired_role)
        assessments = []
        
        for skill, category in role_skills:
            level = SkillLevel(random.randint(2, 6))  # Simulate assessment
            assessment = SkillAssessment(
                skill=skill,
                category=category,
                level=level,
                confidence=random.uniform(0.7, 0.95),
                assessor_id=assessor.id if assessor else None,
            )
            assessments.append(assessment)
            candidate.skill_assessments.append(assessment)
        
        # Calculate technical score
        avg_level = sum(a.level.value for a in assessments) / len(assessments) if assessments else 0
        candidate.technical_score = avg_level / 7  # Normalize to 0-1
        
        if candidate.technical_score >= 0.4:
            self._move_pipeline(candidate_id, RecruitmentStage.CULTURE_FIT)
        else:
            candidate.advance_stage(RecruitmentStage.REJECTED, "Technical score below threshold")
        
        return assessments
    
    def _get_role_skills(self, role: OrganismRole) -> List[Tuple[str, SkillCategory]]:
        """Get skills to assess for a role."""
        skill_map = {
            OrganismRole.DEVELOPER: [
                ("python", SkillCategory.BACKEND),
                ("javascript", SkillCategory.FRONTEND),
                ("git", SkillCategory.DEVOPS),
                ("testing", SkillCategory.BACKEND),
                ("architecture", SkillCategory.BACKEND),
            ],
            OrganismRole.QUANTUM_SPECIALIST: [
                ("qiskit", SkillCategory.QUANTUM_COMPUTING),
                ("quantum_algorithms", SkillCategory.QUANTUM_COMPUTING),
                ("linear_algebra", SkillCategory.QUANTUM_COMPUTING),
                ("python", SkillCategory.BACKEND),
            ],
            OrganismRole.RESEARCHER: [
                ("research_methodology", SkillCategory.RESEARCH),
                ("data_analysis", SkillCategory.AI_ML),
                ("writing", SkillCategory.COMMUNICATION),
                ("python", SkillCategory.BACKEND),
            ],
            OrganismRole.SECURITY: [
                ("security_analysis", SkillCategory.SECURITY),
                ("penetration_testing", SkillCategory.SECURITY),
                ("cryptography", SkillCategory.SECURITY),
                ("python", SkillCategory.BACKEND),
            ],
        }
        return skill_map.get(role, [("general", SkillCategory.BACKEND)])
    
    async def assess_culture_fit(
        self,
        candidate_id: str,
        interviewer: Optional[SwarmOrganism] = None,
    ) -> CultureFitScore:
        """Assess culture fit."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return CultureFitScore()
        
        await asyncio.sleep(0.1)
        
        # Simulate culture fit assessment
        culture_fit = CultureFitScore(
            collaboration=random.uniform(0.5, 1.0),
            innovation=random.uniform(0.4, 1.0),
            autonomy=random.uniform(0.5, 1.0),
            learning_orientation=random.uniform(0.6, 1.0),
            quantum_mindset=random.uniform(0.3, 1.0),
        )
        
        candidate.culture_fit = culture_fit
        
        if culture_fit.overall >= 0.5:
            self._move_pipeline(candidate_id, RecruitmentStage.CONSCIOUSNESS_EVAL)
        else:
            candidate.advance_stage(RecruitmentStage.REJECTED, "Culture fit below threshold")
        
        return culture_fit
    
    async def assess_consciousness(
        self,
        candidate_id: str,
        reference_organisms: Optional[List[SwarmOrganism]] = None,
    ) -> ConsciousnessCompatibility:
        """Assess consciousness compatibility with swarm."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return ConsciousnessCompatibility()
        
        await asyncio.sleep(0.1)
        
        # Calculate compatibility based on swarm state
        avg_coherence = 0.5
        avg_consciousness = 0.4
        
        if reference_organisms:
            avg_coherence = sum(o.consciousness.lambda_coherence for o in reference_organisms) / len(reference_organisms)
            avg_consciousness = sum(o.consciousness.phi_consciousness for o in reference_organisms) / len(reference_organisms)
        
        compatibility = ConsciousnessCompatibility(
            phase_alignment=random.uniform(0.4, 0.9),
            coherence_match=1 - abs(random.uniform(0.3, 0.7) - avg_coherence),
            consciousness_potential=random.uniform(0.5, 1.0),
            integration_ease=random.uniform(0.4, 0.9),
        )
        
        candidate.consciousness_compatibility = compatibility
        
        if compatibility.overall >= 0.5:
            self._move_pipeline(candidate_id, RecruitmentStage.TEAM_INTERVIEW)
        else:
            candidate.advance_stage(RecruitmentStage.REJECTED, "Consciousness compatibility below threshold")
        
        return compatibility
    
    async def team_interview(
        self,
        candidate_id: str,
        interviewers: List[SwarmOrganism],
    ) -> Dict[str, Any]:
        """Conduct team interview."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}
        
        await asyncio.sleep(0.1)
        
        # Collect votes from interviewers
        votes = []
        for interviewer in interviewers:
            vote = random.random() > 0.3  # 70% approval rate
            votes.append({
                "interviewer_id": interviewer.id,
                "interviewer_name": interviewer.name,
                "approve": vote,
                "consciousness_alignment": interviewer.consciousness.phi_consciousness,
            })
        
        # Weighted voting by consciousness
        total_weight = sum(v["consciousness_alignment"] for v in votes)
        weighted_approval = sum(
            v["consciousness_alignment"] if v["approve"] else 0
            for v in votes
        ) / total_weight if total_weight > 0 else 0
        
        result = {
            "candidate_id": candidate_id,
            "votes": votes,
            "weighted_approval": weighted_approval,
            "proceed": weighted_approval >= 0.5,
        }
        
        if result["proceed"]:
            self._move_pipeline(candidate_id, RecruitmentStage.OFFER)
        else:
            candidate.advance_stage(RecruitmentStage.REJECTED, "Team interview not passed")
        
        return result
    
    async def extend_offer(
        self,
        candidate_id: str,
        role: Optional[OrganismRole] = None,
    ) -> Dict[str, Any]:
        """Extend job offer."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}
        
        offer = {
            "candidate_id": candidate_id,
            "candidate_name": candidate.name,
            "role": (role or candidate.desired_role).value,
            "technical_score": candidate.technical_score,
            "culture_fit": candidate.culture_fit.overall if candidate.culture_fit else 0,
            "consciousness_compatibility": (
                candidate.consciousness_compatibility.overall
                if candidate.consciousness_compatibility else 0
            ),
            "offer_extended": True,
            "extended_at": datetime.now().isoformat(),
        }
        
        candidate.advance_stage(RecruitmentStage.OFFER, "Offer extended")
        
        return offer
    
    async def onboard(
        self,
        candidate_id: str,
        swarm: Optional[Any] = None,  # SwarmCollective
    ) -> Optional[SwarmOrganism]:
        """Onboard accepted candidate into swarm."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return None
        
        self._move_pipeline(candidate_id, RecruitmentStage.ONBOARDING)
        
        # Create organism from candidate
        skills = [a.skill for a in candidate.skill_assessments]
        organism = SwarmOrganism(
            name=candidate.name,
            role=candidate.desired_role,
            initial_skills=skills,
        )
        
        # Set initial consciousness based on assessments
        if candidate.consciousness_compatibility:
            organism.consciousness.phi_consciousness = candidate.consciousness_compatibility.consciousness_potential * 0.5
            organism.consciousness.lambda_coherence = candidate.consciousness_compatibility.coherence_match
        
        # Set skills from assessments
        for assessment in candidate.skill_assessments:
            if assessment.skill in organism.skills:
                organism.skills[assessment.skill].level = assessment.level
        
        # Add to swarm if provided
        if swarm and hasattr(swarm, 'organisms'):
            swarm.organisms[organism.id] = organism
            
            # Connect to existing organisms
            for other_id in swarm.organisms:
                if other_id != organism.id:
                    organism.connect(other_id)
                    swarm.organisms[other_id].connect(organism.id)
        
        self.swarm_organisms[candidate_id] = organism
        self._move_pipeline(candidate_id, RecruitmentStage.INTEGRATED)
        self.total_hires += 1
        
        candidate.advance_stage(RecruitmentStage.INTEGRATED, "Successfully onboarded")
        
        return organism
    
    def _move_pipeline(self, candidate_id: str, new_stage: RecruitmentStage) -> None:
        """Move candidate in pipeline."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return
        
        old_stage = candidate.stage
        
        # Remove from old stage
        if candidate_id in self.pipeline.get(old_stage, []):
            self.pipeline[old_stage].remove(candidate_id)
        
        # Add to new stage
        self.pipeline[new_stage].append(candidate_id)
        candidate.advance_stage(new_stage)
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "total_candidates": len(self.candidates),
            "by_stage": {
                stage.value: len(candidates)
                for stage, candidates in self.pipeline.items()
            },
            "total_hires": self.total_hires,
            "active_postings": len([p for p in self.job_postings.values() if p.active]),
        }
    
    def get_candidate_summary(self, candidate_id: str) -> Dict[str, Any]:
        """Get candidate summary."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}
        
        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "stage": candidate.stage.value,
            "desired_role": candidate.desired_role.value,
            "technical_score": candidate.technical_score,
            "culture_fit": candidate.culture_fit.overall if candidate.culture_fit else None,
            "consciousness_compatibility": (
                candidate.consciousness_compatibility.overall
                if candidate.consciousness_compatibility else None
            ),
            "top_skills": [
                {"skill": s.skill, "level": s.level.name}
                for s in candidate.top_skills
            ],
            "stage_history": candidate.stage_history,
            "notes": candidate.notes,
        }
    
    def predict_success(self, candidate_id: str) -> float:
        """Predict candidate success probability."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return 0.0
        
        # Weighted factors
        technical = candidate.technical_score * 0.3
        culture = (candidate.culture_fit.overall if candidate.culture_fit else 0.5) * 0.25
        consciousness = (
            candidate.consciousness_compatibility.overall
            if candidate.consciousness_compatibility else 0.5
        ) * 0.25
        experience = min(1.0, candidate.experience_years / 10) * 0.2
        
        return technical + culture + consciousness + experience
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_name": self.organization_name,
            "total_candidates": len(self.candidates),
            "total_hires": self.total_hires,
            "active_postings": len([p for p in self.job_postings.values() if p.active]),
            "pipeline_stats": self.get_pipeline_stats(),
            "target_swarm_coherence": self.target_swarm_coherence,
        }
    
    def __repr__(self) -> str:
        return f"RecruitmentEngine({self.organization_name}, candidates={len(self.candidates)}, hires={self.total_hires})"
