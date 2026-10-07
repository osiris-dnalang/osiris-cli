"""Quantum circuit execution and backend management."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class QuantumCircuit:
    """Representation of a quantum circuit."""
    
    num_qubits: int
    gates: List[Dict[str, Any]] = field(default_factory=list)
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_gate(self, gate_type: str, **kwargs: Any) -> "QuantumCircuit":
        """Add a gate to the circuit."""
        gate = {"type": gate_type, **kwargs}
        self.gates.append(gate)
        return self
    
    def h(self, target: int) -> "QuantumCircuit":
        """Add Hadamard gate."""
        return self.add_gate("h", target=target)
    
    def x(self, target: int) -> "QuantumCircuit":
        """Add Pauli-X gate."""
        return self.add_gate("x", target=target)
    
    def y(self, target: int) -> "QuantumCircuit":
        """Add Pauli-Y gate."""
        return self.add_gate("y", target=target)
    
    def z(self, target: int) -> "QuantumCircuit":
        """Add Pauli-Z gate."""
        return self.add_gate("z", target=target)
    
    def cx(self, control: int, target: int) -> "QuantumCircuit":
        """Add CNOT gate."""
        return self.add_gate("cx", control=control, target=target)
    
    def to_qiskit(self) -> Any:
        """Convert to Qiskit QuantumCircuit (requires qiskit)."""
        try:
            from qiskit import QuantumCircuit as QiskitCircuit
            
            qc = QiskitCircuit(self.num_qubits, self.num_qubits)
            qc.name = self.name or "dnalang_circuit"
            
            for gate in self.gates:
                gate_type = gate["type"].lower()
                if gate_type == "h":
                    qc.h(gate["target"])
                elif gate_type == "x":
                    qc.x(gate["target"])
                elif gate_type == "y":
                    qc.y(gate["target"])
                elif gate_type == "z":
                    qc.z(gate["target"])
                elif gate_type == "cx":
                    qc.cx(gate["control"], gate["target"])
                elif gate_type == "measure":
                    qc.measure(gate.get("target", range(self.num_qubits)), 
                             gate.get("classical", range(self.num_qubits)))
                else:
                    raise ValueError(f"Unsupported gate type: {gate_type}")
            
            # Add measurements if not already present
            if not any(g["type"] == "measure" for g in self.gates):
                qc.measure_all()
            
            return qc
        except ImportError:
            raise ImportError("Qiskit is required for quantum circuit execution")
    
    def to_json(self) -> str:
        """Serialize circuit to JSON."""
        return json.dumps({
            "num_qubits": self.num_qubits,
            "gates": self.gates,
            "name": self.name,
            "metadata": self.metadata,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "QuantumCircuit":
        """Deserialize circuit from JSON."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class QuantumResult:
    """Result from quantum circuit execution."""
    
    counts: Dict[str, int]
    backend: str
    shots: int
    execution_time: float
    success: bool = True
    lambda_phi_conserved: Optional[float] = None
    ccce_metric: Optional[float] = None
    job_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_probabilities(self) -> Dict[str, float]:
        """Convert counts to probabilities."""
        total = sum(self.counts.values())
        return {state: count / total for state, count in self.counts.items()}
    
    def get_most_frequent(self, n: int = 1) -> List[tuple]:
        """Get n most frequent measurement outcomes."""
        sorted_counts = sorted(self.counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:n]


class QuantumBackend:
    """Interface to quantum computing backends."""
    
    def __init__(self, config):
        """Initialize quantum backend."""
        from .config import QuantumConfig
        self.config: QuantumConfig = config
        self._backend = None
        self._service = None
        
    async def execute(
        self,
        circuit: QuantumCircuit,
        shots: int,
        backend: str,
        optimization_level: int,
    ) -> QuantumResult:
        """Execute quantum circuit on specified backend."""
        import time
        
        start_time = time.time()
        
        try:
            # Convert to Qiskit circuit
            qc = circuit.to_qiskit()
            
            # Execute based on backend type
            if backend == "aer_simulator" or backend.startswith("sim"):
                result = await self._execute_simulator(qc, shots)
            elif backend.startswith("ibm"):
                result = await self._execute_ibm(qc, shots, backend, optimization_level)
            else:
                raise ValueError(f"Unsupported backend: {backend}")
            
            execution_time = time.time() - start_time
            
            return QuantumResult(
                counts=result,
                backend=backend,
                shots=shots,
                execution_time=execution_time,
                success=True,
            )
            
        except Exception as e:
            logger.error("Quantum execution failed on %s: %s", backend, e)
            execution_time = time.time() - start_time
            return QuantumResult(
                counts={},
                backend=backend,
                shots=shots,
                execution_time=execution_time,
                success=False,
                metadata={"error": str(e)},
            )
    
    async def _execute_simulator(self, qc, shots: int) -> Dict[str, int]:
        """Execute on local simulator."""
        from qiskit_aer import AerSimulator
        
        simulator = AerSimulator()
        job = simulator.run(qc, shots=shots)
        result = job.result()
        counts = result.get_counts()
        
        return dict(counts)
    
    async def _execute_ibm(
        self,
        qc,
        shots: int,
        backend: str,
        optimization_level: int,
    ) -> Dict[str, int]:
        """Execute on IBM Quantum hardware."""
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService, Session, SamplerV2
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        except ImportError:
            raise ImportError(
                "qiskit-ibm-runtime is required for IBM Quantum execution. "
                "Install with: pip install qiskit-ibm-runtime"
            )
        
        # Initialize service
        if not self._service:
            token = self.config.api_token or os.environ.get(self.config.api_token_env)
            if not token:
                raise ValueError("IBM Quantum API token not found")
            
            self._service = QiskitRuntimeService(channel="ibm_quantum", token=token)
        
        # Get backend
        backend_obj = self._service.backend(backend)
        
        # Transpile circuit
        pm = generate_preset_pass_manager(optimization_level=optimization_level, backend=backend_obj)
        transpiled_qc = pm.run(qc)
        
        # Execute with Sampler
        with Session(service=self._service, backend=backend) as session:
            sampler = SamplerV2(session=session)
            job = sampler.run([transpiled_qc], shots=shots)
            result = job.result()
            
            # Extract counts from PrimitiveResult
            pub_result = result[0]
            counts_dict = {}
            
            if hasattr(pub_result.data, 'meas'):
                # Convert bit arrays to counts
                from collections import Counter
                measurements = pub_result.data.meas.get_counts()
                counts_dict = dict(measurements)
            
            return counts_dict
