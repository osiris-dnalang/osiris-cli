#!/usr/bin/env python3
"""
OSIRIS CHAT TUI — Rich Terminal User Interface
===============================================

Intelligent chat-first interface with:
- Clean, intuitive TUI layout
- Persistent input field
- Chat history panel
- Hotkey action panel
- Real-time progress updates

Uses Rich library for beautiful terminal rendering.
No command syntax required - pure natural language.
"""

from __future__ import annotations
import logging
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime, timezone

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.text import Text
    from rich.syntax import Syntax
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A message in chat history"""
    role: str  # "user", "osiris", "system"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }


class ChatTUI:
    """
    Rich terminal UI for OSIRIS chat interface.
    """
    
    def __init__(self, width: int = 120, enable_rich: bool = True):
        self.width = width
        self.enable_rich = enable_rich and HAS_RICH
        
        if self.enable_rich:
            self.console = Console(width=width, force_terminal=True)
        else:
            self.console = None
        
        self.chat_history: List[ChatMessage] = []
        self.max_history = 100
    
    def render_welcome(self) -> None:
        """Render welcome screen"""
        if self.enable_rich:
            welcome_text = """
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                              ║
║  🌀 OSIRIS — Omega System Integrated Runtime Intelligence System                            ║
║     v6.0.0 | Quantum-Native Chatbot-Driven Interface                                        ║
║     Gen 6 Cognitive Shell | DNA::}{::lang v51.843 | Agile Defense Systems                  ║
║                                                                                              ║
║  ✨ Welcome to the Chat-First OSIRIS Experience                                             ║
║     • Type naturally (no commands or syntax required)                                        ║
║     • OSIRIS infers your intent and advances your work automatically                        ║
║     • Press [a], [s], [d]... for context-aware actions                                      ║
║     • Type [?] for help or [q] to quit                                                      ║
║                                                                                              ║
║  💡 Pro Tip: OSIRIS can help with quantum, coding, analysis, research,                     ║
║     system design, data science, and much more. Just ask!                                   ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
"""
            self.console.print(welcome_text)
        else:
            print("OSIRIS v6.0.0 - Chat-First Interface")
            print("Type naturally, no commands. [?] for help, [q] to quit.")
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Add message to history"""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )
        
        self.chat_history.append(message)
        
        # Keep history bounded
        if len(self.chat_history) > self.max_history:
            self.chat_history.pop(0)
        
        return message
    
    def render_chat_history(self, max_messages: int = 15) -> None:
        """Render recent chat messages"""
        if not self.chat_history:
            return
        
        recent = self.chat_history[-max_messages:]
        
        if self.enable_rich:
            for msg in recent:
                self._render_message_rich(msg)
        else:
            for msg in recent:
                self._render_message_plain(msg)
    
    def _render_message_rich(self, msg: ChatMessage) -> None:
        """Render message with Rich formatting"""
        if msg.role == "user":
            text = Text(f"You: {msg.content}", style="cyan")
            self.console.print(text)
        elif msg.role == "osiris":
            text = Text(f"OSIRIS: {msg.content}", style="green")
            self.console.print(text)
        else:
            text = Text(f"[{msg.role}] {msg.content}", style="dim")
            self.console.print(text)
    
    def _render_message_plain(self, msg: ChatMessage) -> None:
        """Render message plainly"""
        prefix = {
            "user": "You",
            "osiris": "OSIRIS",
        }.get(msg.role, msg.role)
        print(f"{prefix}: {msg.content}")
    
    def render_input_prompt(self) -> str:
        """Render input prompt and get user input"""
        if self.enable_rich:
            self.console.print("\n" + "─" * self.width)
            prompt_text = Text("💬 Your turn (natural language): ", style="bold yellow")
            self.console.print(prompt_text, end="")
        else:
            print("\nYour turn: ", end="")
        
        return input()
    
    def render_hotkeys(self, hotkeys: List[tuple]) -> None:
        """
        Render hotkey action list.
        
        Args:
            hotkeys: List of (key, description) tuples
        """
        if not hotkeys:
            return
        
        if self.enable_rich:
            self.console.print("\n" + "═" * self.width)
            self.console.print("[bold cyan]⚡ HOTKEY ACTIONS[/bold cyan]")
            
            for i, (key, desc) in enumerate(hotkeys, 1):
                key_text = Text(f"[{key.upper()}]", style="bold yellow")
                desc_text = Text(f" {desc}", style="white")
                line = Text()
                line.append(key_text)
                line.append(desc_text)
                self.console.print(line)
        else:
            print("\n" + "─" * self.width)
            print("HOTKEY ACTIONS:")
            for key, desc in hotkeys:
                print(f"[{key.upper()}] {desc}")
    
    def render_progress(
        self,
        task_name: str,
        progress: float,  # 0.0-1.0
        current_step: Optional[str] = None,
    ) -> None:
        """Render task progress"""
        if self.enable_rich:
            bar_length = 40
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            progress_text = Text()
            progress_text.append(f"{task_name}: ", style="bold")
            progress_text.append(f"[{bar}] {progress:.0%}", style="green")
            
            self.console.print(progress_text)
            
            if current_step:
                step_text = Text(f"  → {current_step}", style="cyan dim")
                self.console.print(step_text)
        else:
            bar_length = 20
            filled = int(bar_length * progress)
            bar = "=" * filled + "-" * (bar_length - filled)
            print(f"{task_name}: [{bar}] {progress:.0%}")
            if current_step:
                print(f"  → {current_step}")
    
    def render_error(self, message: str) -> None:
        """Render error message"""
        if self.enable_rich:
            panel = Panel(
                Text(message, style="bold red"),
                title="⚠ Error",
                border_style="red",
            )
            self.console.print(panel)
        else:
            print(f"ERROR: {message}")
    
    def render_success(self, message: str) -> None:
        """Render success message"""
        if self.enable_rich:
            panel = Panel(
                Text(message, style="bold green"),
                title="✓ Success",
                border_style="green",
            )
            self.console.print(panel)
        else:
            print(f"SUCCESS: {message}")
    
    def render_code(self, code: str, language: str = "python") -> None:
        """Render code block"""
        if self.enable_rich and HAS_RICH:
            try:
                from rich.syntax import Syntax
                syntax = Syntax(code, language, theme="monokai", line_numbers=True)
                self.console.print(syntax)
            except:
                self.console.print(code)
        else:
            print(code)
    
    def render_table(self, data: List[Dict[str, Any]], title: str = "") -> None:
        """Render table"""
        if not data:
            return
        
        if self.enable_rich:
            table = Table(title=title)
            
            # Add columns
            for key in data[0].keys():
                table.add_column(key.title())
            
            # Add rows
            for row in data:
                table.add_row(*[str(v) for v in row.values()])
            
            self.console.print(table)
        else:
            headers = list(data[0].keys())
            print(" | ".join(headers))
            print("-" * len(" | ".join(headers)))
            for row in data:
                print(" | ".join(str(v) for v in row.values()))
    
    def render_panel(self, title: str, content: str, style: str = "cyan") -> None:
        """Render a content panel"""
        if self.enable_rich:
            panel = Panel(
                Text(content, style=style),
                title=title,
                border_style=style,
            )
            self.console.print(panel)
        else:
            print(f"\n{title}:")
            print(content)
    
    def render_status_line(self, status: str) -> None:
        """Render status line"""
        if self.enable_rich:
            status_text = Text(f"⚙ {status}", style="dim white")
            self.console.print(status_text)
        else:
            print(f"[*] {status}")
    
    def clear_screen(self) -> None:
        """Clear screen"""
        if self.enable_rich:
            self.console.clear()
        else:
            print("\033[2J\033[H", end="")
    
    def get_chat_context(self, max_messages: int = 10) -> str:
        """Get recent chat context as string"""
        recent = self.chat_history[-max_messages:]
        lines = []
        for msg in recent:
            lines.append(f"{msg.role}: {msg.content}")
        return "\n".join(lines)
    
    def export_chat(self, filepath: Path) -> None:
        """Export chat history to file"""
        import json
        
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(self.chat_history),
            "messages": [msg.to_dict() for msg in self.chat_history],
        }
        
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Chat exported to {filepath}")
        except Exception as e:
            logger.error(f"Could not export chat: {e}")


# Factory function
def create_chat_tui(width: int = 120) -> ChatTUI:
    """Create a chat TUI"""
    return ChatTUI(width=width)
