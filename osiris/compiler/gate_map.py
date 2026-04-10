"""Canonical gate equivalence table for cross-backend translation."""

from .dna_ir import IROpType

# Gates that take no parameters and act on 1 qubit
SINGLE_QUBIT_GATES = {IROpType.H, IROpType.X, IROpType.Y, IROpType.Z,
                      IROpType.S, IROpType.T}

# Gates that take float parameters and act on 1 qubit
PARAMETERISED_SINGLE_QUBIT_GATES = {IROpType.RX, IROpType.RY, IROpType.RZ}

# U3(theta, phi, lam) — 3 parameters, 1 qubit
U3_GATE = IROpType.U3

# Two-qubit gates (no params)
TWO_QUBIT_GATES = {IROpType.CX, IROpType.CY, IROpType.CZ, IROpType.SWAP}

# Three-qubit gates (no params)
THREE_QUBIT_GATES = {IROpType.CCX, IROpType.CSWAP}

# Special / non-unitary
SPECIAL_OPS = {IROpType.MEASURE, IROpType.BARRIER, IROpType.RESET}

# Number of qubits per gate
QUBIT_COUNT = {
    IROpType.H: 1, IROpType.X: 1, IROpType.Y: 1, IROpType.Z: 1,
    IROpType.S: 1, IROpType.T: 1,
    IROpType.RX: 1, IROpType.RY: 1, IROpType.RZ: 1, IROpType.U3: 1,
    IROpType.CX: 2, IROpType.CY: 2, IROpType.CZ: 2, IROpType.SWAP: 2,
    IROpType.CCX: 3, IROpType.CSWAP: 3,
    IROpType.MEASURE: 1, IROpType.BARRIER: 0, IROpType.RESET: 1,
}

# Canonical name mapping (IROpType value → backend-specific name)
# Each backend adapter overrides where necessary.
QISKIT_GATE_NAMES = {
    IROpType.H: "h", IROpType.X: "x", IROpType.Y: "y", IROpType.Z: "z",
    IROpType.S: "s", IROpType.T: "t",
    IROpType.RX: "rx", IROpType.RY: "ry", IROpType.RZ: "rz",
    IROpType.U3: "u3",
    IROpType.CX: "cx", IROpType.CY: "cy", IROpType.CZ: "cz",
    IROpType.SWAP: "swap", IROpType.CCX: "ccx", IROpType.CSWAP: "cswap",
}

CIRQ_GATE_NAMES = {
    IROpType.H: "H", IROpType.X: "X", IROpType.Y: "Y", IROpType.Z: "Z",
    IROpType.S: "S", IROpType.T: "T",
    IROpType.RX: "rx", IROpType.RY: "ry", IROpType.RZ: "rz",
    IROpType.CX: "CNOT", IROpType.CY: "ControlledGate(Y)",
    IROpType.CZ: "CZ", IROpType.SWAP: "SWAP",
    IROpType.CCX: "CCX", IROpType.CSWAP: "CSWAP",
}

PYQUIL_GATE_NAMES = {
    IROpType.H: "H", IROpType.X: "X", IROpType.Y: "Y", IROpType.Z: "Z",
    IROpType.S: "S", IROpType.T: "T",
    IROpType.RX: "RX", IROpType.RY: "RY", IROpType.RZ: "RZ",
    IROpType.CX: "CNOT", IROpType.CZ: "CZ", IROpType.SWAP: "SWAP",
    IROpType.CCX: "CCNOT", IROpType.CSWAP: "CSWAP",
}
