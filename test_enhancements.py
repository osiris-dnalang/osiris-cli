#!/usr/bin/env python3
"""
Comprehensive tests for OSIRIS enhancement modules:
  - osiris_cognitive_mesh.py (Bayesian trust, Shapley, Nash, causal DAG, Hebbian)
  - osiris_bridge_validator.py (sensitivity tornado, MC falsification, consistency, Bayes factor)
  - osiris_elo_tournament.py (Glicko-2 ratings, tournament, capability radar)
  - osiris_ncllm_swarm.py (mesh-integrated swarm)
"""

import sys
import math
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ════════════════════════════════════════════════════════════════════════════════
# COGNITIVE MESH TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestBetaTrust(unittest.TestCase):
    def test_initial_trust(self):
        from osiris_cognitive_mesh import BetaTrust
        bt = BetaTrust()
        # Prior: alpha=1, beta=1 → mean 0.5
        self.assertAlmostEqual(bt.mean, 0.5, places=2)

    def test_update(self):
        from osiris_cognitive_mesh import BetaTrust
        bt = BetaTrust()
        bt.update(success=True, weight=1.0)
        # After a success, mean should increase
        self.assertGreater(bt.mean, 0.5)

    def test_sample(self):
        from osiris_cognitive_mesh import BetaTrust
        bt = BetaTrust()
        sample = bt.sample()
        self.assertGreaterEqual(sample, 0.0)
        self.assertLessEqual(sample, 1.0)


class TestBayesianTrustNetwork(unittest.TestCase):
    def setUp(self):
        from osiris_cognitive_mesh import BayesianTrustNetwork
        self.net = BayesianTrustNetwork(["a", "b", "c"])

    def test_initial_influence(self):
        inf = self.net.get_aggregate_influence("a")
        # Should be around 0.5 (uniform prior)
        self.assertGreater(inf, 0.0)
        self.assertLessEqual(inf, 1.0)

    def test_update_from_round(self):
        votes = {"a": "approve", "b": "approve", "c": "reject"}
        self.net.update_from_round(votes, "approve", 0.8)
        inf = self.net.get_aggregate_influence("b")
        self.assertIsInstance(inf, float)

    def test_summary(self):
        summary = self.net.summary()
        self.assertIn("a", summary)
        self.assertIn("b", summary)
        self.assertIn("c", summary)


class TestShapleyEstimator(unittest.TestCase):
    def setUp(self):
        from osiris_cognitive_mesh import ShapleyEstimator
        self.est = ShapleyEstimator(["a", "b", "c"], n_samples=50)

    def test_initial_values(self):
        for v in self.est.values.values():
            self.assertEqual(v, 0.0)

    def test_estimate(self):
        # Simple quality function: quality = len(coalition) / 3
        def quality_fn(coalition):
            return len(coalition) / 3.0
        result = self.est.estimate(quality_fn)
        # Each agent should contribute equally
        self.assertAlmostEqual(result["a"], result["b"], places=1)
        self.assertAlmostEqual(result["b"], result["c"], places=1)

    def test_all_agents_present(self):
        for agent in ["a", "b", "c"]:
            self.assertIn(agent, self.est.values)


class TestFictitiousPlaySolver(unittest.TestCase):
    def setUp(self):
        from osiris_cognitive_mesh import FictitiousPlaySolver
        self.solver = FictitiousPlaySolver(["a", "b"])

    def test_initial_frequencies(self):
        for agent in ["a", "b"]:
            self.assertIn(agent, self.solver.freq)

    def test_update(self):
        self.solver.update({"a": "contribute", "b": "challenge"})
        metric = self.solver.convergence_metric()
        self.assertIsInstance(metric, float)

    def test_equilibrium_profile(self):
        profile = self.solver.equilibrium_profile()
        self.assertIn("a", profile)
        self.assertIn("b", profile)


class TestCausalReasoningGraph(unittest.TestCase):
    def setUp(self):
        from osiris_cognitive_mesh import CausalReasoningGraph
        self.graph = CausalReasoningGraph([
            "orchestrator", "reasoner", "coder", "critic"
        ])

    def test_topological_order(self):
        order = self.graph.topological_order()
        self.assertEqual(len(order), 4)
        # Orchestrator should come before reasoner
        self.assertLess(order.index("orchestrator"), order.index("reasoner"))

    def test_to_dict(self):
        d = self.graph.to_dict()
        self.assertIn("nodes", d)
        self.assertIn("edges", d)


class TestHebbianPlasticity(unittest.TestCase):
    def setUp(self):
        from osiris_cognitive_mesh import HebbianPlasticity
        self.hebb = HebbianPlasticity(["a", "b", "c"])

    def test_initial_weights(self):
        # Weights start at 0
        for key, val in self.hebb.weights.items():
            self.assertEqual(val, 0.0)

    def test_update(self):
        self.hebb.update({"a": "approve", "b": "approve", "c": "reject"})
        # a-b should strengthen (both voted same)
        ab_key = frozenset({"a", "b"})
        self.assertGreater(self.hebb.weights[ab_key], 0.0)

    def test_emergent_coalitions(self):
        # After many updates with correlated agents
        for _ in range(20):
            self.hebb.update({"a": "approve", "b": "approve", "c": "reject"})
        coalitions = self.hebb.emergent_coalitions()
        self.assertIsInstance(coalitions, list)


class TestCognitiveMesh(unittest.TestCase):
    def setUp(self):
        from osiris_cognitive_mesh import CognitiveMesh
        self.mesh = CognitiveMesh(["a", "b", "c"])

    def test_execution_order(self):
        order = self.mesh.get_execution_order()
        self.assertEqual(set(order), {"a", "b", "c"})

    def test_dynamic_influence(self):
        inf = self.mesh.get_dynamic_influence("a")
        self.assertGreater(inf, 0.0)
        self.assertLessEqual(inf, 1.0)

    def test_post_round_update(self):
        votes = {"a": "approve", "b": "approve", "c": "reject"}
        self.mesh.post_round_update(votes, "approve", 0.8)
        self.assertEqual(self.mesh._round_count, 1)

    def test_post_task_update(self):
        self.mesh.post_task_update(0.75, {"a": 0.8, "b": 0.7, "c": 0.6})
        self.assertEqual(self.mesh._task_count, 1)
        self.assertAlmostEqual(self.mesh._quality_history[0], 0.75)

    def test_status_report(self):
        votes = {"a": "approve", "b": "approve", "c": "reject"}
        self.mesh.post_round_update(votes, "approve", 0.8)
        report = self.mesh.status_report()
        self.assertIn("rounds", report)
        self.assertIn("trust_summary", report)
        self.assertIn("shapley_values", report)
        self.assertIn("nash_convergence", report)
        self.assertIn("dynamic_influence", report)
        self.assertIn("emergent_coalitions", report)

    def test_print_dashboard(self):
        # Should not raise
        votes = {"a": "approve", "b": "approve", "c": "reject"}
        self.mesh.post_round_update(votes, "approve", 0.8)
        self.mesh.print_dashboard()


# ════════════════════════════════════════════════════════════════════════════════
# BRIDGE VALIDATOR TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestSensitivityTornado(unittest.TestCase):
    def test_run(self):
        from osiris_bridge_validator import SensitivityTornado
        tornado = SensitivityTornado()
        results = tornado.run(n_sigma=1)  # small sigma for speed
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIsInstance(r.elasticity, float)
            self.assertIsInstance(r.conclusion_stable, bool)
            self.assertIsInstance(r.tornado_rank, int)


class TestMonteCarloFalsifier(unittest.TestCase):
    def test_run(self):
        from osiris_bridge_validator import MonteCarloFalsifier
        falsifier = MonteCarloFalsifier()
        results = falsifier.run(n_trials=10)  # small for speed
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIn(r.verdict, ["robust", "moderate", "fragile", "unfalsifiable"])
            self.assertGreaterEqual(r.n_significant, 0)


class TestConsistencyValidator(unittest.TestCase):
    def test_run(self):
        from osiris_bridge_validator import ConsistencyValidator
        validator = ConsistencyValidator()
        results = validator.run()
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIsInstance(r.passed, bool)
            self.assertIsInstance(r.discrepancy, float)


class TestBayesianModelComparison(unittest.TestCase):
    def test_compute(self):
        from osiris_bridge_validator import BayesianModelComparison
        bmc = BayesianModelComparison()
        bf, interpretation = bmc.compute_bayes_factor()
        self.assertIsInstance(bf, float)
        self.assertIsInstance(interpretation, str)
        self.assertGreater(len(interpretation), 0)


class TestAdversarialBridgeValidator(unittest.TestCase):
    def test_full_validation(self):
        from osiris_bridge_validator import AdversarialBridgeValidator
        validator = AdversarialBridgeValidator(mc_trials=5, sensitivity_sigma=1)
        report = validator.validate()
        self.assertTrue(len(report.overall_verdict) > 0)
        self.assertIsInstance(report.bayes_factor, float)
        self.assertGreater(report.elapsed_seconds, 0)
        d = report.to_dict()
        self.assertIn("timestamp", d)
        self.assertIn("overall_verdict", d)


# ════════════════════════════════════════════════════════════════════════════════
# ELO TOURNAMENT TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestRating(unittest.TestCase):
    def test_initial(self):
        from osiris_elo_tournament import Rating
        r = Rating()
        self.assertEqual(r.mu, 1500.0)
        self.assertEqual(r.games, 0)

    def test_expected_score(self):
        from osiris_elo_tournament import Rating
        r1 = Rating()
        r2 = Rating()
        # Equal ratings → expected 0.5
        self.assertAlmostEqual(r1.expected_score(r2), 0.5, places=1)

    def test_update(self):
        from osiris_elo_tournament import Rating
        r = Rating()
        r.update(actual=1.0, expected=0.5)
        # Win against equal → rating should increase
        self.assertGreater(r.mu, 1500.0)
        self.assertEqual(r.wins, 1)


class TestEloTournament(unittest.TestCase):
    def test_run_tournament(self):
        from osiris_elo_tournament import EloTournament
        t = EloTournament()
        results = t.run_tournament(rounds_per_matchup=3)
        self.assertIn("leaderboard", results)
        self.assertIn("elapsed_seconds", results)

    def test_leaderboard(self):
        from osiris_elo_tournament import EloTournament
        t = EloTournament()
        t.run_tournament(rounds_per_matchup=2)
        board = t.leaderboard()
        self.assertGreater(len(board), 0)
        # First entry has highest ELO
        elos = [entry[1] for entry in board]
        self.assertEqual(elos, sorted(elos, reverse=True))

    def test_print_results(self):
        from osiris_elo_tournament import EloTournament
        t = EloTournament()
        t.run_tournament(rounds_per_matchup=2)
        t.print_results()  # should not raise


class TestCapabilityRadar(unittest.TestCase):
    def test_radar(self):
        from osiris_elo_tournament import CapabilityRadar, EloTournament
        t = EloTournament()
        t.run_tournament(rounds_per_matchup=2)
        radar = CapabilityRadar(t)
        data = radar.generate()
        self.assertIn("ncllm", data)
        self.assertIn("ncllm_area", data)
        self.assertIn("competitors", data)


# ════════════════════════════════════════════════════════════════════════════════
# MESH-INTEGRATED SWARM TESTS
# ════════════════════════════════════════════════════════════════════════════════

class TestMeshIntegratedSwarm(unittest.TestCase):
    def test_swarm_with_mesh_enabled(self):
        from osiris_ncllm_swarm import NCLLMSwarm
        swarm = NCLLMSwarm(enable_mesh=True)
        # Verify mesh is attached (private attr _mesh)
        self.assertIsNotNone(getattr(swarm, '_mesh', None))

    def test_swarm_with_mesh_disabled(self):
        from osiris_ncllm_swarm import NCLLMSwarm
        swarm = NCLLMSwarm(enable_mesh=False)
        self.assertIsNone(getattr(swarm, '_mesh', None))

    def test_swarm_status_report(self):
        from osiris_ncllm_swarm import NCLLMSwarm
        swarm = NCLLMSwarm(enable_mesh=True)
        report = swarm.status_report()
        self.assertIsInstance(report, str)
        self.assertIn("Cognitive mesh", report)
        self.assertIn("ACTIVE", report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
