"""Tests for osiris.lab, osiris.organisms, osiris.sovereign."""
import pytest


# ===========================================================================
# LAB
# ===========================================================================

class TestExperimentRegistry:
    def test_import(self):
        from osiris.lab import (
            ExperimentRegistry, ExperimentRecord,
            ExperimentType, ExperimentStatus, ResultRecord,
        )
        assert ExperimentRegistry is not None

    def test_experiment_type_enum(self):
        from osiris.lab import ExperimentType
        types = list(ExperimentType)
        assert len(types) >= 2

    def test_experiment_status_enum(self):
        from osiris.lab import ExperimentStatus
        statuses = list(ExperimentStatus)
        assert len(statuses) >= 2

    def test_registry_instantiation(self):
        from osiris.lab import ExperimentRegistry
        reg = ExperimentRegistry()
        assert reg is not None


class TestLabScanner:
    def test_import(self):
        from osiris.lab import LabScanner
        assert LabScanner is not None

    def test_instantiation(self):
        from osiris.lab import LabScanner
        scanner = LabScanner()
        assert scanner is not None


class TestExperimentDesigner:
    def test_import(self):
        from osiris.lab import ExperimentDesigner, ExperimentTemplate
        assert ExperimentDesigner is not None

    def test_instantiation(self):
        from osiris.lab import ExperimentDesigner
        designer = ExperimentDesigner()
        assert designer is not None


class TestLabExecutor:
    def test_import(self):
        from osiris.lab import LabExecutor
        assert LabExecutor is not None

    def test_instantiation(self):
        from osiris.lab import LabExecutor
        executor = LabExecutor()
        assert executor is not None


# ===========================================================================
# ORGANISMS
# ===========================================================================

class TestGene:
    def test_import(self):
        from osiris.organisms import Gene
        assert Gene is not None

    def test_creation(self):
        from osiris.organisms import Gene
        gene = Gene(name="G0", expression=0.7)
        assert gene.name == "G0"

    def test_activate(self):
        from osiris.organisms import Gene
        gene = Gene(name="G0", expression=0.7)
        result = gene.express(context={"phi": 0.8})
        # express returns expression value when no action callable
        assert result is not None


class TestGenome:
    def test_import(self):
        from osiris.organisms import Genome
        assert Genome is not None

    def test_creation(self):
        from osiris.organisms import Genome, Gene
        genes = [
            Gene(name="G0", expression=0.7),
            Gene(name="G1", expression=0.5),
        ]
        genome = Genome(genes=genes)
        assert len(genome.genes) == 2

    def test_express(self):
        from osiris.organisms import Genome, Gene
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        result = genome.express(context={"phi": 0.8})
        assert result is not None

    def test_mutate(self):
        from osiris.organisms import Genome, Gene
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        genome.mutate(rate=0.1)
        assert genome is not None


class TestOrganism:
    def test_import(self):
        from osiris.organisms import Organism
        assert Organism is not None

    def test_creation(self):
        from osiris.organisms import Organism, Genome, Gene
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org = Organism(name="alpha", genome=genome, domain="physics", purpose="research")
        assert org.name == "alpha"

    def test_phi_property(self):
        from osiris.organisms import Organism, Genome, Gene
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org = Organism(name="beta", genome=genome, domain="quantum", purpose="test")
        assert isinstance(org.phi, (int, float))

    def test_evolve(self):
        from osiris.organisms import Organism, Genome, Gene
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org = Organism(name="gamma", genome=genome, domain="quantum", purpose="test")
        org.evolve(rate=0.1)
        assert org is not None

    def test_to_dict(self):
        from osiris.organisms import Organism, Genome, Gene
        genes = [Gene(name="G0", expression=0.7)]
        genome = Genome(genes=genes)
        org = Organism(name="delta", genome=genome, domain="quantum", purpose="test")
        d = org.to_dict()
        assert isinstance(d, dict)
        assert "name" in d


class TestEvolutionEngine:
    def test_import(self):
        from osiris.organisms import EvolutionEngine
        assert EvolutionEngine is not None

    def test_instantiation(self):
        from osiris.organisms import EvolutionEngine
        engine = EvolutionEngine()
        assert engine is not None


# ===========================================================================
# SOVEREIGN
# ===========================================================================

class TestSovereignAgent:
    def test_import(self):
        from osiris.sovereign import SovereignAgent, AgentResult
        assert SovereignAgent is not None

    def test_instantiation(self):
        from osiris.sovereign import SovereignAgent
        agent = SovereignAgent()
        assert agent is not None


class TestQuantumEngine:
    def test_import(self):
        from osiris.sovereign import AeternaPorta, LambdaPhiEngine, QuantumMetrics
        assert AeternaPorta is not None

    def test_aeterna_porta(self):
        from osiris.sovereign import AeternaPorta
        porta = AeternaPorta()
        assert porta is not None

    def test_lambda_phi_engine(self):
        from osiris.sovereign import LambdaPhiEngine
        engine = LambdaPhiEngine()
        assert engine is not None

    def test_quantum_metrics(self):
        from osiris.sovereign import QuantumMetrics
        metrics = QuantumMetrics(
            phi=0.8, gamma=0.1, ccce=0.5, chi_pc=0.95,
            backend="mock", qubits=5, shots=1024,
            execution_time_s=1.0, success=True,
        )
        assert metrics.phi == 0.8
        assert metrics.success is True

    def test_sovereign_constants(self):
        from osiris.sovereign import (
            LAMBDA_PHI_M, THETA_LOCK_DEG,
            PHI_THRESHOLD_FIDELITY, GAMMA_CRITICAL_RATE, CHI_PC_QUALITY,
        )
        assert abs(THETA_LOCK_DEG - 51.843) < 0.01
        assert abs(PHI_THRESHOLD_FIDELITY - 0.7734) < 0.001


class TestCodeGenerator:
    def test_import(self):
        from osiris.sovereign import QuantumNLPCodeGenerator, CodeIntent
        assert QuantumNLPCodeGenerator is not None

    def test_code_intent(self):
        from osiris.sovereign import CodeIntent
        intent = CodeIntent.QUANTUM_CIRCUIT
        assert intent.value == "quantum_circuit"

    def test_generator_instantiation(self):
        from osiris.sovereign import QuantumNLPCodeGenerator
        gen = QuantumNLPCodeGenerator()
        assert gen is not None


class TestDevTools:
    def test_import(self):
        from osiris.sovereign import DeveloperTools, FileSearchResult, CodeAnalysisResult
        assert DeveloperTools is not None

    def test_instantiation(self):
        from osiris.sovereign import DeveloperTools
        tools = DeveloperTools()
        assert tools is not None

    def test_get_enhanced_agent(self):
        from osiris.sovereign import get_enhanced_agent
        agent = get_enhanced_agent()
        assert agent is not None
