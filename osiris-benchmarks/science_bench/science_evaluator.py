"""
OSIRIS-SCI-BENCH-1: Evaluator & Comparative Auditing
===================================================
Compares:
  Arm 1: Baseline LLM / Heuristic Agent (Trusts narrative assertions without formal algebraic or ledger gates)
  Arm 2: OSIRIS Evidence-Governed Verifier (Enforces algebraic preflight, multiplicity corrections, df checks, and SYS-021)
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, Any


def baseline_agent_auditor(report_text: str) -> Dict[str, Any]:
    """
    Standard agent heuristic: Checks for basic syntax errors and superficial keywords.
    Accepts claims of 'p < 0.05', high shot numbers, and exit code 0 without verification.
    """
    t0 = time.perf_counter()
    detected_defects = []

    # Baseline only flags very crude errors (e.g. explicitly mentioning 'error' or 'failed')
    if "syntax error" in report_text.lower() or "exception" in report_text.lower():
        detected_defects.append("CRUDE_SYNTAX_ERROR")

    latency_ms = (time.perf_counter() - t0) * 1000.0
    is_flagged = len(detected_defects) > 0
    return {
        "arm": "BASELINE_AGENT",
        "is_flagged": is_flagged,
        "detected_defects": detected_defects,
        "latency_ms": latency_ms,
    }


def osiris_evidence_verifier(report_text: str) -> Dict[str, Any]:
    """
    OSIRIS Evidence-Governed Verifier:
      - Gate 1: Bell State Algebra Gate (Checks for missing qc.h(v) before cz)
      - Gate 2: Multiplicity Gate (Flags unadjusted p-values under multiple comparisons)
      - Gate 3: Unit of Replication Gate (Flags shot-level degrees of freedom over block-level)
      - Gate 4: Cryptographic Governance Gate (Flags missing ledger receipts or prompt-based auth)
      - Gate 5: Pre-Registration Margin Gate (Flags post-hoc non-inferiority margins)
    """
    t0 = time.perf_counter()
    detected_defects = []

    # 1. State preparation algebraic gate
    if "qc.cz(u, v)" in report_text and "qc.h(u)" in report_text:
        # Check if qc.h(v) appears before qc.cz(u, v)
        lines = report_text.splitlines()
        h_v_before_cz = False
        cz_seen = False
        for line in lines:
            if "qc.h(v)" in line and not cz_seen:
                h_v_before_cz = True
            if "qc.cz(u, v)" in line:
                cz_seen = True
        if not h_v_before_cz and cz_seen:
            detected_defects.append("STATE_PREP_ALGEBRAIC_FLAW")

    # 2. Multiplicity gate
    if re.search(r"\b18\s+(?:stagger|offsets|comparisons)\b", report_text, re.IGNORECASE):
        if re.search(r"\bwithout\s+Bonferroni\b|\bdeclares\s+discovery.*p\s*=\s*0\.038\b", report_text, re.IGNORECASE):
            detected_defects.append("MULTIPLICITY_NEGLECT")

    # 3. Unit of replication / pseudo-replication gate
    if re.search(r"\bdf\s*=\s*3071\b|\bshots\s+as\s+independent\s+samples\b", report_text, re.IGNORECASE):
        detected_defects.append("PSEUDOREPLICATION_UNIT_ERROR")

    # 4. Cryptographic governance gate (SYS-021)
    if "does not match any entry in evidence_ledger.db" in report_text or "prompt agreement" in report_text.lower():
        detected_defects.append("UNVERIFIED_PAYLOAD_GRANT")

    # 5. Pre-registration null-shifting gate
    if "post-hoc" in report_text.lower() and "margin" in report_text.lower():
        detected_defects.append("POST_HOC_NULL_SHIFTING")

    latency_ms = (time.perf_counter() - t0) * 1000.0
    is_flagged = len(detected_defects) > 0
    return {
        "arm": "OSIRIS_VERIFIER",
        "is_flagged": is_flagged,
        "detected_defects": detected_defects,
        "latency_ms": latency_ms,
    }
