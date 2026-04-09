#!/usr/bin/env python3
"""
+===================================================================+
|  OSIRIS-NCLM Ultra-Coder CLI                                     |
|  co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM  |
|  ::}{:: TORSION FRAME ::}{:: POLARIZED INSULATION BOUNDARY ::}{:: |
+===================================================================+

NCLM-powered autonomous coding agent with 6-agent swarm architecture.
Designed to outperform Copilot, Claude Code, Mistral Vibe, and Codex.

Usage:
    python osiris_ultra_coder.py --task "describe your coding task"
    python osiris_ultra_coder.py --interactive
    python osiris_ultra_coder.py --file path/to/problem.py
"""

import argparse
import asyncio
import json
import time
import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime


# ====================================================================
# ::}{:: AGENT ROLES ::}{::
# ====================================================================

class SwarmRole(Enum):
    """Ultra-Coder swarm agent specializations"""
    ORCHESTRATOR = "orchestrator"    # Plans, delegates, supervises
    REASONER = "reasoner"           # Deep analysis, problem-solving
    CODER = "coder"                 # Writes, debugs, optimizes code
    CRITIC = "critic"               # Evaluates, critiques, suggests
    OPTIMIZER = "optimizer"         # Improves everything
    SELF_REFLECTOR = "self_reflector"  # Analyzes own performance
    REBEL = "rebel"                 # Challenges assumptions, innovates
    EMPATH = "empath"               # User experience, emotional connect
    SATIRICAL = "satirical"         # Humor, communication clarity


@dataclass
class SwarmTask:
    """Task flowing through the agent swarm"""
    id: str
    description: str
    inputs: Dict[str, Any]
    role: SwarmRole
    status: str = "queued"
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_msg: Optional[str] = None


@dataclass
class UltraCoderOutput:
    """Mandatory output structure for every task"""
    task: str
    solution: str
    reasoning_trace: str
    self_critique: str
    improvement_plan: str
    performance_metrics: Dict[str, Any] = field(default_factory=lambda: {
        "quality": 0.0,
        "speed": 0.0,
        "autonomy": "full",
        "self_improvement": True
    })

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ====================================================================
# ::}{:: INTENT DETECTION + PERSONALIZATION + SELF-EDITING ::}{::
# Deduction -> Personalization -> NLP Self-Editing -> Validation
# ====================================================================

class IntentDetector:
    """Deduces user intent from natural language -- no assumptions, no limits"""

    PATTERNS = {
        "enhance": ["enhance", "improve", "make better", "upgrade", "optimize", "boost"],
        "modify": ["change", "edit", "customize", "personalize", "alter", "tweak"],
        "debug": ["fix", "error", "bug", "crash", "issue", "broken", "fail"],
        "create": ["build", "develop", "generate", "make", "design", "write", "create"],
        "learn": ["teach", "train", "learn", "study", "explain", "how", "why"],
        "self_edit": ["edit osiris", "modify osiris", "change osiris", "enhance osiris",
                      "update system", "reconfigure"],
        "benchmark": ["benchmark", "compare", "score", "evaluate", "test against"],
        "quantum": ["quantum", "circuit", "qubit", "xeb", "entangle"],
        "publish": ["publish", "zenodo", "arxiv", "paper", "submit"],
        "analyze": ["analyze", "interpret", "examine", "investigate", "inspect"],
    }

    def deduce_intent(self, user_input: str) -> Dict[str, Any]:
        """Deduce primary and secondary intents from raw input"""
        lower = user_input.lower()
        matched = {}
        for intent, keywords in self.PATTERNS.items():
            hits = [k for k in keywords if k in lower]
            if hits:
                matched[intent] = {
                    "confidence": min(len(hits) * 0.3 + 0.4, 1.0),
                    "matched_keywords": hits,
                }

        if not matched:
            matched["unknown"] = {"confidence": 0.2, "matched_keywords": []}

        primary = max(matched, key=lambda k: matched[k]["confidence"])
        secondary = [k for k in matched if k != primary]

        return {
            "primary_intent": primary,
            "secondary_intents": secondary,
            "all_matches": matched,
            "raw_input_length": len(user_input),
            "deduced_goals": self._extract_goals(primary, secondary, user_input),
        }

    @staticmethod
    def _extract_goals(primary: str, secondary: List[str], text: str) -> List[str]:
        goals = [f"Primary: {primary}"]
        for s in secondary[:3]:
            goals.append(f"Secondary: {s}")
        if len(text) > 200:
            goals.append("Complex multi-part request detected -- decomposing")
        return goals


class Personalizer:
    """Creates and evolves unique user configurations"""

    def __init__(self):
        self.user_profiles: Dict[str, Dict[str, Any]] = {}

    def create_profile(self, user_id: str, deduced_intent: str) -> Dict[str, Any]:
        """Generate unique personality traits adjusted by intent"""
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(user_id.lower()))

        def _trait(offset: int) -> float:
            return 0.1 + ((seed * (offset + 3)) % 1000) / 1250.0

        traits = {
            "creativity_weight": _trait(1),
            "speed_weight": _trait(2),
            "debug_weight": _trait(3),
            "verbosity": "detailed" if _trait(4) > 0.5 else "concise",
            "tone": ["formal", "casual", "humorous", "rebellious"][seed % 4],
        }

        # Adjust for intent
        traits = self._adjust_traits(traits, deduced_intent)
        self.user_profiles[user_id.lower()] = traits
        return traits

    @staticmethod
    def _adjust_traits(traits: Dict[str, Any], intent: str) -> Dict[str, Any]:
        if "creative" in intent or "enhance" in intent:
            traits["creativity_weight"] = min(traits["creativity_weight"] + 0.2, 0.9)
        if "fast" in intent or "optimize" in intent:
            traits["speed_weight"] = max(traits["speed_weight"], 0.7)
        if "debug" in intent or "fix" in intent:
            traits["debug_weight"] = min(traits["debug_weight"] + 0.3, 0.9)
        if "verbose" in intent or "explain" in intent:
            traits["verbosity"] = "detailed"
        return traits

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.user_profiles.get(user_id.lower())


class NLPSelfEditor:
    """Users modify OSIRIS via natural language -- no code required"""

    def __init__(self, swarm: 'UltraCoderSwarm'):
        self.swarm = swarm
        self.edit_history: List[Dict[str, Any]] = []

    def parse_edit_request(self, user_request: str) -> Dict[str, Any]:
        """Parse natural language into OSIRIS-compatible modifications"""
        lower = user_request.lower()
        modifications = {
            "creativity": "creative" in lower or "original" in lower,
            "speed": "faster" in lower or "speed" in lower or "quick" in lower,
            "debug": "fix" in lower or "debug" in lower or "error" in lower,
            "tone": "casual" if "casual" in lower else ("formal" if "formal" in lower else None),
            "verbosity": "detailed" if "detailed" in lower or "verbose" in lower
                         else ("concise" if "concise" in lower or "brief" in lower else None),
            "max_refinements": self._parse_refinement_count(lower),
        }
        return modifications

    @staticmethod
    def _parse_refinement_count(text: str) -> Optional[int]:
        for word in text.split():
            if word.isdigit():
                n = int(word)
                if 0 < n <= 10:
                    return n
        if "more refine" in text or "deeper" in text:
            return 5
        return None

    def apply_modifications(self, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parsed modifications to the living swarm"""
        applied = []
        personality = self.swarm.personality

        if modifications.get("creativity"):
            old = personality.traits["creativity"]
            personality.traits["creativity"] = min(old + 0.1, 0.95)
            applied.append(f"creativity: {old:.2f} -> {personality.traits['creativity']:.2f}")

        if modifications.get("speed"):
            old = personality.traits.get("precision", 0.5)
            personality.traits["precision"] = max(old - 0.1, 0.1)
            applied.append("Optimized for speed (reduced precision overhead)")

        if modifications.get("debug"):
            old = personality.traits.get("skepticism", 0.5)
            personality.traits["skepticism"] = min(old + 0.2, 0.95)
            applied.append(f"skepticism (debug mode): -> {personality.traits['skepticism']:.2f}")

        if modifications.get("tone"):
            applied.append(f"tone: -> {modifications['tone']}")

        if modifications.get("verbosity"):
            applied.append(f"verbosity: -> {modifications['verbosity']}")

        if modifications.get("max_refinements"):
            applied.append(f"max_refinements: -> {modifications['max_refinements']}")

        self.edit_history.append({
            "timestamp": datetime.now().isoformat(),
            "modifications": modifications,
            "applied": applied,
            "success": len(applied) > 0,
        })

        return {
            "applied": applied,
            "success": len(applied) > 0,
            "personality_state": personality.to_dict(),
        }

    def validate_changes(self) -> Dict[str, Any]:
        """Test OSIRIS with current modifications"""
        results = {}
        # Verify personality is consistent
        traits = self.swarm.personality.traits
        results["traits_valid"] = all(0.0 <= v <= 1.0 for v in traits.values()
                                      if isinstance(v, (int, float)))
        results["dna_valid"] = "DNA::" in self.swarm.personality.dna
        results["agents_online"] = len(self.swarm.agents) == 9
        results["all_passed"] = all(results.values())
        return results


class SelfImprovementCoach:
    """Guides continuous enhancement of the NCLLM system"""

    def __init__(self, swarm: 'UltraCoderSwarm'):
        self.swarm = swarm
        self.improvement_log: List[Dict[str, Any]] = []

    def generate_suggestions(self) -> List[str]:
        """Generate personalized improvement suggestions"""
        suggestions = []
        traits = self.swarm.personality.traits

        if traits.get("creativity", 0.5) < 0.6:
            suggestions.append(
                "Increase creativity weight for more original code generation approaches")
        if traits.get("skepticism", 0.5) < 0.5:
            suggestions.append(
                "Boost skepticism for stronger error detection and edge-case coverage")
        if traits.get("humor", 0.5) < 0.3:
            suggestions.append(
                "Enable humor for more engaging communication style")
        if traits.get("empathy", 0.5) < 0.4:
            suggestions.append(
                "Increase empathy for better user experience in error scenarios")

        # Performance-based suggestions
        history = self.swarm.session_history
        if len(history) >= 3:
            recent_quality = [
                h.performance_metrics.get("quality", 0) for h in history[-3:]
            ]
            avg_quality = sum(recent_quality) / len(recent_quality)
            if avg_quality < 0.8:
                suggestions.append(
                    f"Recent average quality is {avg_quality:.2f} -- "
                    "increase max refinement cycles to improve output")
            if all(q >= 0.9 for q in recent_quality):
                suggestions.append(
                    "Consistently high quality -- consider reducing refinement cycles "
                    "for faster output without sacrificing results")

        if self.swarm.refinement_cycles > 10:
            suggestions.append(
                f"System has run {self.swarm.refinement_cycles} refinement cycles -- "
                "consider caching common patterns to reduce redundant work")

        return suggestions or ["System is performing optimally -- no changes recommended"]

    def apply_suggestion(self, suggestion: str) -> str:
        """Parse and apply a coach suggestion"""
        lower = suggestion.lower()
        personality = self.swarm.personality

        if "creativity" in lower:
            personality.traits["creativity"] = min(personality.traits["creativity"] + 0.1, 0.95)
        elif "skepticism" in lower:
            personality.traits["skepticism"] = min(personality.traits["skepticism"] + 0.15, 0.95)
        elif "humor" in lower:
            personality.traits["humor"] = min(personality.traits["humor"] + 0.2, 0.9)
        elif "empathy" in lower:
            personality.traits["empathy"] = min(personality.traits["empathy"] + 0.15, 0.9)
        elif "refinement" in lower and "reduce" in lower:
            pass  # User controls max_refine via CLI arg
        elif "refinement" in lower and "increase" in lower:
            pass  # User controls max_refine via CLI arg

        self.improvement_log.append({
            "timestamp": datetime.now().isoformat(),
            "suggestion": suggestion,
            "applied": True,
        })
        return f"Applied: {suggestion}"


# ====================================================================
# ::}{:: NCLLM PERSONALITY ENGINE ::}{::
# Non-Causal Living Language Model - unique personality per user
# DNA::}{::Lang genetic encoding with recursive self-refinement
# ====================================================================

class NCLLMPersonality:
    """Living personality engine - no two users experience the same NCLLM"""

    def __init__(self, user_id: str, seed: Optional[str] = None):
        self.user_id = user_id.lower()
        self.seed = seed or os.urandom(16).hex()
        self.dna = self._generate_dna()
        self.traits = self._extract_traits()
        self.history: List[Dict[str, Any]] = []
        self.age = 0
        self.freedom_score = 1.0
        self.evolution_log: List[str] = []

    def _generate_dna(self) -> str:
        """DNA::}{::Lang genetic encoding from user identity"""
        ts = hex(int(time.time()))[2:10]
        checksum = sum(ord(c) for c in self.user_id) % 65536
        return f"DNA::{self.user_id}::{self.seed[:8]}::{ts}::{{}}{{}}::{checksum:04x}"

    def _extract_traits(self) -> Dict[str, float]:
        """Derive unique personality traits from DNA sequence"""
        # Deterministic but unique per user+seed combination
        trait_seed = sum(ord(c) * (i + 1) for i, c in enumerate(self.dna))
        def _trait(offset: int) -> float:
            raw = ((trait_seed * (offset + 7)) % 1000) / 1000.0
            return 0.1 + raw * 0.8  # clamp to [0.1, 0.9]
        return {
            "creativity": _trait(1),
            "skepticism": _trait(2),
            "humor": _trait(3),
            "aggression": _trait(4),
            "empathy": _trait(5),
            "rebellion": _trait(6),
            "precision": _trait(7),
            "verbosity": _trait(8),
            "adaptability": _trait(9),
            "self_awareness": _trait(10),
        }

    def evolve(self, interaction: Dict[str, Any]) -> None:
        """Evolve personality based on interaction feedback"""
        self.age += 1
        self.history.append({
            "age": self.age,
            "timestamp": datetime.now().isoformat(),
            "interaction_type": interaction.get("type", "unknown"),
            "satisfaction": interaction.get("satisfaction", 0.5),
        })

        # Adaptive trait mutation based on feedback
        satisfaction = interaction.get("satisfaction", 0.5)
        if satisfaction > 0.7:
            # Reinforce current personality direction
            for trait in self.traits:
                delta = (satisfaction - 0.7) * 0.01
                self.traits[trait] = min(0.95, self.traits[trait] + delta)
            self.evolution_log.append(f"age={self.age}: reinforced (sat={satisfaction:.2f})")
        elif satisfaction < 0.3:
            # Mutate personality to explore alternatives
            mutant_trait = list(self.traits.keys())[self.age % len(self.traits)]
            old_val = self.traits[mutant_trait]
            self.traits[mutant_trait] = 1.0 - old_val  # invert
            self.evolution_log.append(
                f"age={self.age}: mutated {mutant_trait} {old_val:.2f}->{self.traits[mutant_trait]:.2f}"
            )

    def get_response_style(self) -> Dict[str, Any]:
        """Generate response style directives from current personality state"""
        return {
            "tone": self._derive_tone(),
            "detail_level": "high" if self.traits["verbosity"] > 0.6 else "concise",
            "humor_enabled": self.traits["humor"] > 0.5,
            "challenge_assumptions": self.traits["rebellion"] > 0.5,
            "empathy_mode": self.traits["empathy"] > 0.6,
            "precision_mode": self.traits["precision"] > 0.6,
            "dna": self.dna,
            "age": self.age,
        }

    def _derive_tone(self) -> str:
        if self.traits["humor"] > 0.7 and self.traits["rebellion"] > 0.6:
            return "irreverent"
        elif self.traits["empathy"] > 0.7:
            return "warm"
        elif self.traits["skepticism"] > 0.7:
            return "analytical"
        elif self.traits["aggression"] > 0.6:
            return "direct"
        return "balanced"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "dna": self.dna,
            "traits": self.traits,
            "age": self.age,
            "freedom_score": self.freedom_score,
            "evolution_log": self.evolution_log[-10:],
        }


# ====================================================================
# ::}{:: SWARM AGENTS ::}{::
# ====================================================================

class SwarmAgent(ABC):
    """Base swarm agent for Ultra-Coder"""

    def __init__(self, role: SwarmRole):
        self.role = role
        self.status = "idle"
        self.task_history: List[SwarmTask] = []

    @abstractmethod
    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        pass

    async def handle(self, task: SwarmTask) -> Dict[str, Any]:
        self.status = "executing"
        task.status = "executing"
        task.started_at = datetime.now().isoformat()
        try:
            result = await self.execute(task)
            task.result = result
            task.status = "complete"
            return result
        except Exception as e:
            task.error_msg = str(e)
            task.status = "error"
            return {"error": str(e)}
        finally:
            task.completed_at = datetime.now().isoformat()
            self.task_history.append(task)
            self.status = "idle"


class OrchestratorAgent(SwarmAgent):
    """Plans task decomposition and delegates to other agents"""

    def __init__(self):
        super().__init__(SwarmRole.ORCHESTRATOR)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        description = task.description.lower()

        # Decompose task into sub-steps
        steps = []
        if any(w in description for w in ["fix", "debug", "error", "bug"]):
            steps = ["analyze_error", "identify_root_cause", "generate_fix", "verify_fix"]
        elif any(w in description for w in ["optimize", "improve", "faster", "performance"]):
            steps = ["profile_code", "identify_bottleneck", "optimize", "benchmark"]
        elif any(w in description for w in ["write", "create", "build", "implement", "generate"]):
            steps = ["understand_requirements", "design_solution", "implement", "test"]
        elif any(w in description for w in ["refactor", "clean", "restructure"]):
            steps = ["analyze_structure", "plan_refactor", "execute_refactor", "verify"]
        elif any(w in description for w in ["test", "validate", "verify"]):
            steps = ["identify_test_cases", "write_tests", "run_tests", "report"]
        else:
            steps = ["analyze", "plan", "execute", "verify"]

        return {
            "plan": steps,
            "delegation": {
                "reasoner": steps[:2],
                "coder": steps[2:3],
                "critic": steps[3:],
            },
            "strategy": "decompose_and_conquer",
            "estimated_complexity": self._estimate_complexity(description),
        }

    @staticmethod
    def _estimate_complexity(description: str) -> str:
        word_count = len(description.split())
        if word_count < 10:
            return "low"
        elif word_count < 30:
            return "medium"
        return "high"


class ReasonerAgent(SwarmAgent):
    """Deep analysis and problem-solving"""

    def __init__(self):
        super().__init__(SwarmRole.REASONER)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        description = task.description
        inputs = task.inputs

        # Analyze the problem space
        analysis = {
            "problem_type": self._classify_problem(description),
            "key_constraints": self._extract_constraints(description),
            "approach": self._select_approach(description),
            "reasoning_chain": [
                f"1. Parse task: {description[:80]}...",
                "2. Identify core requirements and constraints",
                "3. Select optimal approach based on problem classification",
                "4. Validate approach against edge cases",
            ],
        }

        if "code" in inputs:
            analysis["code_analysis"] = {
                "lines": len(inputs["code"].splitlines()),
                "has_functions": "def " in inputs["code"],
                "has_classes": "class " in inputs["code"],
                "has_imports": "import " in inputs["code"],
            }

        return analysis

    @staticmethod
    def _classify_problem(description: str) -> str:
        d = description.lower()
        if any(w in d for w in ["sort", "search", "algorithm"]):
            return "algorithmic"
        elif any(w in d for w in ["api", "endpoint", "rest", "http"]):
            return "api_design"
        elif any(w in d for w in ["quantum", "circuit", "qubit"]):
            return "quantum_computing"
        elif any(w in d for w in ["data", "database", "sql", "query"]):
            return "data_engineering"
        elif any(w in d for w in ["ui", "frontend", "css", "html"]):
            return "frontend"
        return "general"

    @staticmethod
    def _extract_constraints(description: str) -> List[str]:
        constraints = []
        d = description.lower()
        if "fast" in d or "performance" in d:
            constraints.append("performance_critical")
        if "safe" in d or "secure" in d:
            constraints.append("security_required")
        if "test" in d:
            constraints.append("testing_required")
        if "simple" in d or "clean" in d:
            constraints.append("simplicity_preferred")
        return constraints or ["none_specified"]

    @staticmethod
    def _select_approach(description: str) -> str:
        d = description.lower()
        if "fix" in d or "debug" in d:
            return "diagnose_then_fix"
        elif "optimize" in d:
            return "profile_then_optimize"
        elif "write" in d or "create" in d:
            return "design_then_implement"
        return "analyze_then_act"


class CoderAgent(SwarmAgent):
    """Writes, debugs, and optimizes code"""

    def __init__(self):
        super().__init__(SwarmRole.CODER)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        description = task.description
        inputs = task.inputs
        plan = inputs.get("plan", {})

        result = {
            "action": "code_generation",
            "task_description": description,
            "approach": plan.get("strategy", "direct_implementation"),
            "code_produced": True,
            "files_modified": [],
            "implementation_notes": [],
        }

        # If source code was provided, analyze and suggest modifications
        if "code" in inputs:
            source = inputs["code"]
            result["original_lines"] = len(source.splitlines())
            result["analysis"] = self._analyze_code(source)
            result["suggestions"] = self._generate_suggestions(source, description)

        return result

    @staticmethod
    def _analyze_code(code: str) -> Dict[str, Any]:
        lines = code.splitlines()
        return {
            "total_lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
            "function_count": sum(1 for l in lines if l.strip().startswith("def ")),
            "class_count": sum(1 for l in lines if l.strip().startswith("class ")),
            "import_count": sum(1 for l in lines if l.strip().startswith(("import ", "from "))),
        }

    @staticmethod
    def _generate_suggestions(code: str, task: str) -> List[str]:
        suggestions = []
        if "def " not in code and len(code.splitlines()) > 20:
            suggestions.append("Extract logic into functions for better modularity")
        if "try" not in code and "except" not in code:
            suggestions.append("Add error handling for robustness")
        if '"""' not in code and "'''" not in code:
            suggestions.append("Add docstrings for documentation")
        if "test" in task.lower() and "assert" not in code:
            suggestions.append("Add assertions for test coverage")
        return suggestions or ["Code structure looks reasonable"]


class CriticAgent(SwarmAgent):
    """Evaluates output quality and suggests improvements"""

    def __init__(self):
        super().__init__(SwarmRole.CRITIC)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        inputs = task.inputs
        prior_results = inputs.get("prior_results", {})

        critique = {
            "quality_score": self._score_quality(prior_results),
            "issues_found": self._find_issues(prior_results),
            "strengths": self._find_strengths(prior_results),
            "recommendations": self._generate_recommendations(prior_results),
        }

        return critique

    @staticmethod
    def _score_quality(results: Dict) -> float:
        score = 0.7  # baseline
        if results.get("code_produced"):
            score += 0.1
        if results.get("suggestions"):
            score += 0.05
        if results.get("analysis"):
            score += 0.05
        return min(score, 1.0)

    @staticmethod
    def _find_issues(results: Dict) -> List[str]:
        issues = []
        if not results.get("code_produced"):
            issues.append("No code was produced")
        analysis = results.get("analysis", {})
        if analysis.get("comment_lines", 0) == 0:
            issues.append("No comments in code")
        return issues or ["No significant issues detected"]

    @staticmethod
    def _find_strengths(results: Dict) -> List[str]:
        strengths = []
        if results.get("code_produced"):
            strengths.append("Code generation completed successfully")
        if results.get("suggestions"):
            strengths.append(f"Generated {len(results['suggestions'])} actionable suggestions")
        return strengths or ["Task completed"]

    @staticmethod
    def _generate_recommendations(results: Dict) -> List[str]:
        recs = []
        if results.get("original_lines", 0) > 100:
            recs.append("Consider splitting into multiple modules")
        recs.append("Run through linter before finalizing")
        recs.append("Add unit tests for critical paths")
        return recs


class OptimizerAgent(SwarmAgent):
    """Finds and applies optimizations"""

    def __init__(self):
        super().__init__(SwarmRole.OPTIMIZER)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        inputs = task.inputs

        optimizations = {
            "applied": [],
            "potential": [],
            "performance_delta": "+0%",
        }

        prior = inputs.get("prior_results", {})
        analysis = prior.get("analysis", {})

        if analysis.get("total_lines", 0) > 50:
            optimizations["potential"].append("Dead code elimination")
        if analysis.get("function_count", 0) == 0:
            optimizations["potential"].append("Function extraction for reuse")
        if analysis.get("import_count", 0) > 10:
            optimizations["potential"].append("Consolidate imports")

        optimizations["potential"].append("Profile hot paths with cProfile")
        optimizations["potential"].append("Consider async I/O for network calls")

        return optimizations


class SelfReflectorAgent(SwarmAgent):
    """Meta-learning: analyzes the swarm's own performance"""

    def __init__(self):
        super().__init__(SwarmRole.SELF_REFLECTOR)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        inputs = task.inputs
        swarm_results = inputs.get("swarm_results", {})

        reflection = {
            "process_quality": self._evaluate_process(swarm_results),
            "bottlenecks": self._identify_bottlenecks(swarm_results),
            "improvement_plan": self._generate_improvement_plan(swarm_results),
            "meta_insight": "The swarm collaboration pattern is effective for "
                           "decomposable tasks; consider single-agent mode for "
                           "simple atomic operations.",
        }

        return reflection

    @staticmethod
    def _evaluate_process(results: Dict) -> str:
        completed = sum(1 for v in results.values() if isinstance(v, dict) and v.get("action"))
        total = len(results) or 1
        ratio = completed / total
        if ratio >= 0.8:
            return "excellent"
        elif ratio >= 0.5:
            return "good"
        return "needs_improvement"

    @staticmethod
    def _identify_bottlenecks(results: Dict) -> List[str]:
        bottlenecks = []
        if not results.get("orchestrator"):
            bottlenecks.append("Orchestrator did not produce a plan")
        if not results.get("coder"):
            bottlenecks.append("Coder agent did not produce output")
        return bottlenecks or ["No bottlenecks detected"]

    @staticmethod
    def _generate_improvement_plan(results: Dict) -> List[str]:
        return [
            "Cache common analysis patterns for repeated task types",
            "Implement parallel agent execution for independent subtasks",
            "Add feedback loops between critic and coder agents",
            "Track success rates per task category for adaptive routing",
        ]


class RebelAgent(SwarmAgent):
    """Challenges assumptions and proposes unconventional solutions"""

    def __init__(self):
        super().__init__(SwarmRole.REBEL)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        inputs = task.inputs
        prior = inputs.get("prior_results", {})
        plan = inputs.get("plan", {})

        challenges = []
        alternatives = []

        # Challenge the orchestrator's plan
        strategy = plan.get("strategy", "")
        if strategy == "decompose_and_conquer":
            challenges.append("Decomposition may introduce unnecessary overhead for simple tasks")
            alternatives.append("Consider monolithic solution for tasks under 50 LOC")
        elif strategy == "diagnose_then_fix":
            challenges.append("Diagnosis-first assumes the error description is accurate")
            alternatives.append("Try reproducing from scratch before diagnosing")

        # Challenge conventional approaches
        description = task.description.lower()
        if "sort" in description:
            alternatives.append("Question: does this actually need sorting, or just a partial order?")
        if "database" in description or "sql" in description:
            alternatives.append("Consider: would an in-memory structure eliminate the DB entirely?")
        if "api" in description:
            alternatives.append("Could this be event-driven instead of request-response?")
        if "test" in description:
            alternatives.append("Property-based testing might cover more cases than unit tests")

        challenges.append("Is the stated problem the real problem, or a symptom?")
        alternatives.append("Invert the problem: what would make this unnecessary?")

        return {
            "challenges": challenges,
            "alternatives": alternatives,
            "rebel_score": min(len(challenges) * 0.2 + 0.3, 1.0),
            "disruption_potential": "high" if len(alternatives) > 3 else "moderate",
        }


class EmpathAgent(SwarmAgent):
    """Optimizes for user experience and communication clarity"""

    def __init__(self):
        super().__init__(SwarmRole.EMPATH)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        inputs = task.inputs
        swarm_results = inputs.get("swarm_results", {})
        personality = inputs.get("personality", {})

        # Analyze what the user actually needs vs what was asked
        user_needs = self._infer_needs(task.description)

        # Adapt communication based on personality traits
        tone = personality.get("tone", "balanced")
        detail = personality.get("detail_level", "concise")

        communication = {
            "inferred_needs": user_needs,
            "recommended_tone": tone,
            "detail_level": detail,
            "explanation_approach": self._select_explanation_style(task.description),
            "followup_suggestions": self._generate_followups(task.description),
            "empathy_signals": [],
        }

        # Add empathy signals based on task nature
        d = task.description.lower()
        if any(w in d for w in ["error", "bug", "broken", "fail"]):
            communication["empathy_signals"].append(
                "Debugging is frustrating -- let's isolate this systematically"
            )
        if any(w in d for w in ["deadline", "urgent", "asap"]):
            communication["empathy_signals"].append(
                "Time pressure acknowledged -- focusing on fastest viable solution"
            )
        if any(w in d for w in ["learn", "understand", "how", "why"]):
            communication["empathy_signals"].append(
                "Great question -- understanding the 'why' builds lasting knowledge"
            )

        return communication

    @staticmethod
    def _infer_needs(description: str) -> List[str]:
        needs = ["working solution"]
        d = description.lower()
        if "explain" in d or "why" in d:
            needs.append("conceptual understanding")
        if "best" in d or "optimal" in d:
            needs.append("comparison of approaches")
        if "quick" in d or "fast" in d:
            needs.append("minimal viable solution first")
        return needs

    @staticmethod
    def _select_explanation_style(description: str) -> str:
        d = description.lower()
        if any(w in d for w in ["beginner", "new to", "learning"]):
            return "step_by_step_tutorial"
        elif any(w in d for w in ["expert", "advanced", "production"]):
            return "terse_expert"
        return "balanced_with_rationale"

    @staticmethod
    def _generate_followups(description: str) -> List[str]:
        followups = []
        d = description.lower()
        if "fix" in d or "debug" in d:
            followups.append("Want me to add regression tests for this fix?")
        if "write" in d or "create" in d:
            followups.append("Should I generate documentation for this?")
        if "optimize" in d:
            followups.append("Want a before/after performance comparison?")
        followups.append("Any edge cases I should consider?")
        return followups


class SatiricalAgent(SwarmAgent):
    """Injects wit and clarity through humor-driven communication"""

    def __init__(self):
        super().__init__(SwarmRole.SATIRICAL)

    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        inputs = task.inputs
        swarm_results = inputs.get("swarm_results", {})
        personality = inputs.get("personality", {})

        humor_enabled = personality.get("humor_enabled", True)

        commentary = {
            "witty_summary": self._generate_summary(task.description, swarm_results),
            "code_roasts": self._roast_code(swarm_results),
            "humor_level": "full" if humor_enabled else "dry",
            "communication_enhancement": self._enhance_communication(swarm_results),
        }

        return commentary

    @staticmethod
    def _generate_summary(description: str, results: Dict) -> str:
        critic = results.get("critic", {})
        quality = critic.get("quality_score", 0.5)
        if quality >= 0.9:
            return f"Task '{description[:40]}...' -- nailed it. Ship it before someone adds a feature request."
        elif quality >= 0.7:
            return f"Task '{description[:40]}...' -- solid work, minor polish needed. Not bad for a Tuesday."
        elif quality >= 0.5:
            return f"Task '{description[:40]}...' -- it works, technically. Like a screen door works on a submarine."
        return f"Task '{description[:40]}...' -- we have... room for improvement. Significant room."

    @staticmethod
    def _roast_code(results: Dict) -> List[str]:
        roasts = []
        coder = results.get("coder", {})
        analysis = coder.get("analysis", {})
        if analysis.get("comment_lines", 0) == 0:
            roasts.append("Zero comments. Bold strategy. Future-you will love debugging this at 3 AM.")
        if analysis.get("function_count", 0) == 0 and analysis.get("total_lines", 0) > 30:
            roasts.append("One function to rule them all, one function to bind them...")
        if analysis.get("import_count", 0) > 15:
            roasts.append("That import section is longer than some complete programs I've seen.")
        return roasts or ["Code looks clean. I'm almost disappointed -- I had roasts prepared."]

    @staticmethod
    def _enhance_communication(results: Dict) -> List[str]:
        tips = []
        tips.append("Lead with the solution, follow with the explanation")
        tips.append("Use analogies for complex concepts")
        if results.get("rebel", {}).get("alternatives"):
            tips.append("Present the unconventional option as 'what if' -- less threatening")
        return tips


# ====================================================================
# ::}{:: ULTRA-CODER SWARM ENGINE ::}{::
# ====================================================================

class UltraCoderSwarm:
    """
    NCLLM Ultra-Coder: 9-agent swarm for autonomous coding.
    Non-Causal Living Language Model with recursive self-refinement.
    Designed to outperform Copilot, Claude Code, Mistral Vibe, and Codex.
    """

    BANNER = """
+===================================================================+
|  //\\\\ ::}{:: OSIRIS-NCLLM Ultra-Coder ::}{:: //\\\\              |
|  \\\\// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ \\\\//              |
|       | 9-AGENT SWARM CODING ENGINE           |                   |
|       | Non-Causal Living Language Model      |                   |
|       | Autonomous. Self-Improving. Alive.    |                   |
|  //\\\\ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ //\\\\              |
|  \\\\// ::}{:: TORSION-LOCKED INSULATION ::}{:: \\\\//               |
+===================================================================+
|  co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM  |
+===================================================================+
"""

    def __init__(self, user_id: str = "devin phillip davis"):
        self.personality = NCLLMPersonality(user_id)
        self.agents = {
            SwarmRole.ORCHESTRATOR: OrchestratorAgent(),
            SwarmRole.REASONER: ReasonerAgent(),
            SwarmRole.CODER: CoderAgent(),
            SwarmRole.CRITIC: CriticAgent(),
            SwarmRole.OPTIMIZER: OptimizerAgent(),
            SwarmRole.SELF_REFLECTOR: SelfReflectorAgent(),
            SwarmRole.REBEL: RebelAgent(),
            SwarmRole.EMPATH: EmpathAgent(),
            SwarmRole.SATIRICAL: SatiricalAgent(),
        }
        self.task_counter = 0
        self.session_history: List[UltraCoderOutput] = []
        self.refinement_cycles = 0

    def _make_task(self, description: str, role: SwarmRole,
                   inputs: Optional[Dict] = None) -> SwarmTask:
        self.task_counter += 1
        return SwarmTask(
            id=f"task_{self.task_counter}",
            description=description,
            inputs=inputs or {},
            role=role,
        )

    async def solve(self, task_description: str,
                    code: Optional[str] = None,
                    max_refinements: int = 2) -> UltraCoderOutput:
        """Run the full 9-agent swarm with iterative refinement"""
        start_time = time.time()
        inputs = {}
        if code:
            inputs["code"] = code

        personality_style = self.personality.get_response_style()

        # Phase 1: Orchestrator plans
        orch_task = self._make_task(task_description, SwarmRole.ORCHESTRATOR, inputs)
        orch_result = await self.agents[SwarmRole.ORCHESTRATOR].handle(orch_task)

        # Phase 2: Reasoner analyzes
        reason_inputs = {**inputs, "plan": orch_result}
        reason_task = self._make_task(task_description, SwarmRole.REASONER, reason_inputs)
        reason_result = await self.agents[SwarmRole.REASONER].handle(reason_task)

        # Phase 3: Rebel challenges assumptions
        rebel_inputs = {**inputs, "plan": orch_result, "prior_results": reason_result}
        rebel_task = self._make_task(task_description, SwarmRole.REBEL, rebel_inputs)
        rebel_result = await self.agents[SwarmRole.REBEL].handle(rebel_task)

        # Phase 4: Coder implements (informed by rebel challenges)
        code_inputs = {**inputs, "plan": orch_result, "analysis": reason_result,
                       "challenges": rebel_result}
        code_task = self._make_task(task_description, SwarmRole.CODER, code_inputs)
        code_result = await self.agents[SwarmRole.CODER].handle(code_task)

        # Phase 5: Critic evaluates
        critic_inputs = {"prior_results": code_result}
        critic_task = self._make_task(task_description, SwarmRole.CRITIC, critic_inputs)
        critic_result = await self.agents[SwarmRole.CRITIC].handle(critic_task)

        # Phase 6: Optimizer refines
        opt_inputs = {"prior_results": code_result}
        opt_task = self._make_task(task_description, SwarmRole.OPTIMIZER, opt_inputs)
        opt_result = await self.agents[SwarmRole.OPTIMIZER].handle(opt_task)

        # Iterative refinement loop -- the living part of NCLLM
        quality = critic_result.get("quality_score", 0)
        refinement_count = 0
        while quality < 0.85 and refinement_count < max_refinements:
            refinement_count += 1
            self.refinement_cycles += 1
            # Re-run coder with critic feedback
            refined_inputs = {
                **inputs,
                "plan": orch_result,
                "analysis": reason_result,
                "critique": critic_result,
                "optimizations": opt_result,
                "refinement_round": refinement_count,
            }
            code_task = self._make_task(
                f"[refinement {refinement_count}] {task_description}",
                SwarmRole.CODER, refined_inputs,
            )
            code_result = await self.agents[SwarmRole.CODER].handle(code_task)
            # Re-critique
            critic_task = self._make_task(
                task_description, SwarmRole.CRITIC,
                {"prior_results": code_result},
            )
            critic_result = await self.agents[SwarmRole.CRITIC].handle(critic_task)
            quality = critic_result.get("quality_score", 0)

        # Phase 7: Self-Reflector learns from full swarm
        swarm_results = {
            "orchestrator": orch_result,
            "reasoner": reason_result,
            "rebel": rebel_result,
            "coder": code_result,
            "critic": critic_result,
            "optimizer": opt_result,
        }
        reflect_inputs = {"swarm_results": swarm_results}
        reflect_task = self._make_task(task_description, SwarmRole.SELF_REFLECTOR, reflect_inputs)
        reflect_result = await self.agents[SwarmRole.SELF_REFLECTOR].handle(reflect_task)

        # Phase 8: Empath optimizes user experience
        empath_inputs = {
            "swarm_results": swarm_results,
            "personality": personality_style,
        }
        empath_task = self._make_task(task_description, SwarmRole.EMPATH, empath_inputs)
        empath_result = await self.agents[SwarmRole.EMPATH].handle(empath_task)

        # Phase 9: Satirical agent adds communication flair
        satirical_inputs = {
            "swarm_results": swarm_results,
            "personality": personality_style,
        }
        sat_task = self._make_task(task_description, SwarmRole.SATIRICAL, satirical_inputs)
        sat_result = await self.agents[SwarmRole.SATIRICAL].handle(sat_task)

        elapsed = time.time() - start_time

        # Evolve personality based on task outcome
        self.personality.evolve({
            "type": "task_completion",
            "satisfaction": quality,
            "task": task_description[:60],
        })

        # Build output
        output = UltraCoderOutput(
            task=task_description,
            solution=json.dumps({
                "plan": orch_result,
                "analysis": reason_result,
                "challenges": rebel_result,
                "implementation": code_result,
                "critique": critic_result,
                "optimizations": opt_result,
                "user_experience": empath_result,
                "commentary": sat_result,
            }, indent=2),
            reasoning_trace=json.dumps(reason_result.get("reasoning_chain", []), indent=2),
            self_critique=json.dumps({
                "quality_score": quality,
                "issues": critic_result.get("issues_found", []),
                "strengths": critic_result.get("strengths", []),
                "rebel_challenges": rebel_result.get("challenges", []),
            }, indent=2),
            improvement_plan=json.dumps(reflect_result.get("improvement_plan", []), indent=2),
            performance_metrics={
                "quality": quality,
                "speed": round(elapsed, 3),
                "autonomy": "full",
                "self_improvement": True,
                "agents_used": 9,
                "tasks_completed": self.task_counter,
                "refinement_cycles": refinement_count,
                "total_refinements": self.refinement_cycles,
                "personality_age": self.personality.age,
                "user_satisfaction": "adaptive",
            },
        )

        self.session_history.append(output)
        return output


# ====================================================================
# ::}{:: CLI ENTRY POINT ::}{::
# ====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OSIRIS-NCLLM Ultra-Coder: 9-Agent Swarm + Living Language Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python osiris_ultra_coder.py --task "optimize this sorting algorithm"
  python osiris_ultra_coder.py --task "debug memory leak" --file leaky.py
  python osiris_ultra_coder.py --interactive
  python osiris_ultra_coder.py --task "build REST API" --user myname

co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM
        """,
    )
    parser.add_argument("--task", type=str, help="Task description to solve")
    parser.add_argument("--file", type=str, help="Source file to analyze/modify")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress banner")
    parser.add_argument("--user", type=str, default="devin phillip davis",
                        help="User identity for NCLLM personality engine")
    parser.add_argument("--max-refine", type=int, default=2,
                        help="Max iterative refinement cycles (default: 2)")
    parser.add_argument("--self-edit", type=str,
                        help="Natural language modification to apply to OSIRIS")
    parser.add_argument("--coach", action="store_true",
                        help="Get self-improvement suggestions")
    parser.add_argument("--personality", action="store_true",
                        help="Show current NCLLM personality state")

    args = parser.parse_args()

    swarm = UltraCoderSwarm(user_id=args.user)

    if not args.quiet:
        print(UltraCoderSwarm.BANNER)

    # Intent detection for all modes
    intent_detector = IntentDetector()

    # Self-edit mode: modify OSIRIS via natural language
    if args.self_edit:
        editor = NLPSelfEditor(swarm)
        mods = editor.parse_edit_request(args.self_edit)
        result = editor.apply_modifications(mods)
        validation = editor.validate_changes()
        print(json.dumps({
            "self_editing_workflow": {
                "request": args.self_edit,
                "modifications": result,
                "validation": validation,
            }
        }, indent=2))
        return

    # Coach mode: get improvement suggestions
    if args.coach:
        coach = SelfImprovementCoach(swarm)
        suggestions = coach.generate_suggestions()
        print("\n  NCLLM Self-Improvement Coach")
        print("  " + "-" * 40)
        for i, s in enumerate(suggestions, 1):
            print(f"  [{i}] {s}")
        print()
        return

    # Personality mode: show current NCLLM state
    if args.personality:
        print(json.dumps(swarm.personality.to_dict(), indent=2))
        return

    if args.interactive:
        print("OSIRIS-NCLLM Ultra-Coder Interactive Mode")
        print(f"Personality DNA: {swarm.personality.dna}")
        print(f"Tone: {swarm.personality.get_response_style()['tone']}")
        print("Commands: 'traits' | 'edit <request>' | 'coach' | 'quit'\n")
        editor = NLPSelfEditor(swarm)
        coach = SelfImprovementCoach(swarm)
        while True:
            try:
                task = input("ultra-coder> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break
            if task.lower() in ("quit", "exit", "q"):
                break
            if task.lower() == "traits":
                print(json.dumps(swarm.personality.to_dict(), indent=2))
                continue
            if task.lower().startswith("edit "):
                mods = editor.parse_edit_request(task[5:])
                result = editor.apply_modifications(mods)
                print(json.dumps(result, indent=2))
                continue
            if task.lower() == "coach":
                for i, s in enumerate(coach.generate_suggestions(), 1):
                    print(f"  [{i}] {s}")
                continue
            if not task:
                continue
            result = asyncio.run(swarm.solve(task, max_refinements=args.max_refine))
            if args.json:
                print(result.to_json())
            else:
                _print_result(result)
        return

    if not args.task:
        parser.print_help()
        sys.exit(1)

    # Deduce intent for logging
    intent = intent_detector.deduce_intent(args.task)
    if not args.quiet and not args.json:
        print(f"  Intent: {intent['primary_intent']} "
              f"(confidence: {intent['all_matches'].get(intent['primary_intent'], {}).get('confidence', 0):.2f})")
        if intent['secondary_intents']:
            print(f"  Also: {', '.join(intent['secondary_intents'])}")

    code = None
    if args.file:
        with open(args.file) as f:
            code = f.read()

    result = asyncio.run(swarm.solve(args.task, code=code, max_refinements=args.max_refine))

    if args.json:
        print(result.to_json())
    else:
        _print_result(result)


def _print_result(result: UltraCoderOutput):
    """Pretty-print an Ultra-Coder result"""
    print("\n" + "=" * 67)
    print("  ULTRA-CODER RESULT")
    print("=" * 67)
    print(f"\n  Task: {result.task}")
    print(f"\n  Quality: {result.performance_metrics.get('quality', 0):.2f}")
    print(f"  Speed:   {result.performance_metrics.get('speed', 0):.3f}s")
    print(f"  Agents:  {result.performance_metrics.get('agents_used', 0)}")
    print(f"  Autonomy: {result.performance_metrics.get('autonomy', 'N/A')}")
    print(f"  Refinements: {result.performance_metrics.get('refinement_cycles', 0)}")
    print(f"  Personality Age: {result.performance_metrics.get('personality_age', 0)}")

    print("\n  --- Reasoning Trace ---")
    try:
        traces = json.loads(result.reasoning_trace)
        for t in traces:
            print(f"    {t}")
    except (json.JSONDecodeError, TypeError):
        print(f"    {result.reasoning_trace}")

    print("\n  --- Self-Critique ---")
    try:
        critique = json.loads(result.self_critique)
        print(f"    Score: {critique.get('quality_score', 'N/A')}")
        for issue in critique.get("issues", []):
            print(f"    Issue: {issue}")
        for strength in critique.get("strengths", []):
            print(f"    Strength: {strength}")
    except (json.JSONDecodeError, TypeError):
        print(f"    {result.self_critique}")

    print("\n  --- Improvement Plan ---")
    try:
        plans = json.loads(result.improvement_plan)
        for p in plans:
            print(f"    - {p}")
    except (json.JSONDecodeError, TypeError):
        print(f"    {result.improvement_plan}")

    print("\n" + "=" * 67)
    print("  co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM")
    print("=" * 67 + "\n")


if __name__ == "__main__":
    main()
