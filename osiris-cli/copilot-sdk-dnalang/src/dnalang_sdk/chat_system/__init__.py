#!/usr/bin/env python3
"""
OSIRIS Chat System — Intelligent Chatbot-Driven Interface
==========================================================

Unified module for intelligent chat-driven OSIRIS interface with:
- Intent processor (NLP-based goal deduction)
- Hotkey engine (context-aware action layer)
- Universal input processor (any data type)
- Auto-advancement engine (autonomous task progression)
- Specialist agent swarm (multi-agent execution)
- Mentor protocol (teaching while building)
- Chat TUI (rich terminal interface)
- Agile orchestrator (project management)
"""

from .intent_processor import (
    IntentProcessor,
    UserIntent,
    IntentAction,
    create_intent_processor,
)

from .hotkey_engine import (
    HotkeyEngine,
    HotkeyAction,
    ActionType,
    HotkeyPriority,
    create_hotkey_engine,
)

from .universal_input_processor import (
    UniversalInputProcessor,
    DetectedInput,
    InputType,
    create_input_processor,
)

from .auto_advancement_engine import (
    AutoAdvancementEngine,
    TaskPhase,
    AvailableStep,
    TaskState,
    AutoAdvanceStrategy,
    create_advancement_engine,
)

from .agent_swarm import (
    SpecialistAgent,
    SpecialistAgentSwarm,
    AgentTask,
    AgentReport,
    AgentRole,
    AgentState,
    create_agent_swarm,
)

from .mentor_protocol import (
    MentorProtocol,
    MentorMode,
    CapabilityLevel,
    TeachingExplanation,
    TeachableMoment,
    create_mentor_protocol,
)

from .quantum_supremacy import (
    QasmGenerationResult,
    compute_linear_xeb,
    generate_recursive_qasm,
    generate_surface_code_qasm,
    optional_qiskit_available,
    save_qasm_file,
    world_record_qasm_summary,
)

from .chat_tui import (
    ChatTUI,
    ChatMessage,
    create_chat_tui,
)

from .agile_orchestrator import (
    AgileOrchestrator,
    Sprint,
    Task,
    TaskStatus,
    Priority,
    create_agile_orchestrator,
)

from .memory_graph import (
    MemoryGraph,
    MemoryNode,
    MemoryEdge,
    create_memory_graph,
)

from .meta_reasoner import (
    MetaReasoner,
    StrategyRecord,
    create_meta_reasoner,
)

__all__ = [
    # Intent
    "IntentProcessor",
    "UserIntent",
    "IntentAction",
    "create_intent_processor",
    
    # Hotkeys
    "HotkeyEngine",
    "HotkeyAction",
    "ActionType",
    "HotkeyPriority",
    "create_hotkey_engine",
    
    # Input
    "UniversalInputProcessor",
    "DetectedInput",
    "InputType",
    "create_input_processor",
    
    # Advancement
    "AutoAdvancementEngine",
    "TaskPhase",
    "AvailableStep",
    "TaskState",
    "AutoAdvanceStrategy",
    "create_advancement_engine",
    
    # Agents
    "SpecialistAgent",
    "SpecialistAgentSwarm",
    "AgentTask",
    "AgentReport",
    "AgentRole",
    "AgentState",
    "create_agent_swarm",
    
    # Mentoring
    "MentorProtocol",
    "MentorMode",
    "CapabilityLevel",
    "TeachingExplanation",
    "TeachableMoment",
    "create_mentor_protocol",
    
    # Memory
    "MemoryGraph",
    "MemoryNode",
    "MemoryEdge",
    "create_memory_graph",
    
    # Meta Reasoner
    "MetaReasoner",
    "StrategyRecord",
    "create_meta_reasoner",
    
    # TUI
    "ChatTUI",
    "ChatMessage",
    "create_chat_tui",
    
    # Agile
    "AgileOrchestrator",
    "Sprint",
    "Task",
    "TaskStatus",
    "Priority",
    "create_agile_orchestrator",
]

__version__ = "1.0.0"
__description__ = "OSIRIS Chat System - Intelligent Multi-Agent Chatbot Interface"
