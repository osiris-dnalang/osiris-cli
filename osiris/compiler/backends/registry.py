"""Backend registry — discover, register, and retrieve adapters."""

from typing import Dict, List, Optional, Type

from .base import BackendAdapter


class BackendRegistry:
    """Singleton registry for quantum backend adapters."""

    _adapters: Dict[str, BackendAdapter] = {}

    @classmethod
    def register(cls, adapter: BackendAdapter) -> None:
        """Register an instantiated adapter."""
        cls._adapters[adapter.name] = adapter

    @classmethod
    def get(cls, name: str) -> BackendAdapter:
        """Retrieve adapter by name. Raises KeyError if not found."""
        cls._ensure_loaded()
        if name not in cls._adapters:
            available = ", ".join(sorted(cls._adapters)) or "(none)"
            raise KeyError(
                f"Backend '{name}' not registered. Available: {available}"
            )
        return cls._adapters[name]

    @classmethod
    def list_backends(cls) -> List[str]:
        """List all registered backend names."""
        cls._ensure_loaded()
        return sorted(cls._adapters.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        cls._ensure_loaded()
        return name in cls._adapters

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Lazily auto-register built-in adapters on first access."""
        if cls._adapters:
            return
        cls._auto_discover()

    @classmethod
    def _auto_discover(cls) -> None:
        """Import built-in adapter modules so they self-register."""
        from . import sovereign_adapter  # always available
        try:
            from . import qiskit_adapter
        except Exception:
            pass
        try:
            from . import cirq_adapter
        except Exception:
            pass
        try:
            from . import pyquil_adapter
        except Exception:
            pass

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._adapters.clear()
