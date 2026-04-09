"""
Quantum Execution on IBM Quantum Hardware
========================================

Execute DNA-Lang organisms on real quantum processors.
"""

from typing import Optional, Dict, Any, List
import os
import json
from datetime import datetime

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

from ..organisms.organism import Organism
from .circuits import to_circuit
from .constants import LAMBDA_PHI, CHI_PC


class QuantumResult:
    """Result from quantum execution."""
    
    def __init__(
        self,
        organism: Organism,
        counts: Dict[str, int],
        job_id: str,
        backend_name: str,
        shots: int,
        lambda_phi: float = LAMBDA_PHI
    ):
        """Initialize result.
        
        Args:
            organism: Executed organism
            counts: Measurement counts
            job_id: IBM job ID
            backend_name: Backend used
            shots: Number of shots
            lambda_phi: Lambda phi value
        """
        self.organism = organism
        self.counts = counts
        self.job_id = job_id
        self.backend_name = backend_name
        self.shots = shots
        self.lambda_phi = lambda_phi
        self.timestamp = datetime.now().isoformat()
        
        # Calculate metrics
        self.num_unique_states = len(counts)
        self.total_counts = sum(counts.values())
        self.ccce = self._calculate_ccce()
    
    def _calculate_ccce(self) -> Dict[str, Any]:
        """Calculate CCCE metrics (Consciousness, Coherence, Coupling, Emergence).
        
        Returns:
            CCCE metrics dictionary
        """
        # Phi: Integrated information (from state diversity)
        phi = self.num_unique_states / self.total_counts
        
        # Lambda: Coherence measure
        lambda_val = CHI_PC  # Default
        
        # Gamma: Decoherence rate (inverse of state concentration)
        sorted_counts = sorted(self.counts.values(), reverse=True)
        if sorted_counts:
            top_state_prob = sorted_counts[0] / self.total_counts
            gamma = 1.0 - top_state_prob
        else:
            gamma = 1.0
        
        # Xi: Emergence metric
        xi = phi * lambda_val / (gamma + 1e-6)
        
        # Consciousness threshold
        conscious = phi > 0.7 and gamma < 0.5
        
        # Stability
        stable = gamma < 0.3
        
        return {
            'phi': phi,
            'lambda': lambda_val,
            'gamma': gamma,
            'xi': xi,
            'conscious': conscious,
            'stable': stable
        }
    
    def to_dict(self) -> dict:
        """Serialize result to dictionary."""
        return {
            'organism': self.organism.name,
            'job_id': self.job_id,
            'backend': self.backend_name,
            'shots': self.shots,
            'timestamp': self.timestamp,
            'lambda_phi': self.lambda_phi,
            'num_unique_states': self.num_unique_states,
            'total_counts': self.total_counts,
            'ccce': self.ccce,
            'counts_sample': dict(list(self.counts.items())[:20])  # Top 20 states
        }
    
    def save(self, filepath: str):
        """Save result to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class QuantumExecutor:
    """Execute organisms on IBM Quantum hardware."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        instance: str = "ibm-q/open/main"
    ):
        """Initialize executor.
        
        Args:
            token: IBM Quantum token (or use IBM_QUANTUM_TOKEN env var)
            instance: IBM Quantum instance
        """
        if not QISKIT_AVAILABLE:
            raise ImportError("Qiskit and qiskit-ibm-runtime required")
        
        self.token = token or os.environ.get('IBM_QUANTUM_TOKEN')
        if not self.token:
            raise ValueError("IBM Quantum token required")
        
        self.service = QiskitRuntimeService(
            channel="ibm_quantum",
            token=self.token,
            instance=instance
        )
        self.instance = instance
    
    def execute(
        self,
        organism: Organism,
        backend_name: str = "ibmq_qasm_simulator",
        shots: int = 8192,
        optimization_level: int = 3,
        method: str = 'gene_encoding'
    ) -> QuantumResult:
        """Execute organism on quantum hardware.
        
        Args:
            organism: Organism to execute
            backend_name: IBM backend name
            shots: Number of measurement shots
            optimization_level: Transpilation optimization level
            method: Circuit generation method
            
        Returns:
            QuantumResult
        """
        # Get backend
        backend = self.service.backend(backend_name)
        
        # Generate circuit
        circuit = to_circuit(organism, method=method)
        
        # Transpile
        transpiled = transpile(
            circuit,
            backend=backend,
            optimization_level=optimization_level
        )
        
        # Execute with Sampler
        with Session(service=self.service, backend=backend) as session:
            sampler = Sampler(session=session)
            job = sampler.run([transpiled], shots=shots)
            result = job.result()
        
        # Extract counts
        counts = result.quasi_dists[0].binary_probabilities()
        counts_int = {k: int(v * shots) for k, v in counts.items()}
        
        # Create result object
        qresult = QuantumResult(
            organism=organism,
            counts=counts_int,
            job_id=job.job_id(),
            backend_name=backend_name,
            shots=shots,
            lambda_phi=organism.lambda_phi
        )
        
        # Log to organism
        organism._log_event("quantum_execution", {
            "backend": backend_name,
            "job_id": job.job_id(),
            "shots": shots,
            "ccce": qresult.ccce
        })
        
        return qresult
    
    def list_backends(self, simulator: bool = False) -> List[str]:
        """List available backends.
        
        Args:
            simulator: Include simulators
            
        Returns:
            List of backend names
        """
        backends = self.service.backends(simulator=simulator)
        return [b.name for b in backends]


def execute_organism(
    organism: Organism,
    backend: str = "ibmq_qasm_simulator",
    shots: int = 8192,
    token: Optional[str] = None
) -> QuantumResult:
    """Execute organism on quantum hardware (convenience function).
    
    Args:
        organism: Organism to execute
        backend: Backend name
        shots: Number of shots
        token: IBM Quantum token
        
    Returns:
        QuantumResult
    """
    executor = QuantumExecutor(token=token)
    return executor.execute(organism, backend_name=backend, shots=shots)
