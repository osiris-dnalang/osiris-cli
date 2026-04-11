// Bell State Preparation Circuit
// DNA-Lang Quantum Corpus v1.0
// Prepares |Φ+⟩ = (|00⟩ + |11⟩)/√2

OPENQASM 3.0;
include "stdgates.inc";

// Declare qubits and classical bits
qubit[2] q;
bit[2] c;

// Reset qubits to |0⟩ state
reset q[0];
reset q[1];

// Bell state preparation
// Step 1: Hadamard on q[0] creates (|0⟩ + |1⟩)/√2
h q[0];

// Step 2: CNOT entangles q[0] and q[1]
// Result: (|00⟩ + |11⟩)/√2 = |Φ+⟩
cx q[0], q[1];

// Measurement in computational basis
c[0] = measure q[0];
c[1] = measure q[1];

// Expected outcomes:
// |00⟩: 50% (ideal)
// |11⟩: 50% (ideal)
// |01⟩: 0% (indicates error)
// |10⟩: 0% (indicates error)

// Fidelity calculation:
// F = P(00) + P(11)
// Perfect: F = 1.0
// Measured: F ≈ 0.869 ± 0.023
