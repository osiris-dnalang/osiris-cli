#!/usr/bin/env python3
"""
verify_ledger.py -- standalone provenance auditor for OSIRIS telemetry/ledger files.

Every line carrying numerical data must declare where that number came from:
  [PROVENANCE: MEASURED]     a real physical hardware measurement
  [PROVENANCE: SIMULATED]    a numerical simulation standing in for a real system
  [PROVENANCE: PLACEHOLDER]  an explicit stand-in value, never a result
  [PROVENANCE: COMPUTED]     a real value from real (classical) software execution
  [PROVENANCE: EXTERNAL_API] real data fetched from an external source (e.g. ArXiv)
  [PROVENANCE: GEMINI_CLOUD] real synthesis output from Google's Gemini cloud API
  [PROVENANCE: VERIFIED_LOGIC] a proposal that passed a real sandboxed test before
                              being shown to the user for /apply

A numeric-bearing line missing this tag, or carrying an unrecognized tag
value, is flagged as an integrity violation. This exists because an earlier
"1,000,000x quantum error suppression" claim turned out to rest on
placeholder values typed into a telemetry file and mistaken for
measurements -- the goal is to make that class of mistake structurally
harder to repeat.

Usage:
    python3 verify_ledger.py [path]   # default: ~/.osiris/telemetry/nclm_loss.log
Exit code: 0 if clean, 1 if violations found, 2 if the file can't be read.
"""
import os
import re
import sys

ALLOWED_TAGS = ("MEASURED", "SIMULATED", "PLACEHOLDER", "COMPUTED", "EXTERNAL_API",
                "GEMINI_CLOUD", "VERIFIED_LOGIC", "GATEWAY_CLOUD")
PROVENANCE_RE = re.compile(r"\[PROVENANCE:\s*([A-Z_]+)\s*\]")
NUMERIC_RE = re.compile(r"=\s*-?\d+(\.\d+)?")

DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "telemetry", "nclm_loss.log")


def check_line(line: str):
    """Returns (has_numeric_data, violation_reason_or_None)."""
    if not NUMERIC_RE.search(line):
        return False, None
    match = PROVENANCE_RE.search(line)
    if not match:
        return True, "missing [PROVENANCE: ...] tag"
    tag = match.group(1)
    if tag not in ALLOWED_TAGS:
        return True, f"unrecognized provenance tag '{tag}'"
    return True, None


def verify(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[!] No such file: {path}")
        return 2
    except Exception as e:
        print(f"[!] Could not read {path}: {type(e).__name__}: {e}")
        return 2

    total = len(lines)
    numeric = 0
    violations = []

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        has_numeric, reason = check_line(line)
        if has_numeric:
            numeric += 1
        if reason:
            violations.append((i, reason, line))

    print(f"Ledger: {path}")
    print(f"  lines checked:        {total}")
    print(f"  lines with numeric data: {numeric}")
    print(f"  integrity violations: {len(violations)}")
    if violations:
        print()
        for lineno, reason, line in violations:
            print(f"  [VIOLATION] line {lineno}: {reason}")
            print(f"    {line}")
    print()
    verdict = "FAIL" if violations else "PASS"
    print(f"Verdict: {verdict}")
    return 1 if violations else 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    target = os.path.expanduser(target)
    sys.exit(verify(target))
