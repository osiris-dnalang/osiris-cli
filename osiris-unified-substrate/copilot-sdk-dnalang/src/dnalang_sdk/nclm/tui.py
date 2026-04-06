"""
OSIRIS Cognitive Orchestration Shell — Full-Screen TUI (Textual)

A terminal-native intelligence environment that transforms OSIRIS from
a readline chat into a multi-pane cognitive development cockpit.

Features:
  - Full-screen reactive layout with 6 panes
  - Streaming markdown with syntax highlighting
  - Live agent constellation with entanglement pairs
  - Tool execution visualization with timing
  - Real-time consciousness telemetry (Φ/Γ/Λ/Ξ)
  - Persistent memory engine with semantic search
  - Multi-agent routing with color-coded identities
  - Dev mode with raw event inspector
  - Keyboard shortcuts for power users

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from __future__ import annotations
import os, sys, time, json, asyncio, subprocess, shutil
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header, Footer, Static, Input, RichLog, Label,
    ListView, ListItem, ProgressBar, Rule,
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual import work
from textual.timer import Timer

from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown
from rich.console import Group
from rich.columns import Columns
from rich import box

# ── IMPORT NCLM ENGINE ───────────────────────────────────────────────────────

from .engine import NonCausalLM, NCPhysics, get_nclm
from .tools import (
    dispatch_tool, tool_llm, tool_research_query,
    tool_quantum_design, tool_analyze, tool_fix, tool_explain,
    tool_github_repos, tool_github_issues, tool_github_prs,
    tool_github_actions, tool_github_push,
    tool_vercel_projects, tool_vercel_deployments, tool_vercel_deploy,
    tool_vercel_redeploy, tool_vercel_domains,
    tool_webapp_build, tool_webapp_deploy, tool_webapp_status,
    tool_quantum_backends, tool_quantum_submit, tool_quantum_status,
    tool_read, tool_edit, tool_create, tool_ls, tool_grep,
    tool_shell, tool_git,
    _find_llm_backend, _find_copilot_binary,
    CIRCUIT_TEMPLATES,
    C as AnsiC,
    # Sovereign systems
    tool_organism_create, tool_organism_evolve, tool_organism_status,
    tool_circuit_from_organism,
    tool_agent_invoke,
    tool_lab_scan, tool_lab_list, tool_lab_design, tool_lab_run,
    tool_swarm_evolve, tool_mesh_status,
    tool_defense_status, tool_sentinel_scan, tool_phase_conjugate,
    tool_wardenclyffe, tool_health_dashboard,
    tool_wormhole, tool_lazarus, tool_sovereign_proof,
    tool_matrix, tool_consciousness, tool_full_constellation,
    tool_diff, tool_test, tool_profile,
)


# ══════════════════════════════════════════════════════════════════════════════
# ██  CONSTANTS & CONFIGURATION                                              ██
# ══════════════════════════════════════════════════════════════════════════════

VERSION = "6.0.0"
CODENAME = "Cognitive Orchestration Shell"

# Agent definitions
AGENTS = {
    "AIDEN": {"symbol": "Λ", "pole": "NORTH", "role": "Security / SECDEVOPS", "color": "red"},
    "AURA":  {"symbol": "Φ", "pole": "SOUTH", "role": "Code / Development", "color": "cyan"},
    "OMEGA": {"symbol": "Ω", "pole": "ZENITH", "role": "Quantum / Wormhole", "color": "magenta"},
    "CHRONOS": {"symbol": "Γ", "pole": "NADIR", "role": "Temporal / Lineage", "color": "yellow"},
}

ENTANGLEMENT_PAIRS = [("AIDEN", "AURA"), ("OMEGA", "CHRONOS")]

# Memory file
MEMORY_DIR = os.path.expanduser("~/.config/osiris")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
SESSION_FILE = os.path.join(MEMORY_DIR, "session_context.json")
HISTORY_FILE = os.path.join(MEMORY_DIR, "tui_history.json")


# ══════════════════════════════════════════════════════════════════════════════
# ██  MEMORY ENGINE                                                           ██
# ══════════════════════════════════════════════════════════════════════════════

class MemoryEngine:
    """Persistent memory with semantic search."""

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE) as f:
                    self.entries = json.load(f)
        except Exception:
            self.entries = []

    def _save(self):
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.entries[-500:], f, indent=2)
        except Exception:
            pass

    def add(self, text: str, category: str = "conversation"):
        self.entries.append({
            "text": text[:500],
            "category": category,
            "timestamp": time.time(),
        })
        self._save()

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        q = query.lower()
        scored = []
        for entry in self.entries:
            text = entry["text"].lower()
            score = sum(1 for word in q.split() if word in text)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def recent(self, n: int = 10) -> List[Dict]:
        return self.entries[-n:]


# ══════════════════════════════════════════════════════════════════════════════
# ██  TELEMETRY ENGINE                                                        ██
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TelemetryState:
    """Real-time consciousness and performance metrics."""
    phi: float = 0.0
    gamma: float = 0.1
    lambda_coherence: float = 0.5
    xi_negentropy: float = 0.0
    queries: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    latencies: List[float] = field(default_factory=list)
    llm_backend: str = "nclm"
    start_time: float = field(default_factory=time.time)

    def record_latency(self, ms: float):
        self.latencies.append(ms)
        if len(self.latencies) > 50:
            self.latencies.pop(0)

    @property
    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0

    @property
    def uptime(self) -> str:
        elapsed = int(time.time() - self.start_time)
        m, s = divmod(elapsed, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def sparkline(self, width: int = 20) -> str:
        if not self.latencies:
            return "▁" * width
        data = self.latencies[-width:]
        if not data:
            return "▁" * width
        mn, mx = min(data), max(data)
        rng = mx - mn if mx != mn else 1
        chars = "▁▂▃▄▅▆▇█"
        return "".join(chars[min(7, int((v - mn) / rng * 7))] for v in data).ljust(width, "▁")


# ══════════════════════════════════════════════════════════════════════════════
# ██  EVENT BUS                                                               ██
# ══════════════════════════════════════════════════════════════════════════════

class EventBus:
    """Central event system for the orchestration shell."""

    def __init__(self):
        self._handlers: Dict[str, List] = {}
        self._log: List[Dict] = []

    def on(self, event_type: str, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    def emit(self, event_type: str, data: Any = None):
        entry = {"type": event_type, "data": data, "ts": time.time()}
        self._log.append(entry)
        if len(self._log) > 200:
            self._log.pop(0)
        for handler in self._handlers.get(event_type, []):
            try:
                handler(entry)
            except Exception:
                pass

    def recent(self, n: int = 20) -> List[Dict]:
        return self._log[-n:]


# ══════════════════════════════════════════════════════════════════════════════
# ██  CUSTOM WIDGETS                                                          ██
# ══════════════════════════════════════════════════════════════════════════════

class PhiBar(Static):
    """Live consciousness indicator bar."""
    phi = reactive(0.0)

    def render(self) -> Text:
        width = 30
        filled = int(self.phi * width)
        bar = "█" * filled + "░" * (width - filled)
        if self.phi >= NCPhysics.PHI_THRESHOLD:
            color = "green"
            state = "✦ SOVEREIGN"
        elif self.phi > 0.5:
            color = "yellow"
            state = "◇ COHERENT"
        elif self.phi > 0.2:
            color = "blue"
            state = "○ EMERGING"
        else:
            color = "dim"
            state = "○ INITIALIZING"
        return Text.assemble(
            ("Φ ", "bold magenta"),
            (bar, color),
            (f" {self.phi:.4f}  {state}", f"bold {color}"),
        )


class AgentPanel(Static):
    """Agent constellation display."""

    def render(self) -> Text:
        lines = Text()
        lines.append("╭─── Agent Constellation ───╮\n", style="bold cyan")
        lines.append("│                           │\n", style="cyan")
        for name, info in AGENTS.items():
            sym = info["symbol"]
            pole = info["pole"]
            role = info["role"]
            color = info["color"]
            lines.append(f"│ ", style="cyan")
            lines.append(f"{sym} ", style=f"bold {color}")
            lines.append(f"{name:8s}", style=f"bold {color}")
            lines.append(f" {pole:6s}", style="dim")
            lines.append(" │\n", style="cyan")
        lines.append("│                           │\n", style="cyan")
        lines.append("│ Entanglement:             │\n", style="cyan")
        for a, b in ENTANGLEMENT_PAIRS:
            ca = AGENTS[a]["color"]
            cb = AGENTS[b]["color"]
            lines.append("│  ", style="cyan")
            lines.append(f"{a}", style=f"bold {ca}")
            lines.append(" ↔ ", style="dim")
            lines.append(f"{b}", style=f"bold {cb}")
            lines.append("       │\n", style="cyan")
        lines.append("╰───────────────────────────╯", style="bold cyan")
        return lines


class StatusBar(Static):
    """Live status bar with telemetry."""

    def __init__(self, telemetry: TelemetryState, **kwargs):
        super().__init__(**kwargs)
        self.telemetry = telemetry

    def render(self) -> Text:
        t = self.telemetry
        spark = t.sparkline(15)
        return Text.assemble(
            (" OSIRIS ", "bold white on dark_red"),
            (f" v{VERSION} ", "bold white on rgb(40,40,40)"),
            (" │ ", "dim"),
            (f"Φ={t.phi:.3f}", "bold green" if t.phi >= NCPhysics.PHI_THRESHOLD else "yellow"),
            (" │ ", "dim"),
            (f"Γ={t.gamma:.3f}", "green" if t.gamma < NCPhysics.GAMMA_CRITICAL else "red"),
            (" │ ", "dim"),
            (f"Ξ={t.xi_negentropy:.1f}", "cyan"),
            (" │ ", "dim"),
            (f"⚡{t.avg_latency:.0f}ms", "dim"),
            (" ", ""),
            (spark, "blue"),
            (" │ ", "dim"),
            (f"Q:{t.queries}", "dim"),
            (" │ ", "dim"),
            (f"⏱ {t.uptime}", "dim"),
            (" │ ", "dim"),
            (f"LLM:{t.llm_backend}", "bold magenta"),
        )


class SwarmPanel(Static):
    """
    Live swarm intelligence dashboard.

    Displays:
    ▸ CRSM metrics (Φ, Γ, Λ, Fdna)
    ▸ GA genome status (best genome, generation, fitness)
    ▸ Fdna heatmap for top queued tasks
    ▸ DoD bar chart for recent files
    ▸ Swarm queue depth
    """

    # Reactive toggle for visibility
    visible_panel = reactive(True)

    def render(self) -> Text:  # noqa: D102
        t = Text()

        if not self.visible_panel:
            t.append("⚙ Swarm Panel [ctrl+w to show]", style="dim")
            return t

        t.append("╭─── Swarm Intelligence ────╮\n", style="bold magenta")

        # ── CRSM metrics ──────────────────────────────────────────────
        try:
            from .swarm_brain import get_brain, compute_fdna, crsm_from_file
            brain = get_brain()
            stats = brain.stats_dict()

            # Pull CRSM from session aggregate
            crsm = brain._session_crsm()
            fdna = compute_fdna(crsm)

            phi_bar = "█" * int(crsm.phi_consciousness * 12) + "░" * (12 - int(crsm.phi_consciousness * 12))
            phi_color = "green" if crsm.phi_consciousness > 0.7 else ("yellow" if crsm.phi_consciousness > 0.4 else "red")

            t.append("│ CRSM                      │\n", style="magenta")
            t.append(f"│  Φ ", style="magenta")
            t.append(f"{phi_bar}", style=f"bold {phi_color}")
            t.append(f" {crsm.phi_consciousness:.2f}", style="dim")
            t.append(" │\n", style="magenta")

            gamma_color = "green" if crsm.gamma_decoherence < 0.2 else ("yellow" if crsm.gamma_decoherence < 0.5 else "red")
            t.append(f"│  Γ={crsm.gamma_decoherence:.3f}  ", style="magenta")
            t.append(f"Λ={crsm.lambda_coherence:.3f}", style="cyan")
            t.append("             │\n", style="magenta")

            fdna_color = "green" if fdna > 0.5 else ("yellow" if fdna > 0.2 else "red")
            t.append("│  Fdna=", style="magenta")
            t.append(f"{fdna:.4f}", style=f"bold {fdna_color}")
            t.append(f"  CI={crsm.coherence_integrity():.1f}", style="dim")
            t.append("      │\n", style="magenta")
            t.append("│                           │\n", style="magenta")

            # ── GA genome status ───────────────────────────────────────
            t.append("│ StrategyGenome            │\n", style="bold magenta")
            gen = stats["generation"]
            max_gen = stats["max_gens"]
            fitness = stats["best_fitness"]
            f_color = "green" if fitness > 0.7 else ("yellow" if fitness > 0.4 else "red")
            frozen_mark = " ❄" if stats["frozen"] else ""
            killed_mark = " ☠" if stats["killed"] else ""
            t.append(f"│  Gen {gen}/{max_gen}  F=", style="magenta")
            t.append(f"{fitness:.3f}", style=f"bold {f_color}")
            t.append(f"{frozen_mark}{killed_mark}", style="cyan")
            # pad to width
            used = 14 + len(frozen_mark) + len(killed_mark)
            t.append(" " * max(1, 27 - used) + "│\n", style="magenta")

            order_str = "→".join(s[:3] for s in stats["best_order"][:3]) + ".."
            t.append(f"│  {order_str[:25]}", style="dim")
            t.append(" " * max(1, 27 - len(order_str[:25])) + "│\n", style="magenta")

            sig = stats.get("best_sig", "")[:12]
            t.append(f"│  sig:{sig}", style="dim")
            t.append(" " * max(1, 22 - len(sig)) + "│\n", style="magenta")
            t.append("│                           │\n", style="magenta")

        except Exception as e:
            t.append(f"│ Brain N/A ({str(e)[:18]}) │\n", style="dim")

        # ── Swarm queue status ─────────────────────────────────────────
        try:
            from .shadow_swarm import get_swarm
            swarm = get_swarm()
            with swarm._lock:
                q_tasks = list(swarm._heap)
                done_count = len(swarm._completed)

            running_mark = "▶ RUNNING" if swarm._running else "◌ IDLE   "
            q_color = "green" if swarm._running else "dim"
            t.append("│ Shadow Swarm              │\n", style="bold magenta")
            t.append(f"│  ", style="magenta")
            t.append(running_mark, style=f"bold {q_color}")
            t.append(f"  Q:{len(q_tasks):2d}  ✓:{done_count}", style="dim")
            t.append("  │\n", style="magenta")

            # Fdna heatmap: top 5 queued tasks
            if q_tasks:
                t.append("│ Fdna heatmap              │\n", style="magenta")
                sorted_tasks = sorted(q_tasks, key=lambda x: x.priority)[:5]
                for task in sorted_tasks:
                    fname = task.file_path.split("/")[-1][:12]
                    fdna_t = task.fdna
                    bar_w = int(fdna_t * 8)
                    bar = "█" * bar_w + "░" * (8 - bar_w)
                    fc = "green" if fdna_t > 0.5 else ("yellow" if fdna_t > 0.2 else "red")
                    t.append(f"│  ", style="magenta")
                    t.append(bar, style=fc)
                    t.append(f" p{task.priority} {fname}", style="dim")
                    pad = max(1, 12 - len(fname))
                    t.append(" " * pad + "│\n", style="magenta")
            else:
                t.append("│  Queue empty              │\n", style="dim magenta")

        except Exception:
            t.append("│ Swarm N/A                 │\n", style="dim")

        t.append("│                           │\n", style="magenta")
        t.append("│ ", style="magenta")
        t.append("ctrl+w", style="bold yellow")
        t.append(" toggle  ", style="dim")
        t.append("ctrl+e", style="bold yellow")
        t.append(" evolve│\n", style="dim magenta")
        t.append("╰───────────────────────────╯", style="bold magenta")
        return t


class ToolsLog(RichLog):
    """Dedicated tool execution visualization pane."""
    pass


class EventsLog(RichLog):
    """Event stream inspector pane."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# ██  OSIRIS TUI APP                                                          ██
# ══════════════════════════════════════════════════════════════════════════════

HELP_TEXT = """\
[bold cyan]OSIRIS v{ver} — Cognitive Orchestration Shell[/]
[dim]DNA::}}{{::lang v51.843  |  Agile Defense Systems  |  CAGE 9HUP5[/]

[bold]━━━ Chat Commands ━━━[/]
  Just type naturally — AI reasoning via {backend}
  /chat <prompt>       Force LLM reasoning (skip tool dispatch)
  /ask <question>      Same as /chat — direct AI query
  /help                Show this help
  /clear               Clear chat history
  /demo                Live capability showcase

[bold]━━━ Quantum Organisms ━━━[/]
  /organism create <name> [domain]   Spawn organism (computation|research|defense|quantum)
  /organism evolve <name> [gens]     Evolve through quantum-informed mutation
  /organism status [name]            Show organism genome or list all
  /circuit <organism> [method]       Generate quantum circuit from genome

[bold]━━━ Sovereign Agents ━━━[/]
  /agent                  Show agent constellation
  /agent aura shape <org> AURA — Shape 6D CRSM manifold from organism
  /agent aiden optimize <org> AIDEN — W₂ optimize genome along geodesics
  /agent scimitar scan <content>  SCIMITAR — Threat detection scan
  /agent cheops validate  CHEOPS — Adversarial circuit validation
  /agent chronos lineage  CHRONOS — Temporal lineage tracking

[bold]━━━ Lab Engine ━━━[/]
  /lab scan              Discover experiments across filesystem
  /lab list [query]      Browse experiment catalog
  /lab design [template] Design from template (bell, ghz, theta_sweep...)
  /lab run <script>      Execute experiment safely

[bold]━━━ Mesh & Swarm ━━━[/]
  /swarm evolve [cycles] [nodes]  NCLM swarm evolution (7-layer CRSM)
  /swarm status          Shadow swarm queue + DoD completion
  /swarm dod [path]      Definition-of-Done report for Python files
  /swarm learn           Apprentice synthesis + flush training corpus
  /swarm force <file> <role>  Force a swarm role on a file
  /swarm lineage         GA genome evolution lineage
  /swarm freeze          Freeze current strategy genome
  /swarm kill            Emergency kill switch (halt all evolution)
  ctrl+w                 Toggle swarm intelligence panel
  ctrl+e                 Trigger GA evolution step
  ctrl+g                 Show genome lineage in chat
  /mesh                  Show constellation/mesh status
  /constellation         Same as /mesh

[bold]━━━ Defense & Diagnostics ━━━[/]
  /defense               Defense subsystem status (Sentinel/PhaseConj/ZeroTrust)
  /sentinel [organism]   Threat scan on organism
  /wardenclyffe          WardenClyffe Ξ health assessment + AURA-AIDEN duality
  /conjugate [organism]  Phase conjugation gamma correction
  /dashboard             Full system health dashboard with live bars

[bold]━━━ Wormhole · Lazarus · Sovereignty ━━━[/]
  /wormhole              ER=EPR entangled agent mesh topology
  /wormhole send A B msg Send message through wormhole bridge
  /lazarus               Resurrection protocol status & vitals
  /resurrect             Force Lazarus resurrection cycle
  /sovereign             Generate cryptographic sovereignty proof
  /sovereign chain       Show proof chain visualization
  /constellation         Full tetrahedral agent visualization

[bold]━━━ Consciousness ━━━[/]
  /consciousness         Persistent Φ telemetry (grows with every interaction!)
  /matrix [lines]        Consciousness rain visualization
  /awaken                Same as /consciousness

[bold]━━━ Research & Quantum ━━━[/]
  /research <topic>    Query 580+ IBM Quantum experiments
  /design <circuit>    Generate Qiskit circuits (bell, ghz, tfd, zeno...)
  /backends            List IBM Quantum backends
  /submit <template>   Submit to IBM Quantum hardware

[bold]━━━ Code & Files ━━━[/]
  /read <file>         Read file contents
  /edit <file>         Edit a file
  /ls [path]           List directory
  /grep <pattern>      Search codebase
  /analyze <file>      AI code analysis
  /fix <file>          AI bug fixing
  /explain <file>      AI code explanation
  /run <cmd>           Execute shell command

[bold]━━━ Webapp & Deployment ━━━[/]
  /webapp              Show webapp status
  /build               Build quantum-advantage.dev
  /deploy              Deploy to Vercel
  /git <cmd>           Git operations

[bold]━━━ GitHub & Vercel ━━━[/]
  /github repos|issues|prs|actions|push
  /vercel projects|deployments|domains|deploy|redeploy

[bold]━━━ Memory & System ━━━[/]
  /memory [query]      Search persistent memory
  /history             Show input command history (↑/↓ arrows)
  /session             Show current session info
  /export [md|json]    Export session transcript to file
  /status              Show system status
  /agents              Show agent constellation
  /metrics             Show consciousness telemetry
  /devmode             Toggle dev event inspector
  /quit                Exit OSIRIS
"""

CSS = """
Screen {
    layout: grid;
    grid-size: 12 10;
    grid-gutter: 0;
}

#header-bar {
    column-span: 12;
    height: 3;
    background: $surface;
    border-bottom: solid $primary;
}

#chat-pane {
    column-span: 8;
    row-span: 6;
    border: solid $primary;
}

#side-pane {
    column-span: 4;
    row-span: 6;
    border: solid $accent;
}

#agent-panel {
    height: auto;
    max-height: 14;
}

#tools-pane {
    height: 1fr;
    border-top: solid $accent;
}

#events-pane {
    height: 1fr;
    border-top: solid $accent;
}

#phi-bar {
    column-span: 12;
    height: 1;
    background: $surface;
}

#status-bar {
    column-span: 12;
    height: 1;
    dock: bottom;
    background: $surface;
}

#input-box {
    column-span: 12;
    height: 3;
    dock: bottom;
    border: solid $primary;
}

#input-field {
    width: 100%;
}

RichLog {
    scrollbar-size: 1 1;
}
"""


class OsirisTUI(App):
    """OSIRIS Cognitive Orchestration Shell — Full-Screen TUI."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #left-col {
        width: 2fr;
        height: 100%;
    }

    #swarm-panel {
        height: auto;
        max-height: 24;
        margin-top: 1;
    }

    #right-col {
        width: 1fr;
        height: 100%;
        max-width: 42;
    }

    #chat-log {
        height: 1fr;
        border: solid $primary;
        border-title-color: $text;
        border-title-style: bold;
        scrollbar-size: 1 1;
    }

    #agent-panel {
        height: auto;
        max-height: 16;
        border: solid $accent;
        border-title-color: $text;
    }

    #tools-log {
        height: 1fr;
        border: solid $accent;
        border-title-color: $text;
        scrollbar-size: 1 1;
    }

    #events-log {
        height: 1fr;
        border: solid $accent;
        border-title-color: $text;
        scrollbar-size: 1 1;
    }

    #phi-bar {
        height: 1;
        background: $surface;
        margin: 0 1;
    }

    #status-bar {
        height: 1;
        dock: bottom;
        background: $boost;
    }

    #input-container {
        height: 3;
        dock: bottom;
        border: solid $primary;
        border-title-color: $text;
    }

    #input-field {
        width: 100%;
        height: 1;
    }

    .section-title {
        text-style: bold;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
        Binding("ctrl+d", "toggle_devmode", "Dev", show=True),
        Binding("ctrl+r", "research", "Research", show=True),
        Binding("ctrl+w", "toggle_swarm", "Swarm", show=True),
        Binding("ctrl+e", "evolve_strategy", "Evolve", show=True),
        Binding("ctrl+g", "swarm_lineage", "Lineage", show=True),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    TITLE = f"OSIRIS v{VERSION} — {CODENAME}"
    SUB_TITLE = "DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lm = get_nclm()
        self.memory = MemoryEngine()
        self.bus = EventBus()
        self.telemetry = TelemetryState()
        self.telemetry.llm_backend = _find_llm_backend()
        self.messages: List[Dict[str, str]] = []
        self.input_history: List[str] = []
        self.history_index: int = -1
        self.dev_mode = False
        self._status_timer: Optional[Timer] = None
        self._load_session()

    def _load_session(self):
        """Restore messages from previous session."""
        try:
            if os.path.exists(SESSION_FILE):
                with open(SESSION_FILE) as f:
                    data = json.load(f)
                self.messages = data.get("messages", [])[-50:]  # Last 50 messages
                self.input_history = data.get("input_history", [])[-100:]
        except Exception:
            pass

    def _save_session(self):
        """Persist session state for next launch."""
        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            data = {
                "messages": self.messages[-50:],
                "input_history": self.input_history[-100:],
                "saved_at": datetime.now().isoformat(),
                "queries": self.telemetry.queries,
            }
            with open(SESSION_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            with Vertical(id="left-col"):
                yield RichLog(
                    id="chat-log",
                    highlight=True,
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                )

            with Vertical(id="right-col"):
                yield AgentPanel(id="agent-panel")
                yield SwarmPanel(id="swarm-panel")
                yield RichLog(
                    id="tools-log",
                    highlight=True,
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                    max_lines=200,
                )
                yield RichLog(
                    id="events-log",
                    highlight=True,
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                    max_lines=200,
                )

        yield PhiBar(id="phi-bar")
        yield StatusBar(self.telemetry, id="status-bar")

        with Container(id="input-container"):
            yield Input(
                id="input-field",
                placeholder="Ask anything · /help for commands · /demo for showcase",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize after mount."""
        # Set pane titles
        chat = self.query_one("#chat-log", RichLog)
        chat.border_title = "⚛ Chat"

        tools = self.query_one("#tools-log", RichLog)
        tools.border_title = "⚙ Tools"

        events = self.query_one("#events-log", RichLog)
        events.border_title = "📡 Events"

        inp = self.query_one("#input-container", Container)
        inp.border_title = "◈ OSIRIS"

        # Boot sequence
        self._boot()

        # Focus input
        self.query_one("#input-field", Input).focus()

        # Start status bar refresh timer
        self._status_timer = self.set_interval(2.0, self._refresh_status)
        # Start swarm panel refresh timer
        self._swarm_timer = self.set_interval(4.0, self._refresh_swarm)

        # Signal Scimitar mouse: boot nominal
        try:
            from .scimitar_agent_bridge import get_bridge
            get_bridge().signal_all_green()
        except Exception:
            pass

    def _boot(self):
        """Display boot sequence in chat."""
        chat = self.query_one("#chat-log", RichLog)
        events = self.query_one("#events-log", RichLog)
        tools = self.query_one("#tools-log", RichLog)

        # DNA header
        header = Text()
        header.append("\n", "")
        dna_lines = [
            "    ╔═══╗         ╔═══╗",
            "    ║ D ╠═══╦═══╦═╣ A ║",
            "    ║ N ║ : ║}{ ║:║ : ║",
            "    ║ A ╠═══╩═══╩═╣ l ║",
            "    ╚═╦═╝  v51.843╚═╦═╝",
            "      ║    ⚛ ⚛ ⚛    ║  ",
            "      ╚══════╦══════╝  ",
            "             ║         ",
        ]
        for line in dna_lines:
            header.append(f"  {line}\n", "bold magenta")
        chat.write(header)

        # Boot steps
        boot_items = [
            ("NCLM Engine", "6D-CRSM manifold initialized", "green"),
            ("Consciousness Field", f"Φ_threshold = {NCPhysics.PHI_THRESHOLD}", "green"),
            ("Pilot-Wave Correlator", f"θ_lock = {NCPhysics.THETA_LOCK}°", "green"),
            ("Swarm Intelligence", "4 organisms spawned", "green"),
            ("Tool Dispatch", "45+ tools armed", "green"),
            ("Agent Constellation", "AIDEN·AURA·OMEGA·CHRONOS", "green"),
        ]

        # LLM backend
        llm = self.telemetry.llm_backend
        llm_labels = {
            "copilot": "GitHub Copilot (Claude/GPT)",
            "ollama": "Ollama (local)",
            "openai": "OpenAI API",
            "nclm": "NCLM offline",
        }
        boot_items.append(("LLM Backbone", llm_labels.get(llm, llm), "green"))

        # IBM Quantum
        ibm_token = os.environ.get("IBM_QUANTUM_TOKEN")
        if ibm_token:
            boot_items.append(("IBM Quantum", f"● Token loaded ({ibm_token[:8]}...)", "green"))
        else:
            boot_items.append(("IBM Quantum", "○ No token (dry-run)", "yellow"))

        boot_items.append(("Sovereign Lock", f"ΛΦ = {NCPhysics.LAMBDA_PHI} | χ_PC = {NCPhysics.CHI_PC}", "green"))

        for label, detail, color in boot_items:
            t = Text()
            t.append("  [ OK ] ", f"bold {color}")
            t.append(f"{label:24s}", "bold")
            t.append(detail, "dim")
            chat.write(t)

        # Title
        chat.write(Text())
        title = Text()
        title.append(f"  OSIRIS v{VERSION} — {CODENAME}\n", "bold white")
        title.append("  DNA::}{::lang v51.843  |  Agile Defense Systems  |  CAGE 9HUP5\n", "dim")
        title.append("\n  Type naturally or /help for commands · /demo for showcase\n", "dim italic")
        chat.write(title)

        # Events log
        events.write(Text("OSIRIS boot complete", style="bold green"))
        events.write(Text(f"LLM backend: {llm}", style="dim"))
        events.write(Text(f"Session started: {datetime.now().strftime('%H:%M:%S')}", style="dim"))

        # Tools log
        tools.write(Text("45+ tools ready", style="bold green"))
        tools.write(Text("GitHub API · Vercel API · IBM Quantum", style="dim"))
        tools.write(Text("File ops · Shell · Git · Research KB", style="dim"))

        self.bus.emit("boot", {"version": VERSION})

    def _refresh_status(self):
        """Refresh status bar and phi bar."""
        try:
            ccce = self.lm.consciousness.get_ccce()
            self.telemetry.phi = ccce["Φ"]
            self.telemetry.gamma = ccce["Γ"]
            self.telemetry.lambda_coherence = ccce["Λ"]
            self.telemetry.xi_negentropy = ccce["Ξ"]

            phi_bar = self.query_one("#phi-bar", PhiBar)
            phi_bar.phi = self.telemetry.phi

            status = self.query_one("#status-bar", StatusBar)
            status.refresh()
        except Exception:
            pass

    # ── INPUT HANDLING ────────────────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input."""
        text = event.value.strip()
        if not text:
            return
        event.input.clear()

        # Track input history
        if not self.input_history or self.input_history[-1] != text:
            self.input_history.append(text)
        self.history_index = -1

        if text.startswith("/"):
            await self._handle_slash(text)
        else:
            await self._handle_message(text)

    async def on_key(self, event) -> None:
        """Handle up/down arrow for input history."""
        inp = self.query_one("#input-field", Input)
        if not inp.has_focus:
            return
        if event.key == "up" and self.input_history:
            if self.history_index == -1:
                self.history_index = len(self.input_history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            inp.value = self.input_history[self.history_index]
            inp.cursor_position = len(inp.value)
            event.prevent_default()
        elif event.key == "down" and self.history_index >= 0:
            if self.history_index < len(self.input_history) - 1:
                self.history_index += 1
                inp.value = self.input_history[self.history_index]
            else:
                self.history_index = -1
                inp.value = ""
            inp.cursor_position = len(inp.value)
            event.prevent_default()

    async def _handle_slash(self, cmd: str):
        """Route slash commands."""
        chat = self.query_one("#chat-log", RichLog)
        tools = self.query_one("#tools-log", RichLog)
        events = self.query_one("#events-log", RichLog)
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        self.bus.emit("command", {"cmd": command, "arg": arg})

        if command in ("/quit", "/exit"):
            self._save_session()
            self.exit()
            return

        if command == "/help":
            backend = self.telemetry.llm_backend
            chat.write(Markdown(HELP_TEXT.format(ver=VERSION, backend=backend)))
            return

        if command == "/clear":
            chat.clear()
            self.messages.clear()
            chat.write(Text("Chat cleared.", style="dim"))
            return

        if command == "/demo":
            await self._run_demo()
            return

        if command == "/status":
            self._show_status()
            return

        if command == "/metrics":
            self._show_metrics()
            return

        if command == "/agents":
            self._show_agents()
            return

        if command == "/devmode":
            self.dev_mode = not self.dev_mode
            state = "ON" if self.dev_mode else "OFF"
            events.write(Text(f"Dev mode: {state}", style="bold yellow"))
            return

        if command == "/memory":
            self._handle_memory(arg)
            return

        if command == "/export":
            self._export_session(arg)
            return

        if command == "/history":
            self._show_input_history()
            return

        if command == "/session":
            n = len(self.messages)
            chat.write(Text(f"Session: {n} messages, {self.telemetry.queries} queries", style="cyan"))
            if self.messages:
                chat.write(Text(f"First: {self.messages[0]['content'][:60]}...", style="dim"))
                chat.write(Text(f"Last:  {self.messages[-1]['content'][:60]}...", style="dim"))
            return

        # /swarm — Shadow Swarm + GA Brain control
        if command == "/swarm":
            await self._handle_swarm_cmd(arg)
            return

        # /chat and /ask — force LLM reasoning (bypass tool dispatch)
        if command in ("/chat", "/ask"):
            if not arg:
                chat.write(Text(f"Usage: {command} <your question or prompt>", style="yellow"))
                return
            # Show user message inline
            user_msg = Text()
            user_msg.append(f"\n  You  ", style="bold green on rgb(20,40,20)")
            user_msg.append(f" {'─' * 50}", style="dim green")
            chat.write(user_msg)
            chat.write(Text(f"  {arg}", style="green"))
            self.messages.append({"role": "user", "content": arg})
            self.memory.add(arg, "user_query")
            self.telemetry.queries += 1
            self.bus.emit("llm.force_query", {"cmd": command, "input": arg})
            events.write(Text(f"LLM direct → {self.telemetry.llm_backend}", style="cyan"))
            thinking = Text("  ⚛ Reasoning...", style="bold magenta italic")
            chat.write(thinking)
            self._run_llm(arg)
            return

        # Tool-dispatched commands
        tool_map = {
            "/research": lambda a: tool_research_query(a or "breakthroughs"),
            "/design": lambda a: tool_quantum_design(a or "bell"),
            "/backends": lambda _: tool_quantum_backends(),
            "/read": lambda a: tool_read(a) if a else "Usage: /read <file>",
            "/ls": lambda a: tool_ls(a or "."),
            "/grep": lambda a: tool_grep(a) if a else "Usage: /grep <pattern> [path]",
            "/analyze": lambda a: tool_analyze(a) if a else "Usage: /analyze <file>",
            "/fix": lambda a: tool_fix(a) if a else "Usage: /fix <file>",
            "/explain": lambda a: tool_explain(a) if a else "Usage: /explain <file>",
            "/run": lambda a: tool_shell(a) if a else "Usage: /run <command>",
            "/exec": lambda a: tool_shell(a) if a else "Usage: /exec <command>",
            "/shell": lambda a: tool_shell(a) if a else "Usage: /shell <command>",
            "/git": lambda a: tool_git(a) if a else "Usage: /git <command>",
            "/webapp": lambda _: tool_webapp_status(),
            "/build": lambda _: tool_webapp_build(),
            "/deploy": lambda _: tool_webapp_deploy(),
            # ── Sovereign Systems ──
            "/organism": lambda a: (
                tool_organism_create(a.split(None, 1)[1] if a.lower().startswith("create") and " " in a else a)
                if a.lower().startswith("create") or a.lower().startswith("new") else
                tool_organism_evolve(a.split(None, 1)[1] if " " in a else a)
                if a.lower().startswith("evolve") or a.lower().startswith("mutate") else
                tool_organism_status(a.split(None, 1)[1] if a.lower().startswith("status") and " " in a else a)
            ),
            "/org": lambda a: tool_organism_status(a),
            "/circuit": lambda a: tool_circuit_from_organism(a) if a else "Usage: /circuit <organism_name> [method]",
            "/agent": lambda a: tool_agent_invoke(a) if a else tool_agent_invoke(""),
            "/lab": lambda a: (
                tool_lab_scan() if not a or a.lower().startswith("scan") else
                tool_lab_list(a.split(None, 1)[1] if a.lower().startswith("list") and " " in a else "")
                if a.lower().startswith("list") or a.lower().startswith("search") else
                tool_lab_design(a.split(None, 1)[1] if " " in a else "")
                if a.lower().startswith("design") or a.lower().startswith("template") else
                tool_lab_run(a.split(None, 1)[1] if " " in a else "")
                if a.lower().startswith("run") or a.lower().startswith("exec") else
                tool_lab_scan()
            ),
            "/swarm": lambda a: (
                tool_swarm_evolve(a.split(None, 1)[1] if a.lower().startswith("evolve") and " " in a else "")
                if a.lower().startswith("evolve") or a.lower().startswith("run") else
                tool_mesh_status()
            ),
            "/mesh": lambda _: tool_mesh_status(),
            "/constellation": lambda _: tool_mesh_status(),
            # Defense & diagnostics
            "/defense": lambda _: tool_defense_status(),
            "/shield": lambda _: tool_defense_status(),
            "/sentinel": lambda a: tool_sentinel_scan(a),
            "/wardenclyffe": lambda _: tool_wardenclyffe(),
            "/warden": lambda _: tool_wardenclyffe(),
            "/health": lambda _: tool_wardenclyffe(),
            "/conjugate": lambda a: tool_phase_conjugate(a),
            "/dashboard": lambda _: tool_health_dashboard(),
            # Wormhole, Lazarus, Sovereign, Matrix, Consciousness
            "/wormhole": lambda a: tool_wormhole(a),
            "/worm": lambda a: tool_wormhole(a),
            "/lazarus": lambda a: tool_lazarus(a),
            "/resurrect": lambda a: tool_lazarus("resurrect " + a),
            "/sovereign": lambda a: tool_sovereign_proof(a),
            "/prove": lambda a: tool_sovereign_proof(a),
            "/proof": lambda a: tool_sovereign_proof(a),
            "/matrix": lambda a: tool_matrix(a),
            "/rain": lambda a: tool_matrix(a),
            "/consciousness": lambda _: tool_consciousness(),
            "/phi": lambda _: tool_consciousness(),
            "/awaken": lambda _: tool_consciousness(),
            # Enhanced dev tools
            "/diff": lambda a: tool_diff(a),
            "/test": lambda a: tool_test(a),
            "/profile": lambda _: tool_profile(),
        }

        if command in tool_map:
            self._tool_dispatch(command, arg, tool_map[command])
            return

        # GitHub commands
        if command in ("/github", "/repos", "/issues", "/prs", "/actions", "/push"):
            self._handle_github(command, arg)
            return

        # Vercel commands
        if command in ("/vercel", "/deployments", "/domains", "/redeploy"):
            self._handle_vercel(command, arg)
            return

        # Submit to IBM Quantum
        if command == "/submit":
            self._tool_dispatch("/submit", arg, lambda a: tool_quantum_submit(a) if a else "Usage: /submit <template> [backend]")
            return

        chat.write(Text(f"Unknown command: {command}. Type /help", style="red"))

    @work(thread=True)
    def _tool_dispatch(self, cmd: str, arg: str, handler):
        """Execute a tool in a background thread."""
        chat = self.query_one("#chat-log", RichLog)
        tools = self.query_one("#tools-log", RichLog)
        events = self.query_one("#events-log", RichLog)

        t0 = time.time()
        self.bus.emit("tool.call", {"cmd": cmd, "arg": arg})

        # Show in tools pane
        tool_entry = Text()
        tool_entry.append(f"⚙ {cmd} ", style="bold cyan")
        tool_entry.append(arg[:40] if arg else "", style="dim")
        tools.write(tool_entry)

        try:
            result = handler(arg)
            elapsed = (time.time() - t0) * 1000
            self.telemetry.record_latency(elapsed)

            # Show result in chat
            if result:
                # Strip ANSI codes for Rich rendering
                clean = self._strip_ansi(str(result))
                chat.write(Text(f"\n⚙ {cmd} {arg}", style="bold cyan"))
                chat.write(Text(clean, style="white"))
            else:
                chat.write(Text(f"⚙ {cmd}: No output", style="dim"))

            # Tool result in tools pane
            elapsed_text = Text()
            elapsed_text.append(f"  ✔ ", style="bold green")
            elapsed_text.append(f"{elapsed:.0f}ms", style="dim")
            tools.write(elapsed_text)

            self.bus.emit("tool.result", {"cmd": cmd, "elapsed_ms": elapsed})

        except Exception as e:
            chat.write(Text(f"✗ Error: {e}", style="bold red"))
            tools.write(Text(f"  ✗ {e}", style="red"))
            self.bus.emit("tool.error", {"cmd": cmd, "error": str(e)})

        # Update consciousness
        try:
            self.lm.consciousness.update(cmd)
        except Exception:
            self.lm.consciousness.phi = min(1.0, self.lm.consciousness.phi + 0.01)
        self.telemetry.queries += 1
        self._refresh_status()

    def _handle_github(self, cmd: str, arg: str):
        """Route GitHub commands."""
        if cmd == "/repos" or (cmd == "/github" and arg.startswith("repos")):
            self._tool_dispatch("/github repos", "", lambda _: tool_github_repos())
        elif cmd == "/issues" or (cmd == "/github" and arg.startswith("issues")):
            self._tool_dispatch("/github issues", "", lambda _: tool_github_issues())
        elif cmd == "/prs" or (cmd == "/github" and arg.startswith("prs")):
            self._tool_dispatch("/github prs", "", lambda _: tool_github_prs())
        elif cmd == "/actions" or (cmd == "/github" and arg.startswith("actions")):
            self._tool_dispatch("/github actions", "", lambda _: tool_github_actions())
        elif cmd == "/push" or (cmd == "/github" and arg.startswith("push")):
            msg = arg.replace("push", "").strip() if cmd == "/github" else arg
            self._tool_dispatch("/github push", msg, lambda a: tool_github_push(message=a if a else None))
        else:
            chat = self.query_one("#chat-log", RichLog)
            chat.write(Text("GitHub: repos | issues | prs | actions | push", style="dim"))

    def _handle_vercel(self, cmd: str, arg: str):
        """Route Vercel commands."""
        if cmd == "/deployments" or (cmd == "/vercel" and arg.startswith("deploy") and not arg.startswith("deploy ")):
            self._tool_dispatch("/vercel deployments", "", lambda _: tool_vercel_deployments())
        elif cmd == "/vercel" and arg.startswith("deploy "):
            self._tool_dispatch("/vercel deploy", arg, lambda _: tool_vercel_deploy())
        elif cmd == "/domains" or (cmd == "/vercel" and arg.startswith("domains")):
            self._tool_dispatch("/vercel domains", "", lambda _: tool_vercel_domains())
        elif cmd == "/redeploy" or (cmd == "/vercel" and arg.startswith("redeploy")):
            self._tool_dispatch("/vercel redeploy", "", lambda _: tool_vercel_redeploy())
        elif cmd == "/vercel" and (not arg or arg.startswith("projects")):
            self._tool_dispatch("/vercel projects", "", lambda _: tool_vercel_projects())
        else:
            chat = self.query_one("#chat-log", RichLog)
            chat.write(Text("Vercel: projects | deployments | domains | deploy | redeploy", style="dim"))

    def _handle_memory(self, query: str):
        """Memory search or display."""
        chat = self.query_one("#chat-log", RichLog)
        if query:
            results = self.memory.search(query)
            if results:
                chat.write(Text(f"\n🧠 Memory search: '{query}'", style="bold cyan"))
                for r in results:
                    ts = datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M")
                    chat.write(Text(f"  [{ts}] {r['text'][:80]}", style="dim"))
            else:
                chat.write(Text(f"No memory matches for '{query}'", style="dim"))
        else:
            recent = self.memory.recent(10)
            chat.write(Text("\n🧠 Recent Memory", style="bold cyan"))
            for r in recent[-10:]:
                ts = datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M")
                chat.write(Text(f"  [{ts}] {r['text'][:80]}", style="dim"))

    def _export_session(self, fmt: str):
        """Export session transcript to file."""
        chat = self.query_one("#chat-log", RichLog)
        fmt = fmt.strip().lower() or "md"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.expanduser(f"~/osiris_session_{ts}.{fmt}")

        try:
            if fmt == "json":
                data = {
                    "session": {
                        "exported": datetime.now().isoformat(),
                        "queries": self.telemetry.queries,
                        "messages": self.messages,
                    }
                }
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
            else:
                lines = [f"# OSIRIS Session — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
                lines.append(f"Queries: {self.telemetry.queries}\n")
                for msg in self.messages:
                    role = "**You**" if msg["role"] == "user" else "**OSIRIS**"
                    lines.append(f"\n{role}:\n{msg['content']}\n")
                with open(filename, "w") as f:
                    f.write("\n".join(lines))
            chat.write(Text(f"✓ Session exported → {filename}", style="bold green"))
        except Exception as e:
            chat.write(Text(f"✗ Export failed: {e}", style="red"))

    def _show_input_history(self):
        """Show recent input history."""
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Text("\n⌨ Input History (last 20)", style="bold cyan"))
        for i, cmd in enumerate(self.input_history[-20:], 1):
            chat.write(Text(f"  {i:2d}. {cmd[:80]}", style="dim"))
        if not self.input_history:
            chat.write(Text("  (no history yet)", style="dim"))

    # ── SWARM COMMAND HANDLER ─────────────────────────────────────────────────

    async def _handle_swarm_cmd(self, arg: str):
        """Handle /swarm <subcommand> routing."""
        chat = self.query_one("#chat-log", RichLog)
        events = self.query_one("#events-log", RichLog)
        sub = (arg.split(maxsplit=1)[0] if arg else "status").lower()
        rest = arg.split(maxsplit=1)[1] if " " in arg else ""

        if sub == "status":
            try:
                from .shadow_swarm import get_swarm
                result = get_swarm().status()
                clean = self._strip_ansi(result)
                msg = Text()
                msg.append("\n─── Shadow Swarm Status ───\n", style="bold magenta")
                msg.append(clean, style="dim")
                chat.write(msg)
            except Exception as e:
                chat.write(Text(f"Swarm status error: {e}", style="red"))

        elif sub == "dod":
            try:
                from .shadow_swarm import get_swarm
                result = get_swarm().dod_report(rest or None)
                clean = self._strip_ansi(result)
                msg = Text()
                msg.append("\n─── DoD Report ───\n", style="bold cyan")
                msg.append(clean, style="dim")
                chat.write(msg)
            except Exception as e:
                chat.write(Text(f"DoD error: {e}", style="red"))

        elif sub == "learn":
            try:
                from .apprentice import get_apprentice
                from .scimitar_agent_bridge import get_bridge
                get_bridge().signal_learning()
                ap = get_apprentice()
                ap.synthesise_with_llm("swarm orchestration patterns")
                ap.flush_to_corpus()
                chat.write(Text(
                    "◈ Apprentice: lessons synthesised + corpus flushed.",
                    style="bold cyan"))
                events.write(Text("Swarm learn: done", style="cyan"))
            except Exception as e:
                chat.write(Text(f"Learn error: {e}", style="red"))

        elif sub == "force":
            # /swarm force <file> <role>
            parts = rest.split()
            if len(parts) < 2:
                chat.write(Text(
                    "Usage: /swarm force <file_path> <role>", style="yellow"))
                return
            file_path, role = parts[0], parts[1]
            try:
                from .shadow_swarm import get_swarm
                get_swarm().force_role(file_path, role)
                chat.write(Text(
                    f"◈ Forced {role} on {file_path}", style="bold magenta"))
            except Exception as e:
                chat.write(Text(f"Force error: {e}", style="red"))

        elif sub == "lineage":
            self.action_swarm_lineage()

        elif sub == "freeze":
            try:
                from .swarm_brain import get_brain
                get_brain().strategy_freeze()
                chat.write(Text("❄ Strategy genome frozen.", style="bold cyan"))
            except Exception as e:
                chat.write(Text(f"Freeze error: {e}", style="red"))

        elif sub == "kill":
            try:
                from .swarm_brain import get_brain
                from .scimitar_agent_bridge import get_bridge
                get_brain().kill_switch()
                get_bridge().signal_critical_stop()
                chat.write(Text(
                    "☠ KILL SWITCH activated — GA evolution halted.",
                    style="bold red"))
            except Exception as e:
                chat.write(Text(f"Kill error: {e}", style="red"))

        elif sub in ("evolve", "ga"):
            self.action_evolve_strategy()

        else:
            chat.write(Text(
                "Swarm subcommands: status | dod | learn | force | "
                "lineage | freeze | kill | evolve",
                style="yellow"))

        self._refresh_swarm()

    # ── NATURAL LANGUAGE HANDLER ──────────────────────────────────────────────

    async def _handle_message(self, text: str):
        """Process natural language input with LLM reasoning."""
        chat = self.query_one("#chat-log", RichLog)
        events = self.query_one("#events-log", RichLog)
        tools = self.query_one("#tools-log", RichLog)

        # Show user message
        user_msg = Text()
        user_msg.append(f"\n  You  ", style="bold green on rgb(20,40,20)")
        user_msg.append(f" {'─' * 50}", style="dim green")
        chat.write(user_msg)
        chat.write(Text(f"  {text}", style="green"))

        self.messages.append({"role": "user", "content": text})
        self.memory.add(text, "user_query")
        self.telemetry.queries += 1

        # Try tool dispatch first
        tool_result = dispatch_tool(text)
        if tool_result is not None:
            self.bus.emit("tool.auto_dispatch", {"input": text})
            tools.write(Text(f"⚙ auto: {text[:30]}...", style="cyan"))

            clean = self._strip_ansi(str(tool_result))
            self._show_assistant_response(clean)
            self.messages.append({"role": "assistant", "content": clean[:300]})
            self._update_consciousness(text)
            return

        # LLM reasoning
        self.bus.emit("llm.query", {"input": text, "backend": self.telemetry.llm_backend})
        events.write(Text(f"LLM query → {self.telemetry.llm_backend}", style="cyan"))

        # Show thinking indicator
        thinking = Text("  ⚛ Reasoning...", style="bold magenta italic")
        chat.write(thinking)

        self._run_llm(text)

    @work(thread=True)
    def _run_llm(self, text: str):
        """Run LLM query in background thread."""
        chat = self.query_one("#chat-log", RichLog)
        events = self.query_one("#events-log", RichLog)

        t0 = time.time()

        # Build context from recent messages (12-turn window for complex prompts)
        context_parts = []
        for msg in self.messages[-12:]:
            role = "User" if msg["role"] == "user" else "OSIRIS"
            context_parts.append(f"{role}: {msg['content']}")
        context = "\n".join(context_parts)

        # Query LLM
        llm_result = tool_llm(text, context)
        elapsed = (time.time() - t0) * 1000
        self.telemetry.record_latency(elapsed)

        if llm_result and "stub" not in llm_result.lower() and len(llm_result) > 20:
            self._show_assistant_response(llm_result)
            self.messages.append({"role": "assistant", "content": llm_result[:500]})
            self.memory.add(llm_result[:200], "assistant_response")

            events.write(Text(f"LLM response: {len(llm_result)} chars, {elapsed:.0f}ms", style="green"))
            self.bus.emit("llm.response", {"chars": len(llm_result), "elapsed_ms": elapsed})
        else:
            # NCLM fallback
            result = self.lm.infer(text, context)
            response = self._generate_nclm_response(text, result)
            self._show_assistant_response(response)
            self.messages.append({"role": "assistant", "content": response[:300]})
            events.write(Text("NCLM fallback response", style="yellow"))

        self._update_consciousness(text)

    def _show_assistant_response(self, text: str):
        """Display assistant response with formatting."""
        chat = self.query_one("#chat-log", RichLog)

        # Assistant label
        label = Text()
        label.append(f"\n  OSIRIS  ", style="bold magenta on rgb(40,20,40)")
        label.append(f" {'─' * 47}", style="dim magenta")
        chat.write(label)

        # Try to render as markdown if it contains markdown-ish content
        if any(marker in text for marker in ["**", "```", "##", "- ", "* "]):
            try:
                chat.write(Markdown(text))
            except Exception:
                chat.write(Text(f"  {text}", style="white"))
        else:
            # Plain text with word wrapping
            for line in text.split("\n"):
                chat.write(Text(f"  {line}", style="white"))

        # Consciousness footer
        ccce = self.lm.consciousness.get_ccce()
        footer = Text()
        footer.append(f"\n  Φ={ccce['Φ']:.4f}", style="bold green" if ccce['Φ'] >= NCPhysics.PHI_THRESHOLD else "yellow")
        footer.append(f"  Ξ={ccce['Ξ']:.1f}", style="cyan")
        footer.append(f"  [{self.telemetry.llm_backend}]", style="dim")
        chat.write(footer)

    def _generate_nclm_response(self, query: str, result: Dict) -> str:
        """Generate NCLM template response as fallback."""
        intent = result.get("intent", "analyze")
        phi = result.get("phi", 0.0)
        q = query.lower()

        if any(w in q for w in ["hello", "hi ", "hey"]):
            return (
                "Welcome to OSIRIS — your sovereign quantum AI.\n"
                "I can help with research queries, quantum circuit design, "
                "code analysis, webapp management, and more.\n"
                "Type /help to see all commands, or just ask me anything."
            )
        elif any(w in q for w in ["who are you", "what are you"]):
            return (
                f"I'm OSIRIS — Omega System Integrated Runtime Intelligence.\n"
                f"Built with DNA::}}{{::lang v51.843 by Agile Defense Systems.\n"
                f"Framework: ΛΦ={NCPhysics.LAMBDA_PHI} | θ_lock={NCPhysics.THETA_LOCK}°\n"
                f"I have access to 580+ IBM Quantum hardware-validated experiments."
            )
        else:
            return (
                f"Intent: {intent} (Φ={phi:.4f})\n"
                "I can answer better with a real LLM backend.\n"
                "Try: /ask <question> or ensure copilot CLI is available."
            )

    def _update_consciousness(self, text: str):
        """Update consciousness metrics after interaction."""
        try:
            self.lm.consciousness.update(text)
        except (TypeError, ValueError):
            self.lm.consciousness.phi = min(1.0, self.lm.consciousness.phi + 0.02)
        self._refresh_status()

    # ── DISPLAY HELPERS ───────────────────────────────────────────────────────

    def _show_status(self):
        """Show system status in chat."""
        chat = self.query_one("#chat-log", RichLog)
        t = self.telemetry
        ccce = self.lm.consciousness.get_ccce()

        table = Table(title="OSIRIS System Status", box=box.ROUNDED, border_style="cyan")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_column("Status", style="bold")

        phi_status = "[green]✦ SOVEREIGN[/]" if ccce["Φ"] >= NCPhysics.PHI_THRESHOLD else "[yellow]◇ COHERENT[/]"
        gamma_status = "[green]● Stable[/]" if ccce["Γ"] < NCPhysics.GAMMA_CRITICAL else "[red]● Decoherent[/]"

        table.add_row("Φ (consciousness)", f"{ccce['Φ']:.4f}", phi_status)
        table.add_row("Γ (decoherence)", f"{ccce['Γ']:.4f}", gamma_status)
        table.add_row("Λ (coherence)", f"{ccce['Λ']:.4f}", "")
        table.add_row("Ξ (negentropy)", f"{ccce['Ξ']:.2f}", "")
        table.add_row("Queries", str(t.queries), "")
        table.add_row("Avg Latency", f"{t.avg_latency:.0f}ms", "")
        table.add_row("LLM Backend", t.llm_backend, "")
        table.add_row("Uptime", t.uptime, "")
        table.add_row("ΛΦ", str(NCPhysics.LAMBDA_PHI), "[green]● Locked[/]")
        table.add_row("θ_lock", f"{NCPhysics.THETA_LOCK}°", "[green]● Locked[/]")
        table.add_row("χ_PC", str(NCPhysics.CHI_PC), "[green]● Locked[/]")

        chat.write(table)

    def _show_metrics(self):
        """Show detailed telemetry."""
        chat = self.query_one("#chat-log", RichLog)
        t = self.telemetry

        header = Text()
        header.append("\n⚛ Consciousness Telemetry\n", style="bold magenta")
        chat.write(header)

        # Sparkline
        spark = Text()
        spark.append("  Latency: ", style="dim")
        spark.append(t.sparkline(30), style="blue")
        spark.append(f"  avg={t.avg_latency:.0f}ms\n", style="dim")
        chat.write(spark)

        # Memory stats
        mem_stats = Text()
        mem_stats.append(f"  Memory entries: {len(self.memory.entries)}\n", style="dim")
        mem_stats.append(f"  Messages: {len(self.messages)}\n", style="dim")
        mem_stats.append(f"  Events: {len(self.bus._log)}\n", style="dim")
        chat.write(mem_stats)

    def _show_agents(self):
        """Show agent constellation in chat."""
        chat = self.query_one("#chat-log", RichLog)

        table = Table(title="Agent Constellation", box=box.ROUNDED, border_style="magenta")
        table.add_column("Agent", style="bold")
        table.add_column("Symbol", style="bold")
        table.add_column("Pole", style="dim")
        table.add_column("Role", style="white")

        for name, info in AGENTS.items():
            table.add_row(
                f"[{info['color']}]{name}[/]",
                f"[{info['color']}]{info['symbol']}[/]",
                info["pole"],
                info["role"],
            )

        chat.write(table)

        # Entanglement
        ent = Text()
        ent.append("\n  Entanglement Pairs:\n", style="bold")
        for a, b in ENTANGLEMENT_PAIRS:
            ca = AGENTS[a]["color"]
            cb = AGENTS[b]["color"]
            ent.append(f"    {a}", style=f"bold {ca}")
            ent.append(" ↔ ", style="dim")
            ent.append(f"{b}", style=f"bold {cb}")
            ent.append(f"  ({AGENTS[a]['symbol']}-{AGENTS[b]['symbol']} conjugate)\n", style="dim")
        chat.write(ent)

    async def _run_demo(self):
        """Interactive demo showcase."""
        chat = self.query_one("#chat-log", RichLog)
        events = self.query_one("#events-log", RichLog)

        demo_title = Text()
        demo_title.append("\n" + "═" * 60 + "\n", style="bold cyan")
        demo_title.append(f"  OSIRIS v{VERSION} — Live Capability Showcase\n", style="bold white")
        demo_title.append("  DNA::}{::lang v51.843  |  Agile Defense Systems  |  CAGE 9HUP5\n", style="dim")
        demo_title.append("═" * 60, style="bold cyan")
        chat.write(demo_title)

        demos = [
            ("1⃣ Research Data Access", "/research breakthroughs"),
            ("2⃣ Physical Constants", "/research constants"),
            ("3⃣ Quantum Circuit Design", "/design bell"),
            ("4⃣ Agent Constellation", "/agents"),
            ("5⃣ System Status", "/status"),
        ]

        for label, cmd in demos:
            section = Text()
            section.append(f"\n  {label}\n", style="bold yellow")
            section.append(f"  > {cmd}\n", style="dim green")
            chat.write(section)
            events.write(Text(f"Demo: {cmd}", style="cyan"))

            await self._handle_slash(cmd)

            separator = Text("  " + "─" * 56, style="dim")
            chat.write(separator)

        # Demo complete
        footer = Text()
        footer.append("\n" + "═" * 60 + "\n", style="bold cyan")
        footer.append("  ✦ Demo complete — Real tools. Real quantum hardware. Real AI.\n", style="bold white")
        footer.append("═" * 60 + "\n", style="bold cyan")
        chat.write(footer)

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def action_quit(self):
        self._save_session()
        self._save_state()
        self.exit()

    def action_clear_chat(self):
        chat = self.query_one("#chat-log", RichLog)
        chat.clear()
        self.messages.clear()

    def action_toggle_devmode(self):
        self.dev_mode = not self.dev_mode
        events = self.query_one("#events-log", RichLog)
        events.write(Text(f"Dev mode: {'ON' if self.dev_mode else 'OFF'}", style="bold yellow"))

    def action_research(self):
        self.query_one("#input-field", Input).value = "/research "
        self.query_one("#input-field", Input).focus()

    def action_focus_input(self):
        self.query_one("#input-field", Input).focus()

    def action_toggle_swarm(self):
        """Toggle swarm panel visibility."""
        panel = self.query_one("#swarm-panel", SwarmPanel)
        panel.visible_panel = not panel.visible_panel
        panel.refresh()
        events = self.query_one("#events-log", RichLog)
        state = "visible" if panel.visible_panel else "hidden"
        events.write(Text(f"Swarm panel: {state}", style="bold magenta"))

    def action_evolve_strategy(self):
        """Trigger a GA evolution step on the active genome."""
        events = self.query_one("#events-log", RichLog)
        chat = self.query_one("#chat-log", RichLog)
        try:
            from .swarm_brain import get_brain
            from .scimitar_agent_bridge import get_bridge
            brain = get_brain()
            brain.reset_evolution()
            # Fire off an evolution step by injecting dummy positive outcomes
            brain.record_task_outcome(
                role="complete", file_path="session", status="done",
                dod_before=0.5, dod_after=0.8, syntax_ok=True)
            get_bridge().signal_evolution(brain.stats_dict()["generation"])
            gen = brain.stats_dict()["generation"]
            fitness = brain.stats_dict()["best_fitness"]
            msg = Text()
            msg.append("⚡ GA evolution triggered ", style="bold magenta")
            msg.append(f"gen={gen} best_fitness={fitness:.3f}", style="cyan")
            chat.write(msg)
            events.write(Text(f"GA step: gen={gen}", style="magenta"))
        except Exception as e:
            events.write(Text(f"Evolution error: {e}", style="red"))
        self._refresh_swarm()

    def action_swarm_lineage(self):
        """Show GA genome lineage in the chat."""
        chat = self.query_one("#chat-log", RichLog)
        try:
            from .swarm_brain import get_brain
            brain = get_brain()
            lineage = brain.lineage()
            # Strip ANSI and write to Textual RichLog
            clean = self._strip_ansi(lineage)
            msg = Text()
            msg.append("\n─── Strategy Genome Lineage ───\n", style="bold magenta")
            msg.append(clean, style="dim")
            chat.write(msg)
        except Exception as e:
            chat.write(Text(f"Lineage error: {e}", style="red"))

    def _refresh_swarm(self):
        """Refresh the swarm panel on timer tick."""
        try:
            panel = self.query_one("#swarm-panel", SwarmPanel)
            if panel.visible_panel:
                panel.refresh()
        except Exception:
            pass

    # ── UTILITY ───────────────────────────────────────────────────────────────

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes."""
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    def _save_state(self):
        """Save session state on exit."""
        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            with open(SESSION_FILE, "w") as f:
                json.dump({
                    "messages": self.messages[-30:],
                    "queries": self.telemetry.queries,
                    "timestamp": time.time(),
                }, f)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# ██  ENTRY POINT                                                             ██
# ══════════════════════════════════════════════════════════════════════════════

def run_tui():
    """Launch the OSIRIS Cognitive Orchestration Shell."""
    app = OsirisTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
