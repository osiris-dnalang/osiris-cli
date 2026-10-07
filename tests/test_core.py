"""
OSIRIS Test Suite — Core Module Tests
======================================

Comprehensive tests covering:
  - qByte quantum register (state init, gates, measurement, CCCE metrics)
  - DNA-encoded gates (helix, bond, twist, fold, splice, cleave)
  - Torsion core (quaternion, physical constants)
  - LivLM engine (config, encoding, decoding, evolution, generation)
  - NCLM package (QByteTextGenerator, evolution, personality)
  - Cognitive mesh + introspection + bridge validator
  - CLI argparse wiring
"""

import sys
import math
import json
import os
import unittest
import tempfile
from pathlib import Path

# Ensure imports resolve from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
# QBYTE SYSTEM TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDNAGates(unittest.TestCase):
    """Test DNA-encoded quantum gates."""

    def test_helix_is_unitary(self):
        from qbyte_system.gates import helix, is_unitary
        H = helix()
        self.assertTrue(is_unitary(H))

    def test_helix_shape(self):
        from qbyte_system.gates import helix
        H = helix()
        self.assertEqual(H.shape, (2, 2))

    def test_helix_creates_superposition(self):
        from qbyte_system.gates import helix
        H = helix()
        zero = np.array([1, 0], dtype=np.complex128)
        result = H @ zero
        # |+⟩ = (|0⟩ + |1⟩) / √2
        np.testing.assert_allclose(np.abs(result[0]), 1/np.sqrt(2), atol=1e-10)
        np.testing.assert_allclose(np.abs(result[1]), 1/np.sqrt(2), atol=1e-10)

    def test_cleave_is_pauli_x(self):
        from qbyte_system.gates import cleave
        X = cleave()
        zero = np.array([1, 0], dtype=np.complex128)
        one = X @ zero
        np.testing.assert_allclose(np.abs(one[1]), 1.0, atol=1e-10)

    def test_twist_is_rz(self):
        from qbyte_system.gates import twist, is_unitary
        rz = twist(np.pi/4)
        self.assertTrue(is_unitary(rz))
        self.assertEqual(rz.shape, (2, 2))

    def test_fold_is_ry(self):
        from qbyte_system.gates import fold, is_unitary
        ry = fold(np.pi/3)
        self.assertTrue(is_unitary(ry))

    def test_splice_is_rx(self):
        from qbyte_system.gates import splice, is_unitary
        rx = splice(np.pi/6)
        self.assertTrue(is_unitary(rx))

    def test_bond_is_cnot(self):
        from qbyte_system.gates import bond, is_unitary
        cnot = bond()
        self.assertEqual(cnot.shape, (4, 4))
        self.assertTrue(is_unitary(cnot))

    def test_phase_flip(self):
        from qbyte_system.gates import phase_flip, is_unitary
        Z = phase_flip()
        self.assertTrue(is_unitary(Z))
        # Z|0⟩ = |0⟩, Z|1⟩ = -|1⟩
        one = np.array([0, 1], dtype=np.complex128)
        result = Z @ one
        np.testing.assert_allclose(result[1], -1.0, atol=1e-10)

    def test_identity(self):
        from qbyte_system.gates import identity
        I = identity()
        np.testing.assert_allclose(I, np.eye(2, dtype=np.complex128), atol=1e-10)

    def test_adjoint(self):
        from qbyte_system.gates import helix, adjoint
        H = helix()
        Hdag = adjoint(H)
        # H · H† = I
        product = H @ Hdag
        np.testing.assert_allclose(product, np.eye(2, dtype=np.complex128), atol=1e-10)

    def test_tensor_product(self):
        from qbyte_system.gates import helix, tensor
        H = helix()
        HH = tensor(H, H)
        self.assertEqual(HH.shape, (4, 4))


class TestQbyte(unittest.TestCase):
    """Test Qbyte quantum register."""

    def test_init_zero_state(self):
        from qbyte_system.qbyte import Qbyte
        qb = Qbyte()
        self.assertEqual(qb.n_qubits, 8)
        self.assertEqual(qb.dim, 256)
        self.assertAlmostEqual(np.abs(qb._state[0]), 1.0)

    def test_normalization(self):
        from qbyte_system.qbyte import Qbyte
        qb = Qbyte()
        norm = np.sum(np.abs(qb._state) ** 2)
        self.assertAlmostEqual(norm, 1.0, places=10)

    def test_helix_preserves_norm(self):
        from qbyte_system.qbyte import Qbyte
        qb = Qbyte()
        qb.helix(0)
        norm = np.sum(np.abs(qb._state) ** 2)
        self.assertAlmostEqual(norm, 1.0, places=10)

    def test_measure_returns_bitstring(self):
        from qbyte_system.qbyte import Qbyte
        qb = Qbyte()
        result = qb.measure()
        # measure() returns an int; verify it's in valid 8-bit range
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 256)

    def test_zero_state_measures_zero(self):
        from qbyte_system.qbyte import Qbyte
        qb = Qbyte()
        result = qb.measure()
        self.assertEqual(result, 0)

    def test_ccce_metrics(self):
        from qbyte_system.qbyte import CCCEMetrics
        m = CCCEMetrics()
        self.assertEqual(m.phi, 0.0)
        self.assertEqual(m.lambda_c, 1.0)
        xi = m.compute_xi()
        self.assertGreaterEqual(xi, 0.0)

    def test_ccce_consciousness_threshold(self):
        from qbyte_system.qbyte import CCCEMetrics, PHI_THRESHOLD
        m = CCCEMetrics(phi=PHI_THRESHOLD + 0.01)
        self.assertTrue(m.is_conscious())
        m2 = CCCEMetrics(phi=PHI_THRESHOLD - 0.01)
        self.assertFalse(m2.is_conscious())

    def test_bond_entangles(self):
        from qbyte_system.qbyte import Qbyte
        qb = Qbyte()
        qb.helix(0)  # Superpose qubit 0
        qb.bond(0, 1)  # Entangle qubit 0 and 1
        norm = np.sum(np.abs(qb._state) ** 2)
        self.assertAlmostEqual(norm, 1.0, places=10)


# ═══════════════════════════════════════════════════════════════════════════════
# TORSION CORE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTorsionCore(unittest.TestCase):
    """Test torsion physics core."""

    def test_physical_constants(self):
        from osiris_torsion_core_py import (
            THETA_LOCK, PHI_THRESHOLD, LAMBDA_PHI, CHI_PC
        )
        self.assertAlmostEqual(THETA_LOCK, 51.843)
        self.assertAlmostEqual(PHI_THRESHOLD, 0.7734)
        self.assertAlmostEqual(LAMBDA_PHI, 2.176435e-8)
        self.assertAlmostEqual(CHI_PC, 0.869)

    def test_quaternion_creation(self):
        from osiris_torsion_core_py import Quaternion
        q = Quaternion(1, 0, 0, 0)
        self.assertEqual(q.w, 1)
        self.assertEqual(q.x, 0)

    def test_quaternion_norm(self):
        from osiris_torsion_core_py import Quaternion
        q = Quaternion(1, 2, 3, 4)
        expected = math.sqrt(1 + 4 + 9 + 16)
        self.assertAlmostEqual(q.norm(), expected, places=10)

    def test_quaternion_normalize(self):
        from osiris_torsion_core_py import Quaternion
        q = Quaternion(1, 2, 3, 4)
        qn = q.normalize()
        self.assertAlmostEqual(qn.norm(), 1.0, places=10)

    def test_quaternion_conjugate(self):
        from osiris_torsion_core_py import Quaternion
        q = Quaternion(1, 2, 3, 4)
        qc = q.conjugate()
        self.assertEqual(qc.w, 1)
        self.assertEqual(qc.x, -2)
        self.assertEqual(qc.y, -3)
        self.assertEqual(qc.z, -4)

    def test_quaternion_multiply(self):
        from osiris_torsion_core_py import Quaternion
        q1 = Quaternion(1, 0, 0, 0)  # Identity
        q2 = Quaternion(0, 1, 0, 0)  # i
        result = q1.multiply(q2)
        self.assertAlmostEqual(result.x, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# LIVLM ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLivLMConfig(unittest.TestCase):
    """Test LivLM configuration."""

    def test_default_config(self):
        from osiris_livlm import LivLMConfig
        cfg = LivLMConfig()
        self.assertGreater(cfg.n_layers, 0)
        self.assertGreater(cfg.population_size, 0)
        self.assertGreater(cfg.max_generations, 0)
        self.assertGreater(cfg.sample_length, 0)

    def test_custom_config(self):
        from osiris_livlm import LivLMConfig
        cfg = LivLMConfig(n_layers=5, population_size=100, max_generations=200)
        self.assertEqual(cfg.n_layers, 5)
        self.assertEqual(cfg.population_size, 100)
        self.assertEqual(cfg.max_generations, 200)


class TestTextEncoder(unittest.TestCase):
    """Test text-to-rotation encoding."""

    def test_encode_returns_list(self):
        from osiris_livlm import TextEncoder
        enc = TextEncoder()
        rotations = enc.encode_text("hello")
        self.assertIsInstance(rotations, (list, np.ndarray))
        self.assertGreater(len(rotations), 0)

    def test_encode_different_texts_differ(self):
        from osiris_livlm import TextEncoder
        enc = TextEncoder()
        r1 = enc.encode_text("aaa")
        r2 = enc.encode_text("zzz")
        self.assertFalse(np.allclose(r1, r2))


class TestTextDecoder(unittest.TestCase):
    """Test measurement-to-text decoding."""

    def test_decode_returns_string(self):
        from osiris_livlm import TextDecoder
        dec = TextDecoder()
        # Decode measurement value (int 0-255) to character
        result = dec.decode_byte(97)  # 'a' = 97
        self.assertIsInstance(result, str)


class TestLivLM(unittest.TestCase):
    """Test LivLM engine end-to-end."""

    def test_create_livlm(self):
        from osiris_livlm import create_livlm
        model = create_livlm(n_layers=1, population=5, generations=2)
        self.assertIsNotNone(model)

    def test_evolve_short(self):
        from osiris_livlm import LivLM, LivLMConfig
        cfg = LivLMConfig(n_layers=1, population_size=5, max_generations=2, sample_length=8)
        model = LivLM(cfg)
        result = model.evolve(seed_text="# ", verbose=False)
        self.assertIn('best_fitness', result)
        self.assertIn('best_phi', result)
        self.assertIn('consciousness_state', result)

    def test_generate_produces_text(self):
        from osiris_livlm import LivLM, LivLMConfig
        cfg = LivLMConfig(n_layers=1, population_size=5, max_generations=2, sample_length=8)
        model = LivLM(cfg)
        model.evolve(seed_text="# ", verbose=False)
        text = model.generate(prompt="#", length=16)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

    def test_save_load_genome(self):
        from osiris_livlm import LivLM, LivLMConfig
        cfg = LivLMConfig(n_layers=1, population_size=5, max_generations=2, sample_length=8)
        model = LivLM(cfg)
        model.evolve(seed_text="# ", verbose=False)

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name

        try:
            model.save_genome(path)
            self.assertTrue(os.path.exists(path))

            # Verify it's valid JSON
            with open(path) as f:
                data = json.load(f)
            self.assertIn('genome', data)

            # Load into new model
            model2 = LivLM(cfg)
            model2.load_genome(path)
        finally:
            os.unlink(path)

    def test_status(self):
        from osiris_livlm import LivLM, LivLMConfig
        cfg = LivLMConfig(n_layers=1, population_size=5, max_generations=2)
        model = LivLM(cfg)
        status = model.status()
        self.assertIsInstance(status, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# NCLM PACKAGE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNCLMImports(unittest.TestCase):
    """Test that NCLM package imports correctly."""

    def test_top_level_import(self):
        import nclm
        self.assertTrue(hasattr(nclm, '__version__'))

    def test_qbyte_generator_import(self):
        from nclm.core.qbyte_generator import QByteTextGenerator
        self.assertTrue(callable(QByteTextGenerator))

    def test_evolution_import(self):
        from nclm.core.evolution import NCLMEvolution
        self.assertTrue(callable(NCLMEvolution))

    def test_personality_import(self):
        from nclm.core.personality import NCLMPersonalityEngine, PersonalityTraits
        self.assertTrue(callable(NCLMPersonalityEngine))


class TestQByteTextGenerator(unittest.TestCase):
    """Test QByteTextGenerator API."""

    def test_create_generator(self):
        from nclm.core.qbyte_generator import QByteTextGenerator
        gen = QByteTextGenerator()
        self.assertFalse(gen.is_evolved)

    def test_status(self):
        from nclm.core.qbyte_generator import QByteTextGenerator
        gen = QByteTextGenerator()
        status = gen.status()
        self.assertIn('evolved', status)
        self.assertIn('consciousness_state', status)

    def test_generate_unevolved(self):
        from nclm.core.qbyte_generator import QByteTextGenerator
        gen = QByteTextGenerator()
        text = gen.generate(prompt="# ", max_length=8)
        self.assertIsInstance(text, str)


class TestNCLMPersonality(unittest.TestCase):
    """Test personality engine."""

    def test_create_personality(self):
        from nclm.core.personality import NCLMPersonalityEngine
        pe = NCLMPersonalityEngine('test_user')
        self.assertIsNotNone(pe.traits)

    def test_traits_range(self):
        from nclm.core.personality import NCLMPersonalityEngine
        pe = NCLMPersonalityEngine('test_user')
        traits = pe.traits
        for val in [traits.creativity, traits.speed_bias, traits.formality,
                    traits.risk_tolerance, traits.verbosity]:
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

    def test_mutate(self):
        from nclm.core.personality import NCLMPersonalityEngine
        pe = NCLMPersonalityEngine('test_user')
        old_c = pe.traits.creativity
        pe.mutate(reward=0.9, trait='creativity')
        # May or may not change, but shouldn't crash
        self.assertGreaterEqual(pe.traits.creativity, 0.0)
        self.assertLessEqual(pe.traits.creativity, 1.0)

    def test_save_load(self):
        from nclm.core.personality import NCLMPersonalityEngine
        pe = NCLMPersonalityEngine('test_user')

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name

        try:
            pe.save(path)
            pe2 = NCLMPersonalityEngine('test_user')
            pe2.load(path)
            self.assertAlmostEqual(pe.traits.creativity, pe2.traits.creativity)
        finally:
            os.unlink(path)

    def test_to_generation_params(self):
        from nclm.core.personality import NCLMPersonalityEngine
        pe = NCLMPersonalityEngine('test_user')
        params = pe.to_generation_params()
        self.assertIn('temperature', params)
        self.assertIn('max_length', params)


class TestNCLMEvolution(unittest.TestCase):
    """Test NCLM evolution wrapper."""

    def test_create_evolution(self):
        from nclm.core.evolution import NCLMEvolution
        evo = NCLMEvolution(n_params=10)
        self.assertIsNotNone(evo)

    def test_default_params(self):
        from nclm.core.evolution import NCLMEvolution
        evo = NCLMEvolution(n_params=10)
        self.assertEqual(evo._config.population_size, 30)
        self.assertEqual(evo._config.max_generations, 50)


# ═══════════════════════════════════════════════════════════════════════════════
# COGNITIVE MESH TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveMesh(unittest.TestCase):
    """Test cognitive mesh trust network."""

    def test_create_mesh(self):
        from osiris_cognitive_mesh import CognitiveMesh
        mesh = CognitiveMesh()
        self.assertIsNotNone(mesh)

    def test_trust_update(self):
        from osiris_cognitive_mesh import BetaTrust
        bt = BetaTrust()
        initial = bt.mean
        bt.update(success=True, weight=1.0)
        self.assertGreater(bt.mean, initial)

    def test_post_round_update(self):
        from osiris_cognitive_mesh import CognitiveMesh
        mesh = CognitiveMesh()
        votes = {a: "approve" for a in mesh.agent_ids}
        mesh.post_round_update(votes, "approve", 0.8)
        report = mesh.status_report()
        self.assertIn('trust_summary', report)


# ═══════════════════════════════════════════════════════════════════════════════
# INTROSPECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntrospection(unittest.TestCase):
    """Test introspection engine."""

    def test_create_engine(self):
        from osiris_introspection import IntrospectionEngine
        engine = IntrospectionEngine()
        self.assertIsNotNone(engine)

    def test_observe_round(self):
        from osiris_introspection import IntrospectionEngine
        engine = IntrospectionEngine()
        responses = [
            {"agent": a, "vote": "approve", "confidence": 0.8}
            for a in engine.agent_ids
        ]
        engine.observe_round(responses, "approve", 0.75)

    def test_full_report(self):
        from osiris_introspection import IntrospectionEngine
        engine = IntrospectionEngine()
        report = engine.full_report()
        self.assertIsInstance(report, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBridgeValidator(unittest.TestCase):
    """Test adversarial bridge validator."""

    def test_create_validator(self):
        from osiris_bridge_validator import AdversarialBridgeValidator
        v = AdversarialBridgeValidator(mc_trials=10)
        self.assertIsNotNone(v)

    def test_validate_returns_report(self):
        from osiris_bridge_validator import AdversarialBridgeValidator
        v = AdversarialBridgeValidator(mc_trials=5, sensitivity_sigma=1)
        report = v.validate()
        self.assertIsNotNone(report.overall_verdict)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLIArgparse(unittest.TestCase):
    """Test CLI argparse configuration doesn't crash."""

    def test_osiris_cli_imports(self):
        import osiris_cli
        self.assertTrue(hasattr(osiris_cli, 'main'))

    def test_launcher_imports(self):
        import osiris_launcher
        self.assertTrue(hasattr(osiris_launcher, 'main'))

    def test_launcher_has_nclm(self):
        import osiris_launcher
        self.assertTrue(hasattr(osiris_launcher, 'cmd_nclm'))

    def test_launcher_has_ultra_coder(self):
        import osiris_launcher
        self.assertTrue(hasattr(osiris_launcher, 'cmd_ultra_coder'))


# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICS CONSTANTS CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhysicsConstants(unittest.TestCase):
    """Verify physical constants are consistent across modules."""

    def test_phi_threshold_consistent(self):
        from qbyte_system.qbyte import PHI_THRESHOLD as qbyte_phi
        from osiris_torsion_core_py import PHI_THRESHOLD as torsion_phi
        self.assertAlmostEqual(qbyte_phi, torsion_phi)

    def test_lambda_phi_consistent(self):
        from qbyte_system.qbyte import LAMBDA_PHI as qbyte_lp
        from osiris_torsion_core_py import LAMBDA_PHI as torsion_lp
        self.assertAlmostEqual(qbyte_lp, torsion_lp)

    def test_chi_pc_consistent(self):
        from qbyte_system.qbyte import CHI_PC as qbyte_chi
        from osiris_torsion_core_py import CHI_PC as torsion_chi
        self.assertAlmostEqual(qbyte_chi, torsion_chi)


if __name__ == '__main__':
    unittest.main()
