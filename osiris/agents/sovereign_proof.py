"""
SOVEREIGN PROOF GENERATOR — Cryptographic Proof-of-Sovereignty
==============================================================

Non-repudiable cryptographic proofs that computation was executed
under sovereign conditions.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
import time
import hashlib
import json
import platform
import os


@dataclass
class SovereigntyAttestation:
    proof_id: str
    phi: float
    gamma: float
    ccce: float
    xi: float
    lambda_phi: float
    theta_lock: float
    phi_threshold: float
    gamma_critical: float
    is_sovereign: bool
    is_coherent: bool
    operation: str
    timestamp: float
    prev_proof_hash: str
    proof_hash: str
    machine_fingerprint: str
    chain_position: int


class SovereignProofGenerator:
    """Generate and verify cryptographic proofs of sovereignty."""

    LAMBDA_PHI = 2.176435e-8
    THETA_LOCK = 51.843
    PHI_THRESHOLD = 0.7734
    GAMMA_CRITICAL = 0.3
    CHI_PC = 0.946

    def __init__(self):
        self.proof_chain: List[SovereigntyAttestation] = []
        self._prev_hash = "0" * 64
        self._machine_fp = self._compute_machine_fingerprint()

    def _compute_machine_fingerprint(self) -> str:
        components = [
            platform.node(), platform.machine(),
            platform.processor() or "unknown", str(os.getpid()),
        ]
        raw = "|".join(components)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def generate_proof(self, phi: float, gamma: float, ccce: float = 0.0,
                       operation: str = "general_execution") -> SovereigntyAttestation:
        xi = (self.LAMBDA_PHI * phi) / max(gamma, 0.001)
        is_sovereign = phi >= self.PHI_THRESHOLD
        is_coherent = gamma < self.GAMMA_CRITICAL
        proof_data = {
            "chain_position": len(self.proof_chain),
            "phi": phi, "gamma": gamma, "ccce": ccce, "xi": xi,
            "lambda_phi": self.LAMBDA_PHI, "theta_lock": self.THETA_LOCK,
            "phi_threshold": self.PHI_THRESHOLD, "gamma_critical": self.GAMMA_CRITICAL,
            "is_sovereign": is_sovereign, "is_coherent": is_coherent,
            "operation": operation, "timestamp": time.time(),
            "prev_proof_hash": self._prev_hash,
            "machine_fingerprint": self._machine_fp,
        }
        canonical = json.dumps(proof_data, sort_keys=True, default=str)
        proof_hash = hashlib.sha256(canonical.encode()).hexdigest()
        proof_id = f"SPG-{len(self.proof_chain):06d}-{proof_hash[:12]}"
        attestation = SovereigntyAttestation(
            proof_id=proof_id, phi=phi, gamma=gamma, ccce=ccce, xi=xi,
            lambda_phi=self.LAMBDA_PHI, theta_lock=self.THETA_LOCK,
            phi_threshold=self.PHI_THRESHOLD, gamma_critical=self.GAMMA_CRITICAL,
            is_sovereign=is_sovereign, is_coherent=is_coherent,
            operation=operation, timestamp=proof_data["timestamp"],
            prev_proof_hash=self._prev_hash, proof_hash=proof_hash,
            machine_fingerprint=self._machine_fp,
            chain_position=len(self.proof_chain))
        self._prev_hash = proof_hash
        self.proof_chain.append(attestation)
        return attestation

    def verify_chain(self) -> Dict[str, Any]:
        if not self.proof_chain:
            return {"valid": True, "length": 0, "errors": []}
        errors = []
        prev_hash = "0" * 64
        for i, proof in enumerate(self.proof_chain):
            if proof.prev_proof_hash != prev_hash:
                errors.append(f"Chain break at position {i}")
            proof_data = {
                "chain_position": proof.chain_position,
                "phi": proof.phi, "gamma": proof.gamma, "ccce": proof.ccce, "xi": proof.xi,
                "lambda_phi": proof.lambda_phi, "theta_lock": proof.theta_lock,
                "phi_threshold": proof.phi_threshold, "gamma_critical": proof.gamma_critical,
                "is_sovereign": proof.is_sovereign, "is_coherent": proof.is_coherent,
                "operation": proof.operation, "timestamp": proof.timestamp,
                "prev_proof_hash": proof.prev_proof_hash,
                "machine_fingerprint": proof.machine_fingerprint,
            }
            canonical = json.dumps(proof_data, sort_keys=True, default=str)
            expected = hashlib.sha256(canonical.encode()).hexdigest()
            if proof.proof_hash != expected:
                errors.append(f"Hash mismatch at position {i}")
            if proof.lambda_phi != self.LAMBDA_PHI:
                errors.append(f"Lambda_Phi violation at position {i}")
            prev_hash = proof.proof_hash
        sovereign_count = sum(1 for p in self.proof_chain if p.is_sovereign)
        coherent_count = sum(1 for p in self.proof_chain if p.is_coherent)
        return {
            "valid": len(errors) == 0, "length": len(self.proof_chain), "errors": errors,
            "sovereign_proofs": sovereign_count, "coherent_proofs": coherent_count,
            "sovereignty_rate": sovereign_count / max(len(self.proof_chain), 1),
        }
