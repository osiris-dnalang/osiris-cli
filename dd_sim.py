#!/usr/bin/env python3
"""
dd_sim.py -- a small, deterministic simulator of one qubit under a
dynamical-decoupling pulse sequence: dephasing noise plus imperfect pulses,
as 3x3 rotations of the Bloch vector.

Over a unit time window the qubit precesses about Z by the accumulated
detuning, theta = integral of delta(t) dt between pulses. delta(t) is an
Ornstein-Uhlenbeck process with strength SIGMA and correlation time
NOISE[name] (quasistatic: constant within a shot). Pulse k of n sits at time
(k + 0.5) / n; "I" is an idle slot, "X" and "Y" are pi rotations about the X
and Y axes that over-rotate by FLIP_ERROR (a systematic error, the same on
every pulse). X and Y are therefore different operations: all-X (CPMG)
accumulates the flip error on one axis, XY4 largely cancels it.

The score is the average state fidelity of the whole shot's rotation R over
the Bloch sphere (equivalently over the six states +-x, +-y, +-z):

    F = (1 + trace(R) / 3) / 2,   averaged over `shots` noise draws.

F = 1 is the identity; an idle qubit dephases to 2/3 (z states are kept); a
sequence whose ideal net effect is not the identity (an odd number of pi
pulses, for example) scores low. Pure Python and seeded, so the same inputs
give the same number on any machine.

What it is NOT: a hardware model, a multi-qubit or crosstalk model,
amplitude damping, finite-width pulses, or a claim about any device.
"""
import math
import random

NOISE = {"quasistatic": math.inf, "ou_slow": 0.5, "ou_fast": 0.05}  # correlation times (unit window = 1)
SIGMA = 4.0            # detuning strength: idle x/y coherence exp(-SIGMA^2/2) ~ 0 over the window
STEPS = 128            # time steps per unit window
FLIP_ERROR = 0.05      # each pi pulse rotates by pi * (1 + FLIP_ERROR)
ALPHABET = ("I", "X", "Y")
MAX_LEN = 32


def _mul(a, b):
    return [[a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j] for j in range(3)] for i in range(3)]


def _rz(t):
    c, s = math.cos(t), math.sin(t)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _pulse(axis, flip_error):
    t = math.pi * (1.0 + flip_error)
    c, s = math.cos(t), math.sin(t)
    if axis == "X":
        return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def fidelity(sequence, noise, seed, shots=200, flip_error=FLIP_ERROR):
    """Mean average-state fidelity of the sequence over `shots` noise draws."""
    n = len(sequence)
    at = {}  # time step -> pulse axis applied at the end of that step
    for k, p in enumerate(sequence):
        if p != "I":
            at[min(STEPS - 1, int((k + 0.5) / n * STEPS))] = p
    pulses = {p: _pulse(p, flip_error) for p in ("X", "Y")}
    tau = NOISE[noise]
    dt = 1.0 / STEPS
    a = 1.0 if tau == math.inf else math.exp(-dt / tau)
    b = SIGMA * math.sqrt(max(0.0, 1.0 - a * a))
    rng = random.Random(f"dd:{noise}:{seed}")
    total = 0.0
    for _ in range(shots):
        d = rng.gauss(0.0, SIGMA)
        r = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        theta = 0.0
        for k in range(STEPS):
            theta += d * dt
            if b:
                d = a * d + b * rng.gauss(0.0, 1.0)
            if k in at:
                r = _mul(pulses[at[k]], _mul(_rz(theta), r))
                theta = 0.0
        r = _mul(_rz(theta), r)
        total += (1.0 + (r[0][0] + r[1][1] + r[2][2]) / 3.0) / 2.0
    return total / shots
