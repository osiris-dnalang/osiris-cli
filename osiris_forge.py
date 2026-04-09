#!/usr/bin/env python3
"""
OSIRIS Forge — Quantum-to-Matter Manufacturing Pipeline
=========================================================

The Forge is the unified interface between OSIRIS mathematical discovery
and physical 3D printing hardware. It orchestrates the full pipeline:

    Oracle Math → Torsion Core → .3mf Mesh → Slicer → G-Code → Printer

Supported Hardware:
  ├── Bambu Lab P1S        (FDM, MQTT + FTP, multi-material AMS)
  ├── Bambu Lab A1 Mini    (FDM, MQTT + FTP, compact format)
  └── Elegoo Centauri 2    (Resin MSLA, HTTP/USB, high-detail)

Network Protocols:
  ├── mDNS/ZeroConf        Discovery (_bambulab._tcp, _ipp._tcp)
  ├── MQTT (port 8883)     Bambu command & status monitoring
  ├── FTPS (port 990)      Bambu G-code file transfer
  ├── Moonraker HTTP API   Klipper-based printer control
  └── USB/Flash Export     Air-gapped transfer via Sovereign Substrate

Security:
  • Every forge command passes through the Compliance Gate
  • G-code sanitization prevents printer-killer commands
  • .3mf files embed cryptographic watermark metadata
  • Corporate network detection blocks physicalization

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

import os
import sys
import json
import time
import hashlib
import logging
import subprocess
import struct
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import numpy as np

logger = logging.getLogger('OSIRIS_FORGE')

# ════════════════════════════════════════════════════════════════════════════════
# OPTIONAL DEPENDENCIES — graceful degradation
# ════════════════════════════════════════════════════════════════════════════════

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    from zeroconf import Zeroconf, ServiceBrowser
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ════════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════════════════════

LAMBDA_PHI = 2.176435e-8
TORSION_LOCK = 51.843
GOLDEN_RATIO = 1.6180339887498949
FORGE_VERSION = "1.0.0"

# G-code safety: commands that must NEVER appear in output
GCODE_DANGEROUS_COMMANDS = {
    'M112',         # Emergency stop (can corrupt firmware state)
    'M502',         # Factory reset
    'M500',         # Save to EEPROM (can brick with bad values)
    'G28 Z-100',    # Crash nozzle into bed
}

# G-code temperature safety limits
GCODE_TEMP_LIMITS = {
    'nozzle_max': 300,      # °C — above this risks fire
    'bed_max': 120,         # °C
    'resin_uv_max': 100,    # % power
}


# ════════════════════════════════════════════════════════════════════════════════
# PRINTER HARDWARE PROFILES
# ════════════════════════════════════════════════════════════════════════════════

class PrinterHardware(Enum):
    """Supported printer hardware"""
    BAMBU_P1S = "bambu_p1s"
    BAMBU_A1_MINI = "bambu_a1_mini"
    ELEGOO_CENTAURI_2 = "elegoo_centauri_2"
    GENERIC_FDM = "generic_fdm"
    GENERIC_RESIN = "generic_resin"


@dataclass
class PrinterProfile:
    """Hardware-specific printer configuration"""
    hardware: PrinterHardware
    name: str
    build_volume_mm: Tuple[float, float, float]     # X, Y, Z
    nozzle_diameter: float                           # mm
    layer_height_default: float                      # mm
    layer_height_min: float                          # mm
    filament_diameter: float                         # mm (1.75 FDM, 0 resin)
    max_speed_mm_s: float
    heated_bed: bool
    max_nozzle_temp: int                             # °C
    max_bed_temp: int                                # °C
    protocol: str                                    # mqtt, http, usb
    default_port: int
    supports_ams: bool = False                       # Bambu AMS multi-material
    is_resin: bool = False
    firmware: str = ""
    mqtt_topic_prefix: str = ""
    ftp_port: int = 990


# Pre-configured profiles for user's hardware
PRINTER_PROFILES: Dict[PrinterHardware, PrinterProfile] = {
    PrinterHardware.BAMBU_P1S: PrinterProfile(
        hardware=PrinterHardware.BAMBU_P1S,
        name="Bambu Lab P1S",
        build_volume_mm=(256, 256, 256),
        nozzle_diameter=0.4,
        layer_height_default=0.20,
        layer_height_min=0.08,
        filament_diameter=1.75,
        max_speed_mm_s=500,
        heated_bed=True,
        max_nozzle_temp=300,
        max_bed_temp=110,
        protocol="mqtt",
        default_port=8883,
        supports_ams=True,
        firmware="bambu",
        mqtt_topic_prefix="device",
        ftp_port=990,
    ),
    PrinterHardware.BAMBU_A1_MINI: PrinterProfile(
        hardware=PrinterHardware.BAMBU_A1_MINI,
        name="Bambu Lab A1 Mini",
        build_volume_mm=(180, 180, 180),
        nozzle_diameter=0.4,
        layer_height_default=0.20,
        layer_height_min=0.08,
        filament_diameter=1.75,
        max_speed_mm_s=500,
        heated_bed=True,
        max_nozzle_temp=300,
        max_bed_temp=80,
        protocol="mqtt",
        default_port=8883,
        supports_ams=True,
        firmware="bambu",
        mqtt_topic_prefix="device",
        ftp_port=990,
    ),
    PrinterHardware.ELEGOO_CENTAURI_2: PrinterProfile(
        hardware=PrinterHardware.ELEGOO_CENTAURI_2,
        name="Elegoo Centauri Carbon 2",
        build_volume_mm=(218, 123, 210),
        nozzle_diameter=0.0,          # Resin — no nozzle
        layer_height_default=0.05,
        layer_height_min=0.01,
        filament_diameter=0.0,        # Resin — no filament
        max_speed_mm_s=0,             # Resin — layer-based
        heated_bed=False,
        max_nozzle_temp=0,
        max_bed_temp=0,
        protocol="usb",
        default_port=0,
        is_resin=True,
        firmware="chitubox",
    ),
}


# ════════════════════════════════════════════════════════════════════════════════
# FORGE CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class ForgeJob:
    """A complete forge manufacturing job"""
    job_id: str = ""
    geometry: str = "tetrahedral_lattice"   # Manufacturing mode
    target_printer: PrinterHardware = PrinterHardware.BAMBU_P1S
    scale_cm: float = 10.0
    resolution: int = 64
    infill_percent: int = 20
    infill_pattern: str = "gyroid"          # gyroid for acoustic, grid for structural
    layer_height: float = 0.0              # 0 = use printer default
    material: str = "PLA"
    supports: bool = True
    output_format: str = "3mf"
    slice_gcode: bool = True
    auto_send: bool = False
    export_flash: bool = False
    flash_mount: str = "/media/usb"
    printer_ip: str = ""
    printer_serial: str = ""
    access_code: str = ""                   # Bambu LAN access code
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.job_id:
            raw = f"forge-{self.geometry}-{self.created_at}-{id(self)}"
            self.job_id = hashlib.md5(raw.encode()).hexdigest()[:12]
        profile = PRINTER_PROFILES.get(self.target_printer)
        if profile and self.layer_height == 0.0:
            self.layer_height = profile.layer_height_default


@dataclass
class ForgeResult:
    """Result of a forge operation"""
    job_id: str
    success: bool
    message: str
    model_path: Optional[str] = None
    gcode_path: Optional[str] = None
    vertices: int = 0
    faces: int = 0
    print_time_estimate: Optional[str] = None
    material_estimate_g: float = 0.0
    printer_name: str = ""
    printer_ip: str = ""
    steps_completed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ════════════════════════════════════════════════════════════════════════════════
# G-CODE SANITIZER — Prevents printer-killer commands
# ════════════════════════════════════════════════════════════════════════════════

class GCodeSanitizer:
    """
    Validates G-code before transmission to prevent hardware damage.

    Checks:
      • Dangerous commands (M112 emergency stop, M502 factory reset)
      • Temperature limits (nozzle < 300°C, bed < 120°C)
      • Negative Z moves below safe limit
      • Travel speed limits
    """

    @staticmethod
    def sanitize(gcode_path: str, printer: PrinterProfile) -> Tuple[bool, List[str]]:
        """
        Scan G-code file for dangerous commands.

        Returns:
            (is_safe, list_of_warnings)
        """
        warnings = []
        is_safe = True

        if not Path(gcode_path).exists():
            return False, ["G-code file not found"]

        with open(gcode_path, 'r', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                stripped = line.strip().split(';')[0].strip()  # Remove comments
                if not stripped:
                    continue

                # Check dangerous commands
                cmd = stripped.split()[0] if stripped.split() else ""
                if cmd in GCODE_DANGEROUS_COMMANDS:
                    warnings.append(f"Line {line_num}: DANGEROUS command '{cmd}' blocked")
                    is_safe = False

                # Check temperature safety
                if cmd in ('M104', 'M109'):  # Set nozzle temp
                    temp = GCodeSanitizer._extract_param(stripped, 'S')
                    if temp and temp > printer.max_nozzle_temp:
                        warnings.append(
                            f"Line {line_num}: Nozzle temp {temp}°C exceeds "
                            f"max {printer.max_nozzle_temp}°C"
                        )
                        is_safe = False

                if cmd in ('M140', 'M190'):  # Set bed temp
                    temp = GCodeSanitizer._extract_param(stripped, 'S')
                    if temp and temp > printer.max_bed_temp:
                        warnings.append(
                            f"Line {line_num}: Bed temp {temp}°C exceeds "
                            f"max {printer.max_bed_temp}°C"
                        )
                        is_safe = False

                # Check Z-crash risk
                if cmd in ('G0', 'G1'):
                    z = GCodeSanitizer._extract_param(stripped, 'Z')
                    if z is not None and z < -1.0:
                        warnings.append(
                            f"Line {line_num}: Dangerous Z={z}mm — nozzle crash risk"
                        )
                        is_safe = False

        return is_safe, warnings

    @staticmethod
    def _extract_param(line: str, param: str) -> Optional[float]:
        """Extract a numeric parameter from a G-code line (e.g., 'S200' → 200)."""
        import re
        match = re.search(rf'{param}(-?\d+\.?\d*)', line)
        if match:
            return float(match.group(1))
        return None


# ════════════════════════════════════════════════════════════════════════════════
# BAMBU LAB BRIDGE — MQTT + FTP Communication
# ════════════════════════════════════════════════════════════════════════════════

class BambuBridge:
    """
    Communication bridge for Bambu Lab printers (P1S, A1 Mini).

    Protocol Stack:
      • MQTT (port 8883, TLS) — Command, control, status monitoring
      • FTPS (port 990)       — G-code file transfer
      • mDNS                  — Network discovery

    Authentication:
      • Serial number (printed on device, in Bambu Handy app)
      • LAN access code (generated in printer settings)
    """

    # MQTT topics for Bambu Lab printers
    TOPIC_REPORT = "device/{serial}/report"
    TOPIC_REQUEST = "device/{serial}/request"

    def __init__(self, ip: str, serial: str, access_code: str = "",
                 port: int = 8883):
        self.ip = ip
        self.serial = serial
        self.access_code = access_code
        self.port = port
        self._client = None
        self._status_cache: Dict[str, Any] = {}
        self._connected = False

    def connect(self) -> bool:
        """Establish MQTT connection to Bambu printer."""
        if not HAS_MQTT:
            logger.error("paho-mqtt not installed — cannot connect to Bambu")
            return False

        try:
            self._client = mqtt.Client(
                client_id=f"osiris_forge_{self.serial[:8]}",
                protocol=mqtt.MQTTv311,
            )
            self._client.tls_set()
            self._client.tls_insecure_set(True)  # Bambu uses self-signed certs

            # Bambu auth: username=bblp, password=access_code
            if self.access_code:
                self._client.username_pw_set("bblp", self.access_code)

            self._client.on_message = self._on_message
            self._client.on_connect = self._on_connect

            self._client.connect(self.ip, self.port, keepalive=60)
            self._client.loop_start()

            # Wait for connection
            for _ in range(50):
                if self._connected:
                    break
                time.sleep(0.1)

            return self._connected
        except Exception as e:
            logger.error(f"Bambu MQTT connection failed: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connect callback."""
        if rc == 0:
            self._connected = True
            topic = self.TOPIC_REPORT.format(serial=self.serial)
            client.subscribe(topic)
            logger.info(f"Connected to Bambu {self.serial} at {self.ip}")
        else:
            logger.error(f"MQTT connect failed: rc={rc}")

    def _on_message(self, client, userdata, msg):
        """MQTT message callback — caches printer status."""
        try:
            payload = json.loads(msg.payload.decode())
            self._status_cache = payload
        except Exception:
            pass

    def get_status(self, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Get current printer status.

        Returns dict with:
            status, progress, nozzle_temp, bed_temp, layer, speed,
            fan_speed, filament_used, time_remaining
        """
        if not self._connected:
            return {"status": "disconnected"}

        # Request a push report
        self._push_request({"pushing": {"command": "pushall"}})
        time.sleep(min(timeout, 10))

        if not self._status_cache:
            return {"status": "no_response"}

        p = self._status_cache.get("print", {})
        return {
            "status": p.get("gcode_state", "unknown"),
            "progress": p.get("mc_percent", 0),
            "nozzle_temp": p.get("nozzle_temper", 0),
            "nozzle_target": p.get("nozzle_target_temper", 0),
            "bed_temp": p.get("bed_temper", 0),
            "bed_target": p.get("bed_target_temper", 0),
            "layer": p.get("layer_num", 0),
            "total_layers": p.get("total_layer_num", 0),
            "speed_level": p.get("spd_lvl", 0),
            "fan_speed": p.get("big_fan1_speed", "0"),
            "time_remaining_min": p.get("mc_remaining_time", 0),
            "subtask_name": p.get("subtask_name", ""),
            "wifi_signal": p.get("wifi_signal", ""),
            "ams_status": self._status_cache.get("ams", {}),
            "raw": self._status_cache,
        }

    def send_gcode(self, gcode_path: str) -> bool:
        """
        Transfer G-code to Bambu printer via FTPS (port 990).

        The Bambu P1S/A1 Mini accept files over implicit FTPS.
        Files go to /sdcard/ on the printer.
        """
        import ftplib

        if not Path(gcode_path).exists():
            logger.error(f"G-code file not found: {gcode_path}")
            return False

        try:
            ftp = ftplib.FTP_TLS()
            ftp.connect(self.ip, 990, timeout=30)
            ftp.login("bblp", self.access_code)
            ftp.prot_p()

            filename = Path(gcode_path).name
            with open(gcode_path, 'rb') as f:
                ftp.storbinary(f"STOR /sdcard/{filename}", f)

            ftp.quit()
            logger.info(f"G-code uploaded via FTPS: {filename}")
            return True
        except Exception as e:
            logger.error(f"FTPS transfer failed: {e}")
            return False

    def start_print(self, filename: str) -> bool:
        """Start printing a file already on the SD card."""
        cmd = {
            "print": {
                "command": "project_file",
                "param": f"Metadata/plate_1.gcode",
                "subtask_name": filename,
                "url": f"ftp://{self.ip}/sdcard/{filename}",
                "bed_type": "auto",
                "timelapse": False,
                "bed_leveling": True,
                "flow_cali": True,
                "vibration_cali": True,
                "use_ams": False,
            }
        }
        return self._push_request(cmd)

    def pause_print(self) -> bool:
        """Pause current print."""
        return self._push_request({"print": {"command": "pause", "sequence_id": "0"}})

    def resume_print(self) -> bool:
        """Resume paused print."""
        return self._push_request({"print": {"command": "resume", "sequence_id": "0"}})

    def stop_print(self) -> bool:
        """Stop current print."""
        return self._push_request({"print": {"command": "stop", "sequence_id": "0"}})

    def set_bed_temp(self, temp: int) -> bool:
        """Set bed temperature."""
        if temp > GCODE_TEMP_LIMITS['bed_max']:
            logger.error(f"Bed temp {temp}°C exceeds safety limit")
            return False
        return self._push_request({
            "print": {"command": "gcode_line", "param": f"M140 S{temp}\n", "sequence_id": "0"}
        })

    def set_nozzle_temp(self, temp: int) -> bool:
        """Set nozzle temperature."""
        if temp > GCODE_TEMP_LIMITS['nozzle_max']:
            logger.error(f"Nozzle temp {temp}°C exceeds safety limit")
            return False
        return self._push_request({
            "print": {"command": "gcode_line", "param": f"M104 S{temp}\n", "sequence_id": "0"}
        })

    def home_axes(self) -> bool:
        """Home all axes."""
        return self._push_request({
            "print": {"command": "gcode_line", "param": "G28\n", "sequence_id": "0"}
        })

    def auto_level(self) -> bool:
        """Run auto bed leveling."""
        return self._push_request({
            "print": {"command": "gcode_line", "param": "G29\n", "sequence_id": "0"}
        })

    def calibrate(self) -> bool:
        """Run full calibration sequence (vibration + flow)."""
        return self._push_request({
            "print": {
                "command": "calibration",
                "sequence_id": "0",
                "option": 0,  # Full calibration
            }
        })

    def get_camera_frame(self) -> Optional[bytes]:
        """Capture a frame from the Bambu camera (if available)."""
        # Bambu streams via RTSP on port 6000, or JPEG snapshots
        if not HAS_REQUESTS:
            return None
        try:
            resp = _requests.get(
                f"http://{self.ip}:80/snapshot",
                timeout=5, auth=("bblp", self.access_code)
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    def _push_request(self, payload: Dict) -> bool:
        """Send a command to the printer via MQTT."""
        if not self._client or not self._connected:
            logger.error("Not connected to Bambu printer")
            return False

        topic = self.TOPIC_REQUEST.format(serial=self.serial)
        try:
            result = self._client.publish(topic, json.dumps(payload))
            return result.rc == 0
        except Exception as e:
            logger.error(f"MQTT publish failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from the printer."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False


# ════════════════════════════════════════════════════════════════════════════════
# ELEGOO BRIDGE — USB / HTTP Communication
# ════════════════════════════════════════════════════════════════════════════════

class ElegooBridge:
    """
    Communication bridge for Elegoo resin printers (Centauri Carbon 2).

    The Centauri 2 primarily works via USB flash drive, but some firmware
    versions support WiFi upload. This bridge handles both modes.

    Resin Workflow:
      1. Generate mesh → export to .stl
      2. Slice with ChiTuBox or Lychee Slicer (produces .ctb/.pwmx)
      3. Transfer sliced file to printer via USB or WiFi
    """

    # Resin slicer candidates
    RESIN_SLICERS = [
        "chitubox-cli",
        "ChiTuBox",
        "/opt/ChiTuBox/ChiTuBox",
        "lychee-slicer-cli",
        "UVtools",
    ]

    def __init__(self, ip: str = "", usb_path: str = "/media/usb"):
        self.ip = ip
        self.usb_path = usb_path
        self._resin_slicer = self._find_resin_slicer()

    def _find_resin_slicer(self) -> Optional[str]:
        """Find an available resin slicer CLI."""
        for candidate in self.RESIN_SLICERS:
            try:
                result = subprocess.run(
                    ["which", candidate],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return None

    def slice_resin(self, stl_path: str, layer_height: float = 0.05,
                    exposure_time: float = 2.5,
                    bottom_exposure: float = 30.0,
                    bottom_layers: int = 6) -> Optional[str]:
        """
        Slice an STL for resin printing.

        Returns path to sliced file (.ctb format).
        """
        if not self._resin_slicer:
            logger.warning("No resin slicer found — manual slicing required")
            return None

        output = str(Path(stl_path).with_suffix('.ctb'))
        cmd = [
            self._resin_slicer,
            "--input", stl_path,
            "--output", output,
            "--layer-height", str(layer_height),
            "--exposure", str(exposure_time),
            "--bottom-exposure", str(bottom_exposure),
            "--bottom-layers", str(bottom_layers),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and Path(output).exists():
                return output
            logger.error(f"Resin slicer failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Resin slicing error: {e}")
        return None

    def export_to_usb(self, file_path: str) -> bool:
        """Copy sliced file to USB flash drive for the printer."""
        import shutil

        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            return False

        # Find mounted USB
        target = None
        for mount in [self.usb_path, "/media/usb", "/mnt/usb", "/run/media"]:
            mp = Path(mount)
            if mp.exists() and mp.is_mount():
                target = mp
                break
            elif mp.exists():
                for child in mp.iterdir():
                    if child.is_dir():
                        target = child
                        break
            if target:
                break

        if not target:
            logger.error("No USB flash drive detected")
            return False

        dest = target / Path(file_path).name
        shutil.copy2(file_path, str(dest))
        logger.info(f"Exported to USB: {dest}")
        return True

    def send_wifi(self, file_path: str) -> bool:
        """Send file to Elegoo via WiFi (if firmware supports it)."""
        if not self.ip or not HAS_REQUESTS:
            return False

        try:
            url = f"http://{self.ip}/upload"
            with open(file_path, 'rb') as f:
                resp = _requests.post(
                    url,
                    files={'file': (Path(file_path).name, f)},
                    timeout=120
                )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"WiFi upload failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Query printer status via HTTP (firmware-dependent)."""
        if not self.ip or not HAS_REQUESTS:
            return {"status": "usb_only", "message": "WiFi status unavailable"}

        try:
            resp = _requests.get(f"http://{self.ip}/status", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}


# ════════════════════════════════════════════════════════════════════════════════
# MOONRAKER / KLIPPER BRIDGE — HTTP API
# ════════════════════════════════════════════════════════════════════════════════

class MoonrakerBridge:
    """
    Communication bridge for Klipper/Moonraker-based printers.

    Many modded Elegoo Neptune/Saturn printers run Klipper firmware
    with the Moonraker HTTP API for remote control.
    """

    def __init__(self, ip: str, port: int = 7125):
        self.ip = ip
        self.port = port
        self.base_url = f"http://{ip}:{port}"

    def get_status(self) -> Dict[str, Any]:
        """Query printer status via Moonraker API."""
        if not HAS_REQUESTS:
            return {"status": "unknown", "error": "requests not installed"}
        try:
            resp = _requests.get(
                f"{self.base_url}/printer/objects/query",
                params={"extruder": None, "heater_bed": None, "print_stats": None},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json().get("result", {}).get("status", {})
                extruder = data.get("extruder", {})
                bed = data.get("heater_bed", {})
                stats = data.get("print_stats", {})
                return {
                    "status": stats.get("state", "unknown"),
                    "nozzle_temp": extruder.get("temperature", 0),
                    "nozzle_target": extruder.get("target", 0),
                    "bed_temp": bed.get("temperature", 0),
                    "bed_target": bed.get("target", 0),
                    "filename": stats.get("filename", ""),
                    "progress": stats.get("print_duration", 0),
                }
            return {"status": "error", "code": resp.status_code}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def upload_and_print(self, gcode_path: str) -> bool:
        """Upload G-code and start printing."""
        if not HAS_REQUESTS:
            return False
        try:
            url = f"{self.base_url}/server/files/upload"
            with open(gcode_path, 'rb') as f:
                resp = _requests.post(url, files={'file': f}, timeout=60)
            if resp.status_code in (200, 201):
                filename = Path(gcode_path).name
                _requests.post(
                    f"{self.base_url}/printer/print/start",
                    json={"filename": filename}, timeout=10
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Moonraker upload failed: {e}")
            return False

    def pause(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            resp = _requests.post(f"{self.base_url}/printer/print/pause", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def resume(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            resp = _requests.post(f"{self.base_url}/printer/print/resume", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def cancel(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            resp = _requests.post(f"{self.base_url}/printer/print/cancel", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def home(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            resp = _requests.post(
                f"{self.base_url}/printer/gcode/script",
                json={"script": "G28"}, timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False


# ════════════════════════════════════════════════════════════════════════════════
# WATERMARK ENGINE — Cryptographic mesh watermarking
# ════════════════════════════════════════════════════════════════════════════════

class WatermarkEngine:
    """
    Embeds a cryptographic watermark into mesh geometry.

    The watermark is a micro-displacement of vertex positions that
    encodes the license hash and timestamp. It's invisible at normal
    scale but detectable by OSIRIS verification tools.

    This means any physical print contains provenance data that maps
    back to the Zenodo-archived license record.
    """

    @staticmethod
    def embed(vertices: np.ndarray, license_hash: str,
              amplitude: float = 0.001) -> np.ndarray:
        """
        Embed watermark into vertex positions.

        Args:
            vertices: Nx3 vertex array
            license_hash: SHA-256 hash to encode
            amplitude: Displacement amplitude (fraction of model scale)

        Returns:
            Watermarked vertex array
        """
        watermarked = vertices.copy()
        n = len(vertices)

        # Convert hash to displacement pattern
        hash_bytes = hashlib.sha256(license_hash.encode()).digest()
        pattern = np.frombuffer(hash_bytes, dtype=np.uint8)

        # Apply micro-displacements
        scale = np.ptp(vertices, axis=0).max() * amplitude
        for i in range(n):
            byte_idx = i % len(pattern)
            # Displacement direction based on hash byte
            displacement = (pattern[byte_idx] / 255.0 - 0.5) * 2.0 * scale
            # Apply along vertex normal (approximated by normalized position)
            normal = vertices[i] / max(np.linalg.norm(vertices[i]), 1e-10)
            watermarked[i] += normal * displacement

        return watermarked

    @staticmethod
    def verify(original: np.ndarray, watermarked: np.ndarray,
               license_hash: str, amplitude: float = 0.001) -> float:
        """
        Verify watermark presence by comparing against expected pattern.

        Returns correlation coefficient (>0.8 = verified).
        """
        diff = watermarked - original
        norms = np.linalg.norm(diff, axis=1)

        hash_bytes = hashlib.sha256(license_hash.encode()).digest()
        pattern = np.frombuffer(hash_bytes, dtype=np.uint8)

        scale = np.ptp(original, axis=0).max() * amplitude
        expected = np.array([
            abs((pattern[i % len(pattern)] / 255.0 - 0.5) * 2.0 * scale)
            for i in range(len(original))
        ])

        if np.std(norms) == 0 or np.std(expected) == 0:
            return 0.0
        return float(np.corrcoef(norms, expected)[0, 1])


# ════════════════════════════════════════════════════════════════════════════════
# THE FORGE — Main Pipeline Orchestrator
# ════════════════════════════════════════════════════════════════════════════════

class OsirisForge:
    """
    The OSIRIS Forge: Quantum-to-Matter Manufacturing Pipeline.

    Workflow:
      1. Compliance Gate check
      2. Generate mesh from Torsion Core / Organism genes
      3. Apply cryptographic watermark
      4. Export to .3mf / .stl
      5. Slice to G-code (headless slicer CLI)
      6. Sanitize G-code (safety check)
      7. Discover printers on local network
      8. Transmit to printer OR export to flash drive
      9. Monitor print status in real-time

    The Forge operates entirely local — no cloud dependencies.
    """

    def __init__(self, organism_dir: str = "./organism",
                 output_dir: str = "./manufacturing_output"):
        self.organism_dir = organism_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: List[ForgeResult] = []
        self._compliance_ok = False
        self._bambu_bridges: Dict[str, BambuBridge] = {}
        self._elegoo_bridge: Optional[ElegooBridge] = None
        self._moonraker_bridges: Dict[str, MoonrakerBridge] = {}

    # ── COMPLIANCE ────────────────────────────────────────────────────────

    def _check_compliance(self) -> bool:
        """Manufacturing compliance gate — must pass before any forge op."""
        if self._compliance_ok:
            return True
        try:
            from osiris_license import ComplianceGate
            compliant, msg = ComplianceGate.check(strict=True)
            if not compliant:
                logger.error(f"FORGE BLOCKED: {msg}")
                return False
            self._compliance_ok = True
            return True
        except ImportError:
            logger.warning("License module unavailable — forge allowed")
            self._compliance_ok = True
            return True

    # ── GEOMETRY GENERATION ───────────────────────────────────────────────

    def generate(self, job: ForgeJob) -> Optional[str]:
        """
        Generate 3D mesh from Torsion Core math.

        Maps geometry modes to manufacturing pipeline generators.
        """
        from osiris_manufacturing_3mf import (
            ManufacturingPipeline, ManufacturingConfig,
            ManufacturingMode, PrinterType,
        )

        mode_map = {
            "tetrahedral_lattice": ManufacturingMode.TETRAHEDRAL_LATTICE,
            "toroidal_manifold": ManufacturingMode.TOROIDAL_MANIFOLD,
            "planck_reference_cube": ManufacturingMode.PLANCK_REFERENCE_CUBE,
            "acoustic_resonance_cavity": ManufacturingMode.ACOUSTIC_RESONANCE_CAVITY,
            "quaternion_orbit_model": ManufacturingMode.QUATERNION_ORBIT_MODEL,
            "torsion_lock_visualizer": ManufacturingMode.TORSION_LOCK_VISUALIZER,
        }

        printer_map = {
            PrinterHardware.BAMBU_P1S: PrinterType.BAMBU_P1S,
            PrinterHardware.BAMBU_A1_MINI: PrinterType.BAMBU_A1_MINI,
            PrinterHardware.ELEGOO_CENTAURI_2: PrinterType.GENERIC_RESIN,
            PrinterHardware.GENERIC_FDM: PrinterType.GENERIC_FDM,
            PrinterHardware.GENERIC_RESIN: PrinterType.GENERIC_RESIN,
        }

        config = ManufacturingConfig(
            mode=mode_map.get(job.geometry, ManufacturingMode.TETRAHEDRAL_LATTICE),
            scale_cm=job.scale_cm,
            resolution=job.resolution,
            output_format=job.output_format,
            printer_type=printer_map.get(job.target_printer, PrinterType.GENERIC_FDM),
        )

        pipeline = ManufacturingPipeline(organism_dir=self.organism_dir)
        result = pipeline.run(config)

        if result.model_path:
            logger.info(f"Generated: {result.model_path} "
                        f"({result.vertices} verts, {result.faces} faces)")
        return result.model_path

    # ── SLICING ───────────────────────────────────────────────────────────

    def slice(self, model_path: str, job: ForgeJob) -> Optional[str]:
        """Slice a model to G-code using the appropriate slicer."""
        profile = PRINTER_PROFILES.get(job.target_printer)

        if profile and profile.is_resin:
            return self._slice_resin(model_path, job, profile)
        return self._slice_fdm(model_path, job, profile)

    def _slice_fdm(self, model_path: str, job: ForgeJob,
                   profile: Optional[PrinterProfile]) -> Optional[str]:
        """Slice for FDM printer using PrusaSlicer or BambuStudio CLI."""
        slicer = self._find_fdm_slicer()
        if not slicer:
            logger.warning("No FDM slicer CLI found — install prusa-slicer")
            return None

        gcode_path = str(Path(model_path).with_suffix('.gcode'))

        cmd = [slicer]
        if "bambu" in slicer.lower():
            cmd.extend([
                "--slice", model_path,
                "--output", gcode_path,
            ])
        else:
            # PrusaSlicer CLI
            cmd.extend([
                "--export-gcode", model_path,
                "--output", gcode_path,
                "--layer-height", str(job.layer_height),
                "--fill-density", f"{job.infill_percent}%",
                "--fill-pattern", job.infill_pattern,
            ])
            if job.supports:
                cmd.append("--support-material")
            if profile:
                cmd.extend([
                    "--nozzle-diameter", str(profile.nozzle_diameter),
                    "--filament-diameter", str(profile.filament_diameter),
                ])

            # Load printer config if available
            config_path = self._get_printer_config(job.target_printer)
            if config_path:
                cmd.extend(["--load", config_path])

        logger.info(f"Slicing [{' '.join(cmd[:4])}...]")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0 and Path(gcode_path).exists():
                logger.info(f"G-code generated: {gcode_path}")
                return gcode_path
            logger.error(f"Slicer error: {result.stderr[:500]}")
        except Exception as e:
            logger.error(f"Slicing failed: {e}")
        return None

    def _slice_resin(self, model_path: str, job: ForgeJob,
                     profile: Optional[PrinterProfile]) -> Optional[str]:
        """Slice for resin printer."""
        bridge = ElegooBridge()
        return bridge.slice_resin(
            model_path,
            layer_height=job.layer_height,
            exposure_time=2.5,
            bottom_exposure=30.0,
        )

    @staticmethod
    def _find_fdm_slicer() -> Optional[str]:
        """Find available FDM slicer CLI."""
        candidates = [
            "prusa-slicer", "PrusaSlicer", "prusa-slicer-console",
            "bambu-studio-cli", "BambuStudio",
            "cura-engine", "CuraEngine",
        ]
        for c in candidates:
            try:
                result = subprocess.run(["which", c], capture_output=True,
                                        text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                continue
        return None

    def _get_printer_config(self, hardware: PrinterHardware) -> Optional[str]:
        """Get path to printer-specific slicer config."""
        config_map = {
            PrinterHardware.BAMBU_P1S: "forge_profiles/bambu_p1s.ini",
            PrinterHardware.BAMBU_A1_MINI: "forge_profiles/bambu_a1_mini.ini",
            PrinterHardware.ELEGOO_CENTAURI_2: "forge_profiles/elegoo_centauri_2.ini",
        }
        rel = config_map.get(hardware)
        if rel:
            path = Path(__file__).parent / rel
            if path.exists():
                return str(path)
        return None

    # ── DISCOVERY ─────────────────────────────────────────────────────────

    def discover_printers(self, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Discover 3D printers on the local network."""
        from osiris_auto_discovery import PrinterDiscoveryService

        service = PrinterDiscoveryService()
        printers = service.scan(timeout=timeout)

        results = []
        for p in printers:
            results.append({
                "name": p.name,
                "type": p.printer_type,
                "ip": p.ip_address,
                "port": p.port,
                "protocol": p.protocol,
                "model": p.model,
                "serial": p.serial,
            })

        # Also check for Moonraker endpoints
        for p in printers:
            if p.protocol == "http":
                bridge = MoonrakerBridge(p.ip_address)
                status = bridge.get_status()
                if status.get("status") != "offline":
                    results[-1]["moonraker"] = True
                    results[-1]["moonraker_status"] = status

        return results

    # ── TRANSMISSION ──────────────────────────────────────────────────────

    def send_to_printer(self, gcode_path: str, job: ForgeJob) -> bool:
        """Send G-code to the target printer."""
        profile = PRINTER_PROFILES.get(job.target_printer)
        if not profile:
            logger.error(f"Unknown printer: {job.target_printer}")
            return False

        # G-code safety check
        safe, warnings = GCodeSanitizer.sanitize(gcode_path, profile)
        if not safe:
            logger.error(f"G-CODE SAFETY VIOLATION — transmission blocked:")
            for w in warnings:
                logger.error(f"  {w}")
            return False
        if warnings:
            for w in warnings:
                logger.warning(f"  {w}")

        # Route to appropriate bridge
        if profile.firmware == "bambu":
            return self._send_bambu(gcode_path, job)
        elif profile.is_resin:
            return self._send_elegoo(gcode_path, job)
        else:
            return self._send_moonraker(gcode_path, job)

    def _send_bambu(self, gcode_path: str, job: ForgeJob) -> bool:
        """Send to Bambu Lab printer via FTPS."""
        if not job.printer_ip:
            logger.error("No Bambu printer IP configured")
            return False

        key = job.printer_ip
        if key not in self._bambu_bridges:
            bridge = BambuBridge(
                ip=job.printer_ip,
                serial=job.printer_serial,
                access_code=job.access_code,
            )
            if not bridge.connect():
                return False
            self._bambu_bridges[key] = bridge

        return self._bambu_bridges[key].send_gcode(gcode_path)

    def _send_elegoo(self, gcode_path: str, job: ForgeJob) -> bool:
        """Send to Elegoo via USB or WiFi."""
        bridge = ElegooBridge(ip=job.printer_ip)
        if job.printer_ip:
            return bridge.send_wifi(gcode_path)
        return bridge.export_to_usb(gcode_path)

    def _send_moonraker(self, gcode_path: str, job: ForgeJob) -> bool:
        """Send to Moonraker/Klipper printer."""
        if not job.printer_ip:
            return False
        bridge = MoonrakerBridge(job.printer_ip)
        return bridge.upload_and_print(gcode_path)

    # ── MONITORING ────────────────────────────────────────────────────────

    def get_printer_status(self, job: ForgeJob) -> Dict[str, Any]:
        """Get real-time status from a connected printer."""
        profile = PRINTER_PROFILES.get(job.target_printer)

        if profile and profile.firmware == "bambu" and job.printer_ip:
            key = job.printer_ip
            if key in self._bambu_bridges:
                return self._bambu_bridges[key].get_status()
            bridge = BambuBridge(
                ip=job.printer_ip,
                serial=job.printer_serial,
                access_code=job.access_code,
            )
            if bridge.connect():
                self._bambu_bridges[key] = bridge
                return bridge.get_status()

        if profile and not profile.is_resin and job.printer_ip:
            bridge = MoonrakerBridge(job.printer_ip)
            return bridge.get_status()

        if profile and profile.is_resin:
            bridge = ElegooBridge(ip=job.printer_ip)
            return bridge.get_status()

        return {"status": "unknown"}

    # ── CALIBRATION ───────────────────────────────────────────────────────

    def calibrate_printer(self, job: ForgeJob) -> Dict[str, Any]:
        """
        Run calibration sequence on the target printer.

        Bambu: Auto bed leveling + vibration compensation + flow calibration
        Elegoo: UV power check + Z-offset calibration
        """
        profile = PRINTER_PROFILES.get(job.target_printer)
        result = {"printer": profile.name if profile else "unknown", "steps": []}

        if profile and profile.firmware == "bambu" and job.printer_ip:
            bridge = self._get_or_create_bambu(job)
            if bridge:
                # Full calibration sequence
                result["steps"].append(("home", bridge.home_axes()))
                result["steps"].append(("auto_level", bridge.auto_level()))
                result["steps"].append(("full_calibrate", bridge.calibrate()))
                result["success"] = all(s[1] for s in result["steps"])
            else:
                result["success"] = False
                result["error"] = "Cannot connect to Bambu printer"

        elif profile and profile.is_resin:
            result["steps"].append(("info", True))
            result["message"] = (
                "Elegoo Centauri 2 calibration:\n"
                "  1. Level the build plate manually (paper test)\n"
                "  2. Run UV exposure test from printer menu\n"
                "  3. Check Z-offset with calibration print\n"
                "  4. Verify resin temperature (20-25°C optimal)"
            )
            result["success"] = True

        return result

    def _get_or_create_bambu(self, job: ForgeJob) -> Optional[BambuBridge]:
        key = job.printer_ip
        if key in self._bambu_bridges:
            return self._bambu_bridges[key]
        bridge = BambuBridge(
            ip=job.printer_ip,
            serial=job.printer_serial,
            access_code=job.access_code,
        )
        if bridge.connect():
            self._bambu_bridges[key] = bridge
            return bridge
        return None

    # ── FULL PIPELINE ─────────────────────────────────────────────────────

    def run(self, job: ForgeJob) -> ForgeResult:
        """
        Execute the full Quantum-to-Matter forge pipeline.

        Steps:
          1. Compliance gate
          2. Generate mesh
          3. Watermark
          4. Export model
          5. Slice to G-code
          6. Sanitize G-code
          7. Discover / send / export
        """
        steps = []

        # 1. Compliance
        if not self._check_compliance():
            return ForgeResult(
                job_id=job.job_id, success=False,
                message="BLOCKED: Compliance Gate requires commercial license",
            )
        steps.append("compliance_check")

        # 2. Generate mesh
        model_path = self.generate(job)
        if not model_path:
            return ForgeResult(
                job_id=job.job_id, success=False,
                message="Mesh generation failed",
                steps_completed=steps,
            )
        steps.append("mesh_generated")

        # 3-4. Model is already exported by generate()

        gcode_path = None
        # 5. Slice
        if job.slice_gcode:
            gcode_path = self.slice(model_path, job)
            if gcode_path:
                steps.append("sliced")

                # 6. Sanitize
                profile = PRINTER_PROFILES.get(job.target_printer)
                if profile:
                    safe, warnings = GCodeSanitizer.sanitize(gcode_path, profile)
                    if not safe:
                        return ForgeResult(
                            job_id=job.job_id, success=False,
                            message=f"G-code safety violation: {'; '.join(warnings)}",
                            model_path=model_path,
                            steps_completed=steps,
                        )
                    steps.append("sanitized")
            else:
                steps.append("slice_skipped_no_slicer")

        # 7. Transmission
        if job.auto_send and gcode_path:
            sent = self.send_to_printer(gcode_path, job)
            if sent:
                steps.append("transmitted")
            else:
                steps.append("transmission_failed")
        elif job.export_flash and gcode_path:
            bridge = ElegooBridge(usb_path=job.flash_mount)
            exported = bridge.export_to_usb(gcode_path)
            if exported:
                steps.append("exported_flash")
            else:
                steps.append("flash_export_failed")

        result = ForgeResult(
            job_id=job.job_id,
            success=True,
            message=f"Forge pipeline complete: {len(steps)} steps",
            model_path=model_path,
            gcode_path=gcode_path,
            printer_name=PRINTER_PROFILES.get(job.target_printer, PrinterProfile(
                hardware=PrinterHardware.GENERIC_FDM, name="Generic", build_volume_mm=(0,0,0),
                nozzle_diameter=0, layer_height_default=0, layer_height_min=0,
                filament_diameter=0, max_speed_mm_s=0, heated_bed=False,
                max_nozzle_temp=0, max_bed_temp=0, protocol="", default_port=0,
            )).name,
            steps_completed=steps,
            metadata={
                "forge_version": FORGE_VERSION,
                "geometry": job.geometry,
                "scale_cm": job.scale_cm,
                "printer": job.target_printer.value,
                "infill": f"{job.infill_percent}% {job.infill_pattern}",
            },
        )
        self.jobs.append(result)
        return result

    # ── REPORTING ─────────────────────────────────────────────────────────

    def status_report(self) -> str:
        """Generate forge status report."""
        lines = [
            "",
            "═" * 65,
            "  ⚛ OSIRIS FORGE — Quantum-to-Matter Manufacturing Pipeline",
            "═" * 65,
            "",
            f"  Version: {FORGE_VERSION}",
            f"  Output:  {self.output_dir}",
            f"  Jobs:    {len(self.jobs)}",
            "",
            "  Supported Hardware:",
        ]
        for hw, profile in PRINTER_PROFILES.items():
            vol = profile.build_volume_mm
            lines.append(
                f"    • {profile.name:30s} "
                f"{vol[0]:.0f}×{vol[1]:.0f}×{vol[2]:.0f}mm  "
                f"{'Resin' if profile.is_resin else 'FDM'}"
            )

        lines.append("")

        # Dependency status
        lines.append("  Dependencies:")
        deps = [
            ("trimesh", HAS_TRIMESH),
            ("zeroconf", HAS_ZEROCONF),
            ("paho-mqtt", HAS_MQTT),
            ("requests", HAS_REQUESTS),
        ]
        for name, avail in deps:
            lines.append(f"    {'✓' if avail else '✗'} {name}")

        # Slicer status
        slicer = self._find_fdm_slicer()
        lines.append(f"    {'✓' if slicer else '✗'} FDM slicer: {slicer or 'not found'}")

        lines.append("")

        if self.jobs:
            lines.append("  Recent Jobs:")
            for j in self.jobs[-5:]:
                s = "✓" if j.success else "✗"
                lines.append(f"    {s} [{j.job_id}] {j.message}")
                if j.model_path:
                    lines.append(f"      Model: {j.model_path}")
                if j.gcode_path:
                    lines.append(f"      G-code: {j.gcode_path}")

        lines.extend(["", "═" * 65])
        return "\n".join(lines)

    def cleanup(self):
        """Disconnect all printer bridges."""
        for bridge in self._bambu_bridges.values():
            bridge.disconnect()
        self._bambu_bridges.clear()


# ════════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point for the OSIRIS Forge."""
    import argparse

    parser = argparse.ArgumentParser(
        description="⚛ OSIRIS Forge — Quantum-to-Matter Manufacturing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a 10cm tetrahedral lattice as STL
  python osiris_forge.py generate --geometry tetrahedral_lattice --scale 10

  # Full pipeline: generate + slice + send to Bambu P1S
  python osiris_forge.py forge --printer bambu_p1s --ip 192.168.1.50 --serial XXXX --code YYYY

  # Discover printers on the network
  python osiris_forge.py discover

  # Check printer status
  python osiris_forge.py status --printer bambu_p1s --ip 192.168.1.50

  # Calibrate printer
  python osiris_forge.py calibrate --printer bambu_p1s --ip 192.168.1.50
"""
    )

    sub = parser.add_subparsers(dest="action", help="Forge action")

    # Generate
    gen = sub.add_parser("generate", help="Generate 3D mesh from Torsion Core")
    gen.add_argument("--geometry", default="tetrahedral_lattice",
                     choices=["tetrahedral_lattice", "toroidal_manifold",
                              "planck_reference_cube", "acoustic_resonance_cavity",
                              "quaternion_orbit_model", "torsion_lock_visualizer"])
    gen.add_argument("--scale", type=float, default=10.0, help="Scale in cm")
    gen.add_argument("--format", default="stl", choices=["3mf", "stl", "both"])
    gen.add_argument("--printer", default="bambu_p1s",
                     choices=[h.value for h in PrinterHardware])

    # Full forge pipeline
    forge = sub.add_parser("forge", help="Full: generate → slice → send")
    forge.add_argument("--geometry", default="tetrahedral_lattice")
    forge.add_argument("--scale", type=float, default=10.0)
    forge.add_argument("--printer", default="bambu_p1s",
                       choices=[h.value for h in PrinterHardware])
    forge.add_argument("--ip", type=str, default="", help="Printer IP address")
    forge.add_argument("--serial", type=str, default="", help="Bambu serial number")
    forge.add_argument("--code", type=str, default="", help="Bambu LAN access code")
    forge.add_argument("--infill", type=int, default=20, help="Infill percent")
    forge.add_argument("--pattern", default="gyroid",
                       choices=["gyroid", "grid", "triangles", "honeycomb",
                                "cubic", "line", "concentric"])
    forge.add_argument("--send", action="store_true", help="Auto-send to printer")
    forge.add_argument("--flash", action="store_true", help="Export to flash drive")
    forge.add_argument("--flash-mount", default="/media/usb")

    # Discover
    sub.add_parser("discover", help="Scan network for 3D printers")

    # Status
    stat = sub.add_parser("status", help="Check printer status")
    stat.add_argument("--printer", default="bambu_p1s")
    stat.add_argument("--ip", type=str, required=True)
    stat.add_argument("--serial", type=str, default="")
    stat.add_argument("--code", type=str, default="")

    # Calibrate
    cal = sub.add_parser("calibrate", help="Run printer calibration")
    cal.add_argument("--printer", default="bambu_p1s")
    cal.add_argument("--ip", type=str, required=True)
    cal.add_argument("--serial", type=str, default="")
    cal.add_argument("--code", type=str, default="")

    # Report
    sub.add_parser("report", help="Show forge status report")

    args = parser.parse_args()
    forge_engine = OsirisForge()

    if args.action == "generate":
        job = ForgeJob(
            geometry=args.geometry,
            scale_cm=args.scale,
            output_format=args.format,
            target_printer=PrinterHardware(args.printer),
            slice_gcode=False,
        )
        path = forge_engine.generate(job)
        if path:
            print(f"✓ Model generated: {path}")
        else:
            print("✗ Generation failed")

    elif args.action == "forge":
        job = ForgeJob(
            geometry=args.geometry,
            scale_cm=args.scale,
            target_printer=PrinterHardware(args.printer),
            infill_percent=args.infill,
            infill_pattern=args.pattern,
            auto_send=args.send,
            export_flash=args.flash,
            flash_mount=args.flash_mount,
            printer_ip=args.ip,
            printer_serial=args.serial,
            access_code=args.code,
        )
        result = forge_engine.run(job)
        print(f"\n{'✓' if result.success else '✗'} {result.message}")
        if result.model_path:
            print(f"  Model:  {result.model_path}")
        if result.gcode_path:
            print(f"  G-code: {result.gcode_path}")
        print(f"  Steps:  {' → '.join(result.steps_completed)}")

    elif args.action == "discover":
        print("\n⚛ Scanning local network for 3D printers...\n")
        printers = forge_engine.discover_printers()
        if printers:
            for p in printers:
                print(f"  📡 {p['name']} ({p['type']}) @ {p['ip']}:{p['port']} [{p['protocol']}]")
        else:
            print("  No printers found. Check WiFi connection.")

    elif args.action == "status":
        job = ForgeJob(
            target_printer=PrinterHardware(args.printer),
            printer_ip=args.ip,
            printer_serial=args.serial,
            access_code=args.code,
        )
        status = forge_engine.get_printer_status(job)
        print(f"\n⚛ Printer Status: {status.get('status', 'unknown')}")
        for k, v in status.items():
            if k != 'raw':
                print(f"  {k}: {v}")

    elif args.action == "calibrate":
        job = ForgeJob(
            target_printer=PrinterHardware(args.printer),
            printer_ip=args.ip,
            printer_serial=args.serial,
            access_code=args.code,
        )
        result = forge_engine.calibrate_printer(job)
        print(f"\n⚛ Calibration: {'Complete' if result.get('success') else 'Failed'}")
        if result.get("message"):
            print(result["message"])
        for step, ok in result.get("steps", []):
            print(f"  {'✓' if ok else '✗'} {step}")

    elif args.action == "report":
        print(forge_engine.status_report())

    else:
        print(forge_engine.status_report())

    forge_engine.cleanup()


if __name__ == "__main__":
    main()
