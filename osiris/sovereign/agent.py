"""
Sovereign Agent — Copilot + Aeterna Porta integration.
"""

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .quantum_engine import AeternaPorta, LambdaPhiEngine, QuantumMetrics


@dataclass
class AgentResult:
    output: str
    quantum_metrics: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None
    execution_time_s: float = 0.0


class SovereignAgent:
    """Token-free quantum-enhanced AI agent."""

    def __init__(self, quantum_backend: Optional[AeternaPorta] = None,
                 enable_lambda_phi: bool = True):
        self.quantum_backend = quantum_backend or AeternaPorta()
        self.lambda_phi = LambdaPhiEngine() if enable_lambda_phi else None
        self.execution_history: List[AgentResult] = []

    async def execute(self, task: str,
                      use_quantum: bool = False) -> AgentResult:
        t0 = time.time()
        try:
            analysis = self._analyze_task(task)
            quantum_metrics = None
            if use_quantum or analysis["requires_quantum"]:
                metrics = await self.quantum_backend.execute_quantum_task()
                quantum_metrics = metrics.to_dict()
            result = AgentResult(
                output=f"Completed: {task}",
                quantum_metrics=quantum_metrics,
                success=True,
                execution_time_s=time.time() - t0,
            )
        except Exception as e:
            result = AgentResult(output="", success=False,
                                error=str(e),
                                execution_time_s=time.time() - t0)
        self.execution_history.append(result)
        return result

    @staticmethod
    def _analyze_task(task: str) -> Dict[str, Any]:
        tl = task.lower()
        quantum_kw = ["quantum", "qubit", "entangle", "circuit", "fidelity",
                       "er=epr", "aeterna", "lambda phi"]
        return {
            "requires_quantum": any(kw in tl for kw in quantum_kw),
            "complexity": "high" if any(kw in tl for kw in quantum_kw) else "medium",
        }
