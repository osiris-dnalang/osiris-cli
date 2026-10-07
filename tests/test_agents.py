"""Tests for osiris.agents — 8 polar constellation agents + base framework."""
import pytest


# ---------------------------------------------------------------------------
# BASE AGENT FRAMEWORK
# ---------------------------------------------------------------------------

class TestBaseAgentFramework:
    def test_agent_role_enum(self):
        from osiris.agents import AgentRole
        roles = list(AgentRole)
        assert len(roles) >= 3

    def test_agent_task_creation(self):
        from osiris.agents import AgentTask
        task = AgentTask(id="t1", agent_id="aura", goal="test task", inputs={})
        assert task.status == "queued"

    def test_agent_manager_init(self):
        from osiris.agents import AgentManager
        mgr = AgentManager()
        assert mgr is not None


# ---------------------------------------------------------------------------
# AURA — Autopoietic Universally Recursive Architect
# ---------------------------------------------------------------------------

class TestAURA:
    def test_import(self):
        from osiris.agents import AURA
        assert AURA is not None

    def test_instantiation(self):
        from osiris.agents.aura import AURA
        agent = AURA()
        assert agent.role == "geometer"
        assert agent.pole == "south"

    def test_shape_manifold(self):
        from osiris.agents.aura import AURA
        from osiris.organisms import Organism, Genome, Gene
        agent = AURA()
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org = Organism(name="test", genome=genome, domain="physics", purpose="test")
        result = agent.shape_manifold(org, curvature=0.5)
        assert isinstance(result, dict)

    def test_compute_geodesic(self):
        from osiris.agents.aura import AURA
        from osiris.organisms import Organism, Genome, Gene
        agent = AURA()
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org1 = Organism(name="a", genome=genome, domain="physics", purpose="test")
        org2 = Organism(name="b", genome=genome, domain="physics", purpose="test")
        result = agent.compute_geodesic(org1, org2)
        assert isinstance(result, list)  # returns geodesic path (list of arrays)

    def test_manifold_dim(self):
        from osiris.agents.aura import AURA
        agent = AURA()
        assert isinstance(agent.manifold_dim, int)
        assert agent.manifold_dim > 0


# ---------------------------------------------------------------------------
# AIDEN — Adaptive Integrations for Defense & Engineering
# ---------------------------------------------------------------------------

class TestAIDEN:
    def test_import(self):
        from osiris.agents import AIDEN
        assert AIDEN is not None

    def test_instantiation(self):
        from osiris.agents.aiden import AIDEN
        agent = AIDEN()
        assert agent.role == "optimizer"
        assert agent.pole == "north"

    def test_optimize(self):
        from osiris.agents.aiden import AIDEN
        from osiris.agents.aura import AURA
        from osiris.organisms import Organism, Genome, Gene
        aiden = AIDEN()
        aura = AURA()
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org = Organism(name="opt", genome=genome, domain="physics", purpose="test")
        result = aiden.optimize(org, aura, target=None, iterations=3)
        assert hasattr(result, 'genome')  # returns an Organism

    def test_learning_rate(self):
        from osiris.agents.aiden import AIDEN
        agent = AIDEN()
        assert isinstance(agent.learning_rate, float)
        assert 0 < agent.learning_rate <= 1


# ---------------------------------------------------------------------------
# CHEOPS — Circuit Confidence Check Engine
# ---------------------------------------------------------------------------

class TestCHEOPS:
    def test_import(self):
        from osiris.agents import CHEOPS
        assert CHEOPS is not None

    def test_instantiation(self):
        from osiris.agents.cheops import CHEOPS
        agent = CHEOPS()
        assert agent.role == "validator"
        assert agent.pole == "center"

    def test_validate_invariants_pass(self):
        from osiris.agents.cheops import CHEOPS
        agent = CHEOPS()
        result = agent.validate_invariants(
            phi=0.8, gamma=0.2,
            lambda_phi=2.176435e-8,
            phi_threshold=0.7734,
            gamma_critical=0.3,
        )
        assert isinstance(result, dict)

    def test_bridge_cut_test(self):
        from osiris.agents.cheops import CHEOPS
        agent = CHEOPS()
        result = agent.bridge_cut_test("H q[0]; CX q[0],q[1]")
        assert isinstance(result, dict)

    def test_validation_summary(self):
        from osiris.agents.cheops import CHEOPS
        agent = CHEOPS()
        agent.validate_invariants(
            phi=0.8, gamma=0.2,
            lambda_phi=2.176435e-8,
            phi_threshold=0.7734,
            gamma_critical=0.3,
        )
        summary = agent.get_validation_summary()
        assert isinstance(summary, dict)


# ---------------------------------------------------------------------------
# CHRONOS — Temporal Lineage Scribe
# ---------------------------------------------------------------------------

class TestCHRONOS:
    def test_import(self):
        from osiris.agents import CHRONOS
        assert CHRONOS is not None

    def test_instantiation(self):
        from osiris.agents.chronos import CHRONOS
        agent = CHRONOS()
        assert agent.role == "scribe"
        assert agent.pole == "center"

    def test_record_and_verify(self):
        from osiris.agents.chronos import CHRONOS
        agent = CHRONOS()
        agent.record("creation", "test_org", {"phi": 0.8})
        valid = agent.verify_chain()
        assert valid is True

    def test_lineage(self):
        from osiris.agents.chronos import CHRONOS
        agent = CHRONOS()
        agent.record("creation", "org_alpha", {"phi": 0.8})
        agent.record("mutation", "org_alpha", {"phi": 0.85})
        lineage = agent.get_lineage("org_alpha")
        assert isinstance(lineage, list)
        assert len(lineage) == 2

    def test_telemetry_summary(self):
        from osiris.agents.chronos import CHRONOS
        agent = CHRONOS()
        agent.record("creation", "org_a", {})
        summary = agent.get_telemetry_summary()
        assert isinstance(summary, dict)


# ---------------------------------------------------------------------------
# SCIMITAR — Sentinel
# ---------------------------------------------------------------------------

class TestSCIMITAR:
    def test_import(self):
        from osiris.agents import SCIMITARSentinel, ThreatLevel, SentinelMode
        assert SCIMITARSentinel is not None

    def test_threat_level_enum(self):
        from osiris.agents.scimitar import ThreatLevel
        assert ThreatLevel.CLEAR.value is not None
        assert ThreatLevel.CRITICAL.value is not None

    def test_scan_clean(self):
        from osiris.agents.scimitar import SCIMITARSentinel
        sentinel = SCIMITARSentinel()
        result = sentinel.scan("Hello world, normal text")
        assert isinstance(result, list)

    def test_sentinel_mode(self):
        from osiris.agents.scimitar import SentinelMode
        modes = list(SentinelMode)
        assert len(modes) >= 2


# ---------------------------------------------------------------------------
# LAZARUS — Recovery Protocol
# ---------------------------------------------------------------------------

class TestLazarus:
    def test_import(self):
        from osiris.agents import LazarusProtocol, VitalSigns, RecoveryState
        assert LazarusProtocol is not None

    def test_vital_signs(self):
        from osiris.agents.lazarus import VitalSigns
        vitals = VitalSigns(phi=0.8, gamma=0.2, ccce=0.75, xi=0.6)
        assert vitals.phi == 0.8
        assert vitals.above_threshold is True
        assert vitals.is_coherent is True

    def test_vital_signs_critical(self):
        from osiris.agents.lazarus import VitalSigns
        vitals = VitalSigns(phi=0.3, gamma=0.5, ccce=0.2, xi=0.1)
        assert vitals.is_critical is True

    def test_negentropy(self):
        from osiris.agents.lazarus import VitalSigns
        vitals = VitalSigns(phi=0.8, gamma=0.1, ccce=0.75, xi=0.6)
        neg = vitals.negentropy
        assert isinstance(neg, float)
        assert neg > 0

    def test_monitor(self):
        from osiris.agents.lazarus import LazarusProtocol, VitalSigns
        proto = LazarusProtocol()
        vitals = VitalSigns(phi=0.5, gamma=0.35, ccce=0.3, xi=0.2)
        result = proto.monitor(vitals)
        assert result is not None

    def test_get_status(self):
        from osiris.agents.lazarus import LazarusProtocol
        proto = LazarusProtocol()
        status = proto.get_status()
        assert isinstance(status, dict)

    def test_recovery_state_enum(self):
        from osiris.agents.lazarus import RecoveryState
        states = list(RecoveryState)
        assert len(states) >= 4

    def test_phoenix_protocol(self):
        from osiris.agents.lazarus import PhoenixProtocol
        assert PhoenixProtocol is not None


# ---------------------------------------------------------------------------
# WORMHOLE — ER=EPR Inter-Agent Communication
# ---------------------------------------------------------------------------

class TestWormhole:
    def test_import(self):
        from osiris.agents import WormholeBridge, WormholeMessage, BridgeState
        assert WormholeBridge is not None

    def test_bridge_state_enum(self):
        from osiris.agents.wormhole import BridgeState
        assert BridgeState.DORMANT is not None
        assert BridgeState.ENTANGLED is not None
        assert BridgeState.SOVEREIGN is not None

    def test_message_creation(self):
        from osiris.agents.wormhole import WormholeMessage, MessagePriority
        msg = WormholeMessage(
            sender="aura", receiver="aiden",
            payload={"action": "optimize"},
            priority=MessagePriority.ROUTINE,
        )
        assert msg.sender == "aura"
        assert msg.receiver == "aiden"

    def test_message_sign_and_verify(self):
        from osiris.agents.wormhole import WormholeMessage, MessagePriority
        msg = WormholeMessage(
            sender="aura", receiver="aiden",
            payload={"action": "test"},
            priority=MessagePriority.SOVEREIGN,
        )
        msg.sign(chi_pc=0.946)
        assert msg.verify(chi_pc=0.946) is True

    def test_bridge_topology(self):
        from osiris.agents.wormhole import WormholeBridge
        bridge = WormholeBridge()
        topology = bridge.get_topology()
        assert isinstance(topology, dict)

    def test_bridge_send(self):
        from osiris.agents.wormhole import WormholeBridge, WormholeMessage, MessagePriority
        bridge = WormholeBridge()
        msg = bridge.send("aura", "aiden", {"data": 42}, MessagePriority.ROUTINE)
        assert isinstance(msg, WormholeMessage)
        assert msg.sender == "aura"


# ---------------------------------------------------------------------------
# SOVEREIGN PROOF
# ---------------------------------------------------------------------------

class TestSovereignProof:
    def test_import(self):
        from osiris.agents import SovereignProofGenerator, SovereigntyAttestation
        assert SovereignProofGenerator is not None
        assert SovereigntyAttestation is not None

    def test_generator_instantiation(self):
        from osiris.agents.sovereign_proof import SovereignProofGenerator
        gen = SovereignProofGenerator()
        assert gen is not None
