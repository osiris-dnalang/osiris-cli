"""
Lab Executor — Safe experiment execution engine.

Executes experiment scripts in a controlled subprocess with:
- Timeout enforcement
- Output capture
- Result file detection
- CHRONOS lineage tracking
- Sovereign proof generation
"""

from typing import Dict, Any, Optional
import subprocess, os, time, json, sys


class LabExecutor:
    """Execute quantum experiments safely."""

    DEFAULT_TIMEOUT = 120  # seconds

    def __init__(self, python_bin: Optional[str] = None):
        self.python_bin = python_bin or sys.executable
        self.execution_log: list = []

    def run(
        self,
        script_path: str,
        timeout: int = DEFAULT_TIMEOUT,
        cwd: Optional[str] = None,
        env_extras: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute an experiment script and capture results.

        Returns dict with: success, stdout, stderr, duration, result_file, exit_code
        """
        if not os.path.exists(script_path):
            return {"success": False, "error": f"Script not found: {script_path}"}

        work_dir = cwd or os.path.dirname(script_path)
        env = os.environ.copy()
        if env_extras:
            env.update(env_extras)

        t0 = time.time()
        try:
            result = subprocess.run(
                [self.python_bin, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=work_dir,
                env=env,
            )
            duration = time.time() - t0

            # Look for result file
            result_file = os.path.splitext(script_path)[0] + "_results.json"
            result_data = None
            if os.path.exists(result_file):
                try:
                    with open(result_file) as f:
                        result_data = json.load(f)
                except Exception:
                    pass

            execution = {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_s": round(duration, 2),
                "script": script_path,
                "result_file": result_file if os.path.exists(result_file) else None,
                "result_data": result_data,
                "timestamp": time.time(),
            }

        except subprocess.TimeoutExpired:
            execution = {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Timeout after {timeout}s",
                "duration_s": timeout,
                "script": script_path,
                "result_file": None,
                "result_data": None,
                "timestamp": time.time(),
            }
        except Exception as e:
            execution = {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "duration_s": time.time() - t0,
                "script": script_path,
                "result_file": None,
                "result_data": None,
                "timestamp": time.time(),
            }

        self.execution_log.append(execution)
        return execution

    def dry_run(self, script_path: str) -> Dict[str, Any]:
        """Validate a script can be parsed without executing it."""
        if not os.path.exists(script_path):
            return {"valid": False, "error": f"Script not found: {script_path}"}

        result = subprocess.run(
            [self.python_bin, "-m", "py_compile", script_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "valid": result.returncode == 0,
            "script": script_path,
            "error": result.stderr if result.returncode != 0 else None,
        }

    def get_history(self) -> list:
        return self.execution_log
