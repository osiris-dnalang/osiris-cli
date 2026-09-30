"""Disabled-by-default external adapter boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class AdapterState:
    name: str
    enabled: bool = False
    execution_mode: str = "disabled"


class ExternalAdapter:
    """Provider boundary that never performs work while disabled."""

    def __init__(self, name: str):
        self.state = AdapterState(name)

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.state.name,
            "enabled": self.state.enabled,
            "execution_mode": self.state.execution_mode,
        }

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise PermissionError("{} adapter is disabled".format(self.state.name))


def default_adapters() -> Dict[str, ExternalAdapter]:
    return {
        name: ExternalAdapter(name)
        for name in ("ollama", "vertex_ai", "cloud_run", "pubsub", "quantum", "research")
    }
