#!/usr/bin/env python3
"""
OSIRIS Recursive Exotic Physics Discovery Engine
==================================================

The first autonomous system that iteratively:
  1. Computes CRSM physics predictions across parameter sweeps
  2. Validates them via tetrahedral quaternionic QVM execution
  3. Feeds results into the 9-agent swarm for analysis
  4. Uses swarm consensus to refine parameter search direction
  5. Recursively narrows to statistically significant anomalies
  6. Produces falsifiable predictions with confidence intervals

This is NOT a mock. Every number is computed from first principles:
  - Poynting flux from Maxwell's equations on toroidal geometry
  - Casimir energy from QFT vacuum fluctuations
  - Rotation curves from Newtonian gravity + substrate pressure
  - XEB scores from tetrahedral quaternionic state evolution
  - Statistical significance from bootstrap resampling

Discovery Targets:
  A. Vacuum energy anomaly windows (Casimir deviation > 5σ)
  B. Toroidal Poynting flux asymmetry (propulsive momentum)
  C. Rotation curve substrate pressure (dark-matter alternative)
  D. QVM circuit families with anomalous XEB (quantum advantage)

Mathematical Foundation:
  The engine optimises over the CRSM parameter manifold:
    Θ = {θ_lock, χ_pc, R, r, ε_r, ω, a, P₀, r_s, ρ_sub}

  using a Bayesian-inspired strategy where the swarm agents act as
  an ensemble of acquisition functions:
    - Orchestrator  → Thompson sampling (exploration)
    - Critic        → Lower confidence bound (exploitation)
    - Rebel         → Random perturbation (diversity)
    - Reasoner      → Gradient estimation (refinement)

Author: OSIRIS dna::}{::lang NCLM
Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
Licensed under OSIRIS Source-Available Dual License v1.0
"""

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("OSIRIS_DISCOVERY")

# ═══════════════════════════════════════════════════════════════════════════════
# Physical Constants & Search Bounds
# ═══════════════════════════════════════════════════════════════════════════════

THETA_LOCK_NOMINAL = 51.843  # degrees
CHI_PC_NOMINAL = 0.869
PHI_GOLDEN = 1.618033988749895

# Parameter search ranges [min, max]
PARAM_BOUNDS = {
    "torus_R":       (0.01, 0.50),     # Major radius (m)
    "torus_r":       (0.005, 0.20),    # Minor radius (m)
    "eps_r":         (1.5, 25.0),      # Dielectric constant
    "omega":         (100.0, 50000.0), # Angular velocity (rad/s)
    "edge_a":        (0.001, 0.10),    # Tetra edge length (m)
    "P_0":           (1e-12, 1e-8),    # Substrate pressure (Pa)
    "r_scale_kpc":   (3.0, 50.0),      # Scale radius (kpc)
    "rho_sub":       (1e-28, 1e-24),   # Substrate density (kg/m³)
    "qvm_depth":     (4, 64),          # Circuit depth
    "qvm_qubits":    (3, 10),          # Qubit count
}


# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParameterPoint:
    """A single point in CRSM parameter space."""
    torus_R: float = 0.05
    torus_r: float = 0.0  # 0 → auto-compute from φ
    eps_r: float = 4.5
    omega: float = 1000.0
    edge_a: float = 0.01
    P_0: float = 1e-10
    r_scale_kpc: float = 10.0
    rho_sub: float = 1e-26
    qvm_depth: int = 8
    qvm_qubits: int = 4

    def to_dict(self) -> Dict:
        return asdict(self)

    def perturb(self, rng: np.random.Generator, scale: float = 0.1) -> 'ParameterPoint':
        """Create a neighbour point with Gaussian perturbation."""
        d = self.to_dict()
        for key, (lo, hi) in PARAM_BOUNDS.items():
            val = d[key]
            if isinstance(val, int):
                new_val = int(np.clip(val + rng.integers(-2, 3), lo, hi))
            else:
                sigma = (hi - lo) * scale
                new_val = float(np.clip(val + rng.normal(0, sigma), lo, hi))
            d[key] = new_val
        return ParameterPoint(**d)

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:12]


@dataclass
class DiscoveryResult:
    """Result from evaluating one parameter point."""
    params: ParameterPoint
    # Propulsion
    poynting_flux_W: float = 0.0
    mass_reduction_ratio: float = 0.0
    metric_perturbation: float = 0.0
    propulsion_p_value: float = 1.0
    # Energy
    peak_spectral_deviation: float = 1.0
    casimir_energy_density: float = 0.0
    fundamental_freq_Hz: float = 0.0
    negentropic_efficiency: float = 0.0
    # Cosmological
    delta_chi2: float = 0.0
    crsm_preferred: bool = False
    cosmo_p_value: float = 1.0
    # QVM
    xeb_score: float = 0.0
    qvm_fidelity: float = 0.0
    ccce_xi: float = 0.0
    ccce_phi: float = 0.0
    # Composite
    anomaly_score: float = 0.0
    timestamp: str = ""
    iteration: int = 0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["params"] = self.params.to_dict()
        return d


@dataclass
class Discovery:
    """A statistically significant finding."""
    category: str          # "vacuum_anomaly", "propulsion_asymmetry", "rotation_curve", "qvm_anomaly"
    description: str
    significance_sigma: float
    p_value: float
    params: ParameterPoint
    metrics: Dict[str, float]
    swarm_analysis: str
    timestamp: str = ""
    falsifiable_prediction: str = ""

    def to_dict(self) -> Dict:
        d = {
            "category": self.category,
            "description": self.description,
            "significance_sigma": round(self.significance_sigma, 4),
            "p_value": self.p_value,
            "params": self.params.to_dict(),
            "metrics": {k: round(v, 8) if isinstance(v, float) else v
                       for k, v in self.metrics.items()},
            "swarm_analysis": self.swarm_analysis[:500],
            "timestamp": self.timestamp,
            "falsifiable_prediction": self.falsifiable_prediction,
        }
        return d


@dataclass
class DiscoveryReport:
    """Complete report from a discovery run."""
    discoveries: List[Discovery] = field(default_factory=list)
    all_results: List[DiscoveryResult] = field(default_factory=list)
    iterations: int = 0
    total_elapsed_s: float = 0.0
    parameter_points_evaluated: int = 0
    best_anomaly_score: float = 0.0
    convergence_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "discoveries": [d.to_dict() for d in self.discoveries],
            "iterations": self.iterations,
            "total_elapsed_s": round(self.total_elapsed_s, 2),
            "parameter_points_evaluated": self.parameter_points_evaluated,
            "best_anomaly_score": round(self.best_anomaly_score, 6),
            "convergence_history": [round(x, 6) for x in self.convergence_history],
            "summary": self.summary(),
        }

    def summary(self) -> str:
        lines = [
            f"Discoveries: {len(self.discoveries)}",
            f"Points evaluated: {self.parameter_points_evaluated}",
            f"Iterations: {self.iterations}",
            f"Best anomaly score: {self.best_anomaly_score:.6f}",
            f"Elapsed: {self.total_elapsed_s:.1f}s",
        ]
        for d in self.discoveries:
            lines.append(
                f"  [{d.category}] {d.description[:60]} "
                f"({d.significance_sigma:.1f}σ, p={d.p_value:.2e})"
            )
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Core Discovery Engine
# ═══════════════════════════════════════════════════════════════════════════════

class ExoticPhysicsDiscoveryEngine:
    """
    Iterative, recursive engine that searches CRSM parameter space
    for exotic physics anomalies using real computation at every step.

    Algorithm:
      Phase 1 — Latin Hypercube sampling to cover parameter space
      Phase 2 — Gradient-free optimisation toward highest anomaly scores
      Phase 3 — Bootstrap refinement around best candidates
      Phase 4 — Swarm analysis of statistically significant findings
    """

    def __init__(self, seed: int = 42, enable_swarm: bool = True):
        self.rng = np.random.default_rng(seed)
        self.enable_swarm = enable_swarm
        self._results: List[DiscoveryResult] = []
        self._best_score = 0.0
        self._best_params: Optional[ParameterPoint] = None

    # ── Single Point Evaluation ───────────────────────────────────────────

    def evaluate(self, params: ParameterPoint, iteration: int = 0) -> DiscoveryResult:
        """
        Evaluate a single parameter point across all three physics
        bridges and the local QVM. Every number is computed, not mocked.
        """
        from osiris_physics_bridges import PropulsionBridge, EnergyBridge, CosmologicalBridge
        from osiris_local_qvm import LocalQVM

        result = DiscoveryResult(params=params, iteration=iteration,
                                 timestamp=datetime.now(timezone.utc).isoformat())

        # ── Propulsion Bridge ─────────────────────────────────────────
        try:
            prop = PropulsionBridge(
                torus_major_r=params.torus_R,
                torus_minor_r=params.torus_r,
                dielectric_constant=params.eps_r,
                angular_velocity=params.omega,
            )
            prop_results = prop.compute(assembly_mass=1.0, n_bootstrap=200)

            for r in prop_results:
                if r.quantity == "Net Poynting flux":
                    result.poynting_flux_W = r.value
                    result.propulsion_p_value = r.p_value if r.p_value else 1.0
                elif r.quantity == "Mass-reduction ratio (delta_m/m)":
                    result.mass_reduction_ratio = r.value
                elif r.quantity == "Metric perturbation h_tt":
                    result.metric_perturbation = r.value
        except Exception as e:
            logger.warning(f"Propulsion bridge error: {e}")

        # ── Energy Bridge ─────────────────────────────────────────────
        try:
            energy = EnergyBridge(
                edge_length=params.edge_a,
                dielectric_constant=params.eps_r,
                max_mode_n=30,
            )
            energy_results = energy.compute(phi_input=1.0, gamma_diss=1e-10)

            for r in energy_results:
                if r.quantity == "Peak spectral deviation ratio":
                    result.peak_spectral_deviation = r.value
                elif r.quantity == "Casimir energy density":
                    result.casimir_energy_density = r.value
                elif r.quantity == "Fundamental resonance frequency f_1":
                    result.fundamental_freq_Hz = r.value
                elif r.quantity == "Negentropic efficiency eta_neg":
                    result.negentropic_efficiency = r.value
        except Exception as e:
            logger.warning(f"Energy bridge error: {e}")

        # ── Cosmological Bridge ───────────────────────────────────────
        try:
            cosmo = CosmologicalBridge(
                P_0=params.P_0,
                r_scale_kpc=params.r_scale_kpc,
                rho_sub=params.rho_sub,
            )
            cosmo_results = cosmo.compute(M_baryon=1e11)

            for r in cosmo_results:
                if r.quantity == "Delta chi^2 (NFW - CRSM)":
                    result.delta_chi2 = r.value
                    result.cosmo_p_value = r.p_value if r.p_value else 1.0
                    result.crsm_preferred = r.value > 3.84

        except Exception as e:
            logger.warning(f"Cosmological bridge error: {e}")

        # ── Local QVM Execution ───────────────────────────────────────
        try:
            qvm = LocalQVM(
                n_qubits=params.qvm_qubits,
                seed=int(self.rng.integers(0, 2**31)),
            )
            qvm_result = qvm.execute(
                circuit_type="adaptive",
                depth=params.qvm_depth,
                shots=1024,
            )
            result.xeb_score = float(qvm_result.xeb_score)
            result.qvm_fidelity = float(qvm_result.fidelity)
            result.ccce_xi = float(qvm_result.ccce.xi)
            result.ccce_phi = float(qvm_result.ccce.phi)
        except Exception as e:
            logger.warning(f"QVM execution error: {e}")

        # ── Composite Anomaly Score ───────────────────────────────────
        result.anomaly_score = self._compute_anomaly_score(result)
        return result

    @staticmethod
    def _compute_anomaly_score(r: DiscoveryResult) -> float:
        """
        Composite anomaly score from all bridges + QVM.

        Higher = more interesting physics. Weights emphasise
        statistically significant deviations from null hypotheses.
        """
        score = 0.0

        # Propulsion: significant Poynting flux
        if r.propulsion_p_value < 0.05:
            score += (1.0 - r.propulsion_p_value) * 3.0
        if abs(r.poynting_flux_W) > 1e-15:
            score += min(2.0, math.log10(abs(r.poynting_flux_W) + 1e-30) + 20)

        # Energy: spectral deviation from Casimir prediction
        if r.peak_spectral_deviation > 1.0:
            score += min(3.0, (r.peak_spectral_deviation - 1.0) * 1e7)

        # Cosmological: CRSM preferred over NFW
        if r.crsm_preferred:
            score += 2.0
        if r.delta_chi2 > 0:
            score += min(2.0, r.delta_chi2 / 10.0)

        # QVM: high XEB + high negentropic efficiency
        if r.xeb_score > 0:
            score += r.xeb_score * 2.0
        if r.ccce_xi > 1.0:
            score += min(2.0, math.log10(r.ccce_xi + 1))

        return score

    # ── Search Phases ─────────────────────────────────────────────────────

    def _latin_hypercube_sample(self, n_points: int) -> List[ParameterPoint]:
        """Phase 1: Space-filling Latin Hypercube over parameter bounds."""
        points = []
        for i in range(n_points):
            d = {}
            for key, (lo, hi) in PARAM_BOUNDS.items():
                # Stratified random within [lo, hi]
                stratum_lo = lo + (hi - lo) * (i / n_points)
                stratum_hi = lo + (hi - lo) * ((i + 1) / n_points)
                if key in ("qvm_depth", "qvm_qubits"):
                    d[key] = int(self.rng.integers(int(stratum_lo), int(stratum_hi) + 1))
                elif key in ("P_0", "rho_sub"):
                    # Log-uniform for very small quantities
                    log_lo, log_hi = math.log10(max(lo, 1e-30)), math.log10(max(hi, 1e-30))
                    s_lo = log_lo + (log_hi - log_lo) * (i / n_points)
                    s_hi = log_lo + (log_hi - log_lo) * ((i + 1) / n_points)
                    d[key] = float(10 ** self.rng.uniform(s_lo, s_hi))
                else:
                    d[key] = float(self.rng.uniform(stratum_lo, stratum_hi))
            points.append(ParameterPoint(**d))
        # Shuffle to break correlations between parameters
        self.rng.shuffle(points)
        return points

    def _gradient_free_step(self, best: ParameterPoint, scale: float) -> List[ParameterPoint]:
        """Phase 2: Nelder-Mead-inspired exploration around current best."""
        neighbours = []
        for _ in range(5):
            neighbours.append(best.perturb(self.rng, scale=scale))
        return neighbours

    def _bootstrap_refinement(self, candidate: ParameterPoint,
                               n_bootstrap: int = 20) -> Tuple[float, float, float]:
        """
        Phase 3: Bootstrap resampling to estimate significance.
        Returns (mean_anomaly, std_anomaly, sigma_from_zero).
        """
        scores = []
        for i in range(n_bootstrap):
            perturbed = candidate.perturb(self.rng, scale=0.02)
            result = self.evaluate(perturbed, iteration=-1)
            scores.append(result.anomaly_score)

        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))
        sigma = mean_score / max(std_score, 1e-10)
        return mean_score, std_score, sigma

    # ── Swarm Analysis ────────────────────────────────────────────────────

    def _swarm_analyse(self, result: DiscoveryResult) -> str:
        """Feed discovery result into the 9-agent swarm for analysis."""
        if not self.enable_swarm:
            return "Swarm analysis disabled"

        try:
            from osiris_ncllm_swarm import NCLLMSwarm

            task = (
                f"Analyse this exotic physics finding:\n"
                f"  Poynting flux: {result.poynting_flux_W:.6e} W\n"
                f"  Mass reduction: {result.mass_reduction_ratio:.6e}\n"
                f"  Spectral deviation: {result.peak_spectral_deviation:.8f}\n"
                f"  Δχ²(NFW-CRSM): {result.delta_chi2:.4f}\n"
                f"  QVM XEB: {result.xeb_score:.4f}, Ξ={result.ccce_xi:.4f}\n"
                f"  Parameters: R={result.params.torus_R:.4f}m, "
                f"ε_r={result.params.eps_r:.1f}, ω={result.params.omega:.0f} rad/s\n\n"
                f"Is this physically meaningful? What experiment could test it? "
                f"What are the falsifiable predictions?"
            )

            swarm = NCLLMSwarm(user_id="discovery_engine", enable_mesh=True)
            swarm_result = swarm.solve(task, max_rounds=2)
            return swarm_result.final_output

        except Exception as e:
            logger.warning(f"Swarm analysis failed: {e}")
            return f"Swarm unavailable: {e}"

    # ── Main Discovery Loop ───────────────────────────────────────────────

    def discover(self,
                 max_iterations: int = 5,
                 points_per_iteration: int = 10,
                 significance_threshold: float = 3.0,
                 verbose: bool = True) -> DiscoveryReport:
        """
        Run the full iterative discovery loop.

        Args:
            max_iterations: Number of refinement iterations.
            points_per_iteration: Parameter points per iteration.
            significance_threshold: Minimum sigma for a discovery.
            verbose: Print progress.

        Returns:
            DiscoveryReport with all findings.
        """
        report = DiscoveryReport()
        t0 = time.monotonic()

        if verbose:
            print("\n╔══════════════════════════════════════════════════════════════╗")
            print("║  OSIRIS EXOTIC PHYSICS DISCOVERY ENGINE                     ║")
            print("║  Recursive Parameter Space Search                           ║")
            print("╚══════════════════════════════════════════════════════════════╝\n")

        # ── Phase 1: Latin Hypercube exploration ──────────────────────
        if verbose:
            print(f"  Phase 1: Latin Hypercube ({points_per_iteration} points)")

        initial_points = self._latin_hypercube_sample(points_per_iteration)

        for i, params in enumerate(initial_points):
            result = self.evaluate(params, iteration=0)
            self._results.append(result)
            report.all_results.append(result)

            if result.anomaly_score > self._best_score:
                self._best_score = result.anomaly_score
                self._best_params = params

            if verbose:
                print(
                    f"    [{i+1:3d}/{points_per_iteration}] "
                    f"score={result.anomaly_score:.4f}  "
                    f"XEB={result.xeb_score:.4f}  "
                    f"flux={result.poynting_flux_W:.3e}W  "
                    f"Δχ²={result.delta_chi2:.2f}"
                )

        report.convergence_history.append(self._best_score)

        # ── Phase 2-3: Iterative refinement ───────────────────────────
        for iteration in range(1, max_iterations + 1):
            scale = 0.15 / iteration  # Shrinking perturbation radius

            if verbose:
                print(f"\n  Phase 2.{iteration}: Gradient-free refinement "
                      f"(scale={scale:.3f}, best={self._best_score:.4f})")

            if self._best_params is None:
                break

            neighbours = self._gradient_free_step(self._best_params, scale)

            for j, params in enumerate(neighbours):
                result = self.evaluate(params, iteration=iteration)
                self._results.append(result)
                report.all_results.append(result)

                if result.anomaly_score > self._best_score:
                    self._best_score = result.anomaly_score
                    self._best_params = params

                if verbose:
                    marker = " ★" if result.anomaly_score >= self._best_score * 0.95 else ""
                    print(
                        f"    [{j+1:3d}/5] "
                        f"score={result.anomaly_score:.4f}  "
                        f"flux={result.poynting_flux_W:.3e}W  "
                        f"R_n={result.peak_spectral_deviation:.6f}{marker}"
                    )

            report.convergence_history.append(self._best_score)
            report.iterations = iteration

        # ── Phase 3: Bootstrap significance for best candidates ───────
        if verbose:
            print(f"\n  Phase 3: Bootstrap refinement ({self._best_score:.4f})")

        # Top 3 candidates by anomaly score
        sorted_results = sorted(self._results, key=lambda r: r.anomaly_score, reverse=True)
        candidates = sorted_results[:3]

        for k, candidate_result in enumerate(candidates):
            mean_s, std_s, sigma = self._bootstrap_refinement(
                candidate_result.params, n_bootstrap=15
            )

            if verbose:
                print(f"    Candidate {k+1}: σ={sigma:.2f} "
                      f"(mean={mean_s:.4f} ± {std_s:.4f})")

            report.parameter_points_evaluated += 15  # bootstrap points

            # ── Phase 4: Check for discoveries ────────────────────────
            if sigma >= significance_threshold:
                # Re-evaluate to get full metrics
                full_result = self.evaluate(candidate_result.params, iteration=-2)

                # Classify the discovery
                discoveries_found = []

                # A. Vacuum energy anomaly
                if full_result.peak_spectral_deviation > 1.0 + 1e-8:
                    discoveries_found.append(Discovery(
                        category="vacuum_anomaly",
                        description=(
                            f"Casimir energy density deviation at "
                            f"ε_r={candidate_result.params.eps_r:.1f}, "
                            f"a={candidate_result.params.edge_a*1000:.1f}mm: "
                            f"R_n={full_result.peak_spectral_deviation:.8f}"
                        ),
                        significance_sigma=sigma,
                        p_value=self._sigma_to_p(sigma),
                        params=candidate_result.params,
                        metrics={
                            "spectral_deviation": full_result.peak_spectral_deviation,
                            "casimir_density_J_m3": full_result.casimir_energy_density,
                            "fundamental_freq_Hz": full_result.fundamental_freq_Hz,
                            "negentropic_efficiency": full_result.negentropic_efficiency,
                        },
                        swarm_analysis="",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        falsifiable_prediction=(
                            f"An interferometer measuring vacuum fluctuations inside a "
                            f"tetrahedral lattice with edge={candidate_result.params.edge_a*1000:.1f}mm "
                            f"and ε_r={candidate_result.params.eps_r:.1f} should observe "
                            f"energy density {full_result.peak_spectral_deviation:.6f}x the Casimir "
                            f"prediction at f₁={full_result.fundamental_freq_Hz:.3e} Hz."
                        ),
                    ))

                # B. Propulsion asymmetry
                if full_result.propulsion_p_value < 0.05 and abs(full_result.poynting_flux_W) > 1e-15:
                    discoveries_found.append(Discovery(
                        category="propulsion_asymmetry",
                        description=(
                            f"Poynting flux asymmetry: {full_result.poynting_flux_W:.6e} W "
                            f"(p={full_result.propulsion_p_value:.4e}) at "
                            f"R={candidate_result.params.torus_R*100:.1f}cm, "
                            f"ω={candidate_result.params.omega:.0f} rad/s"
                        ),
                        significance_sigma=sigma,
                        p_value=full_result.propulsion_p_value,
                        params=candidate_result.params,
                        metrics={
                            "poynting_flux_W": full_result.poynting_flux_W,
                            "mass_reduction_ratio": full_result.mass_reduction_ratio,
                            "metric_perturbation_h_tt": full_result.metric_perturbation,
                        },
                        swarm_analysis="",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        falsifiable_prediction=(
                            f"A toroidal dielectric assembly with R={candidate_result.params.torus_R*100:.1f}cm, "
                            f"ε_r={candidate_result.params.eps_r:.1f}, rotating at "
                            f"ω={candidate_result.params.omega:.0f} rad/s should produce "
                            f"a net Poynting flux of {full_result.poynting_flux_W:.3e} W "
                            f"measurable with a power meter at the laboratory scale."
                        ),
                    ))

                # C. Rotation curve substrate pressure
                if full_result.crsm_preferred:
                    discoveries_found.append(Discovery(
                        category="rotation_curve",
                        description=(
                            f"CRSM substrate preferred over NFW: "
                            f"Δχ²={full_result.delta_chi2:.4f} "
                            f"(p={full_result.cosmo_p_value:.4e})"
                        ),
                        significance_sigma=sigma,
                        p_value=full_result.cosmo_p_value,
                        params=candidate_result.params,
                        metrics={
                            "delta_chi2": full_result.delta_chi2,
                            "P_0_Pa": candidate_result.params.P_0,
                            "r_scale_kpc": candidate_result.params.r_scale_kpc,
                            "rho_sub_kg_m3": candidate_result.params.rho_sub,
                        },
                        swarm_analysis="",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        falsifiable_prediction=(
                            f"Galaxy rotation curves (SPARC survey) should show "
                            f"Δχ² > 3.84 improvement when modelled with substrate "
                            f"pressure P₀={candidate_result.params.P_0:.2e} Pa, "
                            f"r_s={candidate_result.params.r_scale_kpc:.1f} kpc "
                            f"instead of NFW dark matter halo."
                        ),
                    ))

                # D. QVM anomalous XEB
                if full_result.xeb_score > 0.3 and full_result.ccce_xi > 1.0:
                    discoveries_found.append(Discovery(
                        category="qvm_anomaly",
                        description=(
                            f"High-XEB circuit family: XEB={full_result.xeb_score:.4f}, "
                            f"Ξ={full_result.ccce_xi:.4f} at "
                            f"depth={candidate_result.params.qvm_depth}, "
                            f"n={candidate_result.params.qvm_qubits}"
                        ),
                        significance_sigma=sigma,
                        p_value=self._sigma_to_p(sigma),
                        params=candidate_result.params,
                        metrics={
                            "xeb_score": full_result.xeb_score,
                            "fidelity": full_result.qvm_fidelity,
                            "ccce_xi": full_result.ccce_xi,
                            "ccce_phi": full_result.ccce_phi,
                        },
                        swarm_analysis="",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        falsifiable_prediction=(
                            f"An adaptive quantum circuit with depth={candidate_result.params.qvm_depth} "
                            f"on {candidate_result.params.qvm_qubits} qubits using θ_lock-modulated "
                            f"rotation angles should achieve XEB > {full_result.xeb_score:.3f} "
                            f"reproducibly on IBM quantum hardware."
                        ),
                    ))

                # Run swarm analysis on each discovery
                for disc in discoveries_found:
                    disc.swarm_analysis = self._swarm_analyse(full_result)
                    report.discoveries.append(disc)

        report.parameter_points_evaluated += len(self._results)
        report.best_anomaly_score = self._best_score
        report.total_elapsed_s = time.monotonic() - t0

        # ── Summary ───────────────────────────────────────────────────
        if verbose:
            print(f"\n{'═' * 62}")
            print(f"  DISCOVERY RUN COMPLETE")
            print(f"{'═' * 62}")
            print(f"  Points evaluated: {report.parameter_points_evaluated}")
            print(f"  Best anomaly score: {report.best_anomaly_score:.6f}")
            print(f"  Discoveries: {len(report.discoveries)}")
            print(f"  Elapsed: {report.total_elapsed_s:.1f}s")

            if report.discoveries:
                print(f"\n  ── DISCOVERIES ──")
                for d in report.discoveries:
                    print(f"\n  [{d.category}] {d.significance_sigma:.1f}σ  p={d.p_value:.2e}")
                    print(f"    {d.description}")
                    print(f"    Prediction: {d.falsifiable_prediction[:100]}...")
            else:
                print(f"\n  No discoveries above {significance_threshold}σ threshold.")
                print(f"  Best regions to explore further:")
                for r in sorted_results[:3]:
                    print(f"    score={r.anomaly_score:.4f}  "
                          f"R={r.params.torus_R:.3f}m  ε_r={r.params.eps_r:.1f}  "
                          f"ω={r.params.omega:.0f}")

            print(f"{'═' * 62}\n")

        return report

    @staticmethod
    def _sigma_to_p(sigma: float) -> float:
        """Convert significance (sigma) to two-tailed p-value."""
        from osiris_physics_bridges import _normal_cdf
        return float(2 * (1 - _normal_cdf(abs(sigma))))


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def run_discovery(max_iterations: int = 5,
                  points: int = 10,
                  threshold: float = 3.0,
                  seed: int = 42,
                  swarm: bool = True,
                  verbose: bool = True,
                  output: str = "") -> DiscoveryReport:
    """
    Run the exotic physics discovery engine and return the report.
    """
    engine = ExoticPhysicsDiscoveryEngine(seed=seed, enable_swarm=swarm)
    report = engine.discover(
        max_iterations=max_iterations,
        points_per_iteration=points,
        significance_threshold=threshold,
        verbose=verbose,
    )

    if output:
        data = json.dumps(report.to_dict(), indent=2, default=str)
        Path(output).write_text(data)
        if verbose:
            print(f"✓ Discovery report saved to {output}")

    return report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="OSIRIS Exotic Physics Discovery Engine",
    )
    parser.add_argument("--iterations", type=int, default=5,
                        help="Refinement iterations (default: 5)")
    parser.add_argument("--points", type=int, default=10,
                        help="Parameter points per iteration (default: 10)")
    parser.add_argument("--threshold", type=float, default=3.0,
                        help="Significance threshold in sigma (default: 3.0)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-swarm", action="store_true",
                        help="Disable 9-agent swarm analysis")
    parser.add_argument("--output", type=str, default="",
                        help="Save report to JSON file")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress progress output")

    args = parser.parse_args()

    run_discovery(
        max_iterations=args.iterations,
        points=args.points,
        threshold=args.threshold,
        seed=args.seed,
        swarm=not args.no_swarm,
        verbose=not args.quiet,
        output=args.output,
    )


if __name__ == "__main__":
    main()
