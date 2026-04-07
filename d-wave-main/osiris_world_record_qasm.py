#!/usr/bin/env python3
"""OSIRIS World-Record OpenQASM Generator

Generates large-scale recursive OpenQASM 2.0 circuits for quantum
benchmarking, stabilization, and recursive control experiments.

Usage:
  python osiris_world_record_qasm.py --qubits 64 --depth 18 --save world_record.qasm
  python osiris_world_record_qasm.py --surface-code --logical-qubits 3 --distance 3 --save surface_code.qasm
"""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import Optional

from dnalang_sdk.quantum_supremacy import (
    QasmGenerationResult,
    compute_batch_xeb,
    compute_linear_xeb,
    create_noise_model,
    compute_noise_aware_xeb,
    generate_ibm_topology_qasm,
    generate_recursive_batch_qasm,
    generate_recursive_qasm,
    generate_surface_code_qasm,
    objective_driven_recursive_generation,
    LearningState,
    optional_qiskit_available,
    save_batch_qasm,
    save_qasm_file,
    world_record_qasm_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate OSIRIS world-record OpenQASM 2.0 circuits",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--qubits", type=int, default=64, help="Number of qubits for the recursive circuit")
    parser.add_argument("--depth", type=int, default=18, help="Depth of the recursive circuit")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for gate generation")
    parser.add_argument("--surface-code", action="store_true", help="Generate a surface code stabilization circuit instead")
    parser.add_argument("--logical-qubits", type=int, default=2, help="Number of logical qubits in surface code generation")
    parser.add_argument("--distance", type=int, default=3, help="Code distance for surface code generation")
    parser.add_argument("--topology", type=str, choices=["heavy-hex", "line", "grid"], help="Hardware topology to constrain the circuit to (for IBM-style backends)")
    parser.add_argument("--batch", action="store_true", help="Generate a batch of circuits with recursive feedback")
    parser.add_argument("--batch-size", type=int, default=8, help="Depth of each batch in recursive batch mode")
    parser.add_argument("--feedback", type=str, default="adaptive", choices=["adaptive", "fixed"], help="Feedback mechanism for batch generation")
    parser.add_argument("--learning", action="store_true", help="Use objective-driven recursive learning generation")
    parser.add_argument("--target-xeb", type=float, default=0.5, help="Target XEB score for learning mode")
    parser.add_argument("--max-iterations", type=int, default=10, help="Maximum iterations for learning mode")
    parser.add_argument("--ibm-backend", type=str, help="IBM Quantum backend name (e.g., 'ibm_kyoto', 'ibm_osaka')")
    parser.add_argument("--ibm-token", type=str, help="IBM Quantum API token (or set IBM_QUANTUM_TOKEN env var)")
    parser.add_argument("--zenodo-token", type=str, help="Zenodo API token for publishing (or set ZENODO_TOKEN env var)")
    parser.add_argument("--noise-aware", action="store_true", help="Include noise model in XEB computation")
    parser.add_argument("--save", type=str, default="world_record.qasm", help="Path to save generated QASM")
    parser.add_argument("--summary", type=str, default="world_record_summary.json", help="Path to save summary metadata")
    parser.add_argument("--simulate", action="store_true", help="Attempt a local simulation if Qiskit is available")
    parser.add_argument("--samples", type=int, default=1024, help="Number of samples to use in simulated measurement analysis")

    return parser.parse_args()


def execute_on_ibm(qasm: str, backend_name: str, token: str, shots: int = 8192) -> Optional[dict]:
    """Execute QASM circuit on IBM Quantum hardware."""
    if not optional_qiskit_available():
        print("Qiskit not available for IBM execution.")
        return None
    
    try:
        from qiskit import QuantumCircuit, transpile, execute
        from qiskit.qasm2 import loads as qasm2_loads
        from qiskit_ibm_provider import IBMProvider
        
        # Initialize provider
        provider = IBMProvider(token=token)
        backend = provider.get_backend(backend_name)
        
        # Load and transpile circuit
        qc = qasm2_loads(qasm)
        transpiled = transpile(qc, backend, optimization_level=3)
        
        print(f"Transpiled circuit: {transpiled.depth()} depth, {transpiled.size()} gates")
        
        # Execute
        job = execute(transpiled, backend, shots=shots)
        print(f"Job submitted: {job.job_id()}")
        
        # Wait for completion (this might take time)
        result = job.result()
        counts = result.get_counts()
        
        # Compute XEB
        n_qubits = qc.num_qubits
        ideal_probs = {format(i, f'0{n_qubits}b'): 1.0 / (2 ** n_qubits) for i in range(2 ** n_qubits)}
        samples = list(counts.keys())
        xeb = compute_linear_xeb(samples, ideal_probs)
        
        return {
            "job_id": job.job_id(),
            "backend": backend_name,
            "shots": shots,
            "xeb_score": xeb,
            "counts": counts,
            "transpiled_depth": transpiled.depth(),
            "transpiled_gates": transpiled.size(),
            "execution_time": result.time_taken
        }
        
    except Exception as e:
        print(f"IBM execution failed: {e}")
        return None


def publish_to_zenodo(metadata: dict, files: list, token: str) -> Optional[str]:
    """Publish results to Zenodo."""
    # Placeholder for Zenodo API integration
    print("Zenodo publishing not yet implemented.")
    return None


def main() -> None:
    args = parse_args()

    if args.surface_code:
        print(f"Generating surface code QASM with {args.logical_qubits} logical qubits, distance {args.distance}...")
        result = generate_surface_code_qasm(
            logical_qubits=args.logical_qubits,
            distance=args.distance,
            seed=args.seed,
            name=f"osiris_surface_code_{args.logical_qubits}L_{args.distance}D",
        )
        results = [result]
    elif args.learning:
        print(f"Generating with objective-driven learning: {args.qubits} qubits, target XEB {args.target_xeb}...")
        noise_model = create_noise_model() if args.noise_aware else None
        initial_state = LearningState(depth=args.depth, max_iterations=args.max_iterations)
        results = objective_driven_recursive_generation(
            initial_state=initial_state,
            n_qubits=args.qubits,
            target_xeb=args.target_xeb,
            max_iterations=args.max_iterations,
            noise_model=noise_model
        )
    elif args.topology:
        print(f"Generating topology-constrained QASM with {args.qubits} qubits, depth {args.depth}, topology {args.topology}...")
        result = generate_ibm_topology_qasm(
            n_qubits=args.qubits,
            depth=args.depth,
            topology=args.topology,
            seed=args.seed,
            name=f"osiris_{args.topology}_{args.qubits}Q_{args.depth}D",
        )
        results = [result]
    elif args.batch:
        print(f"Generating recursive batch QASM with {args.qubits} qubits, total depth {args.depth}, batch size {args.batch_size}...")
        results = generate_recursive_batch_qasm(
            n_qubits=args.qubits,
            total_depth=args.depth,
            batch_size=args.batch_size,
            seed=args.seed,
            feedback_mechanism=args.feedback,
            name_prefix=f"osiris_batch_{args.qubits}Q",
        )
    else:
        print(f"Generating recursive QASM with {args.qubits} qubits, depth {args.depth}...")
        result = generate_recursive_qasm(
            n_qubits=args.qubits,
            depth=args.depth,
            seed=args.seed,
            name=f"osiris_recursive_{args.qubits}Q_{args.depth}D",
        )
        results = [result]

    # Save QASM files
    if len(results) == 1:
        qasm_path = Path(args.save)
        saved_paths = [save_qasm_file(results[0], qasm_path)]
        print(f"QASM saved to: {saved_paths[0]}")
    else:
        base_path = Path(args.save)
        saved_paths = save_batch_qasm(results, base_path)
        print(f"Batch QASM saved to: {', '.join(str(p) for p in saved_paths)}")

    # Save summaries
    summaries = [world_record_qasm_summary(r) for r in results]
    summary_path = Path(args.summary)
    if len(summaries) == 1:
        summary_path.write_text(json.dumps(summaries[0], indent=2), encoding="utf-8")
        print(f"Summary saved to: {summary_path}")
    else:
        batch_summary = {"batch_info": {"total_circuits": len(results), "total_qubits": args.qubits}, "circuits": summaries}
        summary_path.write_text(json.dumps(batch_summary, indent=2), encoding="utf-8")
        print(f"Batch summary saved to: {summary_path}")

    # Print summaries
    for i, result in enumerate(results):
        if len(results) > 1:
            print(f"\n=== CIRCUIT {i+1} SUMMARY ===")
        else:
            print("\n=== CIRCUIT SUMMARY ===")
        print(f"Name: {result.name}")
        print(f"Qubits: {result.qubits}")
        print(f"Depth: {result.depth}")
        print(f"Lines: {result.lines}")
        print(f"Gates: {result.gates}")
        print(f"Entanglement Ratio: {result.entanglement_ratio:.3f}")
        print(f"Hardness Score: {result.hardness_score:.2f}")

    # Optional simulation
    if args.simulate:
        if len(results) == 1 and optional_qiskit_available():
            print("\n=== SIMULATION ATTEMPT ===")
            try:
                from qiskit import QuantumCircuit, execute
                from qiskit.qasm2 import loads as qasm2_loads
                from qiskit_aer import Aer

                qc = qasm2_loads(results[0].qasm)
                backend = Aer.get_backend('qasm_simulator')
                job = execute(qc, backend, shots=args.samples)
                result_sim = job.result()
                counts = result_sim.get_counts(qc)

                if counts:
                    n_qubits = results[0].qubits
                    ideal_probs = {format(i, f'0{n_qubits}b'): 1.0 / (2 ** n_qubits) for i in range(2 ** n_qubits)}
                    samples = list(counts.keys())
                    xeb_score = compute_linear_xeb(samples, ideal_probs)
                    print(f"XEB Score: {xeb_score:.4f}")
                else:
                    print("No measurement results from simulation.")

            except Exception as e:
                print(f"Simulation failed: {e}")
        elif len(results) > 1 and optional_qiskit_available():
            print("\n=== BATCH SIMULATION ATTEMPT ===")
            xeb_scores = compute_batch_xeb(results, args.samples)
            for i, xeb in enumerate(xeb_scores):
                print(f"Circuit {i+1} XEB Score: {xeb:.4f}")
        elif not optional_qiskit_available():
            print("Qiskit not available, skipping simulation.")

    # IBM Hardware Execution
    if args.ibm_backend:
        token = args.ibm_token or os.getenv("IBM_QUANTUM_TOKEN") or "1DkOsJN8ik9nlvPCVVsr2A8XxC9QbyyJNJFDy69Gc1k3"
        if len(results) == 1:
            print(f"\n=== IBM HARDWARE EXECUTION: {args.ibm_backend} ===")
            ibm_result = execute_on_ibm(results[0].qasm, args.ibm_backend, token, args.samples)
            if ibm_result:
                print(f"Job ID: {ibm_result['job_id']}")
                print(f"XEB Score: {ibm_result['xeb_score']:.4f}")
                print(f"Transpiled Depth: {ibm_result['transpiled_depth']}")
                print(f"Transpiled Gates: {ibm_result['transpiled_gates']}")
                
                # Save IBM results
                ibm_summary_path = Path(args.summary).with_suffix('.ibm.json')
                ibm_summary_path.write_text(json.dumps(ibm_result, indent=2), encoding="utf-8")
                print(f"IBM results saved to: {ibm_summary_path}")
        else:
            print("IBM execution only supported for single circuits (not batches).")

    # Zenodo Publishing
    if args.zenodo_token or os.getenv("ZENODO_TOKEN"):
        token = args.zenodo_token or os.getenv("ZENODO_TOKEN") or "4MDB7r2vJXoFL2rHqgzvReu4yDdU1kfeI37i4doSUoxNT0IbwEr1Zm77vxPi"
        print("\n=== ZENODO PUBLISHING ===")
        zenodo_result = publish_to_zenodo({"title": "OSIRIS RQC Results"}, saved_paths, token)
        if zenodo_result:
            print(f"Published to Zenodo: {zenodo_result}")


if __name__ == "__main__":
    main()
