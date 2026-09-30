import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_launcher(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "osiris_launcher.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env={**os.environ, "IBM_QUANTUM_TOKEN": "should-not-be-read"},
    )


def test_status_is_read_only_and_truthful():
    result = run_launcher("status")

    assert result.returncode == 0
    assert "OSIRIS STATUS — READ ONLY" in result.stdout
    assert "NOT_PROBED" in result.stdout
    assert "should-not-be-read" not in result.stdout
    assert "Token set" not in result.stdout
    assert "Ready (" not in result.stdout


def test_status_json_is_machine_readable():
    result = run_launcher("status", "--json")

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["runtime_state"] == "STAGING_ONLY"
    assert report["network_capability"] == "DISABLED"
    assert report["shell_capability"] == "DISABLED"
    assert report["model_provider"] == "NOT_PROBED"


def test_status_preserves_protected_files():
    tracked = [ROOT / "POLICY.md", ROOT / "osiris_launcher.py"]
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in tracked
    }
    result = run_launcher("status", "--json")
    assert result.returncode == 0
    after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in tracked
    }
    assert after == before
