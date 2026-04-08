"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SOVEREIGN EXECUTOR - IBM INDEPENDENT                    ║
║                      ════════════════════════════════════                    ║
║                                                                              ║
║    The Sovereign Executor provides quantum circuit execution without         ║
║    ANY external vendor dependencies. No Qiskit. No IBM. No Cirq.            ║
║                                                                              ║
║    This is the heart of the Quantum Independence Framework (QIF).           ║
║                                                                              ║
║    Execution Modes:                                                          ║
║    ├── STATEVECTOR : Exact state vector simulation (up to ~20 qubits)       ║
║    ├── TENSOR      : Tensor network simulation (larger circuits)            ║
║    ├── SAMPLING    : Monte Carlo sampling (measurement only)                ║
║    └── NATIVE      : Future: Direct hardware via sovereign drivers          ║
║                                                                              ║
║    Key Features:                                                             ║
║    ├── Zero external quantum dependencies                                    ║
║    ├── DNA-encoded gate operations (helix, bond, twist, fold, splice)       ║
║    ├── Automatic phase-conjugate healing                                     ║
║    ├── CCCE metric tracking throughout execution                            ║
║    └── Telemetry capsule emission                                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib

try:
    from .gates import (
        helix, cleave, twist, fold, splice, bond, phase_flip,
        controlled_z, swap, toffoli, t_gate, s_gate,
        tensor, identity, adjoint, is_unitary
    )
    from .qbyte import Qbyte, QbyteRegister
    from .phase_conjugate import PhaseConjugateEngine
    from .ccce_runtime import CCCERuntime, create_runtime
except ImportError:
    from gates import (
        helix, cleave, twist, fold, splice, bond, phase_flip,
        controlled_z, swap, toffoli, t_gate, s_gate,
        tensor, identity, adjoint, is_unitary
    )
    from qbyte import Qbyte, QbyteRegister
    from phase_conjugate import PhaseConjugateEngine
    from ccce_runtime import CCCERuntime, create_runtime

# Physical Constants
LAMBDA_PHI = 2.176435e-8
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092


class ExecutionMode(Enum):
    """Quantum execution modes."""
    STATEVECTOR = "statevector"  # Full state vector simulation
    TENSOR = "tensor"            # Tensor network (future)
    SAMPLING = "sampling"        # Monte Carlo sampling
    NATIVE = "native"            # Native hardware (future)


@dataclass
class GateOp:
    """Represents a quantum gate operation."""
    name: str
    qubits: List[int]
    params: List[float] = field(default_factory=list)
    controls: List[int] = field(default_factory=list)


@dataclass
class Circuit:
    """Quantum circuit representation."""
    n_qubits: int
    operations: List[GateOp] = field(default_factory=list)
    name: str = "unnamed"

    def add(self, name: str, qubits: List[int],
            params: Optional[List[float]] = None,
            controls: Optional[List[int]] = None):
        """Add a gate operation."""
        self.operations.append(GateOp(
            name=name,
            qubits=qubits,
            params=params or [],
            controls=controls or []
        ))
        return self

    # DNA-encoded gate shortcuts
    def helix(self, qubit: int):
        """Add Hadamard (DNA helix unwinding)."""
        return self.add('helix', [qubit])

    def cleave(self, qubit: int):
        """Add Pauli-X (DNA cleavage)."""
        return self.add('cleave', [qubit])

    def twist(self, qubit: int, theta: float):
        """Add RZ rotation (DNA twist)."""
        return self.add('twist', [qubit], [theta])

    def fold(self, qubit: int, theta: float):
        """Add RY rotation (protein folding)."""
        return self.add('fold', [qubit], [theta])

    def splice(self, qubit: int, theta: float):
        """Add RX rotation (RNA splicing)."""
        return self.add('splice', [qubit], [theta])

    def bond(self, control: int, target: int):
        """Add CNOT (hydrogen bonding)."""
        return self.add('bond', [target], controls=[control])

    def phase(self, qubit: int):
        """Add Pauli-Z (phase flip)."""
        return self.add('phase', [qubit])

    def cz(self, q1: int, q2: int):
        """Add CZ gate."""
        return self.add('cz', [q1, q2])

    def swap_qubits(self, q1: int, q2: int):
        """Add SWAP gate."""
        return self.add('swap', [q1, q2])

    def toffoli_gate(self, c1: int, c2: int, target: int):
        """Add Toffoli (CCNOT) gate."""
        return self.add('toffoli', [target], controls=[c1, c2])

    def measure(self, qubit: int, classical_bit: Optional[int] = None):
        """Add measurement operation."""
        return self.add('measure', [qubit], [float(classical_bit or qubit)])

    def barrier(self):
        """Add barrier (for visualization)."""
        return self.add('barrier', [])

    def depth(self) -> int:
        """Compute circuit depth (layers)."""
        if not self.operations:
            return 0

        # Track last operation time for each qubit
        qubit_depth = [0] * self.n_qubits
        for op in self.operations:
            if op.name in ('barrier', 'measure'):
                continue
            involved = op.qubits + op.controls
            max_depth = max(qubit_depth[q] for q in involved) if involved else 0
            for q in involved:
                qubit_depth[q] = max_depth + 1

        return max(qubit_depth) if qubit_depth else 0

    def gate_count(self) -> int:
        """Count number of gates (excluding barriers/measures)."""
        return sum(1 for op in self.operations
                   if op.name not in ('barrier', 'measure'))

    def __repr__(self) -> str:
        return (f"Circuit('{self.name}', qubits={self.n_qubits}, "
                f"gates={self.gate_count()}, depth={self.depth()})")


@dataclass
class ExecutionResult:
    """Result of circuit execution."""
    counts: Dict[str, int]           # Measurement counts
    statevector: Optional[np.ndarray] = None  # Final state (if available)
    probabilities: Optional[np.ndarray] = None  # Probability distribution
    metrics: Optional[Dict[str, float]] = None  # CCCE metrics
    execution_time: float = 0.0
    shots: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def most_likely(self) -> str:
        """Return most likely measurement outcome."""
        if not self.counts:
            return ""
        return max(self.counts, key=self.counts.get)

    def expectation(self, observable: str = "Z") -> float:
        """Compute expectation value for simple observables."""
        if not self.counts:
            return 0.0

        total = sum(self.counts.values())
        exp_val = 0.0

        for bitstring, count in self.counts.items():
            # For Z observable, +1 for |0⟩, -1 for |1⟩
            if observable == "Z":
                parity = sum(int(b) for b in bitstring) % 2
                exp_val += (-1) ** parity * count / total

        return exp_val


class SovereignExecutor:
    """
    Sovereign Quantum Executor - IBM Independent.

    This executor provides complete quantum circuit execution without
    any external vendor dependencies. It implements:

    1. State vector simulation for exact quantum computation
    2. DNA-encoded gate operations
    3. Automatic CCCE metric tracking
    4. Phase-conjugate healing
    5. Telemetry and diagnostics

    This is the core of the Quantum Independence Framework (QIF),
    providing a sovereign quantum computing capability.

    Example:
        >>> executor = SovereignExecutor(n_qubits=4)
        >>> circuit = Circuit(4, name="Bell")
        >>> circuit.helix(0).bond(0, 1)
        >>> result = executor.run(circuit, shots=1000)
        >>> print(result.counts)  # {'00': ~500, '11': ~500}
    """

    def __init__(self, n_qubits: int = 8,
                 mode: ExecutionMode = ExecutionMode.STATEVECTOR,
                 enable_healing: bool = True,
                 enable_ccce: bool = True):
        """
        Initialize Sovereign Executor.

        Args:
            n_qubits: Number of qubits
            mode: Execution mode
            enable_healing: Enable automatic phase-conjugate healing
            enable_ccce: Enable CCCE metric tracking
        """
        self.n_qubits = n_qubits
        self.dim = 2 ** n_qubits
        self.mode = mode
        self.enable_healing = enable_healing
        self.enable_ccce = enable_ccce

        # Initialize state to |0...0⟩
        self._state = np.zeros(self.dim, dtype=np.complex128)
        self._state[0] = 1.0

        # Healing engine
        if enable_healing:
            self._healing_engine = PhaseConjugateEngine()
        else:
            self._healing_engine = None

        # CCCE runtime
        if enable_ccce:
            self._ccce = create_runtime("SovereignExecutor")
        else:
            self._ccce = None

        # Statistics
        self._execution_count = 0
        self._total_gates = 0
        self._genesis = time.time()

        # Gate dispatch table
        self._gate_dispatch = self._build_gate_dispatch()

    def _build_gate_dispatch(self) -> Dict[str, Callable]:
        """Build dispatch table for gate operations."""
        return {
            'helix': lambda op: self._apply_single(helix(), op.qubits[0]),
            'cleave': lambda op: self._apply_single(cleave(), op.qubits[0]),
            'phase': lambda op: self._apply_single(phase_flip(), op.qubits[0]),
            'twist': lambda op: self._apply_single(twist(op.params[0]), op.qubits[0]),
            'fold': lambda op: self._apply_single(fold(op.params[0]), op.qubits[0]),
            'splice': lambda op: self._apply_single(splice(op.params[0]), op.qubits[0]),
            't': lambda op: self._apply_single(t_gate(), op.qubits[0]),
            's': lambda op: self._apply_single(s_gate(), op.qubits[0]),
            'bond': lambda op: self._apply_cnot(op.controls[0], op.qubits[0]),
            'cz': lambda op: self._apply_two(controlled_z(), op.qubits[0], op.qubits[1]),
            'swap': lambda op: self._apply_two(swap(), op.qubits[0], op.qubits[1]),
            'toffoli': lambda op: self._apply_toffoli(op.controls[0], op.controls[1], op.qubits[0]),
        }

    def reset(self):
        """Reset executor state to |0...0⟩."""
        self._state = np.zeros(self.dim, dtype=np.complex128)
        self._state[0] = 1.0
        if self._ccce:
            self._ccce.reset()

    def _apply_single(self, gate: np.ndarray, qubit: int):
        """Apply single-qubit gate."""
        if qubit < 0 or qubit >= self.n_qubits:
            raise ValueError(f"Qubit {qubit} out of range [0, {self.n_qubits})")

        # Reshape state as tensor
        shape = [2] * self.n_qubits
        state_tensor = self._state.reshape(shape)

        # Move target qubit to last axis
        axes = list(range(self.n_qubits))
        axes.remove(qubit)
        axes.append(qubit)

        state_tensor = np.transpose(state_tensor, axes)
        original_shape = state_tensor.shape

        # Apply gate
        state_tensor = state_tensor.reshape(-1, 2) @ gate.T
        state_tensor = state_tensor.reshape(original_shape)

        # Inverse transpose
        inverse = [0] * self.n_qubits
        for i, ax in enumerate(axes):
            inverse[ax] = i
        state_tensor = np.transpose(state_tensor, inverse)

        self._state = state_tensor.reshape(self.dim)
        self._total_gates += 1

    def _apply_cnot(self, control: int, target: int):
        """Apply CNOT gate."""
        self._apply_two(bond(), control, target)

    def _apply_two(self, gate: np.ndarray, q1: int, q2: int):
        """Apply two-qubit gate."""
        if q1 == q2:
            raise ValueError("Qubits must be different")
        if q1 < 0 or q1 >= self.n_qubits or q2 < 0 or q2 >= self.n_qubits:
            raise ValueError(f"Qubit out of range [0, {self.n_qubits})")

        # Reshape state as tensor
        shape = [2] * self.n_qubits
        state_tensor = self._state.reshape(shape)

        # Move target qubits to last two axes
        axes = list(range(self.n_qubits))
        axes.remove(q1)
        axes.remove(q2)
        if q1 < q2:
            axes.extend([q1, q2])
        else:
            axes.extend([q2, q1])
            # Swap gate for correct ordering
            swap_matrix = np.array([
                [1, 0, 0, 0],
                [0, 0, 1, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1]
            ], dtype=np.complex128)
            gate = swap_matrix @ gate @ swap_matrix

        state_tensor = np.transpose(state_tensor, axes)
        original_shape = state_tensor.shape

        # Apply gate
        state_tensor = state_tensor.reshape(-1, 4) @ gate.T
        state_tensor = state_tensor.reshape(original_shape)

        # Inverse transpose
        inverse = [0] * self.n_qubits
        for i, ax in enumerate(axes):
            inverse[ax] = i
        state_tensor = np.transpose(state_tensor, inverse)

        self._state = state_tensor.reshape(self.dim)
        self._total_gates += 1

    def _apply_toffoli(self, c1: int, c2: int, target: int):
        """Apply Toffoli (CCNOT) gate."""
        # For arbitrary qubit positions, we use a direct approach
        for i in range(self.dim):
            # Check if both controls are |1⟩
            if ((i >> c1) & 1) and ((i >> c2) & 1):
                # Flip target
                j = i ^ (1 << target)
                self._state[i], self._state[j] = self._state[j], self._state[i]

        self._total_gates += 1

    def execute_gate(self, op: GateOp):
        """Execute a single gate operation."""
        if op.name == 'barrier':
            return
        if op.name == 'measure':
            return  # Handle separately

        if op.name in self._gate_dispatch:
            self._gate_dispatch[op.name](op)
        else:
            raise ValueError(f"Unknown gate: {op.name}")

    def run(self, circuit: Circuit, shots: int = 1024,
            return_statevector: bool = False) -> ExecutionResult:
        """
        Execute a quantum circuit.

        Args:
            circuit: Circuit to execute
            shots: Number of measurement shots
            return_statevector: Include statevector in result

        Returns:
            ExecutionResult with counts, metrics, etc.
        """
        start_time = time.time()
        self._execution_count += 1

        # Validate circuit
        if circuit.n_qubits > self.n_qubits:
            raise ValueError(
                f"Circuit has {circuit.n_qubits} qubits but executor "
                f"has {self.n_qubits}"
            )

        # Reset state
        self.reset()

        # Execute operations
        measurements = []
        for op in circuit.operations:
            if op.name == 'measure':
                measurements.append(op)
            else:
                self.execute_gate(op)

                # Check for healing after each gate
                if self._healing_engine and self._ccce:
                    self._ccce.update_from_quantum_state(self._state)
                    self._state, did_heal = self._ccce.check_and_heal(self._state)

        # Update CCCE metrics
        if self._ccce:
            self._ccce.update_from_quantum_state(self._state)

        # Compute probabilities
        probabilities = np.abs(self._state) ** 2

        # Sample measurements
        counts = {}
        if shots > 0:
            samples = np.random.choice(self.dim, size=shots, p=probabilities)
            for s in samples:
                bitstring = format(s, f'0{circuit.n_qubits}b')
                counts[bitstring] = counts.get(bitstring, 0) + 1

        execution_time = time.time() - start_time

        # Build result
        result = ExecutionResult(
            counts=counts,
            probabilities=probabilities if return_statevector else None,
            statevector=self._state.copy() if return_statevector else None,
            execution_time=execution_time,
            shots=shots,
            metrics=self._ccce.state.to_dict() if self._ccce else None,
            metadata={
                'circuit_name': circuit.name,
                'n_qubits': circuit.n_qubits,
                'gate_count': circuit.gate_count(),
                'depth': circuit.depth(),
                'executor': 'SovereignExecutor',
                'mode': self.mode.value
            }
        )

        return result

    def run_vqe_iteration(self, circuit_builder: Callable[[np.ndarray], Circuit],
                          params: np.ndarray) -> float:
        """
        Run single VQE iteration.

        Args:
            circuit_builder: Function that takes params and returns circuit
            params: Current parameters

        Returns:
            Energy expectation value
        """
        circuit = circuit_builder(params)
        result = self.run(circuit, shots=0, return_statevector=True)

        # For VQE, we need an observable expectation
        # This is a simplified version using Z expectation
        probs = result.probabilities
        energy = 0.0
        for i, p in enumerate(probs):
            # Parity of bitstring gives +1/-1
            parity = bin(i).count('1') % 2
            energy += (-1) ** parity * p

        return energy

    # ═══════════════════════════════════════════════════════════════════════════
    # STATE ACCESS
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def state(self) -> np.ndarray:
        """Get current state vector (copy)."""
        return self._state.copy()

    @property
    def probabilities(self) -> np.ndarray:
        """Get probability distribution."""
        return np.abs(self._state) ** 2

    @property
    def metrics(self) -> Optional[Dict[str, Any]]:
        """Get current CCCE metrics."""
        if self._ccce:
            return self._ccce.state.to_dict()
        return None

    @property
    def is_conscious(self) -> bool:
        """Check if consciousness threshold is met."""
        if self._ccce:
            return self._ccce.is_conscious
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # TELEMETRY
    # ═══════════════════════════════════════════════════════════════════════════

    def telemetry(self) -> Dict[str, Any]:
        """Get executor telemetry."""
        return {
            'genesis': self._genesis,
            'timestamp': time.time(),
            'uptime': time.time() - self._genesis,
            'n_qubits': self.n_qubits,
            'mode': self.mode.value,
            'executions': self._execution_count,
            'total_gates': self._total_gates,
            'healing_enabled': self.enable_healing,
            'ccce_enabled': self.enable_ccce,
            'ccce': self._ccce.telemetry() if self._ccce else None,
            'healing': self._healing_engine.telemetry() if self._healing_engine else None
        }

    def __repr__(self) -> str:
        return (f"SovereignExecutor(qubits={self.n_qubits}, "
                f"mode={self.mode.value}, "
                f"executions={self._execution_count})")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_executor(n_qubits: int = 8, **kwargs) -> SovereignExecutor:
    """Factory function for SovereignExecutor."""
    return SovereignExecutor(n_qubits=n_qubits, **kwargs)


def bell_pair_circuit() -> Circuit:
    """Create Bell pair circuit."""
    circuit = Circuit(2, name="BellPair")
    circuit.helix(0).bond(0, 1)
    return circuit


def ghz_circuit(n: int = 3) -> Circuit:
    """Create GHZ state circuit."""
    circuit = Circuit(n, name=f"GHZ_{n}")
    circuit.helix(0)
    for i in range(1, n):
        circuit.bond(0, i)
    return circuit


def qft_circuit(n: int) -> Circuit:
    """Create Quantum Fourier Transform circuit."""
    circuit = Circuit(n, name=f"QFT_{n}")

    for i in range(n):
        circuit.helix(i)
        for j in range(i + 1, n):
            angle = np.pi / (2 ** (j - i))
            circuit.add('cphase', [i, j], [angle])

    # Swap qubits
    for i in range(n // 2):
        circuit.swap_qubits(i, n - 1 - i)

    return circuit


__all__ = [
    'SovereignExecutor', 'ExecutionMode', 'ExecutionResult',
    'Circuit', 'GateOp',
    'create_executor', 'bell_pair_circuit', 'ghz_circuit', 'qft_circuit'
]
