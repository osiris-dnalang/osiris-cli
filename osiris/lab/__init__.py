"""osiris.lab — Experiment registry, designer, executor, scanner, autopoietic loop."""

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
from .autopoietic_loop import AutopoieticLoop
from .habitat_scanner import HabitatScanner, HabitatEntry

__all__ = [
    "ExperimentRegistry", "ExperimentRecord", "ExperimentType",
    "ExperimentStatus", "ResultRecord",
    "LabScanner",
    "ExperimentDesigner", "ExperimentTemplate",
    "LabExecutor",
    "AutopoieticLoop",
    "HabitatScanner", "HabitatEntry",
]
