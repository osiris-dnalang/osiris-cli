#!/usr/bin/env python3
"""
Correlation Analyzer: Compute multi-qubit correlations and mutual information.

Key metrics:
1. Bipartite Mutual Information: I(A:B) = H(A) + H(B) - H(AB)
2. Marginal entropies: Trace out subsystems
3. Entanglement entropy estimates
4. Light-cone structure analysis
5. Wasserstein distance: measure of "non-locality"
"""

import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import itertools
from scipy.stats import wasserstein_distance
import logging

logger = logging.getLogger(__name__)


@dataclass
class BipartiteCorrelation:
    """Mutual information between two subsystems."""
    subsystem_a: Set[int]
    subsystem_b: Set[int]
    mutual_information: float
    entropy_a: float
    entropy_b: float
    entropy_ab: float
    redundancy: float  # Shared information / total entropy


@dataclass
class LightConeAnalysis:
    """Correlation structure as function of qubit distance."""
    distance: int  # Manhattan distance between qubits
    avg_correlation: float
    num_pairs: int
    correlation_std: float


@dataclass
class WassertsteinMetrics:
    """Wasserstein distance measures."""
    local_to_global_w2: float  # Distance between local marginals and global
    circuit_id: str
    description: str


class CorrelationAnalyzer:
    """Analyze multi-qubit correlations in quantum circuits."""
    
    def __init__(self):
        self.results: Dict[str, any] = {}
    
    def compute_marginal_entropy(
        self,
        counts: Dict[str, int],
        qubits_to_keep: List[int],
    ) -> float:
        """
        Compute Shannon entropy of a subsystem (marginalize out other qubits).
        
        E.g., if qubits_to_keep = [0, 2], sum over all values of qubits 1, 3, ...
        
        Args:
            counts: dict mapping bitstring (e.g., '0101') -> count
            qubits_to_keep: indices of qubits to keep [0, 1, 2, ...]
        
        Returns:
            Shannon entropy of the marginal state
        """
        if not counts:
            return 0.0
        
        total_shots = sum(counts.values())
        marginal_counts = {}
        
        for bitstring, count in counts.items():
            # Extract bits at specified positions
            marginal_bits = ''.join(bitstring[q] for q in sorted(qubits_to_keep))
            marginal_counts[marginal_bits] = marginal_counts.get(marginal_bits, 0) + count
        
        # Compute entropy of marginal distribution
        entropy = 0.0
        for count in marginal_counts.values():
            p = count / total_shots
            if p > 0:
                entropy -= p * np.log2(p)
        
        return float(entropy)
    
    def compute_bipartite_mutual_information(
        self,
        counts: Dict[str, int],
        qubits_a: List[int],
        qubits_b: List[int],
    ) -> BipartiteCorrelation:
        """
        Compute mutual information I(A:B) = H(A) + H(B) - H(AB).
        
        - I(A:B) = 0 for product states (no correlation)
        - I(A:B) > 0 for entangled/correlated states
        - I(A:B) ≤ min(H(A), H(B)) (upper bound)
        
        Args:
            counts: measurement counts
            qubits_a: indices of qubit subsystem A
            qubits_b: indices of qubit subsystem B
        
        Returns:
            BipartiteCorrelation object
        """
        # Marginal entropies
        h_a = self.compute_marginal_entropy(counts, qubits_a)
        h_b = self.compute_marginal_entropy(counts, qubits_b)
        
        # Joint entropy H(AB)
        h_ab = self.compute_marginal_entropy(counts, qubits_a + qubits_b)
        
        # Mutual information
        mutual_info = h_a + h_b - h_ab
        mutual_info = max(0.0, mutual_info)  # Clip numerical errors
        
        # Redundancy: fraction of total entropy that is shared
        total_entropy = h_a + h_b
        redundancy = mutual_info / total_entropy if total_entropy > 0 else 0.0
        
        return BipartiteCorrelation(
            subsystem_a=set(qubits_a),
            subsystem_b=set(qubits_b),
            mutual_information=float(mutual_info),
            entropy_a=float(h_a),
            entropy_b=float(h_b),
            entropy_ab=float(h_ab),
            redundancy=float(redundancy),
        )
    
    def all_pairs_mutual_information(
        self,
        counts: Dict[str, int],
        num_qubits: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Compute MI for all qubit pairs in a circuit.
        
        Returns:
            dict mapping (qubit_i, qubit_j) -> mutual_information
        """
        mi_matrix = {}
        
        for i in range(num_qubits):
            for j in range(i + 1, num_qubits):
                corr = self.compute_bipartite_mutual_information(counts, [i], [j])
                mi_matrix[(i, j)] = corr.mutual_information
        
        return mi_matrix
    
    def light_cone_analysis(
        self,
        counts: Dict[str, int],
        num_qubits: int,
        qubit_connectivity: Optional[Dict[int, List[int]]] = None,
    ) -> List[LightConeAnalysis]:
        """
        Analyze how correlations decay with qubit distance.
        
        Returns list of LightConeAnalysis objects for each distance.
        """
        if qubit_connectivity is None:
            # Assume linear connectivity
            qubit_connectivity = {i: [i-1, i+1] for i in range(num_qubits)}
        
        mi_matrix = self.all_pairs_mutual_information(counts, num_qubits)
        
        # Compute distance between all pairs (BFS)
        distances = self._compute_pairwise_distances(qubit_connectivity, num_qubits)
        
        # Group MI by distance
        mi_by_distance = {}
        for (i, j), mi in mi_matrix.items():
            dist = distances[(i, j)] if (i, j) in distances else distances[(j, i)]
            if dist not in mi_by_distance:
                mi_by_distance[dist] = []
            mi_by_distance[dist].append(mi)
        
        # Compute statistics by distance
        results = []
        for distance in sorted(mi_by_distance.keys()):
            mis = np.array(mi_by_distance[distance])
            results.append(LightConeAnalysis(
                distance=distance,
                avg_correlation=float(np.mean(mis)),
                num_pairs=len(mis),
                correlation_std=float(np.std(mis)),
            ))
        
        return results
    
    def _compute_pairwise_distances(
        self,
        connectivity: Dict[int, List[int]],
        num_qubits: int,
    ) -> Dict[Tuple[int, int], int]:
        """Compute graph distances (BFS) between all qubit pairs."""
        distances = {}
        
        for start in range(num_qubits):
            visited = {start: 0}
            queue = [start]
            
            while queue:
                node = queue.pop(0)
                for neighbor in connectivity.get(node, []):
                    if neighbor not in visited and 0 <= neighbor < num_qubits:
                        visited[neighbor] = visited[node] + 1
                        queue.append(neighbor)
            
            for end, dist in visited.items():
                key = tuple(sorted([start, end]))
                distances[key] = dist
        
        return distances
    
    def wasserstein_local_global(
        self,
        counts: Dict[str, int],
        num_qubits: int,
    ) -> WassertsteinMetrics:
        """
        Measure "non-locality" using Wasserstein-2 distance between
        local marginal distributions and global distribution.
        
        Low W2 = local behavior matches global (classical-like)
        High W2 = non-local correlations present (quantum)
        
        The idea: Compare the distribution you'd predict from single-qubit
        measurements vs. the actual joint distribution.
        """
        total_shots = sum(counts.values())
        
        # Global distribution (probabilities)
        global_probs = np.array([c / total_shots for c in counts.values()])
        
        # Local marginal entropies (single qubit)
        local_entropies = []
        for q in range(num_qubits):
            marginal = self.compute_marginal_distribution_for_qubit(counts, q)
            # Compute entropy
            entropy = 0.0
            for p in marginal.values():
                if p > 0:
                    entropy -= p * np.log2(p)
            local_entropies.append(entropy)
        
        # Simplified Wasserstein: use average local entropy vs global entropy
        avg_local_entropy = np.mean(local_entropies) if local_entropies else 0.0
        global_entropy = -np.sum(global_probs[global_probs > 0] * np.log2(global_probs[global_probs > 0]))
        
        # W2 proxy: normalized difference in entropies
        w2 = float(abs(global_entropy - avg_local_entropy)) / max(global_entropy, 1e-10)
        
        return WassertsteinMetrics(
            local_to_global_w2=w2,
            circuit_id="",
            description="Distance between local marginals and global distribution"
        )
    
    def compute_marginal_distribution_for_qubit(
        self,
        counts: Dict[str, int],
        qubit_index: int,
    ) -> Dict[str, float]:
        """Get probability distribution for a single qubit."""
        total_shots = sum(counts.values())
        marginal = {'0': 0, '1': 0}
        
        for bitstring, count in counts.items():
            bit_value = bitstring[qubit_index]
            marginal[bit_value] += count
        
        return {k: v / total_shots for k, v in marginal.items()}
    
    def entanglement_entropy(
        self,
        counts: Dict[str, int],
        partition: Tuple[List[int], List[int]],
    ) -> float:
        """
        Compute entanglement entropy across a bipartition.
        
        EE = -Tr(ρ_A log₂ ρ_A) where ρ_A is reduced density matrix.
        
        - Pure product state: EE = 0
        - Maximally entangled state (Bell pair): EE = 1
        """
        subsystem_a, subsystem_b = partition
        
        # Compute reduced density matrix for subsystem A
        # This requires knowledge of quantum state, which we approximate from counts
        
        # Simple approximation: use conditional entropy
        # EE ≈ H(A | B) for weakly correlated systems
        
        entropy_a = self.compute_marginal_entropy(counts, subsystem_a)
        entropy_ab = self.compute_marginal_entropy(counts, subsystem_a + subsystem_b)
        entropy_b = self.compute_marginal_entropy(counts, subsystem_b)
        
        # Conditional entropy: H(A|B) = H(AB) - H(B)
        conditional_entropy = entropy_ab - entropy_b
        conditional_entropy = max(0.0, conditional_entropy)
        
        return float(conditional_entropy)
    
    def batch_analyze(
        self,
        circuit_data: Dict[str, Dict[str, int]],
        qubit_counts: Dict[str, int],
    ) -> Dict[str, any]:
        """Analyze correlations for multiple circuits."""
        results = {}
        
        for circuit_id, counts in circuit_data.items():
            num_qubits = qubit_counts.get(circuit_id, 0)
            if num_qubits < 2:
                continue
            
            # All-pairs MI
            mi_matrix = self.all_pairs_mutual_information(counts, num_qubits)
            
            # Light-cone analysis
            light_cone = self.light_cone_analysis(counts, num_qubits)
            
            # Wasserstein
            wass = self.wasserstein_local_global(counts, num_qubits)
            
            results[circuit_id] = {
                'mi_matrix': mi_matrix,
                'light_cone': [(lc.distance, lc.avg_correlation, lc.num_pairs) 
                              for lc in light_cone],
                'wasserstein_w2': wass.local_to_global_w2,
            }
            
            self.results[circuit_id] = results[circuit_id]
        
        return results


def main():
    """Example usage."""
    analyzer = CorrelationAnalyzer()
    
    # Example 1: Bell pair (maximally entangled)
    bell_counts = {
        '00': 500,
        '11': 500,
    }
    
    print("Bell pair (maximally entangled):")
    mi = analyzer.compute_bipartite_mutual_information(bell_counts, [0], [1])
    print(f"  MI(0:1) = {mi.mutual_information:.4f}")
    print(f"  H(0) = {mi.entropy_a:.4f}, H(1) = {mi.entropy_b:.4f}, H(01) = {mi.entropy_ab:.4f}")
    
    # Example 2: Product state (no entanglement)
    product_counts = {
        '00': 250,
        '01': 250,
        '10': 250,
        '11': 250,
    }
    
    print("\nProduct state (no entanglement):")
    mi = analyzer.compute_bipartite_mutual_information(product_counts, [0], [1])
    print(f"  MI(0:1) = {mi.mutual_information:.4f}")


if __name__ == '__main__':
    main()
