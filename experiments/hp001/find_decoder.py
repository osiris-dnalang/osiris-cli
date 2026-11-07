import numpy as np
from hp001_simulator import HaydenPreskillSimulator, BELL_STATE, BELL_DM, tensor, I2

def find_optimal_unitary_decoder(seed=42):
    sim = HaydenPreskillSimulator(seed=seed)
    # Prepare initial state: (R, M, B1, B2, E1, E2)
    psi_0 = sim.prepare_initial_state(early_entanglement=True)
    # Scramble: U acts on (M, B1, B2) -> outputs (C1, C2, D)
    psi_1 = sim.apply_scrambler(psi_0)
    
    # State psi_1 is in registers: R (0), C1 (1), C2 (2), D (3), E1 (4), E2 (5)
    # Reshape to (dim_R=2, dim_C=4, dim_rad=8)
    t = psi_1.reshape((2, 4, 8)) # index 0 is R, index 1 is C (remnant), index 2 is rad (D, E1, E2)
    
    # Trace out C: rho_{R, rad} has shape (2, 8, 2, 8)
    rho_r_rad = np.einsum('rca, scb -> rasb', t, t.conj()).reshape((16, 16))
    
    # We want a unitary V on rad (8x8) such that after V, rad_0 is M_dec, and (R, M_dec) has max Bell fidelity
    # For a pure state representation, let's find the Kraus operators from M to rad
    # The effective channel from M (dim 2) to rad (dim 8) is:
    # A_c = sqrt(2) * t[:, c, :].T  (shape 8x2)
    # We want to find an 8x8 unitary V = [V_0; V_rest] where V_0 is 2x8 such that V_0 A_c approx delta_{c,0} ...
    
    # Let's test using Polar decomposition / Procrustes on the dominant Kraus operator
    # The Choi state between R and rad is rho_{R, rad}
    # We want max Tr(BELL_DM @ (I_R tensor |0><0|... @ (I tensor V) rho (I tensor V^dagger) ...))
    
    # In quantum information theory, the Petz map gives a CPTP channel.
    # An isometric dilation of the Petz map or the polar decomposition of the Choi matrix gives the optimal unitary!
    # Let's see: the 16x16 matrix rho_{R, rad}:
    # Let's reshape rho_{R, rad} as a map from R to rad:
    # Let's compute the fidelity for random scrambler:
    f_petz, rho_petz, _ = sim.simulate_arm_b_restricted(early_entanglement=True)
    print(f"Seed {seed} | Petz Recovery Fidelity: {f_petz:.4f}")
    
    # Let's find an explicit 3-qubit Clifford or circuit scrambler where the decoder is an EXACT circuit!
    return f_petz

find_optimal_unitary_decoder(42)
