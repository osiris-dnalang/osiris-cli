"""The OSIRIS pipeline, layer by layer, as it exists in code today.

The evidence-governed architecture (intake, intent, orchestration, evidence,
candidates, verification, benchmarks, promotion, ledger) mapped onto the
modules that implement each layer, with each layer's state read from a real
check: a file on disk, a hash chain recomputed, a backend reached. Where no
code implements part of a layer yet, it is listed as not built rather than
drawn as running. Shown compactly at startup and in full by /architecture.

Governing principle: every improvement is a versioned experiment, not an
accepted fact -- proposal, test, critique, benchmark, audit, then promote,
quarantine or reject, and record it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

PRINCIPLE = ("proposal → test → critique → benchmark → audit → "
             "promote / quarantine / reject → ledger")


@dataclass(frozen=True)
class Layer:
    key: str
    name: str
    built: Tuple[Tuple[str, str], ...]   # (what, where: module · command)
    missing: Tuple[str, ...] = ()


LAYERS = (
    Layer("L0", "Intake", (
        ("hash-chained exchange log", "osiris_cli/living.py · ~/.osiris/living/exchanges.jsonl"),
        ("governed intake: records every exchange; learns only from eligible material you explicitly approve",
         "osiris_cli/paste_learning.py · osiris_cli/living.py · osiris_cli/osiris_repl.py"),
        ("a paste is one message, however the terminal splits it", "bracketed paste · living.keys_typed"),
        ("long pastes go to the model as a bounded excerpt", "living.Osiris.excerpt"),
        ("what changed since the last session", "session_state.py"),
    ), ("a run ID per task carrying its permissions and budget",)),
    Layer("L1", "Intent", (
        ("intent classifier: code rules, no model", "intent_router.py · /intent"),
        ("intent card of fixed next steps", "osiris_termux_console._route"),
        ("greetings and thanks answered by code, instantly", "living.Osiris._small_talk_reply"),
    ), ("a risk tier and cost-of-a-wrong-answer estimate per request",)),
    Layer("L2", "Orchestrate", (
        ("next best action from fixed rules over real state", "osiris_termux_console._next_best · /home"),
        ("sprint backlog: plan, execute with k attempts, review", "sprint_manager.py · /sprint"),
        ("a person approves every workspace write", "/apply · /discard"),
    ), ("per-task budgets and stop conditions",)),
    Layer("L3", "Evidence", (
        ("claims register: verdicts answered by code before any model", "osiris_cli/claims.py · /legit"),
        ("a named experiment's recorded verdict, stated by code first", "knowledge.Knowledge.on_record"),
        ("notes from your docs, cited by file", "osiris_cli/knowledge.py"),
        ("facts you asked OSIRIS to keep", "/remember · /forget"),
        ("research lab: sources, concept map, hypotheses", "research.py · /lab"),
    ), ("a provenance record for each claim made in a reply",)),
    Layer("L4", "Propose", (
        ("Architect: intent → spec", "Ollama · osiris_termux_console.CHAT_MODEL"),
        ("draft proposer: spec → candidate code (unpromoted assistant)", "osiris_termux_console._synthesize"),
        ("mentor voice, warmed at start-up, fast voice for long messages", "living.OllamaMentor"),
        ("experiment brief, simulator first", "/experiment"),
    ), ("baseline, alternative and conservative candidates side by side",)),
    Layer("L5", "Verify", (
        ("sandboxed test run after a static AST check", "osiris_termux_console._run_sandboxed_test · /why"),
        ("placeholder gate rejects stub code", "payload_gate.py"),
        ("physics checks: bounds and unit sanity", "osiris_cli/physics_checks.py · /physics"),
        ("read-only probes: trainer, git, ledger, system, evidence", "osiris_cli/probes.py"),
    ), ("an independent critic that tries to falsify a candidate",)),
    Layer("L6", "Benchmark", (
        ("bench ledger with hashed artifacts", "protege.py · /bench · /mentors"),
        ("paired pre/post scoring of the core on held-out exchanges", "osiris_cli/prepost.py"),
    ), ("calibration: stated confidence against measured correctness",)),
    Layer("L7", "Promote", (
        ("speaking gate: the core answers only after earning it on held-out text", "living.Osiris.gate"),
        ("/apply fails closed and can be blocked persistently", "osiris_termux_console._apply_pending_write"),
        ("gap drafts do nothing until activated", "gaps.py · /gaps"),
    ), ("a quarantine queue for inconclusive candidates",)),
    Layer("L8", "Ledger", (
        ("genome ledger: dnalang hash chain", "genome_ledger.py · ~/.osiris/genome_ledger.jsonl"),
        ("write-once run records with artifact hashes", "run_record.py · /runs"),
    ), ("failure-pattern clustering across the ledgers",)),
)

SUBSYSTEMS = (
    ("Physics research", (
        ("bounds checks on a claimed number", "/physics"),
        ("claim verdicts with their evidence", "/legit"),
    ), ("formal model builder (variables, units, symmetries)", "prediction against the standard-theory value")),
    ("Quantum research", (
        ("simulator-first experiment brief", "/experiment"),
        ("ledger row written before any IBM submission", "dnalang-core backends/ibm.py"),
        ("Aer ground truth for decoupling search", "bridge/noise.py"),
    ), ("a hardware-readiness gate in OSIRIS (resource model, noise sensitivity sweep)",)),
)


def _safe(fn: Callable[[], Tuple[str, str]]) -> Tuple[str, str]:
    """A probe that fails says so; it never stops the screen from drawing."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return "review", f"check failed ({type(e).__name__})"


def live_state(living=None, console=None) -> Dict[str, Tuple[str, str]]:
    """(marker kind, one line) per layer, each from a check that reads disk or a
    backend. `living` is the Osiris you talk to; `console` is osiris_termux_console."""
    state: Dict[str, Tuple[str, str]] = {}

    def l0():
        from osiris_cli.probes import verify_chain
        if living is None:
            return "idle", "exchange log unavailable"
        c = verify_chain(living.log_path)
        if not c["intact"]:
            return "blocked", f"exchange log BROKEN at entry {c.get('broken_at', '?')}"
        return "verified", f"{c['entries']} exchanges, hash chain intact"

    def l1():
        return "current", "code rules decide the route; no model"

    def l2():
        if console is None:
            return "idle", "console unavailable"
        pending = console._pending_write["path"]
        nb = console._next_best()
        return ("review", f"a write to {pending} awaits /apply") if pending else \
            ("current", f"next: {nb['label']}")

    def l3():
        from osiris_cli import claims
        parts = [f"{len(claims.REGISTER)} registered claims"]
        if living is not None and living.knowledge is not None:
            parts.append(f"{len(living.knowledge.texts)} note files")
        if living is not None:
            parts.append(f"{len(living.facts())} kept facts")
        if console is not None:
            parts.append(f"{len(console.research.sources())} lab sources")
        return "verified", " · ".join(parts)

    def l4():
        if console is None:
            return "idle", "console unavailable"
        ok, _ = console._check_ollama_reachable(timeout=0.5)
        voice = living.mentor.model() if living is not None and ok else None
        fast = getattr(living.mentor, "fast_model", lambda: None)() if voice else None
        text = (f"Architect {console.CHAT_MODEL} · draft proposer {console._synth_chain()} (unpromoted) · "
                f"voice {voice or 'none'}{f' (fast: {fast})' if fast and fast != voice else ''}")
        return ("verified", text) if ok else ("review", "ollama UNREACHABLE: " + text)

    def l5():
        return "current", "deterministic, no model · no independent critic yet"

    def l6():
        if console is None:
            return "idle", "console unavailable"
        _kind, line = console._integrity()
        bench = next((p for p in line.split(" · ") if p.startswith("bench evidence")), None)
        if bench is None:
            return "idle", "no bench runs recorded"
        return ("verified" if "files verified" in bench else "blocked"), bench

    def l7():
        if living is None:
            return "idle", "core unavailable"
        g = living.gate()
        return ("verified" if g["open"] else "idle"), \
            f"NCLM core step {living._core_step()}: {living.gate_note(g)}"

    def l8():
        import genome_ledger
        if not os.path.exists(genome_ledger.DEFAULT_PATH):
            return "idle", "genome ledger empty"
        led = genome_ledger.GenomeLedger()
        problem, n = led.problem(), len(led.chain)
        if problem:
            return "blocked", f"genome ledger BROKEN ({n} entries): {problem} -- see /architecture"
        return "verified", f"genome ledger valid, {n} entries"

    for key, fn in (("L0", l0), ("L1", l1), ("L2", l2), ("L3", l3), ("L4", l4),
                    ("L5", l5), ("L6", l6), ("L7", l7), ("L8", l8)):
        state[key] = _safe(fn)
    return state


def compact(canvas, state: Dict[str, Tuple[str, str]]) -> str:
    """The startup panel: one row per layer, its state from live_state()."""
    import osiris_ui
    inner = osiris_ui.Canvas(canvas.mode, canvas.cols - 4)
    rows = [(state[ly.key][0], f"{ly.key} {ly.name}", state[ly.key][1]) for ly in LAYERS]
    lines = inner.facts(rows).split("\n")
    lines += ["", inner.dim("/architecture: what implements each layer, and what is not built yet")]
    return canvas.panel("PIPELINE · models propose, code decides", lines)


def full(canvas, state: Dict[str, Tuple[str, str]], ledger_detail: Optional[List[str]] = None) -> str:
    """/architecture: every layer's components, where they live, what is missing."""
    import osiris_ui
    inner = osiris_ui.Canvas(canvas.mode, canvas.cols - 4)
    lines: List[str] = [inner.dim(PRINCIPLE), ""]

    def parts(built, missing):
        out = []
        for what, where in built:
            out += inner._wrap(f"{inner.marker('passed')} {what} -- {where}", inner.cols - 6, indent=5)
        for what in missing:
            out += inner._wrap(f"{inner.marker('idle')} not built: {what}", inner.cols - 6, indent=5)
        return ["     " + p for p in out]

    for layer in LAYERS:
        kind, text = state[layer.key]
        lines += inner.facts([(kind, f"{layer.key} {layer.name}", text)]).split("\n")
        if layer.key == "L8" and ledger_detail:
            for para in ledger_detail:
                lines += ["       " + inner.dim(w) for w in inner._wrap(para, inner.cols - 8)]
        lines += parts(layer.built, layer.missing) + [""]
    for name, built, missing in SUBSYSTEMS:
        lines.append(" " + inner.style(name, "1"))
        lines += parts(built, missing) + [""]
    return canvas.panel("ARCHITECTURE · as built", lines[:-1])


def ledger_detail() -> List[str]:
    """When the genome ledger is broken: which entry, and what it would take."""
    import genome_ledger
    if not os.path.exists(genome_ledger.DEFAULT_PATH):
        return []
    led = genome_ledger.GenomeLedger()
    problem = led.problem()
    if not problem:
        return []
    why = ("its hash does not re-derive with the ledger's rule (sha256 of prev + canonical "
           "body), so it was written or edited outside GenomeLedger.append." if "hash mismatch" in problem
           else "its prev field does not match the entry before it.")
    return [f"{problem}: {why}",
            f"File: {genome_ledger.DEFAULT_PATH}. Nothing is repaired automatically: re-hashing "
            "or appending a correction record is your decision, made with the file open."]
