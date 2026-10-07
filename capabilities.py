#!/usr/bin/env python3
"""
capabilities.py -- the only functions an autonomous OSIRIS organism may call.

An organism never runs a shell command, a script path or model-written code.
It names a capability in REGISTRY and gives arguments; invoke() checks the
name, every argument against the capability's spec (type, allowed values,
range, length; nothing missing, nothing extra) and a time limit, then calls
the audited Python function in-process and returns its result. No capability
here writes files, opens the network or touches hardware -- anything that
would needs a separate, operator-approved path, not an entry in this table.
Adding a capability is a code change: reviewed, tested and /apply'd.
"""
import hashlib
import os
import signal
from dataclasses import dataclass

import dd_sim


@dataclass(frozen=True)
class Capability:
    name: str
    version: str
    fn: object
    params: dict        # name -> (kind, constraint): "seq" {of,min,max} | "enum" values | "int" (lo, hi)
    authority: str      # "sandbox_run": pure, local, no files, no network, no hardware
    max_seconds: int
    about: str


REGISTRY = {
    "simulate_dd_v2": Capability(
        name="simulate_dd_v2", version="2.0.0", fn=dd_sim.fidelity,
        params={"sequence": ("seq", {"of": dd_sim.ALPHABET, "min": 1, "max": dd_sim.MAX_LEN}),
                "noise": ("enum", tuple(dd_sim.NOISE)),
                "seed": ("int", (0, 2 ** 31 - 1)),
                "shots": ("int", (20, 400))},
        authority="sandbox_run", max_seconds=20,
        about=f"average fidelity of one qubit under dephasing and pi pulses that over-rotate by "
              f"{dd_sim.FLIP_ERROR:.0%} (X and Y distinct; dd_sim.py, local simulator)"),
}
AUDITED_FILES = ("capabilities.py", "dd_sim.py")


def code_sha256():
    """Hash of the audited code an organism can reach; recorded with every run."""
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for fn in AUDITED_FILES:
        with open(os.path.join(here, fn), "rb") as f:
            h.update(fn.encode() + b"\0" + f.read())
    return h.hexdigest()


def check(name, args):
    """None if `name` is a registered capability and `args` match its spec
    exactly, else the reason it is refused."""
    cap = REGISTRY.get(name)
    if cap is None:
        return f"unknown capability {name!r}"
    if not isinstance(args, dict):
        return "arguments must be a mapping"
    extra, missing = set(args) - set(cap.params), set(cap.params) - set(args)
    if extra or missing:
        return f"arguments do not match the spec (extra {sorted(extra)}, missing {sorted(missing)})"
    for key, (kind, rule) in cap.params.items():
        v = args[key]
        if kind == "int" and not (type(v) is int and rule[0] <= v <= rule[1]):
            return f"{key} must be an integer in [{rule[0]}, {rule[1]}]"
        if kind == "enum" and v not in rule:
            return f"{key} must be one of {list(rule)}"
        if kind == "seq" and not (isinstance(v, (list, tuple)) and rule["min"] <= len(v) <= rule["max"]
                                  and all(x in rule["of"] for x in v)):
            return f"{key} must be {rule['min']}-{rule['max']} items from {list(rule['of'])}"
    return None


def invoke(name, args):
    """(True, result) or (False, reason). Refused calls never run; a call
    over its time limit is stopped (SIGALRM, where available)."""
    problem = check(name, args)
    if problem:
        return False, problem
    cap = REGISTRY[name]
    alarm = hasattr(signal, "SIGALRM")
    if alarm:
        def _stop(signum, frame):
            raise TimeoutError(f"{name} exceeded {cap.max_seconds}s")
        old = signal.signal(signal.SIGALRM, _stop)
        signal.alarm(cap.max_seconds)
    try:
        return True, cap.fn(**args)
    except TimeoutError as e:
        return False, str(e)
    finally:
        if alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
