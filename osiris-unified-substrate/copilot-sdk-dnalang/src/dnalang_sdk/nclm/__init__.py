"""
OSIRIS NCLM — Non-Local Non-Causal Language Model
==================================================

Consolidated NCLM engine with interactive chat and full-screen TUI.
Zero external API dependencies. Fully sovereign. Air-gapped.

Modules:
  engine.py  — Core NCLM: ManifoldPoint, PilotWave, ConsciousnessField,
                IntentDeducer, CodeSwarm, NonCausalLM
  chat.py    — Interactive readline CLI chat with streaming, history, slash commands
  tui.py     — Full-screen Textual TUI: Cognitive Orchestration Shell
  tools.py   — Real tool dispatch: file ops, shell, webapp, research, quantum
"""

from .engine import (
    NCPhysics,
    ManifoldPoint,
    PilotWaveCorrelation,
    ConsciousnessField,
    IntentDeducer,
    CodeSwarm,
    NonCausalLM,
    get_nclm,
)

# Offline build: chat and remote tools are disabled.
NCLMChat = None
NCLMResponseGenerator = None
async def run_chat(*args, **kwargs):
    raise RuntimeError("Offline NCLM build: NCLM chat is disabled")

def dispatch_tool(*args, **kwargs):
    raise RuntimeError("Offline NCLM build: dispatch_tool is disabled")

# TUI functionality is disabled in offline build.
OsirisTUI = None
async def run_tui(*args, **kwargs):
    raise RuntimeError("Offline NCLM build: TUI is disabled")

__all__ = [
    "NCPhysics",
    "ManifoldPoint",
    "PilotWaveCorrelation",
    "ConsciousnessField",
    "IntentDeducer",
    "CodeSwarm",
    "NonCausalLM",
    "get_nclm",
    "NCLMChat",
    "NCLMResponseGenerator",
    "run_chat",
    "dispatch_tool",
    "OsirisTUI",
    "run_tui",
]
