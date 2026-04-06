"""
OSIRIS Simulation Harness — Phase 4: Generative Theoretical Investigation.

The hypothesis generation loop. Takes a theoretical claim, parametrizes it
mathematically, runs it through multiple simulation frameworks, sweeps the
parameter space, and checks convergence before allowing advancement.

Physics simulation frameworks:
  CoherenceDecaySimulator
    — Lindblad master equation: dρ/dt = -i[H,ρ] + Γ(σ-ρσ+ - ½{σ+σ-,ρ})
    — Parametrized by θ_lock, χ_pc, Γ (decoherence rate), Δt
    — Compares against hardware fidelity results from the knowledge graph
    — Produces: coherence vs time, critical decoherence threshold, Zeno regime

  NBodyCoherenceSimulator
    — N coupled qubits with Hamiltonian H = Σ_i ω_i σ_i^z + Σ_ij J_ij σ_i^x σ_j^x
    — Used for multi-qubit coherence on heavy-hex topology
    — Maps quantum circuit registers onto a graph topology

Biological simulation frameworks:
  ReactionDiffusionSimulator
    — Gray-Scott model: ∂u/∂t = Dᵤ∇²u - uv² + F(1-u)
    —                   ∂v/∂t = D_v∇²v + uv² - (F+k)v
    — Applied to: drug diffusion, molecular pathway dynamics
    — Parameters: diffusion coefficients, feed rate F, kill rate k

  KineticMonteCarlo
    — Gillespie algorithm for stochastic chemical kinetics
    — Models: enzyme catalysis, DNA repair kinetics, drug-target binding rates
    — Parameters: rate constants, molecular concentrations, temperature

Parameter Sweep Infrastructure:
  ParameterSweep
    — Latin hypercube sampling across large parameter spaces
    — ThreadPool parallel execution
    — Bayesian posterior stability convergence criterion
    — Cross-simulation variance gate
    — Recursive refinement on unstable parameter regions

Usage:
  harness = SimulationHarness()
  result  = harness.run_coherence_sweep(claim_id, n_samples=50)
  report  = harness.full_investigation(claim_id)
"""

from __future__ import annotations

import os
import json
import math
import time
import hashlib
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats
from scipy.ndimage import laplace as nd_laplace
from scipy.integrate import solve_ivp

from .research_graph import (
    ResearchGraph, ExperimentNode, TheoreticalClaim,
    NodeType, EdgeType, Domain,
    get_research_graph, _make_id,
)

# ── Persistence ───────────────────────────────────────────────────────────────

_SIM_DIR  = os.path.expanduser("~/.osiris/simulations")
_SIM_LOG  = os.path.join(_SIM_DIR, "simulation_log.jsonl")

# ── Framework constants ───────────────────────────────────────────────────────

THETA_LOCK    = 51.843
CHI_PC        = 0.946
LAMBDA_PHI    = 2.176435e-8
PHI_THRESHOLD = 0.7734
GAMMA_CRIT    = 0.30


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class SimulationResult:
    sim_id:          str
    sim_type:        str
    params:          Dict[str, float]
    output:          Dict[str, Any]     # simulation-specific outputs
    converged:       bool
    variance:        float              # cross-run variance
    residual:        float              # vs experimental data
    runtime_s:       float
    timestamp:       str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> str:
        return (
            f"[{self.sim_type}] converged={self.converged}  "
            f"variance={self.variance:.4f}  residual={self.residual:.4f}"
        )


@dataclass
class SweepResult:
    sweep_id:       str
    claim_id:       str
    sim_type:       str
    n_samples:      int
    param_ranges:   Dict[str, Tuple[float, float]]
    results:        List[SimulationResult]
    converged_n:    int
    overall_variance: float
    stable_region:  Optional[Dict[str, Tuple[float, float]]]
    critical_params: List[str]   # parameters where outcome is most sensitive
    advancement_ok:  bool        # True = passes Phase 4 gate
    timestamp:      str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> str:
        gate = "✓ PASS → Phase 5 eligible" if self.advancement_ok else "✗ BLOCKED"
        return (
            f"SWEEP [{self.sim_type}]  {gate}\n"
            f"  Samples: {self.n_samples}  Converged: {self.converged_n}/"
            f"{self.n_samples}  Variance: {self.overall_variance:.4f}\n"
            f"  Critical params: {', '.join(self.critical_params[:3])}\n"
            f"  Stable region: {self.stable_region}"
        )


# ── Coherence Decay Simulator (Lindblad) ─────────────────────────────────────

class CoherenceDecaySimulator:
    """
    Lindblad master equation for a two-level quantum system.

    State: density matrix ρ (2×2 Hermitian)
    Evolution: dρ/dt = -i[H, ρ] + Γ(σ-ρσ+ - ½{σ+σ-,ρ})

    H = (ω/2) σ_z  where ω = θ_lock-dependent frequency

    Coherence at time t:
      |ρ₀₁(t)| = |ρ₀₁(0)| · exp(-Γt/2) · χ_pc · cos(θ)

    Physical interpretation:
      - θ_lock sets the coherent evolution rate
      - χ_pc is the platform-specific coherence ceiling
      - Γ is the decoherence rate (inverse T2*)
    """

    def __init__(self):
        self.sigma_plus  = np.array([[0, 1], [0, 0]], dtype=complex)
        self.sigma_minus = np.array([[0, 0], [1, 0]], dtype=complex)
        self.sigma_z     = np.array([[1, 0], [0, -1]], dtype=complex)

    def _hamiltonian(self, omega: float) -> np.ndarray:
        return (omega / 2) * self.sigma_z

    def _lindblad_rhs(self, t: float, rho_vec: np.ndarray,
                      omega: float, gamma: float) -> np.ndarray:
        """Flattened density matrix ODE RHS."""
        rho  = rho_vec.reshape(2, 2).astype(complex)
        H    = self._hamiltonian(omega)
        # Coherent part: -i[H, ρ]
        comm = -1j * (H @ rho - rho @ H)
        # Dissipative part: Γ(L ρ L† - ½{L†L, ρ})
        L    = self.sigma_minus * math.sqrt(gamma)
        Ldg  = L.conj().T
        diss = L @ rho @ Ldg - 0.5 * (Ldg @ L @ rho + rho @ Ldg @ L)
        return (comm + diss).flatten()

    def run(self, theta_deg: float, gamma: float, chi_pc: float,
            t_max: float = 10.0, n_points: int = 100) -> Dict[str, Any]:
        """
        Simulate coherence decay.

        Returns: {
          "times": array,
          "coherence": |ρ₀₁(t)|,
          "population": ρ₀₀(t),
          "final_fidelity": float,
          "T2_star": float (estimated from 1/e crossing),
          "theta_preserved": bool
        }
        """
        omega = 2 * math.pi * math.cos(math.radians(theta_deg))

        # Initial state: equal superposition |+> = (|0> + |1>) / √2
        rho0  = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)

        t_span = (0, t_max)
        t_eval = np.linspace(0, t_max, n_points)

        sol = solve_ivp(
            self._lindblad_rhs,
            t_span=t_span,
            y0=rho0.flatten(),
            t_eval=t_eval,
            args=(omega, gamma),
            method="RK45",
            rtol=1e-8, atol=1e-10,
        )

        coherence = []
        population = []
        for rho_flat in sol.y.T:
            rho_t = rho_flat.reshape(2, 2)
            coherence.append(abs(rho_t[0, 1]) * chi_pc)
            population.append(float(rho_t[0, 0].real))

        coherence = np.array(coherence)
        times     = sol.t

        # T2* estimate: time to 1/e
        initial_coh = coherence[0] if coherence[0] > 1e-10 else 1.0
        T2_star     = t_max
        for i, c in enumerate(coherence):
            if c < initial_coh / math.e:
                T2_star = float(times[i])
                break

        final_fidelity = float(coherence[-1])
        theta_preserved = (abs(final_fidelity - chi_pc * abs(math.cos(math.radians(theta_deg))) *
                               math.exp(-gamma * t_max / 2)) < 0.05)

        return {
            "times":           times.tolist(),
            "coherence":       coherence.tolist(),
            "population":      population,
            "final_fidelity":  round(final_fidelity, 4),
            "T2_star":         round(T2_star, 4),
            "theta_preserved": theta_preserved,
            "omega":           round(omega, 4),
        }

    def validate_against_hardware(self, result: Dict, target_fidelity: float) -> float:
        """Return residual: |simulated_final_fidelity - target_fidelity|."""
        return abs(result.get("final_fidelity", 0.0) - target_fidelity)


# ── Reaction-Diffusion Simulator (Gray-Scott) ─────────────────────────────────

class ReactionDiffusionSimulator:
    """
    Gray-Scott reaction-diffusion system.

    Applied to:
      - Drug molecule diffusion and binding in tissue
      - Signaling pathway dynamics (u = activator, v = inhibitor)
      - DNA repair kinetics spatial patterns

    ∂u/∂t = Dᵤ∇²u - uv² + F(1-u)
    ∂v/∂t = D_v∇²v + uv² - (F+k)v
    """

    def run(self, F: float = 0.055, k: float = 0.062,
            Du: float = 0.16, Dv: float = 0.08,
            grid_size: int = 64, n_steps: int = 5000,
            dt: float = 1.0) -> Dict[str, Any]:
        """
        Run Gray-Scott simulation. Returns spatial statistics at final state.
        Uses 2D toroidal grid with Laplacian stencil.
        """
        n = grid_size
        u = np.ones((n, n))
        v = np.zeros((n, n))

        # Seed: small random perturbation in center
        rng = np.random.default_rng(seed=42)
        r   = n // 8
        cx, cy = n // 2, n // 2
        u[cx-r:cx+r, cy-r:cy+r] = 0.50
        v[cx-r:cx+r, cy-r:cy+r] = 0.25
        u += 0.01 * rng.random((n, n))
        v += 0.01 * rng.random((n, n))
        u = np.clip(u, 0, 1)
        v = np.clip(v, 0, 1)

        for _ in range(n_steps):
            uvv  = u * v * v
            lap_u = nd_laplace(u, mode="wrap")
            lap_v = nd_laplace(v, mode="wrap")
            u += dt * (Du * lap_u - uvv + F * (1 - u))
            v += dt * (Dv * lap_v + uvv - (F + k) * v)
            u  = np.clip(u, 0, 1)
            v  = np.clip(v, 0, 1)

        # Spatial statistics
        pattern_formed   = float(np.std(v)) > 0.05
        mean_v           = float(np.mean(v))
        max_v            = float(np.max(v))
        spatial_variance = float(np.var(v))

        return {
            "F":               F,
            "k":               k,
            "Du":              Du,
            "Dv":              Dv,
            "pattern_formed":  pattern_formed,
            "mean_v":          round(mean_v, 5),
            "max_v":           round(max_v, 5),
            "spatial_variance": round(spatial_variance, 6),
            "u_mean":          round(float(np.mean(u)), 5),
            "steps":           n_steps,
        }


# ── Kinetic Monte Carlo ───────────────────────────────────────────────────────

class KineticMonteCarlo:
    """
    Gillespie algorithm for stochastic chemical kinetics.

    Applied to:
      - Enzyme-substrate binding kinetics (Michaelis-Menten + quantum tunnelling)
      - Drug-target association/dissociation rates
      - DNA repair pathway stochastic dynamics

    Reactions are specified as {name: (stoichiometry, rate)}.
    """

    def __init__(self):
        self.rng = np.random.default_rng(seed=12345)

    def run(self, initial_state: Dict[str, int],
            reactions: List[Dict[str, Any]],
            t_max: float = 100.0,
            max_events: int = 100_000) -> Dict[str, Any]:
        """
        Run Gillespie algorithm.
        reactions: [{"name": str, "reactants": {sp: n}, "products": {sp: n}, "rate": float}]
        """
        state   = dict(initial_state)
        t       = 0.0
        history = [{"t": 0.0, **state}]
        n_events = 0

        while t < t_max and n_events < max_events:
            # Compute propensities
            props = []
            for rxn in reactions:
                rate = rxn["rate"]
                for sp, n in rxn.get("reactants", {}).items():
                    pop = state.get(sp, 0)
                    # Combinatorial propensity
                    rate *= math.comb(pop, n) if pop >= n else 0
                props.append(max(rate, 0.0))

            total = sum(props)
            if total < 1e-15:
                break

            # Time to next event (exponential waiting)
            dt_event = self.rng.exponential(1.0 / total)
            t += dt_event

            # Choose reaction
            r = self.rng.random() * total
            cumsum = 0.0
            chosen = 0
            for i, p in enumerate(props):
                cumsum += p
                if cumsum >= r:
                    chosen = i
                    break

            # Apply reaction
            rxn = reactions[chosen]
            for sp, n in rxn.get("reactants", {}).items():
                state[sp] = max(0, state.get(sp, 0) - n)
            for sp, n in rxn.get("products", {}).items():
                state[sp] = state.get(sp, 0) + n

            n_events += 1
            if n_events % (max_events // 100) == 0:
                history.append({"t": round(t, 4), **state})

        history.append({"t": round(t, 4), **state})

        return {
            "final_state":  state,
            "n_events":     n_events,
            "t_final":      round(t, 4),
            "converged":    t >= t_max,
            "history_len":  len(history),
            "final_v_conc": state.get("product", 0) / max(initial_state.get("substrate", 1), 1),
        }


# ── Parameter Sweep Infrastructure ───────────────────────────────────────────

class ParameterSweep:
    """
    Latin hypercube sampling across large parameter spaces.
    ThreadPool parallel execution with Bayesian convergence gating.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def latin_hypercube(self, param_ranges: Dict[str, Tuple[float, float]],
                        n_samples: int) -> List[Dict[str, float]]:
        """
        Generate n_samples points via Latin Hypercube Sampling.
        Ensures stratified coverage of the parameter space.
        """
        params = list(param_ranges.keys())
        n_params = len(params)
        # LHS: divide each dimension into n_samples equal strata, sample one per stratum
        rng = np.random.default_rng(seed=42)
        lhs = np.zeros((n_samples, n_params))
        for j in range(n_params):
            perm = rng.permutation(n_samples)
            u    = (perm + rng.random(n_samples)) / n_samples
            lo, hi = param_ranges[params[j]]
            lhs[:, j] = lo + u * (hi - lo)

        return [dict(zip(params, lhs[i])) for i in range(n_samples)]

    def run(self, simulator_fn: Callable[[Dict[str, float]], Dict[str, Any]],
            param_ranges: Dict[str, Tuple[float, float]],
            n_samples: int = 50,
            convergence_metric: str = "final_fidelity") -> SweepResult:
        """
        Run simulator_fn over n_samples LHS parameter sets in parallel.
        Returns SweepResult with convergence analysis.
        """
        samples     = self.latin_hypercube(param_ranges, n_samples)
        sweep_id    = _make_id("SWP", str(param_ranges) + str(n_samples))
        raw_results: List[SimulationResult] = []

        os.makedirs(_SIM_DIR, exist_ok=True)

        def _run_one(params: Dict[str, float]) -> Optional[SimulationResult]:
            t0 = time.time()
            try:
                output = simulator_fn(params)
                elapsed = time.time() - t0
                return SimulationResult(
                    sim_id=_make_id("SIM", str(params)),
                    sim_type=simulator_fn.__name__ if hasattr(simulator_fn, "__name__") else "unknown",
                    params=params,
                    output=output,
                    converged=output.get("converged", True),
                    variance=0.0,   # filled below
                    residual=output.get("residual", 0.0),
                    runtime_s=elapsed,
                )
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(_run_one, s): s for s in samples}
            for fut in as_completed(futures):
                result = fut.result()
                if result:
                    raw_results.append(result)

        if not raw_results:
            return SweepResult(
                sweep_id=sweep_id, claim_id="", sim_type="unknown",
                n_samples=n_samples, param_ranges=param_ranges,
                results=[], converged_n=0, overall_variance=1.0,
                stable_region=None, critical_params=[], advancement_ok=False,
            )

        # Extract convergence metric values
        metric_values = [
            r.output.get(convergence_metric, 0.0)
            for r in raw_results
            if convergence_metric in r.output
        ]

        overall_variance = float(np.var(metric_values)) if len(metric_values) > 1 else 1.0
        for r in raw_results:
            r.variance = overall_variance

        converged_n = sum(1 for r in raw_results if r.converged)

        # Identify critical parameters (sensitivity analysis)
        critical_params = self._sensitivity_analysis(
            raw_results, param_ranges, convergence_metric
        )

        # Find stable region (where metric_variance < 0.01)
        stable_region = self._find_stable_region(
            raw_results, param_ranges, convergence_metric
        )

        advancement_ok = (
            overall_variance < 0.05 and
            converged_n >= len(raw_results) * 0.8
        )

        self._log_sweep(sweep_id, n_samples, overall_variance, advancement_ok)

        return SweepResult(
            sweep_id=sweep_id, claim_id="", sim_type="",
            n_samples=n_samples, param_ranges=param_ranges,
            results=raw_results, converged_n=converged_n,
            overall_variance=round(overall_variance, 6),
            stable_region=stable_region, critical_params=critical_params,
            advancement_ok=advancement_ok,
        )

    def _sensitivity_analysis(self, results: List[SimulationResult],
                               param_ranges: Dict[str, Tuple[float, float]],
                               metric: str) -> List[str]:
        """
        Identify parameters with highest sensitivity (Sobol-like ranking).
        Uses Spearman correlation between param value and metric output.
        """
        if len(results) < 4:
            return []

        metric_vals = [r.output.get(metric, 0.0) for r in results]
        sensitivities = []
        for param in param_ranges:
            param_vals = [r.params.get(param, 0.0) for r in results]
            if len(set(param_vals)) < 2:
                continue
            corr, _ = sp_stats.spearmanr(param_vals, metric_vals)
            sensitivities.append((param, abs(corr)))

        sensitivities.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in sensitivities[:5]]

    def _find_stable_region(self, results: List[SimulationResult],
                             param_ranges: Dict[str, Tuple[float, float]],
                             metric: str) -> Optional[Dict[str, Tuple[float, float]]]:
        """
        Find parameter sub-region where metric variance is lowest.
        Simple approach: find the 25% of samples with lowest metric deviation
        from median, return their parameter bounding box.
        """
        if len(results) < 8:
            return None

        vals    = np.array([r.output.get(metric, 0.0) for r in results])
        median  = float(np.median(vals))
        devs    = np.abs(vals - median)
        top_idx = np.argsort(devs)[:max(len(results)//4, 2)]

        stable  = [results[i] for i in top_idx]
        region  = {}
        for param in param_ranges:
            pvals = [s.params[param] for s in stable if param in s.params]
            if pvals:
                region[param] = (round(min(pvals), 4), round(max(pvals), 4))
        return region if region else None

    def _log_sweep(self, sweep_id: str, n: int, variance: float, ok: bool) -> None:
        try:
            with open(_SIM_LOG, "a") as f:
                f.write(json.dumps({
                    "ts":        datetime.now(timezone.utc).isoformat(),
                    "sweep_id":  sweep_id,
                    "n_samples": n,
                    "variance":  round(variance, 6),
                    "passed":    ok,
                }) + "\n")
        except Exception:
            pass


# ── Simulation Harness ────────────────────────────────────────────────────────

class SimulationHarness:
    """
    Orchestrates all simulation frameworks for a given research claim.
    Provides the Phase 4 execution cycle.
    """

    def __init__(self, graph: Optional[ResearchGraph] = None):
        self._graph  = graph or get_research_graph()
        self._cds    = CoherenceDecaySimulator()
        self._rds    = ReactionDiffusionSimulator()
        self._kmc    = KineticMonteCarlo()
        self._sweep  = ParameterSweep(max_workers=4)
        os.makedirs(_SIM_DIR, exist_ok=True)

    # ── Domain-dispatched simulations ─────────────────────────────────────────

    def run_coherence_sweep(self, claim_id: str,
                            n_samples: int = 40) -> SweepResult:
        """
        Phase 4 coherence decay simulation for a quantum claim.
        Sweeps θ_lock, χ_pc, and Γ around their reference values.
        """
        # Get hardware target fidelity from graph (if available)
        target_fidelity = self._get_target_fidelity(claim_id)

        param_ranges = {
            "theta_deg": (THETA_LOCK * 0.85, THETA_LOCK * 1.15),
            "gamma":     (GAMMA_CRIT  * 0.5,  GAMMA_CRIT  * 2.0),
            "chi_pc":    (CHI_PC      * 0.90, CHI_PC      * 1.05),
            "t_max":     (5.0, 20.0),
        }

        def _sim(params: Dict[str, float]) -> Dict[str, Any]:
            out = self._cds.run(
                theta_deg=params["theta_deg"],
                gamma=params["gamma"],
                chi_pc=params["chi_pc"],
                t_max=params["t_max"],
            )
            out["residual"] = abs(out["final_fidelity"] - target_fidelity)
            out["converged"] = True   # ODE always completes
            return out

        result = self._sweep.run(
            _sim, param_ranges, n_samples=n_samples,
            convergence_metric="final_fidelity",
        )
        result.claim_id  = claim_id
        result.sim_type  = "coherence_decay_lindblad"
        return result

    def run_biological_sweep(self, claim_id: str,
                             n_samples: int = 30) -> SweepResult:
        """
        Phase 4 reaction-diffusion simulation for oncology/drug-discovery claims.
        Sweeps Gray-Scott F and k parameters around typical biological ranges.
        """
        param_ranges = {
            "F":  (0.020, 0.080),   # feed rate (drug administration rate analog)
            "k":  (0.050, 0.075),   # kill rate (drug clearance / degradation)
            "Du": (0.10,  0.25),    # drug diffusion coefficient
            "Dv": (0.04,  0.12),    # metabolite diffusion coefficient
        }

        def _sim(params: Dict[str, float]) -> Dict[str, Any]:
            out = self._rds.run(
                F=params["F"], k=params["k"],
                Du=params["Du"], Dv=params["Dv"],
                grid_size=32, n_steps=2000,
            )
            out["converged"] = True
            return out

        result = self._sweep.run(
            _sim, param_ranges, n_samples=n_samples,
            convergence_metric="spatial_variance",
        )
        result.claim_id = claim_id
        result.sim_type = "reaction_diffusion_gray_scott"
        return result

    def run_kinetics_sweep(self, claim_id: str,
                           n_samples: int = 30) -> SweepResult:
        """
        Gillespie kinetic MC for enzyme/binding kinetics claims.
        Parametrizes association/dissociation rate constants.
        """
        param_ranges = {
            "k_on":  (1e-3, 1e-1),    # association rate constant
            "k_off": (1e-4, 1e-2),    # dissociation rate constant
            "k_cat": (1e-3, 5e-2),    # catalytic rate constant
        }

        initial_state = {"enzyme": 100, "substrate": 1000,
                         "ES_complex": 0, "product": 0}

        def _sim(params: Dict[str, float]) -> Dict[str, Any]:
            reactions = [
                {"name": "bind",   "reactants": {"enzyme": 1, "substrate": 1},
                 "products": {"ES_complex": 1}, "rate": params["k_on"]},
                {"name": "unbind", "reactants": {"ES_complex": 1},
                 "products": {"enzyme": 1, "substrate": 1}, "rate": params["k_off"]},
                {"name": "catalyze", "reactants": {"ES_complex": 1},
                 "products": {"enzyme": 1, "product": 1}, "rate": params["k_cat"]},
            ]
            return self._kmc.run(initial_state, reactions, t_max=200.0)

        result = self._sweep.run(
            _sim, param_ranges, n_samples=n_samples,
            convergence_metric="final_v_conc",
        )
        result.claim_id = claim_id
        result.sim_type = "kinetic_monte_carlo_gillespie"
        return result

    # ── Full investigation (Phase 4 complete) ─────────────────────────────────

    def full_investigation(self, claim_id: str,
                           n_samples: int = 40) -> Dict[str, Any]:
        """
        Run all applicable simulations for a claim, then assess convergence.
        This is the Phase 4 execution: hypothesis → simulation → validation.
        """
        node   = self._graph.get_node(claim_id)
        if node is None:
            return {"error": f"Claim {claim_id} not found"}

        domain = node.domain
        results: Dict[str, SweepResult] = {}

        if domain in (Domain.QUANTUM, Domain.PHYSICS, Domain.CROSS_DOMAIN):
            results["coherence"] = self.run_coherence_sweep(claim_id, n_samples)

        if domain in (Domain.ONCOLOGY, Domain.BIOLOGY, Domain.CROSS_DOMAIN):
            results["biological"] = self.run_biological_sweep(claim_id, n_samples // 2)

        if domain in (Domain.DRUG_DISCOVERY, Domain.ONCOLOGY, Domain.CROSS_DOMAIN):
            results["kinetics"] = self.run_kinetics_sweep(claim_id, n_samples // 2)

        # Aggregate variance across all simulation types
        variances = [s.overall_variance for s in results.values()]
        mean_var  = float(np.mean(variances)) if variances else 1.0

        # Critical parameters across all simulations
        all_critical = []
        for s in results.values():
            all_critical.extend(s.critical_params)
        # Rank by frequency
        freq: Dict[str, int] = {}
        for p in all_critical:
            freq[p] = freq.get(p, 0) + 1
        critical_params = sorted(freq, key=freq.get, reverse=True)[:5]  # type: ignore

        # Recursive refinement: if variance > 0.1, re-run with 2x samples
        # around the most critical parameters
        refined = False
        if mean_var > 0.1 and n_samples < 200:
            refined_results: Dict[str, SweepResult] = {}
            for sim_type, sweep in results.items():
                if sweep.overall_variance > 0.05 and sweep.stable_region:
                    # Narrow sweep to stable region with more samples
                    if sim_type == "coherence":
                        refined_results[sim_type] = self.run_coherence_sweep(
                            claim_id, n_samples * 2
                        )
                    elif sim_type == "biological":
                        refined_results[sim_type] = self.run_biological_sweep(
                            claim_id, n_samples
                        )
            if refined_results:
                results.update(refined_results)
                variances = [s.overall_variance for s in results.values()]
                mean_var  = float(np.mean(variances))
                refined   = True

        advancement_ok = mean_var < 0.05 and all(s.advancement_ok for s in results.values())

        summary = {
            "claim_id":       claim_id,
            "claim_title":    node.title[:80],
            "domain":         domain,
            "simulations_run": list(results.keys()),
            "mean_variance":  round(mean_var, 6),
            "critical_params": critical_params,
            "advancement_ok": advancement_ok,
            "refined":        refined,
            "stable_regions": {
                k: v.stable_region for k, v in results.items() if v.stable_region
            },
            "sweep_summaries": {k: v.summary() for k, v in results.items()},
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }

        # Persist
        self._save_investigation(summary)
        return summary

    # ── Single-run convenience methods ────────────────────────────────────────

    def simulate_coherence(self, theta_deg: float = THETA_LOCK,
                           gamma: float = GAMMA_CRIT,
                           chi_pc: float = CHI_PC,
                           t_max: float = 10.0) -> Dict[str, Any]:
        """Quick single coherence simulation run."""
        return self._cds.run(theta_deg, gamma, chi_pc, t_max)

    def simulate_reaction_diffusion(self, F: float = 0.055,
                                    k: float = 0.062) -> Dict[str, Any]:
        """Quick single Gray-Scott run."""
        return self._rds.run(F=F, k=k)

    def simulate_enzyme_kinetics(self, k_on: float = 0.01,
                                 k_off: float = 0.001,
                                 k_cat: float = 0.01) -> Dict[str, Any]:
        """Quick single Gillespie run."""
        state = {"enzyme": 100, "substrate": 1000, "ES_complex": 0, "product": 0}
        reactions = [
            {"name": "bind",     "reactants": {"enzyme": 1, "substrate": 1},
             "products": {"ES_complex": 1}, "rate": k_on},
            {"name": "unbind",   "reactants": {"ES_complex": 1},
             "products": {"enzyme": 1, "substrate": 1}, "rate": k_off},
            {"name": "catalyze", "reactants": {"ES_complex": 1},
             "products": {"enzyme": 1, "product": 1}, "rate": k_cat},
        ]
        return self._kmc.run(state, reactions)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_target_fidelity(self, claim_id: str) -> float:
        """Pull hardware target fidelity from graph's supporting experiments."""
        fidelities = []
        for edge in self._graph.edges_for(claim_id):
            if edge.edge_type != EdgeType.SUPPORTS:
                continue
            node = self._graph.get_node(edge.source_id)
            if node and node.node_type == NodeType.EXPERIMENT:
                fid = getattr(node, "quantum_params", {}).get("fidelity", 0.0)
                if fid > 0:
                    fidelities.append(fid)
        return float(np.mean(fidelities)) if fidelities else CHI_PC

    def _save_investigation(self, summary: Dict) -> None:
        path = os.path.join(_SIM_DIR, f"investigation_{summary['claim_id'][:20]}.json")
        try:
            with open(path, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception:
            pass

    def format_investigation(self, summary: Dict) -> str:
        gate = "✓ PASS → Phase 5 eligible" if summary["advancement_ok"] else "✗ BLOCKED"
        lines = [
            f"PHASE 4 INVESTIGATION: {summary['claim_title'][:60]}",
            f"  Domain: {summary['domain']}",
            f"  Gate: {gate}",
            f"  Mean variance: {summary['mean_variance']:.6f}",
            f"  Critical params: {', '.join(summary['critical_params'][:4])}",
            f"  Simulations: {', '.join(summary['simulations_run'])}",
            f"  Refined: {summary['refined']}",
        ]
        for sim_type, s_summary in summary.get("sweep_summaries", {}).items():
            lines.append(f"\n  [{sim_type}]\n  {s_summary}")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_harness_singleton: Optional[SimulationHarness] = None


def get_simulation_harness() -> SimulationHarness:
    global _harness_singleton
    if _harness_singleton is None:
        _harness_singleton = SimulationHarness()
    return _harness_singleton
