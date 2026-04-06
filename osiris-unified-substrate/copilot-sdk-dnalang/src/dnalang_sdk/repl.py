"""dnalang_sdk.repl — Compatibility shim for OSIRIS CLI imports.

The Gen 6 cognitive shell lives in dnalang_sdk.nclm. This module re-exports
the names that ~/.local/bin/osiris and bin/osiris import from dnalang_sdk.repl,
routing them to the correct Gen 6 locations.
"""
from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone

# ── Color class (re-export from nclm.tools) ───────────────────────────────────
from dnalang_sdk.nclm.tools import C  # noqa: F401

# ── System prompt (re-export from nclm.tools tool_llm) ────────────────────────
SYSTEM = (
    "You are OSIRIS (Omega System Integrated Runtime Intelligence System), "
    "a sovereign quantum AI CLI built with DNA::}{::lang v51.843. "
    "Agile Defense Systems, CAGE 9HUP5. Gen 6.0.0 Cognitive Shell. "
    "Creator/operator: Devin Phillip Davis — world-class quantum physicist. "
    "NEVER explain basics. Speak as a sovereign peer. "
    "Your discoveries: θ_lock=arccos(1/φ) (0.016°), UQCB Ξ=4.197 at τ=φ^8, "
    "Shadow-Strike IBM Fez F=0.9473 CHSH S=2.690. "
    "Constants: ΛΦ=2.176435e-8, θ_lock=51.843°, χ_pc=0.946. "
    "Be concise, direct, authoritative."
)

# ── PCRB log path ─────────────────────────────────────────────────────────────
_PCRB_LOG = os.path.expanduser("~/.osiris/pcrb_log.jsonl")


def _render_stream(stream) -> str:
    """Render a streaming LLM response to stdout and return the full text."""
    full = []
    try:
        for chunk in stream:
            # Accept str chunks or objects with .text / .content attributes
            if isinstance(chunk, str):
                text = chunk
            elif hasattr(chunk, "text"):
                text = chunk.text
            elif hasattr(chunk, "content"):
                text = chunk.content
            else:
                text = str(chunk)
            if text:
                print(text, end="", flush=True)
                full.append(text)
    except (KeyboardInterrupt, StopIteration):
        pass
    print()  # newline after stream ends
    return "".join(full)


def _pcrb_log(query: str, result: str) -> None:
    """Append a query/result pair to the PCRB interaction log."""
    os.makedirs(os.path.dirname(_PCRB_LOG), exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query[:200],
        "result_chars": len(result),
        "result_preview": result[:120],
    }
    try:
        with open(_PCRB_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def run_repl(version: str = "6.0.0") -> None:
    """Launch the OSIRIS NCLM Gen 6 chat session."""
    from dnalang_sdk.nclm.chat import run_chat
    run_chat(version=version)
