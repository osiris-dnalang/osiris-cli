"""Tests for osiris.crsm — Penteract, SwarmOrchestrator, TauPhase, NonLocal."""
import pytest


# ---------------------------------------------------------------------------
# SWARM ORCHESTRATOR
# ---------------------------------------------------------------------------

class TestSwarmOrchestrator:
    def test_import(self):
        from osiris.crsm import NCLMSwarmOrchestrator, CRSMLayer, CRSMState
        from osiris.crsm import SwarmNode, NodeRole
        assert NCLMSwarmOrchestrator is not None

    def test_crsm_layer_enum(self):
        from osiris.crsm import CRSMLayer
        layers = list(CRSMLayer)
        assert len(layers) >= 2

    def test_node_role(self):
        from osiris.crsm import NodeRole
        roles = list(NodeRole) if hasattr(NodeRole, "__iter__") else [NodeRole]
        assert len(roles) >= 1

    def test_orchestrator_instantiation(self):
        from osiris.crsm import NCLMSwarmOrchestrator
        orch = NCLMSwarmOrchestrator()
        assert orch is not None

    def test_constants(self):
        from osiris.crsm import LAMBDA_PHI_M, THETA_LOCK_DEG
        from osiris.crsm import PHI_THRESHOLD, GAMMA_CRITICAL, CHI_PC_QUALITY
        assert abs(THETA_LOCK_DEG - 51.843) < 0.01
        assert abs(PHI_THRESHOLD - 0.7734) < 0.001
        assert abs(GAMMA_CRITICAL - 0.3) < 0.01


# ---------------------------------------------------------------------------
# PENTERACT — 5D Hypercube Engine
# ---------------------------------------------------------------------------

class TestPenteract:
    def test_import(self):
        from osiris.crsm import (
            OsirisPenteract, PenteractShell, PenteractState,
            PhysicsProblem, ProblemType,
        )
        assert OsirisPenteract is not None

    def test_problem_type_enum(self):
        from osiris.crsm import ProblemType
        types = list(ProblemType)
        assert len(types) >= 3

    def test_resolution_mechanism_enum(self):
        from osiris.crsm import ResolutionMechanism
        mechs = list(ResolutionMechanism)
        assert len(mechs) >= 2

    def test_penteract_shell(self):
        from osiris.crsm import PenteractShell
        shell = PenteractShell.SURFACE
        assert shell is not None
        assert shell.value == 'surface'

    def test_osiris_penteract(self):
        from osiris.crsm import OsirisPenteract
        pent = OsirisPenteract()
        assert pent is not None

    def test_physics_problem(self):
        from osiris.crsm import PhysicsProblem, ProblemType
        prob = PhysicsProblem(
            problem_id=1,
            problem_type=ProblemType(list(ProblemType)[0].value),
            description="A test physics problem",
        )
        assert prob.problem_id == 1

    def test_resolution_result(self):
        from osiris.crsm import ResolutionResult
        assert ResolutionResult is not None

    def test_aura_observer(self):
        from osiris.crsm import AURAObserver
        obs = AURAObserver()
        assert obs is not None

    def test_aiden_executor(self):
        from osiris.crsm import AIDENExecutor
        exe = AIDENExecutor()
        assert exe is not None

    def test_resolution_engine(self):
        from osiris.crsm import ResolutionEngine
        eng = ResolutionEngine()
        assert eng is not None


# ---------------------------------------------------------------------------
# TAU PHASE ANALYZER
# ---------------------------------------------------------------------------

class TestTauPhaseAnalyzer:
    def test_import(self):
        from osiris.crsm import TauPhaseAnalyzer, AnalysisResult, JobRecord, SweepPoint
        assert TauPhaseAnalyzer is not None

    def test_instantiation(self):
        from osiris.crsm import TauPhaseAnalyzer
        analyzer = TauPhaseAnalyzer()
        assert analyzer is not None

    def test_analysis_result(self):
        from osiris.crsm import AnalysisResult
        assert AnalysisResult is not None

    def test_job_record(self):
        from osiris.crsm import JobRecord
        assert JobRecord is not None

    def test_sweep_point(self):
        from osiris.crsm import SweepPoint
        assert SweepPoint is not None


# ---------------------------------------------------------------------------
# BRIDGE CLI
# ---------------------------------------------------------------------------

class TestBridgeCLI:
    def test_import(self):
        from osiris.crsm import OsirisBridgeCLI
        assert OsirisBridgeCLI is not None

    def test_instantiation(self):
        from osiris.crsm import OsirisBridgeCLI
        cli = OsirisBridgeCLI()
        assert cli is not None


# ---------------------------------------------------------------------------
# NONLOCAL AGENT (lazy import)
# ---------------------------------------------------------------------------

class TestNonLocalAgent:
    def test_lazy_import(self):
        from osiris.crsm import get_nonlocal_agent
        agent_cls = get_nonlocal_agent()
        assert agent_cls is not None
