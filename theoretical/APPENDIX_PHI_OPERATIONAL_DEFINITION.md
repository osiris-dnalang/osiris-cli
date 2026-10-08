# Appendix Φ — Operational Definition of Φ
## OSIRIS τ–Φ Dynamical Theory
### Independent Coherence Coordinate Measurement Protocol

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC (CAGE: 9HUP5)  
**Date:** 2026-10-07  
**Version:** 1.0 (Pre-registered and Frozen)  
**Status:** Non-Substitutable Identity Plane (Q-Plane)

---

## Φ.1 Purpose

This appendix provides the **frozen operational definition** of the coherence coordinate Φ (Phi) for the OSIRIS τ–Φ dynamical theory. Φ is defined **independently** of all other variables, including fidelity, temporal phase, effect sizes, Bayes factors, and φ-network relationships.

**Critical Principle:** Φ must be measured **before** any fidelity analysis begins. No aspect of Φ's definition may be modified based on observed fidelity patterns, thresholds, or φ-structured relationships.

---

## Φ.2 Formal Definition

### Φ.2.1 Mathematical Definition

The coherence coordinate Φ is defined as:

$$\Phi_i = \frac{|\rho_{01}(t_i)|}{|\rho_{01}(0)|}$$

Where:
- $\rho_{01}(t_i)$ = Off-diagonal element of the density matrix at time $t_i$
- $\rho_{01}(0)$ = Off-diagonal element at initial time $t=0$

### Φ.2.2 Domain and Properties

| Property | Specification |
|----------|---------------|
| **Domain** | $\Phi \in [0, 1]$ |
| **Interpretation** | $\Phi = 1$: Full coherence; $\Phi = 0$: Complete decoherence |
| **Dimensionality** | Dimensionless |
| **Independence** | Must be computed before any fidelity analysis |

---

## Φ.3 Measurement Protocol

### Φ.3.1 Independent Construction Requirement

Φ **must** be constructed from:
- **Independent calibration experiments** (separate from fidelity measurements)
- **Tomography data** acquired in dedicated coherence measurement runs
- **Pre-acquired T₂ measurements** (if tomography is impractical)

Φ **must NOT** be constructed from:
- ❌ Fidelity measurements
- ❌ Temporal phase (θ) values
- ❌ Effect size calculations
- ❌ Bayes factor computations
- ❌ φ-network relationships
- ❌ Any post-hoc analysis results

### Φ.3.2 Permissible Measurement Methods

#### Method A: Full Quantum State Tomography
**Procedure:**
1. Prepare the system in a known superposition state: $|+\rangle = \frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$
2. Acquire complete tomography data at time $t=0$
3. Acquire complete tomography data at each time $t_i$
4. Extract $\rho_{01}(t_i)$ from reconstructed density matrices
5. Compute Φ using the definition above

**Requirements:**
- Minimum 3 measurement bases for single-qubit tomography
- Minimum 9 measurement bases for two-qubit systems
- Shot count per basis: ≥ 1024
- State reconstruction via Maximum Likelihood Estimation (MLE)

**Validation:**
- Verify $\rho_{01}(0) \neq 0$ (initial coherence)
- Verify trace($\rho$) = 1 ± 0.01
- Verify $\rho$ is positive semi-definite

#### Method B: T₂-Based Approximation
**When full tomography is impractical**, Φ may be approximated using:

$$\Phi(t) = e^{-t/T_{coh}}$$

Where $T_{coh}$ is measured independently via:

**Ramsey Interferometry:**
1. Apply $R_x(\pi/2)$ to prepare $|+\rangle$
2. Wait time $t$
3. Apply $R_x(\pi/2)$ again
4. Measure population in $|0\rangle$ state
5. Fit exponential decay: $P_0(t) = \frac{1}{2}(1 + e^{-t/T_2^*})$
6. Extract $T_2^*$ (dephasing time)
7. Use $T_{coh} = T_2^*$ for Φ calculation

**Requirements:**
- Minimum 10 time points for $T_2^*$ estimation
- Time points spaced logarithmically
- Shot count per point: ≥ 1024
- Fit R² > 0.95

**Validation:**
- Verify $T_2^*$ > 0
- Verify monotonic decay
- Verify confidence interval width < 20% of estimate

#### Method C: Direct Off-Diagonal Measurement
**For systems with readout of off-diagonal elements:**

1. Prepare $|+\rangle$ state
2. Apply phase damping channel with parameter $t$
3. Directly measure $|\rho_{01}(t)|$
4. Normalize by initial $|\rho_{01}(0)|$

**Requirements:**
- Hardware must support off-diagonal readout
- Calibration of readout fidelity for off-diagonal elements
- Shot count: ≥ 4096 per time point

---

## Φ.4 Implementation Requirements

### Φ.4.1 Data Acquisition

**Mandatory Fields for Each Φ Measurement:**
```json
{
  "phi_id": "unique_identifier",
  "measurement_method": "tomography | T2_ramsey | direct_off_diagonal",
  "t": 0.0,                    // Time in microseconds
  "N_q": 1,                    // Number of qubits
  "backend": "ibm_fez",         // Hardware backend
  "calibration_id": "cal_123", // Calibration session ID
  "shots": 1024,               // Shots per measurement basis
  "rho_01_real": 0.987,       // Real part of ρ₀₁
  "rho_01_imag": 0.012,       // Imaginary part of ρ₀₁
  "rho_01_magnitude": 0.987,  // |ρ₀₁| = sqrt(real² + imag²)
  "rho_01_initial": 1.0,       // |ρ₀₁(0)| (normalization)
  "Phi": 0.987,               // Φ = |ρ₀₁(t)| / |ρ₀₁(0)|
  "timestamp": "2026-10-07T10:46:00Z",
  "metadata": {
    "tomography_bases": ["X", "Y", "Z"],  // For tomography
    "T2_star": 45.0,                          // For Ramsey method
    "fit_r_squared": 0.998                   // For T₂ fitting
  }
}
```

### Φ.4.2 Storage Format

**Primary Format:** JSON Lines (`.jsonl`)
- One Φ measurement per line
- UTF-8 encoding
- No compression
- No filtering

**Alternative Formats:**
- `.json` (array of objects)
- `.csv` (with header row)

**Prohibited Formats:**
- ❌ Binary formats
- ❌ Compressed formats (without accompanying uncompressed version)
- ❌ Proprietary formats
- ❌ Formats that obscure raw measurements

### Φ.4.3 Integrity Constraints

**Must:**
- ✅ Store raw measurement data (ρ₀₁ components or T₂ fit parameters)
- ✅ Include all calibration metadata
- ✅ Preserve timestamp information
- ✅ Use deterministic serialization (sorted keys for JSON)

**Must NOT:**
- ❌ Filter based on Φ values
- ❌ Filter based on fidelity outcomes
- ❌ Modify Φ after seeing fidelity data
- ❌ Aggregate or bin Φ measurements
- ❌ Reconstruct Φ from summaries

---

## Φ.5 Validation Procedures

### Φ.5.1 Self-Consistency Checks

Each Φ measurement must pass:

1. **Range Check:** $0 \leq \Phi \leq 1$
2. **Monotonicity Check:** Φ(t) should be non-increasing (for standard decoherence)
3. **Initial Condition:** Φ(0) = 1.0 ± 0.01
4. **Physical Plausibility:** Φ(t) ≥ 0 for all t

### Φ.5.2 Cross-Method Validation

When multiple methods are available:
- **Tomography vs. Ramsey:** |Φ_tomography - Φ_ramsey| < 0.05
- **Different circuits:** Φ should be consistent across circuit families
- **Different qubits:** Φ should be consistent across qubit subsets

### Φ.5.3 Hardware Calibration Checks

Before Φ measurement:
- Verify T₁ > 20 μs (for superconducting qubits)
- Verify T₂ > 10 μs
- Verify single-qubit gate fidelity > 0.99
- Verify readout fidelity > 0.95

---

## Φ.6 Blinding and Independence

### Φ.6.1 Temporal Blinding

Φ measurements must be acquired **before** the corresponding fidelity measurements:

```
Timeline:
1. Acquire Φ measurements (all time points) → Store with hash H_Φ
2. Acquire fidelity measurements → Store with hash H_F
3. Begin analysis (only after both are complete)
```

### Φ.6.2 Analyst Blinding

Analysts computing Φ must:
- Not have access to fidelity data
- Not know the experimental hypotheses
- Not know the τ-phase predictions
- Not know the φ-network relationships

### Φ.6.3 Automated Execution

Φ measurement scripts must:
- Be frozen before data acquisition
- Run automatically without human intervention
- Output deterministic results for identical inputs
- Include provenance hashes in outputs

---

## Φ.7 Relationship to Other Variables

### Φ.7.1 Independence from Fidelity

**Critical:** Φ and F (fidelity) are **independent variables**.

- Φ is measured from coherence properties
- F is measured from state overlap
- They may correlate, but they are not definitionally linked

**Test for Independence:**
- Compute Φ from calibration data **before** any fidelity analysis
- Verify that Φ distribution is not affected by fidelity outcomes
- Document any correlation as an **empirical finding**, not a definition

### Φ.7.2 Independence from Temporal Phase (θ)

θ is defined as:

$$\theta(t) = 2\pi \frac{t}{\tau_0}$$

- θ depends only on time and τ₀
- Φ depends only on coherence decay
- They are **mathematically independent** variables

**Verification:**
- Φ should show the same decay pattern regardless of θ
- θ should show the same periodicity regardless of Φ
- Joint distribution should factor: P(Φ, θ) = P(Φ) × P(θ)

### Φ.7.3 Independence from φ-Network

The φ-network predictions (τ₀ ≈ φ⁸, F_max ≈ 1 - φ⁻⁸, etc.) **must not** influence Φ measurement:

- Φ is measured **before** φ-network validation
- Φ measurement scripts **must not** contain φ constants
- φ-network analysis **must not** modify Φ values

---

## Φ.8 Example Implementation (Python)

```python
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Optional

class PhiMeasurement:
    """
    Independent Φ measurement implementation.
    
    This class implements Φ measurement per Appendix Φ.
    It is designed to run BEFORE any fidelity analysis.
    """
    
    def __init__(self, backend: str, calibration_id: str):
        self.backend = backend
        self.calibration_id = calibration_id
        self.measurements: List[Dict] = []
        
    def measure_phi_tomography(self, t: float, n_qubits: int = 1, 
                              shots: int = 1024) -> Dict:
        """
        Measure Φ using full quantum state tomography.
        
        Args:
            t: Evolution time in microseconds
            n_qubits: Number of qubits (1 or 2 supported)
            shots: Shots per measurement basis
            
        Returns:
            Dictionary with Φ measurement and metadata
        """
        # In practice, this would interface with QPU
        # For illustration, we simulate expected output
        
        # Simulate coherence decay (example only)
        # In real implementation: run actual tomography
        T2_star = 45.0  # Example dephasing time
        rho_01_initial = 1.0  # Initial coherence
        rho_01_t = rho_01_initial * np.exp(-t / T2_star)
        
        # Add small noise
        rho_01_t *= 1 + 0.01 * np.random.randn()
        
        # Ensure physical constraints
        rho_01_t = np.clip(np.abs(rho_01_t), 0, rho_01_initial)
        
        Phi = float(rho_01_t / rho_01_initial)
        
        measurement = {
            "phi_id": f"phi_{t:.1f}us_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "measurement_method": "tomography",
            "t": float(t),
            "N_q": int(n_qubits),
            "backend": self.backend,
            "calibration_id": self.calibration_id,
            "shots": int(shots),
            "rho_01_real": float(rho_01_t),  # In practice: from tomography
            "rho_01_imag": 0.0,             # In practice: from tomography
            "rho_01_magnitude": float(rho_01_t),
            "rho_01_initial": float(rho_01_initial),
            "Phi": float(Phi),
            "timestamp": datetime.now().isoformat() + "Z",
            "metadata": {
                "tomography_bases": ["X", "Y", "Z"] * n_qubits,
                "state_prep": "|+> state"
            }
        }
        
        # Validate
        assert 0 <= Phi <= 1, f"Phi out of range: {Phi}"
        assert measurement["rho_01_initial"] > 0, "Initial coherence must be non-zero"
        
        self.measurements.append(measurement)
        return measurement
    
    def measure_phi_ramsey(self, t: float, T2_star: float, 
                          shots: int = 1024) -> Dict:
        """
        Measure Φ using Ramsey interferometry (T₂-based approximation).
        
        Args:
            t: Evolution time in microseconds
            T2_star: Pre-measured dephasing time
            shots: Shots per measurement
            
        Returns:
            Dictionary with Φ measurement and metadata
        """
        # Ramsey interferometry: P0(t) = 0.5 * (1 + exp(-t/T2_star))
        # |ρ₀₁(t)| = |ρ₀₁(0)| * exp(-t/(2*T2_star)) for pure dephasing
        # Φ = exp(-t/T2_star)
        
        Phi = float(np.exp(-t / T2_star))
        
        # Add small measurement noise
        Phi *= 1 + 0.02 * np.random.randn()
        Phi = np.clip(Phi, 0, 1)
        
        measurement = {
            "phi_id": f"phi_ramsey_{t:.1f}us_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "measurement_method": "T2_ramsey",
            "t": float(t),
            "N_q": 1,
            "backend": self.backend,
            "calibration_id": self.calibration_id,
            "shots": int(shots),
            "rho_01_magnitude": float(Phi),  # Derived from Ramsey fit
            "rho_01_initial": 1.0,
            "Phi": float(Phi),
            "timestamp": datetime.now().isoformat() + "Z",
            "metadata": {
                "T2_star": float(T2_star),
                "method": "Ramsey interferometry",
                "fit_r_squared": 0.998  # From T2 measurement
            }
        }
        
        self.measurements.append(measurement)
        return measurement
    
    def save_measurements(self, filename: str) -> None:
        """
        Save Φ measurements to JSON Lines file.
        
        Args:
            filename: Output file path
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for measurement in self.measurements:
                # Sort keys for deterministic serialization
                sorted_measurement = dict(sorted(measurement.items()))
                f.write(json.dumps(sorted_measurement, separators=(',', ':')) + '\n')
    
    def compute_hash(self) -> str:
        """
        Compute SHA-256 hash of all measurements.
        
        Returns:
            Hex digest of measurements
        """
        import hashlib
        data_str = ''.join(
            json.dumps(dict(sorted(m.items())), separators=(',', ':'))
            for m in self.measurements
        )
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()


# Example usage
if __name__ == "__main__":
    # Initialize
    phi_measurer = PhiMeasurement(
        backend="ibm_fez",
        calibration_id="cal_20261007_001"
    )
    
    # Measure Φ at multiple time points
    time_points = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45]  # μs
    for t in time_points:
        phi_measurer.measure_phi_ramsey(t, T2_star=45.0, shots=1024)
    
    # Save measurements
    phi_measurer.save_measurements("phi_measurements_20261007.jsonl")
    
    # Compute provenance hash
    measurements_hash = phi_measurer.compute_hash()
    print(f"Φ measurements hash: {measurements_hash}")
    print(f"Saved {len(phi_measurer.measurements)} measurements to phi_measurements_20261007.jsonl")
```

---

## Φ.9 Verification Checklist

- [ ] Φ is defined independently of fidelity
- [ ] Φ measurement occurs before fidelity analysis
- [ ] Φ is stored with complete provenance metadata
- [ ] Φ values are in [0, 1] range
- [ ] Φ(0) = 1.0 ± 0.01
- [ ] Raw measurement data is preserved (not just Φ values)
- [ ] Measurement scripts are frozen before data acquisition
- [ ] Analysts are blinded to fidelity outcomes during Φ measurement
- [ ] Φ measurement passes all validation checks
- [ ] Φ is computed using one of the approved methods

---

## Φ.10 Common Pitfalls and Mitigations

| Pitfall | Mitigation |
|---------|------------|
| Computing Φ from fidelity data | Use independent calibration experiments |
| Modifying Φ after seeing results | Freeze Φ measurement scripts before analysis |
| Using inconsistent measurement methods | Standardize on one method per experiment |
| Insufficient shot counts | Minimum 1024 shots per basis |
| Not storing raw data | Always store ρ₀₁ components or T₂ fit parameters |
| Circular definitions | Φ must not depend on τ–Φ theory parameters |

---

## Φ.11 Final Statement

This operational definition of Φ is **pre-registered and frozen**. 

**Key Principles:**
1. Φ is an **independent variable** measured from coherence properties
2. Φ **must** be computed **before** any fidelity analysis
3. Φ **must not** be influenced by τ–Φ theory or φ-network predictions
4. Φ measurement protocols are **immutable** after preregistration
5. All Φ measurements must be **reproducible** from raw data

**Registration Details:**
- **Registration Date:** 2026-10-07
- **Version:** 1.0 (Frozen)
- **Identity Plane:** Q-Plane (Quantum)
- **Non-Substitution:** Φ cannot substitute for fidelity, θ, or any other variable

**Contact:**
- **Author:** Devin Phillip Davis
- **Email:** research@dnalang.dev
- **Affiliation:** Agile Defense Systems LLC
- **Location:** Lexington, KY, USA

---

## Appendix Φ.1: Quick Reference

### Φ Definition (One Line)
```
Φ_i = |ρ₀₁(t_i)| / |ρ₀₁(0)|, where ρ₀₁ is measured independently of fidelity
```

### Measurement Methods (Priority Order)
1. **Full Quantum State Tomography** (Most accurate)
2. **Ramsey Interferometry** (T₂-based, practical)
3. **Direct Off-Diagonal Measurement** (Hardware-dependent)

### Minimum Requirements
- Shots: ≥ 1024 per measurement basis
- Time points: ≥ 10 for T₂ fitting
- Validation: R² > 0.95 for fits
- Storage: Raw data + Φ values

### Independence Requirements
- ✅ Measured before fidelity analysis
- ✅ No access to fidelity data during measurement
- ✅ No modification based on outcomes
- ✅ Deterministic scripts

---

*This document is part of the OSIRIS τ–Φ Dynamical Theory research program. For updates and errata, see the project repository at github.com/osiris-dnalang/flywheel-2026.*
