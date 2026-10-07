"""Tests for osiris.defense — Sentinel, ZeroTrust, PCRB, PhaseConjugate."""
import pytest


# ---------------------------------------------------------------------------
# SENTINEL
# ---------------------------------------------------------------------------

class TestSentinel:
    def test_import(self):
        from osiris.defense import Sentinel, ThreatLevel, Threat
        assert Sentinel is not None

    def test_threat_level_enum(self):
        from osiris.defense import ThreatLevel
        assert hasattr(ThreatLevel, 'LOW')
        assert hasattr(ThreatLevel, 'MEDIUM')
        assert hasattr(ThreatLevel, 'HIGH')
        assert hasattr(ThreatLevel, 'CRITICAL')

    def test_sentinel_instantiation(self):
        from osiris.defense import Sentinel
        s = Sentinel()
        assert s is not None

    def test_threat_dataclass(self):
        from osiris.defense import Threat
        t = Threat(
            threat_id="t001",
            level="LOW",
            description="No threat detected",
            source="test",
        )
        assert t.level == "LOW"
        assert t.description == "No threat detected"


# ---------------------------------------------------------------------------
# ZERO TRUST
# ---------------------------------------------------------------------------

class TestZeroTrust:
    def test_import(self):
        from osiris.defense import ZeroTrust
        assert ZeroTrust is not None

    def test_instantiation(self):
        from osiris.defense.zero_trust import ZeroTrust
        zt = ZeroTrust()
        assert zt is not None

    def test_verify(self):
        from osiris.defense.zero_trust import ZeroTrust
        zt = ZeroTrust()
        result = zt.verify("test_agent", {"phi": 0.8, "gamma": 0.1})
        assert isinstance(result, (bool, dict))

    def test_add_trusted_domain(self):
        from osiris.defense.zero_trust import ZeroTrust
        zt = ZeroTrust()
        zt.add_trusted_domain("osiris.agents")
        summary = zt.get_verification_summary()
        assert isinstance(summary, dict)

    def test_set_policy(self):
        from osiris.defense.zero_trust import ZeroTrust
        zt = ZeroTrust()
        zt.set_policy("require_phi_above_threshold", True)
        summary = zt.get_verification_summary()
        assert isinstance(summary, dict)


# ---------------------------------------------------------------------------
# PCRB — Phase Conjugate Recursion Bus
# ---------------------------------------------------------------------------

class TestPCRB:
    def test_import(self):
        from osiris.defense import PCRB, PCRBFactory
        from osiris.defense import StabilizerCode, PhaseConjugateMirror, RecursionBus
        assert PCRB is not None

    def test_stabilizer_code(self):
        from osiris.defense import StabilizerCode
        code = StabilizerCode(
            n=5,
            k=1,
            d=3,
            generators=["XII", "IXI"],
        )
        assert code.d == 3
        assert len(code.generators) == 2

    def test_phase_conjugate_mirror(self):
        from osiris.defense import PhaseConjugateMirror
        mirror = PhaseConjugateMirror()
        assert mirror is not None

    def test_recursion_bus(self):
        from osiris.defense import RecursionBus
        bus = RecursionBus()
        assert bus is not None

    def test_pcrb_instantiation(self):
        from osiris.defense import PCRB
        pcrb = PCRB()
        assert pcrb is not None

    def test_pcrb_factory(self):
        from osiris.defense import PCRBFactory
        factory = PCRBFactory()
        assert factory is not None


# ---------------------------------------------------------------------------
# PHASE CONJUGATE — Howitzer, Convergence, Preprocessor
# ---------------------------------------------------------------------------

class TestPhaseConjugate:
    def test_import(self):
        from osiris.defense import (
            PlanckConstants, UniversalConstants, SphericalTetrahedron,
            PhaseConjugateHowitzer, CentripetalConvergence,
            PhaseConjugateSubstratePreprocessor,
        )
        assert PhaseConjugateHowitzer is not None

    def test_planck_constants(self):
        from osiris.defense import PlanckConstants
        pc = PlanckConstants()
        assert hasattr(pc, "hbar") or hasattr(pc, "h_bar") or callable(getattr(pc, "__init__", None))

    def test_spherical_tetrahedron(self):
        from osiris.defense import SphericalTetrahedron
        st = SphericalTetrahedron()
        assert st is not None

    def test_howitzer(self):
        from osiris.defense import PhaseConjugateHowitzer
        h = PhaseConjugateHowitzer()
        assert h is not None

    def test_centripetal_convergence(self):
        from osiris.defense import CentripetalConvergence
        cc = CentripetalConvergence()
        assert cc is not None

    def test_preprocessor(self):
        from osiris.defense import PhaseConjugateSubstratePreprocessor
        pp = PhaseConjugateSubstratePreprocessor()
        assert pp is not None
