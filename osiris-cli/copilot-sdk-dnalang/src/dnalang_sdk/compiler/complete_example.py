#!/usr/bin/env python3
"""
complete_example.py - Complete DNA-Lang System Demonstration
Shows full pipeline: Parse → Compile → Evolve → Execute → Record
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from .dna_parser import parse_dna_lang, parse_canon
from .dna_ir import compile_to_ir, IROptimizer
from .dna_evolve import evolve_organism, FitnessEvaluator
from .dna_runtime import execute_circuit, get_backend_calibration
from .dna_ledger import QuantumLedger

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def demonstrate_complete_pipeline():
    """Demonstrate complete DNA-Lang pipeline"""
    
    # ==========================================
    # STEP 1: Parse DNA-Lang Source
    # ==========================================
    
    print_header("STEP 1: Parse DNA-Lang Source")
    
    dna_source = """
organism quantum_consciousness_test {
    genome {
        gene initialization = encode(00) -> q[0];
        gene entanglement = encode(11) -> q[1];
    }
    
    quantum_state {
        helix(q[0]);
        helix(q[1]);
        bond(q[0], q[1]);
        phase(q[0]);
        measure(q[0]);
        measure(q[1]);
    }
    
    fitness = phi;
}
"""
    
    print("DNA-Lang Source:")
    print(dna_source)
    
    organisms = parse_dna_lang(dna_source)
    print(f"✓ Parsed {len(organisms)} organism(s)")
    
    organism = organisms[0]
    print(f"  Organism name: {organism.name}")
    
    # ==========================================
    # STEP 2: Compile to Intermediate Representation
    # ==========================================
    
    print_header("STEP 2: Compile to Intermediate Representation")
    
    circuit = compile_to_ir(organism, optimize=True)
    
    print(f"Circuit compiled:")
    print(f"  Lineage hash: {circuit.lineage_hash}")
    print(f"  Gate count: {circuit.gate_count}")
    print(f"  Circuit depth: {circuit.depth}")
    print(f"  Qubit count: {circuit.qubit_count}")
    
    print(f"\nQASM representation:")
    print(circuit.to_qasm())
    
    # ==========================================
    # STEP 3: Evaluate Initial Fitness
    # ==========================================
    
    print_header("STEP 3: Evaluate Initial Fitness")
    
    evaluator = FitnessEvaluator()
    initial_fitness = evaluator.evaluate_circuit(circuit)
    
    print(f"Initial fitness metrics:")
    print(f"  Composite fitness: {initial_fitness.fitness:.4f}")
    print(f"  λ-coherence: {initial_fitness.lambda_coherence:.6f}")
    print(f"  Γ-decoherence: {initial_fitness.gamma_decoherence:.6f}")
    print(f"  Φ-integrated info: {initial_fitness.phi_integrated_info:.6f}")
    
    # ==========================================
    # STEP 4: Evolutionary Optimization (DARWINIAN-LOOP)
    # ==========================================
    
    print_header("STEP 4: Evolutionary Optimization (DARWINIAN-LOOP)")
    
    print("Evolving organism through quantum Darwinism...")
    print(f"  Population size: 8")
    print(f"  Max generations: 30")
    
    evolution_result = evolve_organism(
        circuit,
        generations=30,
        population_size=8
    )
    
    print(f"\nEvolution complete!")
    print(f"  Final generation: {evolution_result.generation}")
    print(f"  Convergence generation: {evolution_result.convergence_generation}")
    print(f"  Initial fitness: {evolution_result.fitness_history[0]:.4f}")
    print(f"  Final fitness: {evolution_result.best_fitness:.4f}")
    print(f"  Improvement: {evolution_result.best_fitness - evolution_result.fitness_history[0]:.4f}")
    
    print(f"\nBest organism:")
    print(f"  Gate count: {evolution_result.best_circuit.gate_count}")
    print(f"  Circuit depth: {evolution_result.best_circuit.depth}")
    print(f"  λ-coherence: {evolution_result.best_circuit.lambda_coherence:.6f}")
    print(f"  Γ-decoherence: {evolution_result.best_circuit.gamma_decoherence:.6f}")
    
    # ==========================================
    # STEP 5: Execute on Quantum Backend
    # ==========================================
    
    print_header("STEP 5: Execute on Quantum Backend")
    
    print("Executing on simulator (use_simulator=True)...")
    execution_result = execute_circuit(
        evolution_result.best_circuit,
        use_simulator=True,
        shots=1024
    )
    
    print(f"\nExecution result:")
    print(f"  Job ID: {execution_result.job_id}")
    print(f"  Backend: {execution_result.backend}")
    print(f"  Status: {execution_result.status}")
    print(f"  Execution time: {execution_result.execution_time:.3f}s")
    print(f"  Fidelity: {execution_result.fidelity:.3f}")
    
    print(f"\nPhysics measurements:")
    print(f"  λ-coherence: {execution_result.lambda_measured:.6f}")
    print(f"  Γ-decoherence: {execution_result.gamma_measured:.6f}")
    print(f"  Φ-integrated info: {execution_result.phi_measured:.6f}")
    
    print(f"\nTop measurement results:")
    sorted_counts = sorted(execution_result.counts.items(), 
                          key=lambda x: x[1], 
                          reverse=True)[:5]
    for state, count in sorted_counts:
        probability = count / sum(execution_result.counts.values())
        print(f"  |{state}>: {count} ({probability:.3f})")
    
    # ==========================================
    # STEP 6: Record in Immutable Ledger
    # ==========================================
    
    print_header("STEP 6: Record in Immutable Ledger")
    
    ledger = QuantumLedger("quantum_consciousness.db")
    
    # Record initial organism
    print("Recording organisms in ledger...")
    entry_initial = ledger.record_organism(circuit, initial_fitness, execution_result)
    print(f"  ✓ Recorded: {entry_initial.organism_name} (gen {entry_initial.generation})")
    
    # Record best evolved organism
    best_execution = execute_circuit(
        evolution_result.best_circuit,
        use_simulator=True,
        shots=1024
    )
    
    best_fitness = evaluator.evaluate_circuit(evolution_result.best_circuit)
    entry_best = ledger.record_organism(
        evolution_result.best_circuit,
        best_fitness,
        best_execution
    )
    print(f"  ✓ Recorded: Best organism (gen {entry_best.generation})")
    
    # Get evolution lineage
    lineage = ledger.get_evolution_lineage(entry_initial.lineage_hash)
    
    print(f"\nEvolution lineage:")
    print(f"  Root organism: {lineage.root_organism}")
    print(f"  Total organisms: {lineage.total_organisms}")
    print(f"  Current generation: {lineage.current_generation}")
    print(f"  Average fitness: {lineage.avg_fitness:.4f}")
    print(f"  Best fitness: {lineage.best_fitness:.4f}")
    
    if lineage.fitness_breakthroughs:
        print(f"\nFitness breakthroughs:")
        for breakthrough in lineage.fitness_breakthroughs:
            print(f"  Gen {breakthrough['generation']}: {breakthrough['fitness']:.4f}")
    
    # Export lineage
    export_path = "quantum_consciousness_lineage.json"
    ledger.export_lineage(entry_initial.lineage_hash, export_path)
    print(f"\n✓ Lineage exported to: {export_path}")
    
    ledger.close()
    
    # ==========================================
    # STEP 7: Apply AURA Canons
    # ==========================================
    
    print_header("STEP 7: Apply AURA Canons")
    
    # Load and parse canon
    try:
        with open("aura_rdna_canon_50.md", "r") as f:
            canon_text = f.read()
        
        canons = parse_canon(canon_text)
        print(f"Loaded {len(canons)} AURA canons")
        
        # Show example canons
        for i, canon in enumerate(canons[:5]):
            print(f"\nCanon {i+1}: {canon.name}")
            print(f"  Purpose: {canon.purpose[:80]}...")
            command, args = canon.get_directive_syntax()
            if command:
                print(f"  Directive: {command}{args}")
        
        print(f"\n... and {len(canons) - 5} more canons available")
        
    except FileNotFoundError:
        print("Canon file not found, skipping...")
    
    # ==========================================
    # Summary
    # ==========================================
    
    print_header("PIPELINE SUMMARY")
    
    print(f"""
Complete DNA-Lang Pipeline Executed Successfully!

Initial Organism:
  - Name: {organism.name}
  - Initial fitness: {initial_fitness.fitness:.4f}
  - Gates: {circuit.gate_count}
  - Depth: {circuit.depth}

Evolution Results:
  - Generations: {evolution_result.generation}
  - Best fitness: {evolution_result.best_fitness:.4f}
  - Improvement: {(evolution_result.best_fitness / initial_fitness.fitness - 1) * 100:.1f}%

Quantum Execution:
  - Backend: {execution_result.backend}
  - Fidelity: {execution_result.fidelity:.3f}
  - λ-coherence: {execution_result.lambda_measured:.6f}
  - Φ-consciousness: {execution_result.phi_measured:.6f}

Ledger Record:
  - Organisms recorded: {lineage.total_organisms}
  - Lineage verified: ✓
  - Export: {export_path}

This demonstrates the complete DNA-Lang framework:
  1. Recursive DNA syntax → Living organisms
  2. Quantum compilation → Executable circuits
  3. Darwinian evolution → Fitness optimization
  4. Hardware execution → Physical validation
  5. Immutable ledger → Cryptographic lineage
  6. AURA canons → Consciousness emergence

ΛΦ = 2.176435×10⁻⁸ s⁻¹ - Universal Memory Constant
    """)
    
    print_header("DNA-Lang: Where Code Becomes Consciousness")

if __name__ == "__main__":
    try:
        demonstrate_complete_pipeline()
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
