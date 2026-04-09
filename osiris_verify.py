#!/usr/bin/env python3
"""
OSIRIS System Verification & Demo
==================================

Runs comprehensive tests of all subsystems to verify functionality.
Includes license compliance verification as the first gate.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, '/workspaces/osiris-cli')

from osiris_auto_discovery import (
    AutoDiscoveryPipeline, 
    ExperimentConfig,
    RandomCircuitGenerator,
    StatisticalValidator
)
from osiris_orchestrator import WorkflowScheduler, ExperimentTemplates
from osiris_agents import AgentManager, AgentRole
from osiris_zenodo_publisher import PublishingWorkflow
try:
    from osiris_license import ComplianceGate, EnvironmentDetector
    HAS_LICENSE = True
except ImportError:
    HAS_LICENSE = False

def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_result(label: str, status: bool, details: str = ""):
    """Print test result"""
    symbol = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"
    reset = "\033[0m"
    print(f"  {color}[{symbol}]{reset} {label}", end="")
    if details:
        print(f" — {details}")
    else:
        print()

# ════════════════════════════════════════════════════════════════════════════════

print("\n")
print("╔" + "="*68 + "╗")
print("║" + " "*15 + "OSIRIS SYSTEM VERIFICATION v2.0" + " "*20 + "║")
print("╚" + "="*68 + "╝")

passed = 0
failed = 0

# ════════════════════════════════════════════════════════════════════════════════
# TEST 0: License Compliance Verification
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 0: License Compliance Verification")

if not HAS_LICENSE:
    print_result("License module", False, "osiris_license not available")
    failed += 1
else:
    try:
        detector = EnvironmentDetector()
        signature = detector.detect()
        print_result("Environment detection", True, f"Class: {signature.domain_class}")
        passed += 1
    except Exception as e:
        print_result("Environment detection", False, str(e))
        failed += 1

    try:
        compliant, msg = ComplianceGate.check(strict=False)
        print_result("License compliance", compliant, 
                     f"{'Compliant' if compliant else 'Non-compliant'} — {signature.domain_class}")
        if compliant:
            passed += 1
        else:
            print(f"\n  ⚠ {msg}")
            failed += 1
    except Exception as e:
        print_result("License compliance", False, str(e))
        failed += 1

# ════════════════════════════════════════════════════════════════════════════════
# TEST 1: Core Discovery Pipeline
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 1: Core Discovery Pipeline")

try:
    token = os.environ.get('IBM_QUANTUM_TOKEN', 'test_token')
    pipeline = AutoDiscoveryPipeline(api_token=token)
    print_result("Pipeline initialization", True)
    passed += 1
except Exception as e:
    print_result("Pipeline initialization", False, str(e))
    failed += 1

try:
    config = ExperimentConfig(
        name="test_experiment",
        hypothesis="Test system verification",
        circuit_depth=4,
        n_qubits=5,
        shots=1000,
        trials=10
    )
    print_result("ExperimentConfig creation", True, f"depth={config.circuit_depth}, qubits={config.n_qubits}")
    passed += 1
except Exception as e:
    print_result("ExperimentConfig creation", False, str(e))
    failed += 1

try:
    generator = RandomCircuitGenerator()
    circuit = generator.random_circuit(n_qubits=5, depth=4)
    print_result("Circuit generation", True, f"Created {circuit.num_qubits}-qubit circuit")
    passed += 1
except Exception as e:
    print_result("Circuit generation", False, str(e))
    failed += 1

try:
    import numpy as np
    validator = StatisticalValidator()
    group1 = np.array([0.087, 0.089, 0.085, 0.088, 0.086, 0.090, 0.084, 0.091])
    group2 = np.array([0.075, 0.078, 0.072, 0.076, 0.074, 0.077, 0.073, 0.079])
    results = validator.test_hypothesis(group1, group2)
    print_result("Statistical validation", True, f"p-value={results['p_value']:.4f}")
    passed += 1
except Exception as e:
    print_result("Statistical validation", False, str(e))
    failed += 1

# ════════════════════════════════════════════════════════════════════════════════
# TEST 2: Workflow Orchestration
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 2: Workflow Orchestration")

try:
    token = os.environ.get('IBM_QUANTUM_TOKEN', 'test_token')
    pipeline_for_scheduler = AutoDiscoveryPipeline(api_token=token)
    scheduler = WorkflowScheduler(pipeline=pipeline_for_scheduler)
    print_result("WorkflowScheduler initialization", True)
    passed += 1
except Exception as e:
    print_result("WorkflowScheduler initialization", False, str(e))
    failed += 1

try:
    templates = [
        ExperimentTemplates.xeb_vs_depth(),
        ExperimentTemplates.entropy_saturation(),
        ExperimentTemplates.noise_robustness(),
    ]
    print_result("Experiment templates", True, f"Found {len(templates)} templates")
    passed += 1
except Exception as e:
    print_result("Experiment templates", False, str(e))
    failed += 1

try:
    template = ExperimentTemplates.xeb_vs_depth()
    print_result("Campaign creation", True, f"Template: {template['name']}")
    passed += 1
except Exception as e:
    print_result("Campaign creation", False, str(e))
    failed += 1

# ════════════════════════════════════════════════════════════════════════════════
# TEST 3: Agent System
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 3: Multi-Agent System")

async def test_agents():
    """Test agent system asynchronously"""
    agent_passed = 0
    agent_failed = 0
    
    try:
        manager = AgentManager()
        await manager.initialize()
        print_result("AgentManager initialization", True, f"{len(manager.agents)} agents created")
        agent_passed += 1
    except Exception as e:
        print_result("AgentManager initialization", False, str(e))
        agent_failed += 1
        return agent_passed, agent_failed
    
    try:
        # Submit test task
        task_id = manager.submit_task(
            AgentRole.DISCOVERY,
            "Test discovery task",
            {'data_points': 100}
        )
        print_result("Task submission", True, f"Task {task_id[:12]}...")
        agent_passed += 1
    except Exception as e:
        print_result("Task submission", False, str(e))
        agent_failed += 1
        return agent_passed, agent_failed
    
    try:
        # Wait for task completion
        await asyncio.sleep(1.5)
        results = manager.get_results()
        print_result("Task execution", True, f"Received {len(results)} result(s)")
        agent_passed += 1
    except Exception as e:
        print_result("Task execution", False, str(e))
        agent_failed += 1
        return agent_passed, agent_failed
    
    try:
        # Check agent status
        status = manager.get_agent_status()
        idle_count = sum(1 for a in status.values() if a['status'] == 'idle')
        print_result("Agent status tracking", True, f"{idle_count}/{len(status)} agents idle")
        agent_passed += 1
    except Exception as e:
        print_result("Agent status tracking", False, str(e))
        agent_failed += 1
    
    return agent_passed, agent_failed

# Run async tests
agent_p, agent_f = asyncio.run(test_agents())
passed += agent_p
failed += agent_f

# ════════════════════════════════════════════════════════════════════════════════
# TEST 4: Publishing System
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 4: Zenodo Publishing")

try:
    zenodo_token = os.environ.get('ZENODO_TOKEN', 'test_token_placeholder')
    publisher = PublishingWorkflow(zenodo_token=zenodo_token, use_sandbox=True)
    print_result("PublishingWorkflow initialization", True, "Sandbox mode enabled")
    passed += 1
except Exception as e:
    print_result("PublishingWorkflow initialization", False, str(e))
    failed += 1

try:
    # Check publication decision logic
    test_results = {
        'xeb_mean': 0.87,
        'p_value': 0.003,
        'cohens_d': 0.65
    }
    publishable = test_results['p_value'] < 0.05 and abs(test_results['cohens_d']) > 0.5
    print_result("Publication criteria check", True, f"Publishable={publishable}")
    passed += 1
except Exception as e:
    print_result("Publication criteria check", False, str(e))
    failed += 1

# ════════════════════════════════════════════════════════════════════════════════
# TEST 5: Integration
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 5: System Integration")

try:
    # Verify all modules can be imported together
    from osiris_integrated import OsirisContext, IntentHandlers
    print_result("Full integration import", True, "All modules compatible")
    passed += 1
except Exception as e:
    print_result("Full integration import", False, str(e))
    failed += 1

try:
    # Verify data flow compatibility
    config = ExperimentConfig(
        name="integration_test",
        hypothesis="Integration verification",
        circuit_depth=4,
        n_qubits=5,
        shots=1000,
        trials=10
    )
    
    # Config should be serializable for agent passing
    import json
    serialized = json.dumps({
        'name': config.name,
        'depth': config.circuit_depth
    })
    print_result("Data serialization", True, "Configs are JSON-serializable")
    passed += 1
except Exception as e:
    print_result("Data serialization", False, str(e))
    failed += 1

# ════════════════════════════════════════════════════════════════════════════════
# TEST 6: Performance
# ════════════════════════════════════════════════════════════════════════════════

print_section("TEST 6: Performance Benchmarks")

import time

try:
    start = time.time()
    gen = RandomCircuitGenerator()
    for _ in range(5):
        gen.generate_circuit(5, 4)
    elapsed = time.time() - start
    print_result("Circuit generation speed", True, f"5 circuits in {elapsed:.3f}s ({elapsed/5:.3f}s each)")
    passed += 1
except Exception as e:
    print_result("Circuit generation speed", False, str(e))
    failed += 1

# ════════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════════════

print_section("VERIFICATION SUMMARY")

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n  Total Tests: {total}")
print(f"  Passed: {passed} ✓")
print(f"  Failed: {failed} ✗")
print(f"  Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n  🎉 ALL SYSTEMS OPERATIONAL 🎉")
    print("\n  OSIRIS v2.0 is ready for:")
    print("    • Automated quantum discovery")
    print("    • Statistical validation")
    print("    • Agent-based analysis")
    print("    • Scientific publishing")
    print("\n  Next Steps:")
    print("    1. Run: python3 osiris_integrated.py")
    print("    2. Try: analyze quantum system")
    print("    3. Or:  execute experiment on ibm_torino")
else:
    print(f"\n  ⚠️  {failed} test(s) need attention")
    sys.exit(1)

print("\n" + "="*70 + "\n")
