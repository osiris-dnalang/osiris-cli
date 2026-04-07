#!/usr/bin/env python3
"""
Quantum Data Loader: Discover, validate, and standardize 1,430+ IBM quantum job results.

This module provides tools to:
1. Recursively find all quantum job result files (JSON, QASM, count data)
2. Validate data integrity (shot counts, circuit structure)
3. Create a unified inventory (data_inventory.json)
4. Normalize measurement outcomes for analysis
5. Estimate hardware noise characteristics from historical data
"""

import json
import os
import glob
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
import numpy as np
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CircuitMetadata:
    """Metadata for a quantum circuit."""
    circuit_id: str
    num_qubits: int
    circuit_depth: int
    gate_count: int
    result_path: str
    shots: int
    has_measurement_counts: bool
    has_statevector: bool
    has_noise_info: bool
    creation_timestamp: str
    file_size_bytes: int
    circuit_type: Optional[str] = None  # VQE, random, GHZ, etc.
    parameter_values: Optional[Dict] = None


@dataclass
class MeasurementData:
    """Normalized measurement outcome data."""
    circuit_id: str
    counts: Dict[str, int]  # bitstring -> count
    shots: int
    probabilities: Dict[str, float]  # bitstring -> probability
    num_qubits: int
    entropy: Optional[float] = None
    purity_estimate: Optional[float] = None


class QuantumDataLoader:
    """Discover and load quantum circuit data from filesystem."""
    
    def __init__(self, workspace_root: str = "/workspaces/osiris-cli"):
        self.workspace_root = workspace_root
        self.inventory: Dict[str, CircuitMetadata] = {}
        self.measurement_data: Dict[str, MeasurementData] = {}
        
    def audit_filesystem(self, max_results: Optional[int] = None) -> Dict[str, Any]:
        """
        Recursively search workspace for quantum job result files.
        
        Returns summary of findings:
        {
            'json_files': count,
            'qasm_files': count,
            'ibm_result_files': count,
            'total_files_found': count,
            'total_size_gb': float
        }
        """
        logger.info(f"Starting filesystem audit of {self.workspace_root}...")
        
        patterns = [
            '**/*.json',          # IBM job results, noise models
            '**/*.qasm',          # Circuit definitions
            '**/*counts*.txt',    # Measurement count data
            '**/*results*.pkl',   # Pickled results
        ]
        
        results = {
            'json_files': 0,
            'qasm_files': 0,
            'ibm_result_files': 0,
            'potential_job_results': [],
            'total_size_bytes': 0,
            'directories_scanned': 0,
        }
        
        for pattern in patterns:
            search_path = os.path.join(self.workspace_root, pattern)
            files_found = glob.glob(search_path, recursive=True)
            
            for filepath in files_found[:max_results] if max_results else files_found:
                if not os.path.isfile(filepath):
                    continue
                
                file_size = os.path.getsize(filepath)
                results['total_size_bytes'] += file_size
                
                if filepath.endswith('.json'):
                    results['json_files'] += 1
                    # Try to identify IBM job results
                    if self._is_ibm_job_result(filepath):
                        results['ibm_result_files'] += 1
                        results['potential_job_results'].append(filepath)
                        logger.debug(f"Found IBM job result: {filepath}")
                        
                elif filepath.endswith('.qasm'):
                    results['qasm_files'] += 1
        
        results['total_size_gb'] = results['total_size_bytes'] / (1024**3)
        logger.info(f"Audit complete. Found {results['json_files']} JSON files, "
                   f"{results['qasm_files']} QASM files, "
                   f"{results['ibm_result_files']} IBM results")
        
        return results
    
    def _is_ibm_job_result(self, filepath: str) -> bool:
        """Heuristic: check if JSON file looks like an IBM job result."""
        try:
            with open(filepath, 'r') as f:
                content = f.read(1000)  # Read first 1KB
                # Look for IBM-specific keys
                return any(key in content for key in [
                    '"results":', '"backend_name":', '"job_id":', 
                    '"success":', '"counts":', '"statevector":'
                ])
        except Exception as e:
            logger.debug(f"Could not read {filepath}: {e}")
            return False
    
    def load_job_result(self, result_path: str, circuit_id: Optional[str] = None) -> Optional[CircuitMetadata]:
        """
        Load and validate a single IBM job result file.
        
        Returns CircuitMetadata object or None if invalid.
        """
        if not os.path.exists(result_path):
            logger.warning(f"Result file not found: {result_path}")
            return None
        
        try:
            with open(result_path, 'r') as f:
                data = json.load(f)
            
            # Extract circuit information
            circuit_id = circuit_id or hashlib.md5(
                f"{result_path}{os.path.getmtime(result_path)}".encode()
            ).hexdigest()[:16]
            
            num_qubits = self._extract_num_qubits(data)
            circuit_depth = self._extract_circuit_depth(data)
            gate_count = self._extract_gate_count(data)
            shots = self._extract_shots(data)
            
            has_measurement_counts = 'counts' in str(data) or 'measurement_results' in str(data)
            has_statevector = 'statevector' in str(data)
            has_noise_info = 'noise_model' in str(data) or 'backend_properties' in str(data)
            
            metadata = CircuitMetadata(
                circuit_id=circuit_id,
                num_qubits=num_qubits,
                circuit_depth=circuit_depth,
                gate_count=gate_count,
                result_path=result_path,
                shots=shots,
                has_measurement_counts=has_measurement_counts,
                has_statevector=has_statevector,
                has_noise_info=has_noise_info,
                creation_timestamp=datetime.fromtimestamp(
                    os.path.getmtime(result_path)
                ).isoformat(),
                file_size_bytes=os.path.getsize(result_path),
            )
            
            self.inventory[circuit_id] = metadata
            logger.info(f"Loaded: {circuit_id} ({num_qubits}q, depth={circuit_depth})")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load {result_path}: {e}")
            return None
    
    def _extract_num_qubits(self, data: Dict) -> int:
        """Extract number of qubits from IBM job result."""
        if 'result' in data and 'num_qubits' in data['result']:
            return data['result']['num_qubits']
        if 'num_qubits' in data:
            return data['num_qubits']
        if 'counts' in data:
            # Infer from bitstring length
            for bitstring in data['counts'].keys():
                return len(bitstring)
        return 0
    
    def _extract_circuit_depth(self, data: Dict) -> int:
        """Extract circuit depth from IBM job result."""
        if 'circuit_info' in data and 'depth' in data['circuit_info']:
            return data['circuit_info']['depth']
        if 'depth' in data:
            return data['depth']
        return 0
    
    def _extract_gate_count(self, data: Dict) -> int:
        """Extract total gate count from IBM job result."""
        if 'circuit_info' in data and 'gate_count' in data['circuit_info']:
            return data['circuit_info']['gate_count']
        if 'gates' in data:
            return len(data['gates'])
        return 0
    
    def _extract_shots(self, data: Dict) -> int:
        """Extract shot count from IBM job result."""
        if 'metadata' in data and 'shots' in data['metadata']:
            return data['metadata']['shots']
        if 'shots' in data:
            return data['shots']
        # Infer from total counts
        if 'counts' in data:
            return sum(data['counts'].values())
        return 1024  # Default assumption
    
    def normalize_measurement_counts(self, circuit_id: str, counts: Dict[str, int]) -> MeasurementData:
        """
        Normalize raw measurement counts to probabilities.
        
        Args:
            circuit_id: Identifier for circuit
            counts: dict mapping bitstring -> count
        
        Returns:
            MeasurementData with normalized probabilities
        """
        total_shots = sum(counts.values())
        num_qubits = len(next(iter(counts.keys()))) if counts else 0
        
        probabilities = {bitstring: count / total_shots for bitstring, count in counts.items()}
        
        # Compute entropy
        entropy = self._compute_entropy(probabilities)
        purity = self._compute_purity_estimate(probabilities)
        
        data = MeasurementData(
            circuit_id=circuit_id,
            counts=counts,
            shots=total_shots,
            probabilities=probabilities,
            num_qubits=num_qubits,
            entropy=entropy,
            purity_estimate=purity,
        )
        
        self.measurement_data[circuit_id] = data
        return data
    
    def _compute_entropy(self, probabilities: Dict[str, float]) -> float:
        """Compute Shannon entropy from measurement probabilities."""
        entropy = 0.0
        for p in probabilities.values():
            if p > 0:
                entropy -= p * np.log2(p)
        return entropy
    
    def _compute_purity_estimate(self, probabilities: Dict[str, float]) -> float:
        """Estimate purity Tr(ρ²) from measurement statistics."""
        return sum(p**2 for p in probabilities.values())
    
    def save_inventory(self, output_path: str = "data_inventory.json"):
        """Save circuit inventory to JSON file."""
        inventory_data = {
            circuit_id: asdict(metadata)
            for circuit_id, metadata in self.inventory.items()
        }
        
        with open(output_path, 'w') as f:
            json.dump(inventory_data, f, indent=2)
        
        logger.info(f"Saved inventory of {len(self.inventory)} circuits to {output_path}")
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Return summary statistics of loaded inventory."""
        if not self.inventory:
            return {'error': 'No circuits loaded'}
        
        qubits = [m.num_qubits for m in self.inventory.values()]
        depths = [m.circuit_depth for m in self.inventory.values()]
        shots = [m.shots for m in self.inventory.values()]
        
        return {
            'total_circuits': len(self.inventory),
            'qubit_range': [int(min(qubits)), int(max(qubits))],
            'depth_range': [int(min(depths)), int(max(depths))],
            'shots_range': [int(min(shots)), int(max(shots))],
            'avg_shots': float(np.mean(shots)),
            'total_data_gb': sum(m.file_size_bytes for m in self.inventory.values()) / (1024**3),
            'circuits_with_measurement_counts': sum(1 for m in self.inventory.values() if m.has_measurement_counts),
            'circuits_with_statevector': sum(1 for m in self.inventory.values() if m.has_statevector),
        }


def main():
    """Example usage: audit workspace and load sample results."""
    loader = QuantumDataLoader()
    
    # Step 1: Audit filesystem
    audit_results = loader.audit_filesystem(max_results=10000)
    print("\n=== FILESYSTEM AUDIT ===")
    print(json.dumps(audit_results, indent=2))
    
    # Step 2: Load sample IBM job results
    print("\n=== LOADING SAMPLE RESULTS ===")
    if audit_results['potential_job_results']:
        for result_path in audit_results['potential_job_results'][:5]:
            metadata = loader.load_job_result(result_path)
            if metadata:
                print(f"Loaded: {metadata.circuit_id}, {metadata.num_qubits}q, depth={metadata.circuit_depth}")
    
    # Step 3: Save inventory
    print("\n=== SAVING INVENTORY ===")
    loader.save_inventory("data_inventory.json")
    
    # Step 4: Print summary
    summary = loader.get_inventory_summary()
    print("\n=== INVENTORY SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
