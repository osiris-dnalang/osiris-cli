from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService
import numpy as np

# Load the exact 3-arm circuits
from verify_three_arms_operational import run_three_arms, c_dec

# Let's build the explicit Qiskit circuit for Arm A, Arm B, Arm C
def build_operational_circuit(arm="B_entangled", basis="ZZ"):
    qc = QuantumCircuit(6, 2, name=f"HP001_P2_{arm}_{basis}")
    # 0: R, 1: M, 2: B1, 3: B2, 4: E1, 5: E2
    
    # 1. State preparation
    qc.h(0); qc.cx(0, 1) # |Phi+>_RM
    if arm != "B_control":
        qc.h(2); qc.cx(2, 4) # |Phi+>_{B1 E1}
        qc.h(3); qc.cx(3, 5) # |Phi+>_{B2 E2}
        
    # 2. Scrambler on (1, 2, 3)
    qc.cx(1, 2)
    qc.h(1)
    qc.cx(2, 3)
    qc.h(2)
    qc.cx(1, 3)
    qc.h(3)
    
    # 3. Decoder
    if arm == "A_full":
        # Full inverse on (1, 2, 3)
        qc.h(3)
        qc.cx(1, 3)
        qc.h(2)
        qc.cx(2, 3)
        qc.h(1)
        qc.cx(1, 2)
        dec_qubit = 1
    else:
        # Restricted decoder on (1, 4, 5)
        qc.append(c_dec.to_circuit(), [1, 4, 5])
        dec_qubit = 1 # Output decoded qubit is 1
        
    # 4. Tomography basis rotation on (0, dec_qubit)
    if basis == "XX":
        qc.h(0); qc.h(dec_qubit)
    elif basis == "YY":
        qc.sdg(0); qc.h(0); qc.sdg(dec_qubit); qc.h(dec_qubit)
    elif basis == "ZZ":
        pass
        
    # Measure R (0) and Decoded (dec_qubit) into classical bits 0 and 1
    qc.measure(0, 0)
    qc.measure(dec_qubit, 1)
    return qc

# Let's test transpilation to ibm_fez
s = QiskitRuntimeService()
backend = s.backend("ibm_fez")

for arm in ["A_full", "B_entangled", "B_control"]:
    qc = build_operational_circuit(arm, "ZZ")
    # Transpile to ibm_fez
    t_qc = transpile(qc, backend=backend, optimization_level=3)
    ops = t_qc.count_ops()
    print(f"Arm {arm:<12} | Depth: {t_qc.depth():3d} | Total 2Q Gates (cz): {ops.get('cz', ops.get('cx', 0)):2d} | 1Q Gates: {sum(v for k,v in ops.items() if k not in ['cz', 'cx', 'measure', 'barrier'])}")
