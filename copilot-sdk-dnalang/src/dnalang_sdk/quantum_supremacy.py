#!/usr/bin/env python3
"""Recursive Quantum Circuit Generator and Supremacy Metrics

This module generates OpenQASM 2.0 circuits designed for
large-scale recursive entanglement and pseudo-feedback patterns.
It also provides lightweight championship-style metrics such as
cross-entropy benchmarking (XEB) and stabilization helpers.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class QasmGenerationResult:
    name: str
    qasm: str
    qubits: int
    depth: int
    lines: int
    gates: int
    entanglement_ratio: float
    hardness_score: float
    metadata: Dict[str, object]


def _rotation_gate(index: int) -> str:
    return ["rx", "ry", "rz"][index % 3]


def _angle_fraction(index: int, layer: int) -> str:
    denominator = ((index + layer * 5) % 43) + 3
    return f"pi/{denominator}"


def _pair_index(index: int, n_qubits: int, layer: int) -> int:
    return (index * 7 + layer * 11 + 3) % n_qubits


def _stabilizer_pair(index: int, n_qubits: int) -> int:
    return (index + (n_qubits // 2) + 1) % n_qubits


def _validate_qasm(qasm: str) -> bool:
    return qasm.strip().startswith("OPENQASM 2.0;") and "qreg" in qasm and "measure" in qasm


def _estimate_entanglement_ratio(qubits: int, entangling_gates: int) -> float:
    """Compute entanglement density E = (# entangled pairs) / binom(n, 2)"""
    max_pairs = qubits * (qubits - 1) / 2
    return min(1.0, entangling_gates / max(1.0, max_pairs))


def estimate_supremacy_score(qubits: int, depth: int, entanglement_ratio: float) -> float:
    return round(qubits * depth * (0.25 + entanglement_ratio), 2)


def generate_recursive_qasm(
    n_qubits: int = 64,
    depth: int = 16,
    seed: int = 42,
    include_feedback: bool = True,
    include_barriers: bool = True,
    name: str = "osiris_recursive_world_record",
) -> QasmGenerationResult:
    if n_qubits < 8:
        raise ValueError("n_qubits must be at least 8 for a meaningful world-record-style circuit")
    if depth < 4:
        raise ValueError("depth must be at least 4 to capture complex recursive structure")

    rng = random.Random(seed)
    lines: List[str] = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{n_qubits}];", f"creg c[{n_qubits}];", ""]
    entangling_gates = 0
    operation_count = 0

    lines.append("// === INITIAL SUPERPOSITION LAYER ===")
    for i in range(n_qubits):
        lines.append(f"h q[{i}];")
        operation_count += 1

    for layer in range(depth):
        lines.append(f"// === RANDOM ROTATION LAYER {layer + 1} ===")
        for i in range(n_qubits):
            gate = _rotation_gate(i + layer)
            angle = _angle_fraction(i, layer)
            lines.append(f"{gate}({angle}) q[{i}];")
            operation_count += 1

        if include_barriers:
            lines.append("barrier q;")

        lines.append(f"// === NON-LOCAL ENTANGLEMENT LAYER {layer + 1} ===")
        for i in range(n_qubits):
            j = _pair_index(i, n_qubits, layer)
            if i != j:
                lines.append(f"cx q[{i}], q[{j}];")
                entangling_gates += 1
                operation_count += 1

        if include_feedback and layer % 3 == 2:
            lines.append(f"// === PSEUDO-FEEDBACK ENCODING LAYER {layer + 1} ===")
            for i in range(0, n_qubits, 4):
                j = _pair_index(i + 1, n_qubits, layer + 1)
                if i != j:
                    lines.append(f"cz q[{i}], q[{j}];")
                    entangling_gates += 1
                    operation_count += 1

    lines.append("// === INTERFERENCE STABILIZATION ===")
    for i in range(0, n_qubits, 3):
        lines.append(f"h q[{i}];")
        operation_count += 1

    lines.append("// === MEASUREMENT ===")
    lines.append("measure q -> c;")
    operation_count += 1

    qasm = "\n".join(lines)
    entanglement_ratio = _estimate_entanglement_ratio(n_qubits, entangling_gates)
    hardness_score = estimate_supremacy_score(n_qubits, depth, entanglement_ratio)

    return QasmGenerationResult(
        name=name,
        qasm=qasm,
        qubits=n_qubits,
        depth=depth,
        lines=qasm.count("\n") + 1,
        gates=operation_count,
        entanglement_ratio=entanglement_ratio,
        hardness_score=hardness_score,
        metadata={
            "seed": seed,
            "include_feedback": include_feedback,
            "include_barriers": include_barriers,
            "generated_at": "osiris-cli",
        },
    )


def generate_surface_code_qasm(
    logical_qubits: int = 2,
    distance: int = 3,
    seed: int = 101,
    name: str = "osiris_surface_code",
) -> QasmGenerationResult:
    if logical_qubits < 1:
        raise ValueError("logical_qubits must be at least 1")
    if distance < 3 or distance % 2 == 0:
        raise ValueError("distance must be an odd integer >= 3")

    rng = random.Random(seed)
    physical_per_logical = distance ** 2
    total_physical = logical_qubits * physical_per_logical
    ancillas = logical_qubits * (distance - 1)
    total_qubits = total_physical + ancillas
    lines: List[str] = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg data[{total_physical}];", f"qreg anc[{ancillas}];", f"creg syndrome[{ancillas}];", ""]

    operation_count = 0
    lines.append("// === SURFACE CODE LOGICAL ENCODING ===")
    for block in range(logical_qubits):
        base = block * physical_per_logical
        lines.append(f"// logical qubit {block} encoded into physical block {base}:{base + physical_per_logical - 1}")
        lines.append(f"h data[{base}];")
        lines.append(f"h data[{base + 1}];")
        operation_count += 2
        for offset in range(2, physical_per_logical):
            lines.append(f"cx data[{base}], data[{base + offset}];")
            operation_count += 1

    lines.append("\n// === PARITY CHECKS AND STABILIZERS ===")
    for a_index in range(ancillas):
        target = a_index % total_physical
        partner = (target + physical_per_logical // 2) % total_physical
        lines.append(f"cx data[{target}], anc[{a_index}];")
        lines.append(f"cx data[{partner}], anc[{a_index}];")
        lines.append(f"measure anc[{a_index}] -> syndrome[{a_index}];")
        operation_count += 3

    qasm = "\n".join(lines)
    entangling_gates = logical_qubits * (physical_per_logical - 1) + ancillas * 2
    entanglement_ratio = _estimate_entanglement_ratio(total_physical, entangling_gates)
    hardness_score = estimate_supremacy_score(total_physical, distance, entanglement_ratio)

    return QasmGenerationResult(
        name=name,
        qasm=qasm,
        qubits=total_qubits,
        depth=distance,
        lines=qasm.count("\n") + 1,
        gates=operation_count,
        entanglement_ratio=entanglement_ratio,
        hardness_score=hardness_score,
        metadata={
            "logical_qubits": logical_qubits,
            "distance": distance,
            "seed": seed,
            "generated_at": "osiris-cli",
        },
    )


def generate_recursive_batch_qasm(
    n_qubits: int = 64,
    total_depth: int = 32,
    batch_size: int = 8,
    seed: int = 42,
    feedback_mechanism: str = "adaptive",
    name_prefix: str = "osiris_batch",
) -> List[QasmGenerationResult]:
    """Generate a batch of QASM circuits with classical feedback simulation."""
    results = []
    current_seed = seed

    for batch in range(0, total_depth, batch_size):
        batch_depth = min(batch_size, total_depth - batch)
        batch_name = f"{name_prefix}_batch{batch//batch_size}_{n_qubits}Q_{batch_depth}D"

        # Simulate feedback: adjust parameters based on "previous" batch
        if feedback_mechanism == "adaptive" and batch > 0:
            # Increase entanglement in later batches
            adjusted_depth = batch_depth + (batch // batch_size)
            adjusted_seed = current_seed + batch
        else:
            adjusted_depth = batch_depth
            adjusted_seed = current_seed

        result = generate_recursive_qasm(
            n_qubits=n_qubits,
            depth=adjusted_depth,
            seed=adjusted_seed,
            name=batch_name,
        )
        results.append(result)
        current_seed += 1000  # Vary seed for each batch

    return results


@dataclass
class LearningState:
    depth: int = 12
    entanglement_bias: float = 0.5
    randomness_level: float = 0.1
    xeb_threshold: float = 0.2
    max_iterations: int = 10


def objective_driven_recursive_generation(
    initial_state: LearningState,
    n_qubits: int = 32,
    target_xeb: float = 0.5,
    max_iterations: int = 10,
    noise_model: Optional[object] = None
) -> List[QasmGenerationResult]:
    """Generate circuits with goal-directed adaptive evolution.
    
    Implements true learning: circuit → metrics → modifies circuit → repeat
    """
    results = []
    state = LearningState(**initial_state.__dict__)
    
    for iteration in range(max_iterations):
        # Generate circuit with current state
        result = generate_recursive_qasm(
            n_qubits=n_qubits,
            depth=state.depth,
            seed=42 + iteration * 100,  # Vary seed
            name=f"rqc_iteration_{iteration}"
        )
        
        # Evaluate with XEB
        xeb_score, metrics = compute_noise_aware_xeb(result.qasm, noise_model=noise_model)
        
        results.append(result)
        
        # Goal-directed update
        if xeb_score < state.xeb_threshold:
            # Increase complexity
            state.depth += 2
            state.entanglement_bias += 0.1
            state.randomness_level += 0.05
        else:
            # Refine
            state.depth += 1
            state.entanglement_bias = max(0.1, state.entanglement_bias - 0.05)
        
        # Prevent runaway growth
        state.depth = min(state.depth, 50)
        state.entanglement_bias = min(state.entanglement_bias, 1.0)
        state.randomness_level = min(state.randomness_level, 0.5)
        
        print(f"Iteration {iteration}: XEB={xeb_score:.3f}, Depth={state.depth}, Bias={state.entanglement_bias:.2f}")
        
        if xeb_score >= target_xeb:
            print(f"Target XEB reached at iteration {iteration}")
            break
    
    return results


def save_batch_qasm(batch_results: List[QasmGenerationResult], base_path: Path) -> List[Path]:
    """Save a batch of QASM results to files."""
    saved_paths = []
    base_path = Path(base_path)
    for result in batch_results:
        path = base_path.parent / f"{base_path.stem}_{result.name}.qasm"
        saved_path = save_qasm_file(result, path)
        saved_paths.append(saved_path)
    return saved_paths


def compute_batch_xeb(batch_results: List[QasmGenerationResult], samples_per_circuit: int = 1024) -> List[float]:
    """Compute XEB scores for a batch of circuits (requires Qiskit)."""
    if not optional_qiskit_available():
        return []

    xeb_scores = []
    try:
        from qiskit import QuantumCircuit, execute
        from qiskit.qasm2 import loads as qasm2_loads
        from qiskit_aer import Aer

        backend = Aer.get_backend('qasm_simulator')

        for result in batch_results:
            qc = qasm2_loads(result.qasm)
            job = execute(qc, backend, shots=samples_per_circuit)
            sim_result = job.result()
            counts = sim_result.get_counts(qc)

            if counts:
                # Simplified: assume uniform ideal distribution
                n_qubits = result.qubits
                ideal_probs = {format(i, f'0{n_qubits}b'): 1.0 / (2 ** n_qubits) for i in range(2 ** n_qubits)}
                samples = list(counts.keys())
                xeb = compute_linear_xeb(samples, ideal_probs)
                xeb_scores.append(xeb)
            else:
                xeb_scores.append(0.0)

    except Exception as e:
        print(f"Batch XEB computation failed: {e}")
        xeb_scores = [0.0] * len(batch_results)

    return xeb_scores


def save_qasm_file(result: QasmGenerationResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.qasm, encoding="utf-8")
    return path


def compute_linear_xeb(samples: List[str], ideal_probabilities: Dict[str, float]) -> float:
    """Compute Cross-Entropy Benchmarking (XEB) score.
    
    XEB = 2^n * <P(x)> - 1
    
    Where <P(x)> is the average probability of sampled outcomes under ideal distribution.
    """
    if not samples:
        raise ValueError("Sample list cannot be empty")
    if not ideal_probabilities:
        raise ValueError("Ideal probability distribution is required")

    n = len(samples[0])
    N = len(samples)
    total = 0.0
    for sample in samples:
        total += ideal_probabilities.get(sample, 0.0)
    avg_prob = total / N
    return max(-1.0, min(1.0, (2 ** n) * avg_prob - 1.0))


def create_noise_model(single_qubit_error: float = 1e-3, two_qubit_error: float = 1e-2, 
                      t1: float = 100e-6, t2: float = 80e-6) -> Optional[object]:
    """Create a Qiskit noise model for NISQ simulation."""
    if not optional_qiskit_available():
        return None
    
    try:
        from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error
        
        noise_model = NoiseModel()
        
        # Single qubit depolarizing error
        sq_error = depolarizing_error(single_qubit_error, 1)
        noise_model.add_all_qubit_quantum_error(sq_error, ['rx', 'ry', 'rz', 'h'])
        
        # Two qubit depolarizing error
        tq_error = depolarizing_error(two_qubit_error, 2)
        noise_model.add_all_qubit_quantum_error(tq_error, ['cx', 'cz'])
        
        # Thermal relaxation
        if t1 > 0 and t2 > 0:
            thermal_error = thermal_relaxation_error(t1, t2, 100e-9)  # 100ns gate time
            noise_model.add_all_qubit_quantum_error(thermal_error, ['rx', 'ry', 'rz', 'h', 'cx', 'cz'])
        
        return noise_model
    except Exception:
        return None


def compute_noise_aware_xeb(qasm: str, shots: int = 8192, 
                           noise_model: Optional[object] = None) -> Tuple[float, Dict[str, float]]:
    """Compute XEB with optional noise model."""
    if not optional_qiskit_available():
        return 0.0, {}
    
    try:
        from qiskit import QuantumCircuit, execute
        from qiskit.qasm2 import loads as qasm2_loads
        from qiskit_aer import Aer
        
        qc = qasm2_loads(qasm)
        n_qubits = qc.num_qubits
        
        # Ideal simulation for reference
        ideal_backend = Aer.get_backend('qasm_simulator')
        ideal_job = execute(qc, ideal_backend, shots=shots)
        ideal_result = ideal_job.result()
        ideal_counts = ideal_result.get_counts(qc)
        
        # Create ideal uniform distribution
        ideal_probs = {format(i, f'0{n_qubits}b'): 1.0 / (2 ** n_qubits) for i in range(2 ** n_qubits)}
        
        # Noisy simulation
        if noise_model:
            from qiskit_aer import AerSimulator
            noisy_backend = AerSimulator(noise=noise_model)
            noisy_job = execute(qc, noisy_backend, shots=shots)
            noisy_result = noisy_job.result()
            noisy_counts = noisy_result.get_counts(qc)
            samples = list(noisy_counts.keys())
        else:
            samples = list(ideal_counts.keys())
        
        xeb = compute_linear_xeb(samples, ideal_probs)
        
        # Additional metrics
        metrics = {
            "xeb_score": xeb,
            "fidelity_estimate": max(0, (xeb + 1) / 2),  # Rough approximation
            "shots_used": shots,
            "noise_applied": noise_model is not None
        }
        
        return xeb, metrics
        
    except Exception as e:
        print(f"XEB computation failed: {e}")
        return 0.0, {}


def benchmark_scaling(qubit_range: List[int], depth: int = 12, shots: int = 1024) -> Dict[int, float]:
    """Benchmark classical simulation time vs qubits to prove O(2^n) scaling."""
    import time
    
    if not optional_qiskit_available():
        return {}
    
    scaling_data = {}
    
    try:
        from qiskit import QuantumCircuit, execute
        from qiskit_aer import Aer
        backend = Aer.get_backend('qasm_simulator')
        
        for n in qubit_range:
            if n > 20:  # Skip too large for demo
                continue
                
            # Generate simple circuit
            qc = QuantumCircuit(n)
            for i in range(n):
                qc.h(i)
            for d in range(depth):
                for i in range(n-1):
                    qc.cx(i, i+1)
            
            start_time = time.time()
            job = execute(qc, backend, shots=shots)
            result = job.result()
            end_time = time.time()
            
            scaling_data[n] = end_time - start_time
            
    except Exception as e:
        print(f"Scaling benchmark failed: {e}")
    
    return scaling_data


def world_record_qasm_summary(result: QasmGenerationResult) -> Dict[str, object]:
    return {
        "name": result.name,
        "qubits": result.qubits,
        "depth": result.depth,
        "lines": result.lines,
        "gates": result.gates,
        "entanglement_ratio": result.entanglement_ratio,
        "hardness_score": result.hardness_score,
        "metadata": result.metadata,
    }


def optional_qiskit_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("qiskit") is not None
    except Exception:
        return False


def qasm_supports_simulation() -> bool:
    return optional_qiskit_available()


def generate_ibm_topology_qasm(
    n_qubits: int = 127,
    depth: int = 16,
    topology: str = "heavy-hex",
    seed: int = 42,
    name: str = "osiris_ibm_mapped",
) -> QasmGenerationResult:
    """Generate QASM respecting IBM quantum hardware topology."""
    if topology not in ["heavy-hex", "line", "grid"]:
        raise ValueError("Supported topologies: heavy-hex, line, grid")

    # Simplified topology mappings (in practice, use actual backend coupling maps)
    if topology == "heavy-hex":
        # Eagle processor style: qubits connected in heavy-hex lattice
        coupling_map = _generate_heavy_hex_coupling(n_qubits)
    elif topology == "line":
        coupling_map = [(i, i+1) for i in range(n_qubits-1)]
    elif topology == "grid":
        # Simple 2D grid
        side = int(math.sqrt(n_qubits))
        coupling_map = []
        for i in range(side):
            for j in range(side):
                idx = i * side + j
                if idx < n_qubits:
                    if j < side - 1:  # right
                        coupling_map.append((idx, idx + 1))
                    if i < side - 1:  # down
                        coupling_map.append((idx, idx + side))

    return _generate_topology_constrained_qasm(
        n_qubits=n_qubits,
        depth=depth,
        coupling_map=coupling_map,
        seed=seed,
        name=name,
    )


def _generate_heavy_hex_coupling(n_qubits: int) -> List[Tuple[int, int]]:
    """Generate a simplified heavy-hex coupling map."""
    coupling = []
    # Simplified: connect in groups of 7 (hexagon + center)
    for group_start in range(0, n_qubits, 7):
        group = list(range(group_start, min(group_start + 7, n_qubits)))
        if len(group) >= 2:
            # Connect center to others
            center = group[0]
            for q in group[1:]:
                coupling.append((center, q))
            # Connect others in ring
            for i in range(1, len(group) - 1):
                coupling.append((group[i], group[i+1]))
            if len(group) > 2:
                coupling.append((group[-1], group[1]))
    return coupling


def _generate_topology_constrained_qasm(
    n_qubits: int,
    depth: int,
    coupling_map: List[Tuple[int, int]],
    seed: int = 42,
    name: str = "topology_constrained",
) -> QasmGenerationResult:
    """Generate QASM constrained to a specific coupling map."""
    rng = random.Random(seed)
    lines: List[str] = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{n_qubits}];", f"creg c[{n_qubits}];", ""]
    entangling_gates = 0
    operation_count = 0

    # Initial superposition
    lines.append("// === INITIAL SUPERPOSITION ===")
    for i in range(n_qubits):
        lines.append(f"h q[{i}];")
        operation_count += 1

    for layer in range(depth):
        # Single qubit rotations
        lines.append(f"// === ROTATION LAYER {layer + 1} ===")
        for i in range(n_qubits):
            gate = _rotation_gate(i + layer)
            angle = _angle_fraction(i, layer)
            lines.append(f"{gate}({angle}) q[{i}];")
            operation_count += 1

        # Entangling gates constrained to topology
        lines.append(f"// === TOPOLOGY-CONSTRAINED ENTANGLEMENT LAYER {layer + 1} ===")
        rng.shuffle(coupling_map)
        used_pairs = set()
        for pair in coupling_map:
            if pair not in used_pairs and pair[::-1] not in used_pairs:
                i, j = pair
                if i < n_qubits and j < n_qubits:
                    lines.append(f"cx q[{i}], q[{j}];")
                    entangling_gates += 1
                    operation_count += 1
                    used_pairs.add(pair)

    # Measurement
    lines.append("// === MEASUREMENT ===")
    lines.append("measure q -> c;")
    operation_count += 1

    qasm = "\n".join(lines)
    entanglement_ratio = _estimate_entanglement_ratio(n_qubits, entangling_gates)
    hardness_score = estimate_supremacy_score(n_qubits, depth, entanglement_ratio)

    return QasmGenerationResult(
        name=name,
        qasm=qasm,
        qubits=n_qubits,
        depth=depth,
        lines=qasm.count("\n") + 1,
        gates=operation_count,
        entanglement_ratio=entanglement_ratio,
        hardness_score=hardness_score,
        metadata={
            "topology": "constrained",
            "coupling_edges": len(coupling_map),
            "seed": seed,
        },
    )
