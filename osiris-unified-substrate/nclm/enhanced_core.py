# nclm/enhanced_core.py (updated sections)
from .enhanced_config import NCLMEnhancedConfig, NCLMMode
from .deep_understanding import DeepUnderstandingProcessor
from typing import Dict
from pathlib import Path
from .quantum_cognitive import QuantumCognitiveProcessor
from collections import defaultdict

class EnhancedNCLM:
    """Enhanced Neural Cognitive Language Model with quantum-inspired processing"""

    def __init__(self, config: NCLMEnhancedConfig = None):
        self.config = config or NCLMEnhancedConfig()
        self._quantum_processor = QuantumCognitiveProcessor()
        # Initialize deep understanding processor
        self.deep_understanding_processor = DeepUnderstandingProcessor(self._quantum_processor)

        # Performance metrics
        self.processing_times = []
        self.cognitive_loads = []

        # Domain knowledge
        self.domain_knowledge = defaultdict(dict)

    async def deep_understand(self, prompt: str, max_depth: int = 5,
                             quantum_strength: float = 0.7) -> Dict:
        """Develop deep understanding of a complex topic"""
        try:
            logger.info(f"Starting deep understanding process for: {prompt[:100]}")

            # Save current mode and switch to quantum mode for deep understanding
            original_mode = self.config.mode
            self.config.mode = NCLMMode.QUANTUM

            # Perform deep understanding processing
            result = await self.deep_understanding_processor.develop_understanding(
                prompt, max_depth, quantum_strength
            )

            # Restore original mode
            self.config.mode = original_mode

            # Save state if state directory is configured
            if hasattr(self, '_state_dir') and self._state_dir:
                self.save_state(self._state_dir)

            return result

        except Exception as e:
            logger.error(f"Deep understanding failed: {e}")
            # Restore original mode if error occurs
            self.config.mode = original_mode
            return {
                "status": "error",
                "message": str(e),
                "prompt": prompt
            }

    async def _core_processing(self, enhanced_context: str, metadata: Dict) -> Dict:
        """Core NCLM processing with cognitive enhancements"""
        # ... existing processing code ...

        # Add deep understanding capability for QUANTUM and GROK modes
        if self.config.mode in [NCLMMode.QUANTUM, NCLMMode.GROK]:
            # Check if this is a request for deep understanding
            prompt_lower = metadata["prompt_metadata"].get("original_prompt", "").lower()
            if any(word in prompt_lower for word in ["understand", "explain", "analyze", "develop", "comprehensive"]):
                # Run deep understanding in parallel with regular processing
                deep_result = await self.deep_understand(
                    metadata["prompt_metadata"].get("original_prompt", ""),
                    max_depth=3,
                    quantum_strength=self.config.cognitive_params.quantum_entanglement
                )

                if deep_result.get("status") == "success":
                    result["deep_understanding"] = deep_result

        return result

    def save_state(self, path: Path) -> None:
        """Save the complete NCLM state to directory"""
        # ... existing save code ...

        # Save deep understanding processor state
        deep_state_path = directory / "deep_understanding.json"
        self.deep_understanding_processor.save_state(deep_state_path)

    @classmethod
    def load_state(cls, directory: Path) -> 'EnhancedNCLM':
        """Load NCLM state from directory"""
        # ... existing load code ...

        # Load deep understanding processor state
        deep_state_path = directory / "deep_understanding.json"
        if deep_state_path.exists():
            instance.deep_understanding_processor = DeepUnderstandingProcessor.load_state(
                deep_state_path, instance._quantum_processor
            )

        return instance
