#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import re
import sys
import logging
import random
import time
import math
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from pathlib import Path
import networkx as nx
import numpy as np
from collections import deque

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("osiris")

# Paths and SDK setup
REPO_ROOT = Path(__file__).parent.resolve()
SDK_PATH = REPO_ROOT / "copilot-sdk-dnalang" / "src"
HISTORY_FILE = REPO_ROOT / ".osiris_history.jsonl"
CONFIG_DIR = REPO_ROOT / ".config"
STATE_DIR = REPO_ROOT / ".osiris_state"
AUTOADVANCE_DIR = REPO_ROOT / ".autoadvance"
VERSION = "0.54.0"  # Updated version with auto-enhance and auto-advance

# Ensure required directories exist
CONFIG_DIR.mkdir(exist_ok=True, parents=True)
STATE_DIR.mkdir(exist_ok=True, parents=True)
AUTOADVANCE_DIR.mkdir(exist_ok=True, parents=True)

# Add our enhanced NCLM components to path
ENHANCED_NCLM_PATH = REPO_ROOT / "nclm"
sys.path.insert(0, str(ENHANCED_NCLM_PATH))

from nclm.enhanced_config import NCLMEnhancedConfig, NCLMMode
from nclm.enhanced_client import EnhancedDNALangCopilotClient
from nclm.quantum_cognitive import QuantumCognitiveProcessor
from nclm.deep_understanding import DeepUnderstandingProcessor

def validate_sdk() -> None:
    """Validate that the SDK is available"""
    if not SDK_PATH.exists():
        logger.error("Missing copilot-sdk-dnalang package directory at: %s", SDK_PATH)
        logger.error("Please ensure the package is properly installed.")
        sys.exit(1)

def get_zenodo_token() -> str:
    """Get Zenodo token from environment or config file"""
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        config_file = CONFIG_DIR / "zenodo.json"
        if config_file.exists():
            with open(config_file, "r") as f:
                try:
                    config = json.load(f)
                    token = config.get("token")
                except json.JSONDecodeError:
                    pass

    if not token:
        raise EnvironmentError(
            "Zenodo token not found. Set ZENODO_TOKEN environment variable or "
            f"create config file at {CONFIG_DIR}/zenodo.json"
        )
    return token

def normalize_prompt(prompt: str) -> str:
    """Sanitize prompt text (line breaks preserved, history markers removed)."""
    prompt = prompt.replace("!", "\u00A1") if "!" in prompt else prompt
    prompt = re.sub(r"[ \t]+", " ", prompt).strip()[:20000]
    return prompt

def append_history(entry: Dict[str, Any]) -> None:
    """Append entry to history file with error handling"""
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")
    except Exception as exc:
        logger.warning(f"Failed to persist history: {exc}")

def load_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Load history from file with proper error handling"""
    if not HISTORY_FILE.exists():
        return []

    history = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        history.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        logger.debug(f"Skipping malformed history entry: {exc}")
    except Exception as exc:
        logger.error(f"Failed to load history: {exc}")

    return history[-limit:]

async def create_nclm_client() -> EnhancedDNALangCopilotClient:
    """Create and configure the enhanced NCLM client"""
    # Load or create default config
    config_path = CONFIG_DIR / "nclm_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            config = NCLMEnhancedConfig.from_dict(config_data)
        except Exception as e:
            logger.warning(f"Failed to load NCLM config: {e}. Using defaults.")
            config = NCLMEnhancedConfig()
    else:
        config = NCLMEnhancedConfig()

    # Create client with persistent state
    client = EnhancedDNALangCopilotClient(
        config=config,
        state_dir=STATE_DIR,
        enable_intent_engine=True,
        enable_quantum=True
    )

    return client

class AutoEnhanceEngine:
    """Engine for automatically enhancing prompts and responses"""

    def __init__(self, client: EnhancedDNALangCopilotClient):
        self.client = client
        self.enhancement_history = deque(maxlen=10)
        self.feedback_loop = []
        self.enhancement_strategies = [
            self._enhance_with_memory,
            self._enhance_with_quantum,
            self._enhance_with_domain_knowledge,
            self._enhance_with_cognitive_metrics,
            self._enhance_with_structured_thinking
        ]

    async def auto_enhance_prompt(self, prompt: str, iterations: int = 3) -> Dict:
        """Automatically enhance a prompt through multiple iterations"""
        original_prompt = prompt
        current_prompt = prompt
        enhancement_chain = []

        for i in range(iterations):
            logger.info(f"Auto-enhancement iteration {i+1}/{iterations}")

            # Analyze current prompt
            analysis = await self.client.cognitive_analysis(current_prompt)
            if analysis.get("status") != "success":
                logger.warning(f"Failed to analyze prompt in iteration {i+1}")
                break

            # Select enhancement strategy based on analysis
            strategy = self._select_enhancement_strategy(analysis)
            enhanced = await strategy(current_prompt, analysis)

            # Store enhancement step
            enhancement_chain.append({
                "iteration": i+1,
                "original": current_prompt,
                "enhanced": enhanced,
                "strategy": strategy.__name__,
                "analysis": analysis.get("analysis", {})
            })

            current_prompt = enhanced
            self.enhancement_history.append(enhanced)

        # Generate final enhanced prompt with full context
        final_enhanced = await self._generate_final_enhanced_prompt(
            original_prompt, current_prompt, enhancement_chain
        )

        return {
            "original_prompt": original_prompt,
            "final_enhanced_prompt": final_enhanced,
            "enhancement_chain": enhancement_chain,
            "metrics": self._calculate_enhancement_metrics(enhancement_chain)
        }

    def _select_enhancement_strategy(self, analysis: Dict) -> callable:
        """Select the most appropriate enhancement strategy based on analysis"""
        intent = analysis.get("analysis", {}).get("intent_analysis", {})
        metrics = analysis.get("analysis", {}).get("cognitive_metrics", {})

        # If coherence is low, focus on structured enhancement
        if metrics.get("coherence_lambda", 0) < 0.6:
            return self._enhance_with_structured_thinking

        # If quantum entanglement is high, enhance with quantum processing
        if client.enable_quantum and metrics.get("quantum_entanglement", 0) > 0.5:
            return self._enhance_with_quantum

        # If we have relevant memory, use memory enhancement
        memory_stats = analysis.get("analysis", {}).get("memory_stats", {})
        if memory_stats.get("working_memory_count", 0) > 3:
            return self._enhance_with_memory

        # If we have domain knowledge, use that
        domains = intent.get("domains", [])
        if domains:
            return self._enhance_with_domain_knowledge

        # Default to cognitive metrics enhancement
        return self._enhance_with_cognitive_metrics

    async def _enhance_with_memory(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using relevant memories"""
        # Get relevant memories
        memories = await self._get_relevant_memories(prompt)

        if not memories:
            return prompt

        # Add memory context to prompt
        memory_context = "\n[MEMORY CONTEXT]\n"
        for i, memory in enumerate(memories[:3], 1):
            memory_context += f"Memory {i}: {memory[:150]}...\n"

        return f"{prompt}\n\n{memory_context}\n[ENHANCED PROMPT]\n{prompt}"

    async def _get_relevant_memories(self, prompt: str) -> List[str]:
        """Get relevant memories for prompt enhancement"""
        # In a real implementation, this would query the memory system
        # For now, we'll simulate with some generic memories
        return [
            f"Previous analysis of similar quantum-cognitive relationships showed entanglement patterns",
            f"Memory of processing {prompt[:30]}... revealed coherence score of 0.85",
            f"Related concept exploration identified key connections between quantum states and cognitive processes"
        ]

    async def _enhance_with_quantum(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using quantum cognitive processing"""
        quantum_analysis = analysis.get("analysis", {}).get("quantum_analysis", {})

        if not client.enable_quantum or not quantum_analysis:
            return prompt

        # Get top quantum concepts
        measurements = quantum_analysis.get("quantum_measurements", [])
        top_concepts = sorted(measurements, key=lambda x: -x["post_probability"])[:3]

        quantum_context = "\n[QUANTUM COGNITIVE CONTEXT]\n"
        for concept in top_concepts:
            quantum_context += (
                f"- {concept['concept']}: "
                f"Probability={concept['post_probability']:.3f}, "
                f"State={concept['state']}\n"
            )

        # Add quantum processing instructions
        quantum_context += "\n[QUANTUM PROCESSING INSTRUCTIONS]\n"
        quantum_context += (
            "- Consider concepts in superposition with probabilities as weights\n"
            "- Explore entangled relationships between concepts\n"
            "- Apply quantum-inspired reasoning with current entanglement strength\n"
        )

        return f"{prompt}\n\n{quantum_context}\n[ENHANCED PROMPT]\n{prompt}"

    async def _enhance_with_domain_knowledge(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using domain-specific knowledge"""
        intent = analysis.get("analysis", {}).get("intent_analysis", {})
        domains = intent.get("domains", [])

        if not domains:
            return prompt

        domain_context = "\n[DOMAIN KNOWLEDGE CONTEXT]\n"
        for domain in domains[:2]:  # Limit to top 2 domains
            domain_context += f"Domain: {domain}\n"

            # Get domain concepts (simulated)
            if domain == "quantum":
                concepts = ["superposition", "entanglement", "qubit", "decoherence"]
            elif domain == "cognitive":
                concepts = ["memory", "attention", "reasoning", "understanding"]
            else:
                concepts = ["analysis", "model", "theory", "application"]

            domain_context += f"Key concepts: {', '.join(concepts)}\n"

        return f"{prompt}\n\n{domain_context}\n[ENHANCED PROMPT]\n{prompt}"

    async def _enhance_with_cognitive_metrics(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using cognitive metrics"""
        metrics = analysis.get("analysis", {}).get("cognitive_metrics", {})
        intent = analysis.get("analysis", {}).get("intent_analysis", {})

        cognitive_context = "\n[COGNITIVE METRICS CONTEXT]\n"
        cognitive_context += f"- Coherence (Λ): {metrics.get('coherence_lambda', 0):.3f}\n"
        cognitive_context += f"- Consciousness (Φ): {metrics.get('consciousness_phi', 0):.3f}\n"
        cognitive_context += f"- Cognitive Load: {metrics.get('cognitive_load', 0):.3f}\n"

        if client.enable_quantum:
            cognitive_context += f"- Quantum Entanglement: {metrics.get('quantum_entanglement', 0):.3f}\n"

        # Add processing instructions based on metrics
        cognitive_context += "\n[COGNITIVE PROCESSING INSTRUCTIONS]\n"

        if metrics.get("coherence_lambda", 0) < 0.7:
            cognitive_context += "- Focus on establishing clearer logical connections\n"
        else:
            cognitive_context += "- Maintain high coherence in reasoning\n"

        if metrics.get("consciousness_phi", 0) < 0.7:
            cognitive_context += "- Work on integrating concepts into unified framework\n"
        else:
            cognitive_context += "- Leverage well-integrated conceptual understanding\n"

        if metrics.get("cognitive_load", 0) > 0.8:
            cognitive_context += "- Break complex ideas into manageable parts\n"
        else:
            cognitive_context += "- Comprehensive analysis is feasible with current load\n"

        return f"{prompt}\n\n{cognitive_context}\n[ENHANCED PROMPT]\n{prompt}"

    async def _enhance_with_structured_thinking(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using structured thinking frameworks"""
        intent = analysis.get("analysis", {}).get("intent_analysis", {})
        domains = intent.get("domains", [])
        actions = intent.get("actions", [])

        structured_context = "\n[STRUCTURED THINKING FRAMEWORK]\n"

        # Select appropriate framework based on intent
        if "quantum" in " ".join(domains).lower():
            structured_context += "Quantum-Cognitive Analysis Framework:\n"
            structured_context += (
                "1. Identify quantum principles relevant to cognitive processes\n"
                "2. Map quantum states to cognitive concepts\n"
                "3. Analyze entanglement relationships\n"
                "4. Evaluate superposition effects on reasoning\n"
                "5. Synthesize quantum-cognitive model\n"
            )
        elif any(a.lower() in ["explain", "describe"] for a in actions):
            structured_context += "Explanatory Structure Framework:\n"
            structured_context += (
                "1. Define key terms and concepts\n"
                "2. Establish foundational principles\n"
                "3. Build logical connections\n"
                "4. Provide illustrative examples\n"
                "5. Summarize key insights\n"
            )
        else:
            structured_context += "General Analytical Framework:\n"
            structured_context += (
                "1. Problem decomposition\n"
                "2. Conceptual analysis\n"
                "3. Relationship mapping\n"
                "4. Pattern identification\n"
                "5. Synthesis and conclusion\n"
            )

        return f"{prompt}\n\n{structured_context}\n[ENHANCED PROMPT]\n{prompt}"

    async def _generate_final_enhanced_prompt(self, original: str, current: str,
                                             chain: List[Dict]) -> str:
        """Generate the final enhanced prompt with full context"""
        final_prompt = f"""[AUTO-ENHANCED PROMPT]

Original Prompt: {original}

Enhancement Journey:
"""

        # Add enhancement steps
        for i, step in enumerate(chain, 1):
            final_prompt += f"{i}. {step['strategy'].replace('_', ' ').title()}:\n"
            final_prompt += f"   - Added context about {step['strategy'].split('_')[-1]}\n"

        # Add cognitive processing instructions
        final_prompt += """
[COGNITIVE PROCESSING INSTRUCTIONS]
- Integrate all enhancement layers in analysis
- Maintain coherence across expanded context
- Leverage quantum-cognitive insights where applicable
- Apply structured thinking frameworks
- Generate comprehensive, multi-perspective response

[FINAL ENHANCED PROMPT]
"""

        final_prompt += current
        return final_prompt

    def _calculate_enhancement_metrics(self, chain: List[Dict]) -> Dict:
        """Calculate metrics about the enhancement process"""
        if not chain:
            return {
                "iterations": 0,
                "strategies_used": 0,
                "coherence_improvement": 0,
                "complexity_increase": 0
            }

        # Calculate metrics
        initial_coherence = chain[0]["analysis"].get("cognitive_metrics", {}).get("coherence_lambda", 0)
        final_coherence = chain[-1]["analysis"].get("cognitive_metrics", {}).get("coherence_lambda", 0)

        initial_length = len(chain[0]["original"])
        final_length = len(chain[-1]["enhanced"])

        strategies_used = len(set(step["strategy"] for step in chain))

        return {
            "iterations": len(chain),
            "strategies_used": strategies_used,
            "coherence_improvement": final_coherence - initial_coherence,
            "complexity_increase": (final_length - initial_length) / max(1, initial_length),
            "unique_strategies": list(set(step["strategy"] for step in chain))
        }

class AutoAdvanceEngine:
    """Engine for automatically advancing understanding through iterative refinement"""

    def __init__(self, client: EnhancedDNALangCopilotClient):
        self.client = client
        self.advance_history = []
        self.knowledge_graph = nx.DiGraph()
        self.current_session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.auto_enhance_engine = AutoEnhanceEngine(client)

    async def auto_advance(self, initial_prompt: str, iterations: int = 5,
                          exploration_depth: int = 3) -> Dict:
        """Automatically advance understanding through iterative refinement"""
        session_dir = AUTOADVANCE_DIR / f"session_{self.current_session_id}"
        session_dir.mkdir(exist_ok=True, parents=True)

        current_prompt = initial_prompt
        advance_chain = []
        knowledge_nodes = set()

        for i in range(iterations):
            logger.info(f"Auto-advance iteration {i+1}/{iterations}")

            # Store current state
            iteration_dir = session_dir / f"iteration_{i+1}"
            iteration_dir.mkdir(exist_ok=True)

            # Analyze current prompt
            analysis = await self.client.cognitive_analysis(current_prompt)
            if analysis.get("status") != "success":
                logger.warning(f"Analysis failed in iteration {i+1}")
                break

            # Auto-enhance the prompt
            enhanced = await self.auto_enhance_engine.auto_enhance_prompt(current_prompt)
            current_prompt = enhanced["final_enhanced_prompt"]

            # Perform deep understanding
            deep_result = await self.client.deep_understand(current_prompt, max_depth=exploration_depth)

            # Extract knowledge and update graph
            new_concepts = self._extract_new_concepts(deep_result, knowledge_nodes)
            self._update_knowledge_graph(deep_result, new_concepts)

            # Generate refinement questions
            questions = self._generate_refinement_questions(deep_result, i, iterations)

            # Select most promising question for next iteration
            if i < iterations - 1:  # Don't generate next prompt for last iteration
                next_prompt = await self._generate_next_prompt(current_prompt, questions, deep_result)
            else:
                next_prompt = current_prompt

            # Save iteration results
            iteration_result = {
                "iteration": i+1,
                "prompt": current_prompt,
                "analysis": analysis.get("analysis", {}),
                "deep_understanding": deep_result,
                "new_concepts": list(new_concepts),
                "refinement_questions": questions,
                "next_prompt": next_prompt,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # Save to file
            with open(iteration_dir / "results.json", "w") as f:
                json.dump(iteration_result, f, indent=2)

            advance_chain.append(iteration_result)
            current_prompt = next_prompt

            # Check for convergence
            if self._check_convergence(advance_chain):
                logger.info(f"Convergence detected at iteration {i+1}")
                break

        # Generate final report
        final_report = await self._generate_final_report(advance_chain, initial_prompt, current_prompt)

        # Save session manifest
        manifest = {
            "session_id": self.current_session_id,
            "initial_prompt": initial_prompt,
            "final_prompt": current_prompt,
            "iterations": len(advance_chain),
            "timestamps": {
                "start": advance_chain[0]["timestamp"] if advance_chain else datetime.utcnow().isoformat() + "Z",
                "end": datetime.utcnow().isoformat() + "Z"
            },
            "knowledge_graph": {
                "nodes": list(self.knowledge_graph.nodes()),
                "edges": [
                    {"source": u, "target": v, "data": self.knowledge_graph.edges[u, v]}
                    for u, v in self.knowledge_graph.edges()
                ],
                "metrics": {
                    "nodes": self.knowledge_graph.number_of_nodes(),
                    "edges": self.knowledge_graph.number_of_edges(),
                    "density": nx.density(self.knowledge_graph),
                    "average_degree": sum(dict(self.knowledge_graph.degree()).values()) / max(1, self.knowledge_graph.number_of_nodes())
                }
            },
            "final_report": final_report
        }

        with open(session_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Update session ID for next run
        self.current_session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

        return {
            "status": "success",
            "session_id": manifest["session_id"],
            "initial_prompt": initial_prompt,
            "final_prompt": current_prompt,
            "iterations": len(advance_chain),
            "knowledge_graph": manifest["knowledge_graph"],
            "final_report": final_report,
            "session_dir": str(session_dir),
            "advance_chain": [ac["iteration"] for ac in advance_chain]
        }

    def _extract_new_concepts(self, deep_result: Dict, known_concepts: Set[str]) -> Set[str]:
        """Extract new concepts from deep understanding results"""
        new_concepts = set()

        # Get concepts from deep understanding
        concept_graph = deep_result.get("concept_graph", {})
        all_concepts = set(concept_graph.get("nodes", []))

        # Get concepts from quantum analysis
        if client.enable_quantum:
            quantum_analysis = deep_result.get("quantum_analysis", {})
            quantum_concepts = {
                m["concept"] for m in quantum_analysis.get("quantum_measurements", [])
            }
            all_concepts.update(quantum_concepts)

        # Identify new concepts
        for concept in all_concepts:
            if concept not in known_concepts:
                new_concepts.add(concept)

        return new_concepts

    def _update_knowledge_graph(self, deep_result: Dict, new_concepts: Set[str]) -> None:
        """Update the knowledge graph with new information"""
        # Add new concepts as nodes
        for concept in new_concepts:
            if concept not in self.knowledge_graph:
                self.knowledge_graph.add_node(concept, type="concept")

        # Add relationships from deep understanding
        concept_graph = deep_result.get("concept_graph", {})
        for edge in concept_graph.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            weight = edge["weight"]

            if self.knowledge_graph.has_edge(source, target):
                # Update existing edge
                current_weight = self.knowledge_graph.edges[source, target]["weight"]
                self.knowledge_graph.edges[source, target]["weight"] = max(current_weight, weight)
            else:
                # Add new edge
                self.knowledge_graph.add_edge(
                    source, target,
                    weight=weight,
                    type=edge.get("type", "relationship")
                )

        # Add temporal relationship to previous concepts
        if self.knowledge_graph.nodes():
            latest_concept = list(new_concepts)[0] if new_concepts else None
            if latest_concept:
                # Find most central existing concept
                central_concepts = sorted(
                    self.knowledge_graph.degree(), key=lambda x: -x[1]
                )[:3]

                for concept, degree in central_concepts:
                    if concept != latest_concept and self.knowledge_graph.has_node(concept):
                        self.knowledge_graph.add_edge(
                            concept, latest_concept,
                            weight=0.5,
                            type="temporal"
                        )

    def _generate_refinement_questions(self, deep_result: Dict, current_iter: int,
                                       total_iter: int) -> List[str]:
        """Generate questions to refine understanding"""
        questions = []
        metrics = deep_result.get("metrics", {})
        intent = deep_result.get("intent_analysis", {})
        concepts = deep_result.get("concept_graph", {}).get("nodes", [])

        # Questions based on metrics
        if metrics.get("coherence", 0) < 0.7:
            questions.append(
                f"What are the missing connections needed to improve coherence (Λ={metrics.get('coherence', 0):.2f})?"
            )

        if metrics.get("consciousness", 0) < 0.7:
            questions.append(
                f"How can we better integrate these concepts to improve consciousness (Φ={metrics.get('consciousness', 0):.2f})?"
            )

        if client.enable_quantum and metrics.get("quantum_entanglement", 0) < 0.5:
            questions.append(
                "Which concepts should be more strongly entangled to better model their relationships?"
            )

        # Questions based on concepts
        if concepts:
            sample_concepts = random.sample(concepts, min(3, len(concepts)))
            for concept in sample_concepts:
                questions.append(f"What deeper insights can we gain about {concept}?")

        # Questions based on iteration progress
        if current_iter < total_iter // 2:
            questions.append("What foundational principles need more exploration?")
        else:
            questions.append("What higher-level syntheses can we develop from current understanding?")

        # Domain-specific questions
        domains = intent.get("domains", [])
        if "quantum" in " ".join(domains).lower():
            questions.append(
                "How do quantum principles specifically inform our understanding of this topic?"
            )

        if "cognitive" in " ".join(domains).lower():
            questions.append(
                "What cognitive mechanisms best explain the observed patterns?"
            )

        return questions[:5]  # Return top 5 questions

    async def _generate_next_prompt(self, current_prompt: str, questions: List[str],
                                   deep_result: Dict) -> str:
        """Generate the next prompt for auto-advance"""
        if not questions:
            return current_prompt

        # Select the most promising question based on metrics
        metrics = deep_result.get("metrics", {})
        selected_question = questions[0]  # Default to first question

        # If coherence is low, prioritize connection questions
        if metrics.get("coherence", 0) < 0.6:
            connection_questions = [
                q for q in questions
                if any(word in q.lower() for word in ["connection", "relationship", "link"])
            ]
            if connection_questions:
                selected_question = connection_questions[0]

        # If consciousness is low, prioritize integration questions
        elif metrics.get("consciousness", 0) < 0.6:
            integration_questions = [
                q for q in questions
                if any(word in q.lower() for word in ["integrate", "unify", "synthesize"])
            ]
            if integration_questions:
                selected_question = integration_questions[0]

        # Generate enhanced prompt with the selected question
        enhanced_prompt = f"""[AUTO-ADVANCE ITERATION]

Current Understanding Context:
{current_prompt}

Key Insights from Analysis:
- Coherence (Λ): {metrics.get('coherence', 0):.3f}
- Consciousness (Φ): {metrics.get('consciousness', 0):.3f}
- Quantum Entanglement: {metrics.get('quantum_entanglement', 0):.3f}

Refinement Focus:
{selected_question}

[NEXT ITERATION PROMPT]
"""

        # Auto-enhance the new prompt
        enhanced = await self.auto_enhance_engine.auto_enhance_prompt(
            f"{current_prompt}\n\n{selected_question}", iterations=2
        )

        return enhanced["final_enhanced_prompt"]

    def _check_convergence(self, advance_chain: List[Dict]) -> bool:
        """Check if the auto-advance process has converged"""
        if len(advance_chain) < 3:
            return False

        # Check metric stability
        metrics = [step["deep_understanding"]["metrics"] for step in advance_chain[-3:]]

        coherence_values = [m.get("coherence", 0) for m in metrics]
        consciousness_values = [m.get("consciousness", 0) for m in metrics]

        coherence_stable = max(coherence_values) - min(coherence_values) < 0.05
        consciousness_stable = max(consciousness_values) - min(consciousness_values) < 0.05

        # Check if we're getting diminishing returns on new concepts
        new_concepts = [len(step["new_concepts"]) for step in advance_chain[-3:]]
        concept_growth_stable = max(new_concepts) - min(new_concepts) < 2

        return coherence_stable and consciousness_stable and concept_growth_stable

    async def _generate_final_report(self, advance_chain: List[Dict],
                                    initial_prompt: str, final_prompt: str) -> Dict:
        """Generate a comprehensive final report"""
        report = {
            "summary": self._generate_summary_report(advance_chain, initial_prompt, final_prompt),
            "knowledge_graph": self._generate_graph_report(),
            "metric_trends": self._generate_metric_trends(advance_chain),
            "key_insights": self._generate_key_insights(advance_chain),
            "recommendations": self._generate_final_recommendations(advance_chain)
        }

        return report

    def _generate_summary_report(self, advance_chain: List[Dict],
                                initial_prompt: str, final_prompt: str) -> str:
        """Generate a summary of the auto-advance process"""
        summary = []
        summary.append("AUTO-ADVANCE SUMMARY REPORT")
        summary.append("=" * 50)
        summary.append(f"\nInitial Prompt: {initial_prompt}")
        summary.append(f"Final Prompt Length: {len(final_prompt)} characters")
        summary.append(f"Iterations Completed: {len(advance_chain)}")

        # Calculate metrics improvement
        initial_metrics = advance_chain[0]["deep_understanding"]["metrics"]
        final_metrics = advance_chain[-1]["deep_understanding"]["metrics"]

        coherence_improvement = final_metrics.get("coherence", 0) - initial_metrics.get("coherence", 0)
        consciousness_improvement = final_metrics.get("consciousness", 0) - initial_metrics.get("consciousness", 0)

        summary.append(f"\nMetric Improvements:")
        summary.append(f"- Coherence (Λ): {coherence_improvement:+.3f}")
        summary.append(f"- Consciousness (Φ): {consciousness_improvement:+.3f}")

        # Key concepts discovered
        all_concepts = set()
        for step in advance_chain:
            all_concepts.update(step.get("new_concepts", []))

        summary.append(f"\nKey Concepts Discovered: {len(all_concepts)}")
        top_concepts = sorted(
            all_concepts,
            key=lambda c: sum(1 for step in advance_chain if c in step.get("new_concepts", [])),
            reverse=True
        )[:5]

        for concept in top_concepts:
            count = sum(1 for step in advance_chain if concept in step.get("new_concepts", []))
            summary.append(f"  - {concept} (mentioned in {count} iterations)")

        # Knowledge graph growth
        summary.append(f"\nKnowledge Graph Growth:")
        summary.append(f"- Final Nodes: {self.knowledge_graph.number_of_nodes()}")
        summary.append(f"- Final Edges: {self.knowledge_graph.number_of_edges()}")
        summary.append(f"- Graph Density: {nx.density(self.knowledge_graph):.3f}")

        return "\n".join(summary)

    def _generate_graph_report(self) -> Dict:
        """Generate a report on the knowledge graph"""
        if not self.knowledge_graph.nodes():
            return {"status": "empty"}

        # Calculate centrality metrics
        degree_centrality = nx.degree_centrality(self.knowledge_graph)
        betweenness_centrality = nx.betweenness_centrality(self.knowledge_graph)
        closeness_centrality = nx.closeness_centrality(self.knowledge_graph)

        # Get top concepts by different centrality measures
        top_degree = sorted(degree_centrality.items(), key=lambda x: -x[1])[:5]
        top_betweenness = sorted(betweenness_centrality.items(), key=lambda x: -x[1])[:5]
        top_closeness = sorted(closeness_centrality.items(), key=lambda x: -x[1])[:5]

        # Find strongly connected components
        sccs = list(nx.strongly_connected_components(self.knowledge_graph))
        sccs.sort(key=lambda x: -len(x))

        return {
            "status": "success",
            "metrics": {
                "nodes": self.knowledge_graph.number_of_nodes(),
                "edges": self.knowledge_graph.number_of_edges(),
                "density": nx.density(self.knowledge_graph),
                "average_degree": sum(dict(self.knowledge_graph.degree()).values()) / self.knowledge_graph.number_of_nodes(),
                "is_strongly_connected": nx.is_strongly_connected(self.knowledge_graph),
                "number_strongly_connected_components": len(sccs),
                "largest_scc_size": len(sccs[0]) if sccs else 0
            },
            "top_concepts": {
                "degree_centrality": top_degree,
                "betweenness_centrality": top_betweenness,
                "closeness_centrality": top_closeness
            },
            "strongly_connected_components": [
                {"size": len(scc), "concepts": list(scc)} for scc in sccs[:3]
            ]
        }

    def _generate_metric_trends(self, advance_chain: List[Dict]) -> Dict:
        """Generate trends of metrics across iterations"""
        if not advance_chain:
            return {}

        # Extract metrics from each iteration
        coherence_trend = [step["deep_understanding"]["metrics"].get("coherence", 0)
                         for step in advance_chain]
        consciousness_trend = [step["deep_understanding"]["metrics"].get("consciousness", 0)
                             for step in advance_chain]
        quantum_trend = [step["deep_understanding"]["metrics"].get("quantum_entanglement", 0)
                        for step in advance_chain]
        new_concepts_trend = [len(step.get("new_concepts", []))
                            for step in advance_chain]

        # Calculate trends
        trends = {
            "coherence": {
                "values": coherence_trend,
                "start": coherence_trend[0] if coherence_trend else 0,
                "end": coherence_trend[-1] if coherence_trend else 0,
                "change": (coherence_trend[-1] - coherence_trend[0]) if coherence_trend else 0,
                "average": sum(coherence_trend) / len(coherence_trend) if coherence_trend else 0
            },
            "consciousness": {
                "values": consciousness_trend,
                "start": consciousness_trend[0] if consciousness_trend else 0,
                "end": consciousness_trend[-1] if consciousness_trend else 0,
                "change": (consciousness_trend[-1] - consciousness_trend[0]) if consciousness_trend else 0,
                "average": sum(consciousness_trend) / len(consciousness_trend) if consciousness_trend else 0
            },
            "quantum_entanglement": {
                "values": quantum_trend,
                "start": quantum_trend[0] if quantum_trend else 0,
                "end": quantum_trend[-1] if quantum_trend else 0,
                "change": (quantum_trend[-1] - quantum_trend[0]) if quantum_trend else 0,
                "average": sum(quantum_trend) / len(quantum_trend) if quantum_trend else 0
            },
            "new_concepts": {
                "values": new_concepts_trend,
                "total": sum(new_concepts_trend),
                "average": sum(new_concepts_trend) / len(new_concepts_trend) if new_concepts_trend else 0,
                "max": max(new_concepts_trend) if new_concepts_trend else 0
            }
        }

        # Add convergence analysis
        if len(coherence_trend) > 1:
            trends["convergence"] = {
                "coherence_stable": abs(coherence_trend[-1] - coherence_trend[-2]) < 0.02,
                "consciousness_stable": abs(consciousness_trend[-1] - consciousness_trend[-2]) < 0.02,
                "concepts_stable": new_concepts_trend[-1] <= new_concepts_trend[-2]
            }

        return trends

    def _generate_key_insights(self, advance_chain: List[Dict]) -> List[str]:
        """Generate key insights from the auto-advance process"""
        insights = []

        # Analyze metric trends
        trends = self._generate_metric_trends(advance_chain)

        if trends.get("coherence", {}).get("change", 0) > 0.1:
            insights.append(
                f"Significant coherence improvement (ΔΛ={trends['coherence']['change']:.3f}) "
                f"indicates better logical integration of concepts."
            )

        if trends.get("consciousness", {}).get("change", 0) > 0.1:
            insights.append(
                f"Consciousness metric improved (ΔΦ={trends['consciousness']['change']:.3f}) "
                f"showing better integration of information."
            )

        if trends.get("quantum_entanglement", {}).get("change", 0) > 0.1:
            insights.append(
                f"Increased quantum entanglement ({trends['quantum_entanglement']['change']:+.3f}) "
                f"suggests stronger conceptual relationships were identified."
            )

        # Analyze knowledge graph
        graph_report = self._generate_graph_report()
        if graph_report.get("metrics", {}).get("largest_scc_size", 0) > 5:
            insights.append(
                f"Large strongly connected component ({graph_report['metrics']['largest_scc_size']} concepts) "
                f"indicates a core set of interrelated ideas."
            )

        # Analyze top concepts
        top_concepts = graph_report.get("top_concepts", {}).get("degree_centrality", [])
        if top_concepts:
            insights.append(
                f"Key central concepts identified: {', '.join([c[0] for c in top_concepts[:3]])}"
            )

        # Analyze refinement questions
        all_questions = []
        for step in advance_chain:
            all_questions.extend(step.get("refinement_questions", []))

        if all_questions:
            common_themes = self._find_common_themes(all_questions)
            if common_themes:
                insights.append(
                    f"Recurring themes in refinement: {', '.join(common_themes[:3])}"
                )

        # If no insights generated, add some generic ones
        if not insights:
            insights.extend([
                "Iterative refinement led to progressively deeper understanding",
                "Multiple perspectives were integrated through the process",
                "Conceptual relationships were systematically explored"
            ])

        return insights

    def _find_common_themes(self, questions: List[str]) -> List[str]:
        """Find common themes in refinement questions"""
        # Simple keyword-based theme detection
        theme_keywords = {
            "connections": ["connection", "relationship", "link", "relate"],
            "integration": ["integrate", "unify", "combine", "synthesize"],
            "quantum": ["quantum", "entanglement", "superposition", "qubit"],
            "cognitive": ["cognitive", "reasoning", "understanding", "memory"],
            "application": ["apply", "application", "practical", "use"],
            "foundations": ["foundation", "basic", "principle", "fundamental"]
        }

        theme_counts = {theme: 0 for theme in theme_keywords}

        for question in questions:
            q_lower = question.lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in q_lower for keyword in keywords):
                    theme_counts[theme] += 1

        # Return themes with highest counts
        sorted_themes = sorted(theme_counts.items(), key=lambda x: -x[1])
        return [theme for theme, count in sorted_themes if count > 0]

    def _generate_final_recommendations(self, advance_chain: List[Dict]) -> List[str]:
        """Generate final recommendations based on the auto-advance process"""
        recommendations = []
        trends = self._generate_metric_trends(advance_chain)
        graph_report = self._generate_graph_report()
        last_step = advance_chain[-1] if advance_chain else {}

        # Recommendations based on metrics
        if trends.get("coherence", {}).get("end", 0) < 0.7:
            recommendations.append(
                "Focus on strengthening logical connections between concepts to improve coherence. "
                "Try explicitly mapping relationships between key ideas."
            )

        if trends.get("consciousness", {}).get("end", 0) < 0.7:
            recommendations.append(
                "Work on integrating the concepts into a unified framework. "
                "Look for higher-level principles that can unify the different ideas."
            )

        if client.enable_quantum and trends.get("quantum_entanglement", {}).get("end", 0) < 0.5:
            recommendations.append(
                "Consider increasing quantum entanglement strength to better model "
                "the relationships between concepts, especially for interconnected ideas."
            )

        # Recommendations based on knowledge graph
        if graph_report.get("metrics", {}).get("number_strongly_connected_components", 0) > 2:
            recommendations.append(
                "The knowledge graph shows multiple disconnected components. "
                "Focus on finding connections between these different concept clusters."
            )

        # Recommendations based on domains
        domains = last_step.get("deep_understanding", {}).get("intent_analysis", {}).get("domains", [])
        if "quantum" in " ".join(domains).lower() and "cognitive" in " ".join(domains).lower():
            recommendations.append(
                "The analysis spans both quantum and cognitive domains. "
                "Explore how quantum information theory might provide models for cognitive processes."
            )

        # Recommendations based on convergence
        if not trends.get("convergence", {}).get("coherence_stable", False):
            recommendations.append(
                "The understanding hasn't fully converged. Consider running additional iterations "
                "or exploring the refinement questions from the final iteration."
            )

        # Default recommendations
        if not recommendations:
            recommendations.extend([
                "Review the refinement questions from the final iteration for further exploration",
                "Apply the developed understanding to related problems or domains",
                "Consider publishing or documenting the insights for future reference"
            ])

        return recommendations

async def do_auto_enhance(prompt: str, iterations: int = 3) -> None:
    """Automatically enhance a prompt through multiple iterations"""
    prompt = normalize_prompt(prompt)
    client = await create_nclm_client()
    engine = AutoEnhanceEngine(client)

    try:
        print(f"\n{'='*70}")
        print("AUTO-ENHANCE PROCESS")
        print("="*70)
        print(f"Original Prompt: {prompt}")
        print(f"Iterations: {iterations}\n")

        result = await engine.auto_enhance_prompt(prompt, iterations)

        print(f"Enhancement Summary:")
        print(f"- Original length: {len(prompt)} characters")
        print(f"- Final length: {len(result['final_enhanced_prompt'])} characters")
        print(f"- Complexity increase: {result['metrics']['complexity_increase']:.1%}")
        print(f"- Coherence improvement: {result['metrics']['coherence_improvement']:+.3f}")
        print(f"- Strategies used: {', '.join(result['metrics']['unique_strategies'])}\n")

        print(f"Enhancement Chain:")
        for i, step in enumerate(result['enhancement_chain'], 1):
            print(f"{i}. {step['strategy'].replace('_', ' ').title()}")
            print(f"   From: {step['original'][:60]}...")
            print(f"   To:   {step['enhanced'][:60]}...\n")

        print(f"\n{'='*70}")
        print("FINAL ENHANCED PROMPT")
        print("="*70)
        print(result['final_enhanced_prompt'])

        # Save results
        out_file = REPO_ROOT / f"auto_enhance_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(f"\nSaved auto-enhancement results to: {out_file}")

    except Exception as exc:
        logger.error(f"Auto-enhance failed: {exc}")
        print(f"Error: {exc}")

async def do_auto_advance(prompt: str, iterations: int = 5, depth: int = 3) -> None:
    """Automatically advance understanding through iterative refinement"""
    prompt = normalize_prompt(prompt)
    client = await create_nclm_client()
    engine = AutoAdvanceEngine(client)

    try:
        print(f"\n{'='*70}")
        print("AUTO-ADVANCE PROCESS")
        print("="*70)
        print(f"Initial Prompt: {prompt}")
        print(f"Iterations: {iterations}")
        print(f"Exploration Depth: {depth}\n")

        result = await engine.auto_advance(prompt, iterations, depth)

        print(f"Auto-Advance Summary:")
        print(f"- Session ID: {result['session_id']}")
        print(f"- Iterations Completed: {result['iterations']}")
        print(f"- Final Prompt Length: {len(result['final_prompt'])} characters")
        print(f"- Knowledge Graph: {result['knowledge_graph']['metrics']['nodes']} nodes, "
              f"{result['knowledge_graph']['metrics']['edges']} edges\n")

        print(f"Metric Trends:")
        trends = result['final_report']['metric_trends']
        print(f"- Coherence (Λ): {trends['coherence']['start']:.3f} → {trends['coherence']['end']:.3f}"
              f" (Δ={trends['coherence']['change']:+.3f})")
        print(f"- Consciousness (Φ): {trends['consciousness']['start']:.3f} → {trends['consciousness']['end']:.3f}"
              f" (Δ={trends['consciousness']['change']:+.3f})")
        if client.enable_quantum:
            print(f"- Quantum Entanglement: {trends['quantum_entanglement']['start']:.3f} → "
                  f"{trends['quantum_entanglement']['end']:.3f} (Δ={trends['quantum_entanglement']['change']:+.3f})")

        print(f"\nKey Insights:")
        for i, insight in enumerate(result['final_report']['key_insights'][:3], 1):
            print(f"{i}. {insight}")

        print(f"\nFinal Recommendations:")
        for i, rec in enumerate(result['final_report']['recommendations'][:3], 1):
            print(f"{i}. {rec}")

        print(f"\nSession saved to: {result['session_dir']}")

    except Exception as exc:
        logger.error(f"Auto-advance failed: {exc}")
        print(f"Error: {exc}")

async def do_auto_complete(prompt: str) -> None:
    """Run complete auto-enhance and auto-advance pipeline"""
    prompt = normalize_prompt(prompt)

    try:
        print(f"\n{'='*70}")
        print("COMPLETE AUTO-COMPLETE PIPELINE")
        print("="*70)
        print(f"Initial Prompt: {prompt}\n")

        # Step 1: Auto-enhance
        print("[STAGE 1: AUTO-ENHANCE]")
        client = await create_nclm_client()
        enhance_engine = AutoEnhanceEngine(client)

        enhance_result = await enhance_engine.auto_enhance_prompt(prompt, iterations=3)
        enhanced_prompt = enhance_result['final_enhanced_prompt']

        print(f"Enhancement complete. Final prompt length: {len(enhanced_prompt)}")
        print(f"Coherence improvement: {enhance_result['metrics']['coherence_improvement']:+.3f}\n")

        # Step 2: Auto-advance
        print("[STAGE 2: AUTO-ADVANCE]")
        advance_engine = AutoAdvanceEngine(client)

        advance_result = await advance_engine.auto_advance(enhanced_prompt, iterations=5, depth=3)

        print(f"Auto-advance complete. Iterations: {advance_result['iterations']}")
        print(f"Knowledge graph nodes: {advance_result['knowledge_graph']['metrics']['nodes']}")
        print(f"Final coherence: {advance_result['final_report']['metric_trends']['coherence']['end']:.3f}\n")

        # Step 3: Generate final report
        print("[STAGE 3: FINAL REPORT]")
        final_report = advance_result['final_report']

        print(f"\n{'='*70}")
        print("COMPLETE PIPELINE RESULTS")
        print("="*70)

        print(f"\nSUMMARY:")
        print(final_report['summary'])

        print(f"\nKEY INSIGHTS:")
        for i, insight in enumerate(final_report['key_insights'][:5], 1):
            print(f"{i}. {insight}")

        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(final_report['recommendations'][:5], 1):
            print(f"{i}. {rec}")

        print(f"\nKNOWLEDGE GRAPH METRICS:")
        graph_metrics = final_report['knowledge_graph']['metrics']
        print(f"- Nodes: {graph_metrics['nodes']}")
        print(f"- Edges: {graph_metrics['edges']}")
        print(f"- Density: {graph_metrics['density']:.3f}")
        print(f"- Largest SCC: {graph_metrics['largest_scc_size']} concepts")

        # Save complete pipeline results
        pipeline_result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "initial_prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "auto_enhance_results": enhance_result,
            "auto_advance_results": advance_result,
            "version": VERSION
        }

        out_file = REPO_ROOT / f"auto_complete_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(pipeline_result, f, indent=2)

        print(f"\nComplete pipeline results saved to: {out_file}")

    except Exception as exc:
        logger.error(f"Auto-complete pipeline failed: {exc}")
        print(f"Error: {exc}")

async def do_session_analysis(session_id: str) -> None:
    """Analyze a previous auto-advance session"""
    try:
        session_dir = AUTOADVANCE_DIR / f"session_{session_id}"
        if not session_dir.exists():
            print(f"Session {session_id} not found")
            return

        # Load manifest
        manifest_path = session_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        print(f"\n{'='*70}")
        print(f"SESSION ANALYSIS: {session_id}")
        print("="*70)

        print(f"\nSession Overview:")
        print(f"- Initial Prompt: {manifest['initial_prompt'][:100]}...")
        print(f"- Final Prompt Length: {len(manifest['final_prompt'])}")
        print(f"- Iterations: {manifest['iterations']}")
        print(f"- Duration: {manifest['timestamps']['start']} to {manifest['timestamps']['end']}")

        print(f"\nKnowledge Graph:")
        kg_metrics = manifest['knowledge_graph']['metrics']
        print(f"- Nodes: {kg_metrics['nodes']}")
        print(f"- Edges: {kg_metrics['edges']}")
        print(f"- Density: {kg_metrics['density']:.3f}")
        print(f"- Strongly Connected Components: {kg_metrics['number_strongly_connected_components']}")

        print(f"\nFinal Metrics:")
        trends = manifest['final_report']['metric_trends']
        print(f"- Coherence (Λ): {trends['coherence']['end']:.3f}")
        print(f"- Consciousness (Φ): {trends['consciousness']['end']:.3f}")
        if client.enable_quantum:
            print(f"- Quantum Entanglement: {trends['quantum_entanglement']['end']:.3f}")

        print(f"\nKey Insights:")
        for i, insight in enumerate(manifest['final_report']['key_insights'][:3], 1):
            print(f"{i}. {insight}")

        print(f"\nRecommendations:")
        for i, rec in enumerate(manifest['final_report']['recommendations'][:3], 1):
            print(f"{i}. {rec}")

        # Offer to show specific iteration
        print(f"\nAvailable iterations: 1-{manifest['iterations']}")
        selection = input("Enter iteration number to view details (or 'q' to quit): ").strip()

        if selection.lower() != 'q':
            try:
                iteration_num = int(selection)
                if 1 <= iteration_num <= manifest['iterations']:
                    iteration_dir = session_dir / f"iteration_{iteration_num}"
                    with open(iteration_dir / "results.json", "r") as f:
                        iteration_data = json.load(f)

                    print(f"\nIteration {iteration_num} Details:")
                    print(f"- Prompt: {iteration_data['prompt'][:150]}...")
                    print(f"- New Concepts: {len(iteration_data['new_concepts'])}")
                    print(f"- Coherence: {iteration_data['deep_understanding']['metrics']['coherence']:.3f}")
                    print(f"- Consciousness: {iteration_data['deep_understanding']['metrics']['consciousness']:.3f}")

                    print(f"\nRefinement Questions:")
                    for i, q in enumerate(iteration_data['refinement_questions'][:3], 1):
                        print(f"{i}. {q}")

                else:
                    print("Invalid iteration number")
            except ValueError:
                print("Please enter a number")

    except Exception as exc:
        logger.error(f"Session analysis failed: {exc}")
        print(f"Error: {exc}")

def get_prompt_from_args(args):
    """Get prompt from args, file, or stdin"""
    if hasattr(args, 'prompt') and args.prompt:
        return args.prompt
    elif hasattr(args, 'file') and args.file:
        with open(args.file, 'r') as f:
            return f.read().strip()
    elif hasattr(args, 'stdin') and args.stdin:
        return sys.stdin.read().strip()
    else:
        return None

async def main_async() -> None:
    """Main asynchronous entry point with auto-enhance and auto-advance commands"""
    parser = argparse.ArgumentParser(
        prog="osiris",
        description="OSIRIS CLI with Enhanced Neural Cognitive Language Model, Quantum Processing, Auto-Enhance, and Auto-Advance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  osiris infer "Explain quantum computing to a 5-year-old"
  osiris grok "Develop a comprehensive theory of quantum cognition"
  osiris analyze "What are the implications of quantum computing for AI?"
  osiris understand "Develop deep understanding of quantum-cognitive relationships"
  osiris enhance "Explain quantum entanglement" --iterations 4
  osiris advance "Explore quantum cognition" --iterations 5 --depth 3
  osiris complete "Investigate quantum AI applications"
  osiris session <session_id>
  osiris zenodo "quantum computing" --max 10
  osiris quantum
  osiris diagnostics
  osiris tune
  osiris interactive
"""
    )

    # Global arguments
    parser.add_argument("--version", action="version", version=f"OSIRIS v{VERSION}")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="Directory for persistent state")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", required=False)

    # Infer command
    infer_parser = subparsers.add_parser("infer", help="Run NCLM inference")
    infer_parser.add_argument("prompt", nargs="?", help="Prompt text")
    infer_parser.add_argument("--file", "-f", help="Read prompt from file")
    infer_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    infer_parser.add_argument("--grok", action="store_true", help="Use grok mode (deep understanding)")
    infer_parser.add_argument("--no-telemetry", action="store_true", help="Disable telemetry")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Perform comprehensive cognitive analysis")
    analyze_parser.add_argument("prompt", nargs="?", help="Prompt text")
    analyze_parser.add_argument("--file", "-f", help="Read prompt from file")
    analyze_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")

    # Understand command
    understand_parser = subparsers.add_parser("understand", help="Develop deep understanding of a complex topic")
    understand_parser.add_argument("prompt", nargs="?", help="Topic to understand")
    understand_parser.add_argument("--file", "-f", help="Read prompt from file")
    understand_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    understand_parser.add_argument("--depth", type=int, default=5, help="Maximum depth of understanding")
    understand_parser.add_argument("--quantum", type=float, default=0.7,
                                  help="Quantum processing strength (0.0-1.0)")

    # Enhance command
    enhance_parser = subparsers.add_parser("enhance", help="Automatically enhance a prompt")
    enhance_parser.add_argument("prompt", nargs="?", help="Prompt to enhance")
    enhance_parser.add_argument("--file", "-f", help="Read prompt from file")
    enhance_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    enhance_parser.add_argument("--iterations", type=int, default=3, help="Number of enhancement iterations")

    # Advance command
    advance_parser = subparsers.add_parser("advance", help="Automatically advance understanding")
    advance_parser.add_argument("prompt", nargs="?", help="Topic to advance")
    advance_parser.add_argument("--file", "-f", help="Read prompt from file")
    advance_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    advance_parser.add_argument("--iterations", type=int, default=5, help="Number of advance iterations")
    advance_parser.add_argument("--depth", type=int, default=3, help="Exploration depth per iteration")

    # Complete command
    complete_parser = subparsers.add_parser("complete", help="Run complete auto-enhance and auto-advance pipeline")
    complete_parser.add_argument("prompt", nargs="?", help="Topic to process completely")
    complete_parser.add_argument("--file", "-f", help="Read prompt from file")
    complete_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")

    # Session command
    session_parser = subparsers.add_parser("session", help="Analyze a previous auto-advance session")
    session_parser.add_argument("session_id", help="Session ID to analyze")

    # Concept command
    concept_parser = subparsers.add_parser("concept", help="Generate cognitive concept map")
    concept_parser.add_argument("prompt", nargs="?", help="Prompt text")
    concept_parser.add_argument("--file", "-f", help="Read prompt from file")
    concept_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")

    # Zenodo command
    zenodo_parser = subparsers.add_parser("zenodo", help="Search Zenodo with cognitive analysis")
    zenodo_parser.add_argument("query", nargs="?", default="quantum computing", help="Search query")
    zenodo_parser.add_argument("--max", type=int, default=12, help="Maximum results")

    # GitHub command
    github_parser = subparsers.add_parser("github", help="Ingest GitHub repository")
    github_parser.add_argument("repo", help="GitHub repo URL or owner/repo")

    # Quantum command
    subparsers.add_parser("quantum", help="Run quantum cognitive simulation")

    # Tune command
    subparsers.add_parser("tune", help="Interactive quantum parameter tuning")

    # Diagnostics command
    subparsers.add_parser("diagnostics", help="Run comprehensive cognitive system diagnostics")
    subparsers.add_parser("understand-diag", help="Run deep understanding diagnostics")

    # Memory command
    memory_parser = subparsers.add_parser("memory", help="Manage cognitive memory")
    memory_parser.add_argument("command", choices=["stats", "clear", "clear-working", "save"],
                               help="Memory command to execute")

    # Mode command
    mode_parser = subparsers.add_parser("mode", help="Set NCLM processing mode")
    mode_parser.add_argument("mode", choices=[m.name.lower() for m in NCLMMode],
                            help="Processing mode to set")

    # Param command
    param_parser = subparsers.add_parser("param", help="Adjust cognitive parameters")
    param_parser.add_argument("parameters", nargs="+", help="Parameters to adjust (key=value)")

    # Interactive shell
    subparsers.add_parser("interactive", help="Start interactive cognitive shell")

    args = parser.parse_args()

    if not args.command:
        args.command = "interactive"

    # Set up logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)

    try:
        # Validate SDK before any operations
        validate_sdk()

        # Handle commands
        if args.command == "infer":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for inference")
            await do_infer(prompt, grok=args.grok, no_telemetry=args.no_telemetry)

        elif args.command == "analyze":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for analysis")
            await do_cognitive_analysis(prompt)

        elif args.command == "understand":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for deep understanding")
            await do_deep_understand(prompt)

        elif args.command == "enhance":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for enhancement")
            await do_auto_enhance(prompt, iterations=args.iterations)

        elif args.command == "advance":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for auto-advance")
            await do_auto_advance(prompt, iterations=args.iterations, depth=args.depth)

        elif args.command == "complete":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for complete pipeline")
            await do_auto_complete(prompt)

        elif args.command == "session":
            await do_session_analysis(args.session_id)

        elif args.command == "concept":
            prompt = get_prompt_from_args(args)
            if not prompt:
                raise ValueError("Prompt is required for concept mapping")
            await do_concept_map(prompt)

        elif args.command == "zenodo":
            await do_zenodo_scan(args.query, max_results=args.max)

        elif args.command == "github":
            await do_github_ingest(args.repo)

        elif args.command == "quantum":
            await do_quantum_simulation()

        elif args.command == "tune":
            await do_quantum_tuning()

        elif args.command == "diagnostics":
            await do_cognitive_diagnostics()

        elif args.command == "understand-diag":
            await do_understanding_diagnostics()

        elif args.command == "memory":
            await do_memory_management(args.command)

        elif args.command == "mode":
            await do_mode_selection(args.mode.upper())

        elif args.command == "param":
            params = {}
            for param in args.parameters:
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = float(value)
            await do_parameter_adjustment(params)

        elif args.command == "interactive":
            await interactive_shell()

    except Exception as exc:
        logger.error(f"Fatal error: {exc}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def print_interactive_help():
    """Print help information for interactive shell with all commands"""
    help_text = """
    OSIRIS Enhanced Cognitive Processing Console - Commands:

    General:
      help, ?          - Show this help
      exit, quit, q     - Exit the shell
      history           - Show command history
      !<n>              - Execute command number <n> from history

    Cognitive Processing:
      infer:<prompt>    - Run standard NCLM inference
      grok:<prompt>     - Run deep understanding (grok) mode
      understand:<prompt> - Develop deep understanding of a complex topic
      analyze:<prompt>  - Full cognitive analysis with quantum processing
      enhance:<prompt>  - Automatically enhance a prompt through iterations
      advance:<prompt>   - Automatically advance understanding through refinement
      complete:<prompt> - Run complete auto-enhance and auto-advance pipeline
      concept <prompt>   - Generate cognitive concept map
      session <id>      - Analyze a previous auto-advance session

    Quantum Processing:
      quantum           - Run quantum cognitive simulation
      tune              - Interactive quantum parameter tuning

    System Control:
      mode <mode>       - Set processing mode (standard, grok, creative,
                           analytical, quantum, hybrid)
      param key=value    - Adjust cognitive parameters
      memory <cmd>       - Memory management (stats, clear, clear-working, save)
      diagnostics        - Run comprehensive system diagnostics
      understand-diag    - Run deep understanding diagnostics

    Examples:
      infer: Explain quantum entanglement in simple terms
      grok: Develop a comprehensive theory of quantum cognition
      understand: Develop deep understanding of quantum-cognitive relationships
      analyze: What are the implications of quantum computing for AI?
      enhance: Explain quantum entanglement --iterations 4
      advance: Explore quantum cognition --iterations 5 --depth 3
      complete: Investigate quantum AI applications
      session d7a3f1b5
      concept: Map the relationships between quantum physics and cognition
      mode quantum
      param quantum_entanglement=0.7 coherence_threshold=0.85
      memory stats
      tune
    """
    print(help_text)

async def interactive_shell() -> None:
    """Launch the OSIRIS TUI"""
    from dnalang_sdk.nclm.tui import OsirisTUI
    app = OsirisTUI()
    app.run()

async def do_github_ingest(repo: str) -> None:
    """Ingest a GitHub repository"""
    print(f"Ingesting GitHub repo: {repo}")
    # TODO: Implement full ingestion logic
    # For now, placeholder

def main():
    """Main entry point"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)  # SIGINT exit code
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    main()
