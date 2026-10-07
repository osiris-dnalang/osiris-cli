#!/usr/bin/env python3
"""
dna_ir.py - DNA-Lang Intermediate Representation
Transforms parsed AST into executable quantum circuit IR
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import numpy as np

from .dna_parser import (
    OrganismNode, GenomeNode, GeneNode, QuantumStateNode,
    QuantumOpNode, ControlNode, ExpressionNode
)

# ==========================================
# IR TYPES AND STRUCTURES
# ==========================================

class IROpType(Enum):
    """IR operation types"""
    # Single-qubit gates
    H = "h"           # Hadamard
    X = "x"           # Pauli-X
    Y = "y"           # Pauli-Y
    Z = "z"           # Pauli-Z
    S = "s"           # S gate (phase)
    T = "t"           # T gate
    RX = "rx"         # Rotation-X
    RY = "ry"         # Rotation-Y
    RZ = "rz"         # Rotation-Z
    U3 = "u3"         # Universal single-qubit gate
    
    # Two-qubit gates
    CX = "cx"         # CNOT
    CY = "cy"         # Controlled-Y
    CZ = "cz"         # Controlled-Z
    SWAP = "swap"     # SWAP
    
    # Three-qubit gates
    CCX = "ccx"       # Toffoli
    CSWAP = "cswap"   # Fredkin
    
    # Measurement
    MEASURE = "measure"
    
    # Special
    BARRIER = "barrier"
    RESET = "reset"

@dataclass
class IROperation:
    """Single IR operation"""
    op_type: IROpType
    qubits: List[int]
    params: List[float] = field(default_factory=list)
    classical_bits: Optional[List[int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_qasm(self) -> str:
        """Convert to QASM representation"""
        qubit_str = ", ".join(f"q[{q}]" for q in self.qubits)
        
        if self.op_type == IROpType.MEASURE:
            if self.classical_bits:
                cb_str = ", ".join(f"c[{cb}]" for cb in self.classical_bits)
                return f"measure {qubit_str} -> {cb_str};"
            return f"measure {qubit_str};"
        
        if self.params:
            param_str = ", ".join(f"{p:.6f}" for p in self.params)
            return f"{self.op_type.value}({param_str}) {qubit_str};"
        
        return f"{self.op_type.value} {qubit_str};"

@dataclass
class QuantumRegister:
    """Quantum register"""
    name: str
    size: int
    
@dataclass
class ClassicalRegister:
    """Classical register"""
    name: str
    size: int

@dataclass
class QuantumCircuitIR:
    """Intermediate representation of quantum circuit"""
    name: str
    quantum_registers: List[QuantumRegister]
    classical_registers: List[ClassicalRegister]
    operations: List[IROperation]
    
    # Metadata
    source_organism: str
    lineage_hash: str
    generation: int = 0
    parent_hash: Optional[str] = None
    
    # Metrics
    gate_count: int = 0
    depth: int = 0
    qubit_count: int = 0
    
    # Physics parameters
    lambda_coherence: float = 0.0
    gamma_decoherence: float = 0.0
    phi_integrated_info: float = 0.0
    w2_distance: float = 0.0
    
    def compute_metrics(self):
        """Compute circuit metrics"""
        self.gate_count = len([op for op in self.operations 
                              if op.op_type != IROpType.MEASURE])
        self.qubit_count = sum(reg.size for reg in self.quantum_registers)
        self.depth = self._compute_depth()
    
    def _compute_depth(self) -> int:
        """Compute circuit depth"""
        if not self.operations:
            return 0
        
        # Track when each qubit is last used
        qubit_times = {}
        max_time = 0
        
        for op in self.operations:
            # Get maximum time of all qubits involved
            current_time = max([qubit_times.get(q, 0) for q in op.qubits], default=0)
            
            # Update time for all involved qubits
            for q in op.qubits:
                qubit_times[q] = current_time + 1
            
            max_time = max(max_time, current_time + 1)
        
        return max_time
    
    def to_qasm(self, version: str = "2.0") -> str:
        """Convert IR to QASM"""
        qasm = f"// DNA-Lang Quantum Circuit: {self.name}\n"
        qasm += f"// Lineage: {self.lineage_hash}\n"
        qasm += f"// Generation: {self.generation}\n"
        qasm += f"OPENQASM {version};\n"
        qasm += 'include "qelib1.inc";\n\n'
        
        # Declare registers
        for qreg in self.quantum_registers:
            qasm += f"qreg {qreg.name}[{qreg.size}];\n"
        
        for creg in self.classical_registers:
            qasm += f"creg {creg.name}[{creg.size}];\n"
        
        qasm += "\n"
        
        # Add operations
        for op in self.operations:
            qasm += op.to_qasm() + "\n"
        
        return qasm
    
    def to_qiskit(self):
        """Convert IR to Qiskit QuantumCircuit"""
        try:
            from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
        except ImportError:
            raise ImportError("Qiskit required for quantum circuit execution")
        
        # Create registers
        qregs = [QuantumRegister(qr.size, qr.name) for qr in self.quantum_registers]
        cregs = [ClassicalRegister(cr.size, cr.name) for cr in self.classical_registers]
        
        qc = QuantumCircuit(*qregs, *cregs)
        
        # Add operations
        for op in self.operations:
            if op.op_type == IROpType.H:
                qc.h(op.qubits[0])
            elif op.op_type == IROpType.X:
                qc.x(op.qubits[0])
            elif op.op_type == IROpType.Y:
                qc.y(op.qubits[0])
            elif op.op_type == IROpType.Z:
                qc.z(op.qubits[0])
            elif op.op_type == IROpType.S:
                qc.s(op.qubits[0])
            elif op.op_type == IROpType.T:
                qc.t(op.qubits[0])
            elif op.op_type == IROpType.RX:
                qc.rx(op.params[0], op.qubits[0])
            elif op.op_type == IROpType.RY:
                qc.ry(op.params[0], op.qubits[0])
            elif op.op_type == IROpType.RZ:
                qc.rz(op.params[0], op.qubits[0])
            elif op.op_type == IROpType.U3:
                qc.u(op.params[0], op.params[1], op.params[2], op.qubits[0])
            elif op.op_type == IROpType.CX:
                qc.cx(op.qubits[0], op.qubits[1])
            elif op.op_type == IROpType.CY:
                qc.cy(op.qubits[0], op.qubits[1])
            elif op.op_type == IROpType.CZ:
                qc.cz(op.qubits[0], op.qubits[1])
            elif op.op_type == IROpType.SWAP:
                qc.swap(op.qubits[0], op.qubits[1])
            elif op.op_type == IROpType.CCX:
                qc.ccx(op.qubits[0], op.qubits[1], op.qubits[2])
            elif op.op_type == IROpType.CSWAP:
                qc.cswap(op.qubits[0], op.qubits[1], op.qubits[2])
            elif op.op_type == IROpType.MEASURE:
                if op.classical_bits:
                    for q, c in zip(op.qubits, op.classical_bits):
                        qc.measure(q, c)
                else:
                    qc.measure_all()
            elif op.op_type == IROpType.BARRIER:
                qc.barrier()
            elif op.op_type == IROpType.RESET:
                qc.reset(op.qubits[0])
        
        return qc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'name': self.name,
            'quantum_registers': [{'name': qr.name, 'size': qr.size} 
                                 for qr in self.quantum_registers],
            'classical_registers': [{'name': cr.name, 'size': cr.size} 
                                   for cr in self.classical_registers],
            'operations': [
                {
                    'op_type': op.op_type.value,
                    'qubits': op.qubits,
                    'params': op.params,
                    'classical_bits': op.classical_bits,
                    'metadata': op.metadata
                }
                for op in self.operations
            ],
            'metadata': {
                'source_organism': self.source_organism,
                'lineage_hash': self.lineage_hash,
                'generation': self.generation,
                'parent_hash': self.parent_hash,
                'metrics': {
                    'gate_count': self.gate_count,
                    'depth': self.depth,
                    'qubit_count': self.qubit_count
                },
                'physics': {
                    'lambda_coherence': self.lambda_coherence,
                    'gamma_decoherence': self.gamma_decoherence,
                    'phi_integrated_info': self.phi_integrated_info,
                    'w2_distance': self.w2_distance
                }
            }
        }

# ==========================================
# AST TO IR COMPILER
# ==========================================

class IRCompiler:
    """Compiles AST to IR"""
    
    def __init__(self):
        self.quantum_op_map = {
            'h': IROpType.H,
            'x': IROpType.X,
            'y': IROpType.Y,
            'z': IROpType.Z,
            's': IROpType.S,
            't': IROpType.T,
            'rx': IROpType.RX,
            'ry': IROpType.RY,
            'rz': IROpType.RZ,
            'u3': IROpType.U3,
            'cx': IROpType.CX,
            'cy': IROpType.CY,
            'cz': IROpType.CZ,
            'swap': IROpType.SWAP,
            'ccx': IROpType.CCX,
            'cswap': IROpType.CSWAP,
            'measure': IROpType.MEASURE,
            'bell': IROpType.CX,  # Bell state via H + CX
            'teleport': IROpType.CX  # Teleportation uses CX
        }
    
    def compile_organism(self, organism: OrganismNode) -> QuantumCircuitIR:
        """
        Compile organism AST to quantum circuit IR
        
        Args:
            organism: Parsed organism AST node
            
        Returns:
            Quantum circuit IR
        """
        # Determine qubit count
        qubit_count = self._determine_qubit_count(organism)
        
        # Create registers
        quantum_registers = [QuantumRegister("q", qubit_count)]
        classical_registers = [ClassicalRegister("c", qubit_count)]
        
        # Compile operations
        operations = []
        
        # Add genome encoding operations
        if organism.genome:
            operations.extend(self._compile_genome(organism.genome))
        
        # Add quantum state operations
        if organism.quantum_state:
            operations.extend(self._compile_quantum_state(organism.quantum_state))
        
        # Generate lineage hash
        lineage_hash = self._compute_lineage_hash(organism.name, operations)
        
        # Create circuit IR
        circuit = QuantumCircuitIR(
            name=organism.name,
            quantum_registers=quantum_registers,
            classical_registers=classical_registers,
            operations=operations,
            source_organism=organism.name,
            lineage_hash=lineage_hash,
            generation=0
        )
        
        # Compute metrics
        circuit.compute_metrics()
        
        return circuit
    
    def _determine_qubit_count(self, organism: OrganismNode) -> int:
        """Determine required number of qubits"""
        max_qubit = 0
        
        # Check genome
        if organism.genome:
            for gene in organism.genome.genes:
                if gene.target_qubits:
                    max_qubit = max(max_qubit, max(gene.target_qubits))
        
        # Check quantum state operations
        if organism.quantum_state:
            for op in organism.quantum_state.operations:
                if op.qubits:
                    max_qubit = max(max_qubit, max(op.qubits))
        
        return max_qubit + 1
    
    def _compile_genome(self, genome: GenomeNode) -> List[IROperation]:
        """Compile genome block to IR operations"""
        operations = []
        
        for gene in genome.genes:
            # Encode data into qubits
            # For now, simple encoding: if data contains '1', apply X gate
            if '1' in gene.encoding:
                for qubit in gene.target_qubits:
                    operations.append(IROperation(
                        op_type=IROpType.X,
                        qubits=[qubit],
                        metadata={'gene': gene.name, 'encoding': gene.encoding}
                    ))
        
        return operations
    
    def _compile_quantum_state(self, quantum_state: QuantumStateNode) -> List[IROperation]:
        """Compile quantum_state block to IR operations"""
        operations = []
        
        for op in quantum_state.operations:
            ir_op_type = self.quantum_op_map.get(op.operation, IROpType.H)
            
            # Special handling for Bell state
            if op.operation == 'bell':
                # Bell state: H on first qubit, CX between qubits
                if len(op.qubits) >= 2:
                    operations.append(IROperation(
                        op_type=IROpType.H,
                        qubits=[op.qubits[0]]
                    ))
                    operations.append(IROperation(
                        op_type=IROpType.CX,
                        qubits=[op.qubits[0], op.qubits[1]]
                    ))
            else:
                # Standard operation
                ir_operation = IROperation(
                    op_type=ir_op_type,
                    qubits=op.qubits,
                    params=op.params
                )
                
                # Add classical bits for measurement
                if ir_op_type == IROpType.MEASURE:
                    ir_operation.classical_bits = op.qubits
                
                operations.append(ir_operation)
        
        return operations
    
    def _compute_lineage_hash(self, organism_name: str, operations: List[IROperation]) -> str:
        """Compute SHA-256 lineage hash"""
        # Create deterministic representation
        data = f"{organism_name}:"
        for op in operations:
            data += f"{op.op_type.value}-{op.qubits}-{op.params};"
        
        # Compute hash
        return hashlib.sha256(data.encode()).hexdigest()[:16]

# ==========================================
# OPTIMIZATION PASSES
# ==========================================

class IROptimizer:
    """IR optimization passes"""
    
    @staticmethod
    def remove_redundant_gates(circuit: QuantumCircuitIR) -> QuantumCircuitIR:
        """Remove self-inverse gate pairs (H-H, X-X, etc.)"""
        optimized_ops = []
        skip_next = False
        
        for i, op in enumerate(circuit.operations):
            if skip_next:
                skip_next = False
                continue
            
            # Check if next operation is inverse
            if i + 1 < len(circuit.operations):
                next_op = circuit.operations[i + 1]
                
                # Self-inverse gates
                if (op.op_type == next_op.op_type and 
                    op.qubits == next_op.qubits and
                    op.op_type in [IROpType.H, IROpType.X, IROpType.Y, IROpType.Z]):
                    skip_next = True
                    continue
            
            optimized_ops.append(op)
        
        circuit.operations = optimized_ops
        circuit.compute_metrics()
        return circuit
    
    @staticmethod
    def merge_rotations(circuit: QuantumCircuitIR) -> QuantumCircuitIR:
        """Merge consecutive rotation gates on same qubit"""
        optimized_ops = []
        i = 0
        
        while i < len(circuit.operations):
            op = circuit.operations[i]
            
            # Check if rotation gate
            if op.op_type in [IROpType.RX, IROpType.RY, IROpType.RZ]:
                # Look ahead for same rotation on same qubit
                merged_angle = op.params[0] if op.params else 0.0
                j = i + 1
                
                while j < len(circuit.operations):
                    next_op = circuit.operations[j]
                    if (next_op.op_type == op.op_type and 
                        next_op.qubits == op.qubits):
                        merged_angle += next_op.params[0] if next_op.params else 0.0
                        j += 1
                    else:
                        break
                
                # Create merged operation
                merged_op = IROperation(
                    op_type=op.op_type,
                    qubits=op.qubits,
                    params=[merged_angle % (2 * np.pi)]
                )
                optimized_ops.append(merged_op)
                i = j
            else:
                optimized_ops.append(op)
                i += 1
        
        circuit.operations = optimized_ops
        circuit.compute_metrics()
        return circuit
    
    @staticmethod
    def optimize(circuit: QuantumCircuitIR, level: int = 2) -> QuantumCircuitIR:
        """
        Apply optimization passes
        
        Args:
            circuit: Circuit to optimize
            level: Optimization level (0-3)
        
        Returns:
            Optimized circuit
        """
        if level >= 1:
            circuit = IROptimizer.remove_redundant_gates(circuit)
        
        if level >= 2:
            circuit = IROptimizer.merge_rotations(circuit)
        
        return circuit

# ==========================================
# MAIN INTERFACE
# ==========================================

def compile_to_ir(organism: OrganismNode, optimize: bool = True) -> QuantumCircuitIR:
    """
    Compile organism AST to quantum circuit IR
    
    Args:
        organism: Parsed organism AST
        optimize: Whether to apply optimization passes
        
    Returns:
        Quantum circuit IR
    """
    compiler = IRCompiler()
    circuit = compiler.compile_organism(organism)
    
    if optimize:
        circuit = IROptimizer.optimize(circuit, level=2)
    
    return circuit

if __name__ == "__main__":
    from dna_parser import parse_dna_lang
    
    # Test compilation
    test_source = """
organism bell_state {
    genome {
        gene init = encode(00) -> q[0];
    }
    
    quantum_state {
        helix(q[0]);
        bond(q[0], q[1]);
        measure(q[0]);
        measure(q[1]);
    }
    
    fitness = phi;
}
"""
    
    print("=== IR Compiler Test ===")
    organisms = parse_dna_lang(test_source)
    
    for organism in organisms:
        print(f"\nCompiling organism: {organism.name}")
        circuit = compile_to_ir(organism)
        
        print(f"Lineage Hash: {circuit.lineage_hash}")
        print(f"Gate Count: {circuit.gate_count}")
        print(f"Circuit Depth: {circuit.depth}")
        print(f"Qubit Count: {circuit.qubit_count}")
        
        print("\nQASM:")
        print(circuit.to_qasm())
