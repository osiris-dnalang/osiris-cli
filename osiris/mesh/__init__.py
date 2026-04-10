"""osiris.mesh — NCLM mesh networking.

Re-exports from osiris.decoders and osiris.crsm for backward compatibility.
"""

from osiris.decoders.tesseract import TesseractDecoderOrganism, TesseractResonatorOrganism
from osiris.hardware.quera_adapter import QuEraCorrelatedAdapter

def get_nonlocal_agent():
    from osiris.crsm.nonlocal_agent import BifurcatedSentinelOrchestrator
    return BifurcatedSentinelOrchestrator

def get_swarm_orchestrator():
    from osiris.crsm.swarm_orchestrator import NCLMSwarmOrchestrator
    return NCLMSwarmOrchestrator
