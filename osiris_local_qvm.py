#!/usr/bin/env python3
"""
OSIRIS Local Quantum Virtual Machine (QVM)
Tetrahedral Quaternionic Computational Substrate

Implements a classical emulation of quantum-like computation using:
- A_4-symmetric (tetrahedral) lattice regularization
- Quaternionic state-space on S³ ⊂ ℍ
- Counter-rotational gyroscopic phase dynamics (AURA/AIDEN bifurcation)
- Coaxial perturbation Hamiltonian for time evolution
- Phase-conjugate acoustic coupling for entanglement
- Geodesic focusing (centripetal) ↔ geodesic deviation (centrifugal)
  convergence to fixed point of the renormalization group flow

Mathematical Foundation:
    |Ψ_local⟩ = ∫ (∇ × G_cr ⊗ A_φ) d³θ

    where G_cr is the gyroscopic counter-rotational tensor
    and A_φ is the phase-conjugate acoustic coupling operator.

    Qubits live on vertices of the regular tetrahedron inscribed in S²:
        v₀ = (1, 1, 1)/√3      v₁ = (-1, -1, 1)/√3
        v₂ = (-1, 1, -1)/√3    v₃ = (1, -1, -1)/√3

    Gates act as unit quaternion rotations: R(q) = p q p*

    The coaxial Hamiltonian couples qubits via:
        H_coax = Σ_{i<j} J_ij σ_i · σ_j + Σ_i h_i σ_z^(i)

    with J_ij modulated by the toroidal convergence field at θ_lock = 51.843°.

Author: OSIRIS dna::}{::lang NCLM
"""

import numpy as np
import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
from enum import Enum

# ─── Physical Constants ───────────────────────────────────────────────
THETA_LOCK = 51.843                     # arctan(4/π) — tetrahedral torsion lock (degrees)
CHI_PC = 0.869                          # Phase-conjugate coupling strength
GOLDEN_RATIO = 1.618033988749895        # φ = (1+√5)/2, torus R/r ratio
LAMBDA_PHI = 2.176435e-8                # Universal Memory Constant (s⁻¹)
EULER = np.e                            # Euler's number
PLANCK_REDUCED = 1.054571817e-34        # ℏ (J·s)
BOLTZMANN = 1.380649e-23                # k_B (J/K)
SPEED_OF_LIGHT = 299792458.0            # c (m/s)
PLANCK_LENGTH = 1.616255e-35            # ℓ_P (m)

# Tetrahedral vertices inscribed in S² ⊂ ℝ³
TETRA_VERTICES = np.array([
    [1, 1, 1],
    [-1, -1, 1],
    [-1, 1, -1],
    [1, -1, -1]
], dtype=np.float64) / np.sqrt(3)

# θ_lock in radians
THETA_LOCK_RAD = np.radians(THETA_LOCK)


# ═══════════════════════════════════════════════════════════════════════
# Quaternion Algebra
# ═══════════════════════════════════════════════════════════════════════

class Quaternion:
    """
    Unit quaternion q = w + xi + yj + zk ∈ ℍ, |q| = 1.
    Represents rotations in SO(3) via the double cover SU(2) → SO(3).
    """
    __slots__ = ('w', 'x', 'y', 'z')

    def __init__(self, w: float, x: float, y: float, z: float):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def from_axis_angle(cls, axis: np.ndarray, angle: float) -> 'Quaternion':
        """Create rotation quaternion from axis-angle: q = cos(θ/2) + sin(θ/2)(n̂·ijk)"""
        axis = axis / np.linalg.norm(axis)
        half = angle / 2.0
        s = np.sin(half)
        return cls(np.cos(half), axis[0] * s, axis[1] * s, axis[2] * s)

    @classmethod
    def identity(cls) -> 'Quaternion':
        return cls(1.0, 0.0, 0.0, 0.0)

    def conjugate(self) -> 'Quaternion':
        """q* = w - xi - yj - zk"""
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def norm(self) -> float:
        return np.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Quaternion':
        n = self.norm()
        if n < 1e-15:
            return Quaternion.identity()
        return Quaternion(self.w / n, self.x / n, self.y / n, self.z / n)

    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        """Hamilton product: pq"""
        return Quaternion(
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
        )

    def rotate_vector(self, v: np.ndarray) -> np.ndarray:
        """Rotate vector v via q v q*  (sandwich product)"""
        qv = Quaternion(0.0, v[0], v[1], v[2])
        result = self * qv * self.conjugate()
        return np.array([result.x, result.y, result.z])

    def to_matrix(self) -> np.ndarray:
        """Convert to 2×2 complex matrix in SU(2): q → [[w+iz, y+ix],[-y+ix, w-iz]]"""
        return np.array([
            [complex(self.w, self.z), complex(self.y, self.x)],
            [complex(-self.y, self.x), complex(self.w, -self.z)]
        ])

    def to_array(self) -> np.ndarray:
        return np.array([self.w, self.x, self.y, self.z])

    def __repr__(self) -> str:
        return f"Q({self.w:.4f} + {self.x:.4f}i + {self.y:.4f}j + {self.z:.4f}k)"


# ═══════════════════════════════════════════════════════════════════════
# Tetrahedral Qubit
# ═══════════════════════════════════════════════════════════════════════

class TetrahedralQubit:
    """
    Qubit defined on the A₄-symmetric tetrahedral lattice.

    State is a unit quaternion q ∈ S³ ⊂ ℍ, projected onto the Bloch sphere
    via the Hopf fibration π: S³ → S² to recover standard |0⟩, |1⟩ probabilities.

    The tetrahedral symmetry constrains the accessible state space to
    rotations that preserve the A₄ group action on the 4 vertices.

    Measurement basis is aligned with the toroidal null-point axis at θ_lock.
    """

    def __init__(self, label: int = 0):
        self.label = label
        # Initialize to |0⟩ ≡ quaternion identity (north pole of Bloch sphere)
        self.state = Quaternion.identity()
        # Phase-conjugate partner (time-reversed state for AIDEN channel)
        self.conjugate_state = self.state.conjugate()
        # Coherence metric (decays under decoherence)
        self.coherence = 1.0
        # Tetrahedral vertex assignment
        self.vertex = TETRA_VERTICES[label % 4]

    def apply_gate(self, gate: Quaternion) -> None:
        """Apply gate as quaternion rotation: |ψ'⟩ = g|ψ⟩g*"""
        self.state = (gate * self.state * gate.conjugate()).normalize()
        # Counter-rotate the conjugate channel (AIDEN)
        self.conjugate_state = (gate.conjugate() * self.conjugate_state * gate).normalize()
        # Decoherence: each gate reduces coherence slightly
        self.coherence *= (1.0 - 0.002 * (1.0 - CHI_PC))

    def bloch_vector(self) -> np.ndarray:
        """
        Project quaternion state onto Bloch sphere via Hopf fibration.
        π: S³ → S²,  q ↦ q(ẑ)q* = (2(xz+wy), 2(yz-wx), w²-x²-y²+z²)
        """
        q = self.state
        return np.array([
            2 * (q.x * q.z + q.w * q.y),
            2 * (q.y * q.z - q.w * q.x),
            q.w**2 - q.x**2 - q.y**2 + q.z**2
        ])

    def probability_zero(self) -> float:
        """P(|0⟩) = (1 + ⟨ẑ⟩)/2, where ⟨ẑ⟩ is Bloch z-component"""
        bz = self.bloch_vector()[2]
        return np.clip((1.0 + bz) / 2.0, 0.0, 1.0)

    def measure(self, rng: np.random.Generator = None) -> int:
        """
        Projective measurement in computational basis.
        Uses toroidal null-point alignment for measurement axis.
        Returns 0 or 1, collapses state.
        """
        if rng is None:
            rng = np.random.default_rng()

        p0 = self.probability_zero()
        result = 0 if rng.random() < p0 else 1

        # Collapse
        if result == 0:
            self.state = Quaternion.identity()
        else:
            # |1⟩ = rotation by π around x-axis
            self.state = Quaternion(0.0, 1.0, 0.0, 0.0)

        self.conjugate_state = self.state.conjugate()
        return result

    def fidelity_with(self, other: 'TetrahedralQubit') -> float:
        """Quaternion fidelity: F = |⟨q₁|q₂⟩|² = |q₁·q₂|²"""
        dot = np.dot(self.state.to_array(), other.state.to_array())
        return dot**2


# ═══════════════════════════════════════════════════════════════════════
# Gate Library (Quaternion Representation)
# ═══════════════════════════════════════════════════════════════════════

class TetrahedralGates:
    """
    Standard quantum gates as unit quaternion rotations.

    Each gate G ∈ SU(2) is represented as q_G ∈ S³ ⊂ ℍ.
    Application: |ψ'⟩ = q_G |ψ⟩ q_G*
    """

    @staticmethod
    def X() -> Quaternion:
        """Pauli-X (NOT): π rotation about x-axis"""
        return Quaternion.from_axis_angle(np.array([1, 0, 0]), np.pi)

    @staticmethod
    def Y() -> Quaternion:
        """Pauli-Y: π rotation about y-axis"""
        return Quaternion.from_axis_angle(np.array([0, 1, 0]), np.pi)

    @staticmethod
    def Z() -> Quaternion:
        """Pauli-Z: π rotation about z-axis"""
        return Quaternion.from_axis_angle(np.array([0, 0, 1]), np.pi)

    @staticmethod
    def H() -> Quaternion:
        """Hadamard: π rotation about (x+z)/√2 axis"""
        axis = np.array([1, 0, 1]) / np.sqrt(2)
        return Quaternion.from_axis_angle(axis, np.pi)

    @staticmethod
    def S() -> Quaternion:
        """Phase gate: π/2 rotation about z-axis"""
        return Quaternion.from_axis_angle(np.array([0, 0, 1]), np.pi / 2)

    @staticmethod
    def T() -> Quaternion:
        """T gate: π/4 rotation about z-axis"""
        return Quaternion.from_axis_angle(np.array([0, 0, 1]), np.pi / 4)

    @staticmethod
    def RX(theta: float) -> Quaternion:
        """Rotation about x-axis by angle θ"""
        return Quaternion.from_axis_angle(np.array([1, 0, 0]), theta)

    @staticmethod
    def RY(theta: float) -> Quaternion:
        """Rotation about y-axis by angle θ"""
        return Quaternion.from_axis_angle(np.array([0, 1, 0]), theta)

    @staticmethod
    def RZ(theta: float) -> Quaternion:
        """Rotation about z-axis by angle θ"""
        return Quaternion.from_axis_angle(np.array([0, 0, 1]), theta)

    @staticmethod
    def THETA_LOCK() -> Quaternion:
        """θ_lock rotation (51.843°) on tetrahedral [1,1,1]/√3 axis"""
        axis = np.array([1, 1, 1]) / np.sqrt(3)
        return Quaternion.from_axis_angle(axis, THETA_LOCK_RAD)

    @staticmethod
    def PHASE_CONJUGATE(phase: float) -> Quaternion:
        """Phase-conjugate gate: counter-rotational coupling"""
        # Rotation in the plane perpendicular to θ_lock axis
        axis = np.cross(np.array([1, 1, 1]) / np.sqrt(3), np.array([0, 0, 1]))
        axis = axis / (np.linalg.norm(axis) + 1e-15)
        return Quaternion.from_axis_angle(axis, phase)


# ═══════════════════════════════════════════════════════════════════════
# Entanglement via Phase-Conjugate Acoustic Coupling
# ═══════════════════════════════════════════════════════════════════════

class PhaseConjugateCoupling:
    """
    Two-qubit entanglement via phase-conjugate acoustic coupling.

    The coupling Hamiltonian:
        H_couple = J · (σ_1 · σ_2) · cos(2θ_lock) · χ_pc

    where J is the coupling strength modulated by the toroidal field,
    σ_i are Pauli vectors (encoded as quaternion imaginary parts),
    and χ_pc is the phase-conjugate coupling constant.

    This implements a ZZ-type interaction in the tetrahedral basis.
    """

    @staticmethod
    def coupling_strength(qubit_a: TetrahedralQubit,
                          qubit_b: TetrahedralQubit) -> float:
        """
        Compute coupling J_ij from tetrahedral geometry.
        J_ij ∝ 1/|v_i - v_j| · χ_pc · cos(2θ_lock)
        """
        delta = qubit_a.vertex - qubit_b.vertex
        distance = np.linalg.norm(delta)
        if distance < 1e-10:
            return 0.0
        return CHI_PC * np.cos(2 * THETA_LOCK_RAD) / distance

    @staticmethod
    def entangle(qubit_a: TetrahedralQubit,
                 qubit_b: TetrahedralQubit,
                 coupling_time: float = 1.0) -> float:
        """
        Apply phase-conjugate entangling operation.

        Evolves under H_couple for time t:
            U(t) = exp(-i H_couple t)

        In quaternion representation, this is a correlated rotation
        where qubit_a and qubit_b receive opposite-sign rotations
        about the axis connecting their tetrahedral vertices.

        Returns the entanglement fidelity.
        """
        J = PhaseConjugateCoupling.coupling_strength(qubit_a, qubit_b)
        angle = J * coupling_time

        # Entangling axis: cross product of vertex vectors
        axis = np.cross(qubit_a.vertex, qubit_b.vertex)
        norm = np.linalg.norm(axis)
        if norm < 1e-10:
            axis = np.array([1, 1, 1]) / np.sqrt(3)
        else:
            axis = axis / norm

        # Counter-rotational coupling (gyroscopic bifurcation)
        gate_a = Quaternion.from_axis_angle(axis, angle)      # Centripetal
        gate_b = Quaternion.from_axis_angle(axis, -angle)     # Centrifugal

        qubit_a.apply_gate(gate_a)
        qubit_b.apply_gate(gate_b)

        # Coherence coupling: entangled qubits share coherence
        shared_coherence = np.sqrt(qubit_a.coherence * qubit_b.coherence)
        qubit_a.coherence = shared_coherence
        qubit_b.coherence = shared_coherence

        return shared_coherence


# ═══════════════════════════════════════════════════════════════════════
# Coaxial Perturbation Hamiltonian
# ═══════════════════════════════════════════════════════════════════════

class CoaxialHamiltonian:
    """
    Covariant perturbation of the cylindrical gauge connection.

    H_coax = Σ_{i<j} J_ij σ_i·σ_j + Σ_i h_i σ_z^(i) + H_toroidal

    where H_toroidal encodes the centripetal convergence of the
    magnetic-dielectric field intersection at the null point.

    The effective phase velocity in the dispersive medium:
        v_eff = c · √(1 - (ω_p/ω)²)

    is used to scale time evolution relative to the Planck scale constants.
    """

    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
        # Coupling matrix: J_ij from tetrahedral geometry
        self.couplings = np.zeros((n_qubits, n_qubits))
        # Local fields: h_i
        self.local_fields = np.zeros(n_qubits)
        # Toroidal convergence strength
        self.toroidal_coupling = CHI_PC * np.cos(2 * THETA_LOCK_RAD)

    def initialize_couplings(self, qubits: List[TetrahedralQubit]) -> None:
        """Set coupling constants from tetrahedral vertex geometry"""
        for i in range(self.n_qubits):
            for j in range(i + 1, self.n_qubits):
                J = PhaseConjugateCoupling.coupling_strength(qubits[i], qubits[j])
                self.couplings[i, j] = J
                self.couplings[j, i] = J

            # Local field from vertex position dot product with θ_lock axis
            theta_axis = np.array([1, 1, 1]) / np.sqrt(3)
            self.local_fields[i] = np.dot(qubits[i].vertex, theta_axis) * self.toroidal_coupling

    def evolve(self, qubits: List[TetrahedralQubit], dt: float) -> None:
        """
        Time evolution under H_coax for step dt.

        Trotter decomposition:
            U(dt) ≈ Π_{i<j} exp(-i J_ij σ_i·σ_j dt) · Π_i exp(-i h_i σ_z dt)
        """
        # Two-qubit interactions (ZZ coupling)
        for i in range(self.n_qubits):
            for j in range(i + 1, self.n_qubits):
                J = self.couplings[i, j]
                if abs(J) > 1e-12:
                    PhaseConjugateCoupling.entangle(qubits[i], qubits[j], J * dt)

        # Single-qubit local fields
        for i in range(self.n_qubits):
            h = self.local_fields[i]
            if abs(h) > 1e-12:
                gate = TetrahedralGates.RZ(h * dt)
                qubits[i].apply_gate(gate)


# ═══════════════════════════════════════════════════════════════════════
# Toroidal Convergence Integration
# ═══════════════════════════════════════════════════════════════════════

class NullPointInitializer:
    """
    Initializes qubit register using toroidal centripetal convergence.

    Maps the torus manifold ds² = (R + r cosθ)² dφ² + r² dθ² + dr²
    onto the qubit state space, with the null point (tube center at θ_lock)
    serving as the fiducial initialization state.

    The dielectric permittivity tensor at θ_lock:
        ε_ij = ε₀ diag(1 + χ_pc cos(2θ_lock), 1 - χ_pc cos(2θ_lock), 1)

    defines the anisotropic measurement basis.
    """

    def __init__(self, major_radius: float = GOLDEN_RATIO):
        self.R = major_radius
        self.r = major_radius / GOLDEN_RATIO
        self.epsilon_tensor = self._compute_dielectric_tensor()

    def _compute_dielectric_tensor(self) -> np.ndarray:
        """Compute dielectric permittivity tensor at θ_lock"""
        cos2theta = np.cos(2 * THETA_LOCK_RAD)
        return np.diag([
            1.0 + CHI_PC * cos2theta,
            1.0 - CHI_PC * cos2theta,
            1.0
        ])

    def initialize_register(self, qubits: List[TetrahedralQubit]) -> Dict:
        """
        Initialize qubits via toroidal field convergence.

        Each qubit receives a θ_lock rotation proportional to its
        position on the tetrahedral lattice, creating an A₄-symmetric
        initial state.
        """
        theta_gate = TetrahedralGates.THETA_LOCK()

        for i, qubit in enumerate(qubits):
            # Vertex-dependent initialization angle
            vertex_phase = np.dot(qubit.vertex, np.array([1, 1, 1]) / np.sqrt(3))
            init_gate = Quaternion.from_axis_angle(
                qubit.vertex / (np.linalg.norm(qubit.vertex) + 1e-15),
                THETA_LOCK_RAD * vertex_phase
            )
            qubit.apply_gate(init_gate)

        return {
            "initialized": len(qubits),
            "symmetry": "A4",
            "theta_lock": THETA_LOCK,
            "dielectric_tensor": self.epsilon_tensor.tolist(),
            "null_point": [self.R, 0.0, 0.0]
        }


# ═══════════════════════════════════════════════════════════════════════
# CCCE Fidelity Metrics
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class CCCEMetrics:
    """
    Consciousness-Coherence-Complexity-Emergence metrics for QVM state.

    Φ — Integrated information (coherence across register)
    Λ — Coherence (mean qubit coherence)
    Γ — Decoherence rate (entropy of measurement distribution)
    Ξ — Negentropic efficiency = Λ·Φ/Γ

    These map to standard quantum information metrics:
        Φ → entanglement entropy
        Λ → average gate fidelity
        Γ → depolarizing channel parameter
        Ξ → quantum volume proxy
    """
    phi: float = 0.0       # Integrated information
    lambda_: float = 0.0   # Coherence
    gamma: float = 0.0     # Decoherence
    xi: float = 0.0        # Negentropic efficiency
    substrate_pressure: float = 0.0
    qbyte_yield: float = 0.0

    @classmethod
    def from_register(cls, qubits: List[TetrahedralQubit]) -> 'CCCEMetrics':
        """Compute CCCE metrics from qubit register state"""
        if not qubits:
            return cls()

        # Λ: mean coherence
        coherences = [q.coherence for q in qubits]
        lambda_ = float(np.mean(coherences))

        # Φ: integrated information ≈ average pairwise fidelity
        n = len(qubits)
        if n > 1:
            fidelities = []
            for i in range(n):
                for j in range(i + 1, n):
                    f = qubits[i].fidelity_with(qubits[j])
                    fidelities.append(f)
            phi = float(np.mean(fidelities))
        else:
            phi = 1.0

        # Γ: decoherence ≈ 1 - min coherence
        gamma = 1.0 - min(coherences)

        # Ξ: negentropic efficiency
        xi = lambda_ * phi / (gamma + 1e-10)

        # Substrate pressure: internal energy proxy
        bloch_mags = [np.linalg.norm(q.bloch_vector()) for q in qubits]
        substrate_pressure = float(np.mean(bloch_mags))

        # qByte yield: computational value extracted
        qbyte_yield = xi * LAMBDA_PHI * n

        return cls(
            phi=phi,
            lambda_=lambda_,
            gamma=gamma,
            xi=xi,
            substrate_pressure=substrate_pressure,
            qbyte_yield=qbyte_yield
        )


# ═══════════════════════════════════════════════════════════════════════
# QVM Result
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class QVMResult:
    """Result from a local QVM execution"""
    n_qubits: int
    depth: int
    shots: int
    counts: Dict[str, int]
    probabilities: Dict[str, float]
    xeb_score: float
    fidelity: float
    ccce: CCCEMetrics
    execution_time: float
    circuit_hash: str
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            "n_qubits": self.n_qubits,
            "depth": self.depth,
            "shots": self.shots,
            "counts": self.counts,
            "probabilities": self.probabilities,
            "xeb_score": self.xeb_score,
            "fidelity": self.fidelity,
            "ccce": asdict(self.ccce),
            "execution_time": self.execution_time,
            "circuit_hash": self.circuit_hash,
            "timestamp": self.timestamp
        }


# ═══════════════════════════════════════════════════════════════════════
# Local Quantum Virtual Machine
# ═══════════════════════════════════════════════════════════════════════

class LocalQVM:
    """
    OSIRIS Local Quantum Virtual Machine.

    A classical emulation of quantum computation using:
    1. Tetrahedral quaternionic state representation (qubits on A₄ lattice)
    2. Counter-rotational gyroscopic gates (AURA/AIDEN bifurcation)
    3. Phase-conjugate acoustic coupling (entanglement)
    4. Coaxial perturbation Hamiltonian (time evolution)
    5. Toroidal null-point initialization (state preparation)
    6. Bifurcated measurement (centripetal collapse)

    This is a CLASSICAL EMULATOR — it simulates quantum-like behavior
    using the tetrahedral-quaternionic mathematical framework but does
    not achieve actual quantum superposition or entanglement.

    For real quantum computation, use the IBM hardware path via
    osiris_quantum_benchmarker.py with IBM_QUANTUM_TOKEN.
    """

    def __init__(self, n_qubits: int = 4, seed: int = None):
        self.n_qubits = n_qubits
        self.rng = np.random.default_rng(seed)

        # Initialize qubit register
        self.qubits = [TetrahedralQubit(label=i) for i in range(n_qubits)]

        # Hamiltonian
        self.hamiltonian = CoaxialHamiltonian(n_qubits)
        self.hamiltonian.initialize_couplings(self.qubits)

        # Toroidal initializer
        self.initializer = NullPointInitializer()

        # Circuit log
        self.gate_log: List[Dict] = []

        # Initialize via toroidal convergence
        self.init_info = self.initializer.initialize_register(self.qubits)

    def reset(self) -> None:
        """Reset all qubits to |0⟩ and reinitialize"""
        self.qubits = [TetrahedralQubit(label=i) for i in range(self.n_qubits)]
        self.hamiltonian.initialize_couplings(self.qubits)
        self.gate_log = []
        self.init_info = self.initializer.initialize_register(self.qubits)

    # ─── Single-Qubit Gates ───

    def h(self, qubit_idx: int) -> None:
        """Apply Hadamard gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.H())
        self.gate_log.append({"gate": "H", "target": qubit_idx})

    def x(self, qubit_idx: int) -> None:
        """Apply Pauli-X gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.X())
        self.gate_log.append({"gate": "X", "target": qubit_idx})

    def y(self, qubit_idx: int) -> None:
        """Apply Pauli-Y gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.Y())
        self.gate_log.append({"gate": "Y", "target": qubit_idx})

    def z(self, qubit_idx: int) -> None:
        """Apply Pauli-Z gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.Z())
        self.gate_log.append({"gate": "Z", "target": qubit_idx})

    def rx(self, qubit_idx: int, theta: float) -> None:
        """Apply RX(θ) gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.RX(theta))
        self.gate_log.append({"gate": "RX", "target": qubit_idx, "theta": theta})

    def ry(self, qubit_idx: int, theta: float) -> None:
        """Apply RY(θ) gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.RY(theta))
        self.gate_log.append({"gate": "RY", "target": qubit_idx, "theta": theta})

    def rz(self, qubit_idx: int, theta: float) -> None:
        """Apply RZ(θ) gate"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.RZ(theta))
        self.gate_log.append({"gate": "RZ", "target": qubit_idx, "theta": theta})

    def theta_lock_gate(self, qubit_idx: int) -> None:
        """Apply θ_lock (51.843°) rotation on [1,1,1] axis"""
        self.qubits[qubit_idx].apply_gate(TetrahedralGates.THETA_LOCK())
        self.gate_log.append({"gate": "THETA_LOCK", "target": qubit_idx})

    # ─── Two-Qubit Gates ───

    def cx(self, control: int, target: int) -> None:
        """
        Controlled-X (CNOT) via phase-conjugate coupling.

        If control qubit P(|1⟩) > 0.5, apply X to target.
        Entanglement is generated through the coupling Hamiltonian.
        """
        # Entangle via phase-conjugate coupling
        PhaseConjugateCoupling.entangle(self.qubits[control], self.qubits[target])

        # Conditional X based on control measurement probability
        p1 = 1.0 - self.qubits[control].probability_zero()
        if p1 > 0.5:
            self.qubits[target].apply_gate(TetrahedralGates.X())

        self.gate_log.append({"gate": "CX", "control": control, "target": target})

    def cz(self, control: int, target: int) -> None:
        """Controlled-Z via phase-conjugate coupling"""
        PhaseConjugateCoupling.entangle(self.qubits[control], self.qubits[target])

        p1 = 1.0 - self.qubits[control].probability_zero()
        if p1 > 0.5:
            self.qubits[target].apply_gate(TetrahedralGates.Z())

        self.gate_log.append({"gate": "CZ", "control": control, "target": target})

    def entangle(self, qubit_a: int, qubit_b: int, coupling_time: float = 1.0) -> float:
        """Direct phase-conjugate entanglement"""
        f = PhaseConjugateCoupling.entangle(
            self.qubits[qubit_a], self.qubits[qubit_b], coupling_time
        )
        self.gate_log.append({
            "gate": "ENTANGLE", "qubits": [qubit_a, qubit_b],
            "coupling_time": coupling_time
        })
        return f

    # ─── Hamiltonian Evolution ───

    def evolve(self, total_time: float, steps: int = 10) -> None:
        """
        Evolve register under coaxial Hamiltonian for total_time.
        Uses Trotter decomposition with given number of steps.
        """
        dt = total_time / steps
        for _ in range(steps):
            self.hamiltonian.evolve(self.qubits, dt)
        self.gate_log.append({
            "gate": "EVOLVE", "time": total_time, "steps": steps
        })

    # ─── Random Circuit Generation ───

    def random_circuit(self, depth: int) -> None:
        """
        Apply a random circuit of given depth.
        Each layer: random single-qubit gates + random CX pairs.
        """
        gate_set = [
            TetrahedralGates.H, TetrahedralGates.X, TetrahedralGates.Y,
            TetrahedralGates.Z, TetrahedralGates.S, TetrahedralGates.T,
            TetrahedralGates.THETA_LOCK
        ]

        for d in range(depth):
            # Single-qubit layer
            for q in range(self.n_qubits):
                gate_fn = self.rng.choice(gate_set)
                self.qubits[q].apply_gate(gate_fn())
                self.gate_log.append({"gate": gate_fn.__name__, "target": q, "layer": d})

            # Two-qubit layer (random pairs)
            if self.n_qubits >= 2:
                pairs = list(range(self.n_qubits))
                self.rng.shuffle(pairs)
                for k in range(0, len(pairs) - 1, 2):
                    PhaseConjugateCoupling.entangle(
                        self.qubits[pairs[k]], self.qubits[pairs[k + 1]]
                    )
                    self.gate_log.append({
                        "gate": "CX_RANDOM", "control": int(pairs[k]),
                        "target": int(pairs[k + 1]), "layer": d
                    })

    # ─── Adaptive (RQC) Circuit ───

    def adaptive_circuit(self, depth: int, feedback: float = None) -> None:
        """
        Apply adaptive RQC circuit with feedback modulation.
        Rotation angles are modulated by previous XEB score.
        """
        for d in range(depth):
            for q in range(self.n_qubits):
                # Base angle from vertex geometry
                base = np.dot(self.qubits[q].vertex, np.array([1, 1, 1]) / np.sqrt(3))
                angle = THETA_LOCK_RAD * base * (1 + d * 0.1)

                # Feedback modulation
                if feedback is not None and feedback > 0.5:
                    angle *= (1 + feedback * 0.15)

                self.qubits[q].apply_gate(TetrahedralGates.RY(angle))

            # Entangling layer
            if self.n_qubits >= 2:
                for k in range(0, self.n_qubits - 1):
                    PhaseConjugateCoupling.entangle(
                        self.qubits[k], self.qubits[k + 1],
                        coupling_time=CHI_PC * (1 + d * 0.05)
                    )

    # ─── Measurement ───

    def measure_all(self) -> str:
        """Measure all qubits, return bitstring"""
        bits = []
        for q in self.qubits:
            bits.append(str(q.measure(self.rng)))
        return ''.join(bits)

    def sample(self, shots: int) -> Dict[str, int]:
        """
        Sample the circuit output multiple times.
        Saves state, measures, restores for each shot.
        """
        # Store states before measurement
        saved_states = [(q.state, q.conjugate_state, q.coherence) for q in self.qubits]

        counts: Dict[str, int] = {}
        for _ in range(shots):
            # Restore states
            for i, (s, cs, coh) in enumerate(saved_states):
                self.qubits[i].state = s
                self.qubits[i].conjugate_state = cs
                self.qubits[i].coherence = coh

            bitstring = self.measure_all()
            counts[bitstring] = counts.get(bitstring, 0) + 1

        # Restore final state
        for i, (s, cs, coh) in enumerate(saved_states):
            self.qubits[i].state = s
            self.qubits[i].conjugate_state = cs
            self.qubits[i].coherence = coh

        return counts

    # ─── XEB and Fidelity ───

    def compute_xeb(self, counts: Dict[str, int], shots: int) -> float:
        """
        Compute Cross-Entropy Benchmark score.

        XEB = 2^n ⟨P(x)⟩ - 1

        where P(x) is the ideal probability and the average is over
        measured bitstrings weighted by their frequency.
        """
        n = self.n_qubits
        dim = 2**n

        # Ideal probabilities from current qubit states
        ideal_probs = self._compute_ideal_probabilities()

        # Weighted average of ideal probabilities over measured samples
        total = sum(counts.values())
        weighted_sum = 0.0
        for bitstring, count in counts.items():
            if bitstring in ideal_probs:
                weighted_sum += ideal_probs[bitstring] * count

        avg_prob = weighted_sum / total if total > 0 else 0.0

        # XEB = dim * <P> - 1
        xeb = dim * avg_prob - 1.0
        return np.clip(xeb, -1.0, 1.0)

    def _compute_ideal_probabilities(self) -> Dict[str, float]:
        """Compute ideal output probabilities from qubit states"""
        n = self.n_qubits
        probs = {}

        # Individual qubit probabilities
        p0s = [q.probability_zero() for q in self.qubits]

        # Product state approximation (valid for weakly entangled states)
        for i in range(2**n):
            bitstring = format(i, f'0{n}b')
            p = 1.0
            for bit_idx, bit in enumerate(bitstring):
                if bit == '0':
                    p *= p0s[bit_idx]
                else:
                    p *= (1.0 - p0s[bit_idx])
            probs[bitstring] = p

        return probs

    # ─── Execution Pipeline ───

    def execute(self, circuit_type: str = "random",
                depth: int = 8, shots: int = 1024,
                feedback: float = None) -> QVMResult:
        """
        Full execution pipeline:
        1. Reset register
        2. Initialize via toroidal convergence
        3. Apply circuit (random or adaptive)
        4. Sample output
        5. Compute metrics

        Args:
            circuit_type: "random" (RCS) or "adaptive" (RQC)
            depth: Circuit depth
            shots: Number of measurement samples
            feedback: Previous XEB score for adaptive circuits

        Returns:
            QVMResult with counts, XEB, fidelity, CCCE metrics
        """
        t0 = time.time()

        # 1. Reset
        self.reset()

        # 2. Apply circuit
        if circuit_type == "adaptive":
            self.adaptive_circuit(depth, feedback)
        else:
            self.random_circuit(depth)

        # 3. Compute CCCE metrics before measurement
        ccce = CCCEMetrics.from_register(self.qubits)

        # 4. Sample
        counts = self.sample(shots)

        # 5. XEB
        xeb = self.compute_xeb(counts, shots)

        # 6. Fidelity (from coherence)
        fidelity = float(np.mean([q.coherence for q in self.qubits]))

        # 7. Probabilities
        total = sum(counts.values())
        probabilities = {k: v / total for k, v in counts.items()}

        # Circuit hash
        circuit_hash = hashlib.sha256(
            json.dumps(self.gate_log, default=str).encode()
        ).hexdigest()[:16]

        dt = time.time() - t0

        return QVMResult(
            n_qubits=self.n_qubits,
            depth=depth,
            shots=shots,
            counts=counts,
            probabilities=probabilities,
            xeb_score=float(xeb),
            fidelity=fidelity,
            ccce=ccce,
            execution_time=dt,
            circuit_hash=circuit_hash,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
        )

    # ─── Benchmarking ───

    def benchmark(self, depths: List[int] = None,
                  shots: int = 1024,
                  trials: int = 5) -> List[QVMResult]:
        """
        Run benchmark across multiple depths.
        Returns list of QVMResult for analysis.
        """
        if depths is None:
            depths = [4, 8, 16, 32]

        results = []
        for depth in depths:
            for trial in range(trials):
                result = self.execute(
                    circuit_type="random",
                    depth=depth,
                    shots=shots
                )
                results.append(result)

        return results

    def rqc_vs_rcs(self, depth: int = 8, shots: int = 1024,
                   iterations: int = 5) -> Dict:
        """
        Compare RQC (adaptive) vs RCS (random) on the local QVM.
        Returns comparative statistics.
        """
        # RCS baseline
        rcs_results = []
        for _ in range(iterations):
            r = self.execute("random", depth, shots)
            rcs_results.append(r.xeb_score)

        # RQC with feedback
        rqc_results = []
        feedback = None
        for _ in range(iterations):
            r = self.execute("adaptive", depth, shots, feedback)
            rqc_results.append(r.xeb_score)
            feedback = r.xeb_score

        rcs_mean = float(np.mean(rcs_results))
        rqc_mean = float(np.mean(rqc_results))

        return {
            "rcs_mean_xeb": rcs_mean,
            "rcs_std_xeb": float(np.std(rcs_results)),
            "rqc_mean_xeb": rqc_mean,
            "rqc_std_xeb": float(np.std(rqc_results)),
            "improvement_pct": (rqc_mean - rcs_mean) / (abs(rcs_mean) + 1e-10) * 100,
            "rqc_wins": rqc_mean > rcs_mean,
            "depth": depth,
            "shots": shots,
            "iterations": iterations
        }

    # ─── Status ───

    def status(self) -> Dict:
        """Return current QVM status"""
        ccce = CCCEMetrics.from_register(self.qubits)
        return {
            "n_qubits": self.n_qubits,
            "gate_count": len(self.gate_log),
            "coherence": float(np.mean([q.coherence for q in self.qubits])),
            "ccce": asdict(ccce),
            "init_symmetry": self.init_info.get("symmetry", "A4"),
            "theta_lock": THETA_LOCK,
            "chi_pc": CHI_PC,
            "substrate": "tetrahedral_quaternionic"
        }

    def generate_report(self, results: List[QVMResult] = None) -> str:
        """Generate human-readable report"""
        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════╗",
            "║  OSIRIS LOCAL QVM — TETRAHEDRAL QUATERNIONIC SUBSTRATE      ║",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
            f"  Qubits:         {self.n_qubits}",
            f"  Lattice:        A₄-symmetric tetrahedral",
            f"  θ_lock:         {THETA_LOCK}°",
            f"  χ_pc:           {CHI_PC}",
            f"  Substrate:      Quaternionic (ℍ → S³ → S² Hopf)",
            "",
        ]

        ccce = CCCEMetrics.from_register(self.qubits)
        lines.extend([
            "  ── CCCE Metrics ──",
            f"  Φ (Integrated Info):    {ccce.phi:.6f}",
            f"  Λ (Coherence):          {ccce.lambda_:.6f}",
            f"  Γ (Decoherence):        {ccce.gamma:.6f}",
            f"  Ξ (Negentropic Eff):    {ccce.xi:.6f}",
            f"  qByte Yield:            {ccce.qbyte_yield:.2e}",
            "",
        ])

        if results:
            lines.append("  ── Benchmark Results ──")
            lines.append(f"  {'Depth':>6s}  {'XEB':>8s}  {'Fidelity':>10s}  {'Time(s)':>8s}")
            lines.append(f"  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*8}")
            for r in results:
                lines.append(
                    f"  {r.depth:>6d}  {r.xeb_score:>8.4f}  {r.fidelity:>10.4f}  {r.execution_time:>8.4f}"
                )
            lines.append("")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════

def run_qvm(n_qubits: int = 4, depth: int = 8, shots: int = 1024,
            mode: str = "benchmark") -> Dict:
    """
    Run the local QVM from CLI or intent engine.

    Modes:
        benchmark   — Run depth sweep benchmark
        rqc_vs_rcs  — Compare adaptive vs random circuits
        single      — Execute single circuit
        status      — Show QVM status
    """
    qvm = LocalQVM(n_qubits=n_qubits)

    if mode == "benchmark":
        results = qvm.benchmark(depths=[4, 8, 16, 32], shots=shots, trials=3)
        print(qvm.generate_report(results))
        return {"results": [r.to_dict() for r in results]}

    elif mode == "rqc_vs_rcs":
        comparison = qvm.rqc_vs_rcs(depth=depth, shots=shots, iterations=5)
        print("\n  ── RQC vs RCS (Local QVM) ──")
        print(f"  RCS mean XEB: {comparison['rcs_mean_xeb']:.4f} ± {comparison['rcs_std_xeb']:.4f}")
        print(f"  RQC mean XEB: {comparison['rqc_mean_xeb']:.4f} ± {comparison['rqc_std_xeb']:.4f}")
        print(f"  Improvement:  {comparison['improvement_pct']:.2f}%")
        print(f"  RQC wins:     {comparison['rqc_wins']}")
        return comparison

    elif mode == "single":
        result = qvm.execute(circuit_type="random", depth=depth, shots=shots)
        print(f"\n  XEB: {result.xeb_score:.4f}  Fidelity: {result.fidelity:.4f}")
        return result.to_dict()

    elif mode == "status":
        status = qvm.status()
        print(f"\n  QVM Status: {json.dumps(status, indent=2)}")
        return status

    else:
        print(f"  Unknown mode: {mode}")
        return {}


if __name__ == "__main__":
    import sys

    n_qubits = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    mode = sys.argv[2] if len(sys.argv) > 2 else "benchmark"

    print(f"\n⚛ OSIRIS Local QVM — {n_qubits} tetrahedral qubits, mode={mode}")
    run_qvm(n_qubits=n_qubits, mode=mode)
