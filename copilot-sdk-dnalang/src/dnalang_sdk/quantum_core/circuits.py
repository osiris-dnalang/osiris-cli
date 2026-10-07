"""
Quantum Circuit Generation
===========================

Convert DNA-Lang organisms to executable quantum circuits.
"""

from typing import List, Optional, Dict, Any
import numpy as np

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit import Parameter
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    QuantumCircuit = None

from ..organisms.organism import Organism
from ..organisms.gene import Gene
from .constants import THETA_LOCK, THETA_PC_RAD, CHI_PC


class CircuitGenerator:
    """Generate quantum circuits from DNA-Lang organisms."""
    
    def __init__(self, organism: Organism):
        """Initialize generator.
        
        Args:
            organism: Organism to convert
        """
        if not QISKIT_AVAILABLE:
            raise ImportError("Qiskit required for quantum circuit generation")
        
        self.organism = organism
        self.n_qubits = len(organism.genome)
    
    def to_circuit(
        self,
        method: str = 'gene_encoding',
        include_measurement: bool = True
    ) -> QuantumCircuit:
        """Convert organism to quantum circuit.
        
        Args:
            method: 'gene_encoding' or 'entanglement_structure'
            include_measurement: Whether to add measurements
            
        Returns:
            QuantumCircuit
        """
        if method == 'gene_encoding':
            return self._gene_encoding_circuit(include_measurement)
        elif method == 'entanglement_structure':
            return self._entanglement_circuit(include_measurement)
        else:
            raise ValueError(f"Unknown circuit generation method: {method}")
    
    def _gene_encoding_circuit(self, measure: bool = True) -> QuantumCircuit:
        """Encode genes as quantum rotations.
        
        Each gene's expression level determines rotation angle.
        
        Args:
            measure: Add measurement gates
            
        Returns:
            QuantumCircuit
        """
        qr = QuantumRegister(self.n_qubits, 'q')
        cr = ClassicalRegister(self.n_qubits, 'c') if measure else None
        qc = QuantumCircuit(qr, cr) if measure else QuantumCircuit(qr)
        
        # Initialize with Hadamard for superposition
        qc.h(qr)
        qc.barrier()
        
        # Encode each gene as rotation
        for i, gene in enumerate(self.organism.genome):
            # Expression level determines rotation angle
            angle = gene.expression * np.pi
            qc.ry(angle, qr[i])
            qc.rz(angle * 0.5, qr[i])
        
        qc.barrier()
        
        # Add entanglement based on organism structure
        for i in range(self.n_qubits - 1):
            qc.cx(qr[i], qr[i + 1])
        
        qc.barrier()
        
        # Measurements
        if measure:
            qc.measure(qr, cr)
        
        return qc
    
    def _entanglement_circuit(self, measure: bool = True) -> QuantumCircuit:
        """Create entanglement-based circuit.
        
        Args:
            measure: Add measurement gates
            
        Returns:
            QuantumCircuit
        """
        qr = QuantumRegister(self.n_qubits, 'q')
        cr = ClassicalRegister(self.n_qubits, 'c') if measure else None
        qc = QuantumCircuit(qr, cr) if measure else QuantumCircuit(qr)
        
        # Create GHZ-like state
        qc.h(qr[0])
        for i in range(self.n_qubits - 1):
            qc.cx(qr[i], qr[i + 1])
        
        qc.barrier()
        
        # Apply gene-specific operations
        for i, gene in enumerate(self.organism.genome):
            if gene.expression > 0.5:
                qc.rz(THETA_PC_RAD * gene.expression, qr[i])
        
        qc.barrier()
        
        if measure:
            qc.measure(qr, cr)
        
        return qc
    
    def to_aeterna_porta_circuit(
        self,
        n_left: int = 50,
        n_right: int = 50,
        n_anc: int = 20,
        depth: int = 20
    ) -> QuantumCircuit:
        """Generate AETERNA-PORTA style circuit.
        
        Args:
            n_left: Left partition qubits
            n_right: Right partition qubits
            n_anc: Ancilla qubits
            depth: Circuit depth
            
        Returns:
            QuantumCircuit
        """
        n_total = n_left + n_right + n_anc
        
        qr_l = QuantumRegister(n_left, 'L')
        qr_r = QuantumRegister(n_right, 'R')
        qr_a = QuantumRegister(n_anc, 'Anc')
        cr = ClassicalRegister(n_total, 'c')
        
        qc = QuantumCircuit(qr_l, qr_r, qr_a, cr)
        
        # Initialize superposition
        qc.h(qr_l)
        qc.h(qr_r)
        
        qc.barrier()
        
        # Apply layered structure
        for layer in range(depth):
            # Entangle within partitions
            for i in range(n_left - 1):
                qc.cx(qr_l[i], qr_l[i + 1])
            
            for i in range(n_right - 1):
                qc.cx(qr_r[i], qr_r[i + 1])
            
            # Cross-partition entanglement via ancilla
            for i in range(n_anc):
                l_idx = i % n_left
                r_idx = i % n_right
                qc.ccx(qr_l[l_idx], qr_r[r_idx], qr_a[i])
            
            # Apply rotations based on genes
            if layer < len(self.organism.genome):
                gene = self.organism.genome.genes[layer]
                angle = gene.expression * THETA_PC_RAD
                
                # Apply to random qubits
                qc.ry(angle, qr_l[layer % n_left])
                qc.ry(angle, qr_r[layer % n_right])
            
            qc.barrier()
        
        # Final measurement
        qc.measure_all()
        
        return qc


def to_circuit(
    organism: Organism,
    method: str = 'gene_encoding',
    **kwargs
) -> QuantumCircuit:
    """Convert organism to quantum circuit.
    
    Args:
        organism: Organism to convert
        method: Circuit generation method
        **kwargs: Additional circuit parameters
        
    Returns:
        QuantumCircuit
    """
    generator = CircuitGenerator(organism)
    return generator.to_circuit(method=method, **kwargs)
