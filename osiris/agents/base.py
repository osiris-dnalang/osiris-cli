"""Re-export from osiris_agents for backward compatibility."""
from osiris_agents import (
    BaseAgent, AgentRole, AgentTask, AgentManager,
    DiscoveryAgent, ExecutionAgent, ExpansionAgent,
    IntegrationAgent, OptimizationAgent, VerificationAgent,
)

__all__ = [
    "BaseAgent", "AgentRole", "AgentTask", "AgentManager",
    "DiscoveryAgent", "ExecutionAgent", "ExpansionAgent",
    "IntegrationAgent", "OptimizationAgent", "VerificationAgent",
]
