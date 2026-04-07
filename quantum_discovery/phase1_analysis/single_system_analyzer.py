#!/usr/bin/env python3
"""
Single System Analyzer: Compute information-theoretic metrics for quantum circuits.

Metrics computed:
1. Shannon Entropy - measures state mixedness (0 = pure, log2(d) = maximally mixed)
2. Purity - Tr(ρ²) estimated from measurement statistics
3. Accessible Information - mutual info between measurement settings and outcomes
4. Statistical significance tests
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class EntropyMetrics:
    """Entropy and purity metrics for a single circuit."""
    circuit_id: str
    shannon_entropy: float
    entropy_per_qubit: float
    max_entropy: float  # log2(2^num_qubits)
    entropy_normalized: float  # shannon_entropy / max_entropy
    purity: float  # Tr(ρ²)
    mixedness: float  # 1 - purity
    predictability: float  # max probability in distribution
    num_qubits: int
    num_bitstrings_observed: int
    shots: int


@dataclass
class StatisticalSignificance:
    """Statistical test results comparing observed vs. baseline entropy."""
    circuit_id: str
    observed_entropy: float
    baseline_entropy: float
    z_score: float
    p_value: float
    is_significant: bool  # True if p < 0.01
    effect_size: float


class SingleSystemAnalyzer:
    """Analyze entropy and purity of single quantum systems."""
    
    def __init__(self):
        self.results: Dict[str, EntropyMetrics] = {}
    
    def compute_shannon_entropy(
        self, 
        counts: Dict[str, int],
        num_qubits: int
    ) -> EntropyMetrics:
        """
        Compute Shannon entropy from measurement counts.
        
        H = -Σ_i p_i log₂(p_i)
        
        - Pure state: H = 0
        - Maximally mixed state: H = log₂(2^num_qubits) = num_qubits
        
        Args:
            counts: dict mapping bitstring -> count
            num_qubits: number of qubits
        
        Returns:
            EntropyMetrics object
        """
        total_shots = sum(counts.values())
        probabilities = np.array([c / total_shots for c in counts.values()])
        
        # Compute Shannon entropy (natural log, then divide by ln(2))
        nonzero_probs = probabilities[probabilities > 0]
        shannon_entropy = -np.sum(nonzero_probs * np.log2(nonzero_probs))
        
        max_entropy = num_qubits
        entropy_normalized = shannon_entropy / max_entropy if max_entropy > 0 else 0.0
        
        # Predict: max probability in distribution
        predictability = float(np.max(probabilities))
        
        entropy_per_qubit = shannon_entropy / num_qubits if num_qubits > 0 else 0.0
        
        metrics = EntropyMetrics(
            circuit_id="",  # Will be set by caller
            shannon_entropy=float(shannon_entropy),
            entropy_per_qubit=float(entropy_per_qubit),
            max_entropy=float(max_entropy),
            entropy_normalized=float(entropy_normalized),
            purity=float(np.sum(probabilities**2)),
            mixedness=float(1.0 - np.sum(probabilities**2)),
            predictability=float(predictability),
            num_qubits=num_qubits,
            num_bitstrings_observed=len(counts),
            shots=total_shots,
        )
        
        return metrics
    
    def estimate_purity(self, counts: Dict[str, int]) -> float:
        """
        Estimate purity Tr(ρ²) from measurement statistics.
        
        For a state ρ, Tr(ρ²) = Σ_ij ρ_ij ρ_ji
        
        From measurements: Tr(ρ²) ≈ Σ_i p_i²
        
        - Pure state: Tr(ρ²) = 1
        - Maximally mixed d-dimensional space: Tr(ρ²) = 1/d
        """
        total_shots = sum(counts.values())
        probabilities = np.array([c / total_shots for c in counts.values()])
        return float(np.sum(probabilities**2))
    
    def test_purity_against_baseline(
        self,
        observed_counts: Dict[str, int],
        num_qubits: int,
        baseline_purity: Optional[float] = None,
    ) -> StatisticalSignificance:
        """
        Statistical test: Is observed purity significantly different from random?
        
        Null hypothesis: State is maximally mixed (purity = 1/2^num_qubits)
        Alternative: State has higher purity
        
        Uses chi-squared test on observed vs. expected counts.
        """
        observed_purity = self.estimate_purity(observed_counts)
        
        if baseline_purity is None:
            # For maximally mixed state: purity = 1/2^num_qubits
            baseline_purity = 1.0 / (2**num_qubits)
        
        # Chi-squared test
        total_shots = sum(observed_counts.values())
        expected_count_per_state = total_shots / (2**num_qubits)
        
        chi2 = 0.0
        for count in observed_counts.values():
            chi2 += (count - expected_count_per_state)**2 / expected_count_per_state
        
        # Degrees of freedom = number of bitstrings - 1
        dof = len(observed_counts) - 1
        p_value = 1.0 - stats.chi2.cdf(chi2, dof)
        
        # Z-score (effect size)
        observed_entropy = self.compute_shannon_entropy(observed_counts, num_qubits).shannon_entropy
        baseline_entropy = num_qubits  # Maximally mixed
        
        # Estimate standard error
        se = np.sqrt(observed_entropy * (1 - observed_entropy) / total_shots)
        z_score = (baseline_entropy - observed_entropy) / se if se > 0 else 0.0
        
        return StatisticalSignificance(
            circuit_id="",
            observed_entropy=observed_entropy,
            baseline_entropy=baseline_entropy,
            z_score=float(z_score),
            p_value=float(p_value),
            is_significant=float(p_value) < 0.01,
            effect_size=float(observed_purity - baseline_purity),
        )
    
    def entropy_trend_analysis(
        self,
        circuit_data_sequence: List[Dict[str, int]],
        num_qubits: int,
    ) -> Dict[str, any]:
        """
        Analyze entropy evolution across a sequence of circuits (e.g., increasing depth).
        
        Returns:
        {
            'entropies': [float],
            'trend': 'increasing' | 'decreasing' | 'oscillating',
            'correlation_with_index': float,
            'variance': float,
        }
        """
        entropies = []
        for counts in circuit_data_sequence:
            metrics = self.compute_shannon_entropy(counts, num_qubits)
            entropies.append(metrics.shannon_entropy)
        
        entropies = np.array(entropies)
        indices = np.arange(len(entropies))
        
        # Linear regression for trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(indices, entropies)
        
        trend = 'increasing' if slope > 0.01 else ('decreasing' if slope < -0.01 else 'flat')
        
        return {
            'entropies': [float(e) for e in entropies],
            'trend': trend,
            'slope': float(slope),
            'correlation_with_index': float(r_value),
            'variance': float(np.var(entropies)),
            'mean': float(np.mean(entropies)),
            'std': float(np.std(entropies)),
        }
    
    def accessible_information(
        self,
        counts_dict: Dict[str, Dict[str, int]],
        num_qubits: int,
    ) -> float:
        """
        Compute accessible information between measurement settings and outcomes.
        
        If we have measurement data from different bases or parameters:
        I_accessible = H(outcomes) - <H(outcomes | setting)>
        
        High accessible info = measurement outcomes carry useful information.
        """
        # Global entropy
        all_counts = {}
        for counts in counts_dict.values():
            for bitstring, count in counts.items():
                all_counts[bitstring] = all_counts.get(bitstring, 0) + count
        
        global_metrics = self.compute_shannon_entropy(all_counts, num_qubits)
        global_entropy = global_metrics.shannon_entropy
        
        # Average conditional entropy
        total_outcomes = sum(all_counts.values())
        conditional_entropy = 0.0
        
        for counts in counts_dict.values():
            setting_weight = sum(counts.values()) / total_outcomes
            metrics = self.compute_shannon_entropy(counts, num_qubits)
            conditional_entropy += setting_weight * metrics.shannon_entropy
        
        accessible_info = global_entropy - conditional_entropy
        return float(max(0.0, accessible_info))  # Clip to [0, ∞)
    
    def batch_analyze(
        self,
        circuit_data: Dict[str, Dict[str, int]],
        qubit_counts: Dict[str, int],
    ) -> List[EntropyMetrics]:
        """
        Analyze entropy for multiple circuits at once.
        
        Args:
            circuit_data: dict mapping circuit_id -> counts
            qubit_counts: dict mapping circuit_id -> num_qubits
        
        Returns:
            List of EntropyMetrics objects
        """
        results = []
        for circuit_id, counts in circuit_data.items():
            num_qubits = qubit_counts.get(circuit_id, 0)
            if num_qubits > 0:
                metrics = self.compute_shannon_entropy(counts, num_qubits)
                metrics.circuit_id = circuit_id
                results.append(metrics)
                self.results[circuit_id] = metrics
        
        return results
    
    def export_results(self, output_path: str):
        """Export analysis results to JSON."""
        data = {
            circuit_id: {
                'shannon_entropy': m.shannon_entropy,
                'entropy_per_qubit': m.entropy_per_qubit,
                'entropy_normalized': m.entropy_normalized,
                'purity': m.purity,
                'mixedness': m.mixedness,
                'predictability': m.predictability,
                'num_qubits': m.num_qubits,
                'num_bitstrings_observed': m.num_bitstrings_observed,
                'shots': m.shots,
            }
            for circuit_id, m in self.results.items()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(self.results)} entropy analyses to {output_path}")


def main():
    """Example usage."""
    analyzer = SingleSystemAnalyzer()
    
    # Example: analyze GHZ state (should have low entropy)
    ghz_counts = {
        '000': 500,
        '111': 500,
    }
    
    ghz_metrics = analyzer.compute_shannon_entropy(ghz_counts, num_qubits=3)
    print("GHZ state entropy analysis:")
    print(f"  Shannon entropy: {ghz_metrics.shannon_entropy:.4f} bits (max = {ghz_metrics.max_entropy})")
    print(f"  Purity: {ghz_metrics.purity:.4f}")
    print(f"  Normalized entropy: {ghz_metrics.entropy_normalized:.4f} (0 = pure, 1 = maximally mixed)")
    
    # Example: analyze maximally mixed state
    mixed_counts = {f"{i:03b}": 125 for i in range(8)}
    
    mixed_metrics = analyzer.compute_shannon_entropy(mixed_counts, num_qubits=3)
    print("\nMaximally mixed state entropy analysis:")
    print(f"  Shannon entropy: {mixed_metrics.shannon_entropy:.4f} bits")
    print(f"  Purity: {mixed_metrics.purity:.4f}")
    print(f"  Normalized entropy: {mixed_metrics.entropy_normalized:.4f}")


if __name__ == '__main__':
    main()
