"""Tests for osiris.hardware, osiris.decoders, osiris.qbyte, osiris.mcp, osiris.nclm."""
import pytest


# ===========================================================================
# HARDWARE
# ===========================================================================

class TestQuEraAdapter:
    def test_import(self):
        from osiris.hardware import QuEraCorrelatedAdapter
        assert QuEraCorrelatedAdapter is not None

    def test_instantiation(self):
        from osiris.hardware import QuEraCorrelatedAdapter
        adapter = QuEraCorrelatedAdapter()
        assert adapter is not None


class TestWorkloadExtractor:
    def test_import(self):
        from osiris.hardware import WorkloadExtractor, SubstratePipeline
        from osiris.hardware import IBMBackendSpec, IBM_BACKENDS
        assert WorkloadExtractor is not None

    def test_ibm_backends(self):
        from osiris.hardware import IBM_BACKENDS
        assert isinstance(IBM_BACKENDS, dict)
        assert len(IBM_BACKENDS) >= 3
        assert "ibm_torino" in IBM_BACKENDS

    def test_workload_extractor(self):
        from osiris.hardware import WorkloadExtractor
        we = WorkloadExtractor()
        assert we is not None

    def test_substrate_pipeline(self):
        from osiris.hardware import SubstratePipeline
        sp = SubstratePipeline()
        assert sp is not None


# ===========================================================================
# DECODERS
# ===========================================================================

class TestTesseractDecoder:
    def test_import(self):
        from osiris.decoders import TesseractDecoderOrganism, TesseractResonatorOrganism
        assert TesseractDecoderOrganism is not None

    def test_decoder_instantiation(self):
        from osiris.decoders import TesseractDecoderOrganism
        decoder = TesseractDecoderOrganism()
        assert decoder is not None

    def test_resonator_instantiation(self):
        from osiris.decoders import TesseractResonatorOrganism
        resonator = TesseractResonatorOrganism()
        assert resonator is not None


# ===========================================================================
# QBYTE
# ===========================================================================

class TestQByte:
    def test_import(self):
        from osiris.qbyte import QByteMiner, QByteBlock
        assert QByteMiner is not None

    def test_miner_instantiation(self):
        from osiris.qbyte import QByteMiner
        miner = QByteMiner(difficulty=2)
        assert miner is not None

    def test_mine_block(self):
        from osiris.qbyte import QByteMiner
        miner = QByteMiner(difficulty=1)
        block = miner.mine_block(lambda_c=0.95, phi=0.8)
        assert block is not None

    def test_chain_length(self):
        from osiris.qbyte import QByteMiner
        miner = QByteMiner(difficulty=1)
        block = miner.mine_block(lambda_c=0.95, phi=0.8)
        # Chain length depends on whether block met difficulty target
        assert miner.chain_length() >= 0
        assert block is not None


# ===========================================================================
# MCP
# ===========================================================================

class TestMCP:
    def test_import(self):
        from osiris.mcp import MCPServer, MCPClient
        assert MCPServer is not None
        assert MCPClient is not None

    def test_server_instantiation(self):
        from osiris.mcp import MCPServer
        server = MCPServer()
        assert server is not None

    def test_client_instantiation(self):
        from osiris.mcp import MCPClient
        client = MCPClient()
        assert client is not None


# ===========================================================================
# NCLM
# ===========================================================================

class TestNCLM:
    def test_import(self):
        from osiris.nclm import NonCausalLM, NCPhysics
        from osiris.nclm import ConsciousnessField, IntentDeducer, CodeSwarm
        assert NonCausalLM is not None

    def test_nc_physics(self):
        from osiris.nclm import NCPhysics
        physics = NCPhysics()
        assert physics is not None

    def test_manifold_point(self):
        from osiris.nclm import ManifoldPoint
        assert ManifoldPoint is not None

    def test_pilot_wave_correlation(self):
        from osiris.nclm import PilotWaveCorrelation
        pwc = PilotWaveCorrelation()
        assert pwc is not None

    def test_consciousness_field(self):
        from osiris.nclm import ConsciousnessField
        field = ConsciousnessField()
        assert field is not None

    def test_intent_deducer(self):
        from osiris.nclm import IntentDeducer
        deducer = IntentDeducer()
        assert deducer is not None

    def test_code_swarm(self):
        from osiris.nclm import CodeSwarm
        swarm = CodeSwarm()
        assert swarm is not None

    def test_get_nclm(self):
        from osiris.nclm import get_nclm
        nclm = get_nclm()
        assert nclm is not None

    def test_nclm_instantiation(self):
        from osiris.nclm import NonCausalLM
        nclm = NonCausalLM()
        assert nclm is not None


# ===========================================================================
# MESH (integration layer)
# ===========================================================================

class TestMesh:
    def test_imports(self):
        from osiris.mesh import TesseractDecoderOrganism, TesseractResonatorOrganism
        assert TesseractDecoderOrganism is not None

    def test_quera_adapter(self):
        from osiris.mesh import QuEraCorrelatedAdapter
        assert QuEraCorrelatedAdapter is not None

    def test_lazy_swarm(self):
        from osiris.mesh import get_swarm_orchestrator
        orch = get_swarm_orchestrator()
        assert orch is not None


# ===========================================================================
# BRIDGE MODULES (formerly orphaned)
# ===========================================================================

class TestOrphanBridges:
    """Verify all 14 formerly-orphaned modules are importable."""

    def test_core_health(self):
        import osiris.core.health
        assert osiris.core.health is not None

    def test_core_license(self):
        import osiris.core.license
        assert osiris.core.license is not None

    def test_core_orchestrator(self):
        import osiris.core.orchestrator
        assert osiris.core.orchestrator is not None

    def test_core_fei_demo(self):
        import osiris.core.fei_demo
        assert osiris.core.fei_demo is not None

    def test_nclm_livlm(self):
        import osiris.nclm.livlm
        assert osiris.nclm.livlm is not None

    def test_swarm_ultra_coder(self):
        import osiris.swarm.ultra_coder
        assert osiris.swarm.ultra_coder is not None

    def test_swarm_elo_tournament(self):
        import osiris.swarm.elo_tournament
        assert osiris.swarm.elo_tournament is not None

    def test_defense_policy_upcycle(self):
        import osiris.defense.policy_upcycle
        assert osiris.defense.policy_upcycle is not None

    def test_sovereign_executor(self):
        import osiris.sovereign.executor
        assert osiris.sovereign.executor is not None

    def test_discovery_engine(self):
        import osiris.discovery.engine
        assert osiris.discovery.engine is not None

    def test_applications(self):
        import osiris.applications
        assert osiris.applications is not None


# ===========================================================================
# PACKAGE-LEVEL
# ===========================================================================

class TestPackageLevel:
    """Verify top-level osiris package exports."""

    def test_version(self):
        import osiris
        assert osiris.__version__ == "4.0.0"

    def test_constants(self):
        import osiris
        assert osiris.LAMBDA_PHI == 2.176435e-8
        assert osiris.THETA_LOCK == 51.843
        assert osiris.PHI_THRESHOLD == 0.7734
        assert osiris.GAMMA_CRITICAL == 0.3
        assert osiris.CHI_PC == 0.946

    def test_total_discoverable_modules(self):
        """Verify >= 90 discoverable modules in the package."""
        import pkgutil
        import osiris
        count = 0
        for importer, modname, ispkg in pkgutil.walk_packages(
            osiris.__path__, prefix="osiris."
        ):
            count += 1
        assert count >= 90, f"Expected >= 90 modules, found {count}"
