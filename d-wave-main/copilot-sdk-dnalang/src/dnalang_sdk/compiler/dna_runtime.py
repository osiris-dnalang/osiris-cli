#!/usr/bin/env python3
"""
dna_runtime.py - DNA-Lang Quantum Runtime
Executes quantum circuits on IBM Quantum hardware and simulators
"""

import os
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

from .dna_ir import QuantumCircuitIR


# ==========================================
# STATEVECTOR FALLBACK (when qiskit-aer is absent)
# ==========================================

class _StatevectorBackend:
    """Minimal sampling backend using Qiskit Statevector (no Aer needed)."""
    name = "statevector_fallback"

    def __init__(self, shots: int = 1024):
        self._shots = shots

    def run(self, circuit, shots=None):
        from qiskit.quantum_info import Statevector
        shots = shots or self._shots
        meas_circuit = circuit.remove_final_measurements(inplace=False)
        sv = Statevector.from_instruction(meas_circuit)
        counts = sv.sample_counts(shots)
        return _FakeResult(dict(counts))


class _FakeResult:
    """Wraps a counts dict to look like a Qiskit result."""
    def __init__(self, counts):
        self._counts = counts

    def get_counts(self):
        return self._counts

# ==========================================
# RUNTIME CONFIGURATION
# ==========================================

@dataclass
class RuntimeConfig:
    """Runtime configuration"""
    
    # IBM Quantum settings
    ibm_token: Optional[str] = None
    backend_name: str = "ibm_brisbane"
    use_simulator: bool = False
    
    # Execution settings
    shots: int = 1024
    optimization_level: int = 3
    resilience_level: int = 1
    
    # Timeouts
    max_execution_time: int = 3600  # seconds
    job_check_interval: int = 10    # seconds
    
    # Advanced options
    dynamical_decoupling: bool = True
    measurement_mitigation: bool = True
    use_sabre_layout: bool = True
    
    def __post_init__(self):
        """Load IBM token from environment if not provided"""
        if not self.ibm_token:
            self.ibm_token = os.environ.get('IBM_QUANTUM_TOKEN')

@dataclass
class ExecutionResult:
    """Result of quantum circuit execution"""
    
    # Execution metadata
    job_id: Optional[str] = None
    backend: str = ""
    status: str = "unknown"
    execution_time: float = 0.0
    timestamp: str = ""
    
    # Results
    counts: Dict[str, int] = field(default_factory=dict)
    memory: Optional[List[str]] = None
    
    # Metrics
    fidelity: float = 0.0
    success_rate: float = 0.0
    
    # Physics measurements
    lambda_measured: float = 0.0
    gamma_measured: float = 0.0
    phi_measured: float = 0.0
    
    # Error information
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'backend': self.backend,
            'status': self.status,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp,
            'counts': self.counts,
            'memory': self.memory,
            'metrics': {
                'fidelity': self.fidelity,
                'success_rate': self.success_rate
            },
            'physics': {
                'lambda_coherence': self.lambda_measured,
                'gamma_decoherence': self.gamma_measured,
                'phi_integrated_info': self.phi_measured
            },
            'error': self.error
        }

# ==========================================
# QUANTUM RUNTIME ENGINE
# ==========================================

class QuantumRuntime:
    """Executes quantum circuits on IBM Quantum"""
    
    def __init__(self, config: Optional[RuntimeConfig] = None):
        self.config = config or RuntimeConfig()
        self.qiskit_available = False
        self.service = None
        
        # Try to import Qiskit
        try:
            import qiskit
            from qiskit import transpile
            from qiskit_ibm_runtime import QiskitRuntimeService
            
            self.qiskit_available = True
            self.qiskit = qiskit
            self.transpile = transpile
            
            # Initialize IBM Quantum service
            if self.config.ibm_token:
                try:
                    self.service = QiskitRuntimeService(
                        channel="ibm_quantum",
                        token=self.config.ibm_token
                    )
                except Exception as e:
                    print(f"Warning: Could not initialize IBM Quantum service: {e}")
                    self.config.use_simulator = True
        
        except ImportError:
            print("Warning: Qiskit not available. Install with: pip install qiskit qiskit-ibm-runtime")
            self.qiskit_available = False
    
    def execute(self, circuit: QuantumCircuitIR) -> ExecutionResult:
        """
        Execute quantum circuit
        
        Args:
            circuit: Circuit to execute
            
        Returns:
            Execution result
        """
        if not self.qiskit_available:
            return self._mock_execution(circuit)
        
        try:
            start_time = time.time()
            
            # Convert to Qiskit circuit
            qc = circuit.to_qiskit()
            
            # Get backend
            if self.config.use_simulator:
                backend = self._get_simulator_backend()
            else:
                backend = self._get_hardware_backend()
            
            # Transpile circuit
            transpiled_qc = self.transpile(
                qc,
                backend=backend,
                optimization_level=self.config.optimization_level
            )
            
            # Execute
            if self.config.use_simulator:
                result = self._execute_simulator(transpiled_qc, backend)
            else:
                result = self._execute_hardware(transpiled_qc, backend)
            
            execution_time = time.time() - start_time
            
            # Process results
            execution_result = self._process_results(
                result, 
                backend.name if hasattr(backend, 'name') else "simulator",
                execution_time
            )
            
            # Measure physics parameters
            execution_result = self._measure_physics(execution_result, circuit)
            
            return execution_result
        
        except Exception as e:
            return ExecutionResult(
                status="error",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    def _get_simulator_backend(self):
        """Get simulator backend — prefers Aer, falls back to Qiskit built-in."""
        try:
            from qiskit_aer import AerSimulator
            return AerSimulator()
        except ImportError:
            pass
        # Qiskit 2.x built-in statevector simulator
        try:
            from qiskit.providers.basic_provider import BasicSimulator
            return BasicSimulator()
        except ImportError:
            pass
        # Absolute fallback — generic backend from qiskit
        from qiskit.quantum_info import Statevector
        return _StatevectorBackend(self.config.shots)
    
    def _get_hardware_backend(self):
        """Get IBM Quantum hardware backend"""
        if not self.service:
            raise RuntimeError("IBM Quantum service not initialized")
        
        # Get backend by name
        backend = self.service.backend(self.config.backend_name)
        return backend
    
    def _execute_simulator(self, circuit, backend):
        """Execute on simulator"""
        job = backend.run(circuit, shots=self.config.shots)
        return job.result()
    
    def _execute_hardware(self, circuit, backend):
        """Execute on hardware"""
        from qiskit_ibm_runtime import Session, SamplerV2 as Sampler
        
        with Session(backend=backend) as session:
            sampler = Sampler(session=session)
            
            # Run with error mitigation
            job = sampler.run([circuit], shots=self.config.shots)
            
            # Wait for completion
            result = job.result()
        
        return result
    
    def _process_results(self, result, backend_name: str, execution_time: float) -> ExecutionResult:
        """Process quantum execution results"""
        
        # Extract counts
        try:
            if hasattr(result, 'get_counts'):
                counts = result.get_counts()
            elif hasattr(result, 'quasi_dists'):
                # SamplerV2 result format
                quasi_dist = result.quasi_dists[0]
                counts = {bin(k)[2:].zfill(2): int(v * self.config.shots) 
                         for k, v in quasi_dist.items()}
            else:
                counts = {}
        except Exception as e:
            print(f"Warning: Could not extract counts: {e}")
            counts = {}
        
        # Calculate success rate (probability of |00...0> state)
        total_shots = sum(counts.values()) if counts else self.config.shots
        success_count = counts.get('0' * len(list(counts.keys())[0] if counts else 2), 0)
        success_rate = success_count / total_shots if total_shots > 0 else 0.0
        
        return ExecutionResult(
            job_id=str(id(result)),
            backend=backend_name,
            status="completed",
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            counts=counts,
            success_rate=success_rate,
            fidelity=success_rate  # Simplified fidelity estimate
        )
    
    def _measure_physics(self, result: ExecutionResult, circuit: QuantumCircuitIR) -> ExecutionResult:
        """
        Measure physical parameters from execution
        
        Estimates Λ, Γ, and Φ from measurement statistics
        """
        if not result.counts:
            return result
        
        # Calculate entanglement from correlations
        total_shots = sum(result.counts.values())
        
        # Estimate λ (coherence) from state purity
        probabilities = np.array([count / total_shots for count in result.counts.values()])
        purity = np.sum(probabilities ** 2)
        result.lambda_measured = purity * 2.176435e-8 * 1e8  # Scale to LAMBDA_PHI
        
        # Estimate Γ (decoherence) from measurement entropy
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        max_entropy = np.log2(len(result.counts))
        result.gamma_measured = entropy / max_entropy if max_entropy > 0 else 0.0
        
        # Estimate Φ (integrated information) from correlation structure
        # Simplified: use mutual information between qubit pairs
        if len(result.counts) > 1:
            # Calculate mutual information heuristically
            result.phi_measured = self._estimate_mutual_information(result.counts)
        else:
            result.phi_measured = 0.0
        
        return result
    
    def _estimate_mutual_information(self, counts: Dict[str, int]) -> float:
        """Estimate mutual information from measurement counts"""
        total = sum(counts.values())
        
        # Convert counts to probabilities
        probs = {state: count / total for state, count in counts.items()}
        
        # Calculate marginal distributions for first and second qubit
        p0 = sum(prob for state, prob in probs.items() if state[0] == '0')
        p1 = sum(prob for state, prob in probs.items() if state[-1] == '0')
        
        # Calculate joint distribution
        p00 = probs.get('00', 0)
        p01 = probs.get('01', 0)
        p10 = probs.get('10', 0)
        p11 = probs.get('11', 0)
        
        # Mutual information I(X:Y) = H(X) + H(Y) - H(X,Y)
        h_x = -(p0 * np.log2(p0 + 1e-10) + (1-p0) * np.log2(1-p0 + 1e-10))
        h_y = -(p1 * np.log2(p1 + 1e-10) + (1-p1) * np.log2(1-p1 + 1e-10))
        h_xy = -(p00 * np.log2(p00 + 1e-10) + 
                 p01 * np.log2(p01 + 1e-10) +
                 p10 * np.log2(p10 + 1e-10) + 
                 p11 * np.log2(p11 + 1e-10))
        
        mutual_info = h_x + h_y - h_xy
        return max(0.0, mutual_info)  # Ensure non-negative
    
    def _mock_execution(self, circuit: QuantumCircuitIR) -> ExecutionResult:
        """Mock execution when Qiskit not available"""
        
        # Simulate simple results
        counts = {
            '00': int(self.config.shots * 0.5),
            '01': int(self.config.shots * 0.2),
            '10': int(self.config.shots * 0.2),
            '11': int(self.config.shots * 0.1)
        }
        
        return ExecutionResult(
            job_id="mock_" + circuit.lineage_hash,
            backend="mock_simulator",
            status="completed",
            execution_time=0.1,
            timestamp=datetime.now().isoformat(),
            counts=counts,
            success_rate=0.5,
            fidelity=0.85,
            lambda_measured=0.001,
            gamma_measured=0.3,
            phi_measured=0.6
        )

# ==========================================
# BACKEND CALIBRATION
# ==========================================

class BackendCalibration:
    """Fetch and process backend calibration data"""
    
    def __init__(self, runtime: QuantumRuntime):
        self.runtime = runtime
    
    def get_calibration(self, backend_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get backend calibration data
        
        Args:
            backend_name: Backend to query (default: config backend)
            
        Returns:
            Calibration data dictionary
        """
        if not self.runtime.service:
            return self._mock_calibration()
        
        try:
            backend_name = backend_name or self.runtime.config.backend_name
            backend = self.runtime.service.backend(backend_name)
            
            # Get properties
            props = backend.properties()
            
            # Extract calibration data
            calibration = {
                'backend_name': backend_name,
                'num_qubits': backend.num_qubits,
                'avg_single_gate_error': np.mean([
                    props.gate_error('sx', [i]) 
                    for i in range(backend.num_qubits)
                ]),
                'avg_two_gate_error': self._compute_avg_two_gate_error(props, backend),
                'avg_readout_error': np.mean([
                    props.readout_error(i) 
                    for i in range(backend.num_qubits)
                ]),
                'avg_t1': np.mean([
                    props.t1(i) 
                    for i in range(backend.num_qubits)
                ]),
                'avg_t2': np.mean([
                    props.t2(i) 
                    for i in range(backend.num_qubits)
                ]),
                'timestamp': datetime.now().isoformat()
            }
            
            return calibration
        
        except Exception as e:
            print(f"Warning: Could not fetch calibration: {e}")
            return self._mock_calibration()
    
    def _compute_avg_two_gate_error(self, props, backend) -> float:
        """Compute average two-qubit gate error"""
        errors = []
        
        for gate in ['cx', 'ecr']:
            for pair in backend.configuration().coupling_map:
                try:
                    error = props.gate_error(gate, pair)
                    errors.append(error)
                except Exception:
                    pass
        
        return np.mean(errors) if errors else 0.01
    
    def _mock_calibration(self) -> Dict[str, Any]:
        """Mock calibration data"""
        return {
            'backend_name': 'mock_backend',
            'num_qubits': 5,
            'avg_single_gate_error': 0.001,
            'avg_two_gate_error': 0.01,
            'avg_readout_error': 0.02,
            'avg_t1': 100e-6,  # 100 μs
            'avg_t2': 50e-6,   # 50 μs
            'avg_gate_error': 0.005,
            'timestamp': datetime.now().isoformat()
        }

# ==========================================
# MAIN INTERFACE
# ==========================================

def execute_circuit(circuit: QuantumCircuitIR,
                   backend: str = "ibm_brisbane",
                   shots: int = 1024,
                   use_simulator: bool = False,
                   ibm_token: Optional[str] = None) -> ExecutionResult:
    """
    Execute quantum circuit
    
    Args:
        circuit: Circuit to execute
        backend: Backend name
        shots: Number of shots
        use_simulator: Use simulator instead of hardware
        ibm_token: IBM Quantum token
        
    Returns:
        Execution result
    """
    config = RuntimeConfig(
        ibm_token=ibm_token,
        backend_name=backend,
        shots=shots,
        use_simulator=use_simulator
    )
    
    runtime = QuantumRuntime(config)
    return runtime.execute(circuit)

def get_backend_calibration(backend: str = "ibm_brisbane",
                           ibm_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get backend calibration data
    
    Args:
        backend: Backend name
        ibm_token: IBM Quantum token
        
    Returns:
        Calibration data
    """
    config = RuntimeConfig(
        ibm_token=ibm_token,
        backend_name=backend
    )
    
    runtime = QuantumRuntime(config)
    calibration = BackendCalibration(runtime)
    
    return calibration.get_calibration()

if __name__ == "__main__":
    from dna_parser import parse_dna_lang
    from dna_ir import compile_to_ir
    
    # Test execution
    test_source = """
organism bell_test {
    quantum_state {
        helix(q[0]);
        bond(q[0], q[1]);
        measure(q[0]);
        measure(q[1]);
    }
    
    fitness = phi;
}
"""
    
    print("=== Quantum Runtime Test ===")
    organisms = parse_dna_lang(test_source)
    
    for organism in organisms:
        print(f"\nExecuting organism: {organism.name}")
        circuit = compile_to_ir(organism)
        
        # Execute on simulator
        result = execute_circuit(circuit, use_simulator=True, shots=1024)
        
        print(f"\nExecution Result:")
        print(f"  Backend: {result.backend}")
        print(f"  Status: {result.status}")
        print(f"  Execution time: {result.execution_time:.3f}s")
        print(f"  Success rate: {result.success_rate:.3f}")
        print(f"  Fidelity: {result.fidelity:.3f}")
        
        print(f"\nPhysics Measurements:")
        print(f"  λ-coherence: {result.lambda_measured:.6f}")
        print(f"  Γ-decoherence: {result.gamma_measured:.6f}")
        print(f"  Φ-integrated info: {result.phi_measured:.6f}")
        
        print(f"\nMeasurement counts:")
        for state, count in sorted(result.counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  |{state}>: {count}")
