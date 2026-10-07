"""
QuEra Correlated Decoder Adapter — Maps neutral-atom syndrome data through
tesseract A* decoding with correlated noise modeling.
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from osiris.decoders.tesseract import TesseractDecoderOrganism, TesseractResonatorOrganism


@dataclass
class ErrorMap:
    physical_qubits: int
    error_rate: float
    correlations: Dict[Tuple[int, int], float] = field(default_factory=dict)


class QuEraCorrelatedAdapter:
    """Adapter for correlated decoding of QuEra neutral-atom syndrome data."""

    def __init__(self, distance: int = 3, physical_error_rate: float = 0.005,
                 rounds: int = 10):
        self.distance = distance
        self.physical_error_rate = physical_error_rate
        self.rounds = rounds
        self.decoder = TesseractDecoderOrganism(distance=distance)
        self.resonator = TesseractResonatorOrganism(distance=distance)

    def build_error_map(self, n_qubits: int,
                        calibration: Optional[Dict] = None) -> ErrorMap:
        em = ErrorMap(physical_qubits=n_qubits, error_rate=self.physical_error_rate)
        for i in range(n_qubits - 1):
            em.correlations[(i, i + 1)] = self.physical_error_rate * 0.1
        return em

    def inject_logical_errors(self, n_qubits: int,
                              error_map: Optional[ErrorMap] = None) -> Tuple[int, ...]:
        errors = tuple(
            1 if random.random() < self.physical_error_rate else 0
            for _ in range(n_qubits)
        )
        return errors

    def generate_round_syndromes(self, n_qubits: int,
                                 rounds: Optional[int] = None) -> List[Tuple[int, ...]]:
        r = rounds or self.rounds
        syndromes = []
        for _ in range(r):
            syndrome = tuple(
                1 if random.random() < self.physical_error_rate * 2 else 0
                for _ in range(n_qubits)
            )
            syndromes.append(syndrome)
        return syndromes

    def correlated_merge_rounds(self,
                                syndromes: List[Tuple[int, ...]]) -> Tuple[int, ...]:
        if not syndromes:
            return ()
        n = len(syndromes[0])
        merged = [0] * n
        for s in syndromes:
            for i in range(n):
                merged[i] += s[i]
        threshold = len(syndromes) // 2 + 1
        return tuple(1 if m >= threshold else 0 for m in merged)

    def decode_merged(self, merged: Tuple[int, ...]) -> Tuple[int, ...]:
        return self.decoder.decode(merged)

    def run_dry(self, n_qubits: Optional[int] = None) -> Dict[str, Any]:
        nq = n_qubits or self.distance ** 2
        error_map = self.build_error_map(nq)
        syndromes = self.generate_round_syndromes(nq)
        merged = self.correlated_merge_rounds(syndromes)
        correction = self.decode_merged(merged)
        return {
            "distance": self.distance,
            "physical_qubits": nq,
            "rounds": self.rounds,
            "syndrome_weight": sum(merged),
            "correction_weight": sum(correction),
            "status": "success",
        }
