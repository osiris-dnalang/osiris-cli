"""
Tests for the 5 new OSIRIS modules:
  1. AutopoieticLoop
  2. HabitatScanner
  3. HamiltonianSynthesisEngine
  4. MCPServer / MCPClient
  5. FleetConsciousness
"""

import json
import os
import tempfile
import time
import unittest

# ---------------------------------------------------------------------------
# 1. AutopoieticLoop
# ---------------------------------------------------------------------------
from osiris.lab.autopoietic_loop import AutopoieticLoop
from osiris.organisms.gene import Gene
from osiris.organisms.genome import Genome
from osiris.organisms.organism import Organism


class TestAutopoieticLoop(unittest.TestCase):

    def test_seed_default(self):
        loop = AutopoieticLoop(population_size=10)
        n = loop.seed_default(n=10)
        self.assertEqual(n, 10)
        self.assertEqual(len(loop.population), 10)

    def test_step_returns_snapshot(self):
        loop = AutopoieticLoop(population_size=8)
        loop.seed_default(n=8)
        snap = loop.step()
        self.assertIn("cycle", snap)
        self.assertIn("best_fitness", snap)
        self.assertIn("avg_fitness", snap)
        self.assertEqual(snap["cycle"], 1)

    def test_run_multiple_cycles(self):
        loop = AutopoieticLoop(population_size=8)
        loop.seed_default(n=8)
        results = loop.run(generations=5, verbose=False)
        self.assertEqual(len(results), 5)
        self.assertEqual(loop.cycle, 5)

    def test_chronos_chain_valid(self):
        loop = AutopoieticLoop(population_size=6)
        loop.seed_default(n=6)
        loop.run(generations=3, verbose=False)
        self.assertTrue(loop.chronos.verify_chain())

    def test_summary_structure(self):
        loop = AutopoieticLoop(population_size=6)
        loop.seed_default(n=6)
        loop.run(generations=2, verbose=False)
        s = loop.summary()
        self.assertIn("total_cycles", s)
        self.assertIn("chronos_chain_valid", s)
        self.assertIn("best_organism", s)
        self.assertTrue(s["chronos_chain_valid"])

    def test_seed_from_habitat(self):
        with tempfile.TemporaryDirectory() as td:
            # Write a JSON organism
            org_data = {
                "name": "test_org",
                "genes": [
                    {"name": "g0", "expression": 0.8},
                    {"name": "g1", "expression": 0.6},
                ],
            }
            with open(os.path.join(td, "org1.json"), "w") as f:
                json.dump(org_data, f)
            # Write a .dna file
            with open(os.path.join(td, "circuit.dna"), "w") as f:
                f.write("H q[0]\nCX q[0] q[1]\nMEASURE q[0] -> c[0]\n")

            loop = AutopoieticLoop(population_size=10)
            n = loop.seed_from_habitat(td)
            self.assertEqual(n, 2)
            self.assertEqual(len(loop.population), 2)

    def test_save_telemetry(self):
        loop = AutopoieticLoop(population_size=6)
        loop.seed_default(n=6)
        loop.run(generations=2, verbose=False)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            loop.save_telemetry(path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("summary", data)
            self.assertIn("telemetry", data)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 2. HabitatScanner
# ---------------------------------------------------------------------------
from osiris.lab.habitat_scanner import HabitatScanner, HabitatEntry


class TestHabitatScanner(unittest.TestCase):

    def test_scan_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            scanner = HabitatScanner(roots=[td])
            entries = scanner.scan()
            self.assertEqual(len(entries), 0)

    def test_scan_classifies_py(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "experiment.py"), "w") as f:
                f.write("from qiskit import QuantumCircuit\n")
            scanner = HabitatScanner(roots=[td])
            entries = scanner.scan()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "quantum_script")

    def test_scan_classifies_organism_json(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "org.json"), "w") as f:
                json.dump({"name": "test", "genes": [{"name": "g0"}]}, f)
            scanner = HabitatScanner(roots=[td])
            entries = scanner.scan()
            self.assertEqual(entries[0].kind, "organism")

    def test_scan_classifies_result_json(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "res.json"), "w") as f:
                json.dump({"fidelity": 0.99, "counts": {"00": 500}}, f)
            scanner = HabitatScanner(roots=[td])
            entries = scanner.scan()
            self.assertEqual(entries[0].kind, "result")

    def test_summary(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "a.py"), "w") as f:
                f.write("print('hello')")
            with open(os.path.join(td, "b.dna"), "w") as f:
                f.write("H q[0]")
            scanner = HabitatScanner(roots=[td])
            scanner.scan()
            s = scanner.summary()
            self.assertEqual(s["total_files"], 2)
            self.assertIn("kinds", s)

    def test_organisms_query(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "org.json"), "w") as f:
                json.dump({"name": "a", "genes": [{"name": "x"}]}, f)
            with open(os.path.join(td, "script.py"), "w") as f:
                f.write("pass")
            scanner = HabitatScanner(roots=[td])
            scanner.scan()
            self.assertEqual(len(scanner.organisms()), 1)
            self.assertEqual(len(scanner.scripts()), 1)


# ---------------------------------------------------------------------------
# 3. HamiltonianSynthesisEngine
# ---------------------------------------------------------------------------
from osiris.compiler.hamiltonian_synthesis import (
    HamiltonianSynthesisEngine,
    ProblemType,
)


class TestHamiltonianSynthesis(unittest.TestCase):

    def setUp(self):
        self.engine = HamiltonianSynthesisEngine()

    def test_bell(self):
        r = self.engine.synthesize(ProblemType.BELL, n_qubits=2)
        self.assertGreater(r.gate_count, 0)
        self.assertEqual(r.problem_type, ProblemType.BELL)
        qasm = r.circuit.to_qasm()
        self.assertIn("OPENQASM", qasm)

    def test_ghz(self):
        r = self.engine.synthesize(ProblemType.GHZ, n_qubits=5)
        self.assertEqual(r.qubit_count, 5)

    def test_qft(self):
        r = self.engine.synthesize(ProblemType.QFT, n_qubits=4)
        self.assertGreater(r.depth, 0)

    def test_ising_1d(self):
        r = self.engine.synthesize(ProblemType.ISING_1D, n_qubits=4, depth=3)
        self.assertGreater(r.gate_count, 10)

    def test_maxcut(self):
        r = self.engine.synthesize(ProblemType.MAXCUT, n_qubits=4, depth=2)
        self.assertGreater(r.gate_count, 0)

    def test_vqe_h2(self):
        r = self.engine.synthesize(ProblemType.VQE_H2, n_qubits=4)
        self.assertGreaterEqual(r.qubit_count, 4)

    def test_grover(self):
        r = self.engine.synthesize(ProblemType.GROVER, n_qubits=3, depth=2)
        self.assertGreater(r.gate_count, 0)

    def test_random_rqc(self):
        r = self.engine.synthesize(ProblemType.RANDOM_RQC, n_qubits=4, depth=5)
        self.assertGreater(r.gate_count, 10)

    def test_auto_detect_ising(self):
        r = self.engine.auto_detect("1D Ising spin chain", n_qubits=6)
        self.assertEqual(r.problem_type, ProblemType.ISING_1D)

    def test_auto_detect_grover(self):
        r = self.engine.auto_detect("search for marked element", n_qubits=3)
        self.assertEqual(r.problem_type, ProblemType.GROVER)

    def test_list_problems(self):
        problems = self.engine.list_problems()
        self.assertIn("bell", problems)
        self.assertIn("ising_1d", problems)

    def test_qasm_output(self):
        r = self.engine.synthesize(ProblemType.BELL)
        qasm = r.circuit.to_qasm()
        self.assertIn("qreg", qasm)
        self.assertIn("creg", qasm)
        self.assertIn("measure", qasm)


# ---------------------------------------------------------------------------
# 4. MCP Server + Client
# ---------------------------------------------------------------------------
from osiris.mcp import MCPServer, MCPClient, MCPTool


class TestMCPTool(unittest.TestCase):

    def test_tool_to_dict(self):
        t = MCPTool("test", lambda: 42, "A test tool", {"type": "object"})
        d = t.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["description"], "A test tool")


class TestMCPServerClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = MCPServer(name="test_osiris", port=0)
        cls.server.register_tool("echo", lambda msg="": {"echo": msg},
                                 description="Echo input")
        cls.server.register_tool("add", lambda a=0, b=0: {"sum": a + b},
                                 description="Add two numbers")
        # Use port 0 to get an ephemeral port
        cls.server._server = None
        from http.server import HTTPServer
        from osiris.mcp import _MCPRequestHandler
        cls.server._server = HTTPServer(("127.0.0.1", 0), _MCPRequestHandler)
        cls.server._server.name = cls.server.name
        cls.server._server._tools = cls.server._tools
        cls.server._started_at = time.time()
        actual_port = cls.server._server.server_address[1]
        import threading
        cls.server._thread = threading.Thread(
            target=cls.server._server.serve_forever, daemon=True)
        cls.server._thread.start()
        cls.client = MCPClient(f"http://127.0.0.1:{actual_port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_ping(self):
        self.assertTrue(self.client.ping())

    def test_health(self):
        h = self.client.health()
        self.assertEqual(h["status"], "ok")
        self.assertEqual(h["server"], "test_osiris")

    def test_initialize(self):
        resp = self.client.initialize()
        result = resp.get("result", {})
        self.assertIn("protocolVersion", result)

    def test_list_tools(self):
        tools = self.client.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("echo", names)
        self.assertIn("add", names)

    def test_call_echo(self):
        result = self.client.call_tool("echo", {"msg": "hello"})
        self.assertEqual(result["echo"], "hello")

    def test_call_add(self):
        result = self.client.call_tool("add", {"a": 3, "b": 7})
        self.assertEqual(result["sum"], 10)

    def test_call_unknown_tool(self):
        resp = self.client._rpc("tools/call", {"name": "nonexistent", "arguments": {}})
        self.assertIn("error", resp)

    def test_server_list_tools(self):
        self.assertIn("echo", self.server.list_tools())


# ---------------------------------------------------------------------------
# 5. FleetConsciousness
# ---------------------------------------------------------------------------
from osiris.crsm.fleet_consciousness import FleetConsciousness, FleetState


class TestFleetConsciousness(unittest.TestCase):

    def _make_fleet(self, n=5):
        import random
        fleet = FleetConsciousness()
        for i in range(n):
            genes = [Gene(name=f"g{j}", expression=random.uniform(0.3, 0.9))
                     for j in range(5)]
            org = Organism(name=f"org_{i}", genome=Genome(genes))
            fleet.add(org)
        return fleet

    def test_add_remove(self):
        fleet = FleetConsciousness()
        org = Organism(name="alpha", genome=Genome([Gene("x", 0.5)]))
        fleet.add(org)
        self.assertEqual(fleet.size, 1)
        removed = fleet.remove("alpha")
        self.assertIsNotNone(removed)
        self.assertEqual(fleet.size, 0)

    def test_pulse(self):
        fleet = self._make_fleet(5)
        state = fleet.pulse()
        self.assertEqual(state.tick, 1)
        self.assertGreater(state.phi_fleet, 0)

    def test_run(self):
        fleet = self._make_fleet(5)
        history = fleet.run(ticks=5, verbose=False)
        self.assertEqual(len(history), 5)
        self.assertEqual(fleet.tick, 5)

    def test_merge_genomes(self):
        fleet = self._make_fleet(5)
        child = fleet.merge_genomes("org_0", "org_1")
        self.assertIsNotNone(child)
        self.assertEqual(fleet.size, 6)  # 5 + merged child

    def test_broadcast_gene(self):
        fleet = self._make_fleet(3)
        new_gene = Gene(name="broadcast_test", expression=0.9)
        fleet.broadcast_gene(new_gene)
        for org in fleet.organisms:
            gene_names = [g.name for g in org.genome]
            self.assertIn("broadcast_test", gene_names)

    def test_rank(self):
        fleet = self._make_fleet(5)
        ranked = fleet.rank()
        fitnesses = [o.genome.fitness() for o in ranked]
        self.assertEqual(fitnesses, sorted(fitnesses, reverse=True))

    def test_prune(self):
        fleet = self._make_fleet(10)
        pruned = fleet.prune(keep=5)
        self.assertEqual(pruned, 5)
        self.assertEqual(fleet.size, 5)

    def test_summary(self):
        fleet = self._make_fleet(5)
        fleet.run(ticks=2, verbose=False)
        s = fleet.summary()
        self.assertIn("phi_fleet", s)
        self.assertIn("chronos_chain_valid", s)
        self.assertTrue(s["chronos_chain_valid"])

    def test_save(self):
        fleet = self._make_fleet(3)
        fleet.run(ticks=2, verbose=False)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            fleet.save(path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("summary", data)
            self.assertIn("organisms", data)
        finally:
            os.unlink(path)

    def test_fleet_state_to_dict(self):
        fleet = self._make_fleet(3)
        state = FleetState(1, fleet.organisms)
        d = state.to_dict()
        self.assertIn("phi_fleet", d)
        self.assertIn("gamma_fleet", d)
        self.assertIn("xi_fleet", d)


if __name__ == "__main__":
    unittest.main()
