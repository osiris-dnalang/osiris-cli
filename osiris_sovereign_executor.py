#!/usr/bin/env python3
"""
OSIRIS Sovereign Executor — Physicalization Pipeline
=====================================================

Extends the Sovereign Executor concept (IBM-independent local execution)
to handle physicalization tasks: converting mathematical structures into
physical 3D-printed objects via local printers.

Execution Modes:
  ├── GENERATE   : Create mesh from organism genes (GeometricEngine)
  ├── SLICE      : Convert mesh to G-code via slicer CLI
  ├── DISCOVER   : Scan network for available printers
  ├── TRANSMIT   : Send G-code to printer (MQTT/FTP/HTTP)
  ├── MONITOR    : Real-time printer status via MQTT
  └── EXPORT     : Copy G-code to flash drive / filesystem

All tasks pass through the Compliance Gate before execution.

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger('OSIRIS_SOVEREIGN_EXEC')

# ════════════════════════════════════════════════════════════════════════════════
# TASK DEFINITIONS
# ════════════════════════════════════════════════════════════════════════════════

class PhysicalizationMode(Enum):
    """Physicalization execution modes"""
    GENERATE = "generate"
    SLICE = "slice"
    DISCOVER = "discover"
    TRANSMIT = "transmit"
    MONITOR = "monitor"
    EXPORT = "export"
    FULL_PIPELINE = "full_pipeline"


@dataclass
class PhysicalizationTask:
    """A task to be executed by the Sovereign Executor."""
    mode: PhysicalizationMode
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_printer: Optional[str] = None       # Printer IP or name
    model_path: Optional[str] = None           # Input model path
    gcode_path: Optional[str] = None           # Output G-code path
    flash_mount: Optional[str] = None          # Flash drive mount point
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: str = ""

    def __post_init__(self):
        if not self.task_id:
            import hashlib
            raw = f"{self.mode.value}-{self.created_at}-{id(self)}"
            self.task_id = hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class ExecutionResult:
    """Result of a physicalization execution."""
    task_id: str
    mode: str
    success: bool
    message: str
    output_path: Optional[str] = None
    printer_status: Optional[Dict] = None
    discovered_printers: Optional[List[Dict]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ════════════════════════════════════════════════════════════════════════════════
# SOVEREIGN EXECUTOR — PHYSICALIZATION ENGINE
# ════════════════════════════════════════════════════════════════════════════════

class SovereignPhysicalizationExecutor:
    """
    Sovereign Executor for physicalization tasks.

    This executor operates entirely on local hardware:
      • No cloud dependencies
      • No external vendor lock-in
      • Direct printer communication via local network
      • Compliance gate enforcement on every task

    Maps directly to the Sovereign Substrate architecture:
      sovereign_substrate.sh → consolidates external repos
      sovereign_executor.py  → executes quantum circuits locally
      THIS MODULE            → executes physicalization tasks locally
    """

    def __init__(self, organism_dir: str = "./organism",
                 output_dir: str = "./manufacturing_output"):
        self.organism_dir = organism_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execution_log: List[ExecutionResult] = []
        self._compliance_checked = False

    def _check_compliance(self) -> bool:
        """
        Run Compliance Gate before any manufacturing task.
        Corporate/institutional use requires a commercial license.
        """
        if self._compliance_checked:
            return True

        try:
            from osiris_license import ComplianceGate
            compliant, msg = ComplianceGate.check(strict=True)
            if not compliant:
                logger.error(f"Compliance Gate BLOCKED manufacturing: {msg}")
                return False
            self._compliance_checked = True
            return True
        except ImportError:
            logger.warning("License module not available — allowing execution")
            self._compliance_checked = True
            return True

    def execute(self, task: PhysicalizationTask) -> ExecutionResult:
        """
        Execute a physicalization task.

        Every task must pass the Compliance Gate first.
        """
        import time
        start = time.time()

        # Compliance gate
        if not self._check_compliance():
            result = ExecutionResult(
                task_id=task.task_id,
                mode=task.mode.value,
                success=False,
                message="Blocked by Compliance Gate — commercial license required",
            )
            self.execution_log.append(result)
            return result

        # Dispatch
        handlers = {
            PhysicalizationMode.GENERATE: self._exec_generate,
            PhysicalizationMode.SLICE: self._exec_slice,
            PhysicalizationMode.DISCOVER: self._exec_discover,
            PhysicalizationMode.TRANSMIT: self._exec_transmit,
            PhysicalizationMode.MONITOR: self._exec_monitor,
            PhysicalizationMode.EXPORT: self._exec_export,
            PhysicalizationMode.FULL_PIPELINE: self._exec_full_pipeline,
        }

        handler = handlers.get(task.mode)
        if not handler:
            result = ExecutionResult(
                task_id=task.task_id,
                mode=task.mode.value,
                success=False,
                message=f"Unknown mode: {task.mode.value}",
            )
            self.execution_log.append(result)
            return result

        try:
            result = handler(task)
        except Exception as e:
            result = ExecutionResult(
                task_id=task.task_id,
                mode=task.mode.value,
                success=False,
                message=f"Execution error: {e}",
            )

        result.duration_seconds = time.time() - start
        self.execution_log.append(result)

        logger.info(
            f"Task {task.task_id} [{task.mode.value}]: "
            f"{'SUCCESS' if result.success else 'FAILED'} "
            f"({result.duration_seconds:.2f}s)"
        )
        return result

    # ── GENERATE ──────────────────────────────────────────────────────────

    def _exec_generate(self, task: PhysicalizationTask) -> ExecutionResult:
        """Generate mesh from organism genes."""
        from osiris_manufacturing_3mf import (
            ManufacturingPipeline, ManufacturingConfig, ManufacturingMode, PrinterType
        )

        params = task.parameters
        mode_str = params.get("mode", "tetrahedral_lattice")
        scale = params.get("scale_cm", 10.0)
        resolution = params.get("resolution", 64)
        depth = params.get("lattice_depth", 3)
        fmt = params.get("format", "stl")
        printer_str = params.get("printer_type", "generic_fdm")

        config = ManufacturingConfig(
            mode=ManufacturingMode(mode_str),
            scale_cm=scale,
            resolution=resolution,
            lattice_depth=depth,
            output_format=fmt,
            printer_type=PrinterType(printer_str),
        )

        pipeline = ManufacturingPipeline(organism_dir=self.organism_dir)
        mfg_result = pipeline.run(config)

        return ExecutionResult(
            task_id=task.task_id,
            mode=task.mode.value,
            success=bool(mfg_result.model_path),
            message=f"Generated {mfg_result.vertices} verts, {mfg_result.faces} faces",
            output_path=mfg_result.model_path,
            metadata={
                "vertices": mfg_result.vertices,
                "faces": mfg_result.faces,
                "volume_cm3": mfg_result.volume_cm3,
                "bounding_box": mfg_result.bounding_box_cm,
            },
        )

    # ── SLICE ─────────────────────────────────────────────────────────────

    def _exec_slice(self, task: PhysicalizationTask) -> ExecutionResult:
        """Slice a model into G-code."""
        from osiris_manufacturing_3mf import SlicerPipeline, PrinterType

        model_path = task.model_path or task.parameters.get("model_path")
        if not model_path or not Path(model_path).exists():
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False, message=f"Model not found: {model_path}",
            )

        printer_str = task.parameters.get("printer_type", "generic_fdm")
        slicer = SlicerPipeline()

        if not slicer.slicer_path:
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False,
                message="No slicer CLI found. Install BambuStudio or PrusaSlicer.",
            )

        gcode = slicer.slice_model(model_path, PrinterType(printer_str))
        return ExecutionResult(
            task_id=task.task_id, mode=task.mode.value,
            success=bool(gcode),
            message=f"G-code: {gcode}" if gcode else "Slicing failed",
            output_path=gcode,
        )

    # ── DISCOVER ──────────────────────────────────────────────────────────

    def _exec_discover(self, task: PhysicalizationTask) -> ExecutionResult:
        """Discover printers on the local network."""
        from osiris_auto_discovery import PrinterDiscoveryService

        timeout = task.parameters.get("timeout", 10.0)
        service = PrinterDiscoveryService()
        printers = service.scan(timeout=timeout)

        return ExecutionResult(
            task_id=task.task_id, mode=task.mode.value,
            success=True,
            message=f"Found {len(printers)} printers",
            discovered_printers=[asdict(p) for p in printers],
        )

    # ── TRANSMIT ──────────────────────────────────────────────────────────

    def _exec_transmit(self, task: PhysicalizationTask) -> ExecutionResult:
        """Send G-code to a printer."""
        gcode_path = task.gcode_path or task.parameters.get("gcode_path")
        target = task.target_printer or task.parameters.get("target_printer")

        if not gcode_path or not Path(gcode_path).exists():
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False, message=f"G-code not found: {gcode_path}",
            )

        if not target:
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False, message="No target printer specified",
            )

        # Determine transfer protocol from printer discovery
        protocol = task.parameters.get("protocol", "ftp")

        if protocol == "ftp":
            success = self._transmit_ftp(gcode_path, target)
        elif protocol == "http":
            success = self._transmit_http(gcode_path, target)
        else:
            success = False

        return ExecutionResult(
            task_id=task.task_id, mode=task.mode.value,
            success=success,
            message=f"Transmitted to {target}" if success else f"Transfer failed to {target}",
        )

    @staticmethod
    def _transmit_ftp(gcode_path: str, target: str, port: int = 990) -> bool:
        """Transfer G-code via FTP (Bambu Lab default)."""
        import ftplib
        try:
            ftp = ftplib.FTP_TLS()
            ftp.connect(target, port, timeout=30)
            ftp.login()
            ftp.prot_p()
            filename = Path(gcode_path).name
            with open(gcode_path, 'rb') as f:
                ftp.storbinary(f"STOR {filename}", f)
            ftp.quit()
            logger.info(f"FTP transfer complete: {filename} → {target}")
            return True
        except Exception as e:
            logger.error(f"FTP transfer failed: {e}")
            return False

    @staticmethod
    def _transmit_http(gcode_path: str, target: str, port: int = 80) -> bool:
        """Transfer G-code via HTTP upload (Elegoo / generic)."""
        try:
            import requests
            url = f"http://{target}:{port}/upload"
            with open(gcode_path, 'rb') as f:
                files = {'file': (Path(gcode_path).name, f)}
                resp = requests.post(url, files=files, timeout=60)
            success = resp.status_code in (200, 201)
            if success:
                logger.info(f"HTTP upload complete: {target}")
            else:
                logger.error(f"HTTP upload failed: {resp.status_code}")
            return success
        except Exception as e:
            logger.error(f"HTTP transfer failed: {e}")
            return False

    # ── MONITOR ───────────────────────────────────────────────────────────

    def _exec_monitor(self, task: PhysicalizationTask) -> ExecutionResult:
        """Monitor printer status."""
        from osiris_auto_discovery import PrinterDiscoveryService, DiscoveredPrinter

        target = task.target_printer or task.parameters.get("target_printer")
        if not target:
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False, message="No target printer specified",
            )

        # Create a synthetic printer object for status query
        printer = DiscoveredPrinter(
            name="target",
            printer_type=task.parameters.get("printer_type", "bambu_generic"),
            ip_address=target,
            port=task.parameters.get("port", 8883),
            protocol="mqtt",
            serial=task.parameters.get("serial", ""),
        )

        service = PrinterDiscoveryService()
        status = service.get_bambu_status(printer)

        return ExecutionResult(
            task_id=task.task_id, mode=task.mode.value,
            success=status.get("status") != "error",
            message=f"Printer status: {status.get('status', 'unknown')}",
            printer_status=status,
        )

    # ── EXPORT ────────────────────────────────────────────────────────────

    def _exec_export(self, task: PhysicalizationTask) -> ExecutionResult:
        """Export G-code to flash drive."""
        from osiris_manufacturing_3mf import SlicerPipeline

        gcode_path = task.gcode_path or task.parameters.get("gcode_path")
        mount = task.flash_mount or task.parameters.get("flash_mount", "/media/usb")

        if not gcode_path or not Path(gcode_path).exists():
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False, message=f"G-code not found: {gcode_path}",
            )

        slicer = SlicerPipeline()
        success = slicer.export_to_flash_drive(gcode_path, mount)

        return ExecutionResult(
            task_id=task.task_id, mode=task.mode.value,
            success=success,
            message=f"Exported to {mount}" if success else "Flash drive not found",
        )

    # ── FULL PIPELINE ─────────────────────────────────────────────────────

    def _exec_full_pipeline(self, task: PhysicalizationTask) -> ExecutionResult:
        """
        Run the complete physicalization pipeline:
          1. Discover printers
          2. Generate mesh
          3. Slice to G-code
          4. Transmit or export
        """
        results = []

        # Step 1: Discover
        discover_task = PhysicalizationTask(mode=PhysicalizationMode.DISCOVER, parameters=task.parameters)
        discover_result = self._exec_discover(discover_task)
        results.append(("discover", discover_result))

        # Step 2: Generate
        gen_task = PhysicalizationTask(mode=PhysicalizationMode.GENERATE, parameters=task.parameters)
        gen_result = self._exec_generate(gen_task)
        results.append(("generate", gen_result))

        if not gen_result.success:
            return ExecutionResult(
                task_id=task.task_id, mode=task.mode.value,
                success=False, message=f"Generation failed: {gen_result.message}",
                metadata={"steps": [(s, r.success) for s, r in results]},
            )

        # Step 3: Slice
        slice_task = PhysicalizationTask(
            mode=PhysicalizationMode.SLICE,
            model_path=gen_result.output_path,
            parameters=task.parameters,
        )
        slice_result = self._exec_slice(slice_task)
        results.append(("slice", slice_result))

        # Step 4: Transmit or Export
        if slice_result.success and slice_result.output_path:
            if task.target_printer:
                tx_task = PhysicalizationTask(
                    mode=PhysicalizationMode.TRANSMIT,
                    gcode_path=slice_result.output_path,
                    target_printer=task.target_printer,
                    parameters=task.parameters,
                )
                tx_result = self._exec_transmit(tx_task)
                results.append(("transmit", tx_result))
            elif task.flash_mount:
                ex_task = PhysicalizationTask(
                    mode=PhysicalizationMode.EXPORT,
                    gcode_path=slice_result.output_path,
                    flash_mount=task.flash_mount,
                    parameters=task.parameters,
                )
                ex_result = self._exec_export(ex_task)
                results.append(("export", ex_result))

        all_success = all(r.success for _, r in results)
        return ExecutionResult(
            task_id=task.task_id,
            mode=task.mode.value,
            success=all_success,
            message=f"Pipeline {'complete' if all_success else 'partial'}: "
                    f"{sum(1 for _, r in results if r.success)}/{len(results)} steps",
            output_path=slice_result.output_path if slice_result.success else gen_result.output_path,
            discovered_printers=discover_result.discovered_printers,
            metadata={"steps": [(s, r.success, r.message) for s, r in results]},
        )

    # ── REPORTING ─────────────────────────────────────────────────────────

    def execution_summary(self) -> str:
        """Generate execution log summary."""
        lines = [
            "═" * 60,
            "  SOVEREIGN PHYSICALIZATION EXECUTOR — LOG",
            "═" * 60,
            "",
        ]
        for r in self.execution_log:
            status = "✓" if r.success else "✗"
            lines.extend([
                f"  {status} [{r.task_id}] {r.mode}: {r.message}",
                f"    Duration: {r.duration_seconds:.2f}s",
            ])
            if r.output_path:
                lines.append(f"    Output:   {r.output_path}")
            lines.append("")
        lines.append("═" * 60)
        return "\n".join(lines)

    def save_log(self, filepath: Optional[str] = None):
        """Save execution log to JSON."""
        path = filepath or str(self.output_dir / "execution_log.json")
        log_data = [asdict(r) for r in self.execution_log]
        with open(path, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        logger.info(f"Execution log saved: {path}")


# ════════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="OSIRIS Sovereign Physicalization Executor"
    )
    parser.add_argument("mode", choices=[m.value for m in PhysicalizationMode],
                        help="Execution mode")
    parser.add_argument("--model", type=str, help="Input model path")
    parser.add_argument("--gcode", type=str, help="G-code path")
    parser.add_argument("--printer", type=str, help="Target printer IP/name")
    parser.add_argument("--flash", type=str, help="Flash drive mount point")
    parser.add_argument("--scale", type=float, default=10.0, help="Scale in cm")
    parser.add_argument("--geometry", default="tetrahedral_lattice",
                        help="Geometry mode for generation")
    parser.add_argument("--format", default="stl", choices=["3mf", "stl", "both"])

    args = parser.parse_args()

    executor = SovereignPhysicalizationExecutor()
    task = PhysicalizationTask(
        mode=PhysicalizationMode(args.mode),
        model_path=args.model,
        gcode_path=args.gcode,
        target_printer=args.printer,
        flash_mount=args.flash,
        parameters={
            "mode": args.geometry,
            "scale_cm": args.scale,
            "format": args.format,
        },
    )

    result = executor.execute(task)
    print(executor.execution_summary())

    if result.discovered_printers:
        print(f"\nDiscovered {len(result.discovered_printers)} printers:")
        for p in result.discovered_printers:
            print(f"  • {p['name']} ({p['printer_type']}) @ {p['ip_address']}:{p['port']}")
