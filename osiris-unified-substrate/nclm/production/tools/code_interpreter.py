import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from typing import Dict


@dataclass
class CodeExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def run_code(code: str, timeout: int = 5) -> CodeExecutionResult:
    """Run short Python snippets in an isolated temporary file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", encoding="utf-8", delete=False) as handle:
        handle.write(code)
        temp_path = handle.name

    env = {"PYTHONUNBUFFERED": "1", "PATH": os.environ.get("PATH", "")}
    try:
        completed = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return CodeExecutionResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CodeExecutionResult(
            stdout=exc.stdout or "",
            stderr=exc.stderr or "Execution timed out",
            returncode=124,
            timed_out=True,
        )
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass