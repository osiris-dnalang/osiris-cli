"""
OSIRIS-HP-001: Tomographic Evaluator and Physical Witness Analyzer
===================================================================
Standard: Gate 0 / SYS-021 Verification Suite
Calculates tomographic observables (<XX>, <YY>, <ZZ>) and entanglement fidelity.
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Any

I2 = np.eye(2, dtype=np.complex128)
X2 = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Y2 = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
Z2 = np.array([[1, 0], [0, -1]], dtype=np.complex128)

BELL_STATE = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2.0)
BELL_DM = np.outer(BELL_STATE, BELL_STATE.conj())


def expectation_value(rho: np.ndarray, op: np.ndarray) -> float:
    """Computes Tr(rho @ op) and returns real part."""
    return float(np.real(np.trace(rho @ op)))


def evaluate_tomography(rho_rm: np.ndarray) -> Dict[str, Any]:
    """
    Evaluates 2-qubit state rho_rm against Pauli basis and Bell state fidelity.
    
    For |Phi+> = (|00> + |11>)/sqrt(2):
      <XX>_ideal = +1.0
      <YY>_ideal = -1.0
      <ZZ>_ideal = +1.0
      F_bell = (1 + <XX> - <YY> + <ZZ>) / 4
    """
    assert rho_rm.shape == (4, 4), "rho_rm must be 4x4 density matrix"
    
    xx_op = np.kron(X2, X2)
    yy_op = np.kron(Y2, Y2)
    zz_op = np.kron(Z2, Z2)
    
    exp_xx = expectation_value(rho_rm, xx_op)
    exp_yy = expectation_value(rho_rm, yy_op)
    exp_zz = expectation_value(rho_rm, zz_op)
    
    tomographic_fidelity = (1.0 + exp_xx - exp_yy + exp_zz) / 4.0
    direct_fidelity = float(np.real(np.trace(BELL_DM @ rho_rm)))
    
    # Entanglement witness: W = I/2 - |Phi+><Phi+|. Tr(W rho) < 0 implies genuine entanglement.
    witness_val = 0.5 - direct_fidelity
    is_entangled = bool(witness_val < 0.0)
    
    # Von Neumann entropy S(rho) = -Tr(rho log2 rho)
    eigenvalues = np.linalg.eigvalsh(rho_rm)
    pos_eig = eigenvalues[eigenvalues > 1e-15]
    entropy = float(-np.sum(pos_eig * np.log2(pos_eig))) if len(pos_eig) > 0 else 0.0
    
    return {
        "exp_xx": exp_xx,
        "exp_yy": exp_yy,
        "exp_zz": exp_zz,
        "fidelity_tomographic": tomographic_fidelity,
        "fidelity_direct": direct_fidelity,
        "witness_expectation": witness_val,
        "is_entangled": is_entangled,
        "von_neumann_entropy": entropy
    }
