from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass
class ToolDecision:
    name: Optional[str]
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def route_tool(prompt: str) -> ToolDecision:
    text = prompt.lower()

    if any(token in text for token in ["calculate", "python", "execute", "run code", "simulate"]):
        return ToolDecision(name="code_interpreter", confidence=0.92, reason="Prompt requests executable computation")

    if any(token in text for token in ["benchmark", "evaluate", "score", "leaderboard"]):
        return ToolDecision(name="evaluation_harness", confidence=0.88, reason="Prompt requests measurable evaluation")

    return ToolDecision(name=None, confidence=0.25, reason="No specialized tool routing trigger matched")