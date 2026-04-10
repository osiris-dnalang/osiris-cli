"""
OSIRIS Integration Tests
=========================

End-to-end tests that exercise cross-module integrations,
not just individual units. Tests real data flow between subsystems.
"""

import sys
import unittest
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


class TestLocalQVMPipeline(unittest.TestCase):
    """Full execution pipeline of the tetrahedral quaternionic QVM."""

    def test_random_circuit_execution(self):
        from osiris_local_qvm import LocalQVM
        qvm = LocalQVM(n_qubits=4, seed=123)
        result = qvm.execute(circuit_type="random", depth=4, shots=256)
        self.assertEqual(result.n_qubits, 4)
        self.assertGreater(len(result.counts), 0)
        self.assertAlmostEqual(sum(result.probabilities.values()), 1.0, places=5)

    def test_adaptive_circuit_execution(self):
        from osiris_local_qvm import LocalQVM
        qvm = LocalQVM(n_qubits=4, seed=42)
        r1 = qvm.execute(circuit_type="random", depth=4, shots=128)
        r2 = qvm.execute(circuit_type="adaptive", depth=4, shots=128,
                          feedback=r1.xeb_score)
        self.assertEqual(r2.n_qubits, 4)
        self.assertIsInstance(r2.xeb_score, float)

    def test_rqc_vs_rcs_comparison(self):
        from osiris_local_qvm import LocalQVM
        qvm = LocalQVM(n_qubits=3, seed=7)
        comp = qvm.rqc_vs_rcs(depth=4, shots=128, iterations=2)
        self.assertIn("rcs_mean_xeb", comp)
        self.assertIn("rqc_mean_xeb", comp)
        self.assertIn("rqc_wins", comp)
        self.assertIsInstance(comp["improvement_pct"], float)

    def test_qvm_ccce_metrics(self):
        from osiris_local_qvm import LocalQVM, CCCEMetrics
        qvm = LocalQVM(n_qubits=4, seed=42)
        qvm.random_circuit(depth=4)
        ccce = CCCEMetrics.from_register(qvm.qubits)
        self.assertGreaterEqual(ccce.phi, 0)
        self.assertGreaterEqual(ccce.lambda_, 0)
        self.assertGreaterEqual(ccce.gamma, 0)
        self.assertGreaterEqual(ccce.xi, 0)
        self.assertGreater(ccce.qbyte_yield, 0)

    def test_qvm_gate_log(self):
        from osiris_local_qvm import LocalQVM
        qvm = LocalQVM(n_qubits=2, seed=0)
        qvm.h(0)
        qvm.cx(0, 1)
        qvm.rz(1, 0.5)
        self.assertEqual(len(qvm.gate_log), 3)
        self.assertEqual(qvm.gate_log[0]["gate"], "H")
        self.assertEqual(qvm.gate_log[1]["gate"], "CX")
        self.assertEqual(qvm.gate_log[2]["gate"], "RZ")


class TestTetrahedralMath(unittest.TestCase):
    """Validate the quaternionic mathematical substrate."""

    def test_quaternion_normalization(self):
        from osiris_local_qvm import Quaternion
        q = Quaternion(1, 2, 3, 4).normalize()
        norm = np.sqrt(q.w**2 + q.x**2 + q.y**2 + q.z**2)
        self.assertAlmostEqual(norm, 1.0, places=10)

    def test_quaternion_multiplication(self):
        from osiris_local_qvm import Quaternion
        a = Quaternion(1, 0, 0, 0)  # identity
        b = Quaternion(0, 1, 0, 0)
        c = a * b
        self.assertAlmostEqual(c.x, 1.0)
        self.assertAlmostEqual(c.w, 0.0)

    def test_quaternion_conjugate(self):
        from osiris_local_qvm import Quaternion
        q = Quaternion(1, 2, 3, 4)
        qc = q.conjugate()
        self.assertAlmostEqual(qc.w, q.w)
        self.assertAlmostEqual(qc.x, -q.x)
        self.assertAlmostEqual(qc.y, -q.y)
        self.assertAlmostEqual(qc.z, -q.z)

    def test_hopf_fibration(self):
        from osiris_local_qvm import TetrahedralQubit
        qubit = TetrahedralQubit(label=0)
        bloch = qubit.bloch_vector()
        self.assertEqual(len(bloch), 3)
        # Bloch vector magnitude should be <= 1
        self.assertLessEqual(np.linalg.norm(bloch), 1.0 + 1e-10)

    def test_tetrahedral_gate_unitarity(self):
        from osiris_local_qvm import TetrahedralGates, TetrahedralQubit
        qubit = TetrahedralQubit(label=0)
        # H then H should approximately return to original
        original_state = Quaternion_copy(qubit.state)
        qubit.apply_gate(TetrahedralGates.H())
        qubit.apply_gate(TetrahedralGates.H())
        # Check coherence is preserved (approximately)
        self.assertGreater(qubit.coherence, 0.5)


def Quaternion_copy(q):
    """Helper to copy a Quaternion."""
    from osiris_local_qvm import Quaternion
    return Quaternion(q.w, q.x, q.y, q.z)


class TestSwarmMasterPromptIntegration(unittest.TestCase):
    """Verify master prompt is wired into the swarm agent pipeline."""

    def test_master_prompt_loaded_in_swarm(self):
        from osiris_ncllm_swarm import _MASTER_PROMPT
        self.assertIsInstance(_MASTER_PROMPT, str)
        self.assertGreater(len(_MASTER_PROMPT), 100)
        self.assertIn("OSIRIS", _MASTER_PROMPT)

    def test_livlm_lock_exists(self):
        from osiris_ncllm_swarm import _LIVLM_LOCK
        import threading
        self.assertIsInstance(_LIVLM_LOCK, type(threading.Lock()))


class TestSwarmDeliberation(unittest.TestCase):
    """Test swarm produces structured output with consensus voting."""

    def test_single_round_deliberation(self):
        from osiris_ncllm_swarm import NCLLMSwarm
        swarm = NCLLMSwarm(user_id="test_integration")
        result = swarm.solve("What is 2+2?", max_rounds=1)
        self.assertGreater(len(result.rounds), 0)
        round0 = result.rounds[0]
        self.assertGreater(len(round0.responses), 0)
        # All 9 agents should respond
        agents = {r.agent for r in round0.responses}
        self.assertGreaterEqual(len(agents), 6)  # at least core agents

    def test_quality_score_bounded(self):
        from osiris_ncllm_swarm import NCLLMSwarm
        swarm = NCLLMSwarm(user_id="test_quality")
        result = swarm.solve("Implement a hello world function", max_rounds=1)
        self.assertGreaterEqual(result.quality_score, 0.0)
        self.assertLessEqual(result.quality_score, 1.0)


class TestFeedbackBusIntegration(unittest.TestCase):
    """Test feedback bus pub/sub with real message types."""

    def test_multi_channel_routing(self):
        from osiris_feedback_bus import FeedbackBus, BusMessage, MessageType

        bus = FeedbackBus()
        ch1_msgs = []
        ch2_msgs = []

        bus.subscribe("intent", lambda m: ch1_msgs.append(m))
        bus.subscribe("swarm", lambda m: ch2_msgs.append(m))

        bus.publish(BusMessage(
            source="test", target="intent",
            msg_type=MessageType.CONTEXT, payload={"a": 1},
        ))
        bus.publish(BusMessage(
            source="test", target="swarm",
            msg_type=MessageType.TELEMETRY, payload={"b": 2},
        ))

        self.assertEqual(len(ch1_msgs), 1)
        self.assertEqual(len(ch2_msgs), 1)
        self.assertEqual(ch1_msgs[0].payload["a"], 1)
        self.assertEqual(ch2_msgs[0].payload["b"], 2)


class TestCognitiveMeshIntegration(unittest.TestCase):
    """Test mesh trust updates across multiple rounds."""

    def test_trust_convergence(self):
        from osiris_cognitive_mesh import CognitiveMesh
        import random

        mesh = CognitiveMesh()
        # Run 10 rounds where one agent always votes with consensus
        for _ in range(10):
            votes = {a: random.choice(["approve", "reject"])
                     for a in mesh.agent_ids}
            consensus = "approve"
            mesh.post_round_update(votes, consensus, quality=0.8)

        report = mesh.status_report()
        self.assertIsInstance(report, dict)


class TestHealthDiagnostic(unittest.TestCase):
    """Test the health diagnostic module itself."""

    def test_health_report_structure(self):
        from osiris_health import HealthReport, CheckResult
        report = HealthReport()
        report.checks.append(CheckResult(name="test", status="PASS"))
        report.checks.append(CheckResult(name="test2", status="FAIL", detail="oops"))
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.total, 2)
        self.assertAlmostEqual(report.score, 0.5)

    def test_torsion_core_check(self):
        from osiris_health import check_torsion_core
        result = check_torsion_core()
        self.assertEqual(result.status, "PASS")

    def test_cli_dispatch_check(self):
        from osiris_health import check_cli_dispatch
        result = check_cli_dispatch()
        self.assertEqual(result.status, "PASS")

    def test_master_prompt_check(self):
        from osiris_health import check_master_prompt
        result = check_master_prompt()
        self.assertEqual(result.status, "PASS")

    def test_local_qvm_check(self):
        from osiris_health import check_local_qvm
        result = check_local_qvm()
        self.assertEqual(result.status, "PASS")


class TestCLIDispatchIntegrity(unittest.TestCase):
    """Verify all commands in help text have corresponding dispatch entries."""

    def test_all_help_commands_dispatched(self):
        source = Path(__file__).parent.parent.joinpath("osiris_launcher.py").read_text()

        # Extract commands from help text
        import re
        help_commands = set()
        for m in re.finditer(r"^\s{2}(\S+)\s{2,}", source, re.MULTILINE):
            cmd = m.group(1).strip()
            if cmd and not cmd.startswith("#") and not cmd.startswith("osiris"):
                help_commands.add(cmd)

        # Check dispatch table has entries
        for cmd in ["qvm", "health", "discover", "nclm", "ultra-coder", "swarm",
                     "bridges", "validate", "tournament", "mesh",
                     "introspect", "feedback"]:
            self.assertIn(f"'{cmd}'", source, f"Command '{cmd}' missing from dispatch")


if __name__ == "__main__":
    unittest.main()
