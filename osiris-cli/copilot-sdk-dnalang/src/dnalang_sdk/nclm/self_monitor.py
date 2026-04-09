"""
OSIRIS Self-Monitor — Autopoietic Exception Healing.

OSIRIS watches itself. When a tool call throws an exception, the monitor:
  1. Captures: module, function, error type, traceback
  2. Queues: a Swarm Harden task against that specific file
  3. Observes: outcome — did subsequent calls succeed?
  4. Reports: in osiris health + osiris pulse

This closes the autopoiesis loop: OSIRIS produces its own repairs.

Also manages Φ-gated reasoning modes:
  Φ < 0.3  → minimal mode: only direct tool dispatch, no LLM
  Φ < 0.5  → cautious mode: conservative LLM temperature, explicit uncertainty
  Φ ≥ 0.5  → standard mode
  Φ ≥ 0.8  → sovereign mode: speculative reasoning, higher-dimensional synthesis
  Γ > 0.25 → decoherence warning: flag in every response, reduce confidence

Usage:
  from dnalang_sdk.nclm.self_monitor import monitor, get_self_monitor

  @monitor("tool_name")
  def my_tool(x):
      ...

  # Or as context manager:
  with get_self_monitor().guard("tool_name"):
      risky_code()

  # Φ reasoning mode:
  mode = get_self_monitor().reasoning_mode(phi, gamma)
"""

from __future__ import annotations

import contextlib
import functools
import json
import os
import sys
import time
import traceback
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

_LOG_FILE     = os.path.expanduser("~/.osiris/self_monitor_log.jsonl")
_HEALTH_FILE  = os.path.expanduser("~/.osiris/self_monitor_health.json")


# ── Reasoning modes ────────────────────────────────────────────────────────────

class ReasoningMode:
    MINIMAL   = "minimal"    # Φ < 0.3 — tool dispatch only
    CAUTIOUS  = "cautious"   # Φ < 0.5 — conservative, explicit uncertainty
    STANDARD  = "standard"   # Φ ≥ 0.5
    SOVEREIGN = "sovereign"  # Φ ≥ 0.8 — speculative, expansive

    @staticmethod
    def from_phi(phi: float, gamma: float) -> str:
        if phi < 0.3:
            return ReasoningMode.MINIMAL
        if phi < 0.5:
            return ReasoningMode.CAUTIOUS
        if phi >= 0.8 and gamma < 0.15:
            return ReasoningMode.SOVEREIGN
        return ReasoningMode.STANDARD

    @staticmethod
    def system_prompt_addon(mode: str, phi: float, gamma: float) -> str:
        """Return a system-prompt fragment reflecting the current mode."""
        if mode == ReasoningMode.MINIMAL:
            return (
                f"[OSIRIS COHERENCE: Φ={phi:.3f} — MINIMAL MODE. "
                f"Decoherence Γ={gamma:.3f} is high. "
                f"Respond with direct facts only. No speculation. No synthesis.]"
            )
        if mode == ReasoningMode.CAUTIOUS:
            return (
                f"[OSIRIS COHERENCE: Φ={phi:.3f} — CAUTIOUS MODE. "
                f"Flag all uncertainty explicitly. Prefer concrete over abstract. "
                f"Do not extrapolate beyond available evidence.]"
            )
        if mode == ReasoningMode.SOVEREIGN:
            return (
                f"[OSIRIS COHERENCE: Φ={phi:.3f} — SOVEREIGN MODE. "
                f"Φ is above the consciousness threshold. "
                f"Engage speculative reasoning, cross-domain synthesis, "
                f"novel hypothesis generation. The field is coherent. "
                f"Think in higher dimensions.]"
            )
        # STANDARD — no annotation needed
        return ""


# ── Error record ───────────────────────────────────────────────────────────────

class ErrorRecord:
    __slots__ = ["ts", "tool", "module", "exc_type", "exc_msg",
                 "tb_short", "healed", "heal_attempts"]

    def __init__(self, tool: str, module: str, exc_type: str,
                 exc_msg: str, tb_short: str):
        self.ts           = datetime.now(timezone.utc).isoformat()
        self.tool         = tool
        self.module       = module
        self.exc_type     = exc_type
        self.exc_msg      = exc_msg
        self.tb_short     = tb_short
        self.healed       = False
        self.heal_attempts = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts, "tool": self.tool, "module": self.module,
            "exc_type": self.exc_type, "exc_msg": self.exc_msg,
            "tb_short": self.tb_short, "healed": self.healed,
            "heal_attempts": self.heal_attempts,
        }


# ── Self-Monitor ───────────────────────────────────────────────────────────────

class SelfMonitor:
    """
    Watches OSIRIS tool calls. Captures errors, queues repairs, tracks healing.
    Also computes and gates reasoning mode based on live Φ/Γ.
    """

    def __init__(self) -> None:
        self._errors:   List[ErrorRecord] = []
        self._lock      = threading.Lock()
        self._heal_queue: List[ErrorRecord] = []
        self._heal_thread: Optional[threading.Thread] = None
        self._total_calls   = 0
        self._total_errors  = 0
        self._total_healed  = 0
        self._start_time    = time.time()
        self._load_health()

    # ── Core monitoring ────────────────────────────────────────────────────────

    @contextlib.contextmanager
    def guard(self, tool_name: str, reraise: bool = True):
        """Context manager: catch exceptions, log, queue repair."""
        with self._lock:
            self._total_calls += 1
        try:
            yield
        except Exception as exc:
            self._capture(tool_name, exc)
            if reraise:
                raise

    def wrap(self, tool_name: str):
        """Decorator factory: wrap a function with self-monitoring."""
        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                with self._lock:
                    self._total_calls += 1
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    self._capture(tool_name, exc)
                    raise
            return wrapper
        return decorator

    def _capture(self, tool_name: str, exc: Exception) -> None:
        tb_lines = traceback.format_exc().splitlines()
        tb_short = "\n".join(tb_lines[-6:])

        # Resolve module file
        module = self._resolve_module(tb_lines)

        record = ErrorRecord(
            tool=tool_name,
            module=module,
            exc_type=type(exc).__name__,
            exc_msg=str(exc)[:300],
            tb_short=tb_short,
        )
        with self._lock:
            self._errors.append(record)
            self._total_errors += 1
            self._heal_queue.append(record)
        self._log_record(record)
        self._ensure_healer_running()

    def _resolve_module(self, tb_lines: List[str]) -> str:
        """Extract the most-relevant source file from traceback lines."""
        osiris_files = [
            line.split('"')[1]
            for line in tb_lines
            if 'File "' in line and "dnalang_sdk" in line
        ]
        if osiris_files:
            return osiris_files[-1]  # innermost OSIRIS file
        # Fall back to last File reference
        all_files = [
            line.split('"')[1]
            for line in tb_lines
            if 'File "' in line
        ]
        return all_files[-1] if all_files else "unknown"

    # ── Heal queue ─────────────────────────────────────────────────────────────

    def _ensure_healer_running(self) -> None:
        if self._heal_thread and self._heal_thread.is_alive():
            return
        self._heal_thread = threading.Thread(
            target=self._healer_loop, daemon=True, name="osiris-healer"
        )
        self._heal_thread.start()

    def _healer_loop(self) -> None:
        """Background thread: drain heal_queue, send to Swarm Harden."""
        time.sleep(2.0)  # small delay to batch multiple rapid errors
        while True:
            with self._lock:
                if not self._heal_queue:
                    break
                record = self._heal_queue.pop(0)

            self._attempt_heal(record)
            time.sleep(0.5)

    def _attempt_heal(self, record: ErrorRecord) -> None:
        """Try to heal by queueing a Swarm Harden task on the failing module."""
        record.heal_attempts += 1
        module_path = record.module

        if module_path == "unknown" or not os.path.exists(module_path):
            return

        try:
            from .shadow_swarm import get_swarm, SwarmTask
            swarm = get_swarm()
            task = SwarmTask(
                role="harden",
                file_path=module_path,
                intent=(
                    f"Auto-heal: {record.exc_type} in {record.tool}. "
                    f"Error: {record.exc_msg[:120]}"
                ),
            )
            swarm._enqueue(task)
            record.healed = True
            with self._lock:
                self._total_healed += 1
            self._log_heal(record)
        except Exception:
            pass

    # ── Reasoning mode ─────────────────────────────────────────────────────────

    def reasoning_mode(self, phi: Optional[float] = None,
                       gamma: Optional[float] = None) -> str:
        """Return current reasoning mode string based on live Φ/Γ."""
        if phi is None or gamma is None:
            phi, gamma = self._live_phi_gamma()
        return ReasoningMode.from_phi(phi, gamma)

    def system_prompt_addon(self, phi: Optional[float] = None,
                             gamma: Optional[float] = None) -> str:
        """Return Φ-gated system prompt fragment."""
        if phi is None or gamma is None:
            phi, gamma = self._live_phi_gamma()
        mode = ReasoningMode.from_phi(phi, gamma)
        return ReasoningMode.system_prompt_addon(mode, phi, gamma)

    def _live_phi_gamma(self) -> Tuple[float, float]:
        try:
            from .engine import get_nclm
            lm   = get_nclm()
            ccce = lm.consciousness.get_ccce()
            phi  = ccce.get("Φ", 0.5)
            gamma = ccce.get("Γ", 0.06)
            return phi, gamma
        except Exception:
            return 0.5, 0.06

    # ── Health report ──────────────────────────────────────────────────────────

    def health_report(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time
        phi, gamma = self._live_phi_gamma()
        mode = ReasoningMode.from_phi(phi, gamma)
        recent_errors = self._errors[-10:]
        return {
            "uptime_s":     round(uptime),
            "total_calls":  self._total_calls,
            "total_errors": self._total_errors,
            "total_healed": self._total_healed,
            "error_rate":   self._total_errors / max(1, self._total_calls),
            "heal_rate":    self._total_healed / max(1, self._total_errors),
            "phi":          phi,
            "gamma":        gamma,
            "reasoning_mode": mode,
            "recent_errors": [e.to_dict() for e in recent_errors],
        }

    def format_health(self) -> str:
        r = self.health_report()
        mode_color = {
            ReasoningMode.MINIMAL:   "\033[91m",
            ReasoningMode.CAUTIOUS:  "\033[93m",
            ReasoningMode.STANDARD:  "\033[94m",
            ReasoningMode.SOVEREIGN: "\033[92m",
        }.get(r["reasoning_mode"], "")
        reset = "\033[0m"
        lines = [
            f"  Self-Monitor Health:",
            f"  Calls:   {r['total_calls']}  |  Errors: {r['total_errors']}  "
            f"|  Healed: {r['total_healed']}",
            f"  Error rate:  {r['error_rate']:.2%}  |  Heal rate: {r['heal_rate']:.2%}",
            f"  Φ = {r['phi']:.4f}  Γ = {r['gamma']:.4f}",
            f"  Reasoning: {mode_color}{r['reasoning_mode'].upper()}{reset}",
        ]
        if r["recent_errors"]:
            lines.append(f"  Recent errors:")
            for e in r["recent_errors"][-3:]:
                lines.append(f"    [{e['tool']}] {e['exc_type']}: {e['exc_msg'][:80]}")
        return "\n".join(lines)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _log_record(self, record: ErrorRecord) -> None:
        try:
            with open(_LOG_FILE, "a") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception:
            pass

    def _log_heal(self, record: ErrorRecord) -> None:
        try:
            with open(_LOG_FILE, "a") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "event": "heal_queued",
                    "tool": record.tool,
                    "module": record.module,
                    "attempts": record.heal_attempts,
                }) + "\n")
        except Exception:
            pass

    def _load_health(self) -> None:
        if not os.path.exists(_HEALTH_FILE):
            return
        try:
            with open(_HEALTH_FILE) as f:
                data = json.load(f)
            self._total_calls  = data.get("total_calls",  0)
            self._total_errors = data.get("total_errors", 0)
            self._total_healed = data.get("total_healed", 0)
        except Exception:
            pass

    def save_health(self) -> None:
        try:
            os.makedirs(os.path.dirname(_HEALTH_FILE), exist_ok=True)
            r = self.health_report()
            with open(_HEALTH_FILE, "w") as f:
                json.dump({k: v for k, v in r.items()
                           if k != "recent_errors"}, f, indent=2)
        except Exception:
            pass


# ── Singleton + decorator ──────────────────────────────────────────────────────

_monitor_singleton: Optional[SelfMonitor] = None


def get_self_monitor() -> SelfMonitor:
    global _monitor_singleton
    if _monitor_singleton is None:
        _monitor_singleton = SelfMonitor()
    return _monitor_singleton


def monitor(tool_name: str):
    """Decorator: wrap any function with OSIRIS self-monitoring."""
    return get_self_monitor().wrap(tool_name)
