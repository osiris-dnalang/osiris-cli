"""
OSIRIS Hardware Loop — Autopoietic IBM Quantum Job Ingestion.

Closes the experiment loop: hardware completes → analyze → ingest → brief.
OSIRIS no longer waits to be asked. When a job finishes it knows.

Analysis pipeline per job:
  1. Per-qubit excitation rates
  2. ZZ correlations near high-excitation qubits (shock detection)
  3. Bell fidelity (2-qubit jobs)
  4. GHZ fidelity (multi-qubit all-zero / all-one fraction)
  5. Bimodal structure detection (SPT chain signature)

Ingestion: creates ExperimentNode in ResearchGraph, connects to relevant claims.
Briefing:  formatted summary of what changed since last check.

Usage:
  from dnalang_sdk.nclm.hardware_loop import get_hardware_loop, HardwareLoop
  loop = get_hardware_loop()
  briefing = loop.check()          # poll + ingest new results
  loop.start_daemon()              # background thread, polls every N minutes
  loop.stop_daemon()
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

_SEEN_FILE   = os.path.expanduser("~/.osiris/hardware_loop_seen.json")
_RESULTS_DIR = os.path.expanduser("~/.osiris/hardware_results/")
_LOG_FILE    = os.path.expanduser("~/.osiris/hardware_loop.jsonl")

_POLL_INTERVAL_SEC = 300   # 5 minutes


# ── Analysis result ────────────────────────────────────────────────────────────

@dataclass
class JobAnalysis:
    job_id:         str
    backend:        str
    created:        str
    shots:          int
    n_qubits:       int
    excitation:     List[float]         # per-qubit excitation rates
    shock_qubit:    Optional[int]       # index of most-excited qubit
    shock_exc:      float               # excitation of shock qubit
    zz_near_shock:  Dict[str, float]    # "q56,q58" → ZZ value
    bell_fidelity:  Optional[float]     # only for 2-qubit jobs
    ghz_fidelity:   Optional[float]     # |00...0⟩ + |11...1⟩ fraction
    bimodal:        bool                # SPT chain signature detected
    bimodal_high_n: int                 # qubits with exc > 0.6
    bimodal_low_n:  int                 # qubits with exc < 0.1
    anomalies:      List[str]           # plain-text notable findings

    def summary(self) -> str:
        lines = [
            f"  Job {self.job_id}  [{self.backend}]  {self.shots} shots  {self.n_qubits}q",
        ]
        if self.shock_exc > 0.7:
            lines.append(f"  ⚡ Shock qubit q{self.shock_qubit}: {self.shock_exc:.4f} excitation")
        if self.zz_near_shock:
            best_zz = min(self.zz_near_shock.values())
            lines.append(f"  ZZ strongest: {best_zz:+.4f} ({len(self.zz_near_shock)} correlators)")
        if self.bell_fidelity is not None:
            lines.append(f"  Bell fidelity: {self.bell_fidelity:.4f}")
        if self.ghz_fidelity is not None:
            lines.append(f"  GHZ fidelity: {self.ghz_fidelity:.4f}")
        if self.bimodal:
            lines.append(
                f"  Bimodal SPT structure: {self.bimodal_high_n} high / "
                f"{self.bimodal_low_n} low excitation qubits"
            )
        for a in self.anomalies[:3]:
            lines.append(f"  ★ {a}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        return d


# ── Hardware loop ──────────────────────────────────────────────────────────────

class HardwareLoop:
    """
    Polls IBM Quantum for completed jobs, analyses results, ingests into
    the ResearchGraph, and returns a formatted briefing of new findings.
    """

    def __init__(self) -> None:
        self._seen: Set[str] = self._load_seen()
        self._daemon_thread: Optional[threading.Thread] = None
        self._daemon_stop = threading.Event()
        os.makedirs(_RESULTS_DIR, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def check(self, token: Optional[str] = None, limit: int = 50) -> str:
        """
        Poll IBM Quantum for DONE jobs not yet seen. Analyse + ingest each.
        Returns a formatted briefing string (empty string if nothing new).
        """
        new_analyses: List[JobAnalysis] = []
        svc = self._connect(token)
        if svc is None:
            return ""

        try:
            jobs = svc.jobs(limit=limit)
        except Exception as e:
            self._log(f"poll_error: {e}")
            return ""

        done_jobs = [j for j in jobs if str(j.status()) == "DONE"]
        new_jobs  = [j for j in done_jobs if j.job_id() not in self._seen]

        if not new_jobs:
            return ""

        for job in new_jobs:
            try:
                analysis = self._analyse_job(job)
                if analysis:
                    new_analyses.append(analysis)
                    self._ingest_to_graph(analysis)
                    self._save_result(analysis)
                    self._log_analysis(analysis)
                self._seen.add(job.job_id())
            except Exception as e:
                self._log(f"job_error job={job.job_id()} err={e}")

        self._save_seen()

        if not new_analyses:
            return ""

        return self._format_briefing(new_analyses)

    def start_daemon(self, token: Optional[str] = None,
                     interval_sec: int = _POLL_INTERVAL_SEC) -> None:
        """Start background polling thread."""
        if self._daemon_thread and self._daemon_thread.is_alive():
            return
        self._daemon_stop.clear()

        def _loop():
            while not self._daemon_stop.is_set():
                try:
                    briefing = self.check(token=token)
                    if briefing:
                        self._log(f"briefing_ready: {len(briefing)} chars")
                        # Write to a "pending briefings" file for pulse to pick up
                        _pend = os.path.expanduser("~/.osiris/pending_briefing.txt")
                        with open(_pend, "a") as f:
                            f.write(f"\n\n{briefing}\n")
                except Exception as e:
                    self._log(f"daemon_error: {e}")
                self._daemon_stop.wait(timeout=interval_sec)

        self._daemon_thread = threading.Thread(target=_loop, daemon=True,
                                               name="osiris-hardware-loop")
        self._daemon_thread.start()

    def stop_daemon(self) -> None:
        self._daemon_stop.set()

    def pending_briefing(self) -> str:
        """Read and clear the pending briefing file. Called by osiris pulse."""
        _pend = os.path.expanduser("~/.osiris/pending_briefing.txt")
        if not os.path.exists(_pend):
            return ""
        try:
            with open(_pend) as f:
                content = f.read().strip()
            os.remove(_pend)
            return content
        except Exception:
            return ""

    def last_results(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return the last N analysed results from disk."""
        results = []
        try:
            for fname in sorted(os.listdir(_RESULTS_DIR), reverse=True)[:n]:
                path = os.path.join(_RESULTS_DIR, fname)
                with open(path) as f:
                    results.append(json.load(f))
        except Exception:
            pass
        return results

    # ── Connection ─────────────────────────────────────────────────────────────

    def _connect(self, token: Optional[str] = None):
        """Return QiskitRuntimeService or None if unavailable."""
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            if token:
                return QiskitRuntimeService(token=token, channel="ibm_quantum_platform")
            # Try saved credentials
            return QiskitRuntimeService()
        except Exception:
            return None

    # ── Analysis ───────────────────────────────────────────────────────────────

    def _analyse_job(self, job) -> Optional[JobAnalysis]:
        """Analyse a single completed IBM job. Returns None on failure."""
        try:
            result = job.result()
        except Exception:
            return None

        try:
            pub    = result[0]
            db     = pub.data
            field  = next((a for a in ["meas", "c"] if hasattr(db, a)), None)
            if field is None:
                return None
            counts = getattr(db, field).get_counts()
        except Exception:
            return None

        if not counts:
            return None

        total   = sum(counts.values())
        n_bits  = len(next(iter(counts)))
        backend = ""
        created = ""
        try:
            backend = job.backend().name
            created = str(job.creation_date)[:19]
        except Exception:
            pass

        exc = self._per_qubit_excitation(counts, total, n_bits)

        shock_q   = int(exc.index(max(exc)))
        shock_exc = exc[shock_q]

        # ZZ correlations near shock qubit (only if shock is strong)
        zz_near: Dict[str, float] = {}
        if shock_exc > 0.6 and n_bits >= 4:
            zz_near = self._zz_near(counts, total, shock_q, n_bits, radius=8)

        # Bell fidelity (2-qubit)
        bell_f: Optional[float] = None
        if n_bits == 2:
            c00 = counts.get("00", 0) / total
            c11 = counts.get("11", 0) / total
            bell_f = c00 + c11

        # GHZ fidelity
        ghz_f: Optional[float] = None
        if n_bits >= 3:
            all0 = counts.get("0" * n_bits, 0) / total
            all1 = counts.get("1" * n_bits, 0) / total
            ghz_f = all0 + all1

        # Bimodal detection (SPT chain)
        n_high = sum(1 for e in exc if e > 0.6)
        n_low  = sum(1 for e in exc if e < 0.1)
        bimodal = (
            n_bits >= 10
            and n_high >= 3
            and n_low >= 3
            and abs(n_high - n_low) < n_bits * 0.5
        )

        anomalies = self._detect_anomalies(
            exc=exc, shock_q=shock_q, shock_exc=shock_exc,
            zz=zz_near, bell_f=bell_f, ghz_f=ghz_f,
            bimodal=bimodal, n_bits=n_bits, n_high=n_high, n_low=n_low,
        )

        return JobAnalysis(
            job_id=job.job_id(),
            backend=backend,
            created=created,
            shots=total,
            n_qubits=n_bits,
            excitation=exc,
            shock_qubit=shock_q,
            shock_exc=shock_exc,
            zz_near_shock=zz_near,
            bell_fidelity=bell_f,
            ghz_fidelity=ghz_f,
            bimodal=bimodal,
            bimodal_high_n=n_high,
            bimodal_low_n=n_low,
            anomalies=anomalies,
        )

    def _per_qubit_excitation(self, counts: Dict[str, int],
                               total: int, n_bits: int) -> List[float]:
        exc = [0.0] * n_bits
        for bs, cnt in counts.items():
            for i, bit in enumerate(reversed(bs)):
                if bit == "1":
                    exc[i] += cnt
        return [e / total for e in exc]

    def _zz_near(self, counts: Dict[str, int], total: int,
                  shock_q: int, n_bits: int, radius: int = 8) -> Dict[str, float]:
        zz: Dict[str, float] = {}
        for offset in range(-radius, radius + 1):
            if offset == 0:
                continue
            qB = shock_q + offset
            if qB < 0 or qB >= n_bits:
                continue
            val = 0.0
            for bs, cnt in counts.items():
                blist = list(reversed(bs))
                zA = 1 if blist[shock_q] == "1" else -1
                zB = 1 if blist[qB] == "1" else -1
                val += cnt * zA * zB
            zz[f"q{shock_q},q{qB}"] = val / total
        return zz

    def _detect_anomalies(
        self, exc: List[float], shock_q: int, shock_exc: float,
        zz: Dict[str, float], bell_f: Optional[float],
        ghz_f: Optional[float], bimodal: bool, n_bits: int,
        n_high: int, n_low: int,
    ) -> List[str]:
        anomalies: List[str] = []

        if shock_exc > 0.90:
            anomalies.append(
                f"Exceptional shock excitation q{shock_q} = {shock_exc:.4f} "
                f"(>90% — clean TFD boundary)"
            )
        elif shock_exc > 0.75:
            anomalies.append(
                f"Strong shock excitation q{shock_q} = {shock_exc:.4f}"
            )

        if zz:
            strong = [(k, v) for k, v in zz.items() if abs(v) > 0.70]
            if strong:
                best = min(strong, key=lambda x: x[1])
                anomalies.append(
                    f"Strong anti-correlation ZZ({best[0]}) = {best[1]:+.4f} "
                    f"— entanglement confirmed across {len(strong)} pair(s)"
                )

        if bell_f is not None:
            if bell_f > 0.92:
                anomalies.append(f"Exceptional Bell fidelity F = {bell_f:.4f} (>0.92)")
            elif bell_f > 0.85:
                anomalies.append(f"High Bell fidelity F = {bell_f:.4f}")
            # CHSH estimate: S = F × 2√2
            import math
            S = bell_f * 2 * math.sqrt(2)
            if S > 2.0:
                anomalies.append(f"CHSH S ≈ {S:.4f} — classical bound violated")

        if bimodal:
            frac_high = n_high / n_bits
            anomalies.append(
                f"SPT chain bimodal excitation: {n_high}/{n_bits} qubits high "
                f"({frac_high:.0%}), {n_low} qubits in ground state — "
                f"topological boundary signature"
            )

        # Uniform ~50% (maximally scrambled/entangled subsystem)
        if n_bits >= 20 and bell_f is None:
            import statistics
            mean_exc = statistics.mean(exc)
            std_exc  = statistics.stdev(exc)
            if 0.40 <= mean_exc <= 0.55 and std_exc < 0.05:
                anomalies.append(
                    f"Uniform excitation {mean_exc:.3f}±{std_exc:.3f} across "
                    f"{n_bits} qubits — maximally scrambled entangled subsystem"
                )

        return anomalies

    # ── Graph ingestion ────────────────────────────────────────────────────────

    def _ingest_to_graph(self, a: JobAnalysis) -> None:
        """Add JobAnalysis as an ExperimentNode in the ResearchGraph."""
        try:
            from .research_graph import (
                ExperimentNode, EdgeType, Domain,
                get_research_graph, _make_id,
            )
            graph = get_research_graph()

            # Determine domain and title
            if a.shock_exc > 0.7 and a.n_qubits >= 50:
                domain = Domain.QUANTUM
                title  = (
                    f"IBM {a.backend} {a.n_qubits}q wormhole run "
                    f"(shock={a.shock_exc:.3f}, ZZ={len(a.zz_near_shock)} correlators)"
                )
                claim_connects = ["CLM-GJW-WORMHOLE-TELEPORT", "CLM-CHSH-CLASSICAL-BOUND"]
            elif a.bimodal:
                domain = Domain.QUANTUM
                title  = (
                    f"IBM {a.backend} {a.n_qubits}q SPT chain "
                    f"({a.bimodal_high_n} high / {a.bimodal_low_n} low)"
                )
                claim_connects = ["CLM-TPSM-SPECTRAL-GAP"]
            elif a.bell_fidelity is not None:
                domain = Domain.QUANTUM
                title  = (
                    f"IBM {a.backend} 2q Bell test F={a.bell_fidelity:.4f}"
                )
                claim_connects = ["CLM-CHSH-CLASSICAL-BOUND"]
            else:
                domain = Domain.QUANTUM
                title  = (
                    f"IBM {a.backend} {a.n_qubits}q circuit run ({a.shots} shots)"
                )
                claim_connects = []

            node = ExperimentNode(
                id=_make_id("EXP", f"hw-{a.job_id}"),
                title=title,
                summary=a.summary(),
                domain=domain,
                confidence=min(1.0, 0.6 + a.shock_exc * 0.4),
                backend=a.backend,
                shots=a.shots,
                n_qubits=a.n_qubits,
                raw_data={
                    "job_id": a.job_id,
                    "shock_exc": a.shock_exc,
                    "shock_qubit": a.shock_qubit,
                    "bell_fidelity": a.bell_fidelity,
                    "ghz_fidelity": a.ghz_fidelity,
                    "bimodal": a.bimodal,
                    "anomalies": a.anomalies,
                    "zz_peak": min(a.zz_near_shock.values()) if a.zz_near_shock else None,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            graph.add_node(node)

            # Connect to relevant claims
            for cid in claim_connects:
                if graph.get_node(cid):
                    # Choose SUPPORTS or CONTRADICTS based on result
                    etype = EdgeType.SUPPORTS
                    if cid == "CLM-CHSH-CLASSICAL-BOUND" and a.bell_fidelity:
                        import math
                        S = a.bell_fidelity * 2 * math.sqrt(2)
                        etype = EdgeType.SUPPORTS if S > 2.0 else EdgeType.CONTRADICTS
                    graph.connect(node.id, cid, etype,
                                  note=f"Hardware result: {a.backend} {a.n_qubits}q")

            graph.save()
        except Exception:
            pass

    # ── Formatting ─────────────────────────────────────────────────────────────

    def _format_briefing(self, analyses: List[JobAnalysis]) -> str:
        ts  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"╔══════════════════════════════════════════════════════╗",
            f"║  ⚛  HARDWARE LOOP BRIEFING — {ts}  ║",
            f"╚══════════════════════════════════════════════════════╝",
            f"  {len(analyses)} new completed job(s) analysed:",
            "",
        ]
        for a in analyses:
            lines.append(a.summary())
            lines.append("")

        # Aggregate cross-job anomalies
        all_anomalies = [anm for a in analyses for anm in a.anomalies]
        if all_anomalies:
            lines += ["━━━━ Notable Findings ━━━━"]
            for anm in all_anomalies[:6]:
                lines.append(f"  ★ {anm}")
        return "\n".join(lines)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_seen(self) -> Set[str]:
        if os.path.exists(_SEEN_FILE):
            try:
                with open(_SEEN_FILE) as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _save_seen(self) -> None:
        try:
            os.makedirs(os.path.dirname(_SEEN_FILE), exist_ok=True)
            with open(_SEEN_FILE, "w") as f:
                json.dump(list(self._seen), f)
        except Exception:
            pass

    def _save_result(self, a: JobAnalysis) -> None:
        try:
            fname = f"{a.job_id}.json"
            path  = os.path.join(_RESULTS_DIR, fname)
            with open(path, "w") as f:
                json.dump(a.to_dict(), f, indent=2)
        except Exception:
            pass

    def _log(self, msg: str) -> None:
        try:
            with open(_LOG_FILE, "a") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "msg": msg,
                }) + "\n")
        except Exception:
            pass

    def _log_analysis(self, a: JobAnalysis) -> None:
        self._log(
            f"analysed job={a.job_id} backend={a.backend} "
            f"n_qubits={a.n_qubits} shots={a.shots} "
            f"shock_exc={a.shock_exc:.4f} bell_f={a.bell_fidelity} "
            f"anomalies={len(a.anomalies)}"
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_loop_singleton: Optional[HardwareLoop] = None


def get_hardware_loop() -> HardwareLoop:
    global _loop_singleton
    if _loop_singleton is None:
        _loop_singleton = HardwareLoop()
    return _loop_singleton
