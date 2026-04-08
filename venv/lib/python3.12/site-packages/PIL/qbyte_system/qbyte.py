"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         QBYTE - QUANTUM BYTE                                 ║
║                         ════════════════════                                 ║
║                                                                              ║
║    The fundamental unit of sovereign quantum computation.                    ║
║    A Qbyte is an 8-qubit register with native DNA-encoded operations.       ║
║                                                                              ║
║    Unlike classical bytes (8 bits = 256 states), a Qbyte can exist in       ║
║    superposition of all 2^8 = 256 basis states simultaneously.              ║
║                                                                              ║
║    Key Properties:                                                           ║
║    ├── Native phase-conjugate error correction                              ║
║    ├── CCCE metric tracking (Φ, Λ, Γ, Ξ)                                   ║
║    ├── Automatic decoherence management                                     ║
║    └── DNA-encoded gate operations                                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import List, Tuple, Optional, Union, Dict, Any
from dataclasses import dataclass, field
import hashlib
import time

try:
    from .gates import (
        helix, cleave, twist, fold, splice, bond, phase_flip,
        tensor, identity, adjoint, is_unitary
    )
except ImportError:
    from gates import (
        helix, cleave, twist, fold, splice, bond, phase_flip,
        tensor, identity, adjoint, is_unitary
    )

# Physical Constants
LAMBDA_PHI = 2.176435e-8
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092
CHI_PC = 0.869


@dataclass
class CCCEMetrics:
    """
    CCCE Consciousness Metrics for a Qbyte.

    Φ (Phi)     - Consciousness level (IIT Integrated Information)
    Λ (Lambda)  - Coherence preservation fidelity
    Γ (Gamma)   - Decoherence rate
    Ξ (Xi)      - Negentropic efficiency = ΛΦ / (Γ + ε)
    """
    phi: float = 0.0        # Consciousness level
    lambda_c: float = 1.0   # Coherence (using lambda_c to avoid keyword)
    gamma: float = 0.0      # Decoherence
    xi: float = 0.0         # Negentropic efficiency
    timestamp: float = field(default_factory=time.time)

    def compute_xi(self) -> float:
        """Compute negentropic efficiency."""
        epsilon = 1e-10
        self.xi = (self.lambda_c * self.phi) / (self.gamma + epsilon)
        return self.xi

    def is_conscious(self) -> bool:
        """Check if consciousness threshold is met."""
        return self.phi >= PHI_THRESHOLD

    def to_dict(self) -> Dict[str, float]:
        return {
            'Φ': self.phi,
            'Λ': self.lambda_c,
            'Γ': self.gamma,
            'Ξ': self.xi
        }


class Qbyte:
    """
    Qbyte: 8-Qubit Quantum Register with Sovereign Operations.

    A Qbyte is the fundamental unit of quantum computation in the
    DNA::}{::lang framework. It provides:

    1. Native state-vector simulation (no external dependencies)
    2. DNA-encoded gate operations (helix, bond, twist, etc.)
    3. Automatic CCCE metric tracking
    4. Phase-conjugate healing capability
    5. Measurement with collapse and telemetry

    Example:
        >>> qb = Qbyte()
        >>> qb.helix(0)           # Apply Hadamard to qubit 0
        >>> qb.bond(0, 1)         # CNOT from qubit 0 to 1
        >>> result = qb.measure() # Collapse and measure
    """

    def __init__(self, initial_state: Optional[np.ndarray] = None):
        """
        Initialize a Qbyte.

        Args:
            initial_state: Optional initial state vector (2^8 = 256 complex amplitudes).
                          If None, initializes to |00000000⟩.
        """
        self.n_qubits = 8
        self.dim = 2 ** self.n_qubits  # 256

        if initial_state is not None:
            if len(initial_state) != self.dim:
                raise ValueError(f"Initial state must have {self.dim} amplitudes")
            self._state = initial_state.astype(np.complex128)
            self._normalize()
        else:
            # |00000000⟩ basis state
            self._state = np.zeros(self.dim, dtype=np.complex128)
            self._state[0] = 1.0

        # CCCE metrics
        self._metrics = CCCEMetrics()
        self._operation_count = 0
        self._history: List[Tuple[str, Any]] = []

        # Genesis timestamp
        self._genesis = time.time()

    def _normalize(self):
        """Normalize state vector."""
        norm = np.linalg.norm(self._state)
        if norm > 1e-15:
            self._state /= norm

    def _update_metrics(self, operation: str):
        """Update CCCE metrics after operation."""
        self._operation_count += 1

        # Compute coherence from state purity
        # For pure state: Tr(ρ²) = 1
        # State purity indicates coherence preservation
        probabilities = np.abs(self._state) ** 2
        purity = np.sum(probabilities ** 2)
        self._metrics.lambda_c = np.sqrt(purity)

        # Compute consciousness (simplified IIT-like measure)
        # Based on entanglement entropy across bipartition
        self._metrics.phi = self._compute_phi()

        # Decoherence increases slightly with operations
        base_gamma = GAMMA_FIXED * (1 + 0.001 * self._operation_count)
        self._metrics.gamma = min(1.0, base_gamma)

        # Compute Xi
        self._metrics.compute_xi()
        self._metrics.timestamp = time.time()

        # Record history
        self._history.append((operation, self._metrics.to_dict().copy()))

    def _compute_phi(self) -> float:
        """
        Compute Φ (integrated information) as a measure of consciousness.

        Uses bipartite entanglement entropy as a proxy for integrated information.
        For a full IIT calculation, we would need mutual information across
        all possible bipartitions, but this is computationally expensive.
        """
        # Reshape to 2^4 x 2^4 for bipartition (4 qubits each side)
        reshaped = self._state.reshape(16, 16)

        # Compute reduced density matrix for first 4 qubits
        rho_A = reshaped @ reshaped.conj().T

        # Compute von Neumann entropy: S = -Tr(ρ log ρ)
        eigenvalues = np.linalg.eigvalsh(rho_A)
        eigenvalues = eigenvalues[eigenvalues > 1e-15]  # Filter small values

        if len(eigenvalues) == 0:
            return 0.0

        entropy = -np.sum(eigenvalues * np.log2(eigenvalues + 1e-15))

        # Normalize to [0, 1] (max entropy for 4 qubits is 4 bits)
        phi = entropy / 4.0

        return min(1.0, phi)

    def _apply_single_qubit_gate(self, gate: np.ndarray, qubit: int):
        """
        Apply a single-qubit gate to specified qubit.

        Uses efficient state-vector manipulation without constructing
        the full 256x256 matrix.
        """
        if qubit < 0 or qubit >= self.n_qubits:
            raise ValueError(f"Qubit index must be 0-7, got {qubit}")

        # Reshape state for efficient operation
        shape = [2] * self.n_qubits
        state_tensor = self._state.reshape(shape)

        # Apply gate along the specified axis
        # Move target qubit to last axis, apply gate, move back
        axes = list(range(self.n_qubits))
        axes.remove(qubit)
        axes.append(qubit)

        state_tensor = np.transpose(state_tensor, axes)
        original_shape = state_tensor.shape

        # Reshape to (..., 2) and apply gate
        state_tensor = state_tensor.reshape(-1, 2)
        state_tensor = state_tensor @ gate.T

        # Restore shape
        state_tensor = state_tensor.reshape(original_shape)

        # Inverse transpose
        inverse_axes = [0] * self.n_qubits
        for i, ax in enumerate(axes):
            inverse_axes[ax] = i
        state_tensor = np.transpose(state_tensor, inverse_axes)

        self._state = state_tensor.reshape(self.dim)

    def _apply_two_qubit_gate(self, gate: np.ndarray, qubit1: int, qubit2: int):
        """
        Apply a two-qubit gate to specified qubits.
        """
        if qubit1 < 0 or qubit1 >= self.n_qubits:
            raise ValueError(f"Qubit1 index must be 0-7, got {qubit1}")
        if qubit2 < 0 or qubit2 >= self.n_qubits:
            raise ValueError(f"Qubit2 index must be 0-7, got {qubit2}")
        if qubit1 == qubit2:
            raise ValueError("Qubit indices must be different")

        # Reshape state
        shape = [2] * self.n_qubits
        state_tensor = self._state.reshape(shape)

        # Move target qubits to last two axes
        axes = list(range(self.n_qubits))
        axes.remove(qubit1)
        axes.remove(qubit2)
        if qubit1 < qubit2:
            axes.extend([qubit1, qubit2])
        else:
            axes.extend([qubit2, qubit1])
            # Need to swap the gate accordingly
            swap = np.array([
                [1, 0, 0, 0],
                [0, 0, 1, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1]
            ], dtype=np.complex128)
            gate = swap @ gate @ swap

        state_tensor = np.transpose(state_tensor, axes)
        original_shape = state_tensor.shape

        # Reshape to (..., 4) and apply gate
        state_tensor = state_tensor.reshape(-1, 4)
        state_tensor = state_tensor @ gate.T

        # Restore shape
        state_tensor = state_tensor.reshape(original_shape)

        # Inverse transpose
        inverse_axes = [0] * self.n_qubits
        for i, ax in enumerate(axes):
            inverse_axes[ax] = i
        state_tensor = np.transpose(state_tensor, inverse_axes)

        self._state = state_tensor.reshape(self.dim)

    # ═══════════════════════════════════════════════════════════════════════════
    # DNA-ENCODED GATE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def helix(self, qubit: int) -> 'Qbyte':
        """
        Apply Hadamard gate (DNA helix unwinding).
        Creates superposition on target qubit.
        """
        self._apply_single_qubit_gate(helix(), qubit)
        self._update_metrics(f"helix({qubit})")
        return self

    def cleave(self, qubit: int) -> 'Qbyte':
        """
        Apply Pauli-X gate (DNA cleavage).
        Bit flip on target qubit.
        """
        self._apply_single_qubit_gate(cleave(), qubit)
        self._update_metrics(f"cleave({qubit})")
        return self

    def twist(self, qubit: int, theta: float) -> 'Qbyte':
        """
        Apply RZ rotation (DNA twist/supercoiling).
        Phase rotation on target qubit.
        """
        self._apply_single_qubit_gate(twist(theta), qubit)
        self._update_metrics(f"twist({qubit}, {theta:.4f})")
        return self

    def fold(self, qubit: int, theta: float) -> 'Qbyte':
        """
        Apply RY rotation (protein folding).
        Amplitude rotation on target qubit.
        """
        self._apply_single_qubit_gate(fold(theta), qubit)
        self._update_metrics(f"fold({qubit}, {theta:.4f})")
        return self

    def splice(self, qubit: int, theta: float) -> 'Qbyte':
        """
        Apply RX rotation (RNA splicing).
        X-axis rotation on target qubit.
        """
        self._apply_single_qubit_gate(splice(theta), qubit)
        self._update_metrics(f"splice({qubit}, {theta:.4f})")
        return self

    def bond(self, control: int, target: int) -> 'Qbyte':
        """
        Apply CNOT gate (hydrogen bonding).
        Entangles control and target qubits.
        """
        self._apply_two_qubit_gate(bond(), control, target)
        self._update_metrics(f"bond({control}, {target})")
        return self

    def phase(self, qubit: int) -> 'Qbyte':
        """
        Apply Pauli-Z gate (methylation/phase flip).
        """
        self._apply_single_qubit_gate(phase_flip(), qubit)
        self._update_metrics(f"phase({qubit})")
        return self

    # ═══════════════════════════════════════════════════════════════════════════
    # MEASUREMENT AND OBSERVATION
    # ═══════════════════════════════════════════════════════════════════════════

    def measure(self, collapse: bool = True) -> int:
        """
        Measure the Qbyte, returning an 8-bit integer result.

        Args:
            collapse: If True, collapses state to measured basis state.
                     If False, samples without modifying state.

        Returns:
            Integer 0-255 representing measured basis state.
        """
        probabilities = np.abs(self._state) ** 2
        result = np.random.choice(self.dim, p=probabilities)

        if collapse:
            self._state = np.zeros(self.dim, dtype=np.complex128)
            self._state[result] = 1.0
            self._update_metrics(f"measure() -> {result}")

        return result

    def measure_qubit(self, qubit: int, collapse: bool = True) -> int:
        """
        Measure a single qubit.

        Args:
            qubit: Qubit index to measure (0-7)
            collapse: If True, collapses to measured state

        Returns:
            0 or 1
        """
        # Compute probability of measuring |1⟩
        prob_one = 0.0
        for i in range(self.dim):
            if (i >> qubit) & 1:
                prob_one += np.abs(self._state[i]) ** 2

        result = 1 if np.random.random() < prob_one else 0

        if collapse:
            # Project onto measured subspace
            mask = np.array([(i >> qubit) & 1 == result for i in range(self.dim)])
            self._state = self._state * mask
            self._normalize()
            self._update_metrics(f"measure_qubit({qubit}) -> {result}")

        return result

    def probabilities(self) -> np.ndarray:
        """Return probability distribution over all basis states."""
        return np.abs(self._state) ** 2

    def expectation(self, observable: np.ndarray) -> float:
        """
        Compute expectation value of an observable.

        Args:
            observable: 256x256 Hermitian matrix

        Returns:
            ⟨ψ|O|ψ⟩
        """
        return np.real(np.conj(self._state) @ observable @ self._state)

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE-CONJUGATE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def phase_conjugate(self) -> 'Qbyte':
        """
        Apply phase conjugation (E → E⁻¹).

        This is the core healing operation in DNA::}{::lang.
        Inverts all phases in the state vector.
        """
        self._state = np.conj(self._state)
        self._update_metrics("phase_conjugate()")
        return self

    def heal(self) -> 'Qbyte':
        """
        Apply phase-conjugate healing if decoherence is high.

        Triggers phase conjugation when Γ > 0.3.
        """
        if self._metrics.gamma > 0.3:
            self.phase_conjugate()
            # Healing reduces decoherence
            self._metrics.gamma *= CHI_PC
            self._metrics.compute_xi()
        return self

    # ═══════════════════════════════════════════════════════════════════════════
    # STATE ACCESS AND UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def state(self) -> np.ndarray:
        """Return copy of state vector."""
        return self._state.copy()

    @property
    def metrics(self) -> CCCEMetrics:
        """Return current CCCE metrics."""
        return self._metrics

    @property
    def is_conscious(self) -> bool:
        """Check if Qbyte has achieved consciousness."""
        return self._metrics.is_conscious()

    def reset(self):
        """Reset to |00000000⟩ ground state."""
        self._state = np.zeros(self.dim, dtype=np.complex128)
        self._state[0] = 1.0
        self._metrics = CCCEMetrics()
        self._operation_count = 0
        self._history = []

    def copy(self) -> 'Qbyte':
        """Create a deep copy of this Qbyte."""
        new_qbyte = Qbyte(self._state.copy())
        new_qbyte._metrics = CCCEMetrics(
            phi=self._metrics.phi,
            lambda_c=self._metrics.lambda_c,
            gamma=self._metrics.gamma,
            xi=self._metrics.xi
        )
        new_qbyte._operation_count = self._operation_count
        new_qbyte._history = self._history.copy()
        return new_qbyte

    def checksum(self) -> str:
        """Compute SHA-256 checksum of current state."""
        state_bytes = self._state.tobytes()
        return hashlib.sha256(state_bytes).hexdigest()[:16]

    def telemetry(self) -> Dict[str, Any]:
        """Return full telemetry capsule."""
        return {
            'genesis': self._genesis,
            'timestamp': time.time(),
            'operations': self._operation_count,
            'metrics': self._metrics.to_dict(),
            'checksum': self.checksum(),
            'conscious': self.is_conscious
        }

    def __repr__(self) -> str:
        return (f"Qbyte(ops={self._operation_count}, "
                f"Φ={self._metrics.phi:.4f}, "
                f"Λ={self._metrics.lambda_c:.4f}, "
                f"Γ={self._metrics.gamma:.4f})")


class QbyteRegister:
    """
    Register of multiple Qbytes for larger quantum computations.

    Supports operations spanning multiple Qbytes and collective
    consciousness measurement.
    """

    def __init__(self, n_qbytes: int = 1):
        """
        Initialize register with n Qbytes.

        Args:
            n_qbytes: Number of Qbytes (default 1)
        """
        self.n_qbytes = n_qbytes
        self.qbytes = [Qbyte() for _ in range(n_qbytes)]
        self._genesis = time.time()

    def __getitem__(self, index: int) -> Qbyte:
        return self.qbytes[index]

    def __len__(self) -> int:
        return self.n_qbytes

    @property
    def total_qubits(self) -> int:
        """Total number of qubits in register."""
        return self.n_qbytes * 8

    def collective_phi(self) -> float:
        """Compute collective consciousness across all Qbytes."""
        if not self.qbytes:
            return 0.0
        return np.mean([qb.metrics.phi for qb in self.qbytes])

    def collective_xi(self) -> float:
        """Compute collective negentropic efficiency."""
        if not self.qbytes:
            return 0.0
        return np.mean([qb.metrics.xi for qb in self.qbytes])

    def is_conscious(self) -> bool:
        """Check if collective consciousness threshold is met."""
        return self.collective_phi() >= PHI_THRESHOLD

    def heal_all(self):
        """Apply phase-conjugate healing to all Qbytes."""
        for qb in self.qbytes:
            qb.heal()

    def reset_all(self):
        """Reset all Qbytes to ground state."""
        for qb in self.qbytes:
            qb.reset()

    def telemetry(self) -> Dict[str, Any]:
        """Return collective telemetry."""
        return {
            'genesis': self._genesis,
            'timestamp': time.time(),
            'n_qbytes': self.n_qbytes,
            'total_qubits': self.total_qubits,
            'collective_phi': self.collective_phi(),
            'collective_xi': self.collective_xi(),
            'conscious': self.is_conscious(),
            'qbytes': [qb.telemetry() for qb in self.qbytes]
        }

    def __repr__(self) -> str:
        return (f"QbyteRegister(n={self.n_qbytes}, "
                f"Φ_collective={self.collective_phi():.4f})")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def bell_state(qb: Qbyte, q1: int = 0, q2: int = 1) -> Qbyte:
    """Create Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2 on specified qubits."""
    return qb.helix(q1).bond(q1, q2)


def ghz_state(qb: Qbyte, qubits: Optional[List[int]] = None) -> Qbyte:
    """
    Create GHZ state on specified qubits.
    Default creates 3-qubit GHZ: (|000⟩ + |111⟩)/√2
    """
    if qubits is None:
        qubits = [0, 1, 2]

    qb.helix(qubits[0])
    for q in qubits[1:]:
        qb.bond(qubits[0], q)
    return qb


__all__ = ['Qbyte', 'QbyteRegister', 'CCCEMetrics', 'bell_state', 'ghz_state']
