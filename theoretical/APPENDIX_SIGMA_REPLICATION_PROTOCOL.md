# Appendix Σ — Independent-Lab Replication Protocol
OSIRIS τ–Φ Dynamical Theory  
Independent Laboratory Replication Protocol  
Author: Devin Phillip Davis  
Affiliation: Agile Defense Systems LLC (CAGE: 9HUP5)  
Date: 2026-10-07  
Location: Lexington, KY, USA

---

## Σ.1 Purpose

To define the complete procedure for independent laboratory replication of the OSIRIS τ–Φ dynamical theory. This protocol ensures that:

- Replication is conducted without prior access to confirmatory data
- All parameters are pre-registered and frozen
- Raw-shot archival meets Appendix R requirements
- Statistical analysis follows Appendix Δ exactly
- Cross-plane identity guarantees (Appendix Θ) are maintained
- Cryptographic provenance (Appendix Ψ) is preserved

This appendix is pre-registered and frozen. No modifications may be made after confirmatory data acquisition begins.

---

## Σ.2 Scope

This protocol applies to:

- Independent quantum hardware laboratories
- Third-party research groups
- Journal-mandated replication studies
- Cross-backend validation efforts

All replication attempts must adhere strictly to this protocol to be considered valid for τ–Φ theory evaluation.

---

## Σ.3 Prerequisites

### Σ.3.1 Hardware Requirements

**Minimum Backend Specifications:**
- Qubit count: ≥ 8 physical qubits in a connected topology
- T₁ coherence time: > 20 μs (mean across selected qubits)
- T₂ coherence time: > 10 μs (mean across selected qubits)
- Single-qubit gate fidelity: ≥ 0.998
- Two-qubit gate fidelity: ≥ 0.98
- Readout error: ≤ 0.02
- Backend type: Non-IBM preferred (Rigetti, Quantinuum, IonQ, or equivalent)

**Approved Backend List:**
- Rigetti: Aspen-M series or newer
- Quantinuum: H-series trapped-ion processors
- IonQ: Aria or Forte systems
- IBM: Heron r2 or newer (if non-IBM unavailable)

### Σ.3.2 Software Requirements

- Python 3.10+
- Qiskit 1.0+ (for IBM backends)
- Cirq 1.2+ (for Google backends)
- PennyLane 0.30+ (for cross-backend compatibility)
- NumPy, SciPy, pandas, matplotlib
- OSIRIS analysis package (flywheel-2026)

### Σ.3.3 Personnel Requirements

- At least one quantum hardware operator with backend access
- At least one data analyst independent of the hardware operator
- No overlap with OSIRIS confirmatory team personnel
- Signed Independent-Lab Declaration (Section Σ.9)

---

## Σ.4 Pre-Replication Preparation

### Σ.4.1 Packet Acquisition

1. Download the complete OSIRIS τ–Φ Confirmatory Preregistration Packet
   - DOI: [To be inserted after Zenodo upload]
   - SHA-256: [To be computed]
   - All files in `preregistration/` directory

2. Verify packet integrity:
   ```bash
   sha256sum -c tauPhi_manifest.sha256
   ```

3. Confirm all appendices are present:
   - Appendix Ω (Preregistration)
   - Appendix Δ (Statistical Analysis Plan)
   - Appendix Φ (Operational Definition of Φ)
   - Appendix R (Raw-Shot Specification)
   - Appendix Θ (Identity Guarantees)
   - Appendix Ψ (Canonical Manifest)

### Σ.4.2 Ledger Anchoring

1. Compute SHA-256 hash of `Appendix_Psi_manifest.json`
   ```bash
   sha256sum manifests/tauPhi_manifest_canonical.json
   ```

2. Record the hash in `provenance/ledger_anchor.txt`

3. Append the hash to your laboratory's write-ahead ledger

4. Publish the ledger entry timestamp (UTC)

### Σ.4.3 Environment Setup

1. Create isolated analysis environment:
   ```bash
   python -m venv osiris_replication_env
   source osiris_replication_env/bin/activate
   pip install -r requirements_replication.txt
   ```

2. requirements_replication.txt:
   ```
numpy==1.26.0
scipy==1.11.0
pandas==2.1.0
matplotlib==3.8.0
qiskit==1.0.0
flywheel-2026
```

3. Freeze all package versions:
   ```bash
   pip freeze > environment_frozen.txt
   ```

---

## Σ.5 Circuit Selection and Preparation

### Σ.5.1 Circuit Families

Replicate using the same circuit families from Smoking Guns v5.0:

**Family 1: Bell States**
- 2-qubit Bell state: |Φ⁺⟩ = (|00⟩ + |11⟩)/√2
- Target fidelity: F_bell = ⟨Φ⁺|ρ|Φ⁺⟩
- Circuit depth: 1 (CNOT + H)

**Family 2: GHZ States**
- N-qubit GHZ: |GHZ⟩ = (|0...0⟩ + |1...1⟩)/√2
- N ∈ {4, 6, 8}
- Target fidelity: F_ghz = ⟨GHZ|ρ|GHZ⟩

**Family 3: W States**
- N-qubit W state: |W⟩ = (|0...01⟩ + |0...10⟩ + ... + |1...00⟩)/√N
- N ∈ {4, 6, 8}
- Target fidelity: F_w = ⟨W|ρ|W⟩

**Family 4: Randomized Benchmarking**
- Clifford sequences of length m ∈ {1, 5, 10, 20, 40}
- 100 random circuits per length
- Target: Average gate fidelity

**Family 5: Controlled Phase-Rotation**
- Circuit: H⊗n → CPhase(θ) → H⊗n
- θ ∈ {π/4, π/2, 3π/4, π}
- Target: Phase coherence preservation

### Σ.5.2 Qubit Selection

1. Identify the highest-coherence subgraph on your backend
2. Select 8 connected qubits with minimal crosstalk
3. Document selection criteria and calibration data
4. Record qubit mapping: `qubit_map.json`

### Σ.5.3 Circuit Transpilation

1. Transpile all circuits to target backend
2. Record transpilation parameters:
   - Optimization level
   - Basis gates
   - Coupling map
   - Pulse duration scaling
3. Save transpiled circuits: `circuits_transpiled/`
4. Compute circuit metrics:
   - Depth
   - CX count
   - Gate count
   - Duration

---

## Σ.6 Φ Construction Protocol

### Σ.6.1 Independent Φ Measurement

Φ MUST be constructed independently from fidelity, θ, and φ-network quantities.

**Definition:**
```
Φ_i = |ρ₀₁(t_i)| / |ρ₀₁(0)|
```

Where:
- ρ₀₁(t) is the off-diagonal element of the density matrix
- t_i are the time points for Φ measurement

### Σ.6.2 Measurement Methods

**Method A: Quantum State Tomography (Preferred)**
1. Prepare |+0⟩ state on each qubit pair
2. Measure full density matrix at times t ∈ [0, τ_max]
3. Extract |ρ₀₁(t)| for each time point
4. Normalize by |ρ₀₁(0)|

**Method B: Ramsey Interference**
1. Apply X(π/2) pulse
2. Wait time t
3. Apply X(π/2) pulse
4. Measure in Z basis
5. Fit oscillation: A cos(2πft + φ) + B
6. Extract coherence: |ρ₀₁(t)| ∝ A(t)

**Method C: Direct Off-Diagonal Reconstruction**
1. Use parity oscillation measurements
2. For Bell state: P(00) + P(11) - P(01) - P(10) = 2|ρ₀₁|
3. Normalize appropriately

### Σ.6.3 Φ Measurement Circuit

```python
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np

def measure_phi(tau_values, backend, qubits):
    """
    Measure Φ(t) = |ρ₀₁(t)| / |ρ₀₁(0)| independently
    
    Args:
        tau_values: List of delay times in microseconds
        backend: QPU backend
        qubits: Pair of qubits for measurement
    
    Returns:
        phi_values: List of Φ values
        raw_data: Dictionary of raw measurement data
    """
    phi_values = []
    raw_data = {}
    
    # Reference measurement at t=0
    qc_ref = QuantumCircuit(2, 2)
    qc_ref.h(0)
    qc_ref.cx(0, 1)
    qc_ref.measure([0, 1], [0, 1])
    
    # Execute reference
    job_ref = backend.run(qc_ref, shots=10000)
    counts_ref = job_ref.result().get_counts()
    raw_data['reference'] = counts_ref
    
    # Compute |ρ₀₁(0)| from reference
    rho_01_0 = compute_off_diagonal(counts_ref)
    
    # Measure at each tau
    for tau in tau_values:
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.delay(tau * 1e-6, 0)  # Convert μs to s
        qc.delay(tau * 1e-6, 1)
        qc.measure([0, 1], [0, 1])
        
        job = backend.run(qc, shots=10000)
        counts = job.result().get_counts()
        raw_data[f'tau_{tau}'] = counts
        
        rho_01_t = compute_off_diagonal(counts)
        phi = abs(rho_01_t / rho_01_0)
        phi_values.append(phi)
    
    return phi_values, raw_data

def compute_off_diagonal(counts):
    """Compute |ρ₀₁| from measurement counts"""
    # For Bell state: P(00) + P(11) - P(01) - P(10) = 2|ρ₀₁|
    p00 = counts.get('00', 0) / sum(counts.values())
    p11 = counts.get('11', 0) / sum(counts.values())
    p01 = counts.get('01', 0) / sum(counts.values())
    p10 = counts.get('10', 0) / sum(counts.values())
    return abs(p00 + p11 - p01 - p10) / 2
```

### Σ.6.4 Φ Validation

1. Verify Φ ∈ [0, 1] for all measurements
2. Confirm Φ is monotonically non-increasing (within noise)
3. Check that Φ(0) = 1.0 ± 0.01
4. Validate independence from fidelity measurements

---

## Σ.7 Temporal-Phase Sampling

### Σ.7.1 θ Definition

**Definition:**
```
θ(t) = 2πt / τ₀
```

Where τ₀ is the candidate timescale (φ⁸ μs ≈ 46.98 μs)

### Σ.7.2 Sampling Requirements

- Sample at ≥ 12 phase points per τ₀ period
- Cover at least 2 full periods
- Include θ = 0, π/4, π/2, 3π/4, π, 5π/4, 3π/2, 7π/4, 2π
- Additional points for non-linear validation

### Σ.7.3 Time Points

```python
import numpy as np

phi = (1 + np.sqrt(5)) / 2
tau0 = phi**8  # ≈ 46.98 μs

# Generate sampling times
num_periods = 2
points_per_period = 12
total_points = num_periods * points_per_period

t_values = np.linspace(0, num_periods * tau0, total_points)
theta_values = 2 * np.pi * t_values / tau0

# Ensure we have the critical points
critical_thetas = [0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 
                   5*np.pi/4, 3*np.pi/2, 7*np.pi/4, 2*np.pi]
critical_times = [t * tau0 / (2 * np.pi) for t in critical_thetas]

# Combine and sort
all_t_values = np.unique(np.concatenate([t_values, critical_times]))
all_theta_values = 2 * np.pi * all_t_values / tau0
```

---

## Σ.8 Data Acquisition Protocol

### Σ.8.1 Raw-Shot Acquisition

**Mandatory Requirements:**
- Record ALL raw shots per Appendix R
- No filtering or compression permitted
- No post-selection or error mitigation during acquisition
- Store raw counts as JSON/JSONL

**Per-Circuit Acquisition:**
```python
from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend
import json
from datetime import datetime

def acquire_raw_shots(circuit, backend, shots=10000):
    """
    Acquire raw shots for a single circuit
    
    Args:
        circuit: QuantumCircuit
        backend: QPU backend
        shots: Number of shots (minimum 10,000)
    
    Returns:
        trial_data: Dictionary with complete trial record
    """
    # Transpile to backend
    transpiled = transpile(circuit, backend=backend, 
                          optimization_level=3)
    
    # Execute
    job = backend.run(transpiled, shots=shots)
    result = job.result()
    counts = result.get_counts()
    
    # Build trial record
    trial_data = {
        'trial_id': f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        'circuit_id': circuit.name if hasattr(circuit, 'name') else 'unnamed',
        'backend': backend.name(),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        't': 0.0,  # Will be set by caller
        'T1': None,  # From calibration
        'T2': None,  # From calibration
        'Phi': None,  # From independent Φ measurement
        'theta': None,  # From t and tau0
        'N_q': circuit.num_qubits,
        'D': transpiled.depth(),
        'N_g': transpiled.count_ops().get('cx', 0) + transpiled.count_ops().get('cy', 0) + transpiled.count_ops().get('cz', 0),
        'epsilon_g': None,  # From calibration
        'epsilon_r': None,  # From calibration
        'raw_shots': counts,
        'transpiled_circuit': transpiled.qasm(),
        'circuit_duration': transpiled.duration,
        'calibration_hash': get_current_calibration_hash(backend)
    }
    
    return trial_data
```

### Σ.8.2 Calibration Data

1. Acquire calibration data BEFORE each experimental session
2. Store separately from trial data
3. Include:
   - T₁ measurements for all qubits
   - T₂ measurements for all qubits
   - Gate error rates (1Q and 2Q)
   - Readout error rates
   - Crosstalk matrix
   - Timestamp of calibration

### Σ.8.3 Data Organization

```
replication_data/
├── lab_<LAB_ID>/
│   ├── metadata.json
│   ├── calibration/
│   │   ├── calibration_<TIMESTAMP>.json
│   │   └── calibration_hashes.sha256
│   ├── phi_measurements/
│   │   ├── phi_data.json
│   │   └── phi_validation.json
│   ├── raw_shots/
│   │   ├── circuit_<CIRCUIT_ID>/
│   │   │   ├── trial_<TRIAL_ID>.json
│   │   │   └── ...
│   │   └── raw_shots_index.json
│   └── analysis/
│       ├── fidelity_results.json
│       ├── phi_threshold_results.json
│       └── statistical_tests.json
└── README_LAB.md
```

---

## Σ.9 Statistical Analysis Workflow

### Σ.9.1 Load and Validate Data

```python
import json
import hashlib
from pathlib import Path

def load_and_validate(lab_dir):
    """Load and validate all replication data"""
    # Load metadata
    with open(Path(lab_dir) / 'metadata.json') as f:
        metadata = json.load(f)
    
    # Validate against Appendix R
    validate_raw_shots(Path(lab_dir) / 'raw_shots')
    
    # Load calibration
    calibration = load_calibration(Path(lab_dir) / 'calibration')
    
    # Load Φ measurements
    phi_data = load_phi_measurements(Path(lab_dir) / 'phi_measurements')
    
    return metadata, calibration, phi_data
```

### Σ.9.2 Recompute Φ and θ

```python
def recompute_phi_and_theta(trial_data, phi_measurements):
    """
    Recompute Φ and θ for each trial independently
    """
    for trial in trial_data:
        t = trial['t']
        
        # Find closest Φ measurement
        phi_t = interpolate_phi(phi_measurements, t)
        trial['Phi'] = phi_t
        
        # Compute θ
        tau0 = (1 + 5**0.5) / 2 ** 8  # φ⁸
        theta = 2 * np.pi * t / tau0
        trial['theta'] = theta
    
    return trial_data
```

### Σ.9.3 Fit Models 1-4

Follow Appendix Δ exactly:

**Model 1: τ-Phase Modulation**
```python
from scipy.optimize import curve_fit

def fit_tau_phase_model(t_values, f_values):
    """Fit Model 1: F = β₀ + β₁ cos(2πt/τ₀ + δ) + ε"""
    def model(t, beta0, beta1, delta):
        return beta0 + beta1 * np.cos(2 * np.pi * t / tau0 + delta)
    
    params, cov = curve_fit(model, t_values, f_values)
    return params, cov
```

**Model 2: Φ-Threshold Contrast**
```python
from scipy.stats import ttest_ind, mannwhitneyu

def fit_phi_threshold_model(trial_data, phi_c=0.77):
    """Fit Model 2: F = β₀ + β₁ I(Φ ≥ Φ_c) + ε"""
    group1 = [t['F'] for t in trial_data if t['Phi'] < phi_c]
    group2 = [t['F'] for t in trial_data if t['Phi'] >= phi_c]
    
    # t-test
    t_stat, p_value = ttest_ind(group1, group2)
    
    # Mann-Whitney U
    u_stat, p_value_u = mannwhitneyu(group1, group2)
    
    return {'t_test': {'t': t_stat, 'p': p_value},
            'mann_whitney': {'u': u_stat, 'p': p_value_u}}
```

**Model 3: Continuous Φ Response**
```python
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

def fit_continuous_phi_model(trial_data):
    """Fit Model 3: F = β₀ + β₁ Φ + β₂ Φ² + ε"""
    X = [[t['Phi']] for t in trial_data]
    y = [t['F'] for t in trial_data]
    
    # Linear
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_poly, y)
    
    return model.coef_, model.intercept_
```

**Model 4: φ-Network Validation**
```python
import numpy as np

def validate_phi_network(trial_data, observed_constants):
    """Validate φ-network predictions"""
    phi = (1 + np.sqrt(5)) / 2
    
    predictions = {
        'tau0': phi**8,
        'F_max': 1 - phi**(-8),
        'Cohen_d': phi,  # or 1/phi
        'Bayes_factor': phi**7,
        'enhancement': phi**8 + phi**2
    }
    
    results = {}
    for key, pred in predictions.items():
        obs = observed_constants[key]
        rel_error = abs(obs - pred) / pred
        within_tolerance = rel_error <= 0.05  # 5% tolerance
        results[key] = {
            'predicted': pred,
            'observed': obs,
            'relative_error': rel_error,
            'within_tolerance': within_tolerance
        }
    
    return results
```

### Σ.9.4 Compute Effect Sizes and Confidence Intervals

```python
import numpy as np
from scipy.stats import sem
import bootstrap

def compute_effect_sizes(trial_data, model_results):
    """Compute effect sizes with 95% confidence intervals"""
    
    # τ-Phase ANOVA η²
    ss_effect = model_results['model1']['ss_effect']
    ss_total = model_results['model1']['ss_total']
    eta_squared = ss_effect / ss_total
    
    # Φ-Threshold Cohen's d
    group1 = [t['F'] for t in trial_data if t['Phi'] < 0.77]
    group2 = [t['F'] for t in trial_data if t['Phi'] >= 0.77]
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1 + n2 - 2))
    cohen_d = (np.mean(group1) - np.mean(group2)) / pooled_std
    
    # Bootstrap CIs (10,000 resamples)
    eta_squared_ci = bootstrap.ci(eta_squared, n_boot=10000)
    cohen_d_ci = bootstrap.ci(cohen_d, n_boot=10000)
    
    return {
        'eta_squared': {'value': eta_squared, 'ci': eta_squared_ci},
        'cohen_d': {'value': cohen_d, 'ci': cohen_d_ci}
    }
```

### Σ.9.5 Model Comparison

```python
import numpy as np
from scipy.stats import norm

def compute_model_comparison(model1_results, model2_results, 
                              conventional_model_results):
    """Compute Bayes Factor and AIC"""
    
    # AIC: Akaike Information Criterion
    # AIC = 2k - 2ln(L) where k = number of parameters
    
    n = len(model1_results['f_values'])
    
    # Model 1 (τ-phase): 3 parameters (β₀, β₁, δ)
    k1 = 3
    rss1 = model1_results['rss']
    aic1 = 2 * k1 + n * np.log(rss1 / n)
    
    # Model 2 (Φ-threshold): 2 parameters (β₀, β₁)
    k2 = 2
    rss2 = model2_results['rss']
    aic2 = 2 * k2 + n * np.log(rss2 / n)
    
    # Conventional model: 2 parameters (exponential decay)
    k_conv = 2
    rss_conv = conventional_model_results['rss']
    aic_conv = 2 * k_conv + n * np.log(rss_conv / n)
    
    # ΔAIC
    delta_aic_tau_phi_vs_conv = aic_conv - aic1
    delta_aic_phi_vs_conv = aic_conv - aic2
    
    # Bayes Factor (approximate)
    # BF₁₀ ≈ exp(0.5 * ΔAIC)
    bf10_tau_phi = np.exp(0.5 * delta_aic_tau_phi_vs_conv)
    bf10_phi = np.exp(0.5 * delta_aic_phi_vs_conv)
    
    return {
        'aic': {'model1': aic1, 'model2': aic2, 'conventional': aic_conv},
        'delta_aic': {
            'tau_phi_vs_conventional': delta_aic_tau_phi_vs_conv,
            'phi_vs_conventional': delta_aic_phi_vs_conv
        },
        'bayes_factor': {
            'bf10_tau_phi': bf10_tau_phi,
            'bf10_phi': bf10_phi
        }
    }
```

---

## Σ.10 Reporting Requirements

### Σ.10.1 Required Files

Each replication lab must submit the following files:

1. **Replication_Report.md** — Narrative summary
   - Executive summary
   - Methods (following this protocol)
   - Results
   - Discussion
   - Deviations from protocol (if any)
   - Conclusion

2. **Replication_Data.json** — Structured results
   ```json
   {
     "lab_id": "<LAB_ID>",
     "timestamp": "<ISO8601>",
     "backend": "<BACKEND_NAME>",
     "results": {
       "model1": {...},
       "model2": {...},
       "model3": {...},
       "model4": {...},
       "effect_sizes": {...},
       "model_comparison": {...}
     },
     "phi_network_validation": {...},
     "confirmation_criteria": {...}
   }
   ```

3. **Raw-Shot_Archive.zip** — Unprocessed measurement data
   - All trial JSON files
   - Calibration data
   - Metadata
   - SHA-256 checksums

4. **Calibration_Data.json** — Coherence parameters
   - T₁, T₂ for all qubits
   - Gate fidelities
   - Readout errors
   - Crosstalk data

5. **Statistical_Analysis_Report.pdf** — Test outcomes
   - All statistical tables
   - Residual plots
   - Phase-dependence graphs
   - Confidence intervals
   - p-values

6. **Replication_Certificate.txt** — SHA-256 hashes and signatures
   ```
   SHA-256 (Replication_Report.md): <HASH>
   SHA-256 (Replication_Data.json): <HASH>
   SHA-256 (Raw-Shot_Archive.zip): <HASH>
   SHA-256 (Calibration_Data.json): <HASH>
   SHA-256 (Statistical_Analysis_Report.pdf): <HASH>
   
   Signed by: <AUTHORIZED_SIGNATORY>
   Date: <ISO8601>
   Lab: <LAB_ID>
   ```

### Σ.10.2 Reporting Format

**Summary Table of All Test Statistics:**

| Test | Statistic | p-value | 95% CI | Effect Size |
|------|-----------|---------|-------|-------------|
| τ-Phase ANOVA | F(1, N-2) | <0.05 | [lower, upper] | η² |
| Φ-Threshold t-test | t(df) | <0.05 | [lower, upper] | Cohen's d |
| φ-Network τ₀ | z | <0.01 | [lower, upper] | Rel. Error |
| φ-Network F_max | z | <0.01 | [lower, upper] | Rel. Error |
| ... | ... | ... | ... | ... |

**Confidence Intervals and p-values:**
- Report all CIs with their computation method (parametric, bootstrap, Bayesian)
- Report exact p-values (not just <0.05)
- Include degrees of freedom where applicable

**Effect-Size Estimates:**
- η² for ANOVA
- Cohen's d for t-tests
- Odds ratios for logistic fits
- Relative errors for φ-network comparisons

**Model-Comparison Metrics:**
- Bayes Factors (BF₁₀)
- AIC values and ΔAIC
- Model weights (if applicable)

**Residual Plots and Phase-Dependence Graphs:**
- Residuals vs. fitted values
- Residuals vs. θ
- Residuals vs. Φ
- Periodogram of residuals

**Raw-Shot Provenance Hashes:**
- SHA-256 of each trial file
- SHA-256 of complete archive
- Merkle tree root hash (optional)

**Independent-Lab Declaration:**
- Signed statement of independence
- No prior access to confirmatory data
- No modification of pre-registered parameters
- Full adherence to protocol

---

## Σ.11 Evaluation Criteria

### Σ.11.1 Confirmation Criteria

Replication is considered **CONFIRMED** if ALL of the following are met:

1. **τ₀ Reproduction:**
   - Observed τ₀ within ±3% of φ⁸ μs (≈46.98 μs)
   - p < 0.05 for τ-phase modulation test
   - η² ≥ 0.01 (small effect size)

2. **F_max Bound:**
   - Observed F_max within ±0.5% of 1 - φ⁻⁸ (≈0.9787)
   - No violations of pre-registered F_max threshold

3. **Φ-Threshold Transition:**
   - Transition reappears near Φ ≈ 0.77
   - p < 0.05 for Φ-threshold contrast test
   - Cohen's d within ±3% of φ (≈1.618)

4. **Residual Periodicity:**
   - Residuals exhibit clear periodic structure
   - Period matches τ₀ within ±5%
   - Fourier analysis shows significant peak at 2π/τ₀

5. **φ-Network Relationships:**
   - All φ-structured predictions within tolerance:
     - τ₀: ±3%
     - F_max: ±0.5%
     - Cohen's d: ±3%
     - Bayes Factor: ±5%
     - Enhancement: ±5%

6. **Conventional Model Failure:**
   - Conventional decoherence model fails to explain residual variance
   - ΔAIC > 10 in favor of τ–Φ model
   - BF₁₀ > 10 for τ–Φ model

### Σ.11.2 Falsification Criteria

Replication is considered **FALSIFIED** if ANY of the following are met:

1. p > 0.05 for τ-phase modulation test
2. p > 0.05 for Φ-threshold contrast test
3. Effect sizes below pre-registered thresholds
4. φ-network constants deviate >5% from predictions
5. No periodic residual structure observed
6. Conventional model outperforms τ–Φ model (ΔAIC < 0)

### Σ.11.3 Inconclusive Criteria

Replication is considered **INCONCLUSIVE** if:

- Some but not all confirmation criteria are met
- Data quality issues prevent clear interpretation
- Equipment limitations prevent proper execution
- Protocol deviations are significant but not fatal

---

## Σ.12 Independent-Lab Declaration

Each participating laboratory must sign the following declaration:

```
================================================================================
INDEPENDENT LABORATORY DECLARATION
OSIRIS τ–Φ Dynamical Theory Replication
================================================================================

Laboratory Name: _______________________________________________
Laboratory ID: __________________________________________________
Authorized Signatory: _____________________________________________
Position: _______________________________________________________
Date: ___________________________________________________________

DECLARATION:

1. We have had NO prior access to OSIRIS confirmatory τ–Φ data or results.

2. We have NOT modified any pre-registered parameters from the OSIRIS τ–Φ
   Confirmatory Preregistration Packet.

3. We have followed ALL procedures specified in Appendices Ω, Δ, Φ, R, Θ, Ψ
   exactly as written.

4. All data acquisition and analysis has been conducted independently by
   our laboratory personnel.

5. All raw-shot data has been archived without filtering, compression,
   or post-selection.

6. All statistical analyses have been conducted using the exact procedures
   specified in Appendix Δ.

7. We certify that our backend meets or exceeds the minimum specifications
   defined in Section Σ.3.1.

8. We agree to publish our results regardless of outcome.

9. We authorize the inclusion of our results in the OSIRIS τ–Φ replication
   meta-analysis.

Signature: _____________________________________________________
Printed Name: ____________________________________________________
Date: ___________________________________________________________

Cryptographic Verification:
SHA-256 of this declaration: _______________________________________
```

---

## Σ.13 Final Replication Statement

This protocol defines the complete procedure for independent replication of the OSIRIS τ–Φ dynamical theory. The protocol is:

- **Pre-registered:** All procedures are frozen before confirmatory execution
- **Comprehensive:** Covers all aspects from hardware to analysis
- **Rigorous:** Statistical standards meet or exceed field norms
- **Transparent:** All data and code must be publicly available
- **Reproducible:** Designed for exact replication across laboratories

**Successful replication** will establish the τ–Φ phenomenon as a reproducible dynamical law of quantum coherence, providing strong evidence for the OSIRIS theoretical framework.

**Failure to replicate** will constrain future theoretical development, indicating that either:
- The τ–Φ effect is specific to IBM Heron hardware
- The φ-network predictions require refinement
- The statistical models need adjustment
- The experimental protocol has hidden confounds

In either case, the zero-trust, cryptographically anchored nature of this protocol ensures that the outcome is scientifically valid and free from post-hoc bias.

---

## Σ.14 Frozen Protocol Statement

This Independent-Lab Replication Protocol is hereby **pre-registered and frozen**.

No modifications may be made to this protocol after data acquisition begins at any replication site. Any deviations from this protocol must be documented in the Replication Report and will be considered in the evaluation of the replication attempt.

All confirmatory and replication analyses must adhere strictly to this protocol.

---

*Appendix Σ is part of the OSIRIS τ–Φ Confirmatory Preregistration Packet. For the complete packet, see Appendix Ω.*
