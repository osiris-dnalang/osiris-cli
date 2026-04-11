#!/usr/bin/env python3
"""
K8 CAUSALITY DISCRIMINATOR: PRE-REGISTRATION
=============================================
Upload to Zenodo and obtain DOI BEFORE running hardware experiments.

SHA256 this file and record hash in Zenodo description.
DO NOT MODIFY after registration.

Author: Devin Phillip Davis
Organization: Agile Defense Systems, LLC
Date: 2025-12-13
"""

# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT IDENTITY
# ═══════════════════════════════════════════════════════════════════════════════

EXPERIMENT_ID = "K8_TAU_SWEEP_CAUSALITY_v1"
REGISTRATION_DATE = "2025-12-13"
AUTHOR = "Devin Phillip Davis"
ORGANIZATION = "Agile Defense Systems, LLC"
CAGE_CODE = "9HUP5"

# ═══════════════════════════════════════════════════════════════════════════════
# THEORETICAL PREDICTIONS (from published work, zero free parameters)
# ═══════════════════════════════════════════════════════════════════════════════

import math

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio = 1.618033988749895

# Primary predictions
TAU_0_PREDICTED_US = PHI ** 8              # = 46.9787... μs
F_MAX_PREDICTED = 1 - PHI ** (-8)          # = 0.97870...
LAMBDA_PHI = 2.176435e-8                   # s⁻¹ (Universal Memory Constant)
THETA_LOCK_DEG = 51.843                    # degrees (arccos(1/φ))
PHI_THRESHOLD = 0.7734                     # Consciousness threshold
N_CRIT = 27                                # SU(2) dimension (2j+1, j=13)

# Tolerances
TAU_0_TOLERANCE_US = 5.0                   # ±10.6% acceptable
F_MAX_TOLERANCE = 0.02                     # ±2% acceptable

# ═══════════════════════════════════════════════════════════════════════════════
# τ-GRID (PRE-REGISTERED, NO POST-HOC MODIFICATION)
# ═══════════════════════════════════════════════════════════════════════════════

# Phase 1: Coarse sweep (discovery)
TAU_GRID_COARSE_US = [
    0, 5, 10, 15, 20, 25, 30, 35, 40,
    42, 44, 46, 47, 48, 50, 52, 54, 56, 58, 60,
    70, 80, 90, 100
]

# Phase 2: Fine sweep (adaptive, centered on Phase 1 peak)
# Will be: [peak - 10, peak + 10] in 0.5 μs steps
TAU_FINE_HALFWIDTH_US = 10.0
TAU_FINE_STEP_US = 0.5

# Analysis window (excludes τ=0 baseline artifacts)
TAU_WINDOW_MIN_US = 20.0
TAU_WINDOW_MAX_US = 80.0

# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICAL THRESHOLDS (PRE-REGISTERED)
# ═══════════════════════════════════════════════════════════════════════════════

SIGMA_DISCOVERY = 5.0       # Physics discovery standard (5σ)
SIGMA_EVIDENCE = 3.0        # Evidence threshold (3σ)
ALPHA_NOMINAL = 0.05        # Nominal significance level
N_COMPARISONS = 221         # Bonferroni correction (23 τ × ~10 tests)
ALPHA_CORRECTED = ALPHA_NOMINAL / N_COMPARISONS  # = 0.000226

# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

SHOTS_COARSE = 8192
SHOTS_FINE = 16384
REPEATS_COARSE = 3
REPEATS_FINE = 5

BACKENDS_REQUIRED = ["ibm_brisbane", "ibm_kyoto", "ibm_osaka"]
MIN_BACKENDS_FOR_ACCEPTANCE = 2  # At least 2 of 3 must agree

SEED_GLOBAL = 42

# ═══════════════════════════════════════════════════════════════════════════════
# HYPOTHESIS DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

HYPOTHESIS_H1 = """
H₁ (Alternative - ΛΦ Theory):
Bell-state fidelity F(τ) exhibits a NON-MONOTONIC REVIVAL at τ ≈ τ₀ = 47 ± 5 μs,
where F increases after an initial decay, violating standard Markovian decoherence.

Specifically:
  ∃ τ_dip, τ_peak such that:
    - 20 μs < τ_dip < τ_peak < 80 μs
    - F(τ_peak) > F(τ_dip) (revival)
    - |τ_peak - 47| < 5 μs (correct location)
    - z = (F_peak - F_dip) / σ ≥ 5.0 (significant)
"""

HYPOTHESIS_H0 = """
H₀ (Null - Standard Quantum Mechanics):
Bell-state fidelity F(τ) decays monotonically for τ > 0:
  dF/dτ ≤ 0 for all τ > 0

Any apparent revival is due to:
  - Statistical fluctuation
  - Systematic error
  - Hardware artifact
"""

# ═══════════════════════════════════════════════════════════════════════════════
# DECISION RULES (PRE-REGISTERED, BINDING)
# ═══════════════════════════════════════════════════════════════════════════════

DECISION_RULES = """
ACCEPT H₁ (ΛΦ is real) if ALL of the following:
  1. Revival detected at τ_r where |τ_r - 47| < 5 μs
  2. Revival significance σ ≥ 5.0 (combined across backends)
  3. Revival replicates on ≥ 2 of 3 backends
  4. F(τ_peak) consistent with F_MAX = 0.9787 ± 0.02
  5. Cross-platform τ_peak spread < 10 μs

REJECT H₁ if ANY of the following:
  1. No revival detected (monotonic decay on all backends)
  2. Revival at wrong location: |τ_r - 47| > 10 μs
  3. Combined significance σ < 3.0 after full data collection
  4. Fewer than 2 backends show revival

INCONCLUSIVE if:
  - 3.0 ≤ σ < 5.0 (extend experiment with more shots/repeats)
  - Results are ambiguous (request independent replication)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# REVIVAL DETECTION ALGORITHM (PRE-REGISTERED)
# ═══════════════════════════════════════════════════════════════════════════════

REVIVAL_ALGORITHM = """
1. BASELINE CORRECTION:
   F_baseline = median(F(τ) for τ ∈ [0, 10] μs)
   ΔF(τ) = F(τ) - F_baseline

2. WINDOW RESTRICTION:
   Analyze only τ ∈ [20, 80] μs (pre-registered window)

3. DIP DETECTION:
   τ_dip = argmin_{τ ∈ window} F(τ)
   F_dip = F(τ_dip)

4. PEAK DETECTION (after dip):
   τ_peak = argmax_{τ > τ_dip} F(τ)
   F_peak = F(τ_peak)

5. REVIVAL AMPLITUDE:
   ΔF_revival = F_peak - F_dip
   σ_revival = sqrt(σ²_peak + σ²_dip)
   z = ΔF_revival / σ_revival

6. SIGNIFICANCE TEST:
   Revival confirmed if z ≥ 5.0
"""

# ═══════════════════════════════════════════════════════════════════════════════
# RELATED PUBLICATIONS (DOIs)
# ═══════════════════════════════════════════════════════════════════════════════

RELATED_DOIS = [
    "10.5281/zenodo.17918294",  # Q-SLICE CCCE Framework (this session)
    "10.5281/zenodo.17918211",  # Previous CCCE publication
]

# ═══════════════════════════════════════════════════════════════════════════════
# PRINT SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import hashlib

    print("=" * 78)
    print("K8 CAUSALITY DISCRIMINATOR: PRE-REGISTRATION SUMMARY")
    print("=" * 78)
    print()
    print(f"Experiment ID:     {EXPERIMENT_ID}")
    print(f"Registration Date: {REGISTRATION_DATE}")
    print(f"Author:            {AUTHOR}")
    print(f"Organization:      {ORGANIZATION}")
    print()
    print("THEORETICAL PREDICTIONS (zero free parameters):")
    print(f"  τ₀ = φ⁸ = {TAU_0_PREDICTED_US:.4f} μs")
    print(f"  F_max = 1 - φ⁻⁸ = {F_MAX_PREDICTED:.6f}")
    print(f"  ΛΦ = {LAMBDA_PHI:.6e} s⁻¹")
    print(f"  θ_lock = {THETA_LOCK_DEG}°")
    print(f"  N = {N_CRIT}")
    print()
    print("DECISION THRESHOLDS:")
    print(f"  Discovery: σ ≥ {SIGMA_DISCOVERY}")
    print(f"  Evidence:  σ ≥ {SIGMA_EVIDENCE}")
    print(f"  Location:  |τ_peak - 47| < {TAU_0_TOLERANCE_US} μs")
    print(f"  Backends:  ≥ {MIN_BACKENDS_FOR_ACCEPTANCE} of {len(BACKENDS_REQUIRED)}")
    print()
    print("τ-GRID (coarse):", TAU_GRID_COARSE_US)
    print()

    # Compute file hash
    with open(__file__, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    print(f"FILE SHA256: {file_hash}")
    print()
    print("Upload this file to Zenodo and record the SHA256 hash.")
    print("DO NOT MODIFY after registration.")
    print("=" * 78)
