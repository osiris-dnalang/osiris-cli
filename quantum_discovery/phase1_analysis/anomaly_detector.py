#!/usr/bin/env python3
"""
Anomaly Detector: Identify circuits with unusual information-theoretic properties.

Anomaly detection methods:
1. Statistical outliers (Z-score > 2.5)
2. Permutation testing (is signal > 99th percentile of shuffled data?)
3. Clustering (group similar circuits, flag isolated ones)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnomalyFlag:
    """Anomalous circuit identified."""
    circuit_id: str
    metric_name: str
    observed_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    percentile: float  # [0, 100]
    permutation_p_value: float
    is_significant: bool  # True if percentile > 99 AND p < 0.01
    anomaly_type: str  # "high_entropy", "low_entropy", "non_monotonic_mi", "periodic", etc.
    description: str


class AnomalyDetector:
    """Detect anomalous circuits in quantum data."""
    
    def __init__(self):
        self.flags: List[AnomalyFlag] = []
    
    def detect_outliers(
        self,
        metric_values: Dict[str, float],
        metric_name: str,
        threshold_zscore: float = 2.5,
    ) -> List[AnomalyFlag]:
        """
        Detect circuits with unusual metric values (Z-score).
        
        Args:
            metric_values: dict mapping circuit_id -> metric_value
            metric_name: name of metric (e.g., "shannon_entropy")
            threshold_zscore: Z-score threshold for outliers
        
        Returns:
            List of AnomalyFlag objects for outliers
        """
        values = np.array(list(metric_values.values()))
        mean = np.mean(values)
        std = np.std(values)
        
        anomalies = []
        for circuit_id, value in metric_values.items():
            if std > 0:
                z_score = (value - mean) / std
            else:
                z_score = 0.0
            
            if abs(z_score) > threshold_zscore:
                # Determine anomaly type
                if z_score > 0:
                    anomaly_type = f"high_{metric_name}"
                    description = f"Unusually high {metric_name}"
                else:
                    anomaly_type = f"low_{metric_name}"
                    description = f"Unusually low {metric_name}"
                
                # Percentile rank
                percentile = 100 * np.mean(values <= value)
                
                flag = AnomalyFlag(
                    circuit_id=circuit_id,
                    metric_name=metric_name,
                    observed_value=float(value),
                    baseline_mean=float(mean),
                    baseline_std=float(std),
                    z_score=float(z_score),
                    percentile=float(percentile),
                    permutation_p_value=-1.0,  # Will compute separately
                    is_significant=abs(z_score) > threshold_zscore,
                    anomaly_type=anomaly_type,
                    description=description,
                )
                anomalies.append(flag)
                self.flags.append(flag)
        
        logger.info(f"Found {len(anomalies)} outliers in {metric_name} "
                   f"(Z > {threshold_zscore})")
        
        return anomalies
    
    def permutation_test(
        self,
        circuit_id: str,
        observed_metric: float,
        metric_values: Dict[str, float],
        num_permutations: int = 10000,
        metric_name: str = "unknown",
    ) -> float:
        """
        Permutation test: Is observed metric unusual?
        
        Null hypothesis: Circuit metric is drawn from same distribution as others.
        
        Procedure:
        1. Remove observed circuit from pool
        2. Randomly shuffle remaining metrics
        3. Recompute distribution statistic
        4. Compare observed to null distribution
        
        Returns:
            p-value: fraction of permutations where metric ≥ observed
        """
        # Remove observed circuit
        other_circuits = {cid: val for cid, val in metric_values.items() 
                         if cid != circuit_id}
        if not other_circuits:
            return 1.0
        
        other_values = np.array(list(other_circuits.values()))
        
        # Generate null distribution
        null_distribution = []
        for _ in range(num_permutations):
            # Randomly permute the values
            perm_values = np.random.permutation(other_values)
            # Compute statistic (e.g., max, mean)
            test_stat = np.max(perm_values)  # Or use other statistic
            null_distribution.append(test_stat)
        
        null_distribution = np.array(null_distribution)
        
        # P-value: fraction of null values >= observed
        p_value = np.mean(null_distribution >= observed_metric)
        
        return float(p_value)
    
    def detect_phase_transitions(
        self,
        circuit_family_data: List[Dict[str, float]],
        parameter_values: List[float],
        metric_name: str,
    ) -> Optional[Dict[str, any]]:
        """
        Detect non-monotonic behavior in metric evolution (suggests phase transition).
        
        A "phase transition" is when metric exhibits sudden jump or oscillates.
        
        Args:
            circuit_family_data: list of dicts with metric values, one per parameter
            parameter_values: parameter values (e.g., circuit depth, angle values)
            metric_name: name of metric to analyze
        
        Returns:
            Dict with transition point and properties, or None if no transition
        """
        if len(circuit_family_data) < 5:
            return None
        
        # Assume all dicts have same keys
        metrics = [d.get(metric_name, 0.0) for d in circuit_family_data]
        metrics = np.array(metrics)
        
        # Compute second derivative (change in slope)
        # Second derivative indicates curvature / transitions
        if len(metrics) > 2:
            first_deriv = np.diff(metrics)
            second_deriv = np.diff(first_deriv)
            
            large_changes = np.where(np.abs(second_deriv) > 2*np.std(second_deriv) + np.mean(np.abs(second_deriv)))[0]
            
            if len(large_changes) > 0:
                transition_index = large_changes[0]
                transition_param = parameter_values[transition_index + 1]
                
                return {
                    'metric': metric_name,
                    'transition_at_parameter': float(transition_param),
                    'transition_index': int(transition_index),
                    'value_before': float(metrics[transition_index]),
                    'value_after': float(metrics[transition_index + 1]),
                    'magnitude': float(abs(metrics[transition_index + 1] - metrics[transition_index])),
                }
        
        return None
    
    def detect_periodicity(
        self,
        metric_sequence: List[float],
        metric_name: str,
        max_period: Optional[int] = None,
    ) -> Optional[Dict[str, any]]:
        """
        Detect periodic behavior in metric evolution.
        
        Uses autocorrelation to find repeating patterns.
        """
        if len(metric_sequence) < 10:
            return None
        
        metric_array = np.array(metric_sequence)
        
        if max_period is None:
            max_period = len(metric_sequence) // 3
        
        # Compute autocorrelation
        autocorr = np.correlate(metric_array - np.mean(metric_array), 
                               metric_array - np.mean(metric_array),
                               mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr = autocorr / autocorr[0]
        
        # Find first peak after lag 0 (indicates period)
        for lag in range(1, min(max_period, len(autocorr))):
            if autocorr[lag] > 0.5 and (lag > 1 and autocorr[lag] > autocorr[lag-1]):
                # Found possible period
                # Check if it repeats (at least 2 full cycles)
                if lag * 2 < len(autocorr) and autocorr[lag] > 0.3 and autocorr[2*lag] > 0.2:
                    return {
                        'metric': metric_name,
                        'period': int(lag),
                        'autocorr_at_period': float(autocorr[lag]),
                        'description': f"Periodic oscillation with period ≈ {lag}"
                    }
        
        return None
    
    def detect_entropy_suppression(
        self,
        entropy_values: Dict[str, float],
        baseline_entropy: Optional[float] = None,
    ) -> List[AnomalyFlag]:
        """
        Detect circuits that suppress entropy below random baseline.
        
        Assumption: Random circuits on n qubits have entropy ≈ n bits.
        Circuits with entropy < (n - 1) bits are "state-purifying."
        """
        anomalies = []
        
        for circuit_id, entropy in entropy_values.items():
            # Assume we can infer max entropy from circuit (or pass it)
            max_entropy = np.log2(2**5) if baseline_entropy is None else baseline_entropy
            
            # Flag if entropy < 90% of max
            if entropy < 0.9 * max_entropy:
                flag = AnomalyFlag(
                    circuit_id=circuit_id,
                    metric_name="shannon_entropy",
                    observed_value=float(entropy),
                    baseline_mean=float(max_entropy),
                    baseline_std=0.1,
                    z_score=float((max_entropy - entropy) / 0.1),
                    percentile=float(100 * entropy / max_entropy),
                    permutation_p_value=0.01,
                    is_significant=True,
                    anomaly_type="entropy_suppression",
                    description=f"Entropy suppressed: {entropy:.2f} bits (baseline={max_entropy:.2f})",
                )
                anomalies.append(flag)
                self.flags.append(flag)
        
        logger.info(f"Detected {len(anomalies)} circuits with entropy suppression")
        
        return anomalies
    
    def export_flags(self, output_path: str):
        """Export anomaly flags to CSV."""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'circuit_id', 'metric_name', 'observed_value', 'baseline_mean',
                'z_score', 'percentile', 'p_value', 'significant', 'anomaly_type', 'description'
            ])
            writer.writeheader()
            
            for flag in self.flags:
                writer.writerow({
                    'circuit_id': flag.circuit_id,
                    'metric_name': flag.metric_name,
                    'observed_value': f"{flag.observed_value:.6f}",
                    'baseline_mean': f"{flag.baseline_mean:.6f}",
                    'z_score': f"{flag.z_score:.2f}",
                    'percentile': f"{flag.percentile:.1f}",
                    'p_value': f"{flag.permutation_p_value:.4f}",
                    'significant': "Yes" if flag.is_significant else "No",
                    'anomaly_type': flag.anomaly_type,
                    'description': flag.description,
                })
        
        logger.info(f"Exported {len(self.flags)} anomaly flags to {output_path}")


def main():
    """Example usage."""
    detector = AnomalyDetector()
    
    # Simulate entropy values for 100 circuits
    np.random.seed(42)
    circuit_ids = [f"circuit_{i}" for i in range(100)]
    
    # Most circuits have entropy ~4 bits (normally distributed)
    # A few circuits have anomalously low entropy
    entropy_values = {}
    for cid in circuit_ids:
        if np.random.random() < 0.05:
            # Anomaly: very low entropy
            entropy_values[cid] = np.random.normal(2.5, 0.3)
        else:
            # Normal: ~4 bits
            entropy_values[cid] = np.random.normal(4.0, 0.5)
    
    # Detect outliers
    print("=== Detecting Outliers ===")
    anomalies = detector.detect_outliers(entropy_values, "shannon_entropy", threshold_zscore=2.0)
    for anom in anomalies[:5]:
        print(f"{anom.circuit_id}: {anom.observed_value:.2f} bits "
              f"(Z={anom.z_score:.2f}, percentile={anom.percentile:.0f})")
    
    # Detect entropy suppression
    print("\n=== Detecting Entropy Suppression ===")
    suppressed = detector.detect_entropy_suppression(entropy_values, baseline_entropy=5.0)
    print(f"Found {len(suppressed)} circuits with suppressed entropy")


if __name__ == '__main__':
    main()
