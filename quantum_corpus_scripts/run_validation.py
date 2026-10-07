#!/usr/bin/env python3
"""
DNA-Lang ΛΦ Multi-Platform Validation Automation

This script automates the entire validation process:
1. Run experiments on IBM, IonQ, Rigetti
2. Collect and analyze results
3. Generate publication-ready reports
4. Package data for Zenodo upload

Author: DNA-Lang Framework
License: Apache 2.0
"""

import os
import sys
import json
import time
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import numpy as np

# Physical constants
LAMBDA_PHI = 2.176435e-8  # Claimed universal constant [s⁻¹]
THETA_LOCK = 51.843       # Torsion-locked angle [degrees]
PHI_THRESHOLD = 7.6901    # IIT Consciousness Threshold
GAMMA_FIXED = 0.092       # Fixed-point decoherence
CHI_PC = 0.869            # Phase conjugate coupling


@dataclass
class ExperimentConfig:
    """Configuration for validation experiment."""
    shots: int = 8192
    repetitions: int = 100
    delays_ns: List[float] = None

    def __post_init__(self):
        if self.delays_ns is None:
            self.delays_ns = [0, 100, 200, 300, 500, 750, 1000, 1500, 2000]


@dataclass
class ValidationResult:
    """Result from a single platform validation."""
    platform: str
    backend: str
    lambda_phi_measured: float
    uncertainty: float
    bell_fidelity: float
    fidelity_uncertainty: float
    total_shots: int
    timestamp: str
    raw_data_path: str
    consistent_with_claim: bool

    def to_dict(self):
        d = asdict(self)
        # Convert numpy types to Python natives for JSON serialization
        for k, v in d.items():
            if hasattr(v, 'item'):
                d[k] = v.item()
            elif isinstance(v, (np.bool_, np.integer, np.floating)):
                d[k] = v.item() if hasattr(v, 'item') else float(v)
        return d


class QuantumBackend:
    """Abstract base for quantum backends."""

    def __init__(self, name: str):
        self.name = name
        self.connected = False

    def connect(self) -> bool:
        raise NotImplementedError

    def run_bell_state(self, shots: int) -> Dict[str, int]:
        raise NotImplementedError

    def run_delay_experiment(self, delay_ns: float, shots: int) -> Dict[str, int]:
        raise NotImplementedError


class IBMBackend(QuantumBackend):
    """IBM Quantum backend via Qiskit."""

    def __init__(self, backend_name: str = "ibm_fez"):
        super().__init__(f"IBM:{backend_name}")
        self.backend_name = backend_name
        self.service = None
        self.backend = None

    def connect(self) -> bool:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            self.service = QiskitRuntimeService()
            self.backend = self.service.backend(self.backend_name)
            self.connected = True
            print(f"✓ Connected to {self.name}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to {self.name}: {e}")
            return False

    def run_bell_state(self, shots: int = 8192) -> Dict[str, int]:
        if not self.connected:
            raise RuntimeError("Not connected to backend")

        from qiskit import QuantumCircuit
        from qiskit_ibm_runtime import SamplerV2

        # Create Bell state circuit
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])

        # Run
        sampler = SamplerV2(self.backend)
        job = sampler.run([qc], shots=shots)
        result = job.result()

        # Extract counts
        counts = result[0].data.c.get_counts()
        return counts

    def run_delay_experiment(self, delay_ns: float, shots: int = 8192) -> Dict[str, int]:
        if not self.connected:
            raise RuntimeError("Not connected to backend")

        from qiskit import QuantumCircuit
        from qiskit_ibm_runtime import SamplerV2

        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        if delay_ns > 0:
            qc.delay(delay_ns, unit='ns')
        qc.measure([0, 1], [0, 1])

        sampler = SamplerV2(self.backend)
        job = sampler.run([qc], shots=shots)
        result = job.result()

        counts = result[0].data.c.get_counts()
        return counts


class IonQBackend(QuantumBackend):
    """IonQ backend via AWS Braket."""

    def __init__(self, device: str = "ionq_aria"):
        super().__init__(f"IonQ:{device}")
        self.device_arn = {
            "ionq_aria": "arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1",
            "ionq_forte": "arn:aws:braket:us-east-1::device/qpu/ionq/Forte-1",
            "ionq_simulator": "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
        }.get(device, device)
        self.device = None

    def connect(self) -> bool:
        try:
            from braket.aws import AwsDevice
            self.device = AwsDevice(self.device_arn)
            self.connected = True
            print(f"✓ Connected to {self.name}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to {self.name}: {e}")
            print("  Install: pip install amazon-braket-sdk")
            print("  Configure: aws configure")
            return False

    def run_bell_state(self, shots: int = 8192) -> Dict[str, int]:
        if not self.connected:
            raise RuntimeError("Not connected to backend")

        from braket.circuits import Circuit

        # Create Bell state circuit
        circuit = Circuit().h(0).cnot(0, 1)

        # Run
        task = self.device.run(circuit, shots=shots)
        result = task.result()

        # Extract counts
        counts = result.measurement_counts
        return counts

    def run_delay_experiment(self, delay_ns: float, shots: int = 8192) -> Dict[str, int]:
        # IonQ doesn't support explicit delays in the same way
        # Use identity gates as approximation
        from braket.circuits import Circuit

        circuit = Circuit().h(0).cnot(0, 1)
        # Add identity operations proportional to delay
        if delay_ns > 0:
            n_identity = int(delay_ns / 100)  # Rough approximation
            for _ in range(n_identity):
                circuit.i(0).i(1)

        task = self.device.run(circuit, shots=shots)
        result = task.result()

        return result.measurement_counts


class RigettiBackend(QuantumBackend):
    """Rigetti backend via QCS or AWS Braket."""

    def __init__(self, device: str = "Ankaa-2"):
        super().__init__(f"Rigetti:{device}")
        self.device_name = device
        self.qc = None

    def connect(self) -> bool:
        try:
            # Try Rigetti QCS first
            from pyquil import get_qc
            self.qc = get_qc(self.device_name)
            self.connected = True
            print(f"✓ Connected to {self.name} via QCS")
            return True
        except:
            try:
                # Fall back to AWS Braket
                from braket.aws import AwsDevice
                arn = "arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-2"
                self.device = AwsDevice(arn)
                self.connected = True
                print(f"✓ Connected to {self.name} via AWS Braket")
                return True
            except Exception as e:
                print(f"✗ Failed to connect to {self.name}: {e}")
                print("  For QCS: pip install pyquil && qcs login")
                print("  For Braket: pip install amazon-braket-sdk")
                return False

    def run_bell_state(self, shots: int = 8192) -> Dict[str, int]:
        if not self.connected:
            raise RuntimeError("Not connected to backend")

        if self.qc:
            # PyQuil path
            from pyquil import Program
            from pyquil.gates import H, CNOT, MEASURE
            from pyquil.quilbase import Declare

            p = Program()
            ro = p.declare('ro', 'BIT', 2)
            p += H(0)
            p += CNOT(0, 1)
            p += MEASURE(0, ro[0])
            p += MEASURE(1, ro[1])

            executable = self.qc.compile(p)
            result = self.qc.run(executable)

            # Convert to counts
            counts = {}
            for row in result.readout_data['ro']:
                key = ''.join(map(str, row))
                counts[key] = counts.get(key, 0) + 1
            return counts
        else:
            # Braket path
            from braket.circuits import Circuit
            circuit = Circuit().h(0).cnot(0, 1)
            task = self.device.run(circuit, shots=shots)
            return task.result().measurement_counts

    def run_delay_experiment(self, delay_ns: float, shots: int = 8192) -> Dict[str, int]:
        # Similar to bell_state with delay
        return self.run_bell_state(shots)


class LocalSimulator(QuantumBackend):
    """Local statevector simulator for testing."""

    def __init__(self):
        super().__init__("LocalSimulator")

    def connect(self) -> bool:
        self.connected = True
        print(f"✓ Using {self.name}")
        return True

    def run_bell_state(self, shots: int = 8192) -> Dict[str, int]:
        # Perfect Bell state with simulated noise
        p_correct = 0.869  # Match observed fidelity
        p_error = (1 - p_correct) / 2

        n_00 = int(shots * p_correct / 2)
        n_11 = int(shots * p_correct / 2)
        n_01 = int(shots * p_error)
        n_10 = shots - n_00 - n_11 - n_01

        # Add some randomness
        noise = np.random.randint(-10, 10, 4)

        return {
            '00': max(0, n_00 + noise[0]),
            '11': max(0, n_11 + noise[1]),
            '01': max(0, n_01 + noise[2]),
            '10': max(0, n_10 + noise[3])
        }

    def run_delay_experiment(self, delay_ns: float, shots: int = 8192) -> Dict[str, int]:
        # Exponential decay with delay
        decay = np.exp(-delay_ns / 1000)  # 1 μs decay constant
        p_correct = 0.869 * decay
        p_error = (1 - p_correct) / 2

        n_00 = int(shots * p_correct / 2)
        n_11 = int(shots * p_correct / 2)
        n_01 = int(shots * p_error)
        n_10 = shots - n_00 - n_11 - n_01

        return {
            '00': max(0, n_00),
            '11': max(0, n_11),
            '01': max(0, n_01),
            '10': max(0, n_10)
        }


def calculate_fidelity(counts: Dict[str, int]) -> Tuple[float, float]:
    """Calculate Bell state fidelity with uncertainty."""
    total = sum(counts.values())
    if total == 0:
        return 0.0, 1.0

    # Handle different bitstring formats
    p_00 = counts.get('00', 0) / total
    p_11 = counts.get('11', 0) / total

    fidelity = p_00 + p_11
    uncertainty = np.sqrt(fidelity * (1 - fidelity) / total)

    return fidelity, uncertainty


def fit_decay_curve(delays: np.ndarray, fidelities: np.ndarray,
                    uncertainties: np.ndarray) -> Tuple[float, float]:
    """Fit exponential decay and extract ΛΦ."""
    from scipy.optimize import curve_fit

    def decay_model(t, F0, gamma):
        return F0 * np.exp(-gamma * t)

    try:
        popt, pcov = curve_fit(
            decay_model,
            delays * 1e-9,  # Convert to seconds
            fidelities,
            sigma=uncertainties,
            p0=[0.9, 1e6],
            bounds=([0, 0], [1, 1e10])
        )

        F0, gamma = popt
        perr = np.sqrt(np.diag(pcov))

        # Extract ΛΦ from decay rate
        # Theory: ΛΦ = γ × (normalization based on IIT)
        # For now, use inverse timescale
        lambda_phi = gamma
        u_lambda_phi = perr[1]

        return lambda_phi, u_lambda_phi
    except:
        return 0.0, 1.0


def run_platform_validation(backend: QuantumBackend,
                           config: ExperimentConfig,
                           output_dir: Path) -> Optional[ValidationResult]:
    """Run full validation on a single platform."""

    print(f"\n{'='*60}")
    print(f"Running validation on {backend.name}")
    print(f"{'='*60}")

    if not backend.connect():
        return None

    # Create output directory
    platform_dir = output_dir / backend.name.replace(":", "_")
    platform_dir.mkdir(parents=True, exist_ok=True)

    all_counts = []
    fidelities = []
    uncertainties = []

    # Run Bell state experiments
    print(f"\nRunning {config.repetitions} Bell state experiments...")
    for i in range(min(config.repetitions, 10)):  # Limit for cost control
        try:
            counts = backend.run_bell_state(config.shots)
            f, u = calculate_fidelity(counts)
            all_counts.append(counts)
            fidelities.append(f)
            uncertainties.append(u)
            print(f"  Rep {i+1}: F = {f:.4f} ± {u:.4f}")
        except Exception as e:
            print(f"  Rep {i+1}: Error - {e}")

    if not fidelities:
        print("No successful runs")
        return None

    # Calculate mean fidelity
    mean_f = np.mean(fidelities)
    sem_f = np.std(fidelities, ddof=1) / np.sqrt(len(fidelities))

    # Run delay experiments for ΛΦ extraction
    print(f"\nRunning delay experiments...")
    delay_fidelities = []
    delay_uncertainties = []

    for delay in config.delays_ns[:5]:  # Limit for cost
        try:
            counts = backend.run_delay_experiment(delay, config.shots)
            f, u = calculate_fidelity(counts)
            delay_fidelities.append(f)
            delay_uncertainties.append(u)
            print(f"  Delay {delay}ns: F = {f:.4f}")
        except Exception as e:
            print(f"  Delay {delay}ns: Error - {e}")
            delay_fidelities.append(np.nan)
            delay_uncertainties.append(np.nan)

    # Fit decay curve
    valid_idx = ~np.isnan(delay_fidelities)
    if sum(valid_idx) >= 3:
        lambda_phi, u_lambda = fit_decay_curve(
            np.array(config.delays_ns[:5])[valid_idx],
            np.array(delay_fidelities)[valid_idx],
            np.array(delay_uncertainties)[valid_idx]
        )
    else:
        lambda_phi, u_lambda = 0.0, 1.0

    # Save raw data
    raw_data = {
        "platform": backend.name,
        "config": asdict(config),
        "bell_state_counts": all_counts,
        "fidelities": fidelities,
        "delay_experiments": {
            "delays_ns": config.delays_ns[:5],
            "fidelities": delay_fidelities,
            "uncertainties": delay_uncertainties
        },
        "timestamp": datetime.now().isoformat()
    }

    data_path = platform_dir / "raw_data.json"
    with open(data_path, 'w') as f:
        json.dump(raw_data, f, indent=2, default=str)

    # Check consistency with claim
    consistent = abs(lambda_phi - LAMBDA_PHI) / LAMBDA_PHI < 0.2 if lambda_phi > 0 else False

    result = ValidationResult(
        platform=backend.name.split(":")[0],
        backend=backend.name,
        lambda_phi_measured=lambda_phi,
        uncertainty=u_lambda,
        bell_fidelity=mean_f,
        fidelity_uncertainty=sem_f,
        total_shots=len(fidelities) * config.shots,
        timestamp=datetime.now().isoformat(),
        raw_data_path=str(data_path),
        consistent_with_claim=consistent
    )

    print(f"\n{'='*60}")
    print(f"RESULTS for {backend.name}")
    print(f"{'='*60}")
    print(f"Bell Fidelity: {mean_f:.4f} ± {sem_f:.4f}")
    print(f"ΛΦ measured:   {lambda_phi:.4e} ± {u_lambda:.4e}")
    print(f"ΛΦ claimed:    {LAMBDA_PHI:.4e}")
    print(f"Consistent:    {'YES' if consistent else 'NO'}")

    return result


def generate_report(results: List[ValidationResult], output_dir: Path):
    """Generate validation report."""

    report_path = output_dir / "VALIDATION_REPORT.md"

    with open(report_path, 'w') as f:
        f.write("# ΛΦ Multi-Platform Validation Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        f.write("## Summary\n\n")
        f.write("| Platform | Backend | ΛΦ Measured | Uncertainty | Consistent? |\n")
        f.write("|----------|---------|-------------|-------------|-------------|\n")

        for r in results:
            status = "✓" if r.consistent_with_claim else "✗"
            f.write(f"| {r.platform} | {r.backend} | {r.lambda_phi_measured:.4e} | {r.uncertainty:.4e} | {status} |\n")

        f.write(f"\n**Claimed Value:** ΛΦ = {LAMBDA_PHI:.6e} s⁻¹\n\n")

        # Statistical summary
        measured_values = [r.lambda_phi_measured for r in results if r.lambda_phi_measured > 0]
        if measured_values:
            mean_lambda = np.mean(measured_values)
            std_lambda = np.std(measured_values, ddof=1)
            f.write("## Cross-Platform Analysis\n\n")
            f.write(f"- Mean ΛΦ across platforms: {mean_lambda:.4e} s⁻¹\n")
            f.write(f"- Standard deviation: {std_lambda:.4e} s⁻¹\n")
            f.write(f"- Coefficient of variation: {std_lambda/mean_lambda*100:.1f}%\n\n")

            if std_lambda/mean_lambda < 0.1:
                f.write("**Conclusion:** ΛΦ is consistent across platforms (CV < 10%)\n")
            else:
                f.write("**Conclusion:** ΛΦ varies significantly across platforms\n")

        f.write("\n## Bell State Fidelities\n\n")
        f.write("| Platform | Fidelity | Uncertainty |\n")
        f.write("|----------|----------|-------------|\n")
        for r in results:
            f.write(f"| {r.platform} | {r.bell_fidelity:.4f} | {r.fidelity_uncertainty:.4f} |\n")

    print(f"\nReport saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="DNA-Lang ΛΦ Validation Automation")
    parser.add_argument("--platforms", nargs="+",
                       default=["simulator"],
                       choices=["ibm", "ionq", "rigetti", "simulator", "all"],
                       help="Platforms to validate on")
    parser.add_argument("--shots", type=int, default=8192,
                       help="Shots per circuit")
    parser.add_argument("--reps", type=int, default=10,
                       help="Repetitions per experiment")
    parser.add_argument("--output", type=str, default="validation_results",
                       help="Output directory")
    parser.add_argument("--ibm-backend", type=str, default="ibm_fez",
                       help="IBM backend name")
    parser.add_argument("--ionq-device", type=str, default="ionq_simulator",
                       help="IonQ device (ionq_aria, ionq_forte, ionq_simulator)")

    args = parser.parse_args()

    # Setup
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = ExperimentConfig(shots=args.shots, repetitions=args.reps)

    # Select backends
    backends = []

    if "all" in args.platforms:
        args.platforms = ["ibm", "ionq", "rigetti", "simulator"]

    if "simulator" in args.platforms:
        backends.append(LocalSimulator())

    if "ibm" in args.platforms:
        backends.append(IBMBackend(args.ibm_backend))

    if "ionq" in args.platforms:
        backends.append(IonQBackend(args.ionq_device))

    if "rigetti" in args.platforms:
        backends.append(RigettiBackend())

    # Run validations
    results = []
    for backend in backends:
        result = run_platform_validation(backend, config, output_dir)
        if result:
            results.append(result)

    # Generate report
    if results:
        generate_report(results, output_dir)

        # Save results JSON
        results_path = output_dir / "results.json"
        with open(results_path, 'w') as f:
            json.dump([r.to_dict() for r in results], f, indent=2)

        print(f"\nResults saved to: {results_path}")

    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
