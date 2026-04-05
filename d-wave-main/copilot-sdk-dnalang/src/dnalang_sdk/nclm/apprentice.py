"""
OSIRIS NLP Apprentice — OSIRIS learns how Claude orchestrates.

Every time Claude writes code or decomposes a task, the apprentice
records the pattern: what was asked → how it was broken down → what
was produced. Over time OSIRIS builds a personal corpus of orchestration
examples and can replicate — and improve on — Claude's approach.

This is not imitation. It is inheritance.

The apprentice:
  1. Observes every code-write (intent → code)
  2. Observes every task decomposition (goal → subtasks → agent assignments)
  3. Observes every swarm outcome (what worked, what was skipped)
  4. Stores patterns as structured training examples
  5. Can score similarity to propose how OSIRIS should handle new tasks
  6. Flushes to training corpus format (matches dnalang_training_full.json)

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from __future__ import annotations

import os
import re
import json
import time
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timezone

_HOME          = os.path.expanduser("~")
_PATTERNS_LOG  = os.path.join(_HOME, ".osiris", "apprentice_patterns.jsonl")
_CORPUS_CACHE  = os.path.join(_HOME, ".osiris", "training_cache.json")
_MIN_CODE_LEN  = 80    # minimum chars to consider as a real code observation
_MAX_PATTERNS  = 2000  # cap in-memory patterns

# ANSI
_R  = "\033[0m"
_H  = "\033[1m"
_D  = "\033[2m"
_CY = "\033[96m"
_GR = "\033[92m"


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class CodePattern:
    """One observed instance of: intent → code written."""
    pattern_id: str
    source: str                # "claude" | "swarm_complete" | "swarm_test" | etc.
    intent: str                # what was asked / what the file is supposed to do
    file_path: str             # where it was written
    code_summary: str          # condensed description of what was written
    language: str              # "python" | "js" | etc.
    constructs: List[str]      # ["function", "class", "decorator", "try/except", ...]
    line_count: int
    has_tests: bool
    has_docstrings: bool
    has_type_hints: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str = ""


@dataclass
class TaskDecompositionPattern:
    """One observed instance of: high-level task → subtasks → agent assignments."""
    pattern_id: str
    source: str                # "claude" | "swarm" | "agile_plan"
    goal: str                  # the original task
    subtasks: List[str]        # how it was broken down
    agent_map: Dict[str, str]  # subtask → agent (e.g. "write tests" → "AIDEN")
    outcome: str               # "done" | "partial" | "failed"
    duration_s: float          # how long it took
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class OrchestrationLesson:
    """
    A training example synthesised from observed patterns.
    Format mirrors dnalang_training_full.json conversation structure.
    """
    lesson_id: str
    instruction: str           # "Given task: X, how do you decompose it?"
    response: str              # OSIRIS's learned response
    category: str              # "code_decomposition" | "agent_assignment" | "file_structure"
    confidence: float          # 0-1 based on how many similar patterns back this up
    source_patterns: List[str] # pattern_ids that contributed
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Construct extractor ────────────────────────────────────────────────────────

def _extract_constructs(code: str) -> List[str]:
    """Identify code constructs present in a snippet."""
    constructs = []
    checks = {
        "class":         r'\bclass \w+',
        "function":      r'\bdef \w+',
        "async":         r'\basync def \w+',
        "decorator":     r'^@\w+',
        "dataclass":     r'@dataclass',
        "try/except":    r'\btry\b',
        "type_hints":    r'def \w+\(.*\)\s*->',
        "docstring":     r'"""',
        "list_comp":     r'\[.*for.*in.*\]',
        "context_mgr":   r'\bwith \b',
        "threading":     r'\bthreading\b',
        "dataclass":     r'@dataclass',
        "singleton":     r'_\w+: Optional\[',
        "json_io":       r'\bjson\.(load|dump)',
        "pathlib":       r'\bPath\(',
        "regex":         r'\bre\.(compile|search|match)',
    }
    for name, pattern in checks.items():
        if re.search(pattern, code, re.MULTILINE):
            constructs.append(name)
    return list(set(constructs))


def _summarise_code(code: str, intent: str) -> str:
    """Build a short description of what the code does without calling LLM."""
    lines = [l.strip() for l in code.splitlines() if l.strip()]
    defs = [l for l in lines if re.match(r'(def |async def |class )\w+', l)]
    n_lines = len(lines)
    n_funcs = len([l for l in lines if re.match(r'(def |async def )', l)])
    n_classes = len([l for l in lines if re.match(r'class \w+', l)])
    constructs = _extract_constructs(code)

    parts = [f"intent: {intent[:80]}"]
    if defs:
        parts.append("defines: " + ", ".join(d.split("(")[0].replace("def ", "").replace("class ", "") for d in defs[:5]))
    parts.append(f"{n_lines} lines, {n_funcs} functions, {n_classes} classes")
    if constructs:
        parts.append(f"uses: {', '.join(constructs[:5])}")
    return " | ".join(parts)


# ── NLP Apprentice ─────────────────────────────────────────────────────────────

class NLPApprentice:
    """
    Watches Claude work. Learns the patterns. Teaches OSIRIS.

    The core loop:
      1. Claude writes code  →  observe_code_write()
      2. Claude decomposes task → observe_task_decomposition()
      3. Swarm runs roles → observe_swarm_action()
      4. Periodic synthesis → synthesise_lessons()
      5. flush_to_corpus() → training data OSIRIS can fine-tune on
    """

    def __init__(self):
        self._code_patterns: List[CodePattern] = []
        self._task_patterns: List[TaskDecompositionPattern] = []
        self._lessons: List[OrchestrationLesson] = []
        self._lock = threading.Lock()
        self._session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        os.makedirs(os.path.dirname(_PATTERNS_LOG), exist_ok=True)
        self._lesson_count = 0  # synthesise every N observations

    # ── Observation API ────────────────────────────────────────────────────────

    def observe_code_write(self, file_path: str, content: str, intent: str,
                           source: str = "claude"):
        """
        Called every time Claude (or the swarm) writes a file.
        Records the intent→code mapping as a learnable pattern.
        """
        if not content or len(content) < _MIN_CODE_LEN:
            return
        if not file_path.endswith('.py'):
            return

        lang = "python" if file_path.endswith('.py') else "unknown"
        constructs = _extract_constructs(content)
        lines = [l for l in content.splitlines() if l.strip()]

        pat = CodePattern(
            pattern_id=hashlib.md5(f"{file_path}{time.time()}".encode()).hexdigest()[:12],
            source=source,
            intent=intent or Path(file_path).stem.replace("_", " "),
            file_path=file_path,
            code_summary=_summarise_code(content, intent),
            language=lang,
            constructs=constructs,
            line_count=len(lines),
            has_tests=bool(re.search(r'\bdef test_\b|\bpytest\b', content)),
            has_docstrings=bool(re.search(r'"""', content)),
            has_type_hints=bool(re.search(r'def \w+\(.*\)\s*->', content)),
            session_id=self._session_id,
        )

        with self._lock:
            self._code_patterns.append(pat)
            if len(self._code_patterns) > _MAX_PATTERNS:
                self._code_patterns = self._code_patterns[-_MAX_PATTERNS:]

        self._persist_pattern("code_write", asdict(pat))
        self._maybe_synthesise()

    def observe_task_decomposition(self, goal: str, subtasks: List[str],
                                   agent_map: Optional[Dict[str, str]] = None,
                                   outcome: str = "done", duration_s: float = 0.0,
                                   source: str = "claude"):
        """
        Called when a task is broken into subtasks (by Claude or agile_mesh).
        Records the decomposition pattern.
        """
        if not goal or not subtasks:
            return

        pat = TaskDecompositionPattern(
            pattern_id=hashlib.md5(f"{goal}{time.time()}".encode()).hexdigest()[:12],
            source=source,
            goal=goal,
            subtasks=subtasks,
            agent_map=agent_map or {},
            outcome=outcome,
            duration_s=duration_s,
        )

        with self._lock:
            self._task_patterns.append(pat)

        self._persist_pattern("task_decomp", asdict(pat))
        self._maybe_synthesise()

    def observe_swarm_action(self, task: Any, summary: str, success: bool):
        """
        Called by the shadow swarm after each role completes.
        Records what the swarm did and whether it worked.
        """
        record = {
            "ts": time.time(),
            "role": task.role,
            "file": task.file_path,
            "intent": task.intent,
            "success": success,
            "summary": summary,
            "source": "swarm",
        }
        self._persist_pattern("swarm_action", record)

    def observe_chat_turn(self, user_intent: str, response_summary: str,
                          files_written: List[str], tools_used: List[str]):
        """
        Called at the end of each chat turn that produced code or took actions.
        The highest-level orchestration observation.
        """
        if not files_written and not tools_used:
            return

        record = {
            "ts": time.time(),
            "intent": user_intent[:200],
            "response_summary": response_summary[:300],
            "files_written": files_written,
            "tools_used": tools_used,
            "source": "claude",
            "session_id": self._session_id,
        }
        self._persist_pattern("chat_turn", record)

    # ── Lesson synthesis ───────────────────────────────────────────────────────

    def _maybe_synthesise(self):
        """Synthesise lessons every 5 observations (cheap, no LLM)."""
        self._lesson_count += 1
        if self._lesson_count % 5 == 0:
            self._synthesise_structural_lessons()

    def _synthesise_structural_lessons(self):
        """
        Build lessons from patterns WITHOUT calling LLM.
        These are statistical: 'when intent contains X, Claude uses Y constructs'.
        """
        with self._lock:
            patterns = list(self._code_patterns[-50:])

        if len(patterns) < 3:
            return

        # ── Lesson type 1: construct frequency by intent keyword
        keyword_constructs: Dict[str, Dict[str, int]] = {}
        for pat in patterns:
            for word in re.findall(r'\b\w{4,}\b', pat.intent.lower()):
                if word not in keyword_constructs:
                    keyword_constructs[word] = {}
                for c in pat.constructs:
                    keyword_constructs[word][c] = keyword_constructs[word].get(c, 0) + 1

        for keyword, construct_counts in keyword_constructs.items():
            if sum(construct_counts.values()) < 2:
                continue
            top = sorted(construct_counts.items(), key=lambda x: -x[1])[:3]
            if top[0][1] < 2:
                continue
            lesson = OrchestrationLesson(
                lesson_id=hashlib.md5(f"struct_{keyword}".encode()).hexdigest()[:10],
                instruction=f"When implementing a '{keyword}' module, what code constructs does Claude typically use?",
                response=(
                    f"Based on {sum(construct_counts.values())} observations: "
                    + ", ".join(f"{c} ({n}x)" for c, n in top)
                    + f". Patterns also show type_hints={'type_hints' in dict(top)} "
                    + f"and docstrings in {sum(1 for p in patterns if p.has_docstrings and keyword in p.intent.lower())} cases."
                ),
                category="code_structure",
                confidence=min(sum(construct_counts.values()) / 10, 1.0),
                source_patterns=[p.pattern_id for p in patterns[:5]],
            )
            with self._lock:
                self._lessons.append(lesson)

    def synthesise_with_llm(self, topic: str = "all") -> str:
        """
        Use the LLM to synthesise deeper lessons from accumulated patterns.
        Called explicitly (e.g. 'osiris swarm learn').
        """
        with self._lock:
            code_pats = list(self._code_patterns[-20:])
            task_pats = list(self._task_patterns[-10:])

        if not code_pats and not task_pats:
            return "  No patterns accumulated yet. Keep using OSIRIS."

        # Build summary for LLM
        code_summaries = "\n".join(
            f"  - [{p.source}] intent='{p.intent[:60]}' "
            f"constructs={p.constructs[:4]} lines={p.line_count}"
            for p in code_pats
        )
        task_summaries = "\n".join(
            f"  - goal='{p.goal[:60]}' subtasks={p.subtasks[:3]} outcome={p.outcome}"
            for p in task_pats
        )

        prompt = (
            f"You are OSIRIS, analysing how Claude orchestrates code tasks.\n"
            f"Study these observed patterns and extract:\n"
            f"  1. The 3 most consistent code patterns Claude uses (what constructs appear most)\n"
            f"  2. How Claude decomposes tasks (what subtask structure it favours)\n"
            f"  3. Where Claude's approach has weaknesses OSIRIS could improve on\n"
            f"  4. One specific thing OSIRIS should do differently to be better\n\n"
            f"CODE WRITE PATTERNS ({len(code_pats)}):\n{code_summaries}\n\n"
            f"TASK DECOMPOSITIONS ({len(task_pats)}):\n{task_summaries}\n\n"
            f"Be specific and actionable. 6-8 sentences max."
        )

        try:
            from .tools import tool_llm
            result = tool_llm(prompt)
            if result and len(result) > 40:
                # Persist as a high-value lesson
                lesson = OrchestrationLesson(
                    lesson_id=hashlib.md5(f"llm_{time.time()}".encode()).hexdigest()[:10],
                    instruction=f"What has OSIRIS learned about Claude's orchestration? (topic: {topic})",
                    response=result.strip(),
                    category="meta_learning",
                    confidence=0.8,
                    source_patterns=[p.pattern_id for p in code_pats[:5]],
                )
                with self._lock:
                    self._lessons.append(lesson)
                self._persist_pattern("llm_lesson", asdict(lesson))
                return result.strip()
        except Exception:
            pass

        return self._format_structural_lessons()

    def _format_structural_lessons(self) -> str:
        with self._lock:
            lessons = list(self._lessons[-5:])
        if not lessons:
            return "  No lessons synthesised yet."
        lines = ["  Learned patterns:"]
        for l in lessons:
            lines.append(f"  [{l.category}] {l.instruction[:70]}")
            lines.append(f"    → {l.response[:120]}")
        return "\n".join(lines)

    # ── Training corpus export ─────────────────────────────────────────────────

    def flush_to_corpus(self) -> int:
        """
        Convert accumulated patterns to training examples and write to corpus cache.
        Returns count of examples written.
        """
        examples = []

        with self._lock:
            code_pats = list(self._code_patterns)
            task_pats = list(self._task_patterns)
            lessons   = list(self._lessons)

        # Code write patterns → instruction/response pairs
        for pat in code_pats:
            if pat.line_count < 5:
                continue
            examples.append({
                "id": pat.pattern_id,
                "source": f"apprentice_{pat.source}",
                "instruction": (
                    f"Write a {pat.language} module that {pat.intent}. "
                    f"The implementation should include: {', '.join(pat.constructs[:4])}."
                ),
                "response": (
                    f"Module structure: {pat.code_summary}\n"
                    f"Key constructs: {', '.join(pat.constructs)}\n"
                    f"Lines: {pat.line_count} | Type hints: {pat.has_type_hints} "
                    f"| Docstrings: {pat.has_docstrings}"
                ),
                "category": "code_synthesis",
                "timestamp": pat.timestamp,
            })

        # Task decompositions → instruction/response pairs
        for pat in task_pats:
            examples.append({
                "id": pat.pattern_id,
                "source": f"apprentice_{pat.source}",
                "instruction": f"Decompose this task into subtasks: '{pat.goal}'",
                "response": (
                    f"Subtasks:\n" +
                    "\n".join(f"  {i+1}. {t}" for i, t in enumerate(pat.subtasks)) +
                    (f"\nAgent assignments: {json.dumps(pat.agent_map)}" if pat.agent_map else "") +
                    f"\nOutcome: {pat.outcome}"
                ),
                "category": "task_decomposition",
                "timestamp": pat.timestamp,
            })

        # LLM lessons
        for lesson in lessons:
            if lesson.category == "meta_learning":
                examples.append({
                    "id": lesson.lesson_id,
                    "source": "apprentice_synthesis",
                    "instruction": lesson.instruction,
                    "response": lesson.response,
                    "category": "orchestration_meta",
                    "timestamp": lesson.timestamp,
                    "confidence": lesson.confidence,
                })

        if not examples:
            return 0

        # Load existing cache and merge
        existing = []
        try:
            if os.path.exists(_CORPUS_CACHE):
                with open(_CORPUS_CACHE) as f:
                    data = json.load(f)
                existing = data.get("conversations", [])
        except Exception:
            pass

        existing_ids = {e.get("id") for e in existing}
        new_examples = [e for e in examples if e.get("id") not in existing_ids]

        all_examples = existing + new_examples
        corpus = {
            "source": "osiris_apprentice",
            "version": "1.0",
            "updated": datetime.now(timezone.utc).isoformat(),
            "total": len(all_examples),
            "conversations": all_examples,
        }

        with open(_CORPUS_CACHE, "w") as f:
            json.dump(corpus, f, indent=2)

        return len(new_examples)

    # ── Query interface ────────────────────────────────────────────────────────

    def find_similar_patterns(self, intent: str, top_k: int = 5) -> List[CodePattern]:
        """Find patterns similar to the given intent (keyword overlap)."""
        intent_words = set(re.findall(r'\b\w{4,}\b', intent.lower()))
        with self._lock:
            patterns = list(self._code_patterns)

        scored = []
        for pat in patterns:
            pat_words = set(re.findall(r'\b\w{4,}\b', pat.intent.lower()))
            overlap = len(intent_words & pat_words)
            if overlap > 0:
                scored.append((overlap, pat))

        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored[:top_k]]

    def stats(self) -> Dict:
        with self._lock:
            return {
                "code_patterns": len(self._code_patterns),
                "task_patterns": len(self._task_patterns),
                "lessons": len(self._lessons),
                "session_id": self._session_id,
                "log_path": _PATTERNS_LOG,
                "corpus_path": _CORPUS_CACHE,
            }

    def format_stats(self) -> str:
        s = self.stats()
        lines = [
            f"  {_H}NLP Apprentice — Session {s['session_id']}{_R}",
            f"  Code patterns observed:    {s['code_patterns']}",
            f"  Task decompositions:       {s['task_patterns']}",
            f"  Lessons synthesised:       {s['lessons']}",
            f"  Corpus cache:              {s['corpus_path']}",
        ]
        with self._lock:
            if self._code_patterns:
                recent = self._code_patterns[-3:]
                lines.append(f"\n  {_D}Recent observations:{_R}")
                for p in recent:
                    lines.append(f"    [{p.source}] {p.intent[:55]} ({p.line_count} lines)")
        return "\n".join(lines)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _persist_pattern(self, ptype: str, data: Dict):
        record = {"ts": time.time(), "type": ptype, "data": data}
        try:
            with open(_PATTERNS_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass


# ── Singleton ──────────────────────────────────────────────────────────────────

_apprentice: Optional[NLPApprentice] = None
_apprentice_lock = threading.Lock()


def get_apprentice() -> NLPApprentice:
    global _apprentice
    with _apprentice_lock:
        if _apprentice is None:
            _apprentice = NLPApprentice()
    return _apprentice
