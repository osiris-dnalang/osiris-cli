"""OSIRIS Mesh — NonLocalAgent, NCLM Swarm, Tesseract decoder, QuEra adapter.

These modules are dependency-free and can run without Qiskit.
"""

from .tesseract import TesseractDecoderOrganism, TesseractResonatorOrganism
from .quera_adapter import QuEraCorrelatedAdapter

__all__ = [
    'TesseractDecoderOrganism',
    'TesseractResonatorOrganism',
    'QuEraCorrelatedAdapter',
]

# Lazy imports for heavier modules
def get_nonlocal_agent():
    from .nonlocal_agent import NonLocalAgentEnhanced
    return NonLocalAgentEnhanced

def get_swarm_orchestrator():
    from .swarm_orchestrator import NCLMSwarmOrchestrator
    return NCLMSwarmOrchestrator
