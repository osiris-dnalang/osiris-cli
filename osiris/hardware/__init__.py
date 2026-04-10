"""osiris.hardware — Hardware adapters (QuEra, Braket, workload)."""

from .quera_adapter import QuEraCorrelatedAdapter
from .workload_extractor import (
    WorkloadExtractor, SubstratePipeline, QuantumJobResult,
    IBMBackendSpec, IBM_BACKENDS,
)
