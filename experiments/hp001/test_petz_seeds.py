import numpy as np

# Let's inspect the scrambler in hp001_simulator.py
from hp001_simulator import HaydenPreskillSimulator, BELL_DM
from hp001_evaluator import evaluate_tomography

# Test across 10 random seeds in hp001_simulator
print("Testing hp001_simulator Petz recovery:")
for seed in [42, 123, 2024, 777]:
    sim = HaydenPreskillSimulator(seed=seed)
    f_a, _ = sim.simulate_arm_a_full_access()
    f_b, rho_b, tel = sim.simulate_arm_b_restricted(early_entanglement=True)
    f_ctrl, _, _ = sim.simulate_arm_b_restricted(early_entanglement=False)
    print(f"Seed {seed:5d} | Arm A: {f_a:.4f} | Arm B (Entangled): {f_b:.4f} | Arm B (No Entang): {f_ctrl:.4f} | Delta: {f_b - f_ctrl:+.4f}")
