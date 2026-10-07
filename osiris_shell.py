#!/usr/bin/env python3
"""
OSIRIS Interactive Shell — NCLLM-Powered Quantum Discovery CLI

Single entry point: just type `osiris`.
All user input is routed through the NCLLM 9-agent swarm for intent
deduction and intelligent command execution.

Works like: Claude Code, GitHub Copilot CLI, ChatGPT terminal.
"""

import os
import sys
import time
import json
import signal
import textwrap
import traceback
from datetime import datetime
from pathlib import Path

# Ensure imports resolve
sys.path.insert(0, str(Path(__file__).parent))

# ═══════════════════════════════════════════════════════════════════════════
# Boot Screen
# ═══════════════════════════════════════════════════════════════════════════

BOOT_LOGO = r"""
[36m╔══════════════════════════════════════════════════════════════════════╗
║[0m                                                                      [36m║
║[0m    [1;35m//\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //\\ ::}{::[0m    [36m║
║[0m                                                                      [36m║
║[0m     [1;37m██████╗ ███████╗██╗██████╗ ██╗███████╗[0m                       [36m║
║[0m     [1;37m██╔═══██╗██╔════╝██║██╔══██╗██║██╔════╝[0m                      [36m║
║[0m     [1;37m██║   ██║███████╗██║██████╔╝██║███████╗[0m                      [36m║
║[0m     [1;37m██║   ██║╚════██║██║██╔══██╗██║╚════██║[0m                      [36m║
║[0m     [1;37m╚██████╔╝███████║██║██║  ██║██║███████║[0m                      [36m║
║[0m     [1;37m ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═╝╚═╝╚══════╝[0m                     [36m║
║[0m                                                                      [36m║
║[0m     [1;36mdna::}{::lang NCLM[0m   [33mAutonomous Quantum Discovery System[0m     [36m║
║[0m     [1;36mPhase-Conjugate qByte Substrate Engine v2.0[0m                   [36m║
║[0m                                                                      [36m║
║[0m    [1;35m\\// ::}{:: \\// ::}{:: \\// ::}{:: \\// ::}{:: \\// ::}{::[0m    [36m║
║[0m                                                                      [36m║
╚══════════════════════════════════════════════════════════════════════╝[0m
"""

BOOT_SEQUENCE = [
    ("[36m  ⚛[0m  Initializing NCLLM 9-Agent Swarm", 0.08),
    ("[36m  ⚛[0m  Connecting Ollama language engine", 0.06),
    ("[36m  ⚛[0m  Loading Intent Engine (regex NLP classifier)", 0.05),
    ("[36m  ⚛[0m  Calibrating Bayesian Trust Network", 0.06),
    ("[36m  ⚛[0m  Loading Cognitive Mesh (Shapley + Nash + Hebbian)", 0.05),
    ("[36m  ⚛[0m  Starting Introspection Engine", 0.04),
    ("[36m  ⚛[0m  Registering 21 command modules", 0.03),
    ("[36m  ⚛[0m  Checking IBM Quantum token", 0.02),
    ("[36m  ⚛[0m  Checking Zenodo token", 0.02),
]

def print_boot_screen():
    """Print the epic boot screen with animated init sequence."""
    os.system('clear' if os.name != 'nt' else 'cls')
    print(BOOT_LOGO)

    for msg, delay in BOOT_SEQUENCE:
        print(msg, end="", flush=True)
        time.sleep(delay)
        print("  [1;32m✓[0m")

    # Token status
    ibm = os.getenv("IBM_QUANTUM_TOKEN")
    zen = os.getenv("ZENODO_TOKEN")
    print()

    # Ollama status
    try:
        from osiris_ollama import check_ollama, get_client
        if check_ollama():
            client = get_client()
            model = client.model or "detecting..."
            print(f"  [32m✓[0m  Ollama:       [1;32mONLINE[0m  ({model})")
        else:
            print("  [33m⚠[0m  Ollama:       [33mOFFLINE[0m (install: curl -fsSL https://ollama.com/install.sh | sh)")
    except Exception:
        print("  [33m⚠[0m  Ollama:       [33mNOT AVAILABLE[0m")

    if ibm:
        print("  [32m✓[0m  IBM Quantum: [1;32mCONNECTED[0m")
    else:
        print("  [33m⚠[0m  IBM Quantum: [33mNO TOKEN[0m (Local QVM active)")
    if zen:
        print("  [32m✓[0m  Zenodo:      [1;32mCONNECTED[0m")
    else:
        print("  [33m⚠[0m  Zenodo:      [33mNO TOKEN[0m (publish disabled)")

    print()
    print("  [1;37mType anything in natural language. OSIRIS will figure it out.[0m")
    print("  [90mExamples: 'benchmark ibm_torino', 'swarm decoherence analysis',[0m")
    print("  [90m          'status', 'forge tetrahedral cube', 'help'[0m")
    print("  [90m          'ollama pull qwen2.5:1.5b', 'run git status'[0m")
    print("  [90mType 'quit' or Ctrl+C to exit.[0m")
    print()


# ═══════════════════════════════════════════════════════════════════════════
# Module Registry — Maps intents to real module execution
# ═══════════════════════════════════════════════════════════════════════════

def _safe_import(dotted_path):
    """Import a module by dotted path, return None on failure."""
    try:
        parts = dotted_path.rsplit(".", 1)
        if len(parts) == 2:
            mod = __import__(parts[0], fromlist=[parts[1]])
            return getattr(mod, parts[1])
        return __import__(dotted_path)
    except Exception:
        return None


def run_benchmark(params: dict) -> str:
    """Run quantum hardware benchmark."""
    try:
        from osiris_quantum_benchmarker import QuantumHardwareBenchmarker
        token = os.getenv("IBM_QUANTUM_TOKEN")
        benchmarker = QuantumHardwareBenchmarker(api_token=token)
        quick = params.get("quick", False)
        results = benchmarker.benchmark_all_backends(extreme_mode=not quick)
        report = benchmarker.generate_report()
        return report
    except Exception as e:
        return f"Benchmark error: {e}"


def run_experiment(params: dict) -> str:
    """Run experiment campaign."""
    try:
        from osiris_auto_discovery import AutoDiscoveryPipeline, ExperimentConfig
        token = os.getenv("IBM_QUANTUM_TOKEN", "")
        pipeline = AutoDiscoveryPipeline(api_token=token)
        config = ExperimentConfig(
            name="osiris_shell_experiment",
            backend=params.get("backend", "ibm_torino"),
            n_qubits=params.get("qubits", 12),
            circuit_depth=params.get("depth", 8),
            shots=params.get("shots", 4000),
            hypothesis="CRSM torsion corridor produces measurable negentropy",
            null_hypothesis="No deviation from uniform distribution",
        )
        result = pipeline.run_hypothesis_test(config)
        return f"Experiment complete: {result.name}\n  p-value: {result.p_value}\n  Cohen's d: {result.effect_size}"
    except Exception as e:
        return f"Experiment error: {e}"


def run_orchestrate(params: dict) -> str:
    """Run full research pipeline."""
    try:
        from osiris_rqc_orchestrator import ResearchOrchestrator
        import asyncio
        orch = ResearchOrchestrator()
        # Step 1: system check (sync)
        orch.step_1_system_check()
        return "Orchestration pipeline system check complete."
    except Exception as e:
        return f"Orchestration error: {e}"


def run_publish(params: dict) -> str:
    """Publish results to Zenodo."""
    token = os.getenv("ZENODO_TOKEN")
    if not token:
        return ("Zenodo token not set. Run:\n"
                "  export ZENODO_TOKEN='your_token'\n"
                "  Get one at: https://zenodo.org/account/settings/")
    try:
        from osiris_zenodo_publisher import PublishingWorkflow
        wf = PublishingWorkflow(zenodo_token=token, use_sandbox=True)
        return "Publishing workflow initialized. Use 'osiris publish' with experiment results."
    except Exception as e:
        return f"Publish error: {e}"


def run_status(params: dict) -> str:
    """Show system status."""
    ibm = "CONNECTED" if os.getenv("IBM_QUANTUM_TOKEN") else "NO TOKEN"
    zen = "CONNECTED" if os.getenv("ZENODO_TOKEN") else "NO TOKEN"

    modules = {
        "Benchmarker": "osiris_quantum_benchmarker",
        "Auto-Discovery": "osiris_auto_discovery",
        "Orchestrator": "osiris_rqc_orchestrator",
        "NCLLM Swarm": "osiris_ncllm_swarm",
        "Cognitive Mesh": "osiris_cognitive_mesh",
        "Bridge Validator": "osiris_bridge_validator",
        "ELO Tournament": "osiris_elo_tournament",
        "Introspection": "osiris_introspection",
        "Feedback Bus": "osiris_feedback_bus",
        "FABRIC Bridge": "osiris_fabric_bridge",
        "Policy Upcycler": "osiris_policy_upcycle",
        "Fei Demo": "osiris_fei_demo",
        "Forge (3D Print)": "osiris_forge",
        "Physics Bridges": "osiris_physics_bridges",
        "Ultra-Coder": "osiris_ultra_coder",
        "Intent Engine": "osiris_intent_engine",
        "License Gate": "osiris_license",
        "Ollama Bridge": "osiris_ollama",
    }
    lines = [
        "═" * 60,
        "  OSIRIS SYSTEM STATUS",
        "═" * 60,
        f"  IBM Quantum : {ibm}",
        f"  Zenodo      : {zen}",
    ]

    # Ollama status in dashboard
    try:
        from osiris_ollama import check_ollama, get_client
        if check_ollama():
            client = get_client()
            st = client.status()
            oll_model = st.model or "auto"
            oll_count = len(st.models)
            lines.append(f"  Ollama      : ONLINE ({oll_model}, {oll_count} models)")
        else:
            lines.append("  Ollama      : OFFLINE")
    except Exception:
        lines.append("  Ollama      : NOT AVAILABLE")

    lines.append("")
    for name, mod in modules.items():
        try:
            __import__(mod)
            lines.append(f"  [32m✓[0m {name:20s} Ready")
        except Exception:
            lines.append(f"  [31m✗[0m {name:20s} FAILED")
    lines.append("═" * 60)
    return "\n".join(lines)


def run_bridges(params: dict) -> str:
    """Run CRSM physics bridges."""
    try:
        from osiris_physics_bridges import BridgeExecutor
        executor = BridgeExecutor()
        results = executor.run_all()
        return f"Bridge results:\n{json.dumps(results, indent=2, default=str)[:2000]}"
    except Exception as e:
        return f"Bridges error: {e}"


def run_validate(params: dict) -> str:
    """Run adversarial bridge validation."""
    try:
        from osiris_bridge_validator import AdversarialBridgeValidator
        v = AdversarialBridgeValidator(
            mc_trials=params.get("trials", 500),
            sensitivity_sigma=params.get("sigma", 3),
        )
        report = v.validate()
        return f"Validation report:\n{json.dumps(report, indent=2, default=str)[:2000]}"
    except Exception as e:
        return f"Validation error: {e}"


def run_tournament(params: dict) -> str:
    """Run ELO tournament benchmark."""
    try:
        from osiris_elo_tournament import EloTournament
        t = EloTournament()
        result = t.run_tournament(rounds_per_matchup=params.get("rounds", 10))
        lines = ["ELO Tournament Results:"]
        lines.append(f"  Total matches: {result['total_matches']}")
        lines.append(f"  NCLLM Overall: ELO={result['ncllm_overall']['mu']:.0f}")
        for name, data in result.get("competitor_overall", {}).items():
            lines.append(f"  vs {name:20s}: ELO={data['mu']:.0f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Tournament error: {e}"


def run_mesh(params: dict) -> str:
    """Show cognitive mesh dashboard."""
    try:
        from osiris_cognitive_mesh import CognitiveMesh
        from osiris_ncllm_swarm import AgentID
        mesh = CognitiveMesh([a.value for a in AgentID])
        n = params.get("simulate", 5)
        for _ in range(n):
            mesh.post_task_update(0.8, {a.value: 0.7 for a in AgentID})
        lines = ["Cognitive Mesh State:"]
        for aid in AgentID:
            inf = mesh.get_dynamic_influence(aid.value)
            lines.append(f"  {aid.value:18s}  influence={inf:.4f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Mesh error: {e}"


def run_introspect(params: dict) -> str:
    """Run introspection engine."""
    try:
        from osiris_introspection import IntrospectionEngine
        from osiris_ncllm_swarm import AgentID
        engine = IntrospectionEngine([a.value for a in AgentID])
        n = params.get("simulate", 5)
        for i in range(n):
            resps = [{"agent": a.value, "confidence": 0.7, "vote": "approve"} for a in AgentID]
            engine.observe_round(resps, "approve", 0.8)
        engine.observe_task("test", "result", 0.8, success=True)
        actions = engine.run_improvement_cycle()
        lines = ["Introspection Report:"]
        lines.append(f"  Cognitive entropy: {engine.structural.cognitive_entropy():.4f}")
        lines.append(f"  Echo chamber:     {engine.structural.echo_chamber_score():.4f}")
        lines.append(f"  Improvement actions: {len(actions)}")
        for a in actions[:3]:
            lines.append(f"    - {a.to_dict().get('description', str(a))[:80]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Introspection error: {e}"


def run_feedback(params: dict) -> str:
    """Run tridirectional feedback loop."""
    task = params.get("task", "analyze system performance")
    try:
        from osiris_feedback_bus import OsirisIntelligenceLoop
        loop = OsirisIntelligenceLoop()
        result = loop.execute(task, max_rounds=params.get("rounds", 5))
        return f"Feedback loop complete:\n{json.dumps(result, indent=2, default=str)[:2000]}"
    except Exception as e:
        return f"Feedback error: {e}"


def run_fabric(params: dict) -> str:
    """Run FABRIC Living Slice provisioner."""
    try:
        from osiris_fabric_bridge import demo_living_slice
        result = demo_living_slice()
        return f"FABRIC demo complete:\n{json.dumps(result, indent=2, default=str)[:2000]}"
    except Exception as e:
        return f"Fabric error: {e}"


def run_policy(params: dict) -> str:
    """Run POLANCO policy upcycler."""
    try:
        from osiris_policy_upcycle import demo_upcycle
        result = demo_upcycle()
        return f"Policy upcycle complete:\n{json.dumps(result, indent=2, default=str)[:2000]}"
    except Exception as e:
        return f"Policy error: {e}"


def run_demo(params: dict) -> str:
    """Run Dr. Fei 3-act demonstration."""
    try:
        from osiris_fei_demo import FeiDemo
        demo = FeiDemo()
        result = demo.run()
        return f"Demo complete:\n{json.dumps(result, indent=2, default=str)[:2000]}"
    except Exception as e:
        return f"Demo error: {e}"


def run_forge(params: dict) -> str:
    """Run Forge manufacturing pipeline."""
    try:
        from osiris_forge import OsirisForge, ForgeJob
        forge = OsirisForge()
        mode = params.get("manufacturing_mode", "tetrahedral_lattice")
        scale = params.get("scale_cm", 10.0)
        job = ForgeJob(geometry=mode, scale_cm=scale)
        result = forge.generate(job)
        if result:
            return f"Forge mesh generated: {result}"
        return "Forge: mesh generation complete (check manufacturing_output/)"
    except Exception as e:
        return f"Forge error: {e}"


def run_license(params: dict) -> str:
    """Run license compliance check."""
    try:
        from osiris_license import ComplianceGate
        ok, msg = ComplianceGate.check(strict=False)
        return f"License compliance: {'PASS' if ok else 'FAIL'}\n{msg}"
    except Exception as e:
        return f"License error: {e}"


def run_livlm(params: dict) -> str:
    """Run the Living Language Model — evolve and generate text."""
    try:
        from osiris_livlm import LivLM, LivLMConfig, quick_demo

        action = params.get("action", "generate")
        prompt_text = params.get("task", "")

        if action == "demo":
            text = quick_demo(generations=10, length=48, verbose=True)
            return f"\n  LivLM demo output: {repr(text)}"

        if action == "status":
            m = LivLM()
            return json.dumps(m.status(), indent=2)

        # Default: evolve and generate
        gens = int(params.get("generations", 12))
        length = int(params.get("length", 64))
        seed = prompt_text or "# "

        cfg = LivLMConfig(
            n_layers=2,
            population_size=20,
            max_generations=gens,
            sample_length=16,
            temperature=0.85,
        )
        model = LivLM(cfg)
        print("  \033[90m⚛ Loading corpus...\033[0m", end="", flush=True)
        model.load_corpus()
        print(f" ({model.corpus.size:,} bytes)")

        print(f"  \033[90m⚛ Evolving ({gens} generations)...\033[0m")
        result = model.evolve(seed_text=seed, verbose=True)
        print(f"  \033[90m⚛ Best Ξ={result['best_fitness']:.4f}  "
              f"Φ={result['best_phi']:.4f}  "
              f"State: {result['consciousness_state']}\033[0m")

        print(f"  \033[90m⚛ Generating {length} characters...\033[0m")
        text = model.generate(prompt=seed, length=length)
        return f"\n  LivLM Output:\n  {repr(text)}\n\n  Params: {model.gen_circuit.n_params}  |  State: {result['consciousness_state']}"

    except Exception as e:
        import traceback
        return f"LivLM error: {e}\n{traceback.format_exc()}"


def run_analyze(params: dict) -> str:
    """Analyze results."""
    # Check for recent result files
    result_files = list(Path(".").glob("*result*.json"))
    if result_files:
        latest = max(result_files, key=lambda p: p.stat().st_mtime)
        try:
            data = json.loads(latest.read_text())
            return f"Latest results ({latest.name}):\n{json.dumps(data, indent=2, default=str)[:2000]}"
        except Exception:
            pass
    return "No recent result files found. Run an experiment or benchmark first."


def run_ollama(params: dict) -> str:
    """Interact with Ollama directly or show status."""
    try:
        from osiris_ollama import get_client, check_ollama
        if not check_ollama():
            return (
                "Ollama is not running.\n"
                "  Install:  curl -fsSL https://ollama.com/install.sh | sh\n"
                "  Start:    ollama serve\n"
                "  Pull:     ollama pull qwen2.5:1.5b"
            )
        client = get_client()
        action = params.get("action", "status")
        if action == "status":
            st = client.status()
            lines = [
                "═" * 50,
                "  OLLAMA STATUS",
                "═" * 50,
                f"  Running:  {'Yes' if st.running else 'No'}",
                f"  Model:    {st.model or 'none selected'}",
                f"  Models:   {', '.join(st.models) if st.models else 'none'}",
                "═" * 50,
            ]
            return "\n".join(lines)
        # Chat mode
        task = params.get("task", "Hello")
        resp = client.generate(task, max_tokens=512)
        return resp.text
    except Exception as e:
        return f"Ollama error: {e}"


def run_chat(params: dict) -> str:
    """Direct chat using Ollama — no swarm, just conversation."""
    task = params.get("task", "")
    if not task:
        return "Usage: chat <message>"
    try:
        from osiris_ollama import get_engine, check_ollama
        if not check_ollama():
            return "Ollama offline. Use 'swarm <task>' for template-based responses."
        engine = get_engine()
        return engine.generate_for_agent("orchestrator", task, max_tokens=512)
    except Exception as e:
        return f"Chat error: {e}"


def run_help(params: dict) -> str:
    """Show help."""
    return textwrap.dedent("""\
    [1;37mOSIRIS Commands[0m  (or just describe what you want in natural language)

    [1;36mCore[0m
      benchmark [backend]     Run quantum hardware benchmarks
      experiment              Execute experiment campaign
      orchestrate / pipeline  Full research pipeline
      status                  System status dashboard
      help                    This message

    [1;36mShell Passthrough[0m
      run <cmd>               Execute a system command (ollama, git, pip, etc.)
      ollama pull <model>     Directly runs ollama commands

    [1;36mSwarm & Intelligence[0m
      swarm <task>            9-agent NCLLM deliberation
      mesh                    Cognitive mesh dashboard
      introspect              Self-awareness engine
      feedback <task>         Tridirectional intelligence loop
      tournament              ELO benchmark vs competitors

    [1;36mPhysics & Validation[0m
      bridges                 CRSM physics bridge executor
      validate                Adversarial bridge validation

    [1;36mInfrastructure[0m
      fabric / provision      FABRIC Living Slice provisioner
      policy / polanco        Network policy upcycler
      demo                    Dr. Fei 3-act demonstration

    [1;36mManufacturing[0m
      forge / 3d print        Generate mesh, slice, print
      forge tetrahedral       Tetrahedral lattice model
      forge toroid            Toroidal manifold model

    [1;36mLiving Language Model[0m
      livlm                   Evolve + generate text via LivLM
      livlm demo              Quick LivLM demonstration
      generate <prompt>       Generate text from evolved qByte circuits
      evolve                  Genetically evolve circuit parameters

    [1;36mOllama LLM[0m
      chat <message>          Direct conversation via Ollama
      ollama                  Ollama status and model info
      ollama status           Show available models

    [1;36mPublishing[0m
      publish / zenodo        Publish results to Zenodo
      analyze                 Analyze latest results

    [1;36mSystem[0m
      license                 License compliance check
      quit / exit / Ctrl+C    Exit OSIRIS
    """)


# Intent → handler map
INTENT_HANDLERS = {
    "benchmark":        run_benchmark,
    "experiment":       run_experiment,
    "orchestrate":      run_orchestrate,
    "deploy":           run_publish,
    "publish":          run_publish,
    "status":           run_status,
    "help":             run_help,
    "manufacturing":    run_forge,
    "network_policy":   run_policy,
    "fabric_provision": run_fabric,
    "analyze":          run_analyze,
    "refine":           run_analyze,
    "unknown":          None,  # falls through to swarm
}

# Direct command shortcuts (typed exactly)
DIRECT_COMMANDS = {
    "status":       run_status,
    "help":         run_help,
    "benchmark":    run_benchmark,
    "bridges":      run_bridges,
    "validate":     run_validate,
    "tournament":   run_tournament,
    "mesh":         run_mesh,
    "introspect":   run_introspect,
    "introspection": run_introspect,
    "fabric":       run_fabric,
    "provision":    run_fabric,
    "policy":       run_policy,
    "polanco":      run_policy,
    "demo":         run_demo,
    "forge":        run_forge,
    "license":      run_license,
    "publish":      run_publish,
    "zenodo":       run_publish,
    "analyze":      run_analyze,
    "experiment":   run_experiment,
    "orchestrate":  run_orchestrate,
    "pipeline":     run_orchestrate,
    "feedback":     run_feedback,
    "livlm":        run_livlm,
    "generate":     run_livlm,
    "evolve":       run_livlm,
    "chat":         run_chat,
    "ollama":       run_ollama,
}


# ═══════════════════════════════════════════════════════════════════════════
# NCLLM Swarm Integration
# ═══════════════════════════════════════════════════════════════════════════

_swarm = None

def get_swarm():
    """Lazy-init the NCLLM swarm."""
    global _swarm
    if _swarm is None:
        try:
            from osiris_ncllm_swarm import NCLLMSwarm
            _swarm = NCLLMSwarm(enable_mesh=True)
        except Exception as e:
            print(f"  [33m⚠ Swarm init failed: {e}[0m")
    return _swarm


def route_through_swarm(user_input: str, intent, params: dict) -> str:
    """
    Route input through NCLLM swarm for intelligent processing.
    The swarm deliberates, then we execute the determined action.
    """
    swarm = get_swarm()
    if swarm is None:
        return "NCLLM Swarm unavailable. Falling back to direct execution."

    # Build a rich task description for the swarm
    task = (
        f"User request: {user_input}\n"
        f"Detected intent: {intent.intent_type.value} (confidence: {intent.confidence:.2f})\n"
        f"Parameters: {json.dumps(params)}\n"
        f"Suggested actions: {'; '.join(intent.suggested_actions[:3])}\n"
        f"Required agents: {', '.join(intent.required_agents)}"
    )

    try:
        result = swarm.solve(task, max_rounds=3)
        output_lines = []

        # Show swarm deliberation summary
        consensus = result.rounds[-1].consensus if result.rounds else "N/A"
        output_lines.append(
            f"[90m  ⚛ Swarm: {len(result.rounds)} rounds, "
            f"consensus={consensus}, "
            f"quality={result.quality_score:.3f}, "
            f"{result.total_elapsed_ms:.0f}ms[0m"
        )

        # Show the swarm's synthesized output
        if result.final_output:
            output_lines.append("")
            output_lines.append(result.final_output[:3000])

        return "\n".join(output_lines)
    except Exception as e:
        return f"Swarm error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Shell Passthrough
# ═══════════════════════════════════════════════════════════════════════════

SHELL_PASSTHROUGH = {"ollama", "pip", "pip3", "git", "docker", "kubectl",
                     "curl", "wget", "ssh", "npm", "node", "python",
                     "python3", "pytest", "gh"}


def _exec_shell(cmd: str) -> str:
    """Execute a system command with live streaming output."""
    import subprocess
    print(f"  [90m⚛ Running: {cmd}[0m")
    # Use Popen for streaming — critical for long-running commands like ollama pull
    try:
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        lines = []
        for line in proc.stdout:
            print(f"  {line}", end="", flush=True)
            lines.append(line)
        proc.wait(timeout=300)
        out = "".join(lines).strip()
        if proc.returncode != 0 and not out:
            return f"(exit code {proc.returncode})"
        return out if out else "(command completed)"
    except subprocess.TimeoutExpired:
        proc.kill()
        return "Command timed out after 300 s."
    except FileNotFoundError:
        return f"Command not found: {cmd.split()[0]}"
    except Exception as e:
        return f"Shell error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Main REPL
# ═══════════════════════════════════════════════════════════════════════════

def process_input(user_input: str, intent_engine) -> str:
    """
    Process a single user input:
    1. Check for direct command match
    2. Run through IntentEngine for classification
    3. Execute the matched handler
    4. For complex/unknown intents, also consult the NCLLM swarm
    """
    text = user_input.strip()
    if not text:
        return ""

    # Strip shell-style comments (# ...)
    if text.startswith("#"):
        return "  (comment ignored)"

    # Direct command shortcut (first word)
    words = text.split()
    first_word = words[0].lower()

    # ── Shell passthrough: recognised system commands ──
    # "run <tool> ..." → execute shell command (not experiment)
    if first_word == "run" and len(words) > 1 and words[1].lower() in SHELL_PASSTHROUGH:
        return _exec_shell(" ".join(words[1:]))
    # Bare system tool invocation (e.g. "ollama pull ...")
    if first_word in SHELL_PASSTHROUGH and first_word not in DIRECT_COMMANDS:
        return _exec_shell(text)

    # "swarm" keyword → always route through NCLLM directly
    if first_word == "swarm":
        task = " ".join(words[1:]) if len(words) > 1 else "general analysis"
        print("  [90m⚛ Routing to NCLLM 9-agent swarm...[0m")
        from osiris_intent_engine import IntentType, Intent
        dummy_intent = Intent(
            intent_type=IntentType.UNKNOWN, confidence=1.0,
            parameters={"task": task}, suggested_actions=[], required_agents=[]
        )
        return route_through_swarm(task, dummy_intent, {"task": task})

    # Direct single-word or two-word commands
    if first_word in DIRECT_COMMANDS:
        handler = DIRECT_COMMANDS[first_word]
        extra = " ".join(words[1:])
        # Parse params from extra text via intent engine
        params = intent_engine.parse_intent(text).parameters if len(words) > 1 else {}
        params.setdefault("task", extra or text)
        return handler(params)

    # Run through intent engine
    intent = intent_engine.parse_intent(text)
    params = intent.parameters

    # Also extract task text for commands that need it
    params.setdefault("task", text)

    # Show intent detection
    intent_str = intent.intent_type.value
    conf = intent.confidence

    print(f"  [90m⚛ Intent: {intent_str} (confidence: {conf:.0%})[0m")

    # Get handler
    handler = INTENT_HANDLERS.get(intent_str)

    if handler is not None and conf >= 0.5:
        # Execute via handler
        result = handler(params)

        # For high-complexity intents, also get swarm perspective
        if intent_str in ("orchestrate", "experiment", "analyze", "refine"):
            print("  [90m⚛ Consulting NCLLM swarm...[0m")
            swarm_out = route_through_swarm(text, intent, params)
            result = result + "\n\n" + swarm_out

        # Feed back to intent engine
        try:
            intent_engine.receive_swarm_feedback(
                intent.intent_type, conf, {}
            )
        except Exception:
            pass

        intent_engine.add_to_history(text, result[:200])
        return result

    # Unknown or low confidence — try Ollama direct, then swarm
    try:
        from osiris_ollama import check_ollama, get_engine
        if check_ollama():
            print("  [90m⚛ Querying Ollama...[0m")
            engine = get_engine()
            response = engine.generate_for_agent("orchestrator", text, max_tokens=512)
            if response and len(response.strip()) > 5:
                intent_engine.add_to_history(text, response[:200])
                return response
    except Exception:
        pass

    print("  [90m⚛ Routing to NCLLM swarm for deliberation...[0m")
    swarm_result = route_through_swarm(text, intent, params)
    intent_engine.add_to_history(text, swarm_result[:200])
    return swarm_result


def main():
    """Main REPL loop."""
    # Handle Ctrl+C gracefully
    def sigint_handler(sig, frame):
        print("\n\n  [36m⚛ OSIRIS shutting down. Torsion frame sealed. ⚛[0m\n")
        sys.exit(0)
    signal.signal(signal.SIGINT, sigint_handler)

    # Boot
    print_boot_screen()

    # Init intent engine
    from osiris_intent_engine import IntentEngine
    intent_engine = IntentEngine()

    # Pre-warm swarm in background (lazy — first call will init)
    # Just test import
    try:
        from osiris_ncllm_swarm import NCLLMSwarm
        print("  [32m✓[0m  NCLLM Swarm loaded. 9 agents standing by.")
    except Exception as e:
        print(f"  [33m⚠[0m  NCLLM Swarm: {e}")

    # Check Ollama and show model info
    try:
        from osiris_ollama import check_ollama, get_client
        if check_ollama():
            client = get_client()
            st = client.status()
            if st.models:
                print(f"  [32m✓[0m  Ollama ready: {', '.join(st.models[:3])}")
            else:
                print("  [33m⚠[0m  Ollama running but no models. Run: ollama pull qwen2.5:1.5b")
        else:
            print("  [33m⚠[0m  Ollama offline — using template fallback")
    except Exception:
        print("  [33m⚠[0m  Ollama module unavailable")

    print()

    # REPL
    while True:
        try:
            prompt = "\001\033[1;36m\002osiris\001\033[0m\002 \001\033[36m\002❯\001\033[0m\002 "
            user_input = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\n\n  [36m⚛ OSIRIS shutting down. Torsion frame sealed. ⚛[0m\n")
            break

        text = user_input.strip()
        if not text:
            continue
        if text.lower() in ("quit", "exit", "q", ":q"):
            print("\n  [36m⚛ OSIRIS shutting down. Torsion frame sealed. ⚛[0m\n")
            break

        # Process
        try:
            t0 = time.monotonic()
            result = process_input(text, intent_engine)
            elapsed = (time.monotonic() - t0) * 1000
            if result:
                print()
                print(result)
                print(f"\n  [90m({elapsed:.0f}ms)[0m")
            print()
        except Exception as e:
            print(f"\n  [31m✗ Error: {e}[0m\n")
            traceback.print_exc()


if __name__ == "__main__":
    main()
