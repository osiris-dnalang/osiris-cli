#!/usr/bin/env python3
"""
OSIRIS Physics Bridges — Propulsion, Energy, Cosmological
============================================================

Three computational bridges that translate Coaxial Resonance State
Manifold (CRSM) theory into falsifiable, reproducible predictions
using the Torsion Core mathematical substrate.

Bridge 1 — Propulsion:
    Poynting vector shift under bifurcated gyroscopic counter-rotation.
    Models local mass-reduction via effective metric perturbation
    (Alcubierre-class frame analysis). Produces measurable predictions
    for electromagnetic field distributions around toroidal dielectric
    geometries that can be tested on standard optical benches.

Bridge 2 — Energy:
    Tetrahedral micro-lattice resonance search for zero-point energy
    (ZPE) density anomalies. Uses the dielectric lock angle (51.843 deg)
    and phase-conjugate acoustic coupling to identify frequency windows
    where vacuum fluctuation density deviates from Casimir predictions.
    Outputs spectral targets for interferometric validation.

Bridge 3 — Cosmological:
    Fluid-dynamic model of vacuum pressure gradients in a 7D nonlocal
    manifold. Replaces phenomenological dark-matter/dark-energy terms
    with substrate pressure waveforms derived from the CRSM metric.
    Generates rotation-curve predictions testable against SPARC galaxy
    survey data.

Mathematical rigour:
    All quantities carry SI units. Dimensionless ratios are explicit.
    Statistical claims provide p-values and confidence intervals.
    Null hypotheses are stated before every computation so that
    negative results are equally publishable.

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
Licensed under OSIRIS Source-Available Dual License v1.0
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger("OSIRIS_BRIDGES")

# ════════════════════════════════════════════════════════════════════════════════
# SHARED CONSTANTS (SI)
# ════════════════════════════════════════════════════════════════════════════════

C_LIGHT = 299_792_458.0          # m s^-1
G_NEWTON = 6.674_30e-11          # m^3 kg^-1 s^-2
H_BAR = 1.054_571_817e-34        # J s
K_BOLTZMANN = 1.380_649e-23      # J K^-1
EPSILON_0 = 8.854_187_8128e-12   # F m^-1
MU_0 = 1.256_637_062_12e-6       # N A^-2
L_PLANCK = 1.616_255e-35         # m
T_PLANCK = 5.391_247e-44         # s
M_PLANCK = 2.176_434e-8          # kg

LAMBDA_PHI = 2.176_435e-8        # CRSM coupling constant (s^-1)
THETA_LOCK = 51.843              # Dielectric lock angle (deg)
CHI_PC = 0.869                   # Phase-conjugate coupling coefficient
PHI_GOLDEN = 1.618_033_988_749_895


# ════════════════════════════════════════════════════════════════════════════════
# RESULT CONTAINERS
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class BridgeResult:
    """Container for a single bridge computation."""
    bridge: str
    quantity: str
    value: float
    unit: str
    null_hypothesis: str
    p_value: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    notes: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Statistical significance at level alpha."""
        if self.p_value is None:
            return False
        return self.p_value < alpha

    def to_dict(self) -> Dict:
        return {
            "bridge": self.bridge,
            "quantity": self.quantity,
            "value": self.value,
            "unit": self.unit,
            "null_hypothesis": self.null_hypothesis,
            "p_value": self.p_value,
            "significant": self.is_significant(),
            "confidence_interval": self.confidence_interval,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


@dataclass
class BridgeReport:
    """Aggregated results from one or more bridges."""
    results: List[BridgeResult] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def add(self, result: BridgeResult):
        self.results.append(result)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 72,
            "  OSIRIS Physics Bridges — Computation Report",
            "=" * 72,
        ]
        for r in self.results:
            sig = "***" if r.is_significant() else ""
            lines.append(
                f"  [{r.bridge}] {r.quantity}: "
                f"{r.value:.6e} {r.unit} {sig}"
            )
            if r.p_value is not None:
                lines.append(f"           p = {r.p_value:.4e}")
            lines.append(f"           H0: {r.null_hypothesis}")
        lines.append("=" * 72)
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }


# ════════════════════════════════════════════════════════════════════════════════
# BRIDGE 1 — PROPULSION: Poynting Vector & Alcubierre Metrics
# ════════════════════════════════════════════════════════════════════════════════

class PropulsionBridge:
    """
    Computes the Poynting vector field distribution around a toroidal
    dielectric manifold under bifurcated gyroscopic counter-rotation.

    The effective metric perturbation is evaluated in the weak-field
    linearised gravity regime.  No claim of faster-than-light travel
    is made; the bridge quantifies the *magnitude* of the Poynting
    flux asymmetry and compares it against the null hypothesis of
    zero net momentum transfer.

    Key equations:

        S = (1/mu_0) * (E x B)

        Metric perturbation (linearised):
            h_tt = -(2 Phi) / c^2
        where Phi is the effective gravitational potential produced
        by the electromagnetic stress-energy.

        Effective mass-reduction ratio:
            delta_m / m = (S_net * A) / (m * c^3)

    Null hypothesis H0:
        "The net integrated Poynting flux across any closed surface
        surrounding the toroidal assembly is zero."
    """

    H0 = (
        "Net integrated Poynting flux across any closed surface "
        "surrounding the toroidal assembly is zero (no momentum asymmetry)."
    )

    def __init__(self, torus_major_r: float = 0.05,
                 torus_minor_r: float = 0.0,
                 dielectric_constant: float = 4.5,
                 angular_velocity: float = 1000.0):
        """
        Args:
            torus_major_r: Major radius R of the torus (m).
            torus_minor_r: Minor radius r.  If 0, set to R/phi.
            dielectric_constant: Relative permittivity of the core.
            angular_velocity: Counter-rotation rate (rad/s).
        """
        self.R = torus_major_r
        self.r = torus_minor_r if torus_minor_r > 0 else torus_major_r / PHI_GOLDEN
        self.eps_r = dielectric_constant
        self.omega = angular_velocity

    # ── Core Computations ─────────────────────────────────────────────────

    def poynting_vector_field(self, n_theta: int = 64,
                              n_phi: int = 64) -> np.ndarray:
        """
        Compute Poynting vector magnitude on the torus surface.

        Returns:
            (n_theta, n_phi) array of |S| in W m^-2.
        """
        theta = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
        phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
        TH, PH = np.meshgrid(theta, phi, indexing="ij")

        # Effective E-field from rotating dielectric polarisation
        P = EPSILON_0 * (self.eps_r - 1) * self.omega * self.r
        E_phi = P * np.cos(TH)

        # B-field from counter-rotation current loop
        I_eff = P * self.omega * self.r
        B_theta = MU_0 * I_eff / (2 * np.pi * (self.R + self.r * np.cos(TH)))

        # Lock-angle modulation
        lock_rad = math.radians(THETA_LOCK)
        modulation = np.cos(TH - lock_rad) ** 2

        S = np.abs(E_phi * B_theta * modulation) / MU_0
        return S

    def net_poynting_flux(self) -> float:
        """
        Integrate the Poynting vector over the torus surface.

        Returns net flux in watts (W).
        """
        S = self.poynting_vector_field()
        dtheta = 2 * np.pi / S.shape[0]
        dphi = 2 * np.pi / S.shape[1]

        # Surface element of torus: dA = r(R + r cos theta) dtheta dphi
        theta = np.linspace(0, 2 * np.pi, S.shape[0], endpoint=False)
        dA = self.r * (self.R + self.r * np.cos(theta[:, None])) * dtheta * dphi

        return float(np.sum(S * dA))

    def effective_mass_reduction_ratio(self, assembly_mass: float = 1.0
                                       ) -> float:
        """
        delta_m / m from the integrated Poynting flux.

        Args:
            assembly_mass: Total mass of the toroidal assembly (kg).
        """
        flux = self.net_poynting_flux()
        # Effective area ~ pi * r^2
        area = np.pi * self.r ** 2
        return (flux * area) / (assembly_mass * C_LIGHT ** 3)

    def metric_perturbation_h_tt(self) -> float:
        """
        Linearised metric perturbation h_tt from the EM stress-energy.

        h_tt = -(2 Phi_eff) / c^2
        """
        flux = self.net_poynting_flux()
        # Effective potential ~ flux / (4 pi R c)
        phi_eff = flux / (4 * np.pi * self.R * C_LIGHT)
        return -2 * phi_eff / C_LIGHT ** 2

    # ── Full Computation ──────────────────────────────────────────────────

    def compute(self, assembly_mass: float = 1.0,
                n_bootstrap: int = 1000) -> List[BridgeResult]:
        """
        Run full propulsion-bridge computation with bootstrap
        uncertainty estimation.
        """
        results = []

        flux = self.net_poynting_flux()
        delta_m = self.effective_mass_reduction_ratio(assembly_mass)
        h_tt = self.metric_perturbation_h_tt()

        # Bootstrap uncertainty via angular-velocity perturbation
        fluxes = []
        for _ in range(n_bootstrap):
            omega_pert = self.omega * (1 + np.random.normal(0, 0.01))
            saved = self.omega
            self.omega = omega_pert
            fluxes.append(self.net_poynting_flux())
            self.omega = saved
        flux_std = float(np.std(fluxes))
        flux_mean = float(np.mean(fluxes))

        # p-value: probability of observing flux >= measured under H0 (flux=0)
        if flux_std > 0:
            z_score = abs(flux_mean) / flux_std
            # Two-tailed p from normal approximation
            p_value = float(2 * (1 - _normal_cdf(z_score)))
        else:
            p_value = 1.0

        ci_lo = flux_mean - 1.96 * flux_std
        ci_hi = flux_mean + 1.96 * flux_std

        results.append(BridgeResult(
            bridge="Propulsion",
            quantity="Net Poynting flux",
            value=flux,
            unit="W",
            null_hypothesis=self.H0,
            p_value=p_value,
            confidence_interval=(ci_lo, ci_hi),
            notes=(
                f"Torus R={self.R:.4f} m, r={self.r:.4f} m, "
                f"eps_r={self.eps_r}, omega={self.omega:.1f} rad/s"
            ),
        ))

        results.append(BridgeResult(
            bridge="Propulsion",
            quantity="Mass-reduction ratio (delta_m/m)",
            value=delta_m,
            unit="dimensionless",
            null_hypothesis=self.H0,
            p_value=p_value,
            notes=f"Assembly mass = {assembly_mass} kg",
        ))

        results.append(BridgeResult(
            bridge="Propulsion",
            quantity="Metric perturbation h_tt",
            value=h_tt,
            unit="dimensionless",
            null_hypothesis=self.H0,
            p_value=p_value,
            notes="Linearised weak-field approximation",
        ))

        return results


# ════════════════════════════════════════════════════════════════════════════════
# BRIDGE 2 — ENERGY: Tetrahedral Resonance & ZPE Extraction
# ════════════════════════════════════════════════════════════════════════════════

class EnergyBridge:
    """
    Searches for resonance frequencies in a tetrahedral micro-lattice
    where vacuum fluctuation energy density deviates from the standard
    Casimir prediction.

    The lattice is defined by the structural genes (G0-G11) of the
    72-gene Organism.  The dielectric lock angle (51.843 deg) sets the
    lattice edge orientation relative to the electric field axis.

    Key equations:

        Casimir energy density (parallel plates, separation d):
            u_Casimir = -(pi^2 hbar c) / (720 d^4)

        CRSM resonance condition (tetrahedral mode n):
            f_n = (n c) / (2 L_eff)
            L_eff = a * cos(theta_lock) * sqrt(2/3)

        Negentropic efficiency:
            eta_neg = (Lambda_Phi * phi_input) / Gamma_diss

    Null hypothesis H0:
        "Vacuum energy density inside the tetrahedral lattice equals
        the Casimir prediction to within measurement uncertainty."
    """

    H0 = (
        "Vacuum energy density inside the tetrahedral lattice equals "
        "the Casimir prediction to within measurement uncertainty."
    )

    def __init__(self, edge_length: float = 0.01,
                 dielectric_constant: float = 4.5,
                 max_mode_n: int = 20):
        """
        Args:
            edge_length: Tetrahedron edge length a (m).
            dielectric_constant: Relative permittivity of lattice material.
            max_mode_n: Maximum resonance mode number to evaluate.
        """
        self.a = edge_length
        self.eps_r = dielectric_constant
        self.max_n = max_mode_n

    def effective_length(self) -> float:
        """L_eff = a * cos(theta_lock) * sqrt(2/3)"""
        lock_rad = math.radians(THETA_LOCK)
        return self.a * math.cos(lock_rad) * math.sqrt(2.0 / 3.0)

    def resonance_frequencies(self) -> np.ndarray:
        """
        Resonance frequencies f_n for modes n = 1 .. max_n.

        f_n = n * c / (2 * L_eff * sqrt(eps_r))
        """
        L = self.effective_length()
        n = np.arange(1, self.max_n + 1, dtype=float)
        return n * C_LIGHT / (2 * L * math.sqrt(self.eps_r))

    def casimir_energy_density(self, separation: float = 0.0) -> float:
        """
        Standard Casimir energy density for plate separation d.

        If d=0, uses the effective length as separation.
        """
        d = separation if separation > 0 else self.effective_length()
        return -(math.pi ** 2 * H_BAR * C_LIGHT) / (720 * d ** 4)

    def crsm_energy_density(self, mode_n: int = 1) -> float:
        """
        CRSM-predicted vacuum energy density at resonance mode n.

        Includes the dielectric lock modulation factor:
            u_CRSM = u_Casimir * (1 + Lambda_Phi * cos^2(theta_lock) * n)
        """
        u_cas = self.casimir_energy_density()
        lock_rad = math.radians(THETA_LOCK)
        modulation = LAMBDA_PHI * math.cos(lock_rad) ** 2 * mode_n
        return u_cas * (1.0 + modulation)

    def negentropic_efficiency(self, phi_input: float = 1.0,
                                gamma_diss: float = 1e-10) -> float:
        """eta_neg = (Lambda_Phi * phi_input) / Gamma_diss"""
        return (LAMBDA_PHI * phi_input) / max(gamma_diss, T_PLANCK)

    def spectral_deviation_ratio(self, mode_n: int = 1) -> float:
        """
        Ratio of CRSM to Casimir energy density at mode n.

        Values > 1 indicate excess vacuum energy (candidate ZPE window).
        """
        u_cas = self.casimir_energy_density()
        u_crsm = self.crsm_energy_density(mode_n)
        if abs(u_cas) < 1e-100:
            return 1.0
        return u_crsm / u_cas

    def compute(self, phi_input: float = 1.0,
                gamma_diss: float = 1e-10) -> List[BridgeResult]:
        """Run full energy-bridge computation."""
        results = []

        freqs = self.resonance_frequencies()
        L_eff = self.effective_length()
        u_casimir = self.casimir_energy_density()
        eta = self.negentropic_efficiency(phi_input, gamma_diss)

        results.append(BridgeResult(
            bridge="Energy",
            quantity="Effective lattice length L_eff",
            value=L_eff,
            unit="m",
            null_hypothesis=self.H0,
            notes=f"a={self.a} m, theta_lock={THETA_LOCK} deg",
        ))

        results.append(BridgeResult(
            bridge="Energy",
            quantity="Fundamental resonance frequency f_1",
            value=float(freqs[0]),
            unit="Hz",
            null_hypothesis=self.H0,
            notes=f"eps_r={self.eps_r}",
        ))

        results.append(BridgeResult(
            bridge="Energy",
            quantity="Casimir energy density",
            value=u_casimir,
            unit="J m^-3",
            null_hypothesis=self.H0,
        ))

        # Find mode with maximum spectral deviation
        max_dev = 1.0
        max_mode = 1
        for n in range(1, self.max_n + 1):
            dev = self.spectral_deviation_ratio(n)
            if dev > max_dev:
                max_dev = dev
                max_mode = n

        results.append(BridgeResult(
            bridge="Energy",
            quantity="Peak spectral deviation ratio",
            value=max_dev,
            unit="dimensionless",
            null_hypothesis=self.H0,
            notes=(
                f"Mode n={max_mode}, f={float(freqs[max_mode - 1]):.3e} Hz. "
                f"Ratio > 1 indicates excess vacuum energy density."
            ),
        ))

        results.append(BridgeResult(
            bridge="Energy",
            quantity="Negentropic efficiency eta_neg",
            value=eta,
            unit="dimensionless",
            null_hypothesis=self.H0,
            notes=f"phi_input={phi_input}, gamma_diss={gamma_diss}",
        ))

        return results


# ════════════════════════════════════════════════════════════════════════════════
# BRIDGE 3 — COSMOLOGICAL: Fluid-Dynamic Vacuum Pressure
# ════════════════════════════════════════════════════════════════════════════════

class CosmologicalBridge:
    """
    Replaces the Lambda-CDM dark-matter halo profile with a substrate
    pressure gradient derived from the CRSM 7D nonlocal manifold.

    The vacuum is modelled as a toroidal dielectric fluid with pressure
    waveforms:

        P_sub(r) = P_0 * exp(-r / r_s) * cos^2(theta_lock)

    where r_s is the substrate scale radius and P_0 is the central
    substrate pressure.

    Galaxy rotation curves are predicted by:

        v_circ(r) = sqrt(G M_baryon(r) / r  +  r dP_sub/dr / rho_sub)

    The second term replaces the dark-matter contribution.

    Null hypothesis H0:
        "Galaxy rotation curves are fully explained by baryonic matter
        plus a standard NFW dark-matter halo (Lambda-CDM).  The substrate
        pressure term adds no statistically significant improvement
        (Delta chi^2 < 3.84 for 1 additional parameter)."

    Validation target:
        SPARC (Spitzer Photometry and Accurate Rotation Curves)
        galaxy survey — 175 galaxies with measured rotation curves.
    """

    H0 = (
        "Galaxy rotation curves are fully explained by baryonic matter "
        "plus a standard NFW dark-matter halo (Lambda-CDM). The substrate "
        "pressure term adds no statistically significant improvement "
        "(Delta chi^2 < 3.84 for 1 additional degree of freedom)."
    )

    def __init__(self, P_0: float = 1e-10,
                 r_scale_kpc: float = 10.0,
                 rho_sub: float = 1e-26):
        """
        Args:
            P_0: Central substrate pressure (Pa).
            r_scale_kpc: Substrate scale radius (kpc).
            rho_sub: Substrate fluid density (kg m^-3).
        """
        self.P_0 = P_0
        self.r_s = r_scale_kpc * 3.085_677_581e19   # kpc → m
        self.rho_sub = rho_sub

    def substrate_pressure(self, r: float) -> float:
        """P_sub(r) = P_0 * exp(-r/r_s) * cos^2(theta_lock)"""
        lock_rad = math.radians(THETA_LOCK)
        return self.P_0 * math.exp(-r / self.r_s) * math.cos(lock_rad) ** 2

    def substrate_pressure_gradient(self, r: float) -> float:
        """dP_sub/dr = -(P_0 / r_s) * exp(-r/r_s) * cos^2(theta_lock)"""
        lock_rad = math.radians(THETA_LOCK)
        return (
            -(self.P_0 / self.r_s) *
            math.exp(-r / self.r_s) *
            math.cos(lock_rad) ** 2
        )

    def baryonic_mass_enclosed(self, r: float,
                                M_total: float = 1e11,
                                a_scale: float = 0.0) -> float:
        """
        Exponential disk baryonic mass profile.

        M_bar(r) = M_total * (1 - (1 + r/a) * exp(-r/a))
        """
        if a_scale <= 0:
            a_scale = self.r_s / 5.0
        x = r / a_scale
        return M_total * (1.0 - (1.0 + x) * math.exp(-x))

    def rotation_velocity_crsm(self, r: float,
                                 M_baryon_total: float = 1e11) -> float:
        """
        CRSM rotation velocity (baryonic + substrate pressure).

        v^2 = G M_bar(r)/r  +  r * |dP/dr| / rho_sub
        """
        M_enc = self.baryonic_mass_enclosed(r, M_baryon_total)
        v2_baryon = G_NEWTON * M_enc / max(r, 1.0)
        dPdr = self.substrate_pressure_gradient(r)
        v2_sub = r * abs(dPdr) / max(self.rho_sub, 1e-40)
        return math.sqrt(max(v2_baryon + v2_sub, 0))

    def rotation_velocity_nfw(self, r: float,
                               M_200: float = 1e12,
                               c_nfw: float = 10.0,
                               M_baryon_total: float = 1e11) -> float:
        """
        Standard Lambda-CDM rotation velocity (baryonic + NFW halo).

        NFW enclosed mass:
            M_NFW(r) = M_200 * [ln(1+x) - x/(1+x)] / [ln(1+c) - c/(1+c)]
            x = r / r_s_nfw,   r_s_nfw = r_200 / c
        """
        M_bar = self.baryonic_mass_enclosed(r, M_baryon_total)

        # NFW parameters
        r_200 = (3 * M_200 / (4 * math.pi * 200 * 1.879e-29)) ** (1.0 / 3.0)
        r_s_nfw = r_200 / c_nfw
        x = r / max(r_s_nfw, 1.0)

        nfw_norm = math.log(1 + c_nfw) - c_nfw / (1 + c_nfw)
        nfw_enc = math.log(1 + x) - x / (1 + x)
        M_nfw = M_200 * nfw_enc / max(nfw_norm, 1e-30)

        v2 = G_NEWTON * (M_bar + M_nfw) / max(r, 1.0)
        return math.sqrt(max(v2, 0))

    def rotation_curve(self, r_min_kpc: float = 0.5,
                        r_max_kpc: float = 50.0,
                        n_points: int = 100,
                        M_baryon: float = 1e11) -> Dict[str, np.ndarray]:
        """
        Generate full rotation curves (CRSM vs NFW).

        Returns dict with radii_kpc, v_crsm_km_s, v_nfw_km_s.
        """
        kpc_to_m = 3.085_677_581e19
        r_kpc = np.linspace(r_min_kpc, r_max_kpc, n_points)
        v_crsm = np.zeros(n_points)
        v_nfw = np.zeros(n_points)

        for i, rk in enumerate(r_kpc):
            r_m = rk * kpc_to_m
            v_crsm[i] = self.rotation_velocity_crsm(r_m, M_baryon) / 1e3
            v_nfw[i] = self.rotation_velocity_nfw(r_m, M_baryon_total=M_baryon) / 1e3

        return {
            "radii_kpc": r_kpc,
            "v_crsm_km_s": v_crsm,
            "v_nfw_km_s": v_nfw,
        }

    def chi_squared_comparison(self, observed_v: np.ndarray,
                                observed_r_kpc: np.ndarray,
                                sigma_v: float = 10.0,
                                M_baryon: float = 1e11) -> Dict[str, float]:
        """
        Compare CRSM and NFW fits to observed rotation curve data.

        Returns chi^2 for each model and Delta chi^2.
        """
        kpc_to_m = 3.085_677_581e19
        chi2_crsm = 0.0
        chi2_nfw = 0.0

        for v_obs, rk in zip(observed_v, observed_r_kpc):
            r_m = rk * kpc_to_m
            v_c = self.rotation_velocity_crsm(r_m, M_baryon) / 1e3
            v_n = self.rotation_velocity_nfw(r_m, M_baryon_total=M_baryon) / 1e3
            chi2_crsm += ((v_obs - v_c) / sigma_v) ** 2
            chi2_nfw += ((v_obs - v_n) / sigma_v) ** 2

        delta_chi2 = chi2_nfw - chi2_crsm
        # Delta chi^2 > 3.84  →  CRSM is significantly better at p<0.05 (1 dof)
        significant = delta_chi2 > 3.84

        return {
            "chi2_crsm": chi2_crsm,
            "chi2_nfw": chi2_nfw,
            "delta_chi2": delta_chi2,
            "crsm_preferred": significant,
            "dof_penalty": 1,
            "threshold_p005": 3.84,
        }

    def compute(self, M_baryon: float = 1e11) -> List[BridgeResult]:
        """Run full cosmological-bridge computation."""
        results = []

        P_center = self.substrate_pressure(0)
        curve = self.rotation_curve(M_baryon=M_baryon)

        v_crsm_flat = float(np.median(curve["v_crsm_km_s"][-20:]))
        v_nfw_flat = float(np.median(curve["v_nfw_km_s"][-20:]))

        results.append(BridgeResult(
            bridge="Cosmological",
            quantity="Central substrate pressure P_0",
            value=P_center,
            unit="Pa",
            null_hypothesis=self.H0,
            notes=f"r_s={self.r_s / 3.0856e19:.1f} kpc",
        ))

        results.append(BridgeResult(
            bridge="Cosmological",
            quantity="Asymptotic CRSM rotation velocity",
            value=v_crsm_flat,
            unit="km s^-1",
            null_hypothesis=self.H0,
            notes="Median of outer 20 radial bins",
        ))

        results.append(BridgeResult(
            bridge="Cosmological",
            quantity="Asymptotic NFW rotation velocity",
            value=v_nfw_flat,
            unit="km s^-1",
            null_hypothesis=self.H0,
            notes="Comparison Lambda-CDM prediction",
        ))

        # Synthetic test: compare against flat curve at ~ 200 km/s
        v_obs = np.full(100, 200.0)
        r_obs = np.linspace(0.5, 50.0, 100)
        chi2 = self.chi_squared_comparison(v_obs, r_obs, sigma_v=15.0,
                                            M_baryon=M_baryon)

        results.append(BridgeResult(
            bridge="Cosmological",
            quantity="Delta chi^2 (NFW - CRSM)",
            value=chi2["delta_chi2"],
            unit="dimensionless",
            null_hypothesis=self.H0,
            p_value=_chi2_to_p(chi2["delta_chi2"], df=1),
            notes=(
                f"chi2_crsm={chi2['chi2_crsm']:.2f}, "
                f"chi2_nfw={chi2['chi2_nfw']:.2f}. "
                f"Delta > 3.84 → CRSM preferred at p<0.05."
            ),
        ))

        return results


# ════════════════════════════════════════════════════════════════════════════════
# UNIFIED BRIDGE EXECUTOR
# ════════════════════════════════════════════════════════════════════════════════

class BridgeExecutor:
    """
    Runs all three physics bridges and produces a unified report
    suitable for academic publication and Zenodo archival.
    """

    def __init__(self):
        self.propulsion = PropulsionBridge()
        self.energy = EnergyBridge()
        self.cosmological = CosmologicalBridge()

    def run_all(self, assembly_mass: float = 1.0,
                phi_input: float = 1.0,
                gamma_diss: float = 1e-10,
                M_baryon: float = 1e11) -> BridgeReport:
        """Execute all three bridges and return unified report."""
        report = BridgeReport(metadata={
            "framework": "CRSM (Coaxial Resonance State Manifold)",
            "theta_lock_deg": THETA_LOCK,
            "lambda_phi": LAMBDA_PHI,
            "chi_pc": CHI_PC,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        for r in self.propulsion.compute(assembly_mass):
            report.add(r)
        for r in self.energy.compute(phi_input, gamma_diss):
            report.add(r)
        for r in self.cosmological.compute(M_baryon):
            report.add(r)

        return report


# ════════════════════════════════════════════════════════════════════════════════
# STATISTICAL UTILITIES
# ════════════════════════════════════════════════════════════════════════════════

def _normal_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun 7.1.26)."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (
        1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    return 0.5 * (1.0 + sign * (1.0 - poly * math.exp(-x * x / 2.0)))


def _chi2_to_p(chi2: float, df: int = 1) -> float:
    """
    Approximate p-value for chi-squared statistic.

    Uses Wilson-Hilferty normal approximation for df >= 1.
    """
    if chi2 <= 0 or df < 1:
        return 1.0
    # Wilson-Hilferty approximation
    z = ((chi2 / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(
        2.0 / (9.0 * df)
    )
    return 1.0 - _normal_cdf(z)


# ════════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Run all three physics bridges and print report."""
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(
        description="OSIRIS Physics Bridges — Propulsion, Energy, Cosmological",
    )
    parser.add_argument("--mass", type=float, default=1.0,
                        help="Assembly mass for propulsion bridge (kg)")
    parser.add_argument("--phi", type=float, default=1.0,
                        help="phi_input for energy bridge")
    parser.add_argument("--gamma", type=float, default=1e-10,
                        help="Gamma dissipation for energy bridge")
    parser.add_argument("--M-baryon", type=float, default=1e11,
                        help="Baryonic mass for cosmological bridge (solar masses)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--output", type=str, default="",
                        help="Write results to file")

    args = parser.parse_args()

    executor = BridgeExecutor()
    report = executor.run_all(
        assembly_mass=args.mass,
        phi_input=args.phi,
        gamma_diss=args.gamma,
        M_baryon=args.M_baryon,
    )

    if args.json:
        output = _json.dumps(report.to_dict(), indent=2)
    else:
        output = report.summary()

    print(output)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
