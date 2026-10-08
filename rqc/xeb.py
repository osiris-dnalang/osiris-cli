"""Linear cross-entropy benchmark estimators.

For samples x_1..x_N from the device and ideal probabilities p of the circuit on n qubits:
  plain linear XEB       F_lin  = 2^n · mean_i p(x_i) − 1
  circuit-normalized XEB F_norm = (2^n · mean_i p(x_i) − 1) / (2^n · Σ_x p(x)² − 1)
Under the depolarizing model q = (1 − ε)·p + ε·u, E[F_norm] = 1 − ε for any circuit, while
E[F_lin] = (1 − ε)·(2^n·Σp² − 1): it equals 1 − ε only when Σp² = 2/2^n (Porter–Thomas). A loop that rewards
F_lin can therefore raise it by choosing circuits with concentrated outputs, without any change in fidelity.
Report collision_probability next to any XEB so that drift is visible.
"""
import numpy as np


def collision_probability(p):
    return float(np.sum(np.asarray(p) ** 2))


def _mean_p(p, samples):
    return float(np.mean(np.asarray(p)[np.asarray(samples)]))


def linear_xeb(p, samples):
    return len(p) * _mean_p(p, samples) - 1.0


def normalized_xeb(p, samples):
    denom = len(p) * collision_probability(p) - 1.0
    if denom <= 1e-12:
        raise ValueError("ideal distribution is uniform: XEB is undefined for this circuit")
    return (len(p) * _mean_p(p, samples) - 1.0) / denom
