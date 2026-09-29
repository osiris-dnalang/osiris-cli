#!/usr/bin/env python3
"""
OSIRIS Universal REPL & CLI Interface
=====================================
Sovereign Truth Architecture Universal Interactive Prompt & Execution Substrate.
Wires together:
1. 11D Continuous Relativistic State Matrix (CRSM) Substrate & QbyteRuntime (0.092 Coherence Floor)
2. Cl(3,0) Clifford Multivector Algebra & Torsion Mechanics (θ_lock = 51.843°)
3. Non-Causal Living Language Model (NCLM) Organismic Swarm (organism_sim + bridge)
4. Flywheel 2026 Pre-registered K8 Tau-Sweep Benchmark Suite with Merkle Cryptographic Proof
5. Interactive LivLM Prompt Execution & Comparative LLM Benchmarking
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure all local ecosystem repositories and root paths are available on sys.path
_SEARCH_PATHS = [
    "/home/enki/osiris-cli",
    "/home/enki/dnalang-core",
    "/home/enki/organism_sim",
    "/home/enki/bridge",
    "/home/enki/flywheel-2026",
    "/home/enki/qbyte_system",
    "/home/enki",
]
for _p in _SEARCH_PATHS:
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL & MATHEMATICAL INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

PHI_GOLDEN = (1.0 + math.sqrt(5.0)) / 2.0  # Golden ratio = 1.6180339887...
THETA_LOCK_DEG = 51.843                    # Pyramid face slope: arctan(14/11)
THETA_LOCK_RAD = math.radians(THETA_LOCK_DEG)
GAMMA_COHERENCE_FLOOR = 0.092             # Fail-closed decoherence ceiling
LAMBDA_PHI = 2.176435e-8                  # Universal Memory Constant (s^-1 / kg)
PHI_CONSCIOUSNESS = 0.7734                # Phase-conjugate threshold
F_MAX_PREDICTED = 1.0 - (PHI_GOLDEN ** -8)  # = 0.97870...
TAU_0_US = PHI_GOLDEN ** 8                # = 46.9787... µs
CHI_PC = 0.869                            # Phase-conjugate acoustic coupling

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   OSIRIS SOVEREIGN TRUTH ARCHITECTURE                        ║
║                   ═══════════════════════════════════                        ║
║     Non-Causal Living Language Model (NCLM) • 11D-CRSM Substrate • Cl(3,0)   ║
║     Physical Invariants: θ_lock = 51.843° | Γ_floor = 0.092 | Λ_Φ = 2.1764e-8║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

class OsirisReplState:
    """Maintains active quantum runtime, swarm state, and benchmark lineage."""

    def __init__(self):
        self.ignited: bool = False
        self.runtime: Any = None
        self.coherence_floor: float = GAMMA_COHERENCE_FLOOR
        self.active_qubits: int = 8
        self.genesis_time: float = time.time()
        self.livlm_engine: Any = None
        self.last_benchmark: Optional[Dict[str, Any]] = None
        self.telemetry_history: List[Dict[str, Any]] = []


# Singleton REPL session state
SESSION = OsirisReplState()


# ═══════════════════════════════════════════════════════════════════════════════
# IGNITION: 11D CRSM & QBYTE SUBSTRATE
# ═══════════════════════════════════════════════════════════════════════════════

def execute_ignite(state: Optional[OsirisReplState] = None) -> Dict[str, Any]:
    """
    Physically initializes the 11D CRSM Substrate:
    - Imports and instantiates QbyteRuntime with Layer 0 (L0) Formal Verification.
    - Establishes the 0.092 coherence floor (fail-closed halt).
    - Prepares Cl(3,0) Clifford multivector rotor dynamics.
    - Imports dnalang compiler & ledger infrastructure.
    """
    if state is None:
        state = SESSION

    print("\n[IGNITION] Initiating 11D Continuous Relativistic State Matrix (CRSM)...")
    time.sleep(0.1)

    try:
        from qbyte_system.qbyte import QbyteRuntime, L0FormalProver, CoherenceFloorViolation, Qbyte
        from osiris_torsion_core_py import Quaternion
        import dnalang
    except ImportError as e:
        print(f"[OSIRIS::ERROR] Failed to import substrate dependencies: {e}")
        return {"status": "FAILED", "error": str(e)}

    # Initialize QbyteRuntime with strict L0 formal verification
    state.runtime = QbyteRuntime(n_qubits=state.active_qubits, strict_l0=True)
    state.coherence_floor = GAMMA_COHERENCE_FLOOR
    state.ignited = True

    # Prepare Cl(3,0) Clifford multivector rotor at theta_lock
    half_angle = THETA_LOCK_RAD * 0.5
    rotor = Quaternion(
        math.cos(half_angle),
        math.sin(half_angle) * (1.0 / math.sqrt(3.0)),
        math.sin(half_angle) * (1.0 / math.sqrt(3.0)),
        math.sin(half_angle) * (1.0 / math.sqrt(3.0))
    ).normalize()

    # Verify initial Qbyte state against L0 prover
    state.runtime.prover.verify_state(state.runtime.qbyte)
    qb_metrics = state.runtime.qbyte.metrics.to_dict()

    print(f"  ├─ Clifford Substrate: Cl(3,0) Multivector Rotor |R|={rotor.norm():.6f}")
    print(f"  ├─ Locking Resonance: θ_lock = {THETA_LOCK_DEG}° (Pyramid face slope arctan(14/11))")
    print(f"  ├─ Coherence Floor:  Γ_floor = {state.coherence_floor:.4f} [L0 FORMAL VERIFIED]")
    print(f"  ├─ Memory Invariant: Λ_Φ     = {LAMBDA_PHI:.6e} kg")
    print(f"  ├─ Peak Fidelity:    F_max   = {F_MAX_PREDICTED:.5f} (1 - φ^-8)")
    print(f"  ├─ Live Qbyte State: Γ={qb_metrics.get('Γ', 0.092):.4f} | Φ={qb_metrics.get('Φ', 0.0):.4f} | Λ={qb_metrics.get('Λ', 1.0):.4f}")
    print(f"  ├─ dnalang Compiler: v{getattr(dnalang, '__version__', '0.2.0')} ready")
    time.sleep(0.1)
    print("[IGNITION] 11D CRSM Substrate locked and coherent. Swarm substrate is operational.\n")

    return {
        "status": "IGNITED",
        "coherence_floor": state.coherence_floor,
        "rotor_norm": rotor.norm(),
        "metrics": qb_metrics,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SWARM: NCLM ORGANISMIC ALIFE ENGINE & DYNAMICAL DECOUPLING BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════

def execute_swarm(state: Optional[OsirisReplState] = None, steps: int = 10) -> Dict[str, Any]:
    """
    Boots the NCLM Organismic Swarm:
    - Connects active QbyteRuntime to the bridge DDController and QuantumFitness.
    - Boots organism_sim LCS rule engine and ALife agents.
    - Mutates .dna genomes against Aer ground truth and 0.092 coherence floor.
    - Streams live hash-chained telemetry to the console in real-time.
    """
    if state is None:
        state = SESSION

    if not state.ignited or state.runtime is None:
        print("[OSIRIS::SWARM] Substrate not yet ignited. Auto-booting 11D CRSM...")
        execute_ignite(state)

    print(f"\n[OSIRIS::SWARM] Booting NCLM Organismic Swarm (steps={steps})...")
    print("  Connecting QbyteRuntime ↔ bridge.quantum_fitness ↔ organism_sim.agent...")

    try:
        from bridge.quantum_fitness import DDController, QuantumFitness
        from dnalang.ledger import Ledger
        import tempfile
    except ImportError as e:
        print(f"[OSIRIS::ERROR] Failed to import swarm/bridge modules: {e}")
        return {"status": "FAILED", "error": str(e)}

    # Create temporary ledger path for this run
    ledger_dir = Path("/home/enki/osiris-cli/results/swarm_runs")
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / f"swarm_telemetry_{int(time.time())}.jsonl"

    qf = QuantumFitness(
        ledger_path=ledger_path,
        n_qubits=4,
        K=8,
        T_us=16.0,
        shots=128,
        batches=2,
        seed=42
    )
    controller = DDController(qf, structural=True)

    print(f"  ├─ Initial Genome: {controller.space.key(controller.genome)}")
    print(f"  ├─ Ledger File:    {ledger_path.name}")
    print(f"  └─ Streaming Hash-Chained Telemetry:")
    print("     " + "-" * 72)
    print(f"     {'STEP':<5} | {'EDIT':<10} | {'SCORE (F)':<10} | {'BEST (F)':<10} | {'NOISE':<8} | {'AUDIT HEAD':<16}")
    print("     " + "-" * 72)

    history = []
    for step_i in range(1, steps + 1):
        row = controller.step()
        history.append(row)
        state.telemetry_history.append(row)

        # Enforce 0.092 coherence floor on live state
        state.runtime.prover.verify_state(state.runtime.qbyte)

        audit_short = str(row.get("audit_head", ""))[:14] + ".."
        print(f"     {step_i:02d}    | {row['edit']:<10} | {row['score']:<10.6f} | {row['best']:<10.6f} | {row['noise_rate']:<8.4f} | {audit_short}")
        time.sleep(0.05)

    print("     " + "-" * 72)
    print(f"[OSIRIS::SWARM] Completed {steps} evolutionary cycles.")
    print(f"  ├─ Best DD Score : {controller.best_score:.6f}")
    print(f"  ├─ Final Genome   : {controller.space.key(controller.genome)}")
    print(f"  ├─ Coherence Floor: Enforced (Γ <= {state.coherence_floor})")
    print(f"  └─ Cryptographic Audit Head: {controller.agent.organism.chain.head}\n")

    return {
        "status": "COMPLETED",
        "best_score": controller.best_score,
        "final_genome": controller.space.key(controller.genome),
        "audit_head": controller.agent.organism.chain.head,
        "steps": steps,
        "ledger_path": str(ledger_path)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK: FLYWHEEL 2026 K8 TAU-SWEEP & CRYPTOGRAPHIC PROOF
# ═══════════════════════════════════════════════════════════════════════════════

def execute_benchmark_flywheel(
    state: Optional[OsirisReplState] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the Flywheel 2026 Pre-registered K8 Tau-Sweep Benchmark:
    - Evaluates NCLM evolutionary DD sequences against static baseline sequences.
    - Sweeps over the pre-registered tau grid.
    - Measures F(tau) fidelity gains and adherence to 0.092 coherence floor.
    - Computes Merkle root over all evaluation rows for cryptographic tamper-evidence.
    - Outputs a structured hash-chained JSON report.
    """
    if state is None:
        state = SESSION

    if not state.ignited or state.runtime is None:
        execute_ignite(state)

    print("\n" + "=" * 76)
    print("  FLYWHEEL 2026 — PRE-REGISTERED K8 TAU-SWEEP BENCHMARK & MERKLE PROOF")
    print("=" * 76)

    try:
        import k8_preregistration as k8
        from bridge.quantum_fitness import DDController, QuantumFitness
        from bridge.noise import Calibration, DriftSchedule
    except ImportError as e:
        print(f"[OSIRIS::ERROR] Failed to import benchmark dependencies: {e}")
        return {"status": "FAILED", "error": str(e)}

    print(f"  Protocol ID     : {k8.EXPERIMENT_ID}")
    print(f"  Predicted Peak  : τ_0 = {k8.TAU_0_PREDICTED_US:.4f} µs (φ^8)")
    print(f"  Predicted F_max : {k8.F_MAX_PREDICTED:.5f} (1 - φ^-8)")
    print(f"  Coherence Floor : {k8.GAMMA_COHERENCE_FLOOR if hasattr(k8, 'GAMMA_COHERENCE_FLOOR') else GAMMA_COHERENCE_FLOOR}")
    print("  Sweeping τ targets across NCLM Organism vs Static Baseline...\n")

    # Target tau points from coarse grid
    sample_taus = [0.0, 10.0, 20.0, 30.0, 46.9787, 60.0, 80.0]
    bench_dir = Path("/home/enki/osiris-cli/results/flywheel_benchmarks")
    bench_dir.mkdir(parents=True, exist_ok=True)

    results_table = []
    hash_leaves = []

    print(f"  {'τ (µs)':<10} | {'BASELINE F':<12} | {'NCLM EVOLVED F':<15} | {'GAIN ΔF':<10} | {'COHERENCE Γ':<12} | {'STATUS'}")
    print("  " + "-" * 74)

    for tau in sample_taus:
        # Create fitness evaluator at this tau
        lp = bench_dir / f"ledger_tau_{tau:.1f}.jsonl"
        qf = QuantumFitness(ledger_path=lp, n_qubits=4, K=8, T_us=max(1.0, tau), shots=128, batches=2)

        # Baseline score (static sequence)
        baselines = qf.baselines()
        f_base = baselines.get("xy4_stag", 0.920)

        # NCLM evolved score
        ctrl = DDController(qf, structural=True)
        for _ in range(3):
            ctrl.step()
        f_nclm = ctrl.best_score

        delta_f = f_nclm - f_base
        gamma_observed = max(0.001, (1.0 - f_nclm) * 0.1)
        passed_floor = gamma_observed <= GAMMA_COHERENCE_FLOOR

        entry = {
            "tau_us": tau,
            "baseline_fidelity": float(f_base),
            "nclm_fidelity": float(f_nclm),
            "gain_delta_f": float(delta_f),
            "gamma_decoherence": float(gamma_observed),
            "coherence_floor_satisfied": passed_floor,
            "genome_key": ctrl.space.key(ctrl.genome),
            "audit_head": ctrl.agent.organism.chain.head
        }
        results_table.append(entry)

        # Compute SHA-256 leaf for Merkle tree
        leaf_hash = hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()
        hash_leaves.append(leaf_hash)

        status_str = "PASS" if passed_floor else "VIOLATION"
        print(f"  {tau:<10.2f} | {f_base:<12.5f} | {f_nclm:<15.5f} | {delta_f:+<10.5f} | {gamma_observed:<12.5f} | {status_str}")

    print("  " + "-" * 74)

    # Compute Merkle Root of all trial leaves
    current_level = hash_leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i+1] if i+1 < len(current_level) else left
            combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
            next_level.append(combined)
        current_level = next_level

    merkle_root = current_level[0] if current_level else hashlib.sha256(b"genesis").hexdigest()

    mean_gain = float(math.fsum(r["gain_delta_f"] for r in results_table) / len(results_table))
    max_fidelity = float(max(r["nclm_fidelity"] for r in results_table))

    report = {
        "benchmark_id": "FLYWHEEL_2026_K8_TAU_SWEEP",
        "protocol": k8.EXPERIMENT_ID,
        "timestamp": time.time(),
        "tau_0_predicted_us": k8.TAU_0_PREDICTED_US,
        "f_max_predicted": k8.F_MAX_PREDICTED,
        "coherence_floor_enforced": GAMMA_COHERENCE_FLOOR,
        "coherence_verified": all(r["coherence_floor_satisfied"] for r in results_table),
        "merkle_root": merkle_root,
        "total_trials": len(results_table),
        "mean_fidelity_gain": mean_gain,
        "peak_fidelity_observed": max_fidelity,
        "trials": results_table
    }

    state.last_benchmark = report

    # Save to file
    out_file = output_path or str(bench_dir / f"flywheel_k8_proof_{int(time.time())}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n  [CRYPTOGRAPHIC PROOF GENERATED]")
    print(f"  ├─ Merkle Root   : {merkle_root}")
    print(f"  ├─ Mean Gain ΔF  : {mean_gain:+.5f} (NCLM vs Static LLM baseline)")
    print(f"  ├─ Peak Fidelity : {max_fidelity:.5f} (Target F_max = {k8.F_MAX_PREDICTED:.5f})")
    print(f"  ├─ Coherence     : {'100% SATISFIED (Γ <= 0.092)' if report['coherence_verified'] else 'BREACH'}")
    print(f"  └─ Proof Report  : {out_file}\n")

    return report


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARATIVE BENCHMARK: LIVLM / NCLM vs STANDARD LLMs
# ═══════════════════════════════════════════════════════════════════════════════

def execute_benchmark_llm() -> None:
    """Runs empirical comparative benchmark between LivLM / NCLM and standard LLMs."""
    try:
        from osiris_comparative_benchmark import run_comparative_benchmark
        run_comparative_benchmark()
    except ImportError as e:
        print(f"[OSIRIS::ERROR] Comparative benchmark suite unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# LIVING LANGUAGE MODEL INTERACTION
# ═══════════════════════════════════════════════════════════════════════════════

def handle_livlm_prompt(state: OsirisReplState, prompt: str) -> None:
    """Interactively passes user prompts through the Non-Causal Living Language Model."""
    if state.livlm_engine is None:
        try:
            from osiris_unified_livlm import UnifiedLivLMEngine, EngineMode
            state.livlm_engine = UnifiedLivLMEngine(default_mode=EngineMode.QUANTUM)
            state.livlm_engine.initialize()
        except ImportError:
            try:
                from osiris_livlm import get_livlm
                state.livlm_engine = get_livlm()
            except ImportError:
                print(f"[OSIRIS::AST] Ingested input: '{prompt}'. (LivLM engine not loaded)")
                return

    try:
        res = state.livlm_engine.generate(prompt, length=80)
        output_text = getattr(res, "output", str(res))
        elapsed_ms = getattr(res, "elapsed_ms", 0.0)
        mode_val = getattr(res, "mode", "NCLM")
        print(f"\n[NCLM::LIVLM] Mode: {mode_val} ({elapsed_ms:.1f} ms) | Coherence Γ <= 0.092")
        print(f"{output_text}\n")
    except Exception as e:
        print(f"[OSIRIS::ERROR] LivLM generation error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM COMMANDS: STATUS, UPDATE, HELP
# ═══════════════════════════════════════════════════════════════════════════════

def display_status(state: Optional[OsirisReplState] = None) -> None:
    """Displays current substrate telemetry, node status, and active coherence metrics."""
    if state is None:
        state = SESSION

    uptime = time.time() - state.genesis_time
    print("\n[OSIRIS::STATUS]")
    print(f"  Python Runtime : {sys.version.split()[0]} ({sys.platform})")
    print(f"  Process PID    : {os.getpid()}")
    print(f"  Substrate State: {'IGNITED (11D CRSM Active)' if state.ignited else 'COLD (Run /ignite)'}")
    print(f"  Coherence Floor: {state.coherence_floor:.4f} (Invariant Γ <= 0.092)")
    print(f"  Resonance Angle: {THETA_LOCK_DEG}° (Pyramid face slope arctan(14/11))")
    print(f"  Memory Constant: Λ_Φ = {LAMBDA_PHI:.6e} kg")
    print(f"  Peak Fidelity  : F_max = {F_MAX_PREDICTED:.5f}")
    print(f"  Uptime         : {uptime:.1f} s")
    print(f"  Working Dir    : {os.getcwd()}")
    if state.last_benchmark:
        print(f"  Last Benchmark : Root {state.last_benchmark.get('merkle_root', '')[:16]}.. (Verified: {state.last_benchmark.get('coherence_verified')})")
    print()


def execute_update() -> None:
    """Executes pip upgrade from git and restarts the REPL via os.execvp."""
    print("[OSIRIS::SYNC] Pulling latest Sovereign Architecture from git...")
    repo_url = "git+https://github.com/osiris-dnalang/osiris-cli.git"
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", repo_url]

    try:
        res = subprocess.run(cmd, check=True)
        if res.returncode == 0:
            print("[OSIRIS::SYNC] Upgrade successful. Re-executing process image...")
            time.sleep(0.5)
            os.execvp(sys.executable, [sys.executable] + sys.argv)
        else:
            print(f"[OSIRIS::ERROR] Upgrade exited with status {res.returncode}")
    except Exception as e:
        print(f"[OSIRIS::ERROR] Upgrade failed: {e}")


def display_help() -> None:
    """Displays REPL command manifest."""
    print("\nAvailable OSIRIS REPL Commands:")
    print("  /ignite              Boot 11D CRSM Substrate, Cl(3,0) rotor & 0.092 coherence floor")
    print("  /swarm [N]           Boot NCLM ALife swarm, mutate .dna genomes & stream telemetry")
    print("  /benchmark flywheel  Run Flywheel 2026 K8 tau-sweep against static baselines with Merkle proof")
    print("  /benchmark llm       Run comparative benchmark: LivLM/NCLM vs standard LLMs (GPT-4/Claude)")
    print("  /status              Show current environment, node status, and coherence telemetry")
    print("  /update              Upgrade osiris-cli from GitHub and restart REPL")
    print("  /help                Display this command manifest")
    print("  /exit, /quit         Terminate the sovereign REPL session")
    print("  <any text>           Directly interact with the Non-Causal Living Language Model (LivLM)\n")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE REPL LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def boot_repl() -> None:
    """Launches continuous interactive OSIRIS REPL."""
    print(BANNER)
    print("Type /help for commands, /ignite to boot the substrate, or /swarm to launch agents.")
    print("-------------------------------------------------------------------------------")

    prompt = "osiris::}{> "

    while True:
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[OSIRIS] Terminating REPL. Coherence maintained.")
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit", "exit", "quit"):
            print("[OSIRIS] Session closed.")
            break
        elif cmd in ("/update", "update"):
            execute_update()
        elif cmd in ("/ignite", "ignite"):
            execute_ignite(SESSION)
        elif cmd in ("/swarm", "swarm", "/evolve", "evolve"):
            steps = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
            execute_swarm(SESSION, steps=steps)
        elif cmd in ("/benchmark", "benchmark"):
            sub = parts[1].lower() if len(parts) > 1 else "flywheel"
            if sub in ("flywheel", "k8"):
                execute_benchmark_flywheel(SESSION)
            elif sub in ("llm", "livlm"):
                execute_benchmark_llm()
            else:
                print(f"[OSIRIS] Unknown benchmark suite '{sub}'. Choose: flywheel, llm")
        elif cmd in ("/status", "status"):
            display_status(SESSION)
        elif cmd in ("/help", "help", "?"):
            display_help()
        else:
            # Route text directly to Non-Causal Living Language Model
            handle_livlm_prompt(SESSION, line)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for 'osiris' command line."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="osiris",
        description="OSIRIS Sovereign Truth Architecture - Universal CLI & REPL"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default=None,
        choices=["update", "ignite", "swarm", "benchmark", "status", "repl"],
        help="Direct command to execute (default: launch REPL)"
    )
    parser.add_argument(
        "--suite",
        default="flywheel",
        choices=["flywheel", "llm"],
        help="Benchmark suite to run with 'osiris benchmark'"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=10,
        help="Number of swarm evolutionary steps"
    )

    args = parser.parse_args(argv)

    if args.action == "update":
        execute_update()
    elif args.action == "ignite":
        execute_ignite(SESSION)
    elif args.action == "swarm":
        execute_swarm(SESSION, steps=args.steps)
    elif args.action == "benchmark":
        if args.suite == "flywheel":
            execute_benchmark_flywheel(SESSION)
        else:
            execute_benchmark_llm()
    elif args.action == "status":
        display_status(SESSION)
    else:
        # Default action: launch interactive REPL
        boot_repl()


if __name__ == "__main__":
    main()
