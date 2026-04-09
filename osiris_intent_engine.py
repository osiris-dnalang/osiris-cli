#!/usr/bin/env python3
"""
OSIRIS Intent Engine - Autonomous Intent Detection & Agent Orchestration

Parses natural language + context to infer user intent and spawn agents.
Core intelligence layer - no external LLM dependency.
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class IntentType(Enum):
    """Intent classification"""
    BENCHMARK = "benchmark"
    EXPERIMENT = "experiment"
    ORCHESTRATE = "orchestrate"
    DEPLOY = "deploy"
    ANALYZE = "analyze"
    PUBLISH = "publish"
    REFINE = "refine"
    MANUFACTURING = "manufacturing"
    STATUS = "status"
    HELP = "help"
    UNKNOWN = "unknown"

@dataclass
class Intent:
    """Parsed user intent"""
    intent_type: IntentType
    confidence: float
    parameters: Dict[str, Any]
    suggested_actions: List[str]
    required_agents: List[str]

class IntentEngine:
    """Detects intent from natural language without external LLM"""
    
    # Intent patterns
    BENCHMARK_PATTERNS = [
        r"benchmark",
        r"test.*hardware",
        r"extreme.*shot",
        r"depth.*test",
        r"max.*qubit",
        r"performance.*test",
        r"world record",
        r"fidelity.*test"
    ]
    
    EXPERIMENT_PATTERNS = [
        r"run.*experiment",
        r"execute",
        r"test.*hypothesis",
        r"xeb",
        r"entropy",
        r"circuit.*test"
    ]
    
    DEPLOY_PATTERNS = [
        r"deploy",
        r"publish.*zenodo",
        r"submit",
        r"release",
        r"launch.*production"
    ]
    
    ORCHESTRATE_PATTERNS = [
        r"orchestrator",
        r"run.*campaign",
        r"full.*pipeline",
        r"research.*pipeline",
        r"week1",
        r"rqc.*rcs",
        r"execute.*pipeline"
    ]
    
    ANALYZE_PATTERNS = [
        r"analyze",
        r"interpret",
        r"explain",
        r"what.*results",
        r"why.*failed",
        r"compare"
    ]
    
    PUBLISH_PATTERNS = [
        r"publish",
        r"zenodo",
        r"arxiv",
        r"doi",
        r"citation"
    ]
    
    REFINE_PATTERNS = [
        r"improve",
        r"optimize",
        r"enhance",
        r"fix",
        r"refactor"
    ]
    
    STATUS_PATTERNS = [
        r"status",
        r"how.*going",
        r"what.*running",
        r"progress",
        r"results"
    ]

    MANUFACTURING_PATTERNS = [
        r"3d.*print",
        r"print.*3d",
        r"manufacture",
        r"additive",
        r"physicalize",
        r"tetrahedral.*cube",
        r"planck.*scale.*cube",
        r"detect.*printer",
        r"scan.*printer",
        r"printer.*status",
        r"bambu",
        r"elegoo",
        r"p1s",
        r"a1.*mini",
        r"centauri",
        r"g-?code",
        r"gcode",
        r"slic(?:e|er|ing)",
        r"mesh.*gen",
        r"stl",
        r"3mf",
        r"flash.*drive",
        r"export.*gcode",
        r"resonance.*cavity",
        r"toroid",
        r"lattice.*print",
        r"quaternion.*model",
        r"torsion.*lock.*model",
    ]

    def __init__(self):
        """Initialize intent engine"""
        self.conversation_history: List[Dict] = []
        self.context_memory: Dict[str, Any] = {
            'backend': 'ibm_torino',
            'qubits': 12,
            'shots': 4000,
            'depth': 8,
            'mode': 'benchmark'
        }
    
    def parse_intent(self, user_input: str, context: Optional[Dict] = None) -> Intent:
        """Parse user intent from natural language"""
        
        text = user_input.lower().strip()
        
        # Extract parameters from text
        params = self._extract_parameters(text)
        
        # Detect intent type
        intent_type = self._classify_intent(text)
        confidence = self._calculate_confidence(text, intent_type)
        
        # Generate suggested actions
        actions = self._generate_actions(intent_type, params)
        
        # Determine required agents
        agents = self._select_agents(intent_type, params)
        
        return Intent(
            intent_type=intent_type,
            confidence=confidence,
            parameters=params,
            suggested_actions=actions,
            required_agents=agents
        )
    
    def _classify_intent(self, text: str) -> IntentType:
        """Classify intent from text patterns"""
        
        # Check each pattern
        for pattern in self.MANUFACTURING_PATTERNS:
            if re.search(pattern, text):
                return IntentType.MANUFACTURING

        for pattern in self.BENCHMARK_PATTERNS:
            if re.search(pattern, text):
                return IntentType.BENCHMARK
        
        for pattern in self.ORCHESTRATE_PATTERNS:
            if re.search(pattern, text):
                return IntentType.ORCHESTRATE
        
        for pattern in self.DEPLOY_PATTERNS:
            if re.search(pattern, text):
                return IntentType.DEPLOY
        
        for pattern in self.PUBLISH_PATTERNS:
            if re.search(pattern, text):
                return IntentType.PUBLISH
        
        for pattern in self.REFINE_PATTERNS:
            if re.search(pattern, text):
                return IntentType.REFINE
        
        for pattern in self.ANALYZE_PATTERNS:
            if re.search(pattern, text):
                return IntentType.ANALYZE
        
        for pattern in self.EXPERIMENT_PATTERNS:
            if re.search(pattern, text):
                return IntentType.EXPERIMENT
        
        for pattern in self.STATUS_PATTERNS:
            if re.search(pattern, text):
                return IntentType.STATUS
        
        for pattern in [r"help", r"how", r"what.*do", r"guide"]:
            if re.search(pattern, text):
                return IntentType.HELP
        
        return IntentType.UNKNOWN
    
    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract quantitative parameters from text"""
        
        params = {}
        
        # Extract qubit count
        qubit_match = re.search(r'(\d+)\s*(?:qubit|q)', text)
        if qubit_match:
            params['qubits'] = int(qubit_match.group(1))
        
        # Extract shots
        shots_match = re.search(r'(\d+)\s*shot', text)
        if shots_match:
            params['shots'] = int(shots_match.group(1))
        
        # Extract depth
        depth_match = re.search(r'depth\s*.*?(\d+)', text)
        if depth_match:
            params['depth'] = int(depth_match.group(1))
        
        # Extract backend
        backends = ['ibm_torino', 'ibm_fez', 'ibm_nazca', 'ibm_brisbane']
        for backend in backends:
            if backend in text:
                params['backend'] = backend
        
        # Extract trial count
        trials_match = re.search(r'(\d+)\s*trial', text)
        if trials_match:
            params['trials'] = int(trials_match.group(1))

        # Extract scale (cm)
        scale_match = re.search(r'(\d+(?:\.\d+)?)\s*cm', text)
        if scale_match:
            params['scale_cm'] = float(scale_match.group(1))

        # Extract printer target
        printer_map = {
            'p1s': 'bambu_p1s', 'bambu p1s': 'bambu_p1s',
            'a1 mini': 'bambu_a1_mini', 'a1mini': 'bambu_a1_mini',
            'centauri': 'elegoo_centauri_2', 'elegoo': 'elegoo_centauri_2',
        }
        for pattern, printer_type in printer_map.items():
            if pattern in text:
                params['printer_type'] = printer_type
                break

        # Extract manufacturing geometry mode
        geom_map = {
            'tetrahedral': 'tetrahedral_lattice',
            'toroid': 'toroidal_manifold',
            'planck': 'planck_reference_cube',
            'resonance': 'acoustic_resonance_cavity',
            'cavity': 'acoustic_resonance_cavity',
            'quaternion': 'quaternion_orbit_model',
            'torsion': 'torsion_lock_visualizer',
        }
        for pattern, geom_mode in geom_map.items():
            if pattern in text:
                params['manufacturing_mode'] = geom_mode
                break

        return params
    
    def _calculate_confidence(self, text: str, intent_type: IntentType) -> float:
        """Calculate confidence in intent classification"""
        
        if intent_type == IntentType.UNKNOWN:
            return 0.3
        
        # Confidence based on keyword matches
        keywords_in_text = len(re.findall(r'\b\w{4,}\b', text))
        
        # More specific text = higher confidence
        if keywords_in_text > 10:
            confidence = 0.95
        elif keywords_in_text > 5:
            confidence = 0.85
        else:
            confidence = 0.7
        
        return confidence
    
    def _generate_actions(self, intent_type: IntentType, params: Dict) -> List[str]:
        """Generate suggested next actions based on intent"""
        
        actions = []
        
        if intent_type == IntentType.BENCHMARK:
            actions = [
                "1. Initialize quantum benchmarker",
                "2. Configure backend and qubits",
                "3. Run extreme shot/depth tests",
                "4. Generate performance report",
                "5. Compare against baseline"
            ]
        
        elif intent_type == IntentType.EXPERIMENT:
            actions = [
                "1. Load experiment config",
                "2. Validate hypothesis",
                "3. Execute on hardware",
                "4. Collect statistics",
                "5. Check significance"
            ]
        
        elif intent_type == IntentType.DEPLOY:
            actions = [
                "1. Validate results",
                "2. Package for Zenodo",
                "3. Generate DOI",
                "4. Create citation",
                "5. Publish"
            ]
        
        elif intent_type == IntentType.PUBLISH:
            actions = [
                "1. Check publication criteria",
                "2. Package result",
                "3. Upload to Zenodo",
                "4. Retrieve DOI",
                "5. Update bibliography"
            ]
        
        elif intent_type == IntentType.ORCHESTRATE:
            actions = [
                "1. Run full research pipeline",
                "2. Execute RQC vs RCS experiments",
                "3. Run domain-specific applications",
                "4. Publish results to Zenodo",
                "5. Generate archive manifest"
            ]
        
        elif intent_type == IntentType.MANUFACTURING:
            actions = [
                "1. Scan local network for 3D printers",
                "2. Generate mesh from organism structural genes",
                "3. Slice model to G-code for target printer",
                "4. Transmit G-code or export to flash drive",
                "5. Monitor print status via MQTT"
            ]

        elif intent_type == IntentType.STATUS:
            actions = [
                "1. Check running jobs",
                "2. Collect results",
                "3. Generate report",
                "4. Show progress"
            ]
        
        return actions
    
    def _select_agents(self, intent_type: IntentType, params: Dict) -> List[str]:
        """Select agents to spawn based on intent"""
        
        agents = []
        
        if intent_type == IntentType.BENCHMARK:
            agents = ["benchmarker_agent", "hardware_monitor"]
        elif intent_type == IntentType.EXPERIMENT:
            agents = ["executor_agent", "validator_agent"]
        elif intent_type == IntentType.DEPLOY:
            agents = ["packager_agent", "publisher_agent"]
        elif intent_type == IntentType.PUBLISH:
            agents = ["publisher_agent", "citation_agent"]
        elif intent_type == IntentType.ORCHESTRATE:
            agents = ["orchestrator_agent", "executor_agent", "publisher_agent"]
        elif intent_type == IntentType.ANALYZE:
            agents = ["analyzer_agent"]
        elif intent_type == IntentType.REFINE:
            agents = ["optimizer_agent"]
        elif intent_type == IntentType.MANUFACTURING:
            agents = ["manufacturing_agent", "printer_discovery_agent", "sovereign_executor"]
        elif intent_type == IntentType.STATUS:
            agents = ["monitor_agent"]
        
        return agents
    
    def add_to_history(self, user_input: str, response: str):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            'user': user_input,
            'response': response,
            'timestamp': str(__import__('datetime').datetime.now())
        })
    
    def update_context(self, key: str, value: Any):
        """Update context memory"""
        self.context_memory[key] = value
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context"""
        return self.context_memory.copy()


if __name__ == "__main__":
    engine = IntentEngine()
    
    # Test cases
    test_inputs = [
        "benchmark ibm_torino with 32 qubits at extreme depth",
        "run xeb experiment with 50 trials",
        "deploy results to zenodo",
        "what's the status of my jobs",
        "analyze why that circuit failed",
        "optimize this circuit for better XEB"
    ]
    
    for inp in test_inputs:
        intent = engine.parse_intent(inp)
        print(f"\nInput: {inp}")
        print(f"Intent: {intent.intent_type.value}")
        print(f"Confidence: {intent.confidence:.2f}")
        print(f"Parameters: {intent.parameters}")
        print(f"Agents: {intent.required_agents}")
        print(f"Actions: {intent.suggested_actions[:2]}")
