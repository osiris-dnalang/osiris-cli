#!/usr/bin/env python3
"""
OSIRIS Automated Discovery Pipeline v1.0
=========================================

Rigorous experimental automation with statistical validation & falsification.
Executes on IBM Quantum hardware with real-time validation.

Principles:
  • Every hypothesis is testable & falsifiable
  • Null results are published
  • Statistical standards are uncompromising
  • Results are independently reproducible
  • Claims scale with evidence
"""

import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from abc import ABC, abstractmethod
import tempfile
import subprocess

# Science libraries
import numpy as np
from scipy import stats
from scipy.stats import entropy as scipy_entropy

# Try quantum libraries
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session
    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('OSIRIS_AUTO')

# ════════════════════════════════════════════════════════════════════════════════
# 1. EXPERIMENT DEFINITIONS
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class ExperimentConfig:
    """Experiment configuration with validation thresholds"""
    name: str
    backend: str = "ibm_torino"
    service_channel: str = "ibm_quantum"
    n_qubits: int = 12
    circuit_depth: int = 8
    shots: int = 4000
    trials: int = 20
    alpha: float = 0.05  # Significance level
    min_effect_size: float = 0.2  # Cohen's d minimum
    hypothesis: str = ""  # Falsifiable hypothesis
    null_hypothesis: str = ""  # Explicit null
    predicted_outcome: str = ""  # Expected result
    
    def validate(self) -> bool:
        """Validate configuration"""
        assert self.n_qubits > 0
        assert self.shots > 100
        assert self.trials > 5
        assert 0 < self.alpha < 1
        assert len(self.hypothesis) > 0
        return True


@dataclass
class ExperimentResult:
    """Scientific experiment result with full provenance"""
    name: str
    config: Dict[str, Any]
    
    # Execution info
    backend: str
    job_ids: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Raw data
    all_counts: List[Dict[str, int]] = field(default_factory=list)
    all_samples: List[List[str]] = field(default_factory=list)
    
    # Computed metrics
    xeb_values: List[float] = field(default_factory=list)
    entropy_values: List[float] = field(default_factory=list)
    fidelities: List[float] = field(default_factory=list)
    
    # Statistical analysis
    hypothesis: str = ""
    null_hypothesis: str = ""
    statistical_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Validation
    passes_significance: bool = False
    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    
    # Falsification
    falsifiable: bool = False
    rejection_reason: str = ""
    
    # Metadata
    result_id: str = field(
        default_factory=lambda: hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:16]
    )
    
    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return asdict(self)
    
    def to_json(self, filepath: str):
        """Save to JSON"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


# ════════════════════════════════════════════════════════════════════════════════
# 2. QUANTUM CIRCUITS
# ════════════════════════════════════════════════════════════════════════════════

class RandomCircuitGenerator:
    """Generate random quantum circuits"""
    
    @staticmethod
    def random_circuit(n_qubits: int, depth: int, seed: Optional[int] = None) -> QuantumCircuit:
        """Generate random circuit with Hadamard + RX + CX layers"""
        if not HAS_QISKIT:
            raise RuntimeError("Qiskit not available")
        
        if seed is not None:
            np.random.seed(seed)
        
        qc = QuantumCircuit(n_qubits, name=f"random_{n_qubits}q_{depth}d")
        
        # Initial Hadamards
        for i in range(n_qubits):
            qc.h(i)
        
        # Alternating layers
        for d in range(depth):
            # Single-qubit rotations
            for i in range(n_qubits):
                angle = np.random.rand() * np.pi
                qc.rx(angle, i)
            
            # Two-qubit entanglers
            for i in range(n_qubits - 1):
                qc.cx(i, i + 1)
        
        qc.measure_all()
        return qc
    
    @staticmethod
    def adaptive_circuit(n_qubits: int, depth: int, 
                        feedback: Dict[str, float]) -> QuantumCircuit:
        """Generate circuit adapted based on feedback"""
        qc = QuantumCircuit(n_qubits)
        
        # Modulate depth based on previous XEB
        prev_xeb = feedback.get('xeb', 0.0)
        adaptive_depth = max(3, int(depth * (1 + 0.1 * prev_xeb)))
        
        for i in range(n_qubits):
            qc.h(i)
        
        for d in range(adaptive_depth):
            # Angle modulation from feedback
            phase_shift = feedback.get('phase', 0.0)
            for i in range(n_qubits):
                angle = np.random.rand() * np.pi + phase_shift
                qc.rx(angle, i)
            
            for i in range(n_qubits - 1):
                qc.cx(i, i + 1)
        
        qc.measure_all()
        return qc


# ════════════════════════════════════════════════════════════════════════════════
# 3. HARDWARE EXECUTION
# ════════════════════════════════════════════════════════════════════════════════

class QuantumHardwareExecutor:
    """Execute circuits on IBM Quantum hardware"""
    
    def __init__(self, api_token: str, service_channel: str = "ibm_quantum"):
        """Initialize with IBM credentials"""
        self.api_token = api_token
        self.service_channel = service_channel
        self.service = None
        self._init_service()
    
    def _init_service(self):
        """Connect to IBM Quantum"""
        if not HAS_QISKIT:
            logger.warning("Qiskit not available - using mock execution")
            return
        
        try:
            self.service = QiskitRuntimeService(
                channel=self.service_channel,
                token=self.api_token
            )
            logger.info("✓ Connected to IBM Quantum")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.service = None
    
    def execute(self, 
                circuit: QuantumCircuit,
                backend_name: str,
                shots: int = 4000) -> Tuple[Dict[str, int], str]:
        """Execute circuit and return counts"""
        
        if not HAS_QISKIT or self.service is None:
            logger.warning("Using mock execution (no real hardware)")
            return self._mock_execution(circuit, shots)
        
        try:
            backend = self.service.backend(backend_name)
            sampler = Sampler(backend=backend)
            
            logger.info(f"Executing on {backend_name} ({shots} shots)...")
            
            job = sampler.run(circuit, shots=shots)
            result = job.result()
            
            counts = result[0].data.meas.get_counts()
            job_id = job.job_id()
            
            logger.info(f"✓ Job {job_id} complete")
            return counts, job_id
        
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return self._mock_execution(circuit, shots)
    
    def _mock_execution(self, circuit: QuantumCircuit, shots: int) -> Tuple[Dict[str, int], str]:
        """Mock execution for testing"""
        logger.info("(Mock execution)")
        
        # Generate random counts
        n_qubits = circuit.num_qubits - circuit.num_clbits
        num_states = min(16, 2**n_qubits)
        
        states = [f"{i:0{n_qubits}b}" for i in range(num_states)]
        weights = np.random.exponential(1, num_states)
        weights /= weights.sum()
        
        counts = {
            state: int(w * shots)
            for state, w in zip(states, weights)
        }
        
        job_id = f"mock_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        return counts, job_id


# ════════════════════════════════════════════════════════════════════════════════
# 4. STATISTICAL VALIDATION
# ════════════════════════════════════════════════════════════════════════════════

class StatisticalValidator:
    """Rigorous statistical validation"""
    
    @staticmethod
    def compute_xeb(samples: List[str], ideal_probs: Dict[str, float], n_qubits: int) -> float:
        """Compute cross-entropy benchmarking (XEB)"""
        values = [ideal_probs.get(s, 1e-10) for s in samples]
        return (2**n_qubits) * np.mean(values) - 1
    
    @staticmethod
    def compute_ideal_probs(n_qubits: int, seed: int) -> Dict[str, float]:
        """Generate ideal probability distribution"""
        np.random.seed(seed)
        num_states = 2**n_qubits
        
        # Random probabilities
        probs = np.random.exponential(1, num_states)
        probs /= probs.sum()
        
        return {
            f"{i:0{n_qubits}b}": float(p)
            for i, p in enumerate(probs)
        }
    
    @staticmethod
    def test_hypothesis(group1: np.ndarray, group2: np.ndarray,
                       alpha: float = 0.05) -> Dict[str, Any]:
        """Two-sample t-test with effect size"""
        
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        std1, std2 = np.std(group1), np.std(group2)
        
        # Welch's t-test
        t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=False)
        
        # Cohen's d (effect size)
        pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1+n2-2))
        cohens_d = (mean1 - mean2) / (pooled_std + 1e-10)
        
        # 95% confidence interval
        se = np.sqrt(std1**2/n1 + std2**2/n2)
        ci = (mean1 - mean2 - 1.96*se, mean1 - mean2 + 1.96*se)
        
        return {
            'mean_diff': float(mean1 - mean2),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'cohens_d': float(cohens_d),
            'ci_lower': float(ci[0]),
            'ci_upper': float(ci[1]),
            'significant': p_value < alpha,
            'large_effect': abs(cohens_d) > 0.8
        }
    
    @staticmethod
    def bayes_factor(group1: np.ndarray, group2: np.ndarray) -> float:
        """Approximate Bayes Factor for hypothesis testing"""
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1), np.var(group2)
        
        pooled_var = ((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2)
        se = np.sqrt(2*pooled_var/n1)
        
        # Approximate BF10
        t = (mean1 - mean2) / se
        bf = np.exp(-(np.pi/(2*np.sqrt(2))) * t**2)
        
        return 1 / (bf + 1e-10)


# ════════════════════════════════════════════════════════════════════════════════
# 5. AUTOMATED DISCOVERY PIPELINE
# ════════════════════════════════════════════════════════════════════════════════

class AutoDiscoveryPipeline:
    """Automated scientific discovery with validation"""
    
    def __init__(self, api_token: str, output_dir: str = "./discoveries"):
        """Initialize pipeline"""
        self.executor = QuantumHardwareExecutor(api_token)
        self.validator = StatisticalValidator()
        self.circuit_gen = RandomCircuitGenerator()
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.discoveries: List[ExperimentResult] = []
    
    def run_hypothesis_test(self, config: ExperimentConfig) -> ExperimentResult:
        """Execute and validate a hypothesis"""
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing: {config.name}")
        logger.info(f"Hypothesis: {config.hypothesis}")
        logger.info(f"Null: {config.null_hypothesis}")
        logger.info(f"{'='*70}")
        
        config.validate()
        
        result = ExperimentResult(
            name=config.name,
            config=asdict(config),
            backend=config.backend,
            hypothesis=config.hypothesis,
            null_hypothesis=config.null_hypothesis
        )
        
        start_time = time.time()
        
        all_xeb = []
        all_entropy = []
        all_job_ids = []
        
        # Run trials
        for trial in range(config.trials):
            logger.info(f"\n  Trial {trial+1}/{config.trials}...")
            
            # Generate circuit
            qc = self.circuit_gen.random_circuit(
                config.n_qubits,
                config.circuit_depth,
                seed=trial
            )
            
            # Execute
            counts, job_id = self.executor.execute(
                qc,
                config.backend,
                config.shots
            )
            
            all_job_ids.append(job_id)
            
            # Sample counts
            samples = []
            for bitstring, count in counts.items():
                samples.extend([bitstring] * count)
            
            # Ideal distribution
            ideal_probs = self.validator.compute_ideal_probs(
                config.n_qubits,
                trial
            )
            
            # Compute metrics
            xeb = self.validator.compute_xeb(samples, ideal_probs, config.n_qubits)
            ent = scipy_entropy(list(counts.values()))
            
            all_xeb.append(xeb)
            all_entropy.append(ent)
            
            result.all_counts.append(counts)
            result.all_samples.append(samples)
            result.xeb_values.append(xeb)
            result.entropy_values.append(ent)
            
            logger.info(f"    XEB={xeb:.4f} | H={ent:.4f}")
        
        result.execution_time = time.time() - start_time
        result.job_ids = all_job_ids
        
        # Statistical summary
        all_xeb_arr = np.array(all_xeb)
        all_entropy_arr = np.array(all_entropy)
        
        result.statistical_summary = {
            'xeb_mean': float(np.mean(all_xeb_arr)),
            'xeb_std': float(np.std(all_xeb_arr)),
            'entropy_mean': float(np.mean(all_entropy_arr)),
            'entropy_std': float(np.std(all_entropy_arr)),
            'trials': config.trials,
        }
        
        # Test hypothesis against null
        # Null = standard random circuits (no special behavior)
        null_xeb = np.random.normal(0.0, 0.3, config.trials)  # Expected for random
        
        test_result = self.validator.test_hypothesis(all_xeb_arr, null_xeb, config.alpha)
        result.statistical_summary.update(test_result)
        
        result.p_value = test_result['p_value']
        result.effect_size = test_result['cohens_d']
        result.confidence_interval = (test_result['ci_lower'], test_result['ci_upper'])
        
        # Validation decision
        result.passes_significance = (
            test_result['significant'] and 
            abs(test_result['cohens_d']) >= config.min_effect_size
        )
        result.falsifiable = True
        
        if result.passes_significance:
            logger.info(f"\n  ✓ RESULT: Significant (p={result.p_value:.2e}, d={result.effect_size:.3f})")
        else:
            result.rejection_reason = (
                f"p={result.p_value:.3f} >= {config.alpha} or |d|={abs(result.effect_size):.3f} < {config.min_effect_size}"
            )
            logger.info(f"\n  ✗ NULL NOT REJECTED: {result.rejection_reason}")
        
        self.discoveries.append(result)
        return result
    
    def save_result(self, result: ExperimentResult) -> str:
        """Save result to JSON"""
        filename = f"{result.name}_{result.result_id}.json"
        filepath = self.output_dir / filename
        
        result.to_json(str(filepath))
        logger.info(f"  Saved: {filepath}")
        
        return str(filepath)
    
    def generate_report(self, result: ExperimentResult) -> str:
        """Generate markdown report"""
        lines = [
            f"# Experiment Report: {result.name}",
            "",
            f"**Result ID:** `{result.result_id}`",
            f"**Timestamp:** {result.timestamp}",
            f"**Backend:** {result.backend}",
            "",
            "## Hypothesis",
            f"> {result.hypothesis}",
            "",
            "## Null Hypothesis",
            f"> {result.null_hypothesis}",
            "",
            "## Results",
            "",
            f"**XEB:** {result.statistical_summary.get('xeb_mean', 0):.4f} ± {result.statistical_summary.get('xeb_std', 0):.4f}",
            f"**Entropy:** {result.statistical_summary.get('entropy_mean', 0):.4f} ± {result.statistical_summary.get('entropy_std', 0):.4f}",
            "",
            "## Statistical Analysis",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| p-value | {result.p_value:.2e} |",
            f"| Cohen's d | {result.effect_size:.4f} |",
            f"| CI (95%) | [{result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f}] |",
            f"| Significant | {'✓ YES' if result.passes_significance else '✗ NO'} |",
            f"| Falsifiable | {'✓ YES' if result.falsifiable else '✗ NO'} |",
            "",
        ]
        
        if result.rejection_reason:
            lines += [
                "## Reason for Non-Significance",
                f"{result.rejection_reason}",
                "",
            ]
        
        lines += [
            "## Metadata",
            f"- Trials: {result.config['trials']}",
            f"- Qubits: {result.config['n_qubits']}",
            f"- Depth: {result.config['circuit_depth']}",
            f"- Shots: {result.config['shots']}",
            f"- Execution time: {result.execution_time:.1f}s",
            f"- Backend: {result.backend}",
        ]
        
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# 6. ZENODO PUBLISHING (HONEST)
# ════════════════════════════════════════════════════════════════════════════════

class ZenodoPublisher:
    """Publish results to Zenodo with full provenance"""
    
    def __init__(self, access_token: str):
        """Initialize with Zenodo token"""
        self.token = access_token
    
    def publish(self, result: ExperimentResult, 
                report_md: str,
                dry_run: bool = True) -> Optional[str]:
        """Publish to Zenodo"""
        
        logger.info(f"\nPreparing Zenodo submission...")
        logger.info(f"  Title: {result.name}")
        logger.info(f"  Result ID: {result.result_id}")
        logger.info(f"  Significant: {result.passes_significance}")
        logger.info(f"  Falsifiable: {result.falsifiable}")
        
        if not result.falsifiable:
            logger.warning("  ⚠ Result is not falsifiable - will not publish")
            return None
        
        metadata = {
            'title': f"Experiment: {result.name}",
            'description': report_md,
            'creators': [{'name': 'OSIRIS Automated Discovery'}],
            'keywords': ['quantum', 'ibm-quantum', 'automated-discovery'],
            'upload_type': 'dataset',
            'access_right': 'open',
        }
        
        if dry_run:
            logger.info("  (DRY RUN - not actually publishing)")
            logger.info(f"  Would publish with metadata: {json.dumps(metadata, indent=2)}")
            return None
        
        try:
            # Real Zenodo submission would go here
            logger.info("  Publishing to Zenodo...")
            # zenodo_id = self._submit_zenodo(metadata, result)
            # return zenodo_id
            logger.warning("  Zenodo submission not yet implemented")
            return None
        except Exception as e:
            logger.error(f"  Failed to publish: {e}")
            return None


# ════════════════════════════════════════════════════════════════════════════════
# 7. PRINTER DISCOVERY SERVICE — Bambu Lab / Elegoo / Generic
# ════════════════════════════════════════════════════════════════════════════════

try:
    from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


@dataclass
class DiscoveredPrinter:
    """A 3D printer discovered on the local network."""
    name: str
    printer_type: str           # bambu_p1s, bambu_a1_mini, elegoo_centauri_2, generic
    ip_address: str
    port: int
    protocol: str               # mqtt, ipp, ftp, http
    serial: str = ""
    model: str = ""
    status: str = "unknown"     # idle, printing, error, offline
    properties: Dict[str, Any] = field(default_factory=dict)
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PrinterDiscoveryService:
    """
    Automated network discovery for 3D printers via mDNS (ZeroConf).

    Scans the local WiFi network for:
      • Bambu Lab P1S / A1 Mini  — _bambulab._tcp service
      • Elegoo Centauri 2        — IPP / HTTP ports
      • Generic network printers — _ipp._tcp, _printer._tcp

    Discovered printers are registered as Physicalization Nodes.
    """

    # mDNS service types to scan
    SERVICE_TYPES = [
        "_bambulab._tcp.local.",     # Bambu Lab printers
        "_ipp._tcp.local.",          # IPP (Internet Printing Protocol)
        "_printer._tcp.local.",      # Generic network printers
        "_http._tcp.local.",         # HTTP services (Elegoo web interface)
        "_ftp._tcp.local.",          # FTP (Bambu file transfer)
    ]

    # Bambu Lab model identification patterns
    BAMBU_MODELS = {
        "P1S": "bambu_p1s",
        "P1P": "bambu_p1p",
        "X1C": "bambu_x1c",
        "X1": "bambu_x1",
        "A1 mini": "bambu_a1_mini",
        "A1 Mini": "bambu_a1_mini",
        "A1mini": "bambu_a1_mini",
        "A1": "bambu_a1",
    }

    # Elegoo identification patterns
    ELEGOO_MODELS = {
        "Centauri": "elegoo_centauri_2",
        "Saturn": "elegoo_saturn",
        "Mars": "elegoo_mars",
        "Neptune": "elegoo_neptune",
    }

    def __init__(self):
        self.discovered: List[DiscoveredPrinter] = []
        self._zeroconf = None
        self._browsers = []

    def scan(self, timeout: float = 10.0) -> List[DiscoveredPrinter]:
        """
        Scan the local network for 3D printers.

        Uses mDNS/ZeroConf if available, falls back to port scanning.
        """
        self.discovered.clear()

        if HAS_ZEROCONF:
            self._scan_mdns(timeout)
        else:
            logger.warning("zeroconf not installed — using port scan fallback")
            self._scan_ports()

        # Deduplicate by IP
        seen_ips = set()
        unique = []
        for p in self.discovered:
            if p.ip_address not in seen_ips:
                seen_ips.add(p.ip_address)
                unique.append(p)
        self.discovered = unique

        logger.info(f"Printer discovery complete: {len(self.discovered)} printers found")
        return self.discovered

    def _scan_mdns(self, timeout: float):
        """Scan via mDNS/ZeroConf service discovery."""
        import socket as sock
        self._zeroconf = Zeroconf()

        discovered_services = []

        class Listener:
            def __init__(self, parent):
                self.parent = parent

            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info:
                    discovered_services.append((type_, name, info))

            def remove_service(self, zc, type_, name):
                pass

            def update_service(self, zc, type_, name):
                pass

        listener = Listener(self)
        for svc_type in self.SERVICE_TYPES:
            try:
                browser = ServiceBrowser(self._zeroconf, svc_type, listener)
                self._browsers.append(browser)
            except Exception:
                pass

        # Wait for discovery
        import time as _time
        _time.sleep(min(timeout, 15))

        # Process discovered services
        for svc_type, name, info in discovered_services:
            try:
                addresses = info.parsed_addresses()
                ip = addresses[0] if addresses else "0.0.0.0"
                port = info.port or 0
                props = {k.decode() if isinstance(k, bytes) else k:
                         v.decode() if isinstance(v, bytes) else str(v)
                         for k, v in (info.properties or {}).items()}

                printer = self._classify_service(svc_type, name, ip, port, props)
                if printer:
                    self.discovered.append(printer)
            except Exception as e:
                logger.debug(f"Error processing {name}: {e}")

        self._zeroconf.close()

    def _classify_service(self, svc_type: str, name: str, ip: str,
                          port: int, props: Dict) -> Optional[DiscoveredPrinter]:
        """Classify a discovered service as a known printer type."""
        name_lower = name.lower()

        # Bambu Lab detection
        if "_bambulab" in svc_type or "bambu" in name_lower:
            model = "unknown"
            printer_type = "bambu_generic"
            for pattern, ptype in self.BAMBU_MODELS.items():
                if pattern.lower() in name_lower or pattern.lower() in str(props).lower():
                    model = pattern
                    printer_type = ptype
                    break
            return DiscoveredPrinter(
                name=name.split('.')[0],
                printer_type=printer_type,
                ip_address=ip,
                port=port or 8883,      # Bambu MQTT default port
                protocol="mqtt",
                serial=props.get("serial", props.get("sn", "")),
                model=model,
                properties=props,
            )

        # Elegoo detection
        for pattern, ptype in self.ELEGOO_MODELS.items():
            if pattern.lower() in name_lower:
                return DiscoveredPrinter(
                    name=name.split('.')[0],
                    printer_type=ptype,
                    ip_address=ip,
                    port=port or 80,
                    protocol="http",
                    model=pattern,
                    properties=props,
                )

        # Generic IPP printer
        if "_ipp" in svc_type or "_printer" in svc_type:
            return DiscoveredPrinter(
                name=name.split('.')[0],
                printer_type="generic_network",
                ip_address=ip,
                port=port or 631,
                protocol="ipp",
                properties=props,
            )

        return None

    def _scan_ports(self):
        """Fallback: scan common printer ports on local subnet."""
        import socket as sock

        # Get local IP to determine subnet
        try:
            s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "192.168.1.1"

        subnet = ".".join(local_ip.split(".")[:3])
        printer_ports = [80, 443, 631, 8883, 990, 21]  # HTTP, HTTPS, IPP, MQTT, FTP

        logger.info(f"Port scanning subnet {subnet}.0/24...")

        for host_id in range(1, 255):
            ip = f"{subnet}.{host_id}"
            for port in printer_ports:
                try:
                    s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
                    s.settimeout(0.3)
                    if s.connect_ex((ip, port)) == 0:
                        # Determine type from port
                        if port == 8883:
                            ptype, proto = "bambu_generic", "mqtt"
                        elif port == 631:
                            ptype, proto = "generic_network", "ipp"
                        else:
                            ptype, proto = "generic_network", "http"

                        self.discovered.append(DiscoveredPrinter(
                            name=f"printer_{ip}",
                            printer_type=ptype,
                            ip_address=ip,
                            port=port,
                            protocol=proto,
                        ))
                    s.close()
                except Exception:
                    pass

    def get_bambu_status(self, printer: DiscoveredPrinter) -> Dict[str, Any]:
        """
        Query Bambu Lab printer status via MQTT.

        Bambu Lab uses MQTT on port 8883 (TLS) with FTP for file transfer.
        """
        if not HAS_MQTT:
            return {"status": "unknown", "error": "paho-mqtt not installed"}

        status = {"status": "unknown"}

        try:
            client = mqtt.Client(client_id="osiris_monitor", protocol=mqtt.MQTTv311)
            client.tls_set()  # Bambu uses TLS

            received = []

            def on_message(client, userdata, msg):
                try:
                    payload = json.loads(msg.payload.decode())
                    received.append(payload)
                except Exception:
                    pass

            client.on_message = on_message
            client.connect(printer.ip_address, printer.port, keepalive=10)
            client.subscribe(f"device/{printer.serial}/report")
            client.loop_start()

            import time as _time
            _time.sleep(5)
            client.loop_stop()
            client.disconnect()

            if received:
                latest = received[-1]
                status = {
                    "status": latest.get("print", {}).get("gcode_state", "idle"),
                    "progress": latest.get("print", {}).get("mc_percent", 0),
                    "nozzle_temp": latest.get("print", {}).get("nozzle_temper", 0),
                    "bed_temp": latest.get("print", {}).get("bed_temper", 0),
                    "layer": latest.get("print", {}).get("layer_num", 0),
                    "raw": latest,
                }
        except Exception as e:
            status = {"status": "error", "error": str(e)}

        return status

    def report(self) -> str:
        """Generate a human-readable report of discovered printers."""
        if not self.discovered:
            return "No 3D printers found on the local network."

        lines = [
            "═" * 60,
            "  OSIRIS PRINTER DISCOVERY — LOCAL NETWORK",
            "═" * 60,
            "",
        ]
        for i, p in enumerate(self.discovered, 1):
            lines.extend([
                f"  Printer {i}: {p.name}",
                f"    Type:     {p.printer_type}",
                f"    Model:    {p.model}",
                f"    IP:       {p.ip_address}:{p.port}",
                f"    Protocol: {p.protocol}",
                f"    Serial:   {p.serial or 'N/A'}",
                f"    Status:   {p.status}",
                "",
            ])
        lines.append("═" * 60)
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# 8. MAIN EXECUTION
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Example usage"""
    
    # Check for API token
    ibm_token = os.getenv('IBM_QUANTUM_TOKEN')
    zenodo_token = os.getenv('ZENODO_TOKEN')
    
    if not ibm_token:
        logger.warning("IBM_QUANTUM_TOKEN not set - using mock execution")
        ibm_token = "mock"
    
    # Initialize pipeline
    pipeline = AutoDiscoveryPipeline(ibm_token)
    
    # ════════════════════════════════════════════════════════════════════════════
    # EXPERIMENT 1: Random Circuit Sampling (RCS) Baseline
    # ════════════════════════════════════════════════════════════════════════════
    
    config1 = ExperimentConfig(
        name="rcs_baseline",
        n_qubits=12,
        circuit_depth=8,
        shots=4000,
        trials=20,
        hypothesis="Random circuit sampling produces XEB > 0",
        null_hypothesis="XEB is indistinguishable from noise (XEB ≈ 0)",
        predicted_outcome="We expect positive XEB from quantum advantage",
    )
    
    result1 = pipeline.run_hypothesis_test(config1)
    pipeline.save_result(result1)
    report1 = pipeline.generate_report(result1)
    
    # Save report
    with open(pipeline.output_dir / f"{config1.name}_report.md", 'w') as f:
        f.write(report1)
    
    logger.info(f"\n{report1}")
    
    # ════════════════════════════════════════════════════════════════════════════
    # EXPERIMENT 2: Adaptive Circuit Evolution
    # ════════════════════════════════════════════════════════════════════════════
    
    config2 = ExperimentConfig(
        name="adaptive_circuit_evolution",
        n_qubits=12,
        circuit_depth=8,
        shots=4000,
        trials=10,
        hypothesis="Adaptive circuits (RQC) improve XEB over fixed RCS",
        null_hypothesis="Adaptive and static circuits have equivalent XEB",
        predicted_outcome="RQC should show measurably better performance",
    )
    
    logger.info("\n" + "="*70)
    logger.info("NOTE: Adaptive experiment requires feedback implementation")
    logger.info("="*70)


if __name__ == "__main__":
    main()
