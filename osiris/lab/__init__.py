"""osiris.lab — Experiment registry, designer, executor, scanner."""

from .registry import (
    ExperimentRegistry,
    ExperimentRecord,
    ExperimentType,
    ExperimentStatus,
    ResultRecord,
)
from .scanner import LabScanner
from .designer import ExperimentDesigner, ExperimentTemplate
from .executor import LabExecutor

__all__ = [
    "ExperimentRegistry", "ExperimentRecord", "ExperimentType",
    "ExperimentStatus", "ResultRecord",
    "LabScanner",
    "ExperimentDesigner", "ExperimentTemplate",
    "LabExecutor",
]
