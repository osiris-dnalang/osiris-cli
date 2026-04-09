"""
OSIRIS Quantum Lab — Research & Development Engine
===================================================

Discovers, catalogs, designs, and executes quantum experiments.
Integrates with the full OSIRIS ecosystem: sovereign proofs,
SCIMITAR threat scanning, CHRONOS lineage tracking.

Modules:
  scanner.py    — Filesystem scanner for experiments & results
  registry.py   — Structured experiment catalog
  designer.py   — Experiment designer with circuit templates
  executor.py   — Safe experiment execution engine
"""

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
    "ExperimentRegistry",
    "ExperimentRecord",
    "ExperimentType",
    "ExperimentStatus",
    "ResultRecord",
    "LabScanner",
    "ExperimentDesigner",
    "ExperimentTemplate",
    "LabExecutor",
]
