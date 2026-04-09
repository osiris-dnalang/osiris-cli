#!/usr/bin/env python3
"""
Comprehensive tests for OSIRIS tridirectional introspection & feedback bus:
  - osiris_introspection.py (CUSUM, temporal, structural, semantic, self-improver)
  - osiris_feedback_bus.py (FeedbackBus, OsirisIntelligenceLoop)
  - osiris_intent_engine.py (adaptive confidence methods)
"""

import sys
import math
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent))


# ════════════════════════════════════════════════════════════════════════════════
# CUSUM DETECTOR TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestCUSUMDetector(unittest.TestCase):
    def test_no_drift_initially(self):
        from osiris_introspection import CUSUMDetector
        cd = CUSUMDetector(threshold=5.0, drift_weight=0.5)
        self.assertFalse(cd.drift_detected)

    def test_detects_positive_drift(self):
        from osiris_introspection import CUSUMDetector
        cd = CUSUMDetector(threshold=3.0, drift_weight=0.5)
        # Feed consistently high values to trigger positive drift
        for _ in range(50):
            cd.update(1.5)
        self.assertTrue(cd.drift_detected)

    def test_detects_negative_drift(self):
        from osiris_introspection import CUSUMDetector
        cd = CUSUMDetector(threshold=3.0, drift_weight=0.5)
        for _ in range(50):
            cd.update(-1.5)
        self.assertTrue(cd.drift_detected)

    def test_stable_signal_no_drift(self):
        from osiris_introspection import CUSUMDetector
        cd = CUSUMDetector(threshold=5.0, drift_weight=0.5)
        # Feed stable values around mean
        for v in [0.01, -0.01, 0.005, -0.005, 0.0]:
            cd.update(v)
        self.assertFalse(cd.drift_detected)


# ════════════════════════════════════════════════════════════════════════════════
# TEMPORAL INTROSPECTOR TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestTemporalIntrospector(unittest.TestCase):
    def setUp(self):
        from osiris_introspection import TemporalIntrospector
        self.agents = ["Orchestrator", "Reasoner", "Coder"]
        self.temporal = TemporalIntrospector(self.agents)

    def _make_responses(self, conf=0.7, vote="approve"):
        """Build responses list in the expected format."""
        return [
            {"agent": a, "confidence": conf, "vote": vote}
            for a in self.agents
        ]

    def test_observe_round(self):
        responses = self._make_responses(0.7, "approve")
        self.temporal.observe_round(responses, "approve", 0.8)
        self.assertEqual(len(self.temporal._quality_history), 1)

    def test_quality_forecast(self):
        # Feed multiple rounds to enable forecasting
        for i in range(5):
            responses = self._make_responses(0.5 + i * 0.05, "approve")
            self.temporal.observe_round(responses, "approve", 0.5 + i * 0.05)
        forecast = self.temporal.quality_forecast()
        self.assertIsInstance(forecast, list)
        self.assertEqual(len(forecast), 5)  # default horizon=5

    def test_agent_health(self):
        for _ in range(3):
            responses = self._make_responses(0.8, "approve")
            self.temporal.observe_round(responses, "approve", 0.8)
        health = self.temporal.agent_health()
        self.assertIn("Orchestrator", health)
        self.assertIn("avg_confidence", health["Orchestrator"])

    def test_drift_alerts(self):
        # Initially no alerts
        alerts = self.temporal.recent_alerts()
        self.assertIsInstance(alerts, list)

    def test_clear_alerts(self):
        self.temporal.clear_alerts()
        self.assertEqual(len(self.temporal._alerts), 0)


# ════════════════════════════════════════════════════════════════════════════════
# STRUCTURAL INTROSPECTOR TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestStructuralIntrospector(unittest.TestCase):
    def setUp(self):
        from osiris_introspection import StructuralIntrospector
        self.agents = ["Orchestrator", "Reasoner", "Coder", "Critic", "Rebel"]
        self.structural = StructuralIntrospector(self.agents)

    def test_observe_round(self):
        votes = {
            "Orchestrator": "approve",
            "Reasoner": "approve",
            "Coder": "reject",
            "Critic": "reject",
            "Rebel": "refine",
        }
        self.structural.observe_round(votes, "approve", 0.7)
        self.assertEqual(len(self.structural._vote_ledger), 1)

    def test_cognitive_entropy(self):
        # Max entropy: all agents vote differently
        self.structural.observe_round({
            "Orchestrator": "approve",
            "Reasoner": "reject",
            "Coder": "refine",
            "Critic": "approve",
            "Rebel": "reject",
        }, "approve", 0.7)
        entropy = self.structural.cognitive_entropy()
        # With 3 distinct votes among 5 agents, entropy > 0
        self.assertGreater(entropy, 0.0)

    def test_echo_chamber_score(self):
        # All agents vote the same → high echo chamber
        for _ in range(5):
            self.structural.observe_round({
                a: "approve" for a in self.agents
            }, "approve", 0.7)
        score = self.structural.echo_chamber_score()
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)

    def test_contrarian_value(self):
        value = self.structural.contrarian_value()
        self.assertIsInstance(value, dict)

    def test_voting_pattern_matrix(self):
        for _ in range(3):
            self.structural.observe_round({
                a: "approve" for a in self.agents
            }, "approve", 0.7)
        matrix = self.structural.voting_pattern_matrix()
        self.assertIsInstance(matrix, dict)


# ════════════════════════════════════════════════════════════════════════════════
# SEMANTIC INTROSPECTOR TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestSemanticIntrospector(unittest.TestCase):
    def setUp(self):
        from osiris_introspection import SemanticIntrospector
        self.semantic = SemanticIntrospector()

    def test_observe_task(self):
        self.semantic.observe_task(
            task="fix the login bug",
            final_output="patched auth module",
            quality=0.8,
            success=True,
        )
        cap = self.semantic.capability_map()
        self.assertIsInstance(cap, dict)

    def test_capability_map(self):
        # Add tasks of different types
        for i in range(5):
            self.semantic.observe_task(
                task="create a new module",
                final_output=f"module_{i}.py created",
                quality=0.6 + i * 0.05,
                success=True,
            )
        boundary = self.semantic.capability_map()
        self.assertIn("creation", boundary)
        self.assertIn("avg_quality", boundary["creation"])

    def test_blind_spots(self):
        # Add tasks with failures
        for i in range(3):
            self.semantic.observe_task(
                task="security audit for injection",
                final_output="scan incomplete",
                quality=0.2,
                success=False,
            )
        spots = self.semantic.blind_spots()
        self.assertIsInstance(spots, list)

    def test_strategy_novelty(self):
        self.semantic.observe_task("create a parser", "parser.py", 0.7, True)
        self.semantic.observe_task("create a formatter", "formatter.py", 0.8, True)
        novelty = self.semantic.strategy_novelty()
        self.assertIsInstance(novelty, dict)


# ════════════════════════════════════════════════════════════════════════════════
# RECURSIVE SELF-IMPROVER TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestRecursiveSelfImprover(unittest.TestCase):
    def setUp(self):
        from osiris_introspection import (
            TemporalIntrospector,
            StructuralIntrospector,
            SemanticIntrospector,
            RecursiveSelfImprover,
        )
        agents = ["A", "B", "C"]
        self.temporal = TemporalIntrospector(agents)
        self.structural = StructuralIntrospector(agents)
        self.semantic = SemanticIntrospector()
        self.improver = RecursiveSelfImprover(
            self.temporal, self.structural, self.semantic
        )

    def test_diagnose_empty(self):
        # With no data, diagnose should return empty or minimal actions
        actions = self.improver.diagnose()
        self.assertIsInstance(actions, list)

    def test_diagnose_with_data(self):
        # Feed some data
        for _ in range(5):
            self.temporal.observe_round(
                [{"agent": "A", "confidence": 0.3, "vote": "reject"},
                 {"agent": "B", "confidence": 0.9, "vote": "approve"},
                 {"agent": "C", "confidence": 0.5, "vote": "refine"}],
                "approve", 0.5
            )
            self.structural.observe_round(
                {"A": "reject", "B": "approve", "C": "refine"},
                "approve", 0.5
            )
        actions = self.improver.diagnose()
        self.assertIsInstance(actions, list)

    def test_apply_with_mock_mesh(self):
        mesh = MagicMock()
        mesh.agent_ids = ["A", "B", "C"]
        mesh.trust_net = MagicMock()

        from osiris_introspection import ImprovementAction
        action = ImprovementAction(
            action_type="reweight",
            target="A",
            parameter="trust",
            current_value=0.5,
            recommended_value=0.3,
            rationale="Test reweight",
            priority=0.8,
        )
        result = self.improver.apply(action, mesh=mesh)
        self.assertIsInstance(result, bool)

    def test_verify(self):
        self.improver.verify(pre_quality=0.5, post_quality=0.7)
        # Should record a success
        self.assertEqual(len(self.improver._improvement_success), 1)
        self.assertGreater(self.improver._improvement_success[0], 0)

    def test_improvement_report(self):
        report = self.improver.improvement_report()
        self.assertIn("iteration", report)
        self.assertIn("total_actions", report)
        self.assertIn("success_rate", report)


# ════════════════════════════════════════════════════════════════════════════════
# INTROSPECTION ENGINE (UNIFIED) TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestIntrospectionEngine(unittest.TestCase):
    def setUp(self):
        from osiris_introspection import IntrospectionEngine
        self.engine = IntrospectionEngine()

    def test_observe_round(self):
        responses = [
            {"agent": "orchestrator", "confidence": 0.7, "vote": "approve"},
            {"agent": "reasoner", "confidence": 0.8, "vote": "approve"},
            {"agent": "coder", "confidence": 0.6, "vote": "reject"},
        ]
        self.engine.observe_round(responses, "approve", 0.75)
        self.assertEqual(self.engine._round_count, 1)

    def test_observe_task(self):
        self.engine.observe_task(
            task="optimize the database queries",
            final_output="added indexing and query batching",
            quality=0.8,
            success=True,
        )
        self.assertEqual(self.engine._task_count, 1)

    def test_run_improvement_cycle(self):
        # Feed data
        for _ in range(3):
            self.engine.observe_round(
                [{"agent": "orchestrator", "confidence": 0.7, "vote": "approve"},
                 {"agent": "reasoner", "confidence": 0.5, "vote": "reject"}],
                "approve", 0.6
            )
        actions = self.engine.run_improvement_cycle()
        self.assertIsInstance(actions, list)

    def test_full_report(self):
        report = self.engine.full_report()
        self.assertIn("rounds_observed", report)
        self.assertIn("tasks_observed", report)

    def test_print_dashboard(self):
        # Just verify it doesn't crash
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.engine.print_dashboard()
        output = buf.getvalue()
        # Dashboard should contain some text
        self.assertGreater(len(output), 0)


# ════════════════════════════════════════════════════════════════════════════════
# FEEDBACK BUS TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestFeedbackBus(unittest.TestCase):
    def setUp(self):
        from osiris_feedback_bus import FeedbackBus
        self.bus = FeedbackBus()

    def test_publish_and_subscribe(self):
        from osiris_feedback_bus import BusMessage, MessageType
        received = []
        self.bus.subscribe("intent", lambda msg: received.append(msg))
        self.bus.publish(BusMessage(
            msg_type=MessageType.TELEMETRY,
            source="swarm",
            target="intent",
            payload={"quality": 0.8},
        ))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["quality"], 0.8)

    def test_all_subscriber(self):
        from osiris_feedback_bus import BusMessage, MessageType
        received = []
        self.bus.subscribe("all", lambda msg: received.append(msg))
        self.bus.publish(BusMessage(
            msg_type=MessageType.ALERT,
            source="swarm",
            target="intent",
            payload={"msg": "test"},
        ))
        # "all" subscriber should receive messages to any target
        self.assertEqual(len(received), 1)

    def test_emit_swarm_telemetry(self):
        from osiris_feedback_bus import MessageType
        received_intent = []
        received_tui = []
        self.bus.subscribe("intent", lambda msg: received_intent.append(msg))
        self.bus.subscribe("tui", lambda msg: received_tui.append(msg))
        self.bus.emit_swarm_telemetry(0.85, {"entropy": 1.2}, {"trust": 0.7})
        self.assertEqual(len(received_intent), 1)
        self.assertEqual(len(received_tui), 1)

    def test_emit_intent_routing(self):
        received = []
        self.bus.subscribe("swarm", lambda msg: received.append(msg))
        self.bus.emit_intent_routing("debug", 0.9, ["compile", "test"], {})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["intent_type"], "debug")

    def test_emit_alert(self):
        received = []
        self.bus.subscribe("all", lambda msg: received.append(msg))
        self.bus.emit_alert("introspection", "high entropy", severity=0.8)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["severity"], 0.8)

    def test_get_unified_state(self):
        self.bus.emit_swarm_telemetry(0.9, {}, {})
        state = self.bus.get_unified_state()
        self.assertIn("swarm", state)
        self.assertIn("intent", state)
        self.assertIn("bus_stats", state)
        self.assertEqual(state["bus_stats"]["total_messages"], 2)  # telemetry + diagnostic

    def test_recent_messages(self):
        from osiris_feedback_bus import BusMessage, MessageType
        for i in range(5):
            self.bus.publish(BusMessage(
                msg_type=MessageType.TELEMETRY,
                source="swarm",
                target="intent",
                payload={"i": i},
            ))
        recent = self.bus.recent_messages(3)
        self.assertEqual(len(recent), 3)

    def test_recent_alerts(self):
        self.bus.emit_alert("test", "alert1", 0.5)
        self.bus.emit_alert("test", "alert2", 0.9)
        alerts = self.bus.recent_alerts(5)
        self.assertEqual(len(alerts), 2)

    def test_print_status(self):
        import io, contextlib
        self.bus.emit_alert("test", "test alert", 0.6)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.bus.print_status()
        output = buf.getvalue()
        self.assertIn("FEEDBACK BUS", output)

    def test_bus_message_to_dict(self):
        from osiris_feedback_bus import BusMessage, MessageType
        msg = BusMessage(
            msg_type=MessageType.TELEMETRY,
            source="swarm",
            target="intent",
            payload={"quality": 0.8},
        )
        d = msg.to_dict()
        self.assertEqual(d["msg_type"], "telemetry")
        self.assertEqual(d["source"], "swarm")

    def test_max_history(self):
        from osiris_feedback_bus import FeedbackBus, BusMessage, MessageType
        bus = FeedbackBus(max_history=5)
        for i in range(10):
            bus.publish(BusMessage(
                msg_type=MessageType.TELEMETRY,
                source="swarm",
                target="intent",
                payload={"i": i},
            ))
        self.assertEqual(len(bus._message_history), 5)
        self.assertEqual(bus._message_count, 10)


# ════════════════════════════════════════════════════════════════════════════════
# INTENT ENGINE ADAPTIVE CONFIDENCE TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestIntentEngineAdaptive(unittest.TestCase):
    def setUp(self):
        from osiris_intent_engine import IntentEngine
        self.engine = IntentEngine()

    def test_receive_swarm_feedback(self):
        self.engine.receive_swarm_feedback("debug", 0.9, {})
        ctx = self.engine.get_swarm_capability_context()
        self.assertIn("intent_success_rates", ctx)
        self.assertIn("debug", ctx["intent_success_rates"])

    def test_get_adaptive_confidence_no_data(self):
        # Without feedback, adaptive confidence == base confidence
        result = self.engine.get_adaptive_confidence(0.8, "unknown_type")
        self.assertAlmostEqual(result, 0.8, places=2)

    def test_adaptive_confidence_improves_with_good_feedback(self):
        for _ in range(5):
            self.engine.receive_swarm_feedback("creation", 0.9, {})
        adjusted = self.engine.get_adaptive_confidence(0.7, "creation")
        # Good feedback should boost confidence
        self.assertGreaterEqual(adjusted, 0.7)

    def test_adaptive_confidence_degrades_with_poor_feedback(self):
        for _ in range(5):
            self.engine.receive_swarm_feedback("debug", 0.2, {})
        adjusted = self.engine.get_adaptive_confidence(0.7, "debug")
        # Poor feedback should reduce confidence
        self.assertLessEqual(adjusted, 0.7)

    def test_get_swarm_capability_context(self):
        ctx = self.engine.get_swarm_capability_context()
        self.assertIn("intent_success_rates", ctx)
        self.assertIn("confidence_adjustments", ctx)

    def test_confidence_bounded(self):
        # Even with extreme feedback, confidence stays in [0, 1]
        for _ in range(20):
            self.engine.receive_swarm_feedback("test", 0.0, {})
        result = self.engine.get_adaptive_confidence(0.1, "test")
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

        for _ in range(20):
            self.engine.receive_swarm_feedback("test2", 1.0, {})
        result2 = self.engine.get_adaptive_confidence(0.95, "test2")
        self.assertGreaterEqual(result2, 0.0)
        self.assertLessEqual(result2, 1.0)


# ════════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestIntrospectionIntegration(unittest.TestCase):
    """Test that introspection components work together."""

    def test_full_observation_cycle(self):
        from osiris_introspection import IntrospectionEngine
        engine = IntrospectionEngine()
        agents = engine.agent_ids

        # Simulate 10 rounds
        import random
        random.seed(42)
        for r in range(10):
            responses = []
            for a in agents:
                responses.append({
                    "agent": a,
                    "confidence": max(0.1, min(1.0, random.gauss(0.7, 0.2))),
                    "vote": random.choice(["approve", "reject", "refine"]),
                })
            consensus = random.choice(["approve", "reject", "refine"])
            quality = max(0.0, min(1.0, random.gauss(0.6 + r * 0.02, 0.15)))
            engine.observe_round(responses, consensus, quality)

        # Simulate 5 tasks
        task_descs = [
            ("fix the login bug", "patched auth"),
            ("create a REST API", "api.py with endpoints"),
            ("optimize the sort", "switched to timsort"),
            ("analyze memory leak", "found circular ref"),
            ("build a CLI tool", "argparse module created"),
        ]
        for task, output in task_descs:
            quality = max(0.0, min(1.0, random.gauss(0.65, 0.15)))
            engine.observe_task(task, output, quality)

        # Run improvement cycle
        actions = engine.run_improvement_cycle()
        self.assertIsInstance(actions, list)

    def test_feedback_bus_state_accumulation(self):
        from osiris_feedback_bus import FeedbackBus
        bus = FeedbackBus()

        # Simulate swarm telemetry
        bus.emit_swarm_telemetry(0.8, {"entropy": 1.5}, {"trust": 0.7})
        bus.emit_intent_routing("optimization", 0.85, ["profile"], {"known": True})

        state = bus.get_unified_state()
        self.assertEqual(state["swarm"]["quality"], 0.8)
        self.assertEqual(state["intent"]["intent_type"], "optimization")


if __name__ == "__main__":
    unittest.main(verbosity=2)
