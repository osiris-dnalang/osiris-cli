import sys
from pathlib import Path
import numpy as np

# Add experiments/hp001 to path
sys.path.insert(0, "/mnt/c/Users/Ron/osiris-cli/experiments/hp001")

from execute_hp001_qpu import build_hp001_circuit
from qiskit_aer import AerSimulator

sim = AerSimulator()

def evaluate_circuit_arm(arm_name):
    print(f"\n--- Evaluating Arm: {arm_name} ---")
    results = {}
    for basis in ["XX", "YY", "ZZ"]:
        qc = build_hp001_circuit(arm_name, basis)
        job = sim.run(qc, shots=8192, seed_simulator=42)
        counts = job.result().get_counts()
        total = sum(counts.values())
        
        # In Qiskit, measurement ordering: classical bit 0 is R, classical bit 1 is Decoded
        # Bitstring format: 'b1 b0' (index 0 is b1, index 1 is b0)
        exp_val = 0.0
        for bitstring, count in counts.items():
            cb = bitstring.replace(" ", "")
            # Parity: bit0 == bit1 -> +1, else -1
            parity = 1.0 if cb[0] == cb[1] else -1.0
            exp_val += parity * count
        exp_val /= total
        results[basis] = exp_val
        print(f"  Basis {basis}: expectation = {exp_val:+.4f} (counts: {counts})")
    
    # Bell state fidelity: F = (1 + <XX> - <YY> + <ZZ>) / 4
    # Note: Depending on phase conventions in circuit, <YY> for |Phi+> is -1, so -<YY> is +1.
    f_bell = (1.0 + results["XX"] - results["YY"] + results["ZZ"]) / 4.0
    print(f"  --> Operational Reconstructed Bell Fidelity: {f_bell:.4f} (Entangled: {f_bell > 0.50})")
    return results, f_bell

evaluate_circuit_arm("A_full")
evaluate_circuit_arm("B_entangled")
evaluate_circuit_arm("B_control")
