"""osiris.compiler.backends — Pluggable quantum backend adapters."""

from .base import BackendAdapter
from .registry import BackendRegistry

__all__ = ["BackendAdapter", "BackendRegistry"]
