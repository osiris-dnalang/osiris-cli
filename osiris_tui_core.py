#!/usr/bin/env python3
"""
OSIRIS Chat-Native TUI
Full-screen chat interface with intent inference, agent orchestration, and real-time benchmarking.
Single entry point: `python osiris_tui_core.py` or `osiris` command
"""

import os
import io
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from contextlib import redirect_stdout, redirect_stderr

# Textual TUI framework
try:
    from textual.app import App, ComposeResult, on
    from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
    from textual.widgets import Header, Footer, Static, Input, Label, Button, RichLog
    from textual.binding import Binding
    from textual import work
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel
    from rich.console import Console
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False

# OSIRIS components
from osiris_intent_engine import IntentEngine, IntentType
from osiris_quantum_benchmarker import QuantumHardwareBenchmarker, BenchmarkResult
from osiris_auto_discovery import AutoDiscoveryPipeline, ExperimentConfig
from osiris_orchestrator import campaign_week1_foundation, campaign_week1_adaptive
from osiris_rqc_orchestrator import ResearchOrchestrator

console = Console()

@dataclass
class ChatMessage:
    """Chat message dataclass"""
    sender: str  # 'user' or 'osiris'
    content: str
    timestamp: str
    message_type: str  # 'text', 'code', 'result', 'error'

class ChatHeader(Static):
    """OSIRIS header with status"""
    
    def __init__(self):
        super().__init__()
        self.status = "ready"
        self.current_task = ""
    
    def render(self) -> str:
        """Render header"""
        status_color = "green" if self.status == "ready" else "yellow"
        task_text = f" | Task: {self.current_task}" if self.current_task else ""
        
        header = f"""[bold cyan]⚛  OSIRIS Quantum Discovery System[/bold cyan]
[{status_color}]● {self.status.upper()}{task_text}[/{status_color}]
[dim]IBM Quantum Hardware Benchmarking & Autonomous Research[/dim]
════════════════════════════════════════════════════════════"""
        return header

class ChatLog(RichLog):
    """Chat message log with formatting"""
    
    def add_message(self, message: ChatMessage):
        """Add formatted message to log"""
        if message.sender == "user":
            prefix = "❯ You"
            color = "cyan"
        else:
            prefix = "⚛ Osiris"
            color = "green"
        
        timestamp = message.timestamp.split('T')[1][:8] if 'T' in message.timestamp else message.timestamp
        
        if message.message_type == "error":
            self.write(f"[red]{prefix}: {message.content}[/red]")
        elif message.message_type == "result":
            self.write(f"[{color}]{prefix}:[/] {message.content}")
        else:
            self.write(f"[{color}]{prefix}:[/] {message.content}")

class HotkeysPanel(Static):
    """Dynamic hotkeys based on context"""
    
    def __init__(self):
        super().__init__()
        self.hotkeys = self._default_hotkeys()
    
    def _default_hotkeys(self) -> Dict[str, str]:
        return {
            "[1]": "Benchmark",
            "[2]": "Run Exp",
            "[3]": "Status",
            "[4]": "Deploy",
            "[5]": "Pipeline",
            "[6]": "Help",
        }
    
    def update_hotkeys(self, hotkeys: Dict[str, str]):
        """Update hotkeys for current context"""
        self.hotkeys = hotkeys
    
    def render(self) -> str:
        """Render hotkeys panel"""
        hotkey_text = " ".join([f"{k}→{v}" for k, v in self.hotkeys.items()])
        return Panel(
            hotkey_text,
            title="Quick Actions",
            border_style="dim blue"
        )

class StatusPanel(Static):
    """System status panel"""
    
    def __init__(self):
        super().__init__()
        self.queue_size = 0
        self.last_result = ""
        self.token_status = "unknown"
    
    def update_status(self, **kwargs):
        """Update status info"""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def render(self) -> str:
        """Render status"""
        status_table = Table(title="System Status", show_header=False, box=None)
        status_table.add_row("Queue:", str(self.queue_size))
        status_table.add_row("Tokens:", self.token_status)
        status_table.add_row("Mode:", "Benchmarking")
        return status_table

class OsirisApp:
    """OSIRIS Chat-Native TUI Application"""
    
    def __init__(self):
        self.intent_engine = IntentEngine()
        self.benchmarker = None
        self.pipeline = None
        self.orchestrator = None
        self.chat_history: List[ChatMessage] = []
        self.token = os.getenv('IBM_QUANTUM_TOKEN')
        self.zenodo_token = os.getenv('ZENODO_TOKEN')
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize OSIRIS components"""
        
        # Check tokens
        if self.token:
            print("✓ IBM Quantum token loaded")
        if self.zenodo_token:
            print("✓ Zenodo token loaded")
        
        # Initialize benchmarker
        try:
            self.benchmarker = QuantumHardwareBenchmarker(api_token=self.token)
            print("✓ Quantum benchmarker initialized")
        except Exception as e:
            print(f"⚠ Benchmarker init warning: {e}")
        
        # Initialize pipeline
        try:
            self.pipeline = AutoDiscoveryPipeline(api_token=self.token)
            print("✓ Discovery pipeline initialized")
        except Exception as e:
            print(f"⚠ Pipeline init warning: {e}")

        # Initialize orchestrator
        try:
            self.orchestrator = ResearchOrchestrator()
            print("✓ Research orchestrator initialized")
        except Exception as e:
            print(f"⚠ Orchestrator init warning: {e}")
    
    async def process_user_input(self, user_input: str) -> str:
        """Process user input through intent engine and execute"""
        
        # Parse intent
        intent = self.intent_engine.parse_intent(user_input)
        
        # Add to history
        msg = ChatMessage(
            sender="user",
            content=user_input,
            timestamp=datetime.now().isoformat(),
            message_type="text"
        )
        self.chat_history.append(msg)
        
        # Process based on intent
        response = await self._execute_intent(intent)
        
        # Add response to history
        resp_msg = ChatMessage(
            sender="osiris",
            content=response,
            timestamp=datetime.now().isoformat(),
            message_type="result"
        )
        self.chat_history.append(resp_msg)
        
        return response
    
    async def _execute_intent(self, intent) -> str:
        """Execute intent and return response"""
        
        if intent.intent_type == IntentType.BENCHMARK:
            return await self._handle_benchmark(intent)
        elif intent.intent_type == IntentType.EXPERIMENT:
            return await self._handle_experiment(intent)
        elif intent.intent_type == IntentType.DEPLOY:
            return await self._handle_deploy(intent)
        elif intent.intent_type == IntentType.ORCHESTRATE:
            return await self._handle_orchestrate(intent)
        elif intent.intent_type == IntentType.STATUS:
            return await self._handle_status(intent)
        elif intent.intent_type == IntentType.HELP:
            return self._handle_help()
        else:
            return f"Intent: {intent.intent_type.value} (confidence: {intent.confidence:.1%})\nActions: {chr(10).join(intent.suggested_actions[:3])}"
    
    async def _handle_benchmark(self, intent) -> str:
        """Handle benchmark intent"""
        
        response = "⚛ Starting quantum hardware benchmarking...\n"
        response += "📊 Testing extreme shot/depth parameters\n\n"
        
        if not self.benchmarker:
            return response + "⚠ Benchmarker not initialized"
        
        try:
            # Run benchmark
            results = self.benchmarker.benchmark_all_backends(extreme_mode=True)
            
            response += "✓ Benchmark complete!\n\n"
            
            # Summarize results
            for backend, backend_results in results.items():
                if backend_results:
                    best = max(backend_results, key=lambda r: r.xeb_score)
                    response += f"{backend}: Best XEB={best.xeb_score:.4f}, Fidelity={best.avg_fidelity:.4f}\n"
            
            # Export
            filename = self.benchmarker.export_results('quantum_benchmark_results.json')
            response += f"\n📁 Results saved to {filename}\n"
            
        except Exception as e:
            response = f"⚠ Benchmark error: {e}"
        
        return response
    
    async def _handle_experiment(self, intent) -> str:
        """Handle experiment execution intent"""
        
        response = "⚛ Configuring experiment...\n"
        
        # Use parameters from intent or defaults
        params = intent.parameters
        
        try:
            config = ExperimentConfig(
                hypothesis="Random circuits produce measurable quantum advantage",
                null_hypothesis="Circuits are noise-limited",
                n_qubits=params.get('qubits', 12),
                circuit_depth=params.get('depth', 8),
                shots=params.get('shots', 4000),
                trials=params.get('trials', 5),
                alpha=0.05
            )
            
            if self.pipeline:
                # Execute (mock if no token)
                result = self.pipeline.run_hypothesis_test(config)
                response += f"✓ Experiment complete!\n"
                response += f"p-value: {result.get('p_value', 'N/A')}\n"
                response += f"Effect size: {result.get('effect_size', 'N/A')}\n"
            else:
                response += "⚠ Pipeline not initialized"
        
        except Exception as e:
            response = f"⚠ Experiment error: {e}"
        
        return response
    
    async def _handle_deploy(self, intent) -> str:
        """Handle deployment/publishing intent"""
        
        response = "📦 Preparing deployment...\n"
        
        if self.zenodo_token:
            response += "✓ Zenodo token configured\n"
            response += "→ Would publish results with DOI\n"
            response += "→ Set ZENODO_TOKEN env var to enable\n"
        else:
            response += "⚠ ZENODO_TOKEN not set\n"
            response += "Set with: export ZENODO_TOKEN='your_token'\n"
        
        return response

    async def _handle_orchestrate(self, intent) -> str:
        """Handle full orchestrator pipeline intent"""
        response = "⚛ Launching full OSIRIS research pipeline...\n"

        if not self.orchestrator:
            return response + "⚠ Orchestrator unavailable"

        try:
            # Capture orchestrator streaming output
            buffer = io.StringIO()
            with redirect_stdout(buffer), redirect_stderr(buffer):
                await asyncio.to_thread(self.orchestrator.run_full_pipeline)
            output = buffer.getvalue()
            response += "✓ Pipeline complete.\n"
            response += "\n" + output.strip()
        except Exception as e:
            response = f"⚠ Orchestrator error: {e}"

        return response
    
    async def _handle_status(self, intent) -> str:
        """Handle status inquiry"""
        
        response = "📊 System Status:\n\n"
        response += f"Chat messages: {len(self.chat_history)}\n"
        response += f"IBM Quantum: {'✓ Connected' if self.token else '⚠ No token'}\n"
        response += f"Zenodo: {'✓ Ready' if self.zenodo_token else '⚠ No token'}\n"
        response += f"Benchmarker: {'✓ Ready' if self.benchmarker else '⚠ Not initialized'}\n"
        
        return response
    
    def _handle_help(self) -> str:
        """Show help and commands"""
        
        help_text = """
⚛ OSIRIS Chat Commands:

Benchmarking:
  "benchmark ibm_torino with 32 qubits at extreme depth"
  "test all backends" → Runs full suite
  "compare backends" → Performance comparison

Experiments:
  "run xeb experiment with 50 trials"
  "execute platform stability tests"
  "test with 16 qubits at depth 32"

Research Pipeline:
  "run full research pipeline"
  "execute the orchestrator"
  "run week1 campaign"
  "perform RQC vs RCS experiments"

Deployment:
  "deploy results to zenodo"
  "publish findings with DOI"

Status:
  "show status" → System info
  "what's running" → Active jobs
  "results" → Latest results

Pure Natural Language:
- No syntax required, just describe what you want
- System infers intent automatically
- Spawns agents for execution (background)

Hotkeys:
  [1] → Start benchmark
  [2] → Run experiment  
  [3] → Check status
  [4] → Deploy results
  [5] → Help
  [q] → Quit
"""
        return help_text


class OsirisTextualApp(App):
    """Textual chat-native OSIRIS interface"""

    TITLE = "OSIRIS Quantum Discovery System"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "show_help", "Help"),
        Binding("f2", "show_status", "Status")
    ]

    def __init__(self):
        super().__init__()
        self.osiris = OsirisApp()
        self.chat_log = ChatLog()
        self.status_panel = StatusPanel()
        self.hotkeys_panel = HotkeysPanel()
        self.input_widget = Input(placeholder="Type or paste natural language here, then press Enter...", id="user_input")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, title=self.TITLE)

        with Container():
            with Horizontal():
                yield self.chat_log
                with Vertical():
                    yield self.status_panel
                    yield self.hotkeys_panel

            with Horizontal():
                yield self.input_widget

        yield Footer()

    def on_mount(self) -> None:
        self.chat_log.write("[bold green]⚛ Welcome to OSIRIS. Type or paste commands below.[/bold green]\n")
        self.chat_log.write("[dim]Press F1 for help, F2 for status, or Ctrl+C to quit.[/dim]\n")
        self.refresh_status()
        self.set_focus(self.input_widget)

    def refresh_status(self) -> None:
        self.status_panel.update_status(
            queue_size=len(self.osiris.chat_history),
            last_result=self.osiris.chat_history[-1].content if self.osiris.chat_history else "Ready",
            token_status="connected" if self.osiris.token else "no token"
        )

    async def submit_message(self, user_input: str) -> None:
        if not user_input:
            return

        message = ChatMessage(
            sender="user",
            content=user_input,
            timestamp=datetime.now().isoformat(),
            message_type="text"
        )
        self.chat_log.add_message(message)

        response_text = await self.osiris.process_user_input(user_input)

        response = ChatMessage(
            sender="osiris",
            content=response_text,
            timestamp=datetime.now().isoformat(),
            message_type="result"
        )
        self.chat_log.add_message(response)
        self.input_widget.value = ""
        self.refresh_status()

    @on(Input.Submitted)
    async def handle_input(self, event: Input.Submitted) -> None:
        await self.submit_message(event.value)

    async def action_show_help(self) -> None:
        self.chat_log.write("[cyan]Type any natural language command, such as:\n  - 'benchmark ibm_torino with extreme depth'\n  - 'run xeb experiment'\n  - 'publish to zenodo'\n  - 'show status'[/cyan]\n")

    async def action_show_status(self) -> None:
        status_text = (
            f"IBM Quantum Token: {'SET' if self.osiris.token else 'NOT SET'}\n"
            f"Zenodo Token: {'SET' if self.osiris.zenodo_token else 'NOT SET'}\n"
            f"Chat History: {len(self.osiris.chat_history)} messages"
        )
        self.chat_log.write(f"[yellow]{status_text}[/yellow]\n")


def run_textual_mode() -> None:
    """Run the Textual OSIRIS application"""
    if not HAS_TEXTUAL:
        print("✗ Textual TUI requires 'textual' and 'rich' packages.")
        print("  Install with: pip install textual rich")
        print("  Falling back to CLI mode...")
        asyncio.run(run_cli_mode())
        return
    OsirisTextualApp().run()


async def run_cli_mode():
    """Run OSIRIS in CLI chat mode (for testing)"""
    
    print("\n" + "="*70)
    print("⚛  OSIRIS QUANTUM DISCOVERY SYSTEM - CHAT MODE")
    print("="*70)
    print("Type commands in natural language. Examples:")
    print("  - 'benchmark ibm_torino with extreme parameters'")
    print("  - 'run xeb experiment'")
    print("  - 'show status'")
    print("  - 'help'")
    print("Type 'quit' to exit\n")
    
    osiris = OsirisApp()
    
    while True:
        try:
            user_input = input("❯ ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n⚛ OSIRIS shutting down. Goodbye!")
                break
            
            # Process input
            response = await osiris.process_user_input(user_input)
            print(f"\n⚛ {response}\n")
        
        except KeyboardInterrupt:
            print("\n\n⚛ OSIRIS shutting down...")
            break
        except Exception as e:
            print(f"⚠ Error: {e}\n")


def main():
    """Main entry point"""
    run_textual_mode()


if __name__ == "__main__":
    # Check Python version
    import sys
    if sys.version_info < (3, 9):
        print("Python 3.9+ required")
        sys.exit(1)
    
    # Run TUI
    main()
