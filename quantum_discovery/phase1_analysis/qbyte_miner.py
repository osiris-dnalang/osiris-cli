#!/usr/bin/env python3
"""
QBYTE Mining Framework: Extract quantum information patterns from measurement data.

QBYTE = Quantum Byte (information quantum)
Mining = extracting structure from raw data

This module bridges:
- Raw measurement outcomes (bitstrings, counts)
- Encoded information patterns (QBYTEs)
- Anomaly detection and invariant discovery
"""

import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import json
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class QBYTE:
    """Quantum Byte: encoded information pattern."""
    id: str
    bitstring_pattern: str  # Template pattern (e.g., "01*1" where * is wildcard)
    frequency: int  # How many bitstrings match this pattern
    probability: float
    subsystem: List[int]  # Which qubits this pattern spans
    entropy: float  # Information content of this pattern
    discovery_type: str  # "core", "anomaly", "invariant", "periodic"


@dataclass
class QBYTEMinedResult:
    """Results from QBYTE mining on a circuit."""
    circuit_id: str
    total_qbytes: int
    core_patterns: List[QBYTE]
    anomalous_patterns: List[QBYTE]
    invariant_patterns: List[QBYTE]
    periodic_patterns: List[QBYTE]
    information_density: float  # Fraction of data captured by top patterns


class QBYTEMiner:
    """Mine quantum information from measurement outcomes."""
    
    def __init__(self, min_frequency: int = 10):
        """
        Args:
            min_frequency: Minimum occurrences to consider a pattern significant
        """
        self.min_frequency = min_frequency
        self.mined_qbytes: Dict[str, List[QBYTE]] = {}
    
    def identify_core_patterns(
        self,
        counts: Dict[str, int],
        num_qubits: int,
        top_k: int = 5,
    ) -> List[QBYTE]:
        """
        Identify most frequent bitstrings (core patterns).
        
        Core = the "center" of the probability distribution
        E.g., if 70% of shots are in |000⟩, that's the core.
        """
        total_shots = sum(counts.values())
        
        # Sort by frequency
        sorted_bitstrings = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        core_patterns = []
        cumulative_prob = 0.0
        
        for bitstring, count in sorted_bitstrings[:top_k]:
            prob = count / total_shots
            cumulative_prob += prob
            
            # Compute entropy of this single state
            entropy = -prob * np.log2(prob) if prob > 0 else 0.0
            
            qbyte = QBYTE(
                id=f"core_{bitstring}",
                bitstring_pattern=bitstring,
                frequency=count,
                probability=float(prob),
                subsystem=list(range(num_qubits)),
                entropy=float(entropy),
                discovery_type="core",
            )
            core_patterns.append(qbyte)
        
        logger.info(f"Found {len(core_patterns)} core patterns (cumulative prob: {cumulative_prob:.2%})")
        return core_patterns
    
    def identify_anomalous_patterns(
        self,
        counts: Dict[str, int],
        num_qubits: int,
        baseline_prob: float = 0.01,  # Patterns with prob > baseline but rare
    ) -> List[QBYTE]:
        """
        Identify patterns that exist but are anomalously frequent or rare.
        
        Anomalous = appears more often than random baseline (1/2^n)
        but less frequently than core patterns.
        """
        total_shots = sum(counts.values())
        random_baseline = 1.0 / (2**num_qubits)
        
        anomalous = []
        
        for bitstring, count in counts.items():
            prob = count / total_shots
            
            # Anomaly: prob significantly higher than random, but not in top-k core
            if prob > baseline_prob * random_baseline and count >= self.min_frequency:
                entropy = -prob * np.log2(prob) if prob > 0 else 0.0
                
                qbyte = QBYTE(
                    id=f"anom_{bitstring}",
                    bitstring_pattern=bitstring,
                    frequency=count,
                    probability=float(prob),
                    subsystem=list(range(num_qubits)),
                    entropy=float(entropy),
                    discovery_type="anomaly",
                )
                anomalous.append(qbyte)
        
        # Sort by anomaly strength (how much above random)
        anomalous.sort(
            key=lambda q: q.probability / (random_baseline),
            reverse=True
        )
        
        logger.info(f"Found {len(anomalous)} anomalous patterns")
        return anomalous
    
    def identify_invariant_patterns(
        self,
        counts_family: Dict[str, Dict[str, int]],  # circuit_id -> counts
        num_qubits: int,
    ) -> List[Tuple[str, float]]:
        """
        Identify patterns that appear CONSISTENTLY across a circuit family.
        
        Invariant = appears in nearly all circuits in the family,
        suggests structural property.
        
        Returns: (pattern, frequency_across_family)
        """
        # Collect which bitstrings appear in each circuit
        family_size = len(counts_family)
        pattern_occurrence = Counter()
        
        for counts in counts_family.values():
            for bitstring in counts.keys():
                pattern_occurrence[bitstring] += 1
        
        # Find invariants: appear in >80% of circuits
        invariants = []
        for pattern, occurrences in pattern_occurrence.items():
            freq = occurrences / family_size
            if freq > 0.8:
                invariants.append((pattern, freq))
        
        invariants.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Found {len(invariants)} invariant patterns across family")
        return invariants
    
    def identify_periodic_patterns(
        self,
        counts_sequence: List[Dict[str, int]],  # List ordered by parameter
        num_qubits: int,
        parameter_name: str = "depth",
    ) -> Dict[str, any]:
        """
        Identify patterns that REPEAT periodically as parameter varies.
        
        Periodic = bitstring or pattern recurs at regular intervals
        suggests resonance or symmetry.
        
        Returns: dict mapping pattern -> period
        """
        periodicity = {}
        
        # For each qubit, track its bit value across sequence
        for qubit_index in range(num_qubits):
            qubit_bits = []
            
            for counts in counts_sequence:
                # Get most likely value for this qubit
                marginal = {'0': 0, '1': 0}
                total = sum(counts.values())
                
                for bitstring, count in counts.items():
                    bit = bitstring[qubit_index]
                    marginal[bit] += count
                
                # Most likely value
                dominant_bit = max(marginal, key=marginal.get)
                qubit_bits.append(int(dominant_bit))
            
            # Check for periodicity in qubit_bits sequence
            period = self._find_period(qubit_bits)
            if period is not None:
                periodicity[f"qubit_{qubit_index}"] = {
                    'period': period,
                    'sequence': qubit_bits,
                    'parameter': parameter_name,
                }
        
        logger.info(f"Found periodicity in {len(periodicity)} qubits")
        return periodicity
    
    def _find_period(self, sequence: List[int], min_repeats: int = 2) -> Optional[int]:
        """Find repeating period in a sequence of bits."""
        for period in range(1, len(sequence) // (min_repeats + 1)):
            is_periodic = True
            for i in range(len(sequence) - period):
                if sequence[i] != sequence[i + period]:
                    is_periodic = False
                    break
            
            if is_periodic:
                return period
        
        return None
    
    def encode_qbytes_for_circuit(
        self,
        counts: Dict[str, int],
        num_qubits: int,
    ) -> QBYTEMinedResult:
        """
        Complete QBYTE mining pipeline for a single circuit.
        
        Returns:
            QBYTEMinedResult with all discovered patterns
        """
        core = self.identify_core_patterns(counts, num_qubits)
        anomalous = self.identify_anomalous_patterns(counts, num_qubits)
        
        # Information density: fraction of shots in identified patterns
        identified_shots = sum(qb.frequency for qb in core + anomalous)
        total_shots = sum(counts.values())
        info_density = identified_shots / total_shots if total_shots > 0 else 0.0
        
        return QBYTEMinedResult(
            circuit_id="",
            total_qbytes=len(core) + len(anomalous),
            core_patterns=core,
            anomalous_patterns=anomalous,
            invariant_patterns=[],
            periodic_patterns=[],
            information_density=float(info_density),
        )
    
    def detect_anomalies_via_qbytes(
        self,
        circuit_data: Dict[str, Dict[str, int]],
        qubit_counts: Dict[str, int],
    ) -> List[Tuple[str, List[QBYTE]]]:
        """
        Detect anomalies by finding circuits with unusual QBYTE structure.
        
        Anomalous circuit = has unique patterns not seen in others.
        """
        all_patterns: Dict[str, Set[str]] = {}
        
        for circuit_id, counts in circuit_data.items():
            num_qubits = qubit_counts.get(circuit_id, 0)
            if num_qubits == 0:
                continue
            
            result = self.encode_qbytes_for_circuit(counts, num_qubits)
            patterns = {qb.bitstring_pattern for qb in result.anomalous_patterns}
            all_patterns[circuit_id] = patterns
        
        # Find circuits with unique patterns
        anomalous_circuits = []
        for circuit_id, patterns in all_patterns.items():
            unique_to_this = patterns.copy()
            
            for other_id, other_patterns in all_patterns.items():
                if other_id != circuit_id:
                    unique_to_this -= other_patterns
            
            if len(unique_to_this) > 0:
                # This circuit has unique patterns
                num_qubits = qubit_counts[circuit_id]
                result = self.encode_qbytes_for_circuit(
                    circuit_data[circuit_id], num_qubits
                )
                anomalous_circuits.append((circuit_id, result.anomalous_patterns))
        
        logger.info(f"Found {len(anomalous_circuits)} anomalous circuits via QBYTE mining")
        return anomalous_circuits
    
    def export_qbytes(self, output_path: str = "qbytes_mined.json"):
        """Export mined QBYTEs to JSON for analysis."""
        data = {
            circuit_id: [
                {
                    'id': qb.id,
                    'pattern': qb.bitstring_pattern,
                    'frequency': qb.frequency,
                    'probability': qb.probability,
                    'entropy': qb.entropy,
                    'type': qb.discovery_type,
                }
                for qb in qbytes
            ]
            for circuit_id, qbytes in self.mined_qbytes.items()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported QBYTEs to {output_path}")


def main():
    """Example: QBYTE mining on a simple circuit."""
    miner = QBYTEMiner()
    
    # Example 1: Circuit with clear structure (GHZ-like)
    counts_ghz = {
        '000': 450,
        '111': 450,
        '001': 30,
        '010': 20,
        '100': 50,
    }
    
    print("=== QBYTE Mining on GHZ-like Circuit ===\n")
    result = miner.encode_qbytes_for_circuit(counts_ghz, num_qubits=3)
    
    print(f"Core patterns ({len(result.core_patterns)}):")
    for qb in result.core_patterns:
        print(f"  {qb.bitstring_pattern}: {qb.probability:.1%} ({qb.frequency} shots)")
    
    print(f"\nAnomalous patterns ({len(result.anomalous_patterns)}):")
    for qb in result.anomalous_patterns:
        print(f"  {qb.bitstring_pattern}: {qb.probability:.1%} ({qb.frequency} shots)")
    
    print(f"\nInformation density: {result.information_density:.1%}")
    
    # Example 2: Invariant patterns across circuit family
    print("\n=== Invariant Pattern Detection ===\n")
    
    family = {
        'circuit_1': counts_ghz,
        'circuit_2': {'000': 480, '111': 480, '011': 20, '101': 20},
        'circuit_3': {'000': 470, '111': 470, '010': 30, '100': 30},
    }
    
    invariants = miner.identify_invariant_patterns(family, num_qubits=3)
    print(f"Invariant patterns (appear in ≥80% of circuits):")
    for pattern, freq in invariants:
        print(f"  {pattern}: {freq:.1%}")


if __name__ == '__main__':
    main()
