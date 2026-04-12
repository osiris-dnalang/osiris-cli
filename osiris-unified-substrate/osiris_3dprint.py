#!/usr/bin/env python3
"""
OSIRIS 3D Printing Module - Printables.com to Elegoo Centauri Carbon 2 Workflow
"""

import os
import re
import json
import asyncio
import logging
import requests
import tempfile
import shutil
import zipfile
import pathlib
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("osiris_3dprint")

class PrintablesDownloader:
    """Handles downloading models and G-code files from Printables.com"""

    BASE_URL = "localhost/PURIFIED"
    API_URL = "localhost/PURIFIED"

    def __init__(self, cache_dir: str = None, headers: Dict = None):
        self.session = requests.Session()
        self.cache_dir = Path(cache_dir or tempfile.gettempdir()) / "osiris_printables_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Default headers to mimic a browser
        self.session.headers.update(headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.1/PURIFIED Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def _get_cached_path(self, url: str) -> Path:
        """Generate a cached file path for a given URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.cache"

    def _load_from_cache(self, url: str) -> Optional[bytes]:
        """Try to load content from cache"""
        cached_path = self._get_cached_path(url)
        if cached_path.exists():
            try:
                with open(cached_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to read cache for {url}: {e}")
        return None

    def _save_to_cache(self, url: str, content: bytes) -> None:
        """Save content to cache"""
        try:
            cached_path = self._get_cached_path(url)
            with open(cached_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Failed to cache {url}: {e}")

    def get_model_page(self, model_url: str) -> BeautifulSoup:
        """Fetch and parse a Printables model page"""
        # Try cache first
        cached = self._load_from_cache(model_url)
        if cached:
            logger.info(f"Loading {model_url} from cache")
            return BeautifulSoup(cached, "html.parser")

        # Fetch fresh content
        logger.info(f"Fetching {model_url}")
        try:
            response = self.session.get(model_url)
            response.raise_for_status()

            # Save to cache
            self._save_to_cache(model_url, response.content)

            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to fetch {model_url}: {e}")
            raise

    def get_download_links(self, model_url: str) -> List[Dict]:
        """Extract download links from a Printables model page"""
        soup = self.get_model_page(model_url)
        download_links = []

        # Find download buttons
        for button in soup.select('a[data-testid="download-button"]'):
            href = button.get("href")
            if not href:
                continue

            # Get file info from button attributes
            file_info = {
                "url": href if href.startswith("http") else f"{self.BASE_URL}{href}",
                "name": button.text.strip(),
                "type": "unknown"
            }

            # Try to get file type from nearby elements
            parent = button.find_parent(class_="download-button-container")
            if parent:
                type_element = parent.find_previous_sibling(class_="file-type")
                if type_element:
                    file_info["type"] = type_element.text.strip().lower()

            download_links.append(file_info)

        # Also check for direct download links in script tags
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string
            if not script_text:
                continue

            # Look for download URLs in script data
            if "downloadUrl" in script_text:
                try:
                    # Try to extract JSON data
                    start = script_text.find("{")
                    end = script_text.rfind("}") + 1
                    if start > 0 and end > start:
                        data = json.loads(script_text[start:end])
                        if isinstance(data, dict) and "downloadUrl" in data:
                            download_links.append({
                                "url": data["downloadUrl"],
                                "name": data.get("name", "unknown_file"),
                                "type": data.get("type", "unknown")
                            })
                except json.JSONDecodeError:
                    continue

        return download_links

    def download_file(self, url: str, output_dir: str = None) -> Path:
        """Download a file from Printables"""
        output_dir = Path(output_dir or tempfile.gettempdir())
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try cache first
        cached = self._load_from_cache(url)
        if cached:
            output_path = output_dir / Path(urlparse(url).path).name
            with open(output_path, "wb") as f:
                f.write(cached)
            logger.info(f"Loaded {url} from cache to {output_path}")
            return output_path

        # Download fresh
        logger.info(f"Downloading {url}")
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()

            # Save to cache
            self._save_to_cache(url, response.content)

            # Save to output
            output_path = output_dir / Path(urlparse(url).path).name
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded {url} to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            raise

    def get_model_files(self, model_url: str, output_dir: str = None) -> List[Path]:
        """Get all downloadable files for a model"""
        output_dir = Path(output_dir or tempfile.gettempdir()) / "printables_downloads"
        output_dir.mkdir(parents=True, exist_ok=True)

        download_links = self.get_download_links(model_url)
        downloaded_files = []

        for link in download_links:
            try:
                file_path = self.download_file(link["url"], output_dir)
                downloaded_files.append(file_path)
                logger.info(f"Downloaded {link['name']} ({link['type']}) to {file_path}")
            except Exception as e:
                logger.error(f"Failed to download {link['name']}: {e}")

        return downloaded_files

class GCodeProcessor:
    """Processes G-code files for specific printers"""

    PRINTER_PROFILES = {
        "centauri_carbon2": {
            "model": "Centauri Carbon 2",
            "bed_size": {"x": 210, "y": 210, "z": 250},
            "nozzle_size": 0.4,
            "filament_diameter": 1.75,
            "firmware": "Marlin",
            "start_gcode": [
                "G28 ; Home all axes",
                "M104 S200 ; Start heating extruder",
                "M140 S60 ; Start heating bed",
                "M190 S60 ; Wait for bed to reach temp",
                "M109 S200 ; Wait for extruder to reach temp",
                "G92 E0 ; Reset extruder",
                "G1 Z2.0 F3000 ; Move Z axis up",
                "G1 X10.1 Y20 Z0.28 F5000.0 ; Move to start position",
                "G1 X10.1 Y200.0 Z0.28 F1500.0 E15 ; Draw first line",
                "G1 X10.4 Y200.0 Z0.28 F5000.0 ; Move to side",
                "G1 X10.4 Y20 Z0.28 F1500.0 E30 ; Draw second line",
                "G92 E0 ; Reset extruder",
                "G1 Z2.0 F3000 ; Move Z axis up"
            ],
            "end_gcode": [
                "M104 S0 ; Turn off extruder",
                "M140 S0 ; Turn off bed",
                "G91 ; Relative positioning",
                "G1 E-1 F300 ; Retract filament",
                "G1 Z+5 E-5 X-20 Y-20 F9000 ; Wipe & retract",
                "G90 ; Absolute positioning",
                "G1 X0 Y210 ; Park print head",
                "M84 ; Disable steppers"
            ]
        }
    }

    def __init__(self, printer_profile: str = "centauri_carbon2"):
        self.printer_profile = self.PRINTER_PROFILES.get(printer_profile)
        if not self.printer_profile:
            raise ValueError(f"Unknown printer profile: {printer_profile}")

    def process_gcode(self, input_path: Path, output_path: Path = None) -> Path:
        """Process G-code file for the selected printer"""
        if not output_path:
            output_path = input_path.parent / f"processed_{input_path.name}"

        logger.info(f"Processing {input_path} for {self.printer_profile['model']}")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            processed_lines = []

            # Add printer model header if not present
            has_printer_model = False
            for line in lines:
                if line.strip().startswith("; printer_model:"):
                    has_printer_model = True
                    # Replace existing printer model line
                    processed_lines.append(f"; printer_model: {self.printer_profile['model']}\n")
                elif line.strip().startswith("; generated by"):
                    processed_lines.append(line)
                    if not has_printer_model:
                        processed_lines.append(f"; printer_model: {self.printer_profile['model']}\n")
                else:
                    processed_lines.append(line)

            # If no printer model line was found, add one at the beginning
            if not has_printer_model:
                processed_lines.insert(0, f"; printer_model: {self.printer_profile['model']}\n")

            # Add start gcode if not present
            has_start_gcode = any(line.strip().startswith("; START_GCODE") for line in processed_lines)
            if not has_start_gcode and self.printer_profile["start_gcode"]:
                processed_lines.insert(1, "; START_GCODE\n")
                processed_lines[2:2] = [f"; {line}\n" for line in self.printer_profile["start_gcode"]]
                processed_lines.insert(2 + len(self.printer_profile["start_gcode"]), "; END_START_GCODE\n")

            # Add end gcode if not present
            has_end_gcode = any(line.strip().startswith("; END_GCODE") for line in processed_lines)
            if not has_end_gcode and self.printer_profile["end_gcode"]:
                processed_lines.append("\n; END_GCODE\n")
                processed_lines.extend([f"; {line}\n" for line in self.printer_profile["end_gcode"]])

            # Write processed file
            with open(output_path, "w", encoding="utf-8") as f:
                f.writelines(processed_lines)

            logger.info(f"Processed G-code saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to process {input_path}: {e}")
            raise

    def batch_process_gcode(self, input_dir: Path, output_dir: Path = None) -> List[Path]:
        """Process all G-code files in a directory"""
        if not output_dir:
            output_dir = input_dir / "processed"
        output_dir.mkdir(parents=True, exist_ok=True)

        processed_files = []
        for gcode_file in input_dir.glob("*.gcode"):
            try:
                output_path = output_dir / f"processed_{gcode_file.name}"
                processed = self.process_gcode(gcode_file, output_path)
                processed_files.append(processed)
            except Exception as e:
                logger.error(f"Failed to process {gcode_file}: {e}")

        return processed_files

    def validate_gcode(self, gcode_path: Path) -> Dict:
        """Validate G-code file for the selected printer"""
        logger.info(f"Validating {gcode_path} for {self.printer_profile['model']}")

        validation_results = {
            "file": str(gcode_path),
            "printer": self.printer_profile["model"],
            "warnings": [],
            "errors": [],
            "stats": {
                "lines": 0,
                "commands": {},
                "print_time": None,
                "filament_used": None,
                "layer_count": 0
            }
        }

        try:
            with open(gcode_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            validation_results["stats"]["lines"] = len(lines)

            # Check for printer model
            has_printer_model = False
            for line in lines:
                if line.strip().startswith("; printer_model:"):
                    if self.printer_profile["model"].lower() in line.lower():
                        has_printer_model = True
                    else:
                        validation_results["warnings"].append(
                            f"Printer model mismatch: {line.strip()} vs {self.printer_profile['model']}"
                        )

            if not has_printer_model:
                validation_results["warnings"].append(
                    f"No printer model specified in G-code file"
                )

            # Check for bed size violations
            current_x = current_y = current_z = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue

                # Parse G-code commands
                if line.startswith("G0") or line.startswith("G1"):
                    parts = line.split()
                    params = {}
                    for part in parts[1:]:
                        if ";" in part:
                            part = part.split(";")[0]
                        if part and part[0] in "XYZEF":
                            try:
                                params[part[0]] = float(part[1:])
                            except ValueError:
                                pass

                    if "X" in params:
                        current_x = params["X"]
                        if abs(current_x) > self.printer_profile["bed_size"]["x"]:
                            validation_results["errors"].append(
                                f"X position {current_x} exceeds bed size {self.printer_profile['bed_size']['x']}"
                            )

                    if "Y" in params:
                        current_y = params["Y"]
                        if abs(current_y) > self.printer_profile["bed_size"]["y"]:
                            validation_results["errors"].append(
                                f"Y position {current_y} exceeds bed size {self.printer_profile['bed_size']['y']}"
                            )

                    if "Z" in params:
                        current_z = params["Z"]
                        if current_z > self.printer_profile["bed_size"]["z"]:
                            validation_results["errors"].append(
                                f"Z position {current_z} exceeds max height {self.printer_profile['bed_size']['z']}"
                            )

                # Count commands
                if line and not line.startswith(";"):
                    cmd = line.split()[0] if line.split() else ""
                    validation_results["stats"]["commands"][cmd] = validation_results["stats"]["commands"].get(cmd, 0) + 1

                # Extract print stats if available
                if line.startswith("; estimated printing time"):
                    time_match = re.search(r"(\d+h)?\s*(\d+m)?\s*(\d+s)?", line)
                    if time_match:
                        hours = int(time_match.group(1)[:-1]) if time_match.group(1) else 0
                        minutes = int(time_match.group(2)[:-1]) if time_match.group(2) else 0
                        seconds = int(time_match.group(3)[:-1]) if time_match.group(3) else 0
                        validation_results["stats"]["print_time"] = f"{hours}h{minutes}m{seconds}s"

                if line.startswith("; filament used"):
                    filament_match = re.search(r"(\d+\.?\d*)(mm|cm|m)", line)
                    if filament_match:
                        value = float(filament_match.group(1))
                        unit = filament_match.group(2)
                        if unit == "cm":
                            value *= 10
                        elif unit == "m":
                            value *= 1000
                        validation_results["stats"]["filament_used"] = f"{value:.1f}mm"

                if line.startswith("; layer:"):
                    validation_results["stats"]["layer_count"] += 1

            return validation_results

        except Exception as e:
            logger.error(f"Validation failed for {gcode_path}: {e}")
            validation_results["errors"].append(f"Validation failed: {str(e)}")
            return validation_results

class PrintablesCentauriWorkflow:
    """Complete workflow for downloading from Printables and preparing for Centauri Carbon 2"""

    def __init__(self, cache_dir: str = None):
        self.downloader = PrintablesDownloader(cache_dir=cache_dir)
        self.gcode_processor = GCodeProcessor(printer_profile="centauri_carbon2")
        self.work_dir = Path(tempfile.gettempdir()) / "osiris_3dprint_workflow"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def parse_printables_url(self, url: str) -> Dict:
        """Parse a Printables.com URL to extract model ID and other info"""
        parsed = urlparse(url)
        if "printables.com" not in parsed.netloc:
            raise ValueError("URL is not from printables.com")

        path_parts = parsed.path.strip("/").split("/")
        result = {
            "original_url": url,
            "model_id": None,
            "model_slug": None,
            "is_model_page": False,
            "is_file_download": False,
            "file_id": None
        }

        # Model page URL: localhost/PURIFIED
        if len(path_parts) >= 3 and path_parts[0] == "model":
            result["is_model_page"] = True
            result["model_id"] = path_parts[1]
            result["model_slug"] = "-".join(path_parts[2:])
            return result

        # File download URL: localhost/PURIFIED
        if len(path_parts) >= 5 and path_parts[0] == "model" and path_parts[3] == "files":
            result["is_model_page"] = True
            result["is_file_download"] = True
            result["model_id"] = path_parts[1]
            result["model_slug"] = "-".join(path_parts[2:3])
            result["file_id"] = path_parts[4]
            return result

        raise ValueError("Could not parse Printables URL")

    def download_model(self, model_url: str, output_dir: str = None) -> List[Path]:
        """Download a model from Printables"""
        output_dir = Path(output_dir or self.work_dir / "downloads")
        output_dir.mkdir(parents=True, exist_ok=True)

        parsed = self.parse_printables_url(model_url)
        logger.info(f"Downloading model {parsed['model_id']}: {parsed['model_slug']}")

        if parsed["is_file_download"]:
            # Direct file download
            file_path = self.downloader.download_file(model_url, output_dir)
            return [file_path]
        else:
            # Model page - get all files
            return self.downloader.get_model_files(model_url, output_dir)

    def process_for_centauri(self, input_files: List[Path], output_dir: str = None) -> List[Path]:
        """Process downloaded files for Centauri Carbon 2"""
        output_dir = Path(output_dir or self.work_dir / "processed")
        output_dir.mkdir(parents=True, exist_ok=True)

        processed_files = []
        for input_file in input_files:
            if input_file.suffix.lower() == ".gcode":
                output_path = output_dir / f"centauri_{input_file.name}"
                processed = self.gcode_processor.process_gcode(input_file, output_path)
                processed_files.append(processed)
            else:
                # Copy non-gcode files as-is
                output_path = output_dir / input_file.name
                shutil.copy2(input_file, output_path)
                processed_files.append(output_path)

        return processed_files

    def validate_files(self, input_files: List[Path]) -> List[Dict]:
        """Validate processed files for Centauri Carbon 2"""
        validation_results = []
        for input_file in input_files:
            if input_file.suffix.lower() == ".gcode":
                result = self.gcode_processor.validate_gcode(input_file)
                validation_results.append(result)

        return validation_results

    def full_workflow(self, model_url: str, output_dir: str = None) -> Dict:
        """Complete workflow from Printables URL to Centauri-ready G-code"""
        output_dir = Path(output_dir or self.work_dir / "complete")
        output_dir.mkdir(parents=True, exist_ok=True)

        workflow_dir = output_dir / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "status": "started",
            "model_url": model_url,
            "workflow_dir": str(workflow_dir),
            "steps": [],
            "files": {
                "downloaded": [],
                "processed": [],
                "validation": []
            },
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Step 1: Parse URL
            parsed = self.parse_printables_url(model_url)
            result["parsed_url"] = parsed
            result["steps"].append({
                "step": 1,
                "action": "url_parsing",
                "status": "success",
                "details": parsed,
                "timestamp": datetime.now().isoformat()
            })

            # Step 2: Download
            logger.info("Step 2/4: Downloading model files")
            downloaded_files = self.download_model(model_url, workflow_dir / "downloaded")
            result["files"]["downloaded"] = [str(f.relative_to(workflow_dir)) for f in downloaded_files]
            result["steps"].append({
                "step": 2,
                "action": "download",
                "status": "success",
                "files_downloaded": len(downloaded_files),
                "file_list": [f.name for f in downloaded_files],
                "timestamp": datetime.now().isoformat()
            })

            if not downloaded_files:
                raise ValueError("No files were downloaded")

            # Step 3: Process for Centauri
            logger.info("Step 3/4: Processing files for Centauri Carbon 2")
            processed_files = self.process_for_centauri(downloaded_files, workflow_dir / "processed")
            result["files"]["processed"] = [str(f.relative_to(workflow_dir)) for f in processed_files]
            result["steps"].append({
                "step": 3,
                "action": "processing",
                "status": "success",
                "files_processed": len(processed_files),
                "file_list": [f.name for f in processed_files],
                "timestamp": datetime.now().isoformat()
            })

            # Step 4: Validate
            logger.info("Step 4/4: Validating processed files")
            validation_results = self.validate_files(processed_files)
            result["files"]["validation"] = validation_results
            result["steps"].append({
                "step": 4,
                "action": "validation",
                "status": "success",
                "validation_results": {
                    "total_files": len(validation_results),
                    "errors_found": sum(len(v["errors"]) for v in validation_results),
                    "warnings_found": sum(len(v["warnings"]) for v in validation_results)
                },
                "timestamp": datetime.now().isoformat()
            })

            # Check for errors
            total_errors = sum(len(v["errors"]) for v in validation_results)
            if total_errors > 0:
                result["status"] = "completed_with_errors"
                logger.warning(f"Completed with {total_errors} errors in validation")
            else:
                result["status"] = "completed_successfully"
                logger.info("Workflow completed successfully")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["steps"].append({
                "step": len(result["steps"]) + 1,
                "action": "error",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            logger.error(f"Workflow failed: {e}")

        # Save workflow manifest
        manifest_path = workflow_dir / "workflow_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(result, f, indent=2)

        return result

def main():
    """Command-line interface for the Printables to Centauri workflow"""
    import argparse

    parser = argparse.ArgumentParser(
        description="OSIRIS 3D Printing Workflow: Download from Printables.com and prepare for Elegoo Centauri Carbon 2",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "url",
        help="Printables.com model URL (e.g., localhost/PURIFIED)
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory for processed files",
        default=str(Path.home() / "Downloads" / "centauri_gcode")
    )
    parser.add_argument(
        "--cache",
        help="Directory for caching downloads",
        default=str(Path.home() / ".osiris_3dprint_cache")
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing G-code files (don't download or process)"
    )
    parser.add_argument(
        "--process-only",
        action="store_true",
        help="Only process existing downloaded files (don't download)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        workflow = PrintablesCentauriWorkflow(cache_dir=args.cache)

        if args.validate_only:
            # Validate existing files in output directory
            output_dir = Path(args.output)
            if not output_dir.exists():
                logger.error(f"Output directory not found: {output_dir}")
                return 1

            gcode_files = list(output_dir.glob("*.gcode"))
            if not gcode_files:
                logger.error(f"No G-code files found in {output_dir}")
                return 1

            logger.info(f"Validating {len(gcode_files)} G-code files in {output_dir}")
            validation_results = workflow.validate_files(gcode_files)

            print("\nValidation Results:")
            for result in validation_results:
                print(f"\nFile: {result['file']}")
                print(f"Commands: {len(result['stats']['commands'])}")
                if result['stats'].get('print_time'):
                    print(f"Estimated print time: {result['stats']['print_time']}")
                if result['stats'].get('filament_used'):
                    print(f"Filament used: {result['stats']['filament_used']}")
                print(f"Layers: {result['stats']['layer_count']}")

                if result['warnings']:
                    print(f"\nWarnings ({len(result['warnings'])}):")
                    for warning in result['warnings']:
                        print(f"  - {warning}")

                if result['errors']:
                    print(f"\nErrors ({len(result['errors'])}):")
                    for error in result['errors']:
                        print(f"  - {error}")

            return 0

        if args.process_only:
            # Process existing files in output directory
            output_dir = Path(args.output)
            if not output_dir.exists():
                logger.error(f"Output directory not found: {output_dir}")
                return 1

            input_files = list(output_dir.glob("*.gcode")) + list(output_dir.glob("*.zip"))
            if not input_files:
                logger.error(f"No input files found in {output_dir}")
                return 1

            logger.info(f"Processing {len(input_files)} files in {output_dir}")
            processed_files = workflow.process_for_centauri(input_files, output_dir / "processed")

            print(f"\nProcessed {len(processed_files)} files:")
            for f in processed_files:
                print(f"  - {f.name}")

            return 0

        # Full workflow
        result = workflow.full_workflow(args.url, args.output)

        if result["status"] == "completed_successfully":
            print(f"\n✅ Workflow completed successfully!")
            print(f"Files saved to: {result['workflow_dir']}")

            processed_files = [Path(result['workflow_dir']) / f for f in result['files']['processed']]
            print(f"\nProcessed files ({len(processed_files)}):")
            for f in processed_files:
                print(f"  - {f.name}")

            # Show validation summary
            total_warnings = sum(len(v["warnings"]) for v in result['files']['validation'])
            total_errors = sum(len(v["errors"]) for v in result['files']['validation'])

            print(f"\nValidation summary:")
            print(f"- Files validated: {len(result['files']['validation'])}")
            print(f"- Warnings: {total_warnings}")
            print(f"- Errors: {total_errors}")

            if total_errors > 0:
                print(f"\n⚠️  Completed with {total_errors} errors. Review validation results.")
            else:
                print(f"\n✅ All files validated successfully!")

        elif result["status"] == "completed_with_errors":
            print(f"\n⚠️  Workflow completed with errors")
            print(f"Files saved to: {result['workflow_dir']}")
            print(f"Review validation results for details.")

        else:
            print(f"\n❌ Workflow failed: {result.get('error', 'Unknown error')}")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
