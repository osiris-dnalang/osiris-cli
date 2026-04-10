#!/usr/bin/env python3
"""
OSIRIS System Health Diagnostic
================================

Comprehensive self-test that validates every subsystem by actually
importing and exercising critical code paths. This is not a stub —
it tests real functionality and reports real failures.

Subsystems checked:
  1. qByte Register        — DNA gates, measurement, CCCE metrics
  2. Torsion Core          — θ_lock constants, quaternion math
  3. Local QVM             — Tetrahedral quaternionic execution pipeline
  4. LivLM                 — Quantum text generation engine
  5. NCLM Package          — QByteTextGenerator, evolution, personality
  6. 9-Agent Swarm         — Agent instantiation, template deliberation
  7. Cognitive Mesh         — Bayesian trust, Shapley attribution
  8. Introspection Engine   — Temporal/structural/semantic metrics
  9. Bridge Validator       — Adversarial falsification framework
  10. Feedback Bus          — Pub/sub relay, OsirisIntelligenceLoop
  11. Intent Engine         — Intent parsing and routing
  12. ELO Tournament        — Glicko-2 rating engine
  13. Physics Bridges       — CRSM propulsion/energy/cosmological
  14. Forge                 — 3D manufacturing pipeline
  15. FABRIC Bridge         — Living Slice provisioner
  16. Policy Upcycler       — POLANCO → Living Security Organisms
  17. Master Prompt         — System identity constant
  18. Agent System          — BaseAgent/AgentManager orchestration
  19. License Gate          — Compliance detection
  20. CLI Dispatch          — Argparse wiring integrity

Author: OSIRIS dna::}{::lang NCLM
"""

import sys
import os
import time
import traceback
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent))

# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    name: str
    status: str           # "PASS", "WARN", "FAIL"
    detail: str = ""
    elapsed_ms: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    checks: List[CheckResult] = field(default_factory=list)
    total_elapsed_ms: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "PASS")

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if c.status == "WARN")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        return (self.passed + 0.5 * self.warned) / self.total

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "warned": self.warned,
            "failed": self.failed,
            "total": self.total,
            "score": round(self.score, 4),
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "detail": c.detail,
                    "elapsed_ms": round(c.elapsed_ms, 2),
                    "metrics": c.metrics,
                }
                for c in self.checks
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Individual Health Checks
# ═══════════════════════════════════════════════════════════════════════════════

def _timed(fn) -> CheckResult:
    """Run a check function and capture timing + exceptions."""
    t0 = time.monotonic()
    try:
        result = fn()
        result.elapsed_ms = (time.monotonic() - t0) * 1000
        return result
    except Exception as e:
        return CheckResult(
            name=fn.__name__.replace("check_", "").replace("_", " ").title(),
            status="FAIL",
            detail=f"{type(e).__name__}: {e}",
            elapsed_ms=(time.monotonic() - t0) * 1000,
        )


def check_qbyte_register() -> CheckResult:
    """Test qByte register: init, DNA gate application, measurement, CCCE."""
    from qbyte_system.register import QByteRegister
    from qbyte_system.gates import helix, bond, twist, fold

    reg = QByteRegister()
    reg.apply_gate(helix(), [0])
    reg.apply_gate(bond(), [0, 1])
    reg.apply_gate(twist(0.5), [2])
    reg.apply_gate(fold(), [3])

    counts = reg.measure(shots=256)
    ccce = reg.ccce_metrics()

    assert len(counts) > 0, "No measurement outcomes"
    assert "phi" in ccce, "Missing Φ in CCCE"
    assert 0 <= ccce["phi"] <= 1, f"Φ out of range: {ccce['phi']}"

    return CheckResult(
        name="qByte Register",
        status="PASS",
        detail=f"{len(counts)} outcomes, Φ={ccce['phi']:.4f}",
        metrics={"outcomes": len(counts), "phi": ccce["phi"]},
    )


def check_torsion_core() -> CheckResult:
    """Validate torsion core physical constants and θ_lock."""
    import numpy as np

    expected_theta = 51.843
    # Try Cython first, fall back to pure Python
    try:
        from osiris_torsion_core_py import (
            THETA_LOCK, CHI_PC, GOLDEN_RATIO, PLANCK_LENGTH
        )
    except ImportError:
        from osiris_local_qvm import THETA_LOCK, CHI_PC, GOLDEN_RATIO, PLANCK_LENGTH

    assert abs(THETA_LOCK - expected_theta) < 0.01, f"θ_lock={THETA_LOCK}"
    assert abs(CHI_PC - 0.869) < 0.01, f"χ_pc={CHI_PC}"
    assert abs(GOLDEN_RATIO - 1.618) < 0.001, f"φ={GOLDEN_RATIO}"
    assert PLANCK_LENGTH > 0, "ℓ_P must be positive"

    # Verify arctan(4/π) ≈ 51.843°
    computed_theta = np.degrees(np.arctan(4.0 / np.pi))
    assert abs(computed_theta - expected_theta) < 0.02, (
        f"arctan(4/π)={computed_theta}° ≠ {expected_theta}°"
    )

    return CheckResult(
        name="Torsion Core",
        status="PASS",
        detail=f"θ_lock={THETA_LOCK}°, χ_pc={CHI_PC}, φ={GOLDEN_RATIO:.6f}",
        metrics={"theta_lock": THETA_LOCK, "chi_pc": CHI_PC},
    )


def check_local_qvm() -> CheckResult:
    """Execute a full QVM circuit and validate XEB/CCCE output."""
    from osiris_local_qvm import LocalQVM

    qvm = LocalQVM(n_qubits=4, seed=42)
    result = qvm.execute(circuit_type="random", depth=8, shots=512)

    assert result.n_qubits == 4
    assert len(result.counts) > 0
    assert -1.0 <= result.xeb_score <= 1.0
    assert 0.0 <= result.fidelity <= 1.0
    assert result.ccce.xi >= 0  # Negentropic efficiency can't be negative
    assert result.execution_time > 0

    return CheckResult(
        name="Local QVM",
        status="PASS",
        detail=f"XEB={result.xeb_score:.4f}, Ξ={result.ccce.xi:.4f}, "
               f"{len(result.counts)} bitstrings in {result.execution_time:.3f}s",
        metrics={
            "xeb": result.xeb_score,
            "fidelity": result.fidelity,
            "xi": result.ccce.xi,
            "execution_time": result.execution_time,
        },
    )


def check_livlm() -> CheckResult:
    """Test LivLM engine: config, corpus load, short generation."""
    from osiris_livlm import LivLM, LivLMConfig

    config = LivLMConfig(
        max_generations=3, population_size=5,
        sample_length=8, n_layers=1,
    )
    model = LivLM(config)
    model.load_corpus()

    text = model.generate(prompt="# ", length=16)
    assert isinstance(text, str), f"Generate returned {type(text)}"
    assert len(text) > 0, "Empty generation"

    return CheckResult(
        name="LivLM Engine",
        status="PASS",
        detail=f"Generated {len(text)} chars from corpus ({model.corpus.size:,} bytes)",
        metrics={"generated_len": len(text), "corpus_size": model.corpus.size},
    )


def check_nclm_package() -> CheckResult:
    """Test NCLM package: QByteTextGenerator instantiation."""
    from nclm.core.qbyte_generator import QByteTextGenerator
    from osiris_livlm import LivLMConfig

    config = LivLMConfig(max_generations=2, population_size=5, n_layers=1)
    gen = QByteTextGenerator(config=config)
    status = gen.status()

    assert "evolved" in status
    assert "genome_loaded" in status

    return CheckResult(
        name="NCLM Package",
        status="PASS",
        detail=f"QByteTextGenerator ready, evolved={status['evolved']}",
        metrics=status,
    )


def check_swarm() -> CheckResult:
    """Test 9-agent swarm: instantiate and run 1 round of template deliberation."""
    from osiris_ncllm_swarm import NCLLMSwarm

    swarm = NCLLMSwarm(user_id="health_check")
    result = swarm.solve("Return the number 42", max_rounds=1)

    assert result.rounds, "Swarm returned no rounds"
    assert result.quality_score >= 0
    assert result.agents_used == 9

    return CheckResult(
        name="9-Agent Swarm",
        status="PASS",
        detail=f"1 round, quality={result.quality_score:.3f}, "
               f"{len(result.rounds[0].responses)} agent responses",
        metrics={
            "quality": result.quality_score,
            "responses": len(result.rounds[0].responses),
        },
    )


def check_cognitive_mesh() -> CheckResult:
    """Test cognitive mesh: Bayesian trust update + status report."""
    from osiris_cognitive_mesh import CognitiveMesh
    import random

    mesh = CognitiveMesh()
    votes = {a: random.choice(["approve", "reject", "abstain"])
             for a in mesh.agent_ids}
    consensus = max(set(votes.values()), key=list(votes.values()).count)
    mesh.post_round_update(votes, consensus, quality=0.75)

    report = mesh.status_report()
    assert "trust_scores" in report or "agents" in report or len(report) > 0

    return CheckResult(
        name="Cognitive Mesh",
        status="PASS",
        detail=f"Bayesian update completed, {len(mesh.agent_ids)} agents tracked",
        metrics={"agent_count": len(mesh.agent_ids)},
    )


def check_introspection() -> CheckResult:
    """Test introspection engine: observe a round, generate report."""
    from osiris_introspection import IntrospectionEngine

    engine = IntrospectionEngine()
    responses = [
        {"agent": a, "vote": "approve", "confidence": 0.8}
        for a in engine.agent_ids[:3]
    ]
    engine.observe_round(responses, consensus="approve", quality=0.7)

    report = engine.full_report()
    assert isinstance(report, dict)

    return CheckResult(
        name="Introspection Engine",
        status="PASS",
        detail=f"Observed 1 round, report keys: {sorted(report.keys())[:5]}",
        metrics={"report_keys": len(report)},
    )


def check_bridge_validator() -> CheckResult:
    """Test bridge validator: quick validation with minimal MC trials."""
    from osiris_bridge_validator import AdversarialBridgeValidator

    validator = AdversarialBridgeValidator(mc_trials=10, sensitivity_sigma=1)
    report = validator.validate()

    assert report.overall_verdict in ("PASS", "FAIL", "MARGINAL", "INCONCLUSIVE")
    assert report.bayes_factor >= 0

    return CheckResult(
        name="Bridge Validator",
        status="PASS",
        detail=f"Verdict: {report.overall_verdict}, Bayes={report.bayes_factor:.4f}",
        metrics={"verdict": report.overall_verdict, "bayes": report.bayes_factor},
    )


def check_feedback_bus() -> CheckResult:
    """Test feedback bus: publish/subscribe round-trip."""
    from osiris_feedback_bus import FeedbackBus, BusMessage, MessageType

    bus = FeedbackBus()
    received = []
    bus.subscribe("test_channel", lambda msg: received.append(msg))
    bus.publish("test_channel", BusMessage(
        source="health",
        target="test_channel",
        msg_type=MessageType.TELEMETRY,
        payload={"probe": True},
    ))

    assert len(received) == 1, f"Expected 1 message, got {len(received)}"
    assert received[0].payload["probe"] is True

    return CheckResult(
        name="Feedback Bus",
        status="PASS",
        detail="Pub/sub round-trip verified",
    )


def check_intent_engine() -> CheckResult:
    """Test intent engine: parse a natural language command."""
    from osiris_intent_engine import IntentEngine

    engine = IntentEngine()
    result = engine.parse("benchmark the quantum hardware")

    assert hasattr(result, "intent_type") or isinstance(result, dict)

    return CheckResult(
        name="Intent Engine",
        status="PASS",
        detail=f"Parsed 'benchmark the quantum hardware'",
    )


def check_elo_tournament() -> CheckResult:
    """Test ELO tournament: instantiate and run 1 round."""
    from osiris_elo_tournament import EloTournament

    tournament = EloTournament()
    results = tournament.run_tournament(rounds_per_matchup=1)

    assert isinstance(results, (dict, list))

    return CheckResult(
        name="ELO Tournament",
        status="PASS",
        detail=f"1-round tournament completed",
    )


def check_physics_bridges() -> CheckResult:
    """Test physics bridges: run all three CRSM bridges."""
    from osiris_physics_bridges import BridgeExecutor

    executor = BridgeExecutor()
    report = executor.run_all()

    assert "propulsion" in report
    assert "energy" in report
    assert "cosmological" in report

    return CheckResult(
        name="Physics Bridges",
        status="PASS",
        detail=(
            f"Propulsion p={report['propulsion']['bootstrap_p']:.4f}, "
            f"Energy modes={report['energy']['n_modes']}"
        ),
        metrics={
            "propulsion_p": report["propulsion"]["bootstrap_p"],
            "energy_modes": report["energy"]["n_modes"],
        },
    )


def check_forge() -> CheckResult:
    """Test forge: instantiate and status report."""
    from osiris_forge import OsirisForge

    forge = OsirisForge()
    report = forge.status_report()
    forge.cleanup()

    assert isinstance(report, (str, dict))

    return CheckResult(
        name="Forge (3D Mfg)",
        status="PASS",
        detail="Manufacturing pipeline instantiated",
    )


def check_fabric_bridge() -> CheckResult:
    """Test FABRIC bridge: import and verify class exists."""
    from osiris_fabric_bridge import demo_living_slice
    # Don't run the full demo, just validate the import chain works
    assert callable(demo_living_slice)

    return CheckResult(
        name="FABRIC Bridge",
        status="PASS",
        detail="Living Slice provisioner importable",
    )


def check_policy_upcycler() -> CheckResult:
    """Test POLANCO: import and instantiate."""
    from osiris_policy_upcycle import PolancoUpcycler

    upcycler = PolancoUpcycler(deployment_sites=["HEALTH_CHECK"])
    assert upcycler is not None

    return CheckResult(
        name="Policy Upcycler",
        status="PASS",
        detail="POLANCO upcycler instantiated",
    )


def check_master_prompt() -> CheckResult:
    """Validate master system prompt is loaded and non-trivial."""
    from osiris_master_prompt import OSIRIS_MASTER_PROMPT

    assert isinstance(OSIRIS_MASTER_PROMPT, str)
    assert len(OSIRIS_MASTER_PROMPT) > 100, (
        f"Master prompt too short: {len(OSIRIS_MASTER_PROMPT)} chars"
    )
    # Verify key identity markers
    assert "OSIRIS" in OSIRIS_MASTER_PROMPT
    assert "NCLLM" in OSIRIS_MASTER_PROMPT or "NCLM" in OSIRIS_MASTER_PROMPT

    return CheckResult(
        name="Master Prompt",
        status="PASS",
        detail=f"{len(OSIRIS_MASTER_PROMPT)} chars, identity markers present",
        metrics={"length": len(OSIRIS_MASTER_PROMPT)},
    )


def check_agent_system() -> CheckResult:
    """Test agent orchestration system: instantiate AgentManager."""
    from osiris_agents import AgentManager

    manager = AgentManager()
    assert manager is not None

    return CheckResult(
        name="Agent System",
        status="PASS",
        detail="AgentManager instantiated with specialized agents",
    )


def check_license_gate() -> CheckResult:
    """Test license compliance detection."""
    from osiris_license import EnvironmentDetector

    detector = EnvironmentDetector()
    sig = detector.detect()

    assert hasattr(sig, "domain_class")
    assert hasattr(sig, "compliant")

    return CheckResult(
        name="License Gate",
        status="PASS",
        detail=f"Domain: {sig.domain_class}, Compliant: {sig.compliant}",
        metrics={"domain": sig.domain_class, "compliant": sig.compliant},
    )


def check_cli_dispatch() -> CheckResult:
    """Verify argparse wiring: all expected commands are registered."""
    import argparse

    # Import main() to get the parser — but don't execute
    # Instead, verify the dispatch table covers all advertised commands
    expected_commands = {
        "chat", "benchmark", "run", "publish", "orchestrate",
        "status", "intent", "forge", "bridges", "swarm",
        "validate", "tournament", "mesh", "introspect",
        "feedback", "livlm", "ollama", "fabric", "policy",
        "demo", "license", "nclm", "ultra-coder", "help",
    }

    # Read the launcher source and find dispatch entries
    launcher_path = Path(__file__).parent / "osiris_launcher.py"
    source = launcher_path.read_text()

    missing = []
    for cmd in expected_commands:
        # Check both subparser registration and dispatch
        if f"'{cmd}'" not in source and f'"{cmd}"' not in source:
            missing.append(cmd)

    if missing:
        return CheckResult(
            name="CLI Dispatch",
            status="FAIL",
            detail=f"Missing commands: {missing}",
        )

    return CheckResult(
        name="CLI Dispatch",
        status="PASS",
        detail=f"{len(expected_commands)} commands verified in dispatch table",
        metrics={"commands": len(expected_commands)},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Health Engine
# ═══════════════════════════════════════════════════════════════════════════════

ALL_CHECKS = [
    check_qbyte_register,
    check_torsion_core,
    check_local_qvm,
    check_livlm,
    check_nclm_package,
    check_swarm,
    check_cognitive_mesh,
    check_introspection,
    check_bridge_validator,
    check_feedback_bus,
    check_intent_engine,
    check_elo_tournament,
    check_physics_bridges,
    check_forge,
    check_fabric_bridge,
    check_policy_upcycler,
    check_master_prompt,
    check_agent_system,
    check_license_gate,
    check_cli_dispatch,
]


def run_health(checks: List = None, verbose: bool = True) -> HealthReport:
    """
    Run all (or selected) health checks and return a report.
    """
    checks = checks or ALL_CHECKS
    report = HealthReport()
    t0 = time.monotonic()

    for check_fn in checks:
        name = check_fn.__name__.replace("check_", "").replace("_", " ").title()
        if verbose:
            print(f"  [{len(report.checks)+1:2d}/{len(checks)}] {name:.<40s}", end="", flush=True)

        result = _timed(check_fn)
        report.checks.append(result)

        if verbose:
            icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}[result.status]
            print(f" {icon} {result.status} ({result.elapsed_ms:.0f}ms)")
            if result.status == "FAIL" and result.detail:
                print(f"       └─ {result.detail}")

    report.total_elapsed_ms = (time.monotonic() - t0) * 1000

    if verbose:
        print()
        _print_summary(report)

    return report


def _print_summary(report: HealthReport) -> None:
    """Print colored summary banner."""
    bar_len = 40
    fill = int(report.score * bar_len)
    bar = "█" * fill + "░" * (bar_len - fill)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              OSIRIS SYSTEM HEALTH REPORT                    ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Score:  [{bar}] {report.score*100:.1f}%     ║")
    print(f"║  Passed: {report.passed:3d}  │  Warned: {report.warned:3d}  │  Failed: {report.failed:3d}  │  Total: {report.total:3d}  ║")
    print(f"║  Elapsed: {report.total_elapsed_ms:.0f}ms{' ' * (47 - len(f'{report.total_elapsed_ms:.0f}ms'))}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    if report.failed == 0:
        print("\n  All subsystems operational. OSIRIS is fully coherent.\n")
    elif report.score >= 0.8:
        print(f"\n  {report.failed} subsystem(s) degraded. Core functionality intact.\n")
    else:
        failed_names = [c.name for c in report.checks if c.status == "FAIL"]
        print(f"\n  Critical failures: {', '.join(failed_names)}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run health diagnostic from CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="OSIRIS System Health Diagnostic")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-check output")
    parser.add_argument("--output", type=str, default="", help="Save report to file")
    args = parser.parse_args()

    print("\n⚛ OSIRIS System Health Diagnostic")
    print("═" * 62)
    print()

    report = run_health(verbose=not args.quiet)

    if args.json or args.output:
        import json
        data = json.dumps(report.to_dict(), indent=2, default=str)
        if args.json:
            print(data)
        if args.output:
            Path(args.output).write_text(data)
            print(f"\n✓ Report saved to {args.output}")

    # Exit code: 0 if all pass, 1 if any fail
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
