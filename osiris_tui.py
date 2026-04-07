#!/usr/bin/env python3
"""
OSIRIS TUI - Chat-Native Terminal Interface
============================================

Core implementation of the chat-first, intent-driven TUI.
Builds on Rich + async agents.
"""

import os
import sys
import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import threading
from queue import Queue

# TUI framework
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.table import Table
except ImportError:
    print("ERROR: Rich library not installed")
    print("Install with: pip install rich")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════════════════════
# 1. INTENT ENGINE
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedIntent:
    """User intent parsed from natural language"""
    primary: str  # Main action: "analyze", "execute", "visualize", etc.
    secondary: List[str]  # Related actions
    confidence: float  # 0.0-1.0
    context: Dict[str, Any]  # Extracted context
    suggested_hotkeys: List['HotKeyAction'] = field(default_factory=list)

class IntentEngine:
    """Parse natural language intent"""
    
    INTENT_KEYWORDS = {
        'analyze': ['analyze', 'examine', 'check', 'validate', 'test', 'review'],
        'execute': ['run', 'execute', 'go', 'do it', 'start', 'begin'],
        'visualize': ['show', 'plot', 'graph', 'display', 'see', 'draw'],
        'optimize': ['improve', 'optimize', 'enhance', 'speed up', 'refactor'],
        'discover': ['find', 'detect', 'discover', 'search', 'explore'],
        'explain': ['why', 'how', 'explain', 'understand', 'help'],
        'publish': ['publish', 'submit', 'share', 'upload', 'document'],
    }
    
    def parse(self, user_input: str) -> DetectedIntent:
        """Detect intent from user input"""
        lower_input = user_input.lower()
        
        primary = None
        secondary = []
        confidence = 0.0
        
        # Match keywords
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in lower_input:
                    if primary is None:
                        primary = intent
                        confidence = 0.8
                    else:
                        secondary.append(intent)
        
        # Fallback
        if primary is None:
            primary = "interact"  # Neutral intent
            confidence = 0.5
        
        return DetectedIntent(
            primary=primary,
            secondary=secondary,
            confidence=confidence,
            context=self._extract_context(user_input),
            suggested_hotkeys=[]
        )
    
    def _extract_context(self, text: str) -> Dict[str, Any]:
        """Extract structured context from text"""
        context = {}
        
        # Detect domain
        if any(x in text.lower() for x in ['circuit', 'qubit', 'gate', 'qasm']):
            context['domain'] = 'quantum'
        elif any(x in text.lower() for x in ['data', 'plot', 'graph', 'metric']):
            context['domain'] = 'data'
        else:
            context['domain'] = 'general'
        
        # Detect data presence
        has_code = (text.count('{') > 2 or text.count('def ') > 0)
        has_json = (text.count('{') + text.count('[') > 4)
        
        context['has_code'] = has_code
        context['has_data'] = has_json
        
        return context


# ════════════════════════════════════════════════════════════════════════════════
# 2. HOTKEY ACTION SYSTEM
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class HotKeyAction:
    """Executable action triggered by hotkey"""
    key: int  # 1-9
    label: str
    description: str
    action: str  # Executable action
    
    def display(self) -> str:
        return f"[{self.key}] {self.label}"

class HotKeyGenerator:
    """Generate context-aware hotkeys"""
    
    ACTIONS_BY_INTENT = {
        'analyze': [
            HotKeyAction(1, "Statistical test", "Run rigorous validation", "analyze:stats"),
            HotKeyAction(2, "Visualize", "Plot results", "analyze:plot"),
            HotKeyAction(3, "Report", "Generate summary", "analyze:report"),
        ],
        'execute': [
            HotKeyAction(1, "Run now", "Execute immediately", "execute"),
            HotKeyAction(2, "Simulate first", "Test before real hardware", "execute:simulate"),
            HotKeyAction(3, "Spawn agents", "Parallel verification", "execute:agents"),
        ],
        'discover': [
            HotKeyAction(1, "Expand hypothesis", "Deepen analysis", "discover:expand"),
            HotKeyAction(2, "Cross-check", "Verify with different method", "discover:crosscheck"),
            HotKeyAction(3, "Publish", "Share to Zenodo", "discover:publish"),
        ],
        'interact': [
            HotKeyAction(1, "Tell me more", "Expand on this", "interact:expand"),
            HotKeyAction(2, "Examples", "Show concrete examples", "interact:examples"),
            HotKeyAction(3, "Next steps", "What's recommended?", "interact:next"),
        ]
    }
    
    @classmethod
    def generate(cls, intent: DetectedIntent) -> List[HotKeyAction]:
        """Generate hotkeys for detected intent"""
        return cls.ACTIONS_BY_INTENT.get(intent.primary, cls.ACTIONS_BY_INTENT['interact'])


# ════════════════════════════════════════════════════════════════════════════════
# 3. AGENT ORCHESTRATOR
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class Agent:
    """Autonomous agent"""
    id: str
    goal: str
    status: str = "pending"  # pending, running, complete, error
    result: Optional[str] = None
    
    def __str__(self):
        return f"Agent[{self.id}: {self.status}]"

class AgentOrchestrator:
    """Spawn and manage autonomous agents"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.task_queue: Queue = Queue()
    
    def spawn(self, agent_type: str, goal: str) -> str:
        """Spawn new agent"""
        agent_id = f"{agent_type}_{len(self.agents)}"
        agent = Agent(agent_id=agent_id, goal=goal)
        
        self.agents[agent_id] = agent
        self.task_queue.put((agent_id, agent_type, goal))
        
        return agent_id
    
    def get_status(self, agent_id: str) -> Optional[Agent]:
        """Get agent status"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Agent]:
        """List all agents"""
        return list(self.agents.values())


# ════════════════════════════════════════════════════════════════════════════════
# 4. CONVERSATION MEMORY
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    timestamp: str
    role: str  # "user", "osiris", "agent"
    content: str
    intent: Optional[str] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'role': self.role,
            'content': self.content,
            'intent': self.intent,
        }

class ConversationMemory:
    """Persistent conversation history"""
    
    def __init__(self, max_turns: int = 100):
        self.turns: List[ConversationTurn] = []
        self.max_turns = max_turns
    
    def add(self, role: str, content: str, intent: Optional[str] = None):
        """Add turn to memory"""
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            intent=intent
        )
        self.turns.append(turn)
        
        # Trim if too long
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
    
    def get_context(self, last_n: int = 5) -> str:
        """Get recent conversation context"""
        recent = self.turns[-last_n:]
        return "\n".join(f"{t.role}: {t.content[:100]}" for t in recent)
    
    def save(self, filepath: str):
        """Persist to file"""
        with open(filepath, 'w') as f:
            json.dump([t.to_dict() for t in self.turns], f, indent=2)


# ════════════════════════════════════════════════════════════════════════════════
# 5. TUI LAYOUT + RENDERING
# ════════════════════════════════════════════════════════════════════════════════

class OsirisTUI:
    """OSIRIS Terminal User Interface"""
    
    def __init__(self):
        self.console = Console(width=140, height=40)
        self.intent_engine = IntentEngine()
        self.agent_orchestrator = AgentOrchestrator()
        self.memory = ConversationMemory()
        
        self.chat_history: List[str] = []
        self.current_hotkeys: List[HotKeyAction] = []
    
    def render_header(self):
        """Render top banner"""
        title = Text("⚛ OSIRIS v2.0 - Autonomous Quantum Discovery System", style="bold cyan")
        subtitle = Text("Chat-native quantum research | Intent-driven | Agent-powered", style="dim")
        
        self.console.print(Panel(
            title + "\n" + subtitle,
            style="blue",
            expand=False
        ))
    
    def render_chat_pane(self):
        """Render chat history"""
        if self.chat_history:
            for msg in self.chat_history[-15:]:  # Last 15 messages
                self.console.print(msg)
    
    def render_hotkeys(self):
        """Render available hotkeys"""
        if self.current_hotkeys:
            hotkey_text = "  Available: " + " | ".join(
                f"[bold]{ak.display()}[/bold]" for ak in self.current_hotkeys[:5]
            )
            self.console.print(hotkey_text, style="dim yellow")
    
    def render_status_bar(self):
        """Render bottom status bar"""
        agents_count = len(self.agent_orchestrator.list_agents())
        status_text = f"Agents: {agents_count} | Turns: {len(self.memory.turns)} | Ready"
        
        self.console.print(
            Panel(status_text, style="dim green", expand=False),
            style="dim"
        )
    
    def add_message(self, role: str, content: str):
        """Add message to chat history"""
        if role == "user":
            self.chat_history.append(f"[bold cyan]You:[/bold cyan] {content[:80]}")
        elif role == "osiris":
            self.chat_history.append(f"[bold magenta]OSIRIS:[/bold magenta] {content[:100]}")
        elif role == "agent":
            self.chat_history.append(f"[bold green]Agent:[/bold green] {content[:100]}")
    
    def show_prompt(self) -> str:
        """Show input prompt and get user input"""
        self.console.print()
        user_input = self.console.input("[bold cyan]> [/bold cyan]").strip()
        return user_input
    
    def process_hotkey(self, key: int) -> Optional[str]:
        """Process hotkey press"""
        if key < 1 or key > len(self.current_hotkeys):
            return None
        
        action = self.current_hotkeys[key - 1]
        self.console.print(f"→ Executing: {action.label}")
        return action.action
    
    def respond(self, intent: DetectedIntent, response: str):
        """OSIRIS responds"""
        self.add_message("osiris", response)
        self.console.print(f"\n[bold magenta]OSIRIS:[/bold magenta] {response}\n")
        
        # Gen hotkeys
        self.current_hotkeys = HotKeyGenerator.generate(intent)
        self.render_hotkeys()


# ════════════════════════════════════════════════════════════════════════════════
# 6. MAIN INTERACTION LOOP
# ════════════════════════════════════════════════════════════════════════════════

class OsirisCore:
    """Main OSIRIS execution core"""
    
    def __init__(self):
        self.tui = OsirisTUI()
    
    def run(self):
        """Start OSIRIS"""
        self.tui.render_header()
        self.tui.console.print("\n[dim]Starting autonomous quantum discovery system...[/dim]\n")
        
        while True:
            try:
                user_input = self.tui.show_prompt()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self.tui.console.print("[dim]Saving session...[/dim]")
                    self.tui.memory.save("/tmp/osiris_session.json")
                    break
                
                # Check for hotkey
                if user_input.isdigit():
                    action = self.tui.process_hotkey(int(user_input))
                    if action:
                        self._execute_action(action)
                        continue
                
                # Process natural language intent
                self.tui.add_message("user", user_input)
                intent = self.tui.intent_engine.parse(user_input)
                self.tui.memory.add("user", user_input, intent.primary)
                
                # Generate response
                response = self._generate_response(user_input, intent)
                self.tui.respond(intent, response)
                self.tui.memory.add("osiris", response)
            
            except KeyboardInterrupt:
                self.tui.console.print("\n[dim]Interrupted. Save state? (y/n)[/dim]")
                if input().lower() == 'y':
                    self.tui.memory.save("/tmp/osiris_session.json")
                break
    
    def _generate_response(self, user_input: str, intent: DetectedIntent) -> str:
        """Generate OSIRIS response"""
        
        responses = {
            'analyze': f"I'm analyzing your input (detected: {intent.context.get('domain', 'general')}). Running analysis...",
            'execute': "Ready to execute. Using safety-first defaults: simulate before real hardware.",
            'discover': "Interesting discovery potential. Let's validate rigorously.",
            'explain': "Here's my analysis...",
            'interact': f"Your input detected domain: {intent.context.get('domain')}. How can I help?",
        }
        
        return responses.get(intent.primary, "I understand. What would you like to do?")
    
    def _execute_action(self, action: str):
        """Execute hotkey action"""
        action_type, action_detail = action.split(':') if ':' in action else (action, 'default')
        
        if action == 'execute':
            agent_id =self.tui.agent_orchestrator.spawn("executor", "Run quantum experiment")
            self.tui.console.print(f"[green]✓ Spawned {agent_id}[/green]")
        
        elif action == 'analyze:stats':
            self.tui.console.print("[yellow]Running statistical validation...[/yellow]")
        
        elif action == 'discover:publish':
            self.tui.console.print("[magenta]Preparing for Zenodo publication...[/magenta]")
        
        else:
            self.tui.console.print(f"[dim]Executing: {action}[/dim]")


# ════════════════════════════════════════════════════════════════════════════════
# 7. ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Launch OSIRIS TUI"""
    osiris = OsirisCore()
    osiris.run()

if __name__ == "__main__":
    main()
