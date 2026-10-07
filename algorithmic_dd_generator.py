#!/usr/bin/env python3
"""
algorithmic_dd_generator.py -- deterministic, non-ML generator for dynamical-decoupling
(DD) sequences satisfying DDSpace's dual-parity constraint (even X-count AND even Y-count,
independently, per sublattice) BY CONSTRUCTION.

Built after this session established, through real testing (17x more diverse real
training data, zero measurable improvement), that Engine 3's NCLM -- a ~726K-parameter
byte-level model -- cannot reliably learn this task; an isolated architectural limitation,
not a data problem. Ordinary combinatorics solves it exactly instead of searching for it:
there are exactly 1641 valid 8-symbol {I,X,Y} sublattice patterns out of 3**8 = 6561 total
(confirmed below by full enumeration against the real DDSpace.screen(), not a hand-derived
parity check) -- small enough to enumerate once and sample pairs from.

Standalone: `python3 algorithmic_dd_generator.py --count 20 [--seed N]`
Also invoked by /dd programmatic in the osiris REPL.
"""
import argparse
import itertools
import random
import sys
import os

DNALANG_SRC = "/data/data/com.termux/files/home/.osiris/src/dnalang-core"
if DNALANG_SRC not in sys.path:
    sys.path.insert(0, DNALANG_SRC)

from dnalang.evolve.space import DDSpace  # noqa: E402

PULSES = ("I", "X", "Y")
K = 8

_space = DDSpace(n_qubits=8, K=K)


def _valid_sublattices():
    """All length-K {I,X,Y} strings passing DDSpace.screen()'s real dual-parity rule.
    screen() checks the 'even' and 'odd' keys independently against the identical rule,
    so probing a single candidate as both keys at once validates it standalone without
    a second, hand-written parity check that could drift from the real one."""
    valid = []
    for combo in itertools.product(PULSES, repeat=K):
        seq = list(combo)
        if _space.screen({"even": seq, "odd": seq, "offset": 0.0}) is None:
            valid.append("".join(combo))
    return valid


_VALID_SUBLATTICES = _valid_sublattices()


def _canonical_family_strings():
    """Canonical baselines, guaranteed reachable by direct construction -- not left to
    chance sampling. cpmg8/xy4x2/xy8 patterns match this session's real published
    hardware data; xy4 also matches DDSpace.baselines()'s own definition."""
    families = {"cpmg8": "XXXXXXXX", "xy4x2": "XYXYXYXY", "xy8": "XYXYYXYX"}
    out = []
    for name, pat in families.items():
        assert pat in _VALID_SUBLATTICES, f"{name} pattern {pat!r} unexpectedly fails screen()"
        for offset in _space.offsets:
            out.append(f"{pat}|{pat}|{offset}")
    return out


_CANONICAL = _canonical_family_strings()


def generate(count: int, seed: int | None = None) -> list:
    """Return `count` valid DD sequence strings ('EVEN|ODD|OFFSET'), each satisfying
    DDSpace.screen() by construction. Canonical families come first (guaranteed present,
    not probabilistic), then novel interleaved combinations sampled from the full
    valid-sublattice pool fill the remainder."""
    rng = random.Random(seed)
    out = []
    seen = set()

    for s in _CANONICAL:
        if len(out) >= count:
            break
        if s not in seen:
            out.append(s)
            seen.add(s)

    attempts = 0
    limit = max(count * 50, 10000)
    while len(out) < count and attempts < limit:
        attempts += 1
        even = rng.choice(_VALID_SUBLATTICES)
        odd = rng.choice(_VALID_SUBLATTICES)
        offset = rng.choice(_space.offsets)
        s = f"{even}|{odd}|{offset}"
        if s in seen:
            continue
        # Re-verify against the real screen() via the actual genome dict shape -- should
        # be unreachable given _VALID_SUBLATTICES's own construction, kept as a defensive
        # guarantee rather than trusting sublattice-level membership alone.
        g = {"even": list(even), "odd": list(odd), "offset": offset}
        if _space.screen(g) is not None:
            continue
        out.append(s)
        seen.add(s)

    return out[:count]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    for s in generate(args.count, seed=args.seed):
        print(s)


if __name__ == "__main__":
    main()
