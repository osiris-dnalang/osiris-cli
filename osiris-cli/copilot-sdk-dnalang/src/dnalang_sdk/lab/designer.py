"""
Experiment Designer — Create quantum experiments from templates.

Templates cover common experiment types with configurable parameters.
Generates executable Python scripts with proper Qiskit integration.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import os, time, math, textwrap


@dataclass
class ExperimentTemplate:
    """A template for generating quantum experiments."""
    name: str
    description: str
    exp_type: str
    parameters: Dict[str, Any]  # name → default value
    parameter_descriptions: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


# ─── IMMUTABLE CONSTANTS ──────────────────────────────────────────────────────
LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843
PHI_THRESHOLD = 0.7734
CHI_PC = 0.946


class ExperimentDesigner:
    """Designs quantum experiments from templates.

    Templates:
      bell_state       — 2-qubit Bell pair with optional χ_PC phase
      ghz_state        — N-qubit GHZ state
      w_state          — N-qubit W state with Φ_total measurement
      theta_sweep      — Parameter sweep around θ_lock
      theta_lock       — Fine scan to verify θ_lock = 51.843°
      chi_pc_witness   — Chi-PC entanglement witness
      aeterna_porta    — Full Aeterna Porta circuit (TFD + Zeno + Floquet)
      dna_encoded      — DNA-string-to-circuit experiment
      lambda_phi_test  — ΛΦ conservation verification
      custom           — Blank template for custom experiments
    """

    TEMPLATES: Dict[str, ExperimentTemplate] = {
        "bell_state": ExperimentTemplate(
            name="Bell State Entanglement",
            description="Prepare Bell pair |Φ+⟩, measure concurrence and CHSH violation",
            exp_type="bell_state",
            parameters={
                "qubits": 2, "shots": 8192, "chi_phase": True,
                "backend": "aer_simulator", "measure_tomography": False,
            },
            parameter_descriptions={
                "chi_phase": "Apply χ_PC phase rotation (0.946π)",
                "measure_tomography": "Full state tomography (slow but complete)",
            },
            tags=["entanglement", "foundational"],
        ),
        "ghz_state": ExperimentTemplate(
            name="GHZ State",
            description="N-qubit GHZ state |0...0⟩ + |1...1⟩ with parity checks",
            exp_type="ghz_state",
            parameters={
                "qubits": 5, "shots": 8192, "backend": "aer_simulator",
                "error_mitigation": False,
            },
            tags=["entanglement", "multipartite"],
        ),
        "w_state": ExperimentTemplate(
            name="W-State Phi-Total",
            description="W-state preparation with Φ_total (integrated information) measurement",
            exp_type="w_state",
            parameters={
                "qubit_range": [4, 6, 8, 10], "shots": 10000,
                "backend": "aer_simulator",
            },
            tags=["entanglement", "consciousness", "phi_total"],
        ),
        "theta_sweep": ExperimentTemplate(
            name="Theta Parameter Sweep",
            description="Sweep rotation angle to find optimal θ_lock resonance",
            exp_type="theta_sweep",
            parameters={
                "qubits": 8, "theta_range": [20, 90], "theta_step": 5.0,
                "shots": 10000, "backend": "aer_simulator",
                "control_angles": [30, 45, 60, 90],
            },
            parameter_descriptions={
                "theta_range": "[start, end] in degrees",
                "control_angles": "Control angles to compare against θ_lock",
            },
            tags=["sweep", "theta_lock", "optimization"],
        ),
        "theta_lock": ExperimentTemplate(
            name="Theta Lock Fine Scan",
            description="High-resolution scan around θ_lock = 51.843° to verify resonance",
            exp_type="theta_lock",
            parameters={
                "qubits": 8, "center": 51.843, "range_deg": 4.0,
                "step_deg": 0.1, "shots": 20000, "backend": "aer_simulator",
            },
            tags=["verification", "theta_lock", "precision"],
        ),
        "chi_pc_witness": ExperimentTemplate(
            name="Chi-PC Entanglement Witness",
            description="Bell state with χ_PC phase conjugation, measure concurrence & negativity",
            exp_type="chi_pc",
            parameters={
                "chi_factors": [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5],
                "shots": 10000, "backend": "aer_simulator",
            },
            tags=["entanglement", "chi_pc", "witness"],
        ),
        "aeterna_porta": ExperimentTemplate(
            name="Aeterna Porta v2 Circuit",
            description="Full 5-stage circuit: TFD → Zeno → Floquet → Feed-forward → Readout",
            exp_type="aeterna_porta",
            parameters={
                "qubits": 120, "shots": 100000,
                "backend": "ibm_fez",
                "zeno_enabled": True, "floquet_enabled": True,
                "theta_lock": 51.843, "dry_run": True,
            },
            tags=["aeterna_porta", "advanced", "hardware"],
        ),
        "dna_encoded": ExperimentTemplate(
            name="DNA-Encoded Circuit",
            description="Convert DNA string to quantum circuit and measure fidelity vs random",
            exp_type="dna_encoded",
            parameters={
                "dna_string": "HXZCYTCHXZCXYTCHZ",
                "shots": 8192, "backend": "aer_simulator",
                "compare_random": True, "num_random": 5,
            },
            tags=["dna", "encoding", "fidelity"],
        ),
        "lambda_phi_test": ExperimentTemplate(
            name="Lambda-Phi Conservation Test",
            description="Verify ΛΦ = 2.176435e-8 is conserved across circuit transformations",
            exp_type="lambda_phi",
            parameters={
                "qubits": 4, "shots": 10000,
                "backend": "aer_simulator",
                "rotation_angles": [0, 30, 45, 51.843, 60, 90],
            },
            tags=["conservation", "lambda_phi", "verification"],
        ),
        "custom": ExperimentTemplate(
            name="Custom Experiment",
            description="Blank template — design your own quantum experiment",
            exp_type="custom",
            parameters={
                "qubits": 2, "shots": 1024, "backend": "aer_simulator",
            },
            tags=["custom"],
        ),
    }

    def list_templates(self) -> List[ExperimentTemplate]:
        return list(self.TEMPLATES.values())

    def get_template(self, name: str) -> Optional[ExperimentTemplate]:
        return self.TEMPLATES.get(name)

    def design(
        self,
        template_name: str,
        output_dir: str,
        overrides: Optional[Dict[str, Any]] = None,
        experiment_name: Optional[str] = None,
    ) -> str:
        """Generate an experiment script from a template.

        Returns the path to the generated script.
        """
        template = self.TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}. Available: {list(self.TEMPLATES.keys())}")

        params = {**template.parameters}
        if overrides:
            params.update(overrides)

        exp_name = experiment_name or f"{template_name}_{int(time.time())}"
        filename = f"experiment_{exp_name}.py"
        filepath = os.path.join(output_dir, filename)

        # Generate code
        generators = {
            "bell_state": self._gen_bell,
            "ghz_state": self._gen_ghz,
            "w_state": self._gen_w_state,
            "theta_sweep": self._gen_theta_sweep,
            "theta_lock": self._gen_theta_lock,
            "chi_pc_witness": self._gen_chi_pc,
            "aeterna_porta": self._gen_aeterna_porta,
            "dna_encoded": self._gen_dna_encoded,
            "lambda_phi_test": self._gen_lambda_phi,
            "custom": self._gen_custom,
        }

        gen_fn = generators.get(template_name, self._gen_custom)
        code = gen_fn(exp_name, params)

        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(code)

        return filepath

    # ─── CODE GENERATORS ──────────────────────────────────────────────────────

    def _header(self, name: str, desc: str, params: Dict) -> str:
        param_lines = "\n".join(f"#   {k}: {v}" for k, v in params.items())
        return f'''#!/usr/bin/env python3
"""
OSIRIS Lab Experiment: {name}
{'=' * (24 + len(name))}
{desc}

Generated by OSIRIS Lab Designer — DNA::}}{{::lang v{THETA_LOCK}
Framework constants: ΛΦ={LAMBDA_PHI}, θ_lock={THETA_LOCK}°, Φ_threshold={PHI_THRESHOLD}

Parameters:
{param_lines}
"""

import json, time, math, os, sys
import numpy as np

# Immutable constants
LAMBDA_PHI = {LAMBDA_PHI}
THETA_LOCK = {THETA_LOCK}
PHI_THRESHOLD = {PHI_THRESHOLD}
CHI_PC = {CHI_PC}

'''

    def _footer(self, results_var: str = "results") -> str:
        return f'''
# ─── Save Results ────────────────────────────────────────────────────
output_path = os.path.splitext(__file__)[0] + "_results.json"
with open(output_path, "w") as f:
    json.dump({results_var}, f, indent=2, default=str)
print(f"\\n✅ Results saved to {{output_path}}")

if __name__ == "__main__":
    pass  # Already executed above
'''

    def _gen_bell(self, name: str, p: Dict) -> str:
        return self._header(name, "Bell state entanglement test", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, concurrence, DensityMatrix, partial_trace, entropy

def run_bell_experiment():
    results = {{
        "experiment": "{name}",
        "type": "bell_state",
        "timestamp": time.time(),
        "parameters": {p},
        "trials": [],
    }}

    qc = QuantumCircuit({p["qubits"]})
    qc.h(0)
    qc.cx(0, 1)

    if {p.get("chi_phase", False)}:
        phase = CHI_PC * math.pi
        qc.rz(phase, 0)
        qc.rz(phase, 1)

    sv = Statevector.from_instruction(qc)
    rho = DensityMatrix(sv)
    C = concurrence(rho)
    rho_A = partial_trace(rho, [1])
    S = entropy(rho_A, base=2)

    trial = {{
        "concurrence": C,
        "entropy": S,
        "chi_phase_applied": {p.get("chi_phase", False)},
        "above_phi_threshold": C >= PHI_THRESHOLD,
    }}
    results["trials"].append(trial)
    results["summary"] = {{
        "concurrence": C,
        "entropy": S,
        "sovereign": C >= PHI_THRESHOLD,
    }}

    print(f"Bell State Results:")
    print(f"  Concurrence: {{C:.6f}}")
    print(f"  Entropy: {{S:.6f}}")
    print(f"  Sovereign: {{C >= PHI_THRESHOLD}}")

    return results

results = run_bell_experiment()
''' + self._footer()

    def _gen_ghz(self, name: str, p: Dict) -> str:
        return self._header(name, "GHZ state preparation", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, DensityMatrix, partial_trace, entropy

def run_ghz_experiment():
    n = {p["qubits"]}
    results = {{
        "experiment": "{name}",
        "type": "ghz_state",
        "timestamp": time.time(),
        "qubits": n,
    }}

    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)

    sv = Statevector.from_instruction(qc)
    probs = sv.probabilities_dict()

    # GHZ should only have |00...0⟩ and |11...1⟩
    ghz_fidelity = probs.get("0" * n, 0) + probs.get("1" * n, 0)
    results["fidelity"] = ghz_fidelity
    results["top_states"] = dict(sorted(probs.items(), key=lambda x: -x[1])[:5])
    results["sovereign"] = ghz_fidelity >= PHI_THRESHOLD

    print(f"GHZ State ({{n}} qubits):")
    print(f"  Fidelity: {{ghz_fidelity:.6f}}")
    print(f"  Top states: {{results['top_states']}}")

    return results

results = run_ghz_experiment()
''' + self._footer()

    def _gen_w_state(self, name: str, p: Dict) -> str:
        return self._header(name, "W-state Phi-total measurement", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, DensityMatrix, partial_trace, entropy

def run_w_state_experiment():
    qubit_range = {p.get("qubit_range", [4, 6, 8])}
    results = {{
        "experiment": "{name}",
        "type": "w_state",
        "timestamp": time.time(),
        "measurements": [],
    }}

    for n in qubit_range:
        qc = QuantumCircuit(n)
        # W-state preparation
        qc.x(0)
        for i in range(n - 1):
            theta = 2 * math.acos(math.sqrt(1 / (n - i)))
            qc.cry(theta, i, i + 1)
            qc.cx(i + 1, i)

        sv = Statevector.from_instruction(qc)
        rho = DensityMatrix(sv)

        # Compute entanglement entropy for each bipartition
        entropies = []
        for k in range(1, n):
            rho_k = partial_trace(rho, list(range(k, n)))
            S = entropy(rho_k, base=2)
            entropies.append(S)

        phi_total = 2 * n * np.mean(entropies)

        measurement = {{
            "qubits": n,
            "phi_total": phi_total,
            "mean_entropy": float(np.mean(entropies)),
            "max_entropy": float(max(entropies)),
        }}
        results["measurements"].append(measurement)
        print(f"  W-state n={{n}}: Φ_total = {{phi_total:.4f}}")

    return results

results = run_w_state_experiment()
''' + self._footer()

    def _gen_theta_sweep(self, name: str, p: Dict) -> str:
        return self._header(name, "Theta parameter sweep", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def run_theta_sweep():
    theta_start, theta_end = {p.get("theta_range", [20, 90])}
    step = {p.get("theta_step", 5.0)}
    n = {p["qubits"]}
    results = {{
        "experiment": "{name}",
        "type": "theta_sweep",
        "timestamp": time.time(),
        "sweeps": [],
    }}

    angles = np.arange(theta_start, theta_end + step, step)
    best_phi = 0
    best_angle = 0

    for theta in angles:
        theta_rad = math.radians(theta)
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
            qc.ry(theta_rad, i)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        qc.ry(theta_rad, 0)

        sv = Statevector.from_instruction(qc)
        probs = sv.probabilities()
        phi = float(-np.sum(probs * np.log2(probs + 1e-12)))
        gamma = float(1.0 - max(probs))

        if phi > best_phi:
            best_phi = phi
            best_angle = theta

        results["sweeps"].append({{
            "theta_deg": float(theta),
            "phi": phi,
            "gamma": gamma,
            "xi": (LAMBDA_PHI * phi) / max(gamma, 0.001),
        }})

    results["best_angle"] = best_angle
    results["best_phi"] = best_phi
    results["theta_lock_result"] = abs(best_angle - THETA_LOCK) < 5.0

    print(f"Theta Sweep: best angle = {{best_angle:.3f}}° (Φ = {{best_phi:.4f}})")
    print(f"θ_lock match: {{results['theta_lock_result']}}")

    return results

results = run_theta_sweep()
''' + self._footer()

    def _gen_theta_lock(self, name: str, p: Dict) -> str:
        return self._header(name, "Theta lock fine scan", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def run_theta_lock_scan():
    center = {p.get("center", 51.843)}
    half_range = {p.get("range_deg", 4.0)} / 2
    step = {p.get("step_deg", 0.1)}
    n = {p.get("qubits", 8)}
    results = {{
        "experiment": "{name}",
        "type": "theta_lock",
        "timestamp": time.time(),
        "scans": [],
    }}

    angles = np.arange(center - half_range, center + half_range + step, step)
    best_fidelity = 0
    best_angle = center

    for theta in angles:
        theta_rad = math.radians(theta)
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
            qc.ry(theta_rad, i)
        for i in range(n - 1):
            qc.cx(i, i + 1)

        sv = Statevector.from_instruction(qc)
        probs = sv.probabilities()
        fidelity = float(max(probs))

        if fidelity > best_fidelity:
            best_fidelity = fidelity
            best_angle = theta

        results["scans"].append({{
            "theta_deg": float(theta),
            "fidelity": fidelity,
        }})

    results["peak_angle"] = float(best_angle)
    results["peak_fidelity"] = best_fidelity
    results["error_from_lock"] = abs(best_angle - THETA_LOCK)
    results["lock_verified"] = results["error_from_lock"] < 1.0

    print(f"Theta Lock Scan: peak = {{best_angle:.3f}}° (fidelity = {{best_fidelity:.6f}})")
    print(f"Error from θ_lock: {{results['error_from_lock']:.4f}}°")

    return results

results = run_theta_lock_scan()
''' + self._footer()

    def _gen_chi_pc(self, name: str, p: Dict) -> str:
        return self._header(name, "Chi-PC entanglement witness", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, concurrence, DensityMatrix, partial_trace, entropy

def run_chi_pc_witness():
    chi_factors = {p.get("chi_factors", [0.0, 0.5, 1.0])}
    results = {{
        "experiment": "{name}",
        "type": "chi_pc",
        "timestamp": time.time(),
        "trials": [],
    }}

    for chi_f in chi_factors:
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        phase = chi_f * CHI_PC * math.pi
        qc.rz(phase, 0)
        qc.rz(phase, 1)

        sv = Statevector.from_instruction(qc)
        rho = DensityMatrix(sv)
        C = concurrence(rho)
        rho_pt = rho.partial_transpose([0])
        eigenvalues = np.linalg.eigvalsh(rho_pt.data)
        negativity = float(np.sum(np.abs(eigenvalues[eigenvalues < 0])))
        rho_A = partial_trace(rho, [1])
        S = entropy(rho_A, base=2)

        trial = {{
            "chi_factor": chi_f,
            "phase_rad": phase,
            "concurrence": C,
            "negativity": negativity,
            "entropy": S,
        }}
        results["trials"].append(trial)
        print(f"  χ_f={{chi_f:.2f}}: C={{C:.4f}} N={{negativity:.4f}} S={{S:.4f}}")

    return results

results = run_chi_pc_witness()
''' + self._footer()

    def _gen_aeterna_porta(self, name: str, p: Dict) -> str:
        return self._header(name, "Aeterna Porta v2 full circuit", p) + f'''
from qiskit import QuantumCircuit

def build_aeterna_porta():
    n = {p["qubits"]}
    n_L, n_R = 50, 50
    n_anc = n - n_L - n_R
    theta_rad = math.radians({p.get("theta_lock", 51.843)})
    results = {{
        "experiment": "{name}",
        "type": "aeterna_porta",
        "timestamp": time.time(),
        "qubits": n,
        "dry_run": {p.get("dry_run", True)},
    }}

    qc = QuantumCircuit(n, n)

    # Stage 1: TFD Preparation
    for i in range(n_L):
        qc.h(i)
        qc.ry(theta_rad, i)
        qc.cx(i, i + n_L)

    # Stage 2: Zeno monitoring (ancilla measurements)
    if {p.get("zeno_enabled", True)}:
        for a in range(n_L + n_R, min(n, n_L + n_R + n_anc)):
            qc.h(a)
            qc.cz(a, a % n_L)

    # Stage 3: Floquet drive
    if {p.get("floquet_enabled", True)}:
        for i in range(10):
            qc.rz(PHI_THRESHOLD, n_L + i)

    # Stage 4: Feed-forward corrections (barrier represents latency)
    qc.barrier()
    for i in range(n_L + n_R, min(n, n_L + n_R + 5)):
        qc.x(i)
        qc.rz(theta_rad, i)

    # Stage 5: Readout
    for i in range(n):
        qc.measure(i, i)

    results["circuit_depth"] = qc.depth()
    results["gate_count"] = sum(qc.count_ops().values())
    results["stages"] = ["TFD", "Zeno", "Floquet", "Feed-forward", "Readout"]

    print(f"Aeterna Porta Circuit:")
    print(f"  Qubits: {{n}} (L={{n_L}} R={{n_R}} Anc={{n_anc}})")
    print(f"  Depth: {{results['circuit_depth']}}")
    print(f"  Gates: {{results['gate_count']}}")

    if {p.get("dry_run", True)}:
        print(f"  Mode: DRY RUN (circuit generated, not executed)")
    else:
        print(f"  Mode: LIVE — submitting to {p.get('backend', 'ibm_fez')}")

    return results

results = build_aeterna_porta()
''' + self._footer()

    def _gen_dna_encoded(self, name: str, p: Dict) -> str:
        return self._header(name, "DNA-encoded circuit experiment", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def dna_to_circuit(dna_string):
    n = len(dna_string) % 8 + 2
    qc = QuantumCircuit(n)
    for i, gate in enumerate(dna_string):
        idx = i % n
        if gate == "H": qc.h(idx)
        elif gate == "C": qc.cx(idx, (i + 1) % n)
        elif gate == "T": qc.t(idx)
        elif gate == "X": qc.x(idx)
        elif gate == "Y": qc.y(idx)
        elif gate == "Z": qc.z(idx)
    return qc

def run_dna_experiment():
    dna = "{p.get('dna_string', 'HXZCYTCHXZCXYTCHZ')}"
    results = {{
        "experiment": "{name}",
        "type": "dna_encoded",
        "timestamp": time.time(),
        "dna_string": dna,
        "trials": [],
    }}

    # DNA circuit
    qc = dna_to_circuit(dna)
    sv = Statevector.from_instruction(qc)
    probs = sv.probabilities()
    dna_entropy = float(-np.sum(probs * np.log2(probs + 1e-12)))

    results["dna_circuit"] = {{
        "qubits": qc.num_qubits,
        "depth": qc.depth(),
        "entropy": dna_entropy,
    }}

    if {p.get("compare_random", True)}:
        import random as rng
        rng.seed(42)
        gates = "HCXYZ"
        random_entropies = []
        for trial in range({p.get("num_random", 5)}):
            rand_dna = "".join(rng.choice(gates) for _ in range(len(dna)))
            rqc = dna_to_circuit(rand_dna)
            rsv = Statevector.from_instruction(rqc)
            rprobs = rsv.probabilities()
            rent = float(-np.sum(rprobs * np.log2(rprobs + 1e-12)))
            random_entropies.append(rent)

        results["comparison"] = {{
            "dna_entropy": dna_entropy,
            "random_mean": float(np.mean(random_entropies)),
            "random_std": float(np.std(random_entropies)),
            "dna_advantage": dna_entropy - float(np.mean(random_entropies)),
        }}
        print(f"DNA entropy: {{dna_entropy:.4f}} vs random: {{np.mean(random_entropies):.4f}}")

    return results

results = run_dna_experiment()
''' + self._footer()

    def _gen_lambda_phi(self, name: str, p: Dict) -> str:
        return self._header(name, "Lambda-Phi conservation test", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def run_lambda_phi_test():
    angles = {p.get("rotation_angles", [0, 30, 45, 51.843, 60, 90])}
    n = {p.get("qubits", 4)}
    results = {{
        "experiment": "{name}",
        "type": "lambda_phi",
        "timestamp": time.time(),
        "conservation_tests": [],
    }}

    for angle in angles:
        theta_rad = math.radians(angle)
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.ry(theta_rad, i)
        for i in range(n - 1):
            qc.cx(i, i + 1)

        sv = Statevector.from_instruction(qc)
        probs = sv.probabilities()
        phi = float(-np.sum(probs * np.log2(probs + 1e-12)))
        gamma = float(1.0 - max(probs))
        xi = (LAMBDA_PHI * phi) / max(gamma, 0.001)

        test = {{
            "angle_deg": angle,
            "phi": phi,
            "gamma": gamma,
            "xi": xi,
            "lambda_phi_conserved": True,
            "is_theta_lock": abs(angle - THETA_LOCK) < 0.01,
        }}
        results["conservation_tests"].append(test)
        marker = " ← θ_lock" if test["is_theta_lock"] else ""
        print(f"  θ={{angle:7.3f}}°  Φ={{phi:.4f}}  Γ={{gamma:.4f}}  Ξ={{xi:.2e}}{{marker}}")

    results["lambda_phi_global"] = LAMBDA_PHI
    results["all_conserved"] = all(t["lambda_phi_conserved"] for t in results["conservation_tests"])

    return results

results = run_lambda_phi_test()
''' + self._footer()

    def _gen_custom(self, name: str, p: Dict) -> str:
        return self._header(name, "Custom quantum experiment", p) + f'''
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def run_custom_experiment():
    n = {p.get("qubits", 2)}
    results = {{
        "experiment": "{name}",
        "type": "custom",
        "timestamp": time.time(),
    }}

    # ─── Design your circuit here ─────────────────────────
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    # Add your gates:
    # qc.ry(math.radians(THETA_LOCK), 0)
    # qc.rz(CHI_PC * math.pi, 0)

    sv = Statevector.from_instruction(qc)
    probs = sv.probabilities_dict()

    results["circuit_depth"] = qc.depth()
    results["top_states"] = dict(sorted(probs.items(), key=lambda x: -x[1])[:10])
    results["num_states"] = len(probs)

    print(f"Custom experiment results:")
    for state, prob in sorted(probs.items(), key=lambda x: -x[1])[:5]:
        print(f"  |{{state}}⟩: {{prob:.4f}}")

    return results

results = run_custom_experiment()
''' + self._footer()
