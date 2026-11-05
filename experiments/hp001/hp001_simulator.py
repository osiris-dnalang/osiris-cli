"""
OSIRIS-HP-001: Hayden-Preskill Quantum Information Recovery Simulator
====================================================================
Standard: Gate 0 / SYS-021 Verification Suite
Substrate: Exact Statevector / Density Matrix Linear Algebra (NumPy/SciPy)

Registers (Canonical Hayden-Preskill Architecture):
  R  : Reference qubit (1 qubit, index 0) - entangled with message M in |Phi+>_RM
  M  : Message qubit   (1 qubit, index 1) - input state scrambled into black hole
  B  : Black hole      (2 qubits, indices 2, 3) - initially entangled with early radiation E
  E  : Early radiation (2 qubits, indices 4, 5) - collected prior to message injection
  Partition of scrambled output:
    C : Inaccessible remnant (2 qubits) - remains in black hole
    D : Accessible late radiation (1 qubit) - emitted after scrambling

Decoder Access:
  Arm A : Full access (C + D) -> Inverse U^dagger achieves F_rec = 1.000000 (control)
  Arm B : Restricted access:
          - Early Radiation Entangled: Decoder has (D, E) -> Recovers message (F_rec > 0.50)
          - Control (No Early Radiation): Decoder has only D -> Information trapped (F_rec <= 0.50)
  Arm C : Noise Sensitivity: Calibrated noise applied on radiation channels prior to Petz decoding.
"""

from __future__ import annotations
import numpy as np
from typing import Tuple, Dict, Any, Optional, List

# Standard single-qubit matrices
I2 = np.eye(2, dtype=np.complex128)
X2 = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Y2 = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
Z2 = np.array([[1, 0], [0, -1]], dtype=np.complex128)

BELL_STATE = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2.0)
BELL_DM = np.outer(BELL_STATE, BELL_STATE.conj())


def tensor(*args: np.ndarray) -> np.ndarray:
    """Kronecker product over arbitrary number of tensors."""
    res = args[0]
    for m in args[1:]:
        res = np.kron(res, m)
    return res


def random_unitary(dim: int, seed: Optional[int] = None) -> np.ndarray:
    """Haar-random unitary generated via Gaussian QR decomposition."""
    rng = np.random.default_rng(seed)
    Z = rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))
    Q, R = np.linalg.qr(Z)
    d = np.diagonal(R)
    ph = d / np.abs(d)
    return Q * ph


class HaydenPreskillSimulator:
    """
    Exact linear-algebra simulator for the Hayden-Preskill recovery protocol.
    """
    def __init__(self, scrambler_u: Optional[np.ndarray] = None, seed: Optional[int] = None):
        """
        Scrambler U acts on (M, B1, B2) -> (C1, C2, D), a 3-qubit (8x8) unitary.
        If None, generates Haar-random 8x8 unitary.
        """
        if scrambler_u is not None:
            assert scrambler_u.shape == (8, 8), "Scrambler U must be an 8x8 unitary"
            assert np.allclose(scrambler_u @ scrambler_u.conj().T, np.eye(8)), "U must be unitary"
            self.U = scrambler_u
        else:
            self.U = random_unitary(8, seed=seed)

    def prepare_initial_state(self, early_entanglement: bool = True) -> np.ndarray:
        """
        Prepares 6-qubit initial state:
          R (0), M (1), B1 (2), B2 (3), E1 (4), E2 (5)
        - |Phi+>_RM
        - If early_entanglement=True: |Phi+>_{B1 E1} tensor |Phi+>_{B2 E2}
        - If early_entanglement=False: |00>_{B1 B2} tensor |00>_{E1 E2}
        """
        ket0 = np.array([1, 0], dtype=np.complex128)
        if early_entanglement:
            # (R, M) is Bell, (B1, E1) is Bell, (B2, E2) is Bell
            psi_raw = tensor(BELL_STATE, BELL_STATE, BELL_STATE) # (R, M, B1, E1, B2, E2)
            # Permute to (R, M, B1, B2, E1, E2):
            t = psi_raw.reshape((2, 2, 2, 2, 2, 2))
            psi_ordered = np.transpose(t, (0, 1, 2, 4, 3, 5)).reshape((64,))
            return psi_ordered
        else:
            # Unentangled black hole
            return tensor(BELL_STATE, ket0, ket0, ket0, ket0)

    def apply_scrambler(self, psi_0: np.ndarray) -> np.ndarray:
        """
        Applies U on (M, B1, B2):
        Total unitary: I_R (dim 2) tensor U_{MB} (dim 8) tensor I_{E1, E2} (dim 4)
        acting on (R, M, B1, B2, E1, E2) -> outputs (R, C1, C2, D, E1, E2).
        """
        u_full = tensor(I2, self.U, np.eye(4, dtype=np.complex128))
        return u_full @ psi_0

    def simulate_arm_a_full_access(self) -> Tuple[float, np.ndarray]:
        """
        Arm A: Identity Control.
        Decoder possesses full access to (C1, C2, D) and applies U^dagger.
        Must recover message M with unit fidelity (F = 1.000000).
        """
        psi_0 = self.prepare_initial_state(early_entanglement=True)
        psi_1 = self.apply_scrambler(psi_0)
        
        # Apply inverse U^dagger on (C1, C2, D):
        u_inv_full = tensor(I2, self.U.conj().T, np.eye(4, dtype=np.complex128))
        psi_rec = u_inv_full @ psi_1
        
        # Reduced state on (R, M) (indices 0 and 1):
        t = psi_rec.reshape((2, 2, 16)) # (R, M, rest)
        rho_rm = np.einsum('rma, sna -> rmsn', t, t.conj()).reshape((4, 4))
        fidelity = float(np.real(np.trace(BELL_DM @ rho_rm)))
        return fidelity, rho_rm

    def simulate_arm_b_restricted(self, early_entanglement: bool = True) -> Tuple[float, np.ndarray, Dict[str, Any]]:
        """
        Arm B: Hayden-Preskill Restricted Recovery.
        Remnant C = (C1, C2) is completely inaccessible (traced out).
        Accessible radiation:
          - If early_entanglement=True: Decoder possesses late radiation D (1 qubit)
            AND early radiation E = (E1, E2) (2 qubits). Total radiation = 3 qubits (dim 8).
          - If early_entanglement=False: Decoder has only late radiation D (1 qubit).
        """
        psi_0 = self.prepare_initial_state(early_entanglement=early_entanglement)
        psi_1 = self.apply_scrambler(psi_0)
        
        if early_entanglement:
            # Accessible radiation: rad = (D, E1, E2) (dim 8). Remnant C = (C1, C2) (dim 4).
            t_rad = psi_1.reshape((2, 4, 8)) # M/R (2), C (4), rad (8)
            # Kraus operators A_c from M -> rad for c in 0..3:
            A_list = [np.sqrt(2.0) * t_rad[:, c, :].T for c in range(4)]
            
            # Petz recovery map:
            rho_rad = sum(A @ A.conj().T for A in A_list) / 2.0
            evals, evecs = np.linalg.eigh(rho_rad)
            inv_sqrt = np.array([1.0/np.sqrt(ev) if ev > 1e-12 else 0.0 for ev in evals])
            rho_rad_inv_half = evecs @ np.diag(inv_sqrt) @ evecs.conj().T
            
            def petz_channel(Y: np.ndarray) -> np.ndarray:
                Y_tilde = rho_rad_inv_half @ Y @ rho_rad_inv_half
                adj = sum(A.conj().T @ Y_tilde @ A for A in A_list)
                return 0.5 * adj
            
            # Compute recovered state rho_RM'
            rho_RM = np.zeros((2, 2, 2, 2), dtype=np.complex128)
            for i in range(2):
                for j in range(2):
                    E_ij = np.zeros((2, 2), dtype=np.complex128)
                    E_ij[i, j] = 1.0
                    N_ij = sum(A @ E_ij @ A.conj().T for A in A_list)
                    P_ij = petz_channel(N_ij)
                    for r in range(2):
                        for s in range(2):
                            if i == r and j == s:
                                rho_RM[r, :, s, :] += 0.5 * P_ij
            
            rho_rm_4 = rho_RM.reshape((4, 4))
            fidelity = float(np.real(np.trace(BELL_DM @ rho_rm_4)))
            
            telemetry = {
                "fidelity": fidelity,
                "accessible_qubits": 3,
                "remnant_qubits": 2,
                "entangled_witness_passed": fidelity > 0.50
            }
            return fidelity, rho_rm_4, telemetry
        else:
            # Control: Without early radiation, decoder has access only to late radiation D (1 qubit).
            # Remnant C (4) and E (4) are inaccessible.
            t = psi_1.reshape((2, 4, 2, 4)) # R (2), C (4), D (2), E (4)
            rho_rd = np.einsum('rcde, scfe -> r d s f', t, t.conj()).reshape((4, 4))
            fidelity = float(np.real(np.trace(BELL_DM @ rho_rd)))
            telemetry = {
                "fidelity": fidelity,
                "accessible_qubits": 1,
                "remnant_qubits": 2,
                "entangled_witness_passed": fidelity > 0.50
            }
            return fidelity, rho_rd, telemetry

    def simulate_arm_c_noisy(self, noise_gamma: float, noise_type: str = "depolarizing") -> Tuple[float, np.ndarray]:
        """
        Arm C: Scrambling and Recovery Under Noise.
        Applies local noise channel with parameter gamma on radiation channels (D, E1, E2)
        prior to Petz recovery decoding.
        """
        assert 0.0 <= noise_gamma <= 1.0, "Noise gamma must be in [0, 1]"
        psi_0 = self.prepare_initial_state(early_entanglement=True)
        psi_1 = self.apply_scrambler(psi_0)
        
        # Single-qubit Kraus noise operators on radiation lines
        if noise_type == "depolarizing":
            k_single = [
                np.sqrt(1.0 - 0.75 * noise_gamma) * I2,
                np.sqrt(noise_gamma / 4.0) * X2,
                np.sqrt(noise_gamma / 4.0) * Y2,
                np.sqrt(noise_gamma / 4.0) * Z2
            ]
        elif noise_type == "dephasing":
            k_single = [
                np.sqrt(1.0 - 0.5 * noise_gamma) * I2,
                np.sqrt(0.5 * noise_gamma) * Z2
            ]
        else:
            raise ValueError(f"Unknown noise type: {noise_type}")
            
        # Clean Kraus operators from M -> rad:
        t_rad = psi_1.reshape((2, 4, 8)) # (m, c, rad)
        A_clean = [np.sqrt(2.0) * t_rad[:, c, :].T for c in range(4)] # list of (8, 2)
        
        # Compose with noise on D (the emitted late radiation qubit):
        # D is qubit 0 of the 3-qubit radiation (D, E1, E2):
        # Kraus noise on radiation: K_i = k_single_i \otimes I_4
        kraus_noisy: List[np.ndarray] = []
        for K_d in k_single:
            K_rad = np.kron(K_d, np.eye(4, dtype=np.complex128)) # (8, 8)
            for A in A_clean:
                kraus_noisy.append(K_rad @ A) # (8, 2)
                
        # Petz recovery on noisy channel:
        rho_rad_noisy = sum(A @ A.conj().T for A in kraus_noisy) / 2.0
        evals, evecs = np.linalg.eigh(rho_rad_noisy)
        inv_sqrt = np.array([1.0/np.sqrt(ev) if ev > 1e-12 else 0.0 for ev in evals])
        rho_rad_inv_half = evecs @ np.diag(inv_sqrt) @ evecs.conj().T
        
        def petz_channel(Y: np.ndarray) -> np.ndarray:
            Y_tilde = rho_rad_inv_half @ Y @ rho_rad_inv_half
            adj = sum(A.conj().T @ Y_tilde @ A for A in kraus_noisy)
            return 0.5 * adj
        
        rho_RM = np.zeros((2, 2, 2, 2), dtype=np.complex128)
        for i in range(2):
            for j in range(2):
                E_ij = np.zeros((2, 2), dtype=np.complex128)
                E_ij[i, j] = 1.0
                N_ij = sum(A @ E_ij @ A.conj().T for A in kraus_noisy)
                P_ij = petz_channel(N_ij)
                for r in range(2):
                    for s in range(2):
                        if i == r and j == s:
                            rho_RM[r, :, s, :] += 0.5 * P_ij
        
        rho_rm_4 = rho_RM.reshape((4, 4))
        fidelity = float(np.real(np.trace(BELL_DM @ rho_rm_4)))
        return fidelity, rho_rm_4
