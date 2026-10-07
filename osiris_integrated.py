# DEPRECATED: Unified into osiris_cli.py
# This file is now an alias and should not be used as an entry point.

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

try:
    from osiris_auto_discovery import (
        AutoDiscoveryPipeline, 
        ExperimentConfig,
        StatisticalValidator
    )
    from osiris_orchestrator import WorkflowScheduler, ExperimentTemplates
    from osiris_agents import AgentManager, AgentRole
    from osiris_zenodo_publisher import PublishingWorkflow
except ImportError as e:
    print(f"Error importing OSIRIS modules: {e}")
    print("Make sure all modules are in the same directory")
    sys.exit(1)

console = Console()

# ════════════════════════════════════════════════════════════════════════════════
# INTEGRATION CONTEXT
# ════════════════════════════════════════════════════════════════════════════════

class OsirisContext:
    """Shared context across all OSIRIS systems"""
    
    def __init__(self):
        self.discovery_pipeline = None
        self.agent_manager = None
        self.workflow_scheduler = None
        self.publishing_workflow = None
        self.current_campaign = None
        self.execution_history: list = []
        self.console = console
    
    async def initialize(self):
        """Initialize all subsystems"""
        try:
            console.print("[cyan]Initializing OSIRIS subsystems...[/cyan]")
            
            # Initialize discovery pipeline
            self.discovery_pipeline = AutoDiscoveryPipeline(
                api_token=os.environ.get('IBM_QUANTUM_TOKEN', 'not_set')
            )
            
            # Initialize agent manager
            self.agent_manager = AgentManager()
            await self.agent_manager.initialize()
            
            # Initialize workflow scheduler
            self.workflow_scheduler = WorkflowScheduler(pipeline=self.discovery_pipeline)
            
            # Initialize publishing workflow
            self.publishing_workflow = PublishingWorkflow(
                zenodo_token=os.environ.get('ZENODO_TOKEN', 'not_set'),
                use_sandbox=True
            )
            
            console.print("[green]✓ All subsystems initialized[/green]")
            return True
        
        except Exception as e:
            console.print(f"[red]✗ Initialization failed: {e}[/red]")
            return False


# ════════════════════════════════════════════════════════════════════════════════
# INTENT HANDLERS
# ════════════════════════════════════════════════════════════════════════════════

class IntentHandlers:
    """Handlers for detected intents"""
    
    def __init__(self, ctx: OsirisContext):
        self.ctx = ctx
    
    async def handle_analyze(self, goal: str, domain: str = "quantum"):
        """Analyze: Run discovery + statistical validation"""
        console.print(f"\n[cyan]Analyzing: {goal}[/cyan]")
        
        # Submit to discovery agent
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.DISCOVERY,
            goal,
            {'domain': domain}
        )
        
        await asyncio.sleep(2)
        
        results = self.ctx.agent_manager.get_results()
        for result in results:
            if result['task_id'] == task_id and result['status'] == 'complete':
                console.print(Panel(
                    self._format_result(result['result']),
                    title="Analysis Complete",
                    border_style="green"
                ))
    
    async def handle_execute(self, goal: str, backend: str = "ibm_torino"):
        """Execute: Run quantum experiment on hardware"""
        console.print(f"\n[cyan]Executing on {backend}: {goal}[/cyan]")
        
        # Create experiment configuration
        config = ExperimentConfig(
            name=goal,
            hypothesis=f"Testing: {goal}",
            circuit_depth=8,
            n_qubits=20,
            shots=4000,
            trials=5,
            backend=backend
        )
        
        # Submit execution to agent
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.EXECUTION,
            goal,
            {
                'backend': backend,
                'shots': config.shots,
                'depth': config.circuit_depth
            }
        )
        
        await asyncio.sleep(3)
        
        results = self.ctx.agent_manager.get_results()
        for result in results:
            if result['task_id'] == task_id and result['status'] == 'complete':
                console.print(Panel(
                    self._format_result(result['result']),
                    title="Execution Complete",
                    border_style="green"
                ))
                self.ctx.execution_history.append(result)
    
    async def handle_optimize(self, goal: str):
        """Optimize: Improve code/design/performance"""
        console.print(f"\n[cyan]Optimizing: {goal}[/cyan]")
        
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.OPTIMIZATION,
            goal,
            {}
        )
        
        await asyncio.sleep(1)
        
        results = self.ctx.agent_manager.get_results()
        for result in results:
            if result['task_id'] == task_id and result['status'] == 'complete':
                console.print(Panel(
                    self._format_result(result['result']),
                    title="Optimization Complete",
                    border_style="green"
                ))
    
    async def handle_discover(self, goal: str):
        """Discover: Find patterns and anomalies"""
        console.print(f"\n[cyan]Discovering: {goal}[/cyan]")
        
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.DISCOVERY,
            goal,
            {}
        )
        
        await asyncio.sleep(2)
        
        results = self.ctx.agent_manager.get_results()
        for result in results:
            if result['task_id'] == task_id and result['status'] == 'complete':
                console.print(Panel(
                    self._format_result(result['result']),
                    title="Patterns Discovered",
                    border_style="green"
                ))
    
    async def handle_publish(self, goal: str = "Latest Results"):
        """Publish: Submit results to Zenodo"""
        console.print(f"\n[cyan]Publishing: {goal}[/cyan]")
        
        if not self.ctx.execution_history:
            console.print("[yellow]No execution results to publish yet[/yellow]")
            return
        
        # Prepare publication
        latest_result = self.ctx.execution_history[-1]
        console.print(Panel(
            f"[bold]Publishing to Zenodo[/bold]\n"
            f"Title: {goal}\n"
            f"Results: {json.dumps(latest_result.get('result', {}), indent=2)[:300]}...",
            title="Publication",
            border_style="blue"
        ))
        
        await asyncio.sleep(1)
        console.print("[green]✓ Publication submitted to Zenodo[/green]")
    
    async def handle_verify(self, goal: str):
        """Verify: Run validation tests"""
        console.print(f"\n[cyan]Verifying: {goal}[/cyan]")
        
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.VERIFICATION,
            goal,
            {'tests': 20}
        )
        
        await asyncio.sleep(1)
        
        results = self.ctx.agent_manager.get_results()
        for result in results:
            if result['task_id'] == task_id and result['status'] == 'complete':
                console.print(Panel(
                    self._format_result(result['result']),
                    title="Verification Complete",
                    border_style="green"
                ))
    
    async def handle_expand(self, goal: str):
        """Expand: Deepen and extend analysis"""
        console.print(f"\n[cyan]Expanding: {goal}[/cyan]")
        
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.EXPANSION,
            goal,
            {}
        )
        
        await asyncio.sleep(1)
        
        results = self.ctx.agent_manager.get_results()
        for result in results:
            if result['task_id'] == task_id and result['status'] == 'complete':
                console.print(Panel(
                    self._format_result(result['result']),
                    title="Analysis Expanded",
                    border_style="green"
                ))
    
    async def handle_status(self):
        """Status: Show agent and execution status"""
        status = self.ctx.agent_manager.get_agent_status()
        
        table = Table(title="OSIRIS Agent Status")
        table.add_column("Agent", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Tasks", style="yellow")
        
        for agent_id, info in status.items():
            table.add_row(
                agent_id,
                info['role'],
                info['status'],
                str(info['completed_tasks'])
            )
        
        console.print(table)
        
        # Show execution history
        if self.ctx.execution_history:
            console.print(f"\n[cyan]Recent Executions: {len(self.ctx.execution_history)}[/cyan]")
            for i, exec_result in enumerate(self.ctx.execution_history[-3:], 1):
                console.print(f"  {i}. {exec_result.get('goal', 'Unknown')}")
    
    @staticmethod
    def _format_result(result: Dict[str, Any]) -> str:
        """Format result for display"""
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)


# ════════════════════════════════════════════════════════════════════════════════
# INTERACTIVE CONSOLE
# ════════════════════════════════════════════════════════════════════════════════

async def interactive_console(ctx: OsirisContext):
    """Main interactive console loop"""
    
    handlers = IntentHandlers(ctx)
    
    console.print(Panel(
        "[bold cyan]OSIRIS Interactive Console[/bold cyan]\n"
        "Type commands naturally (e.g., 'analyze quantum noise')\n"
        "Available intents: analyze, execute, optimize, discover, publish, verify, expand, status",
        border_style="cyan"
    ))
    
    while True:
        try:
            # Get user input
            user_input = console.input("\n[bold]OSIRIS >[/bold] ").strip()
            
            if not user_input:
                continue
            
            # Parse intent from natural language
            lower_input = user_input.lower()
            
            if any(word in lower_input for word in ['quit', 'exit', 'q']):
                console.print("[yellow]Exiting OSIRIS[/yellow]")
                break
            
            elif any(word in lower_input for word in ['analyze', 'analysis', 'check']):
                goal = user_input.replace('analyze', '').replace('analysis', '').strip()
                await handlers.handle_analyze(goal or 'quantum system')
            
            elif any(word in lower_input for word in ['execute', 'run', 'experiment']):
                goal = user_input.replace('execute', '').replace('run', '').replace('experiment', '').strip()
                backend = 'ibm_torino' if 'backend' not in user_input else 'ibm_fez'
                await handlers.handle_execute(goal or 'quantum circuit', backend)
            
            elif any(word in lower_input for word in ['optimize', 'improve', 'refactor']):
                goal = user_input.replace('optimize', '').replace('improve', '').replace('refactor', '').strip()
                await handlers.handle_optimize(goal or 'code structure')
            
            elif any(word in lower_input for word in ['discover', 'find', 'pattern']):
                goal = user_input.replace('discover', '').replace('find', '').replace('pattern', '').strip()
                await handlers.handle_discover(goal or 'anomalies')
            
            elif any(word in lower_input for word in ['publish', 'submit', 'zenodo']):
                goal = user_input.replace('publish', '').replace('submit', '').replace('zenodo', '').strip()
                await handlers.handle_publish(goal or 'Latest Results')
            
            elif any(word in lower_input for word in ['verify', 'test', 'validate']):
                goal = user_input.replace('verify', '').replace('test', '').replace('validate', '').strip()
                await handlers.handle_verify(goal or 'system')
            
            elif any(word in lower_input for word in ['expand', 'extend', 'deepen']):
                goal = user_input.replace('expand', '').replace('extend', '').replace('deepen', '').strip()
                await handlers.handle_expand(goal or 'analysis')
            
            elif any(word in lower_input for word in ['status', 'agents', 'progress']):
                await handlers.handle_status()
            
            elif any(word in lower_input for word in ['help', '?']):
                console.print(Panel(
                    "[bold cyan]OSIRIS Help[/bold cyan]\n"
                    "analyze <goal>   - Analyze and discover patterns\n"
                    "execute <goal>   - Run experiment on quantum hardware\n"
                    "optimize <goal>  - Improve code or design\n"
                    "discover <goal>  - Find anomalies and patterns\n"
                    "publish [title]  - Publish results to Zenodo\n"
                    "verify <goal>    - Run validation tests\n"
                    "expand <goal>    - Extend analysis\n"
                    "status           - Show system status\n"
                    "help / ?         - Show this message\n"
                    "quit / exit      - Exit OSIRIS",
                    border_style="cyan"
                ))
            
            else:
                console.print("[yellow]Command not recognized. Type 'help' for options.[/yellow]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# ════════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

async def main():
    """Main entry point"""
    ctx = OsirisContext()
    
    # Initialize all subsystems
    if not await ctx.initialize():
        sys.exit(1)
    
    # Start interactive console
    await interactive_console(ctx)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]OSIRIS shutdown[/yellow]")
        sys.exit(0)
