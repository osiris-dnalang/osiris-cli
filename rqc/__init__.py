"""Recursive (adaptive) vs random quantum circuits, measured honestly.

Stage S0 of ~/experiments/rqc-pipeline/SCOPE.md: circuit families with a fixed layer structure, exact ideal
probabilities, the plain and circuit-normalized linear XEB estimators, and an experiment loop that writes a
ledger row before every sampler call. No hardware access lives here: a sampler is passed in.
"""
from .circuits import Circuit, random_circuit, perturbed
from .sim import probabilities
from .xeb import collision_probability, linear_xeb, normalized_xeb
from .experiment import Ledger, run_adaptive, run_random

__all__ = ["Circuit", "random_circuit", "perturbed", "probabilities", "collision_probability", "linear_xeb",
           "normalized_xeb", "Ledger", "run_adaptive", "run_random"]
