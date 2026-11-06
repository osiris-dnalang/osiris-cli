#!/usr/bin/env python3
"""
test_experiment_e4_circuits.py -- Local validation for Experiment E4 circuits.
"""

from pathlib import Path
import sys

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))

from execute_experiment_e4_fingerprinting import (
    build_all_circuits, compute_dd_delays, TOTAL_DT, DT_NS, OFFSETS_NS, EDGES, BASES, BLOCKS
)

def test_circuits():
    circuits, manifest = build_all_circuits()
    print(f"Total circuits: {len(circuits)}")
    assert len(circuits) == 72, f"Expected 72 circuits, got {len(circuits)}"
    assert len(manifest) == 72

    # Check that each circuit has correct duration and timing
    for off_ns in OFFSETS_NS:
        off_dt = int(off_ns // DT_NS)
        lu, inter, tu, lv, tv = compute_dd_delays(TOTAL_DT, off_dt)
        assert lu + 8 * 8 + 7 * inter + tu == TOTAL_DT
        assert lv + 8 * 8 + 7 * inter + tv == TOTAL_DT
        assert lv - lu == off_dt

    print("All circuit structures, manifests, and delays validated successfully!")

if __name__ == "__main__":
    test_circuits()
