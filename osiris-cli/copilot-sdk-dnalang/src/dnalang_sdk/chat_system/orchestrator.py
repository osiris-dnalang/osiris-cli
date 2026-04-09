#!/usr/bin/env python3
"""
OSIRIS CHAT ORCHESTRATOR — Main Integration Layer
==================================================

Unifies all chat system components into a coherent, intelligent interface:
- Intent processor for NLP
- Hotkey engine for rapid interaction
- Universal input handler
- Auto-advancement for autonomous progression
- Agent swarm for multi-task execution
- Mentor protocol for teaching
- Agile orchestrator for project management
- Rich Chat TUI for beautiful interface

This is the main runtime that binds everything together.
"""

from __future__ import annotations
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime, timezone

from .intent_processor import IntentProcessor, create_intent_processor
from .hotkey_engine import HotkeyEngine, create_hotkey_engine
from .universal_input_processor import UniversalInputProcessor, create_input_processor
from .auto_advancement_engine import AutoAdvancementEngine, create_advancement_engine
from .agent_swarm import SpecialistAgentSwarm, create_agent_swarm
from .mentor_protocol import MentorProtocol, create_mentor_protocol
from .chat_tui import ChatTUI, create_chat_tui
from .agile_orchestrator import AgileOrchestrator, create_agile_orchestrator

logger = logging.getLogger(__name__)


class OSIRISChatOrchestrator:
    """
    Main orchestrator unifying all OSIRIS chat subsystems.
    
    Orchestrates:
    - Natural language understanding (intent processor)
    - Context-aware action generation (hotkey engine)
    - Input parsing (universal processor)
    - Autonomous task advancement
    - Multi-agent execution
    - Interactive mentoring
    - Project management
    - Rich TUI rendering
    """
    
    def __init__(
        self,
        state_dir: Optional[Path] = None,
        enable_tui: bool = True,
        enable_agents: bool = True,
        max_agents: int = 12,
    ):
        """
        Initialize the OSIRIS Chat Orchestrator.
        """
        self.state_dir = Path(state_dir) if state_dir else Path.home() / ".osiris"
        self.state_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize all subsystems
        self.intent_processor = create_intent_processor(state_dir=self.state_dir / "intent")
        self.hotkey_engine = create_hotkey_engine(max_hotkeys=8)
        self.input_processor = create_input_processor()
        self.advancement_engine = create_advancement_engine()
        self.tui = create_chat_tui() if enable_tui else None
        self.agent_swarm = create_agent_swarm(max_agents=max_agents) if enable_agents else None
        self.mentor = create_mentor_protocol()
        self.agile = create_agile_orchestrator()
        
        # State tracking
        self.session_start = datetime.now(timezone.utc)
        self.interaction_count = 0
        self.current_task_id: Optional[str] = None
        self.is_running = False
    
    async def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Main processing pipeline for user input.
        
        1. Parse input (detect type/structure)
        2. Deduce intent
        3. Generate response
        4. Advance task autonomously
        5. Suggest next actions (hotkeys)
        
        Returns result dict with response, hotkeys, progress, etc.
        """
        self.interaction_count += 1
        
        # Step 1: Parse input
        detected = self.input_processor.process(user_input)
        
        # Add to chat history
        if self.tui:
            self.tui.add_message("user", user_input, {
                "detected_type": detected.detected_type.value,
                "confidence": detected.confidence,
            })
        
        # Step 2: Deduce intent
        context = {
            "input_type": detected.detected_type.value,
            "previous_goal": (
                self.intent_processor.previous_intents[-1]
                if self.intent_processor.previous_intents else None
            ),
            "current_task": self.current_task_id,
        }
        
        intent = self.intent_processor.process(user_input, context)
        
        # Step 3: Generate response
        response = await self._generate_response(intent, detected)
        
        # Step 4: Auto-advance task
        if self.current_task_id:
            advancement = self.advancement_engine.auto_advance(self.current_task_id)
            if advancement:
                response["auto_advanced"] = advancement
        
        # Step 5: Generate hotkeys
        hotkeys = self.hotkey_engine.generate_hotkeys(
            intent_goal=intent.primary_goal,
            suggested_actions=intent.suggested_next_steps,
            current_trajectory=intent.trajectory,
        )
        
        # Build result
        result = {
            "intent": intent.to_dict(),
            "response": response,
            "hotkeys": [
                {
                    "key": h.key,
                    "description": h.description,
                    "type": h.action_type.value,
                    "probability": h.success_probability,
                }
                for h in hotkeys
            ],
            "progress": (
                self.advancement_engine.get_task_summary(self.current_task_id)
                if self.current_task_id else None
            ),
        }
        
        # Add to chat history
        if self.tui:
            self.tui.add_message("osiris", response.get("summary", ""))
        
        return result
    
    async def _generate_response(self, intent: Any, detected: Any) -> Dict[str, Any]:
        """
        Generate response based on intent and detected input.
        """
        # Spawn agent tasks based on intent
        agent_reports = []
        if self.agent_swarm and intent.actions:
            tasks = [
                self._intent_action_to_agent_task(action)
                for action in intent.actions[:3]  # Limit to 3 parallel tasks
            ]
            
            for task in tasks:
                self.agent_swarm.assign_task(task)
            
            # Let agents work
            agent_reports = await self.agent_swarm.work()
        
        # Synthesize findings
        synthesis = self.agent_swarm.synthesize_findings() if self.agent_swarm else {}
        
        # Create main response
        response = {
            "summary": f"Processing: {intent.primary_goal}",
            "details": {
                "goal": intent.primary_goal,
                "trajectory": intent.trajectory,
                "suggested_next": intent.suggested_next_steps,
                "confidence": intent.confidence,
            },
            "agent_reports": [r.to_dict() for r in agent_reports] if agent_reports else [],
            "agent_synthesis": synthesis,
        }
        
        return response
    
    def _intent_action_to_agent_task(self, action: Any) -> Any:
        """Convert intent action to agent task"""
        from .agent_swarm import AgentTask
        
        return AgentTask(
            task_id=f"task-{self.interaction_count}-{action.action}",
            description=action.action,
            domain=action.domain,
            priority=5,
            context=action.parameters,
        )
    
    async def interactive_session(self) -> None:
        """
        Main interactive chat session.
        """
        if self.tui:
            self.tui.render_welcome()
        
        self.is_running = True
        
        try:
            while self.is_running:
                # Get input
                if self.tui:
                    user_input = self.tui.render_input_prompt()
                else:
                    user_input = input("OSIRIS> ").strip()
                
                # Check for control commands
                if user_input.lower() == "q":
                    break
                elif user_input.lower() == "?":
                    self._show_help()
                    continue
                elif not user_input:
                    continue
                
                # Process input
                result = await self.process_user_input(user_input)
                
                # Render output
                if self.tui:
                    self._render_result(result)
                else:
                    self._print_result(result)
        
        except KeyboardInterrupt:
            logger.info("Session interrupted by user")
        finally:
            self.is_running = False
            if self.tui:
                self.tui.render_status_line("Session ended. Saving state...")
            self.intent_processor.save_state()
    
    def _render_result(self, result: Dict[str, Any]) -> None:
        """Render result using TUI"""
        if not self.tui:
            return
        
        # Render response
        response = result.get("response", {})
        self.tui.render_panel(
            "OSIRIS Response",
            response.get("summary", "Processing..."),
            style="green"
        )
        
        # Render hotkeys
        hotkeys = result.get("hotkeys", [])
        hotkey_list = [(h["key"], h["description"]) for h in hotkeys]
        self.tui.render_hotkeys(hotkey_list)
        
        # Render progress if available
        progress = result.get("progress")
        if progress:
            self.tui.render_progress(
                progress.get("goal", "Task"),
                progress.get("progress", 0.0),
                progress.get("phase")
            )
    
    def _print_result(self, result: Dict[str, Any]) -> None:
        """Print result in plain text"""
        response = result.get("response", {})
        print(f"\nOSIRIS: {response.get('summary', 'Processing...')}")
        
        hotkeys = result.get("hotkeys", [])
        if hotkeys:
            print("\nHOTKEYS:")
            for h in hotkeys:
                print(f"  [{h['key'].upper()}] {h['description']}")
    
    def _show_help(self) -> None:
        """Show help information"""
        help_text = """
OSIRIS Chat Commands:
  [?]  Show this help
  [q]  Quit OSIRIS
  [h]  Show chat history
  [p]  Show progress
  [m]  Show metrics
  
For any task, just describe it naturally. OSIRIS will:
  1. Understand your intent
  2. Suggest next steps (hotkeys)
  3. Execute with agent team
  4. Advance automatically
  5. Teach along the way

Use letter keys (a, s, d, etc.) for instant actions.
"""
        if self.tui:
            self.tui.render_panel("Help", help_text)
        else:
            print(help_text)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of this session"""
        duration = (datetime.now(timezone.utc) - self.session_start).total_seconds()
        
        return {
            "duration_seconds": duration,
            "interactions": self.interaction_count,
            "chat_messages": len(self.tui.chat_history) if self.tui else 0,
            "tasks_created": len(self.agile.tasks),
            "agents_used": len(self.agent_swarm.agents) if self.agent_swarm else 0,
            "agent_reports": len(self.agent_swarm.completed_reports) if self.agent_swarm else 0,
        }


# Factory function
def create_chat_orchestrator(
    state_dir: Optional[Path] = None,
    enable_tui: bool = True,
    enable_agents: bool = True,
) -> OSIRISChatOrchestrator:
    """Create a chat orchestrator"""
    return OSIRISChatOrchestrator(
        state_dir=state_dir,
        enable_tui=enable_tui,
        enable_agents=enable_agents,
    )
