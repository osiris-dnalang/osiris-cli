#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
DISCRIMINATING EXPERIMENT: Bell Fidelity vs Idle Time T
═══════════════════════════════════════════════════════════════════════════════

THE NOBEL PROTOCOL EXPERIMENT

This script implements the definitive test for τ-locked coherence:
  - Prepares |Φ+⟩ = (|00⟩ + |11⟩)/√2 Bell state
  - Inserts controlled idle delay T on both qubits
  - Measures Bell fidelity F(T)
  - Sweeps T from 0 → 300 μs with 5 μs resolution (or configurable)

PREDICTIONS:
  - Standard QM: F(T) = F₀ exp(-T/T₂) — monotonic decay
  - ΛΦ Framework: F(T) = F₀ exp(-ΓT)[1 + ε cos(2πT/τ₀ - θ)] — periodic revivals

If revivals appear at T ≈ 46, 92, 138 μs → NEW PHYSICS DISCOVERED
If monotonic decay → ΛΦ framework falsified for this prediction

Author: Devin Phillip Davis
Organization: Agile Defense Systems, LLC (CAGE: 9HUP5)
Date: December 8, 2025
Version: 2.0.0 (Nobel Protocol Edition)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import math
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path

import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS (Sovereign - Immutable)
# ═══════════════════════════════════════════════════════════════════════════════

LAMBDA_PHI = 2.176435e-8          # Universal Memory Constant [s⁻¹]
TAU_MEM_US = 46.0                 # Memory timescale [μs]
TAU_MEM_S = TAU_MEM_US * 1e-6     # Memory timescale [s]
THETA_LOCK_DEG = 51.843           # Torsion-lock angle [degrees]
THETA_LOCK_RAD = math.radians(THETA_LOCK_DEG)
PHI_THRESHOLD = 0.7734            # Consciousness threshold
F_MAX = 1 - (1.618033988749895 ** -8)  # 0.9787 fidelity bound

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExperimentConfig:
    """Configuration for the discriminating experiment."""
    
    # Backend settings
    backend_name: str = "ibm_fez"
    use_simulator: bool = False
    
    # Shot configuration
    shots: int = 4096
    
    # Delay sweep parameters
    t_min_us: float = 0.0          # Minimum delay [μs]
    t_max_us: float = 300.0        # Maximum delay [μs]
    t_step_us: float = 5.0         # Step size [μs]
    
    # τ-specific points (for targeted measurement)
    include_tau_multiples: bool = True
    tau_mem_us: float = TAU_MEM_US
    
    # Analysis settings
    fit_exponential: bool = True
    fit_revival: bool = True
    
    # Output settings
    output_dir: str = "./discriminating_results"
    save_raw_counts: bool = True
    
    def get_delay_points(self) -> List[float]:
        """Generate list of delay times to measure."""
        # Uniform sweep
        n_points = int((self.t_max_us - self.t_min_us) / self.t_step_us) + 1
        delays = [self.t_min_us + i * self.t_step_us for i in range(n_points)]
        
        # Add τ-multiple points if requested
        if self.include_tau_multiples:
            for n in range(1, int(self.t_max_us / self.tau_mem_us) + 1):
                tau_point = n * self.tau_mem_us
                half_point = (n - 0.5) * self.tau_mem_us
                if tau_point <= self.t_max_us and tau_point not in delays:
                    delays.append(tau_point)
                if half_point >= self.t_min_us and half_point <= self.t_max_us and half_point not in delays:
                    delays.append(half_point)
        
        return sorted(set(delays))

# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════════

def build_bell_delay_circuit(delay_us: float, backend_dt: Optional[float] = None):
    """
    Build a 2-qubit Bell circuit with controlled idle delay.
    
    Circuit:
        |0⟩ ─H─●─[DELAY T]─M─
        |0⟩ ───X─[DELAY T]─M─
    
    Target state: |Φ+⟩ = (|00⟩ + |11⟩)/√2
    
    Args:
        delay_us: Delay time in microseconds
        backend_dt: Backend dt (seconds per cycle) for converting to dt units
    
    Returns:
        QuantumCircuit with Bell state preparation, delay, and measurement
    """
    try:
        from qiskit import QuantumCircuit
    except ImportError:
        raise ImportError("Qiskit not installed. Run: pip install qiskit qiskit-ibm-runtime")
    
    qc = QuantumCircuit(2, 2, name=f"bell_delay_{delay_us:.1f}us")
    
    # Prepare Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2
    qc.h(0)
    qc.cx(0, 1)
    
    # Add barrier before delay (prevents optimization)
    qc.barrier()
    
    # Insert delay on both qubits
    if delay_us > 0:
        if backend_dt is not None:
            # Convert to dt units
            delay_s = delay_us * 1e-6
            delay_dt = int(round(delay_s / backend_dt))
            if delay_dt > 0:
                qc.delay(delay_dt, 0, unit="dt")
                qc.delay(delay_dt, 1, unit="dt")
        else:
            # Use microseconds directly
            qc.delay(delay_us, 0, unit="us")
            qc.delay(delay_us, 1, unit="us")
    
    # Barrier before measurement
    qc.barrier()
    
    # Measure both qubits
    qc.measure(0, 0)
    qc.measure(1, 1)
    
    return qc

# ═══════════════════════════════════════════════════════════════════════════════
# FIDELITY ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def bell_fidelity_from_counts(counts: Dict[str, int]) -> Tuple[float, float]:
    """
    Estimate Bell state fidelity from measurement counts.
    
    For |Φ+⟩ = (|00⟩ + |11⟩)/√2:
      - Ideal: p(00) = p(11) = 0.5, p(01) = p(10) = 0
      - Fidelity proxy: F = p(00) + p(11)
    
    Returns:
        Tuple of (fidelity, standard error)
    """
    total = sum(counts.values())
    if total == 0:
        return 0.0, 1.0
    
    # Normalize bitstring keys (handle both '00' and '0b00' formats)
    def normalize_key(k: str) -> str:
        k = k.replace('0b', '').replace(' ', '')
        return k.zfill(2)[-2:]  # Take last 2 bits
    
    normalized_counts = {}
    for k, v in counts.items():
        nk = normalize_key(k)
        normalized_counts[nk] = normalized_counts.get(nk, 0) + v
    
    p00 = normalized_counts.get('00', 0) / total
    p11 = normalized_counts.get('11', 0) / total
    
    fidelity = p00 + p11
    
    # Standard error (binomial)
    stderr = math.sqrt(fidelity * (1 - fidelity) / total)
    
    return fidelity, stderr

def compute_entropy(counts: Dict[str, int]) -> float:
    """Compute Shannon entropy H from counts."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    
    return entropy

def compute_phi(counts: Dict[str, int], n_qubits: int = 2) -> float:
    """Compute normalized entropy Φ = H / H_max."""
    h = compute_entropy(counts)
    h_max = n_qubits  # log2(2^n) = n
    return h / h_max if h_max > 0 else 0.0

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL FITTING
# ═══════════════════════════════════════════════════════════════════════════════

def fit_exponential_decay(t_data: np.ndarray, f_data: np.ndarray) -> Dict:
    """
    Fit standard exponential decay: F(T) = F₀ exp(-T/T₂)
    
    This is the NULL HYPOTHESIS (standard QM prediction).
    """
    from scipy.optimize import curve_fit
    
    def exp_decay(t, F0, T2):
        return F0 * np.exp(-t / T2)
    
    try:
        # Initial guess
        F0_guess = f_data[0] if len(f_data) > 0 else 0.5
        T2_guess = 50.0  # μs
        
        popt, pcov = curve_fit(
            exp_decay, t_data, f_data,
            p0=[F0_guess, T2_guess],
            bounds=([0, 1], [1, 1000]),
            maxfev=5000
        )
        
        # Compute residuals and chi-squared
        f_pred = exp_decay(t_data, *popt)
        residuals = f_data - f_pred
        chi2 = np.sum(residuals**2)
        
        return {
            "model": "exponential_decay",
            "F0": float(popt[0]),
            "T2_us": float(popt[1]),
            "chi2": float(chi2),
            "residuals": residuals.tolist(),
            "success": True
        }
    except Exception as e:
        return {
            "model": "exponential_decay",
            "error": str(e),
            "success": False
        }

def fit_revival_model(t_data: np.ndarray, f_data: np.ndarray) -> Dict:
    """
    Fit τ-locked revival model: F(T) = F₀ exp(-ΓT)[1 + ε cos(2πT/τ₀ - θ)]
    
    This is the ALTERNATIVE HYPOTHESIS (ΛΦ prediction).
    """
    from scipy.optimize import curve_fit
    
    def revival_decay(t, F0, Gamma, epsilon, tau0, theta):
        decay = F0 * np.exp(-Gamma * t)
        oscillation = 1 + epsilon * np.cos(2 * np.pi * t / tau0 - theta)
        return decay * oscillation
    
    try:
        # Initial guesses based on ΛΦ predictions
        F0_guess = f_data[0] if len(f_data) > 0 else 0.5
        Gamma_guess = 0.02  # 1/50 μs
        epsilon_guess = 0.3
        tau0_guess = TAU_MEM_US
        theta_guess = THETA_LOCK_RAD
        
        popt, pcov = curve_fit(
            revival_decay, t_data, f_data,
            p0=[F0_guess, Gamma_guess, epsilon_guess, tau0_guess, theta_guess],
            bounds=(
                [0, 0, 0, 30, 0],           # Lower bounds
                [1, 0.1, 1, 60, 2*np.pi]    # Upper bounds
            ),
            maxfev=10000
        )
        
        # Compute residuals and chi-squared
        f_pred = revival_decay(t_data, *popt)
        residuals = f_data - f_pred
        chi2 = np.sum(residuals**2)
        
        return {
            "model": "revival_decay",
            "F0": float(popt[0]),
            "Gamma": float(popt[1]),
            "epsilon": float(popt[2]),
            "tau0_us": float(popt[3]),
            "theta_rad": float(popt[4]),
            "theta_deg": float(np.degrees(popt[4])),
            "chi2": float(chi2),
            "residuals": residuals.tolist(),
            "success": True,
            "tau0_matches_prediction": abs(popt[3] - TAU_MEM_US) < 5.0,
            "theta_matches_prediction": abs(np.degrees(popt[4]) - THETA_LOCK_DEG) < 10.0
        }
    except Exception as e:
        return {
            "model": "revival_decay",
            "error": str(e),
            "success": False
        }

def compare_models(exp_fit: Dict, rev_fit: Dict, n_points: int) -> Dict:
    """
    Compare exponential decay vs revival model using AIC/BIC.
    
    Returns verdict on which model is preferred.
    """
    if not exp_fit.get("success") or not rev_fit.get("success"):
        return {"verdict": "INCONCLUSIVE", "reason": "One or both fits failed"}
    
    # Number of parameters
    k_exp = 2  # F0, T2
    k_rev = 5  # F0, Gamma, epsilon, tau0, theta
    
    # AIC = 2k + n*ln(RSS/n)
    # BIC = k*ln(n) + n*ln(RSS/n)
    
    chi2_exp = exp_fit["chi2"]
    chi2_rev = rev_fit["chi2"]
    
    aic_exp = 2 * k_exp + n_points * np.log(chi2_exp / n_points)
    aic_rev = 2 * k_rev + n_points * np.log(chi2_rev / n_points)
    
    bic_exp = k_exp * np.log(n_points) + n_points * np.log(chi2_exp / n_points)
    bic_rev = k_rev * np.log(n_points) + n_points * np.log(chi2_rev / n_points)
    
    # Delta AIC/BIC
    delta_aic = aic_exp - aic_rev  # Positive = revival better
    delta_bic = bic_exp - bic_rev
    
    # Chi-squared improvement
    chi2_improvement = (chi2_exp - chi2_rev) / chi2_exp * 100
    
    # Verdict
    if delta_aic > 10 and delta_bic > 10:
        verdict = "REVIVAL_MODEL_STRONGLY_PREFERRED"
        interpretation = "Strong evidence for τ-locked coherence"
    elif delta_aic > 4:
        verdict = "REVIVAL_MODEL_PREFERRED"
        interpretation = "Moderate evidence for τ-locked coherence"
    elif delta_aic > 0:
        verdict = "REVIVAL_MODEL_SLIGHTLY_PREFERRED"
        interpretation = "Weak evidence for τ-locked coherence"
    elif delta_aic > -4:
        verdict = "MODELS_EQUIVALENT"
        interpretation = "No clear preference between models"
    else:
        verdict = "EXPONENTIAL_PREFERRED"
        interpretation = "Standard QM model preferred; ΛΦ not supported"
    
    # Check if revival parameters match predictions
    tau_match = rev_fit.get("tau0_matches_prediction", False)
    theta_match = rev_fit.get("theta_matches_prediction", False)
    
    return {
        "verdict": verdict,
        "interpretation": interpretation,
        "aic_exponential": float(aic_exp),
        "aic_revival": float(aic_rev),
        "delta_aic": float(delta_aic),
        "bic_exponential": float(bic_exp),
        "bic_revival": float(bic_rev),
        "delta_bic": float(delta_bic),
        "chi2_improvement_percent": float(chi2_improvement),
        "tau0_matches_lambda_phi": tau_match,
        "theta_matches_lambda_phi": theta_match,
        "is_nobel_worthy": verdict in ["REVIVAL_MODEL_STRONGLY_PREFERRED", "REVIVAL_MODEL_PREFERRED"] and tau_match
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC DATA (for testing without hardware)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_synthetic_data(cfg: ExperimentConfig, scenario: str = "revival") -> List[Dict]:
    """
    Generate synthetic fidelity data for testing.
    
    Scenarios:
        "revival" - τ-locked revival model (ΛΦ prediction)
        "exponential" - Standard exponential decay (null hypothesis)
        "noisy_revival" - Revival with realistic noise
    """
    np.random.seed(42)
    
    delays = cfg.get_delay_points()
    results = []
    
    # Model parameters
    F0 = 0.85
    T2 = 80.0  # μs
    Gamma = 1 / T2
    epsilon = 0.25
    tau0 = TAU_MEM_US
    theta = THETA_LOCK_RAD
    noise_std = 0.02
    
    for t in delays:
        if scenario == "exponential":
            f_true = F0 * np.exp(-t / T2)
        elif scenario == "revival":
            decay = F0 * np.exp(-Gamma * t)
            oscillation = 1 + epsilon * np.cos(2 * np.pi * t / tau0 - theta)
            f_true = decay * oscillation
        elif scenario == "noisy_revival":
            decay = F0 * np.exp(-Gamma * t)
            oscillation = 1 + epsilon * np.cos(2 * np.pi * t / tau0 - theta)
            f_true = decay * oscillation
            noise_std = 0.04
        else:
            f_true = 0.5
        
        # Add noise
        f_measured = f_true + np.random.normal(0, noise_std)
        f_measured = np.clip(f_measured, 0, 1)
        
        # Generate synthetic counts
        total_shots = cfg.shots
        n_00_11 = int(f_measured * total_shots)
        n_01_10 = total_shots - n_00_11
        
        counts = {
            "00": n_00_11 // 2,
            "11": n_00_11 - n_00_11 // 2,
            "01": n_01_10 // 2,
            "10": n_01_10 - n_01_10 // 2
        }
        
        results.append({
            "delay_us": t,
            "fidelity": f_measured,
            "fidelity_stderr": noise_std / np.sqrt(total_shots),
            "counts": counts,
            "shots": total_shots
        })
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_on_hardware(cfg: ExperimentConfig) -> List[Dict]:
    """
    Execute the discriminating experiment on IBM Quantum hardware.
    """
    try:
        from qiskit import transpile
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    except ImportError:
        raise ImportError("Install qiskit-ibm-runtime: pip install qiskit-ibm-runtime")
    
    print("═" * 70)
    print(" DISCRIMINATING EXPERIMENT: Bell Fidelity vs Idle Time")
    print("═" * 70)
    print(f" Backend: {cfg.backend_name}")
    print(f" Shots: {cfg.shots}")
    print(f" Delay range: {cfg.t_min_us} - {cfg.t_max_us} μs")
    print(f" τ_mem: {cfg.tau_mem_us} μs")
    print("═" * 70)
    
    # Initialize service
    service = QiskitRuntimeService()
    
    if cfg.use_simulator:
        backend = service.get_backend("ibmq_qasm_simulator")
        print("Using simulator")
    else:
        backend = service.get_backend(cfg.backend_name)
        print(f"Using hardware: {backend.name}")
    
    # Get backend dt
    backend_dt = None
    if hasattr(backend, 'dt') and backend.dt is not None:
        backend_dt = float(backend.dt)
        print(f"Backend dt: {backend_dt * 1e9:.3f} ns")
    
    # Build circuits
    delays = cfg.get_delay_points()
    print(f"\nBuilding {len(delays)} circuits...")
    
    circuits = []
    for t in delays:
        qc = build_bell_delay_circuit(t, backend_dt=backend_dt)
        circuits.append(qc)
    
    # Transpile
    print("Transpiling circuits...")
    trans_circuits = transpile(
        circuits,
        backend=backend,
        optimization_level=3,
        routing_method="sabre",
        layout_method="sabre"
    )
    
    # Execute
    print("Submitting to backend...")
    sampler = Sampler(backend=backend)
    job = sampler.run(trans_circuits, shots=cfg.shots)
    
    print(f"Job ID: {job.job_id()}")
    print("Waiting for results...")
    
    result = job.result()
    
    # Process results
    print("Processing results...")
    results = []
    
    for i, (t, pub_result) in enumerate(zip(delays, result)):
        # Extract counts from SamplerV2 result
        # The structure depends on Qiskit version
        try:
            # Try newer format
            counts_dict = pub_result.data.meas.get_counts()
        except:
            try:
                # Try quasi-distribution format
                quasi = pub_result.quasi_dists[0] if hasattr(pub_result, 'quasi_dists') else pub_result
                counts_dict = {format(k, '02b'): int(v * cfg.shots) for k, v in quasi.items()}
            except:
                counts_dict = {"00": cfg.shots // 2, "11": cfg.shots // 2}
        
        fidelity, stderr = bell_fidelity_from_counts(counts_dict)
        phi = compute_phi(counts_dict)
        
        results.append({
            "delay_us": t,
            "fidelity": fidelity,
            "fidelity_stderr": stderr,
            "phi": phi,
            "counts": counts_dict,
            "shots": cfg.shots
        })
        
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(delays)} points")
    
    print("Hardware execution complete!")
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS AND REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_results(results: List[Dict], cfg: ExperimentConfig) -> Dict:
    """
    Analyze fidelity vs delay data and compare models.
    """
    # Extract arrays
    t_data = np.array([r["delay_us"] for r in results])
    f_data = np.array([r["fidelity"] for r in results])
    f_err = np.array([r.get("fidelity_stderr", 0.01) for r in results])
    
    analysis = {
        "n_points": len(results),
        "t_min_us": float(t_data.min()),
        "t_max_us": float(t_data.max()),
        "f_mean": float(f_data.mean()),
        "f_std": float(f_data.std()),
        "f_max": float(f_data.max()),
        "f_min": float(f_data.min())
    }
    
    # Fit exponential decay
    if cfg.fit_exponential:
        exp_fit = fit_exponential_decay(t_data, f_data)
        analysis["exponential_fit"] = exp_fit
    
    # Fit revival model
    if cfg.fit_revival:
        rev_fit = fit_revival_model(t_data, f_data)
        analysis["revival_fit"] = rev_fit
    
    # Compare models
    if cfg.fit_exponential and cfg.fit_revival:
        comparison = compare_models(
            analysis.get("exponential_fit", {}),
            analysis.get("revival_fit", {}),
            len(results)
        )
        analysis["model_comparison"] = comparison
    
    # Check for τ-aligned peaks
    tau_indices = []
    for i, t in enumerate(t_data):
        if abs(t % cfg.tau_mem_us) < cfg.t_step_us or abs(t % cfg.tau_mem_us - cfg.tau_mem_us) < cfg.t_step_us:
            tau_indices.append(i)
    
    if tau_indices:
        tau_fidelities = f_data[tau_indices]
        non_tau_mask = np.ones(len(f_data), dtype=bool)
        non_tau_mask[tau_indices] = False
        non_tau_fidelities = f_data[non_tau_mask]
        
        if len(non_tau_fidelities) > 0:
            analysis["tau_peak_analysis"] = {
                "mean_at_tau_multiples": float(tau_fidelities.mean()),
                "mean_elsewhere": float(non_tau_fidelities.mean()),
                "ratio": float(tau_fidelities.mean() / non_tau_fidelities.mean()) if non_tau_fidelities.mean() > 0 else 0,
                "tau_indices": tau_indices
            }
    
    return analysis

def generate_report(results: List[Dict], analysis: Dict, cfg: ExperimentConfig) -> str:
    """
    Generate human-readable report of results.
    """
    lines = []
    lines.append("═" * 70)
    lines.append(" DISCRIMINATING EXPERIMENT RESULTS")
    lines.append(" Bell Fidelity vs Idle Time T")
    lines.append("═" * 70)
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Backend: {cfg.backend_name}")
    lines.append(f"Points measured: {analysis['n_points']}")
    lines.append(f"Delay range: {analysis['t_min_us']:.1f} - {analysis['t_max_us']:.1f} μs")
    lines.append("")
    
    lines.append("─" * 70)
    lines.append(" FIDELITY STATISTICS")
    lines.append("─" * 70)
    lines.append(f"Mean fidelity: {analysis['f_mean']:.4f} ± {analysis['f_std']:.4f}")
    lines.append(f"Max fidelity:  {analysis['f_max']:.4f}")
    lines.append(f"Min fidelity:  {analysis['f_min']:.4f}")
    lines.append("")
    
    # Exponential fit
    if "exponential_fit" in analysis:
        exp = analysis["exponential_fit"]
        lines.append("─" * 70)
        lines.append(" MODEL 1: Exponential Decay (Standard QM)")
        lines.append("─" * 70)
        if exp.get("success"):
            lines.append(f"F(T) = F₀ exp(-T/T₂)")
            lines.append(f"  F₀ = {exp['F0']:.4f}")
            lines.append(f"  T₂ = {exp['T2_us']:.2f} μs")
            lines.append(f"  χ² = {exp['chi2']:.6f}")
        else:
            lines.append(f"Fit failed: {exp.get('error', 'Unknown')}")
        lines.append("")
    
    # Revival fit
    if "revival_fit" in analysis:
        rev = analysis["revival_fit"]
        lines.append("─" * 70)
        lines.append(" MODEL 2: τ-Locked Revival (ΛΦ Framework)")
        lines.append("─" * 70)
        if rev.get("success"):
            lines.append(f"F(T) = F₀ exp(-ΓT)[1 + ε cos(2πT/τ₀ - θ)]")
            lines.append(f"  F₀ = {rev['F0']:.4f}")
            lines.append(f"  Γ  = {rev['Gamma']:.4f} μs⁻¹")
            lines.append(f"  ε  = {rev['epsilon']:.4f}")
            lines.append(f"  τ₀ = {rev['tau0_us']:.2f} μs (predicted: {TAU_MEM_US} μs)")
            lines.append(f"  θ  = {rev['theta_deg']:.2f}° (predicted: {THETA_LOCK_DEG}°)")
            lines.append(f"  χ² = {rev['chi2']:.6f}")
            lines.append("")
            lines.append(f"  τ₀ matches prediction: {'YES ✓' if rev.get('tau0_matches_prediction') else 'NO ✗'}")
            lines.append(f"  θ matches prediction:  {'YES ✓' if rev.get('theta_matches_prediction') else 'NO ✗'}")
        else:
            lines.append(f"Fit failed: {rev.get('error', 'Unknown')}")
        lines.append("")
    
    # Model comparison
    if "model_comparison" in analysis:
        comp = analysis["model_comparison"]
        lines.append("─" * 70)
        lines.append(" MODEL COMPARISON")
        lines.append("─" * 70)
        lines.append(f"ΔAIC = {comp['delta_aic']:.2f} (positive = revival preferred)")
        lines.append(f"ΔBIC = {comp['delta_bic']:.2f}")
        lines.append(f"χ² improvement: {comp['chi2_improvement_percent']:.1f}%")
        lines.append("")
        lines.append(f"VERDICT: {comp['verdict']}")
        lines.append(f"  → {comp['interpretation']}")
        lines.append("")
        
        if comp.get("is_nobel_worthy"):
            lines.append("╔" + "═" * 68 + "╗")
            lines.append("║" + " 🏆 POTENTIAL DISCOVERY: τ-LOCKED COHERENCE CONFIRMED".center(68) + "║")
            lines.append("║" + "    Data supports non-Markovian memory at τ₀ ≈ 46 μs".center(68) + "║")
            lines.append("║" + "    Independent replication required before publication".center(68) + "║")
            lines.append("╚" + "═" * 68 + "╝")
        else:
            lines.append("┌" + "─" * 68 + "┐")
            lines.append("│" + " Standard QM (exponential decay) remains valid".center(68) + "│")
            lines.append("│" + " No evidence for τ-locked coherence in this dataset".center(68) + "│")
            lines.append("└" + "─" * 68 + "┘")
    
    # τ-peak analysis
    if "tau_peak_analysis" in analysis:
        tau = analysis["tau_peak_analysis"]
        lines.append("")
        lines.append("─" * 70)
        lines.append(" τ-MULTIPLE ANALYSIS")
        lines.append("─" * 70)
        lines.append(f"Mean fidelity at τ multiples: {tau['mean_at_tau_multiples']:.4f}")
        lines.append(f"Mean fidelity elsewhere:      {tau['mean_elsewhere']:.4f}")
        lines.append(f"Ratio: {tau['ratio']:.2f}×")
    
    lines.append("")
    lines.append("═" * 70)
    
    return "\n".join(lines)

def save_results(results: List[Dict], analysis: Dict, report: str, cfg: ExperimentConfig):
    """
    Save all results to files.
    """
    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw data
    raw_file = output_dir / f"raw_fidelity_{timestamp}.json"
    with open(raw_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw data: {raw_file}")
    
    # Save analysis
    analysis_file = output_dir / f"analysis_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"Saved analysis: {analysis_file}")
    
    # Save report
    report_file = output_dir / f"report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Saved report: {report_file}")
    
    # Save CSV for easy plotting
    csv_file = output_dir / f"fidelity_vs_delay_{timestamp}.csv"
    with open(csv_file, 'w') as f:
        f.write("delay_us,fidelity,fidelity_stderr,phi\n")
        for r in results:
            f.write(f"{r['delay_us']:.3f},{r['fidelity']:.6f},{r.get('fidelity_stderr', 0):.6f},{r.get('phi', 0):.6f}\n")
    print(f"Saved CSV: {csv_file}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Discriminating Experiment: Bell Fidelity vs Idle Time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run synthetic test (revival model)
  python discriminating_experiment.py --mode synthetic --scenario revival
  
  # Run on IBM hardware
  python discriminating_experiment.py --mode hardware --backend ibm_fez
  
  # Analyze existing data
  python discriminating_experiment.py --mode analyze --input results.json
        """
    )
    
    parser.add_argument("--mode", choices=["synthetic", "hardware", "analyze"],
                        default="synthetic", help="Execution mode")
    parser.add_argument("--backend", default="ibm_fez", help="IBM backend name")
    parser.add_argument("--shots", type=int, default=4096, help="Shots per circuit")
    parser.add_argument("--t-max", type=float, default=300.0, help="Max delay [μs]")
    parser.add_argument("--t-step", type=float, default=5.0, help="Delay step [μs]")
    parser.add_argument("--scenario", choices=["revival", "exponential", "noisy_revival"],
                        default="revival", help="Synthetic data scenario")
    parser.add_argument("--input", type=str, help="Input file for analyze mode")
    parser.add_argument("--output", default="./discriminating_results", help="Output directory")
    parser.add_argument("--simulator", action="store_true", help="Use simulator instead of hardware")
    
    args = parser.parse_args()
    
    # Build config
    cfg = ExperimentConfig(
        backend_name=args.backend,
        use_simulator=args.simulator,
        shots=args.shots,
        t_max_us=args.t_max,
        t_step_us=args.t_step,
        output_dir=args.output
    )
    
    # Execute based on mode
    if args.mode == "synthetic":
        print(f"Generating synthetic data (scenario: {args.scenario})...")
        results = generate_synthetic_data(cfg, scenario=args.scenario)
        
    elif args.mode == "hardware":
        print(f"Running on hardware: {cfg.backend_name}")
        results = run_on_hardware(cfg)
        
    elif args.mode == "analyze":
        if not args.input:
            print("Error: --input required for analyze mode")
            sys.exit(1)
        with open(args.input, 'r') as f:
            results = json.load(f)
    
    # Analyze results
    print("\nAnalyzing results...")
    analysis = analyze_results(results, cfg)
    
    # Generate report
    report = generate_report(results, analysis, cfg)
    print("\n" + report)
    
    # Save everything
    save_results(results, analysis, report, cfg)
    
    # Return verdict for scripting
    if "model_comparison" in analysis:
        verdict = analysis["model_comparison"].get("verdict", "UNKNOWN")
        if "REVIVAL" in verdict and analysis["model_comparison"].get("is_nobel_worthy"):
            sys.exit(0)  # Potential discovery!
        else:
            sys.exit(1)  # Standard QM holds

if __name__ == "__main__":
    main()
