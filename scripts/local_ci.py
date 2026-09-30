#!/usr/bin/env python3
"""Run .github/workflows/ci.yml's checks on this machine and record the result.

GitHub Actions cannot run while the account is billing-locked, so this does the
same steps locally against the *committed* tree (a `git archive` of the commit,
not the working copy):

  lint   ruff check --select E,F,W --ignore E501 <ci.yml's paths>
  test   pytest tests/ -v --tb=short --strict-markers, on each installed Python
         (3.9-3.12) in a venv holding only ci.yml's core deps, with Ollama
         unreachable -- as on a GitHub runner

Each run is appended to ~/.osiris/ci/runs.jsonl (hash-chained) and, when
NEON_DATABASE_URL is set, inserted into the Neon table osiris_ci_runs through
db_ledger's connection (the DSN is read from the environment only and never
printed). A Neon failure is reported, never fatal: the local file is the record.

  set -a; . <file with NEON_DATABASE_URL>; set +a
  python scripts/local_ci.py [--commit REF] [--no-neon]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Optional

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CI_HOME = os.path.join(os.path.expanduser("~"), ".osiris", "ci")
CORE_DEPS = ["numpy", "scipy", "requests", "PyYAML", "rich", "pytest", "pytest-cov"]
LINT_PATHS = ["osiris_launcher.py", "osiris_cli.py", "osiris_livlm.py", "nclm/", "qbyte_system/", "osiris/"]
PYTHONS = ["3.9", "3.10", "3.11", "3.12"]
DEAD_OLLAMA = "http://127.0.0.1:9"


def sh(args: List[str], cwd: Optional[str] = None, env: Optional[dict] = None,
       timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def ci_env() -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "NEON_DATABASE_URL", "ZENODO_TOKEN", "IBM_QUANTUM_TOKEN", "GITHUB_TOKEN")}
    env.update(OLLAMA_HOST=DEAD_OLLAMA, OSIRIS_OLLAMA=DEAD_OLLAMA)
    return env


def export_tree(ref: str, dest: str) -> str:
    commit = sh(["git", "-C", REPO, "rev-parse", f"{ref}^{{commit}}"]).stdout.strip()  # a tag names its commit
    if not commit:
        sys.exit(f"unknown commit {ref!r}")
    archive = subprocess.Popen(["git", "-C", REPO, "archive", commit], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", dest], stdin=archive.stdout, check=True)
    archive.wait()
    return commit


def venv_for(version: str) -> Optional[str]:
    exe = shutil.which(f"python{version}")
    if not exe:
        return None
    path = os.path.join(CI_HOME, f"venv-{version}")
    py = os.path.join(path, "bin", "python")
    if not os.path.exists(py):
        r = sh([exe, "-m", "venv", path])
        if r.returncode:
            return None
    stamp = os.path.join(path, ".deps")
    if not os.path.exists(stamp):
        r = sh([py, "-m", "pip", "install", "-q", *CORE_DEPS], env=ci_env(), timeout=3600)
        if r.returncode:
            print(f"  python{version}: dependency install failed:\n{r.stderr[-800:]}")
            return None
        open(stamp, "w").write(" ".join(CORE_DEPS))
    return py


def lint(tree: str) -> Dict[str, object]:
    ruff = shutil.which("ruff") or os.path.join(os.path.expanduser("~"), "osiris_env", "bin", "ruff")
    if not os.path.exists(ruff):
        return {"status": "skipped", "reason": "ruff not installed"}
    paths = [p for p in LINT_PATHS if os.path.exists(os.path.join(tree, p))]
    r = sh([ruff, "check", "--select", "E,F,W", "--ignore", "E501", "--output-format", "concise", *paths], cwd=tree)
    m = re.search(r"Found (\d+) error", r.stdout)
    return {"status": "pass" if r.returncode == 0 else "fail", "findings": int(m.group(1)) if m else 0}


def test(tree: str, version: str) -> Dict[str, object]:
    py = venv_for(version)
    if py is None:
        return {"python": version, "status": "skipped", "reason": f"python{version} unavailable"}
    t0 = time.time()
    r = sh([py, "-m", "pytest", "tests/", "-v", "--tb=short", "--strict-markers", "-p", "no:cacheprovider"],
           cwd=tree, env=ci_env(), timeout=3600)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|errors?|skipped)", tail[0])}
    failed = [ln.split(" ", 1)[1].split(" - ")[0] for ln in r.stdout.splitlines() if ln.startswith("FAILED ")]
    return {"python": version, "status": "pass" if r.returncode == 0 else "fail", "seconds": round(time.time() - t0, 1),
            "passed": counts.get("passed", 0), "failed": counts.get("failed", 0),
            "errors": counts.get("error", 0) + counts.get("errors", 0), "failed_tests": failed[:50],
            "summary": tail[0][:200]}


def record_local(row: dict) -> str:
    os.makedirs(CI_HOME, exist_ok=True)
    path = os.path.join(CI_HOME, "runs.jsonl")
    prev = "0" * 64
    try:
        with open(path, encoding="utf-8") as f:
            last = f.read().strip().splitlines()[-1:]
            prev = json.loads(last[0])["hash"] if last else prev
    except (OSError, ValueError, KeyError):
        pass
    row["prev"] = prev
    row["hash"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row["hash"]


def record_neon(row: dict) -> str:
    sys.path.insert(0, REPO)
    import db_ledger
    if not db_ledger.is_configured_neon():
        return "not configured (NEON_DATABASE_URL unset)"
    try:
        conn = db_ledger._neon_connect()
    except Exception:  # noqa: BLE001 - never surface the driver's text (it can contain the DSN)
        return "connection failed"
    try:
        conn.run("CREATE TABLE IF NOT EXISTS osiris_ci_runs ("
                 "id BIGSERIAL PRIMARY KEY, recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
                 "repo TEXT NOT NULL, commit_sha TEXT NOT NULL, branch TEXT, status TEXT NOT NULL, "
                 "lint_findings INTEGER, tests_passed INTEGER, tests_failed INTEGER, "
                 "run_hash TEXT NOT NULL, detail JSONB NOT NULL)")
        tests = row["tests"]
        conn.run("INSERT INTO osiris_ci_runs (repo, commit_sha, branch, status, lint_findings, tests_passed, "
                 "tests_failed, run_hash, detail) VALUES (:r, :c, :b, :s, :l, :p, :f, :h, CAST(:d AS JSONB))",
                 r=row["repo"], c=row["commit"], b=row["branch"], s=row["status"],
                 l=row["lint"].get("findings"), p=sum(t.get("passed", 0) for t in tests),
                 f=sum(t.get("failed", 0) for t in tests), h=row["hash"], d=json.dumps(row))
        return "recorded in osiris_ci_runs"
    except Exception:  # noqa: BLE001
        return "query failed"
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--no-neon", action="store_true")
    ap.add_argument("--python", action="append", help="limit to these versions (repeatable)")
    args = ap.parse_args(argv)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="osiris-ci-") as tree:
        commit = export_tree(args.commit, tree)
        print(f"osiris-cli CI · commit {commit[:12]} (committed tree, not the working copy)")
        lint_res = lint(tree)
        print(f"  lint: {lint_res['status']}" + (f" ({lint_res.get('findings')} findings)" if "findings" in lint_res else
                                                 f" ({lint_res.get('reason')})"))
        tests = []
        for v in args.python or PYTHONS:
            res = test(tree, v)
            tests.append(res)
            print(f"  test {v}: {res['status']}" + (f" -- {res['summary']}" if "summary" in res else
                                                   f" ({res.get('reason')})"))
            for name in res.get("failed_tests", [])[:10]:
                print(f"      FAILED {name}")
    ran = [t for t in tests if t["status"] != "skipped"]
    status = "pass" if ran and all(t["status"] == "pass" for t in ran) and lint_res["status"] != "fail" else (
        "tests-pass-lint-fail" if ran and all(t["status"] == "pass" for t in ran) else "fail")
    row = {"repo": "osiris-dnalang/osiris-cli", "commit": commit,
           "branch": sh(["git", "-C", REPO, "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip(),
           "status": status, "lint": lint_res, "tests": tests,
           "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)), "seconds": round(time.time() - t0, 1),
           "host": os.uname().nodename}
    h = record_local(row)
    print(f"  result: {status} · {row['seconds']} s · run {h[:12]} in ~/.osiris/ci/runs.jsonl")
    if not args.no_neon:
        print(f"  neon: {record_neon(row)}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
