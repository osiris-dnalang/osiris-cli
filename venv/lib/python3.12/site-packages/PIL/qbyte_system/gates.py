"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              DNA-ENCODED QUANTUM GATES - SOVEREIGN IMPLEMENTATION            ║
║              ════════════════════════════════════════════════════            ║
║                                                                              ║
║    Native quantum gate implementations using DNA metaphors.                  ║
║    NO external dependencies (Qiskit, Cirq, etc.) - pure NumPy.              ║
║                                                                              ║
║    DNA Gate Mapping:                                                         ║
║    ├── helix()   → H (Hadamard)      : √NOT, superposition creation        ║
║    ├── bond()    → CNOT              : 2-qubit entanglement                 ║
║    ├── twist()   → RZ(θ)             : Phase rotation around Z             ║
║    ├── fold()    → RY(θ)             : Amplitude rotation around Y         ║
║    ├── splice()  → RX(θ)             : Rotation around X axis              ║
║    ├── unwind()  → H†                : Hadamard adjoint                    ║
║    └── cleave()  → X (NOT)           : Bit flip                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import Union, Optional
import math

# ═══════════════════════════════════════════════════════════════════════════════
# FUNDAMENTAL CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SQRT2_INV = 1.0 / np.sqrt(2)

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE-QUBIT GATES
# ═══════════════════════════════════════════════════════════════════════════════

def helix() -> np.ndarray:
    """
    Hadamard gate (H) - Creates superposition.
    DNA metaphor: DNA helix unwinding to expose bases.

    H = (1/√2) |1  1|
               |1 -1|

    Returns:
        2x2 complex matrix representing Hadamard gate
    """
    return np.array([
        [SQRT2_INV, SQRT2_INV],
        [SQRT2_INV, -SQRT2_INV]
    ], dtype=np.complex128)


def unwind() -> np.ndarray:
    """
    Hadamard adjoint (H†) - Returns to computational basis.
    DNA metaphor: DNA rewinding after transcription.

    Note: H is self-adjoint, so H† = H
    """
    return helix()  # H is Hermitian


def cleave() -> np.ndarray:
    """
    Pauli-X gate (NOT) - Bit flip.
    DNA metaphor: Restriction enzyme cleaving DNA strand.

    X = |0 1|
        |1 0|
    """
    return np.array([
        [0, 1],
        [1, 0]
    ], dtype=np.complex128)


def phase_flip() -> np.ndarray:
    """
    Pauli-Z gate - Phase flip.
    DNA metaphor: Methylation affecting gene expression.

    Z = |1  0|
        |0 -1|
    """
    return np.array([
        [1, 0],
        [0, -1]
    ], dtype=np.complex128)


def rotate_y() -> np.ndarray:
    """
    Pauli-Y gate - Combined bit and phase flip.

    Y = |0 -i|
        |i  0|
    """
    return np.array([
        [0, -1j],
        [1j, 0]
    ], dtype=np.complex128)


def twist(theta: float) -> np.ndarray:
    """
    RZ rotation gate - Phase rotation around Z axis.
    DNA metaphor: Supercoiling twist in DNA helix.

    RZ(θ) = |e^{-iθ/2}    0     |
            |   0      e^{iθ/2}|

    Args:
        theta: Rotation angle in radians

    Returns:
        2x2 complex rotation matrix
    """
    half_theta = theta / 2
    return np.array([
        [np.exp(-1j * half_theta), 0],
        [0, np.exp(1j * half_theta)]
    ], dtype=np.complex128)


def fold(theta: float) -> np.ndarray:
    """
    RY rotation gate - Amplitude rotation around Y axis.
    DNA metaphor: Protein folding changing structure.

    RY(θ) = |cos(θ/2)  -sin(θ/2)|
            |sin(θ/2)   cos(θ/2)|

    Args:
        theta: Rotation angle in radians

    Returns:
        2x2 real rotation matrix
    """
    half_theta = theta / 2
    c = np.cos(half_theta)
    s = np.sin(half_theta)
    return np.array([
        [c, -s],
        [s, c]
    ], dtype=np.complex128)


def splice(theta: float) -> np.ndarray:
    """
    RX rotation gate - Rotation around X axis.
    DNA metaphor: RNA splicing modifying transcript.

    RX(θ) = |cos(θ/2)   -i·sin(θ/2)|
            |-i·sin(θ/2)  cos(θ/2) |

    Args:
        theta: Rotation angle in radians

    Returns:
        2x2 complex rotation matrix
    """
    half_theta = theta / 2
    c = np.cos(half_theta)
    s = np.sin(half_theta)
    return np.array([
        [c, -1j * s],
        [-1j * s, c]
    ], dtype=np.complex128)


def phase_gate(phi: float) -> np.ndarray:
    """
    General phase gate P(φ).

    P(φ) = |1      0   |
           |0  e^{iφ}|

    Args:
        phi: Phase angle in radians
    """
    return np.array([
        [1, 0],
        [0, np.exp(1j * phi)]
    ], dtype=np.complex128)


def t_gate() -> np.ndarray:
    """
    T gate (π/8 gate) - Used for universal gate sets.

    T = P(π/4) = |1      0     |
                 |0  e^{iπ/4}|
    """
    return phase_gate(np.pi / 4)


def s_gate() -> np.ndarray:
    """
    S gate (√Z) - Phase gate.

    S = P(π/2) = |1  0|
                 |0  i|
    """
    return phase_gate(np.pi / 2)


# ═══════════════════════════════════════════════════════════════════════════════
# TWO-QUBIT GATES
# ═══════════════════════════════════════════════════════════════════════════════

def bond() -> np.ndarray:
    """
    CNOT gate - Controlled NOT, creates entanglement.
    DNA metaphor: Hydrogen bonding between base pairs.

    CNOT = |1 0 0 0|
           |0 1 0 0|
           |0 0 0 1|
           |0 0 1 0|

    Control: qubit 0, Target: qubit 1
    """
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0]
    ], dtype=np.complex128)


def controlled_z() -> np.ndarray:
    """
    CZ gate - Controlled-Z, symmetric entanglement.

    CZ = |1  0  0  0|
         |0  1  0  0|
         |0  0  1  0|
         |0  0  0 -1|
    """
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, -1]
    ], dtype=np.complex128)


def swap() -> np.ndarray:
    """
    SWAP gate - Exchange two qubits.
    DNA metaphor: Crossing over during recombination.

    SWAP = |1 0 0 0|
           |0 0 1 0|
           |0 1 0 0|
           |0 0 0 1|
    """
    return np.array([
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1]
    ], dtype=np.complex128)


def iswap() -> np.ndarray:
    """
    iSWAP gate - Exchange with phase.

    iSWAP = |1  0  0  0|
            |0  0  i  0|
            |0  i  0  0|
            |0  0  0  1|
    """
    return np.array([
        [1, 0, 0, 0],
        [0, 0, 1j, 0],
        [0, 1j, 0, 0],
        [0, 0, 0, 1]
    ], dtype=np.complex128)


def controlled_phase(phi: float) -> np.ndarray:
    """
    Controlled phase gate CP(φ).

    CP(φ) = |1  0  0      0    |
            |0  1  0      0    |
            |0  0  1      0    |
            |0  0  0  e^{iφ}|
    """
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, np.exp(1j * phi)]
    ], dtype=np.complex128)


def xx_rotation(theta: float) -> np.ndarray:
    """
    XX rotation (Ising coupling) - Native to trapped-ion systems.

    RXX(θ) = exp(-i θ/2 X⊗X)
    """
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, 0, 0, -1j * s],
        [0, c, -1j * s, 0],
        [0, -1j * s, c, 0],
        [-1j * s, 0, 0, c]
    ], dtype=np.complex128)


def yy_rotation(theta: float) -> np.ndarray:
    """
    YY rotation (Ising coupling).

    RYY(θ) = exp(-i θ/2 Y⊗Y)
    """
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, 0, 0, 1j * s],
        [0, c, -1j * s, 0],
        [0, -1j * s, c, 0],
        [1j * s, 0, 0, c]
    ], dtype=np.complex128)


def zz_rotation(theta: float) -> np.ndarray:
    """
    ZZ rotation (Ising coupling) - Native to superconducting systems.

    RZZ(θ) = exp(-i θ/2 Z⊗Z)
    """
    return np.diag([
        np.exp(-1j * theta / 2),
        np.exp(1j * theta / 2),
        np.exp(1j * theta / 2),
        np.exp(-1j * theta / 2)
    ]).astype(np.complex128)


# ═══════════════════════════════════════════════════════════════════════════════
# THREE-QUBIT GATES
# ═══════════════════════════════════════════════════════════════════════════════

def toffoli() -> np.ndarray:
    """
    Toffoli gate (CCNOT) - Universal for classical computation.
    DNA metaphor: Transcription factor binding requiring two signals.

    Flips target only if both controls are |1⟩
    """
    gate = np.eye(8, dtype=np.complex128)
    gate[6, 6] = 0
    gate[7, 7] = 0
    gate[6, 7] = 1
    gate[7, 6] = 1
    return gate


def fredkin() -> np.ndarray:
    """
    Fredkin gate (CSWAP) - Controlled swap.

    Swaps qubits 1 and 2 if control (qubit 0) is |1⟩
    """
    gate = np.eye(8, dtype=np.complex128)
    gate[5, 5] = 0
    gate[6, 6] = 0
    gate[5, 6] = 1
    gate[6, 5] = 1
    return gate


# ═══════════════════════════════════════════════════════════════════════════════
# GATE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def tensor(*gates: np.ndarray) -> np.ndarray:
    """
    Tensor product of multiple gates (Kronecker product).

    Args:
        *gates: Variable number of gate matrices

    Returns:
        Tensor product of all gates
    """
    result = gates[0]
    for gate in gates[1:]:
        result = np.kron(result, gate)
    return result


def identity(n: int = 2) -> np.ndarray:
    """
    Identity matrix of size n×n.

    Args:
        n: Dimension (default 2 for single qubit)
    """
    return np.eye(n, dtype=np.complex128)


def adjoint(gate: np.ndarray) -> np.ndarray:
    """
    Compute adjoint (conjugate transpose) of a gate.

    Args:
        gate: Input gate matrix

    Returns:
        Gate adjoint (G†)
    """
    return np.conj(gate.T)


def compose(*gates: np.ndarray) -> np.ndarray:
    """
    Compose gates by matrix multiplication (right to left).

    compose(A, B, C) = A @ B @ C (C applied first, then B, then A)

    Args:
        *gates: Variable number of gate matrices

    Returns:
        Composed gate
    """
    result = gates[0]
    for gate in gates[1:]:
        result = result @ gate
    return result


def is_unitary(gate: np.ndarray, tol: float = 1e-10) -> bool:
    """
    Check if a gate is unitary (U†U = I).

    Args:
        gate: Gate matrix to check
        tol: Tolerance for comparison

    Returns:
        True if gate is unitary
    """
    n = gate.shape[0]
    product = adjoint(gate) @ gate
    return np.allclose(product, np.eye(n), atol=tol)


def fidelity(gate1: np.ndarray, gate2: np.ndarray) -> float:
    """
    Compute fidelity between two gates.

    F = |Tr(G1† G2)|² / n²

    Args:
        gate1, gate2: Gate matrices

    Returns:
        Fidelity value [0, 1]
    """
    n = gate1.shape[0]
    trace = np.abs(np.trace(adjoint(gate1) @ gate2))
    return (trace / n) ** 2


# ═══════════════════════════════════════════════════════════════════════════════
# GATE ALIASES (DNA Metaphors)
# ═══════════════════════════════════════════════════════════════════════════════

# Standard gate names as aliases
H = helix
X = cleave
Y = rotate_y
Z = phase_flip
RX = splice
RY = fold
RZ = twist
CNOT = bond
CZ = controlled_z
SWAP = swap
CP = controlled_phase
RXX = xx_rotation
RYY = yy_rotation
RZZ = zz_rotation
T = t_gate
S = s_gate
CCX = toffoli
CSWAP = fredkin


# Export all
__all__ = [
    # DNA metaphors
    'helix', 'unwind', 'cleave', 'twist', 'fold', 'splice', 'bond',
    # Standard names
    'H', 'X', 'Y', 'Z', 'RX', 'RY', 'RZ', 'T', 'S',
    'CNOT', 'CZ', 'SWAP', 'CP', 'iswap',
    'RXX', 'RYY', 'RZZ',
    'CCX', 'CSWAP', 'toffoli', 'fredkin',
    # Utilities
    'tensor', 'identity', 'adjoint', 'compose', 'is_unitary', 'fidelity',
    'phase_gate', 'controlled_phase', 'phase_flip', 'rotate_y',
]
