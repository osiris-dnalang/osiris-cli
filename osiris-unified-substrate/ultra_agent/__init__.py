"""OSIRIS Ultra-Agent: Autonomous self-improving reasoning engine.

Swarm architecture:
  Orchestrator → Reasoner → Coder → Critic → Optimizer → SelfReflector

Dual-swarm mentorship:
  MentorSwarm → critique → ProtegeSwarm → improve → DistillationEngine

Every output is tagged with inference mode (simulation/model) and
includes token/latency accounting for scientific defensibility.
"""

from .swarm import AgentSwarm, run_ultra_agent
from .model_interface import ModelInterface, get_model_interface

__all__ = ["AgentSwarm", "run_ultra_agent", "ModelInterface", "get_model_interface"]
