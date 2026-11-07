#!/usr/bin/env python3
"""
osiris_tetrahedral_field.py — N-Dimensional Tetrahedral Field Simulator
Physical Substrate Engine for OSIRIS 11D-CRSM & Quantum-Inspired Evolution
"""

import math
from typing import Dict, List, Optional, Any, Union

# Physical substrate invariants
LAMBDA_PHI = 2.176435e-8   # Planck mass / normalizer (kg)
THETA_LOCK = 51.843        # Degree lock angle
GAMMA_FLOOR = 0.0920       # Coherence floor threshold


class TetrahedralField:
    """
    N-Dimensional Tetrahedral Lattice & Torsion Field Simulator.
    Supports arbitrary dimensions (4D, 7D, 11D-CRSM), physical substrate
    mapping, Planck mass normalization, and non-causal phase evolution.
    """

    def __init__(
        self,
        ndim: int = 4,
        substrate: str = "11D-CRSM",
        planck_norm: Union[bool, float] = True,
        causality: str = "non-causal",
        beta: float = 0.5,
    ):
        self.ndim = max(4, int(ndim))
        self.substrate = str(substrate)
        self.causality = str(causality)
        self.beta = float(beta)

        # Planck normalization scale factor
        if isinstance(planck_norm, (int, float)):
            self.planck_norm = float(planck_norm)
        elif planck_norm:
            self.planck_norm = LAMBDA_PHI
        else:
            self.planck_norm = 1.0

        # State vector: [q, a, c, j, ...]
        # For ndim > 4, remaining dimensions represent higher CRSM manifolds
        self.state: List[float] = [0.0] * self.ndim
        self.history: List[List[float]] = []

    def step(self, beta: Optional[float] = None) -> List[float]:
        """
        Advance the tetrahedral field by one discrete physical epoch.
        Updates core tetrahedral coordinates [q, a, c, j] and coupled N-D modes.
        """
        if beta is not None:
            self.beta = float(beta)

        # Core tetrahedral modes: query, answer, constraint, judge
        q = self.state[0]
        a = self.state[1]
        c = self.state[2]
        j = self.state[3]

        # Mentor ensemble perturbation (adversarial torsion)
        mentors = [a + 0.1, a - 0.1, a]
        a_new = sum(mentors) / len(mentors)
        c_new = abs(q - a_new)  # Constraint distance
        j_new = 1.0 if c_new < 0.05 else 0.0  # Judge boundary evaluation

        # Non-causal coupling with higher dimensions if ndim > 4
        high_d_sum = 0.0
        if self.ndim > 4:
            for k in range(4, self.ndim):
                # Coupling phase modulated by theta_lock
                phi_k = math.radians(THETA_LOCK * (k - 3))
                high_d_sum += self.state[k] * math.cos(phi_k)

        # Update primary query coordinate
        torsion = 0.05 * math.sin(math.radians(THETA_LOCK)) * (high_d_sum if self.ndim > 4 else 0.0)
        q_new = q + self.beta * (a_new - q) - 0.1 * c_new + torsion

        new_state = [q_new, a_new, c_new, j_new]

        # Evolve higher dimensions with damped phase rotation
        for k in range(4, self.ndim):
            decay = 0.95
            phase = math.radians(THETA_LOCK * (k - 3))
            coupling = 0.02 * (q_new - self.state[k])
            val_new = self.state[k] * decay * math.cos(phase) + coupling
            new_state.append(val_new)

        self.state = new_state
        self.history.append(list(self.state))
        return self.state

    def summary(self) -> Dict[str, Any]:
        """
        Generate operational summary compatible with experimentalist and tournament labs.
        """
        mean_val = sum(self.state) / len(self.state) if self.state else 0.0
        energy_val = sum(x * x for x in self.state) if self.state else 0.0

        res: Dict[str, Any] = {
            "q": round(self.state[0], 6),
            "a": round(self.state[1], 6),
            "c": round(self.state[2], 6),
            "j": round(self.state[3], 6),
            "mean": round(mean_val, 6),
            "energy": round(energy_val, 6),
            "ndim": self.ndim,
            "substrate": self.substrate,
            "planck_norm": self.planck_norm,
            "causality": self.causality,
        }

        # Include higher dimensions if present
        if self.ndim > 4:
            for k in range(4, self.ndim):
                res[f"d{k}"] = round(self.state[k], 6)

        return res


def main():
    print("=== OSIRIS N-Dimensional Tetrahedral Field Simulator ===")
    
    # 4D Baseline Demonstration
    print("\n--- 4D Baseline Field ---")
    tf4 = TetrahedralField(ndim=4, beta=0.5)
    for epoch in range(5):
        tf4.step()
        s = tf4.summary()
        print(f"Epoch {epoch:02d} | q: {s['q']:.4f}, a: {s['a']:.4f}, c: {s['c']:.4f}, j: {s['j']:.1f} | mean: {s['mean']:.4f}, energy: {s['energy']:.4f}")

    # 11D CRSM Substrate Demonstration
    print("\n--- 11D-CRSM Substrate Field ---")
    tf11 = TetrahedralField(ndim=11, substrate="11D-CRSM", planck_norm=True, causality="non-causal")
    print(f"[Physics] Substrate: {tf11.substrate}, N-dim: {tf11.ndim}, Planck norm: {tf11.planck_norm:.4e}, Causality: {tf11.causality}")
    for epoch in range(5):
        tf11.step(beta=0.6)
        s = tf11.summary()
        print(f"Epoch {epoch:02d} | q: {s['q']:.4f}, a: {s['a']:.4f}, c: {s['c']:.4f}, j: {s['j']:.1f} | mean: {s['mean']:.4f}, energy: {s['energy']:.4f}")


if __name__ == "__main__":
    main()
