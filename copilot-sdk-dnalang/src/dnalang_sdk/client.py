"""DNALang Copilot Client - Main client implementation."""

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from .config import QuantumConfig, LambdaPhiConfig, ConsciousnessConfig
from .quantum import QuantumCircuit, QuantumBackend, QuantumResult
from .lambda_phi import LambdaPhiValidator
from .consciousness import ConsciousnessAnalyzer
from .tools import ToolRegistry
from .nclm_provider import (
    NCLMModelProvider,
    NCLMConfig,
    is_nclm_available,
    NCLM_MODEL_ID,
)
from .intent_engine import IntentDeductionEngine
from .gemini_provider import GeminiModelProvider, GeminiConfig


@dataclass
class CopilotConfig:
    """Configuration for Copilot CLI connection."""
    cli_path: str = "copilot"
    server_mode: bool = False  # offline build: no server process started by default
    allow_all_tools: bool = False
    port: Optional[int] = None
    timeout: int = 300
    model: str = "nclm-v2"  # offline inference model
    use_nclm: bool = True  # Enable NCLM by default in offline build


class DNALangCopilotClient:
    """
    Main client for DNALang SDK.
    
    Provides quantum computing, lambda-phi conservation, consciousness
    scaling, NCLM, Gemini, and Intent-Deduction Engine capabilities 
    through GitHub Copilot CLI agent runtime.
    """
    
    def __init__(
        self,
        quantum_config: Optional[QuantumConfig] = None,
        lambda_phi_config: Optional[LambdaPhiConfig] = None,
        consciousness_config: Optional[ConsciousnessConfig] = None,
        copilot_config: Optional[CopilotConfig] = None,
        nclm_config: Optional[NCLMConfig] = None,
        # New parameters
        enable_intent_engine: bool = False,
        enable_gemini: bool = False,
        gemini_api_key: Optional[str] = None,
    ):
        """Initialize DNALang Copilot client."""
        self.quantum_config = quantum_config or QuantumConfig()
        self.lambda_phi_config = lambda_phi_config or LambdaPhiConfig()
        self.consciousness_config = consciousness_config or ConsciousnessConfig()
        self.copilot_config = copilot_config or CopilotConfig()
        self.nclm_config = nclm_config or NCLMConfig()
        
        self._cli_process: Optional[subprocess.Popen] = None
        self._request_id: int = 0
        self._tool_registry = ToolRegistry()
        
        # Initialize quantum backend
        self._quantum_backend: Optional[QuantumBackend] = None
        if self.quantum_config.backend:
            self._quantum_backend = QuantumBackend(self.quantum_config)
        
        # Initialize validators
        self._lambda_phi_validator: Optional[LambdaPhiValidator] = None
        self._consciousness_analyzer: Optional[ConsciousnessAnalyzer] = None
        
        # Initialize NCLM provider if enabled
        self._nclm_provider: Optional[NCLMModelProvider] = None
        if self.copilot_config.use_nclm and is_nclm_available():
            self._nclm_provider = NCLMModelProvider(self.nclm_config)
            logger.info("NCLM Model Provider initialized (λφ=%s)", self.nclm_config.lambda_decay)
        elif self.copilot_config.use_nclm:
            logger.warning("NCLM requested but not available. Falling back to Copilot CLI.")
        
        # Initialize Intent-Deduction Engine if enabled
        self.intent_engine: Optional[IntentDeductionEngine] = None
        if enable_intent_engine:
            self.intent_engine = IntentDeductionEngine(
                recursion_depth=getattr(copilot_config, 'intent_recursion_depth', 3) if copilot_config else 3,
                enable_nclm=self.copilot_config.use_nclm,
                nclm_model=self._nclm_provider
            )
            logger.info("Intent-Deduction Engine initialized")
        
        # Initialize Gemini provider if enabled
        self._gemini_provider: Optional[GeminiModelProvider] = None
        if enable_gemini:
            from .gemini_provider import GeminiModelProvider, GeminiConfig
            self._gemini_provider = GeminiModelProvider(
                config=GeminiConfig(api_key=gemini_api_key)
            )
            logger.info("Gemini Model Provider initialized (model=%s)", self._gemini_provider.config.model)

    
    async def __aenter__(self) -> "DNALangClient":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def start(self) -> None:
        """Start Copilot CLI in server mode."""
        if self.copilot_config.server_mode and not self._cli_process:
            cmd = [self.copilot_config.cli_path, "server"]
            if self.copilot_config.allow_all_tools:
                cmd.append("--allow-all")
            if self.copilot_config.port:
                cmd.extend(["--port", str(self.copilot_config.port)])
            
            try:
                self._cli_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                await asyncio.sleep(2)
            except FileNotFoundError:
                logger.warning("Copilot CLI not found at '%s'. Running in standalone mode.", self.copilot_config.cli_path)
    
    async def close(self) -> None:
        """Close Copilot CLI connection."""
        if self._cli_process:
            self._cli_process.terminate()
            try:
                self._cli_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._cli_process.kill()
            self._cli_process = None
    
    def create_quantum_circuit(
        self,
        num_qubits: int,
        gates: List[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> QuantumCircuit:
        """Create a quantum circuit."""
        return QuantumCircuit(num_qubits=num_qubits, gates=gates or [], name=name)
    
    async def execute_quantum_circuit(
        self,
        circuit: QuantumCircuit,
        shots: Optional[int] = None,
        backend: Optional[str] = None,
        optimization_level: Optional[int] = None,
    ) -> QuantumResult:
        """Execute a quantum circuit on specified backend."""
        if not self._quantum_backend:
            self._quantum_backend = QuantumBackend(self.quantum_config)
        
        shots = shots or self.quantum_config.shots
        backend = backend or self.quantum_config.default_backend
        optimization_level = optimization_level or self.quantum_config.optimization_level
        
        result = await self._quantum_backend.execute(
            circuit=circuit,
            shots=shots,
            backend=backend,
            optimization_level=optimization_level,
        )
        
        return result
    
    def create_lambda_phi_validator(self) -> LambdaPhiValidator:
        """Create lambda-phi conservation validator."""
        if not self._lambda_phi_validator:
            self._lambda_phi_validator = LambdaPhiValidator(
                config=self.lambda_phi_config,
                quantum_backend=self._quantum_backend,
            )
        return self._lambda_phi_validator
    
    def create_consciousness_analyzer(self) -> ConsciousnessAnalyzer:
        """Create consciousness scaling analyzer."""
        if not self._consciousness_analyzer:
            self._consciousness_analyzer = ConsciousnessAnalyzer(
                config=self.consciousness_config,
                quantum_backend=self._quantum_backend,
            )
        return self._consciousness_analyzer
    
    @classmethod
    def from_config_file(cls, config_path: str) -> "DNALangCopilotClient":
        """Create client from JSON configuration file."""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        return cls(
            quantum_config=QuantumConfig(**config.get("quantum", {})),
            lambda_phi_config=LambdaPhiConfig(**config.get("lambda_phi", {})),
            consciousness_config=ConsciousnessConfig(**config.get("consciousness", {})),
            copilot_config=CopilotConfig(**config.get("copilot", {})),
        )
    
    async def nclm_infer(
        self,
        prompt: str,
        context: str = "",
        grok: bool = False,
    ) -> Dict[str, Any]:
        """
        Perform NCLM inference using quantum consciousness model.
        
        Args:
            prompt: User prompt
            context: Optional context
            grok: Use deep grokking mode
            
        Returns:
            NCLM inference result
            
        Example:
            >>> result = await client.nclm_infer("Explain lambda-phi conservation")
            >>> print(result["content"])
        """
        if not self._nclm_provider:
            raise ValueError("NCLM not enabled. Set use_nclm=True in CopilotConfig")
        
        result = self._nclm_provider.generate_completion(
            prompt=prompt,
            context=context,
            grok=grok,
        )
        
        return result
    
    async def nclm_grok(self, prompt: str) -> Dict[str, Any]:
        """
        Perform deep grokking with NCLM swarm evolution.
        
        Args:
            prompt: Complex prompt for deep analysis
            
        Returns:
            Grok result with swarm discoveries
        """
        return await self.nclm_infer(prompt, grok=True)
    
    def get_nclm_telemetry(self) -> Dict[str, Any]:
        """
        Get NCLM session telemetry.
        
        Returns:
            Telemetry data including Φ, consciousness ratio, token count
        """
        if not self._nclm_provider:
            return {"error": "NCLM not enabled"}
        
        return self._nclm_provider.get_session_telemetry()
