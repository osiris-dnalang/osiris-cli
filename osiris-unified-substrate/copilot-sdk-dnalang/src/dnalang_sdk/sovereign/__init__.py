"""Sovereign Copilot SDK — SovereignAgent, AeternaPorta, CodeGenerator, DevTools.

These modules provide the async-first agent framework with NLP-to-code
generation and token-free quantum execution.
"""

from .agent import SovereignAgent
from .quantum_engine import AeternaPorta, LambdaPhiEngine, QuantumMetrics
from .code_generator import QuantumNLPCodeGenerator, CodeIntent
from .dev_tools import DeveloperTools

__all__ = [
    'SovereignAgent',
    'AeternaPorta',
    'LambdaPhiEngine',
    'QuantumMetrics',
    'QuantumNLPCodeGenerator',
    'CodeIntent',
    'DeveloperTools',
]

# Lazy import for enhanced agent (depends on all above)
def get_enhanced_agent():
    from .enhanced_agent import EnhancedSovereignAgent
    return EnhancedSovereignAgent
