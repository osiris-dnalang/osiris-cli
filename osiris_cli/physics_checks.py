"""Deterministic physics checks: bounds a claim must respect, computed by code, not a model.

Each check takes plain SI numbers and returns a ``Check``: the quantities it computed, a
verdict, and one sentence saying why. They test claims against conservation laws and
textbook bounds; they cannot confirm a claim, only rule one out or show it is not ruled out.

Verdicts: ``RULED_OUT`` (violates the bound), ``CONSISTENT`` (does not violate it; that is
not evidence for it), ``FEASIBLE`` / ``MARGINAL`` / ``NOT_FEASIBLE`` (experiment design).

Constants: CODATA 2018 (c, h-bar, k_B exact; G recommended), standard gravity g0.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

C = 299_792_458.0                # m/s
G = 6.67430e-11                  # m^3 kg^-1 s^-2
HBAR = 1.054571817e-34           # J s
K_B = 1.380649e-23               # J/K
G0 = 9.80665                     # m/s^2
TSIRELSON = 2.0 * math.sqrt(2.0)


@dataclass
class Check:
    name: str
    verdict: str
    why: str
    quantities: Dict[str, str] = field(default_factory=dict)

    def lines(self) -> List[str]:
        out = [f"{self.name}: {self.verdict}"]
        out += [f"  {k} = {v}" for k, v in self.quantities.items()]
        out.append(f"  {self.why}")
        return out


def _sci(x: float, unit: str = "") -> str:
    return (f"{x:.4g}" if 1e-3 <= abs(x) < 1e5 or x == 0 else f"{x:.3e}") + (f" {unit}" if unit else "")


def radiation_thrust(power_w: float, mass_kg: Optional[float] = None) -> Check:
    """Most thrust radiated power can give: F = P/c (all of it emitted in one direction).
    A net Poynting flux through a closed surface is power leaving, not a force."""
    f_max = power_w / C
    q = {"power": _sci(power_w, "W"), "max thrust P/c": _sci(f_max, "N")}
    if mass_kg is None:
        return Check("radiation thrust", "CONSISTENT", "No mass given; this is the ceiling on thrust "
                     "from radiating that power, reached only if all of it leaves in one direction.", q)
    need = mass_kg * G0
    q["thrust to hover"] = _sci(need, "N") + f" (m g0, m = {_sci(mass_kg, 'kg')})"
    q["shortfall factor"] = _sci(need / f_max)
    if f_max >= need:
        return Check("radiation thrust", "CONSISTENT", "The radiated power could in principle carry this "
                     "weight; that says nothing about whether the device radiates it.", q)
    return Check("radiation thrust", "RULED_OUT", f"Even perfectly collimated, {_sci(power_w, 'W')} of "
                 f"radiation pushes with at most {_sci(f_max, 'N')}; lifting the mass needs "
                 f"{_sci(need / f_max)} times more.", q)


def rim_speed(omega_rad_s: float, radius_m: float) -> Check:
    v = omega_rad_s * radius_m
    q = {"omega": _sci(omega_rad_s, "rad/s"), "radius": _sci(radius_m, "m"),
         "rim speed": _sci(v, "m/s"), "v / c": _sci(v / C)}
    if v >= C:
        return Check("rim speed", "RULED_OUT", "A material body cannot rotate this fast: its rim would "
                     "move faster than light. (A rotating field pattern can; matter cannot.)", q)
    return Check("rim speed", "CONSISTENT", "Below light speed; material strength is a separate limit.", q)


def static_metric_mass(h: float, r_m: float, power_w: Optional[float] = None,
                       duration_s: Optional[float] = None) -> Check:
    """Weak field: |h_tt| = 2GM/(r c^2). The mass-energy a static perturbation of that size implies,
    and (given a power and a duration) whether everything supplied in that time could account for it."""
    m = abs(h) * r_m * C ** 2 / (2 * G)
    e = m * C ** 2
    q = {"|h_tt|": _sci(abs(h)), "at distance": _sci(r_m, "m"), "implied mass": _sci(m, "kg"),
         "implied energy M c^2": _sci(e, "J")}
    note = ("Interferometers such as LIGO measure oscillating strain between about 10 Hz and a few kHz, "
            "not a static h_tt.")
    if power_w is None or duration_s is None:
        return Check("static metric perturbation", "IMPLIED", "The source of this perturbation must hold "
                     f"{_sci(e, 'J')} of mass-energy. Give power= and duration= to compare. " + note, q)
    supplied = power_w * duration_s
    q["energy supplied P t"] = _sci(supplied, "J") + f" ({_sci(power_w, 'W')} for {_sci(duration_s, 's')})"
    q["shortfall factor"] = _sci(e / supplied)
    if supplied < e:
        return Check("static metric perturbation", "RULED_OUT", "Even if every joule supplied in that time "
                     f"were stored at once, it is {_sci(e / supplied)} times too little. " + note, q)
    return Check("static metric perturbation", "CONSISTENT", "Enough energy is supplied in principle. " + note, q)


def planck_mass() -> Check:
    m = math.sqrt(HBAR * C / G)
    return Check("Planck mass", "CONSISTENT", "sqrt(h-bar c / G), in kilograms.",
                 {"m_P": f"{m:.6e} kg"})


def same_number(value: float, reference: float, label: str) -> Check:
    rel = abs(value - reference) / abs(reference)
    return Check(f"compare with {label}", "MATCH" if rel < 1e-5 else "DIFFERENT",
                 f"Relative difference {rel:.1e}." + (" The same number, whatever units it is "
                                                      "given." if rel < 1e-5 else ""),
                 {"value": f"{value:.6e}", label: f"{reference:.6e}"})


def chsh(s: float) -> Check:
    q = {"|S|": _sci(abs(s)), "local bound": "2", "quantum bound 2 sqrt 2": f"{TSIRELSON:.4f}"}
    if abs(s) > TSIRELSON + 1e-9:
        return Check("CHSH", "RULED_OUT", "Above Tsirelson's bound: no quantum system gives this; "
                     "the analysis or the correlators are wrong.", q)
    if abs(s) > 2.0:
        return Check("CHSH", "CONSISTENT", "Violates the local bound, within the quantum one.", q)
    return Check("CHSH", "CONSISTENT", "No Bell violation: |S| <= 2 is reproducible by local models.", q)


def efficiency(eta: float) -> Check:
    q = {"efficiency": f"{eta:.4g} ({eta * 100:.4g} %)"}
    if eta > 1.0:
        return Check("energy efficiency", "RULED_OUT", "More energy out than in violates conservation "
                     "of energy; vacuum fluctuations are not an extractable energy source.", q)
    return Check("energy efficiency", "CONSISTENT", "At or below 100 %.", q)


def entropy_ceiling(shots: float, reported_bits: Optional[float] = None) -> Check:
    """With N shots, the plug-in (empirical) entropy can never exceed log2(N)."""
    cap = math.log2(shots)
    q = {"shots": _sci(shots), "log2(shots)": f"{cap:.4f} bits"}
    if reported_bits is None:
        return Check("entropy ceiling", "CONSISTENT", "Ceiling on any entropy estimated from this many "
                     "shots, whatever the number of qubits.", q)
    q["reported"] = f"{reported_bits:.4f} bits"
    if abs(reported_bits - cap) < 0.01:
        return Check("entropy ceiling", "RULED_OUT", "The reported entropy equals log2(shots): every shot "
                     "was unique, so the number measures the sample size, not the state.", q)
    if reported_bits > cap + 1e-9:
        return Check("entropy ceiling", "RULED_OUT", "Above log2(shots): impossible for a plug-in "
                     "estimate from this many shots.", q)
    return Check("entropy ceiling", "CONSISTENT", "Below the sampling ceiling.", q)


def dd_window(window_s: float, pulse_s: float, n_pulses: int, min_ratio: float = 2.0) -> Check:
    """Does an n-pulse decoupling sequence fit a fixed idle window? Free time T_f = window - n*pulse;
    feasible when window >= min_ratio * n*pulse (Qiskit's PadDynamicalDecoupling default ratio is 2).
    Symmetric spacing: T_f/(2n) at each edge, T_f/n between pulses."""
    dp = n_pulses * pulse_s
    tf = window_s - dp
    q = {"pulse train D_p": _sci(dp * 1e6, "us"), "window": _sci(window_s * 1e6, "us"),
         "free time T_f": _sci(tf * 1e6, "us"), "window / D_p": _sci(window_s / dp) if dp else "inf",
         "required ratio": _sci(min_ratio)}
    if tf > 0:
        q["edge gap T_f/2n"] = _sci(tf / (2 * n_pulses) * 1e6, "us")
        q["inner gap T_f/n"] = _sci(tf / n_pulses * 1e6, "us")
    if tf <= 0:
        return Check("DD window", "NOT_FEASIBLE", "The pulses alone fill or exceed the window: reject the "
                     "condition before dispatch; never stretch the window, shorten pulses or drop pulses "
                     "and keep the name.", q)
    if window_s < min_ratio * dp:
        return Check("DD window", "MARGINAL", "The pulses fit, but below the required window-to-sequence "
                     "ratio; a scheduler applying that ratio would not insert the sequence. Pre-register "
                     "the cell as not applicable rather than running a different sequence.", q)
    return Check("DD window", "FEASIBLE", "Fits with the required margin; still convert each gap to "
                 "integer dt and check the backend's pulse alignment.", q)


def repetition_code(n: int = 3) -> Check:
    """The n-bit repetition (bit-flip) code, the classical content of an n-qubit GHZ encoding. Its syndrome is
    the parity of each neighbouring pair, so it sees flips made after encoding, never the value encoded."""
    def syndrome(bits):
        return "".join(str(bits[i] ^ bits[i + 1]) for i in range(n - 1))
    flagged = sum(1 for e in range(1, 2 ** n) if "1" in syndrome([(e >> i) & 1 for i in range(n)]))
    q = {"syndrome of encoded 0": syndrome([0] * n), "syndrome of encoded 1": syndrome([1] * n),
         "flip patterns flagged": f"{flagged} of {2 ** n - 1}"}
    return Check("repetition code", "RULED_OUT", "Every valid codeword has the all-zero syndrome, so the syndrome "
                 "says nothing about which value was encoded -- only about flips after encoding (and it "
                 "misses the all-qubit flip, which turns one codeword into the other).", q)


# ── quantities with units, for the /physics command ──────────────────────────

_UNITS = {"": 1.0, "w": 1.0, "kw": 1e3, "gw": 1e9,   # "mw" is ambiguous: write mW or MW
          "s": 1.0, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "ns": 1e-9, "ps": 1e-12,
          "m": 1.0, "cm": 1e-2, "mm": 1e-3, "km": 1e3,
          "kg": 1.0, "g": 1e-3, "t": 1e3, "tonne": 1e3, "tonnes": 1e3,
          "hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9, "rad/s": 1.0, "j": 1.0, "%": 0.01,
          "yr": 3.15576e7, "year": 3.15576e7, "day": 86400.0, "h": 3600.0}
_CASE_SENSITIVE = {"mW": 1e-3, "MW": 1e6, "mm": 1e-3, "Mm": 1e6, "ms": 1e-3, "MHz": 1e6, "mHz": 1e-3}
_QTY = re.compile(r"^\s*([-+]?(?:\d[\d,]*)?\.?\d+(?:[eE][-+]?\d+)?)\s*([A-Za-zµ%/]*)\s*$")


def parse_quantity(text: str) -> float:
    """'1.1MW' -> 1.1e6, '35.55ns' -> 3.555e-8, '18,500kg' -> 18500, '5cm' -> 0.05."""
    m = _QTY.match(text.replace("×", "x"))
    if not m:
        raise ValueError(f"not a number with a unit: {text!r}")
    value, unit = float(m.group(1).replace(",", "")), m.group(2)
    if unit in _CASE_SENSITIVE:
        return value * _CASE_SENSITIVE[unit]
    if unit.lower() not in _UNITS:
        raise ValueError(f"unknown unit {unit!r} in {text!r}")
    return value * _UNITS[unit.lower()]


USAGE = """/physics thrust power=1.1MW [mass=18500kg]     most thrust radiated power can give
/physics rim omega=8.8e10 radius=5cm              (or freq=14GHz) rim speed vs light
/physics metric h=1.297e-19 r=5cm [power=4.4MW duration=3.15e7s]  mass-energy a static h_tt implies
/physics chsh S=2.9                               local and quantum (Tsirelson) bounds
/physics efficiency eta=194%                      energy out over energy in
/physics entropy shots=1e6 [bits=19.93]           log2(shots) ceiling on measured entropy
/physics dd window=2us pulse=35.55ns n=8 [ratio=2]  does a DD sequence fit its window
/physics planck                                   the Planck mass (compare a 'constant' with it)"""


def run_command(args: str) -> str:
    parts = args.split()
    if not parts:
        return USAGE
    name, kv = parts[0].lower(), {}
    for p in parts[1:]:
        if "=" not in p:
            return f"expected key=value, got {p!r}\n{USAGE}"
        k, v = p.split("=", 1)
        kv[k.lower()] = v
    try:
        if name == "thrust":
            c = radiation_thrust(parse_quantity(kv["power"]),
                                 parse_quantity(kv["mass"]) if "mass" in kv else None)
        elif name == "rim":
            omega = parse_quantity(kv["omega"]) if "omega" in kv else 2 * math.pi * parse_quantity(kv["freq"])
            c = rim_speed(omega, parse_quantity(kv["radius"]))
        elif name == "metric":
            c = static_metric_mass(parse_quantity(kv["h"]), parse_quantity(kv["r"]),
                                   parse_quantity(kv["power"]) if "power" in kv else None,
                                   parse_quantity(kv["duration"]) if "duration" in kv else None)
        elif name == "chsh":
            c = chsh(parse_quantity(kv.get("s", "")))
        elif name == "efficiency":
            c = efficiency(parse_quantity(kv["eta"]))
        elif name == "entropy":
            c = entropy_ceiling(parse_quantity(kv["shots"]),
                                parse_quantity(kv["bits"]) if "bits" in kv else None)
        elif name == "dd":
            c = dd_window(parse_quantity(kv["window"]), parse_quantity(kv["pulse"]), int(kv["n"]),
                          parse_quantity(kv["ratio"]) if "ratio" in kv else 2.0)
        elif name == "planck":
            c = planck_mass()
        else:
            return f"unknown check {name!r}\n{USAGE}"
    except KeyError as e:
        return f"missing {e.args[0]}=...\n{USAGE}"
    except ValueError as e:
        return str(e)
    return "\n".join(c.lines())
