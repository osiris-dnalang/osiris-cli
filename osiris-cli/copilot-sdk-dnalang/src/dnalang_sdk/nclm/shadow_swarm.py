"""
OSIRIS Shadow Swarm — Code Completion Engine.

When Claude writes code, this runs behind it.
Not to undo — to finish.

Roles:
  complete   — fill stubs/TODOs with real implementations
  test       — write pytest coverage for every function
  document   — add/improve docstrings and module docs
  harden     — add input validation, error handling, edge cases
  integrate  — wire the file into the sprint (imports, __init__.py, etc.)

Each role is a separate LLM pass on the file.
Runs in a background thread — never blocks the main session.
All changes logged to PCRB ledger.
Definition of Done tracked per file.

The apprentice (nclm/apprentice.py) observes every swarm action and
records Claude's orchestration patterns as training data.

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from __future__ import annotations

import os
import re
import json
import time
import hashlib
import heapq
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone

_HOME = os.path.expanduser("~")
_SWARM_LOG   = os.path.join(_HOME, ".osiris", "swarm_log.jsonl")
_SWARM_STATE = os.path.join(_HOME, ".osiris", "swarm_state.json")
_RATE_DELAY  = 2.5     # seconds between LLM calls to avoid hammering
_MAX_QUEUE   = 48      # max queued tasks

# ANSI
_R  = "\033[0m"
_H  = "\033[1m"
_D  = "\033[2m"
_CY = "\033[96m"
_MG = "\033[95m"
_GR = "\033[92m"
_YE = "\033[93m"
_RD = "\033[91m"


# ── Definition of Done ─────────────────────────────────────────────────────────

@dataclass
class DoDScore:
    file_path: str
    has_module_docstring: bool = False
    has_function_docstrings: bool = False
    has_type_hints: bool = False
    has_tests: bool = False
    no_bare_stubs: bool = False
    has_error_handling: bool = False
    score: float = 0.0
    missing: List[str] = field(default_factory=list)


def score_file(file_path: str) -> DoDScore:
    """Compute Definition-of-Done score for a Python file."""
    result = DoDScore(file_path=file_path)
    try:
        text = Path(file_path).read_text()
    except Exception:
        return result

    lines = text.splitlines()
    # Module docstring: first non-empty non-comment line is a string
    stripped = [l.strip() for l in lines if l.strip()]
    result.has_module_docstring = bool(stripped and stripped[0].startswith(('"""', "'''")))

    # Function docstrings: every def followed within 3 lines by a docstring
    defs = [i for i, l in enumerate(lines) if re.match(r'^\s*(def |async def )\w+', l)]
    if defs:
        defs_with_docs = sum(
            1 for i in defs
            if any('"""' in lines[j] or "'''" in lines[j]
                   for j in range(i + 1, min(i + 4, len(lines))))
        )
        result.has_function_docstrings = defs_with_docs >= len(defs) * 0.6
    else:
        result.has_function_docstrings = True  # no functions — not a problem

    # Type hints: at least half of defs have -> or : annotation
    typed_defs = sum(1 for i in defs if '->' in lines[i] or ': ' in lines[i])
    result.has_type_hints = (not defs) or (typed_defs >= len(defs) * 0.5)

    # Tests: companion test file exists
    base = Path(file_path)
    test_candidates = [
        base.parent.parent / "tests" / f"test_{base.name}",
        base.parent / f"test_{base.name}",
        base.parent.parent / "tests" / f"test_{base.stem}_test.py",
    ]
    result.has_tests = any(p.exists() for p in test_candidates)

    # No bare stubs: no `pass` or `raise NotImplementedError` or `# TODO`
    stub_lines = [l for l in lines if re.search(
        r'^\s*pass\s*$|raise NotImplementedError|#\s*TODO', l
    )]
    result.no_bare_stubs = len(stub_lines) == 0

    # Error handling: has try/except or explicit ValueError/TypeError raises
    result.has_error_handling = bool(re.search(r'\btry\b|\bexcept\b|raise \w+Error', text))

    # Score
    criteria = [
        result.has_module_docstring,
        result.has_function_docstrings,
        result.has_type_hints,
        result.has_tests,
        result.no_bare_stubs,
        result.has_error_handling,
    ]
    result.score = sum(criteria) / len(criteria)

    names = [
        "module_docstring", "function_docstrings", "type_hints",
        "tests", "no_stubs", "error_handling",
    ]
    result.missing = [n for n, c in zip(names, criteria) if not c]
    return result


# ── Swarm Task ─────────────────────────────────────────────────────────────────

@dataclass
class SwarmTask:
    role: str           # complete | test | document | harden | integrate
    file_path: str
    intent: str         # what the code is supposed to do (from user message)
    sprint_id: str = ""
    priority: int = 5   # 1=high, 10=low (lower = more urgent)
    queued_at: float = field(default_factory=time.time)
    task_id: str = field(default_factory=lambda: hashlib.md5(
        f"{time.time()}".encode()).hexdigest()[:8])
    status: str = "pending"   # pending | running | done | failed | skipped
    result_path: str = ""
    error: str = ""
    # CRSM / Fdna fields
    fdna: float = 0.5   # DNA-Lang Fidelity score (lower = higher urgency)
    lambda_coherence: float = 0.5
    gamma_decoherence: float = 0.1
    phi_consciousness: float = 0.5
    dod_before: float = 0.0
    dod_after: float = 0.0

    # Heap comparison (min-heap on priority, tie-break on queued_at)
    def __lt__(self, other: "SwarmTask") -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.queued_at < other.queued_at


# ── Agent prompts ──────────────────────────────────────────────────────────────

_PROMPTS: Dict[str, str] = {
    "complete": """\
You are a code completion agent in the OSIRIS swarm.
The file below was partially written. Your mission:
  1. Replace every `pass`, stub, or `# TODO` with a real implementation
  2. Complete any function whose body is clearly incomplete
  3. Do NOT remove any existing working code
  4. Do NOT change function signatures or public interfaces
  5. Keep the same style and naming conventions

Original intent: {intent}

Return ONLY the complete Python file. No explanation. No fences.
---FILE---
{content}
""",

    "test": """\
You are a test-writing agent in the OSIRIS swarm.
Write a comprehensive pytest test file for the module below.
Cover:
  - Happy path for every public function
  - Edge cases: None input, empty collections, boundary values
  - Error/exception conditions
  - At minimum 1 test per public function

Use pytest fixtures where sensible. Mock external I/O.
File being tested: {file_path}

Return ONLY the Python test file. No explanation. No fences.
---FILE---
{content}
""",

    "document": """\
You are a documentation agent in the OSIRIS swarm.
Improve the documentation in this file:
  1. Add/improve the module-level docstring (purpose, usage, key classes)
  2. Add docstrings to every function/class that lacks one
  3. Add inline comments for non-obvious logic
  4. Do NOT change any logic or function signatures

Return ONLY the improved Python file. No explanation. No fences.
---FILE---
{content}
""",

    "harden": """\
You are a defensive coding agent in the OSIRIS swarm.
Make this code production-grade:
  1. Validate inputs at function boundaries (None checks, type checks, range checks)
  2. Add try/except with specific, meaningful error messages where I/O or parsing occurs
  3. Handle empty/None returns from called functions
  4. Do NOT change the happy-path logic
  5. Add logging statements for key failure paths (use standard logging module)

Return ONLY the hardened Python file. No explanation. No fences.
---FILE---
{content}
""",

    "integrate": """\
You are a project integration agent in the OSIRIS swarm.
Given this new file in the project, update the package __init__.py
to export the key classes/functions it defines.
List the exact lines to add to __init__.py (not the whole file — just the additions).

File: {file_path}
---FILE---
{content}
""",
}


def _llm(prompt: str) -> str:
    try:
        from .tools import tool_llm
        return tool_llm(prompt)
    except Exception:
        return ""


# ── Individual agent runner ────────────────────────────────────────────────────

class SwarmAgent:
    """Runs one LLM pass on a file to fulfill one role."""

    def run(self, task: SwarmTask) -> Tuple[bool, str]:
        """
        Execute the swarm task.
        Returns (success, result_summary).
        Writes result to disk if applicable.
        """
        try:
            content = Path(task.file_path).read_text()
        except Exception as e:
            return False, f"Cannot read {task.file_path}: {e}"

        template = _PROMPTS.get(task.role, "")
        if not template:
            return False, f"Unknown role: {task.role}"

        prompt = template.format(
            intent=task.intent or "unknown",
            file_path=task.file_path,
            content=content[:6000],  # context budget
        )

        result = _llm(prompt)
        if not result or len(result) < 30:
            return False, "LLM returned empty response"

        # Clean up fences if LLM added them anyway
        result = re.sub(r'^```(?:python)?\s*\n', '', result, flags=re.MULTILINE)
        result = re.sub(r'\n```\s*$', '', result, flags=re.MULTILINE)

        if task.role == "test":
            # Write to tests/ directory
            base = Path(task.file_path)
            tests_dir = base.parent.parent / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            test_path = tests_dir / f"test_{base.name}"
            test_path.write_text(result)
            task.result_path = str(test_path)
            return True, f"Tests → {test_path}"

        elif task.role == "integrate":
            # Write as a note — don't auto-modify __init__.py
            note_path = Path(task.file_path).parent / ".swarm_integrate_note.txt"
            note_path.write_text(f"# SWARM INTEGRATION SUGGESTIONS\n# {task.file_path}\n\n{result}")
            task.result_path = str(note_path)
            return True, f"Integration note → {note_path}"

        else:
            # Overwrite the file with improved version
            # Only write if result looks like real code (has def/class/import)
            if not re.search(r'\bdef \b|\bclass \b|\bimport \b', result):
                return False, "Result doesn't look like Python code — skipped"
            Path(task.file_path).write_text(result)
            task.result_path = task.file_path
            return True, f"{task.role} pass applied → {Path(task.file_path).name}"

        return False, "Unknown outcome"


# ── Shadow Swarm Orchestrator ──────────────────────────────────────────────────

class ShadowSwarm:
    """
    Background swarm that watches code writes and completes them.

    Usage:
        swarm = get_swarm()
        swarm.observe(file_path, intent)   # after Claude writes a file
        swarm.status()                      # see queue
    """

    # Roles to run per file type, in priority order
    _ROLE_SEQUENCE = ["complete", "document", "harden", "test"]

    def __init__(self):
        self._heap: List[SwarmTask] = []   # min-heap (priority, queued_at)
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._agent = SwarmAgent()
        self._completed: List[SwarmTask] = []
        os.makedirs(os.path.dirname(_SWARM_LOG), exist_ok=True)
        self._load_state()

    @staticmethod
    def compute_priority(fdna: float, dod_score: float, role: str) -> int:
        """
        Compute task priority from Fdna and DoD score.

        Lower priority number = higher urgency (min-heap).
        Fdna < 0.1 (severe decoherence) → priority 1
        Fdna 0.1-0.3 (degraded)         → priority 2
        Fdna 0.3-0.6 (normal)           → priority 3-4
        Fdna > 0.6   (healthy)          → priority 5

        DoD score penalty: very incomplete files (DoD < 0.3) boost priority.
        Role bump: 'complete' always gets priority 1 if Fdna is low.
        """
        # Map fdna to base priority
        if fdna < 0.1:
            base = 1
        elif fdna < 0.3:
            base = 2
        elif fdna < 0.5:
            base = 3
        else:
            base = 4

        # DoD penalty: boost priority for very incomplete files
        if dod_score < 0.3:
            base = max(1, base - 1)

        # Role: complete is most urgent
        if role == "complete" and base > 2:
            base -= 1

        return min(base, 5)

    def reprioritize(self):
        """
        Recompute Fdna for all queued tasks and rebuild the heap.
        Called by the reprioritize daemon thread.
        """
        try:
            from .swarm_brain import crsm_from_file, compute_fdna
        except ImportError:
            return

        with self._lock:
            tasks = list(self._heap)
            self._heap.clear()

        updated = []
        for task in tasks:
            try:
                if os.path.exists(task.file_path):
                    crsm = crsm_from_file(task.file_path)
                    task.fdna = compute_fdna(crsm)
                    task.lambda_coherence = crsm.lambda_coherence
                    task.gamma_decoherence = crsm.gamma_decoherence
                    task.phi_consciousness = crsm.phi_consciousness
                    dod = score_file(task.file_path)
                    task.priority = self.compute_priority(
                        task.fdna, dod.score, task.role)
                updated.append(task)
            except Exception:
                updated.append(task)

        with self._lock:
            for task in updated:
                heapq.heappush(self._heap, task)

    # Queue size property for backward compat
    @property
    def _queue(self) -> List[SwarmTask]:
        """Read-only view of the heap (for status/dod methods)."""
        return list(self._heap)

    # ── Public API ─────────────────────────────────────────────────────────────

    def observe(self, file_path: str, intent: str = "", sprint_id: str = "",
                roles: Optional[List[str]] = None):
        """
        Called every time Claude writes or edits a file.
        Queues swarm tasks to complete, document, test, and harden it.
        """
        if not file_path.endswith('.py'):
            return  # Only handle Python files for now

        if not os.path.exists(file_path):
            return

        use_roles = roles or self._ROLE_SEQUENCE

        # Score current DoD to determine what's actually needed
        dod = score_file(file_path)
        role_needed = {
            "complete":  not dod.no_bare_stubs,
            "document":  not dod.has_function_docstrings or not dod.has_module_docstring,
            "harden":    not dod.has_error_handling,
            "test":      not dod.has_tests,
            "integrate": False,  # opt-in only
        }

        # Compute Fdna for priority assignment
        fdna = 0.5
        crsm_lambda = 0.5
        crsm_gamma = 0.1
        crsm_phi = 0.5
        try:
            from .swarm_brain import crsm_from_file, compute_fdna
            crsm = crsm_from_file(file_path)
            fdna = compute_fdna(crsm)
            crsm_lambda = crsm.lambda_coherence
            crsm_gamma = crsm.gamma_decoherence
            crsm_phi = crsm.phi_consciousness
        except Exception:
            pass

        with self._lock:
            queued = 0
            for role in use_roles:
                if len(self._heap) >= _MAX_QUEUE:
                    break
                if not role_needed.get(role, True):
                    continue  # already done — skip
                prio = self.compute_priority(fdna, dod.score, role)
                task = SwarmTask(
                    role=role,
                    file_path=file_path,
                    intent=intent,
                    sprint_id=sprint_id,
                    priority=prio,
                    fdna=fdna,
                    lambda_coherence=crsm_lambda,
                    gamma_decoherence=crsm_gamma,
                    phi_consciousness=crsm_phi,
                    dod_before=dod.score,
                )
                heapq.heappush(self._heap, task)
                queued += 1

        if queued:
            self._print(f"◌ Swarm queued {queued} task(s) for {Path(file_path).name} "
                        f"[DoD {dod.score:.0%}] missing: {', '.join(dod.missing)}")
            self._ensure_running()

    def observe_sprint(self, sprint_path: str, intent: str = "", sprint_id: str = ""):
        """Queue swarm tasks for all Python files in a sprint directory."""
        count = 0
        for py_file in Path(sprint_path).rglob("*.py"):
            if ".osiris" not in str(py_file) and "test_" not in py_file.name:
                self.observe(str(py_file), intent=intent, sprint_id=sprint_id)
                count += 1
        if count:
            self._print(f"◌ Swarm observing {count} file(s) in sprint {sprint_id or sprint_path}")

    def status(self) -> str:
        """Return formatted status string."""
        with self._lock:
            q = list(self._queue)
            done = list(self._completed[-10:])

        lines = [f"  {_H}Shadow Swarm Status{_R}"]
        running = "running" if self._running else "idle"
        lines.append(f"  State: {_GR if self._running else _D}{running}{_R}  "
                     f"Queue: {len(q)}  Completed: {len(self._completed)}")

        if q:
            lines.append(f"\n  {_YE}Queued:{_R}")
            for t in q[:8]:
                age = int(time.time() - t.queued_at)
                lines.append(f"    [{t.role:10s}] {Path(t.file_path).name:<30} queued {age}s ago")

        if done:
            lines.append(f"\n  {_GR}Recent completions:{_R}")
            for t in reversed(done):
                symbol = _GR + "✓" + _R if t.status == "done" else _RD + "✗" + _R
                lines.append(f"    {symbol} [{t.role:10s}] {Path(t.file_path).name}")
                if t.result_path and t.result_path != t.file_path:
                    lines.append(f"       → {t.result_path}")

        return "\n".join(lines)

    def dod_report(self, sprint_path: Optional[str] = None) -> str:
        """Print DoD scores for all Python files in path."""
        search = Path(sprint_path) if sprint_path else Path.cwd()
        files = [f for f in search.rglob("*.py")
                 if ".osiris" not in str(f) and "test_" not in f.name]
        if not files:
            return "  No Python files found."

        lines = [f"  {_H}Definition of Done Report{_R}"]
        total_score = 0.0
        for f in sorted(files):
            dod = score_file(str(f))
            bar = "█" * int(dod.score * 10) + "·" * (10 - int(dod.score * 10))
            miss = ", ".join(dod.missing) or "complete"
            rel = f.relative_to(search) if search in f.parents else f
            lines.append(f"  {_CY}{bar}{_R} {dod.score:.0%}  {str(rel):<40} "
                         f"{_D}{miss}{_R}")
            total_score += dod.score

        avg = total_score / len(files) if files else 0
        lines.append(f"\n  {_H}Overall: {avg:.0%} done across {len(files)} files{_R}")
        return "\n".join(lines)

    def force_role(self, file_path: str, role: str, intent: str = ""):
        """Force a specific swarm role on a file regardless of DoD score."""
        task = SwarmTask(
            role=role, file_path=file_path,
            intent=intent, priority=1,
        )
        with self._lock:
            heapq.heappush(self._heap, task)
        self._ensure_running()
        self._print(f"◌ Swarm: forced {role} on {Path(file_path).name}")

    # ── Background worker ──────────────────────────────────────────────────────

    def _ensure_running(self):
        if not self._running:
            self._thread = threading.Thread(
                target=self._worker, daemon=True, name="osiris-swarm"
            )
            self._thread.start()

    def _worker(self):
        self._running = True
        try:
            while True:
                task = None
                with self._lock:
                    if self._heap:
                        task = heapq.heappop(self._heap)
                    else:
                        break

                if task is None:
                    break

                task.status = "running"
                fdna_str = f"Fdna={task.fdna:.3f}" if task.fdna != 0.5 else ""
                self._print(
                    f"  ◈ Swarm [{task.role:10s}] p={task.priority} "
                    f"{fdna_str} → {Path(task.file_path).name}"
                )

                # Snapshot DoD before
                dod_before = score_file(task.file_path)
                task.dod_before = dod_before.score

                success, summary = self._agent.run(task)
                task.status = "done" if success else "failed"

                # Snapshot DoD after
                dod_after = score_file(task.file_path)
                task.dod_after = dod_after.score

                self._log_task(task, summary)

                with self._lock:
                    self._completed.append(task)
                    if len(self._completed) > 100:
                        self._completed = self._completed[-100:]

                # Notify SwarmBrain (GA fitness recording)
                try:
                    from .swarm_brain import get_brain
                    syntax_ok = success and bool(re.search(
                        r'\bdef \b|\bclass \b', summary + " "))
                    get_brain().record_task_outcome(
                        role=task.role,
                        file_path=task.file_path,
                        status=task.status,
                        dod_before=task.dod_before,
                        dod_after=task.dod_after,
                        duration_s=time.time() - task.queued_at,
                        syntax_ok=syntax_ok,
                        has_security_checks=(task.role == "harden" and success),
                    )
                except Exception:
                    pass

                # Notify Scimitar mouse
                try:
                    from .scimitar_agent_bridge import get_bridge
                    get_bridge().signal_role_complete(task.role, success)
                except Exception:
                    pass

                # Notify apprentice
                try:
                    from .apprentice import get_apprentice
                    get_apprentice().observe_swarm_action(task, summary, success)
                except Exception:
                    pass

                if success:
                    self._print(f"  {_GR}✓{_R} Swarm [{task.role:10s}] "
                                f"DoD {task.dod_before:.0%}→{task.dod_after:.0%}  {summary}")
                else:
                    self._print(f"  {_RD}✗{_R} Swarm [{task.role:10s}] {summary}")

                time.sleep(_RATE_DELAY)

        finally:
            self._running = False
            self._save_state()

    def _print(self, msg: str):
        """Non-disruptive status print — only if a TTY is attached."""
        try:
            import sys
            if sys.stdout.isatty():
                print(f"\r{msg}", flush=True)
        except Exception:
            pass

    # ── Persistence ────────────────────────────────────────────────────────────

    def _log_task(self, task: SwarmTask, summary: str):
        record = {
            "ts": round(time.time(), 3),
            "role": task.role,
            "file": task.file_path,
            "intent": task.intent,
            "sprint_id": task.sprint_id,
            "status": task.status,
            "summary": summary,
            "task_id": task.task_id,
        }
        try:
            with open(_SWARM_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    def _save_state(self):
        try:
            state = {
                "completed_count": len(self._completed),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            with open(_SWARM_STATE, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    def _load_state(self):
        pass  # State is ephemeral per session; log is the persistent record


# ── Singleton ──────────────────────────────────────────────────────────────────

_swarm: Optional[ShadowSwarm] = None
_swarm_lock = threading.Lock()


def get_swarm() -> ShadowSwarm:
    """Get the singleton ShadowSwarm."""
    global _swarm
    with _swarm_lock:
        if _swarm is None:
            _swarm = ShadowSwarm()
    return _swarm
