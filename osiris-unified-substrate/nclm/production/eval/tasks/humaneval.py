import os
import subprocess
import sys
import tempfile
from typing import Callable, Dict, Iterable, List


def _safe_execute(code: str, timeout: int = 10) -> bool:
    """Execute generated code + tests in a sandboxed subprocess.

    Returns True if all tests pass (exit code 0), False otherwise.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", encoding="utf-8", delete=False) as fh:
        fh.write(code)
        path = fh.name
    env = {"PYTHONUNBUFFERED": "1", "PATH": os.environ.get("PATH", "")}
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def evaluate(predict_fn: Callable[[str], str], dataset: Iterable[Dict[str, object]], k: int = 1) -> float:
    """Evaluate pass@1 (or pass@k) on HumanEval-style problems.

    Each sample must have:
      - ``prompt``: the function signature + docstring
      - ``test``: the test harness code (``check(candidate)``)
      - ``entry_point`` (optional): function name
    """
    results: List[bool] = []
    for sample in dataset:
        prompt = str(sample.get("prompt", ""))
        test_code = str(sample.get("test", sample.get("tests", "")))
        entry_point = str(sample.get("entry_point", ""))

        passed_any = False
        for _ in range(k):
            completion = predict_fn(prompt)
            # Build runnable script: prompt + completion + tests
            full_code = prompt + completion + "\n" + test_code
            if entry_point:
                full_code += f"\ncheck({entry_point})\n"
            if _safe_execute(full_code):
                passed_any = True
                break
        results.append(passed_any)

    return sum(results) / len(results) if results else 0.0