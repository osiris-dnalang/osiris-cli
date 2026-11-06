#!/usr/bin/env python3
"""OSIRIS NCLM CLI — auto-enhance / auto-advance pipelines and research tooling.

Every heavy dependency (``networkx``, the ``nclm`` stack, ``ultra_agent``, the TUI) is
imported lazily, so lightweight commands such as ``--version``, ``status``, ``doctor``,
``zenodo`` and ``github`` work in an environment where those packages are absent.

Commands whose backing implementation is not present in this checkout fail with a
single ``NotAvailableError`` line and exit code 2 rather than an ImportError traceback.
Run ``osiris-nclm doctor`` for a per-backend availability report.

Entry point: ``osiris-nclm`` (see ``[project.scripts]`` in pyproject.toml).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Set

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from nclm.enhanced_client import EnhancedDNALangCopilotClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("osiris")

# Paths and SDK setup
REPO_ROOT = Path(__file__).parent.resolve()
SDK_PATH = REPO_ROOT / "copilot-sdk-dnalang" / "src"
HISTORY_FILE = REPO_ROOT / ".osiris_history.jsonl"
CONFIG_DIR = REPO_ROOT / ".config"
STATE_DIR = REPO_ROOT / ".osiris_state"
AUTOADVANCE_DIR = REPO_ROOT / ".autoadvance"
ENHANCED_NCLM_PATH = REPO_ROOT / "nclm"
VERSION = "0.58.0"

MAX_PROMPT_CHARS = 20000
HTTP_TIMEOUT_S = 20
HISTORY_MAX_BYTES = 5 * 1024 * 1024
DEMO_BANNER = "[DEMO OUTPUT - illustrative/simulated content, not a research result]"

# Processing modes accepted by `mode`. Kept static so the parser can be built without
# importing the nclm stack; validated against NCLMMode at run time.
NCLM_MODE_NAMES = ["standard", "grok", "creative", "analytical", "quantum", "hybrid"]

MEMORY_ACTIONS = ["stats", "clear", "clear-working", "save"]


class NotAvailableError(RuntimeError):
    """Raised when a command's backing implementation is not present in this build."""


# ---------------------------------------------------------------------------
# Lazy third-party / optional-backend access
# ---------------------------------------------------------------------------

_nx: Any = None


def require_networkx() -> Any:
    """Import networkx on first use.

    The module-level import this replaces broke the lazy-import contract in the
    docstring: it made every command, including ``--version`` and ``status``, fail on an
    install without networkx. CI installs only numpy/scipy/requests/PyYAML/rich, and
    networkx is declared in requirements.txt but not in pyproject's runtime
    dependencies, so a wheel install does not pull it in either.
    """
    global _nx
    if _nx is None:
        try:
            import networkx
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise NotAvailableError(
                "networkx is required for auto-advance and session analysis. "
                "Install it with: pip install 'networkx>=2.6.3'"
            ) from exc
        _nx = networkx
    return _nx


def _import_backend(module: str, attr: Optional[str] = None, *, needed_for: str) -> Any:
    """Import an optional backend, or raise NotAvailableError naming what is missing."""
    _setup_import_paths()
    try:
        mod = __import__(module, fromlist=[attr] if attr else [])
    except ImportError as exc:
        raise NotAvailableError(
            f"{needed_for} needs the '{module}' module, which is not present in this "
            f"checkout ({exc}). Run `doctor` for the full availability report."
        ) from exc
    if attr is None:
        return mod
    try:
        return getattr(mod, attr)
    except AttributeError as exc:
        raise NotAvailableError(
            f"{needed_for} needs '{module}.{attr}', which this build of {module} does "
            "not provide."
        ) from exc


# Backends this module drives, and the commands that need each one. Used by `doctor`.
OPTIONAL_BACKENDS: Dict[str, Dict[str, Any]] = {
    "networkx": {"commands": ["advance", "complete", "session"], "import": "networkx"},
    "nclm.enhanced_client": {
        "commands": ["infer", "analyze", "understand", "enhance", "advance", "complete"],
        "import": "nclm.enhanced_client",
    },
    "nclm.physics_discovery": {"commands": ["discover"], "import": "nclm.physics_discovery"},
    "nclm.consciousness_telemetry": {
        "commands": ["consciousness"],
        "import": "nclm.consciousness_telemetry",
    },
    "nclm.production.stack": {"commands": ["stack"], "import": "nclm.production.stack"},
    "ultra_agent.swarm": {"commands": ["ultra"], "import": "ultra_agent.swarm"},
    "dual_node_runtime": {"commands": ["dual-node"], "import": "dual_node_runtime"},
}


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def utc_iso() -> str:
    """Current UTC time as ISO-8601 with a trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    """Compact UTC timestamp for file names."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def new_session_id() -> str:
    """Collision-resistant short session id."""
    return uuid.uuid4().hex[:8]


def _json_default(obj: Any) -> Any:
    """Make numpy scalars/arrays, sets and paths JSON-serializable."""
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "item"):
        return obj.item()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj, key=str)
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def write_json(path: Path, data: Any) -> Path:
    """Write JSON atomically-ish (temp file + rename) with safe serialization."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=_json_default)
    tmp.replace(path)
    return path


def ensure_dirs() -> None:
    """Create runtime directories (done at startup, not at import time)."""
    for d in (CONFIG_DIR, STATE_DIR, AUTOADVANCE_DIR):
        d.mkdir(exist_ok=True, parents=True)


def _setup_import_paths() -> None:
    for p in (ENHANCED_NCLM_PATH, SDK_PATH):
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))


def validate_sdk() -> None:
    """Validate that the SDK is available (only for commands that need it)."""
    if not SDK_PATH.exists():
        logger.error("Missing copilot-sdk-dnalang package directory at: %s", SDK_PATH)
        logger.error("Please ensure the package is properly installed.")
        sys.exit(1)
    _setup_import_paths()


def get_zenodo_token(required: bool = True) -> Optional[str]:
    """Get Zenodo token from environment or config file."""
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        config_file = CONFIG_DIR / "zenodo.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    token = json.load(f).get("token")
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not read %s: %s", config_file, exc)

    if not token and required:
        raise EnvironmentError(
            "Zenodo token not found. Set ZENODO_TOKEN environment variable or "
            f"create config file at {CONFIG_DIR}/zenodo.json"
        )
    return token


def normalize_prompt(prompt: str) -> str:
    """Collapse runs of spaces/tabs (line breaks preserved) and cap length."""
    prompt = re.sub(r"[ \t]+", " ", prompt or "").strip()
    return prompt[:MAX_PROMPT_CHARS]


def append_history(entry: Dict[str, Any]) -> None:
    """Append an entry to the history file, rotating it once it exceeds the cap.

    The log is append-only and read by `load_history`, so without rotation it grows
    without bound and a 20-row listing ends up scanning the whole file.
    """
    try:
        if HISTORY_FILE.exists() and HISTORY_FILE.stat().st_size > HISTORY_MAX_BYTES:
            HISTORY_FILE.replace(HISTORY_FILE.with_suffix(".jsonl.1"))
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, default=_json_default)
            f.write("\n")
    except OSError as exc:
        logger.warning("Failed to persist history: %s", exc)


def load_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Load the most recent history entries, skipping malformed lines."""
    if not HISTORY_FILE.exists():
        return []

    history: deque = deque(maxlen=limit)
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        history.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        logger.debug("Skipping malformed history entry: %s", exc)
    except OSError as exc:
        logger.error("Failed to load history: %s", exc)

    return list(history)


def http_get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Any:
    """GET a JSON document with a timeout and readable errors."""
    req = urllib.request.Request(
        url, headers={"User-Agent": f"osiris-cli/{VERSION}", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} from {url.split('?')[0]}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error reaching {url.split('?')[0]}: {exc.reason}") from exc


async def create_nclm_client(state_dir: Optional[Path] = None) -> "EnhancedDNALangCopilotClient":
    """Create and configure the enhanced NCLM client."""
    config_cls = _import_backend(
        "nclm.enhanced_config", "NCLMEnhancedConfig", needed_for="NCLM inference"
    )
    client_cls = _import_backend(
        "nclm.enhanced_client", "EnhancedDNALangCopilotClient", needed_for="NCLM inference"
    )

    config_path = CONFIG_DIR / "nclm_config.json"
    config = None
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = config_cls.from_dict(json.load(f))
        except Exception as e:  # config schema errors vary by nclm version
            logger.warning("Failed to load NCLM config: %s. Using defaults.", e)
    if config is None:
        config = config_cls()

    try:
        return client_cls(
            config=config,
            state_dir=state_dir or STATE_DIR,
            enable_intent_engine=True,
            enable_quantum=True,
        )
    except ImportError as exc:
        # The nclm stack imports some submodules lazily inside __init__, so a broken
        # dependency surfaces here rather than at the top-level import above.
        raise NotAvailableError(
            f"The nclm client failed to initialize: {exc}. Run `doctor` for the "
            "backend report."
        ) from exc


async def _maybe_await(value: Any) -> Any:
    return await value if asyncio.iscoroutine(value) else value


async def call_client(client: Any, candidates: Iterable[str], *args: Any, **kwargs: Any) -> Any:
    """Call the first method in ``candidates`` that the client implements.

    Lets the CLI work across nclm client versions without hard-coding one API.
    Raises NotAvailableError (exit code 2) if none exist.
    """
    names = list(candidates)
    for name in names:
        fn = getattr(client, name, None)
        if callable(fn):
            return await _maybe_await(fn(*args, **kwargs))
    raise NotAvailableError(
        f"{type(client).__name__} has none of: {', '.join(names)}. "
        "This command is not wired to the installed nclm client."
    )


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))


def _section(title: str, width: int = 70) -> None:
    print(f"\n{'=' * width}\n{title}\n{'=' * width}")


def _append_context(prompt: str, context: str) -> str:
    """Append a context block once.

    An earlier implementation returned ``prompt + context + prompt``, which doubled the
    prompt on every enhancement pass (8x after 3 passes, far more inside auto-advance).
    Blocks are appended once, and a block whose header is already present is skipped.
    """
    context = context.strip("\n")
    header = context.splitlines()[0] if context else ""
    if not context or (header and header in prompt):
        return prompt
    return f"{prompt}\n\n{context}"[:MAX_PROMPT_CHARS]


def _analysis_section(analysis: Dict, key: str) -> Dict:
    section = (analysis or {}).get("analysis", {}).get(key, {})
    return section if isinstance(section, dict) else {}


class AutoEnhanceEngine:
    """Engine for automatically enhancing prompts through context augmentation."""

    def __init__(self, client: "EnhancedDNALangCopilotClient"):
        self.client = client
        self.enhancement_history: deque = deque(maxlen=10)
        self.enhancement_strategies: List[Callable] = [
            self._enhance_with_memory,
            self._enhance_with_quantum,
            self._enhance_with_domain_knowledge,
            self._enhance_with_cognitive_metrics,
            self._enhance_with_structured_thinking,
        ]

    @property
    def quantum_enabled(self) -> bool:
        return bool(getattr(self.client, "enable_quantum", False))

    async def auto_enhance_prompt(self, prompt: str, iterations: int = 3) -> Dict:
        """Enhance a prompt over several passes, choosing a strategy per pass."""
        iterations = max(1, int(iterations))
        original_prompt = prompt
        current_prompt = prompt
        enhancement_chain: List[Dict] = []
        used: Set[str] = set()

        stopped_because: Optional[str] = None
        for i in range(iterations):
            logger.info("Auto-enhancement iteration %d/%d", i + 1, iterations)

            analysis = await self.client.cognitive_analysis(current_prompt)
            if not isinstance(analysis, dict) or analysis.get("status") != "success":
                # Carry the backend's own error forward. Dropping it made a broken or
                # stubbed nclm backend look like a prompt that simply needed no changes.
                reason = (
                    analysis.get("error") or f"status={analysis.get('status')!r}"
                    if isinstance(analysis, dict)
                    else f"cognitive_analysis returned {type(analysis).__name__}"
                )
                stopped_because = f"iteration {i + 1}: {reason}"
                logger.warning("Failed to analyze prompt in %s", stopped_because)
                break

            strategy = self._select_enhancement_strategy(
                analysis, exclude=used, prompt_text=current_prompt
            )
            enhanced = await strategy(current_prompt, analysis)
            used.add(strategy.__name__)

            enhancement_chain.append({
                "iteration": i + 1,
                "original": current_prompt,
                "enhanced": enhanced,
                "strategy": strategy.__name__,
                "changed": enhanced != current_prompt,
                "analysis": analysis.get("analysis", {}),
            })

            current_prompt = enhanced

        final_enhanced = self._generate_final_enhanced_prompt(
            original_prompt, current_prompt, enhancement_chain
        )
        # Remember the *original* prompt of each run, for memory enhancement in later runs
        if original_prompt not in self.enhancement_history:
            self.enhancement_history.append(original_prompt)

        return {
            "original_prompt": original_prompt,
            "final_enhanced_prompt": final_enhanced,
            "enhancement_chain": enhancement_chain,
            "metrics": self._calculate_enhancement_metrics(enhancement_chain),
            "stopped_because": stopped_because,
        }

    @staticmethod
    def _content_words(text: str) -> Set[str]:
        return set(re.findall(r"\w{4,}", (text or "").lower()))

    @classmethod
    def _history_overlaps(cls, prompt_text: str, history: Iterable[str],
                          min_overlap: int = 2) -> bool:
        """True when some past prompt shares at least ``min_overlap`` content words.

        Replaces a bare ``any(p not in prompt_text for p in history)`` test, which was
        true whenever history held anything that was not a literal substring of the
        current prompt - i.e. nearly always after the first run. That ranked the memory
        strategy first regardless of relevance, and it was then frequently selected only
        to return the prompt unchanged, burning one of the available passes.
        """
        words = cls._content_words(prompt_text)
        return any(len(words & cls._content_words(past)) >= min_overlap for past in history)

    def _select_enhancement_strategy(self, analysis: Dict, exclude: Optional[Set[str]] = None,
                                     prompt_text: str = "") -> Callable:
        """Pick the most appropriate strategy, preferring ones not yet used this run."""
        exclude = exclude or set()
        prompt_text = prompt_text or ""
        intent = _analysis_section(analysis, "intent_analysis")
        metrics = _analysis_section(analysis, "cognitive_metrics")
        memory_stats = _analysis_section(analysis, "memory_stats")

        ranked: List[Callable] = []
        if metrics.get("coherence_lambda", 0) < 0.6:
            ranked.append(self._enhance_with_structured_thinking)
        if self.quantum_enabled and metrics.get("quantum_entanglement", 0) > 0.5:
            ranked.append(self._enhance_with_quantum)
        unseen = [p for p in self.enhancement_history if p not in prompt_text]
        if memory_stats.get("working_memory_count", 0) > 3 or self._history_overlaps(
            prompt_text, unseen
        ):
            ranked.append(self._enhance_with_memory)
        if intent.get("domains"):
            ranked.append(self._enhance_with_domain_knowledge)
        ranked.append(self._enhance_with_cognitive_metrics)
        ranked.extend(self.enhancement_strategies)  # fallbacks

        for strategy in ranked:
            if strategy.__name__ not in exclude:
                return strategy
        return ranked[0]

    async def _enhance_with_memory(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using this engine's real prior prompts (no fabricated memories)."""
        memories = await self._get_relevant_memories(prompt)
        if not memories:
            return prompt
        memory_context = "[MEMORY CONTEXT]\n" + "\n".join(
            f"Memory {i}: {m[:150]}{'...' if len(m) > 150 else ''}"
            for i, m in enumerate(memories[:3], 1)
        )
        return _append_context(prompt, memory_context)

    async def _get_relevant_memories(self, prompt: str) -> List[str]:
        """Return prior prompts ranked by word overlap with ``prompt``.

        Uses the client's own memory search if it exposes one; otherwise falls back to
        this session's enhancement history. Returns [] rather than inventing content.
        """
        for name in ("search_memory", "recall", "retrieve_memories"):
            fn = getattr(self.client, name, None)
            if callable(fn):
                try:
                    result = await _maybe_await(fn(prompt))
                except Exception as exc:
                    logger.debug("%s failed: %s", name, exc)
                    continue
                # A dict return would otherwise iterate to its keys.
                if isinstance(result, (list, tuple, set)) and result:
                    return [str(r) for r in result]
                if result:
                    logger.debug("%s returned %s, not a sequence; ignoring",
                                 name, type(result).__name__)

        words = self._content_words(prompt)
        scored = []
        for past in self.enhancement_history:
            if past in prompt:  # the prompt being enhanced isn't a memory of itself
                continue
            overlap = len(words & self._content_words(past))
            if overlap:
                scored.append((overlap, past))
        return [p for _, p in sorted(scored, key=lambda x: -x[0])]

    async def _enhance_with_quantum(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using quantum-cognitive concept weights."""
        quantum_analysis = _analysis_section(analysis, "quantum_analysis")
        if not self.quantum_enabled or not quantum_analysis:
            return prompt

        measurements = [
            m for m in quantum_analysis.get("quantum_measurements", []) if isinstance(m, dict)
        ]
        top_concepts = sorted(
            measurements, key=lambda x: -float(x.get("post_probability", 0))
        )[:3]
        if not top_concepts:
            return prompt

        lines = ["[QUANTUM COGNITIVE CONTEXT]"]
        for c in top_concepts:
            lines.append(
                f"- {c.get('concept', '?')}: Probability={float(c.get('post_probability', 0)):.3f}, "
                f"State={c.get('state', '?')}"
            )
        lines += [
            "",
            "[QUANTUM PROCESSING INSTRUCTIONS]",
            "- Treat the concept probabilities above as relative weights",
            "- Explore relationships between the weighted concepts",
        ]
        return _append_context(prompt, "\n".join(lines))

    async def _enhance_with_domain_knowledge(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt using domain-specific vocabulary."""
        domains = _analysis_section(analysis, "intent_analysis").get("domains", [])
        if not domains:
            return prompt

        vocab = {
            "quantum": ["superposition", "entanglement", "qubit", "decoherence"],
            "cognitive": ["memory", "attention", "reasoning", "understanding"],
        }
        lines = ["[DOMAIN KNOWLEDGE CONTEXT]"]
        for domain in domains[:2]:
            concepts = vocab.get(
                str(domain).lower(), ["analysis", "model", "theory", "application"]
            )
            lines.append(f"Domain: {domain}")
            lines.append(f"Key concepts: {', '.join(concepts)}")
        return _append_context(prompt, "\n".join(lines))

    async def _enhance_with_cognitive_metrics(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt with metric-driven processing instructions."""
        m = _analysis_section(analysis, "cognitive_metrics")
        lines = [
            "[COGNITIVE METRICS CONTEXT]",
            f"- Coherence (L): {m.get('coherence_lambda', 0):.3f}",
            f"- Consciousness (Phi): {m.get('consciousness_phi', 0):.3f}",
            f"- Cognitive Load: {m.get('cognitive_load', 0):.3f}",
        ]
        if self.quantum_enabled:
            lines.append(f"- Quantum Entanglement: {m.get('quantum_entanglement', 0):.3f}")

        lines += ["", "[COGNITIVE PROCESSING INSTRUCTIONS]"]
        lines.append(
            "- Focus on establishing clearer logical connections"
            if m.get("coherence_lambda", 0) < 0.7
            else "- Maintain high coherence in reasoning"
        )
        lines.append(
            "- Work on integrating concepts into a unified framework"
            if m.get("consciousness_phi", 0) < 0.7
            else "- Leverage well-integrated conceptual understanding"
        )
        lines.append(
            "- Break complex ideas into manageable parts"
            if m.get("cognitive_load", 0) > 0.8
            else "- Comprehensive analysis is feasible with current load"
        )
        return _append_context(prompt, "\n".join(lines))

    async def _enhance_with_structured_thinking(self, prompt: str, analysis: Dict) -> str:
        """Enhance prompt with a structured reasoning framework."""
        intent = _analysis_section(analysis, "intent_analysis")
        domains = [str(d) for d in intent.get("domains", [])]
        actions = [str(a) for a in intent.get("actions", [])]

        if "quantum" in " ".join(domains).lower():
            title, steps = "Quantum-Cognitive Analysis Framework:", [
                "Identify quantum principles relevant to the question",
                "Map quantum states to the concepts involved",
                "Analyze entanglement relationships",
                "Evaluate superposition effects on reasoning",
                "Synthesize a model and state its limits",
            ]
        elif any(a.lower() in ("explain", "describe") for a in actions):
            title, steps = "Explanatory Structure Framework:", [
                "Define key terms and concepts",
                "Establish foundational principles",
                "Build logical connections",
                "Provide illustrative examples",
                "Summarize key insights",
            ]
        else:
            title, steps = "General Analytical Framework:", [
                "Problem decomposition",
                "Conceptual analysis",
                "Relationship mapping",
                "Pattern identification",
                "Synthesis and conclusion",
            ]
        body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        return _append_context(prompt, f"[STRUCTURED THINKING FRAMEWORK]\n{title}\n{body}")

    def _generate_final_enhanced_prompt(self, original: str, current: str,
                                        chain: List[Dict]) -> str:
        """Wrap the enhanced prompt with a short provenance header.

        The original prompt is previewed, not duplicated in full.
        """
        journey = "\n".join(
            f"{i}. {step['strategy'].replace('_', ' ').strip().title()}"
            f"{'' if step.get('changed', True) else ' (no change)'}"
            for i, step in enumerate(chain, 1)
        ) or "(no enhancement steps completed)"
        preview = original if len(original) <= 200 else original[:200] + "..."

        return (
            "[AUTO-ENHANCED PROMPT]\n\n"
            f"Original Prompt: {preview}\n\n"
            f"Enhancement Journey:\n{journey}\n\n"
            "[COGNITIVE PROCESSING INSTRUCTIONS]\n"
            "- Integrate all enhancement layers in analysis\n"
            "- Maintain coherence across expanded context\n"
            "- Apply the structured framework where one is given\n"
            "- Generate a comprehensive, multi-perspective response\n\n"
            "[FINAL ENHANCED PROMPT]\n"
            f"{current}"
        )[:MAX_PROMPT_CHARS]

    def _calculate_enhancement_metrics(self, chain: List[Dict]) -> Dict:
        """Summarize the enhancement run."""
        if not chain:
            return {
                "iterations": 0,
                "strategies_used": 0,
                "coherence_improvement": 0.0,
                "complexity_increase": 0.0,
                "unique_strategies": [],
            }

        def coherence(step: Dict) -> float:
            analysis = step.get("analysis")
            if not isinstance(analysis, dict):
                return 0.0
            metrics = analysis.get("cognitive_metrics")
            if not isinstance(metrics, dict):
                return 0.0
            return float(metrics.get("coherence_lambda", 0) or 0)

        unique = sorted({step["strategy"] for step in chain})
        initial_length = len(chain[0]["original"])
        return {
            "iterations": len(chain),
            "strategies_used": len(unique),
            "coherence_improvement": coherence(chain[-1]) - coherence(chain[0]),
            "complexity_increase": (
                (len(chain[-1]["enhanced"]) - initial_length) / max(1, initial_length)
            ),
            "unique_strategies": unique,
        }


def _step_metrics(step: Dict) -> Dict:
    """Metrics dict from an advance-chain step, tolerant of missing keys."""
    du = step.get("deep_understanding") or {}
    metrics = du.get("metrics", {}) if isinstance(du, dict) else {}
    return metrics if isinstance(metrics, dict) else {}


class AutoAdvanceEngine:
    """Engine for automatically advancing understanding through iterative refinement."""

    def __init__(self, client: "EnhancedDNALangCopilotClient"):
        nx = require_networkx()
        self.client = client
        self.advance_history: List[Dict] = []
        self.knowledge_graph = nx.DiGraph()
        self.current_session_id = new_session_id()
        self.auto_enhance_engine = AutoEnhanceEngine(client)

    @property
    def quantum_enabled(self) -> bool:
        return bool(getattr(self.client, "enable_quantum", False))

    async def auto_advance(self, initial_prompt: str, iterations: int = 5,
                           exploration_depth: int = 3) -> Dict:
        """Iteratively deepen understanding of ``initial_prompt``.

        Each iteration enhances a focused prompt (the original topic plus the current
        refinement question), runs deep understanding, grows the knowledge graph and
        picks the next question. Prompts are rebuilt from the original topic each time
        instead of nesting the previous enhanced prompt, which used to grow without
        bound.

        ``initial_prompt`` must be a raw topic, not an already-enhanced prompt: this
        method runs its own enhancement pass per iteration, so handing it the output of
        ``AutoEnhanceEngine.auto_enhance_prompt`` nests the enhancement envelope.
        """
        iterations = max(1, int(iterations))
        session_dir = AUTOADVANCE_DIR / f"session_{self.current_session_id}"
        session_dir.mkdir(exist_ok=True, parents=True)

        focus_prompt = initial_prompt
        current_prompt = initial_prompt
        stopped_because: Optional[str] = None
        advance_chain: List[Dict] = []
        knowledge_nodes: Set[str] = set()
        asked: List[str] = []

        for i in range(iterations):
            logger.info("Auto-advance iteration %d/%d", i + 1, iterations)

            analysis = await self.client.cognitive_analysis(focus_prompt)
            if not isinstance(analysis, dict) or analysis.get("status") != "success":
                reason = (
                    analysis.get("error") or f"status={analysis.get('status')!r}"
                    if isinstance(analysis, dict)
                    else f"cognitive_analysis returned {type(analysis).__name__}"
                )
                stopped_because = f"iteration {i + 1}: {reason}"
                logger.warning("Analysis failed in %s", stopped_because)
                break

            # Created only once the iteration is known to produce results, so a failed
            # pass does not leave an empty iteration_N/ directory behind.
            iteration_dir = session_dir / f"iteration_{i+1}"
            iteration_dir.mkdir(exist_ok=True)

            enhanced = await self.auto_enhance_engine.auto_enhance_prompt(focus_prompt)
            current_prompt = enhanced["final_enhanced_prompt"]

            deep_result = await self.client.deep_understand(
                current_prompt, max_depth=exploration_depth
            )
            if not isinstance(deep_result, dict):
                deep_result = {"result": deep_result}

            new_concepts = self._extract_new_concepts(deep_result, knowledge_nodes)
            knowledge_nodes.update(new_concepts)
            self._update_knowledge_graph(deep_result, new_concepts)

            candidates = self._generate_refinement_questions(deep_result, i, iterations)
            questions = [q for q in candidates if q not in asked] or candidates

            selected_question = None
            if i < iterations - 1 and questions:
                selected_question = self._select_question(questions, deep_result)
                asked.append(selected_question)
                focus_prompt = self._build_focus_prompt(initial_prompt, asked)

            iteration_result = {
                "iteration": i + 1,
                "prompt": current_prompt,
                "analysis": analysis.get("analysis", {}),
                "deep_understanding": deep_result,
                "new_concepts": sorted(map(str, new_concepts)),
                "refinement_questions": questions,
                "selected_question": selected_question,
                "next_prompt": focus_prompt if selected_question else None,
                "timestamp": utc_iso(),
            }
            write_json(iteration_dir / "results.json", iteration_result)
            advance_chain.append(iteration_result)

            if self._check_convergence(advance_chain):
                logger.info("Convergence detected at iteration %d", i + 1)
                break

        final_report = await self._generate_final_report(
            advance_chain, initial_prompt, current_prompt
        )

        g = self.knowledge_graph
        manifest = {
            "session_id": self.current_session_id,
            "version": VERSION,
            "initial_prompt": initial_prompt,
            "final_prompt": current_prompt,
            "iterations": len(advance_chain),
            "timestamps": {
                "start": advance_chain[0]["timestamp"] if advance_chain else utc_iso(),
                "end": utc_iso(),
            },
            "knowledge_graph": {
                "nodes": list(g.nodes()),
                "edges": [
                    {"source": u, "target": v, "data": g.edges[u, v]} for u, v in g.edges()
                ],
                "metrics": self._graph_metrics(),
            },
            "final_report": final_report,
        }
        write_json(session_dir / "manifest.json", manifest)

        session_id = self.current_session_id
        self.current_session_id = new_session_id()

        return {
            "status": "success" if advance_chain else "no_iterations",
            "stopped_because": stopped_because,
            "session_id": session_id,
            "initial_prompt": initial_prompt,
            "final_prompt": current_prompt,
            "iterations": len(advance_chain),
            "knowledge_graph": manifest["knowledge_graph"],
            "final_report": final_report,
            "session_dir": str(session_dir),
            "advance_chain": [ac["iteration"] for ac in advance_chain],
        }

    def _graph_metrics(self) -> Dict:
        nx = require_networkx()
        g = self.knowledge_graph
        n = g.number_of_nodes()
        sccs = list(nx.strongly_connected_components(g)) if n else []
        return {
            "nodes": n,
            "edges": g.number_of_edges(),
            "density": nx.density(g) if n > 1 else 0.0,
            "average_degree": sum(dict(g.degree()).values()) / max(1, n),
            "number_strongly_connected_components": len(sccs),
            "largest_scc_size": max((len(c) for c in sccs), default=0),
        }

    @staticmethod
    def _build_focus_prompt(initial_prompt: str, asked: List[str]) -> str:
        prior = "\n".join(f"- {q}" for q in asked[:-1])
        parts = [initial_prompt]
        if prior:
            parts.append(f"[PREVIOUSLY EXPLORED]\n{prior}")
        parts.append(f"[REFINEMENT FOCUS]\n{asked[-1]}")
        return "\n\n".join(parts)[:MAX_PROMPT_CHARS]

    def _extract_new_concepts(self, deep_result: Dict, known_concepts: Set[str]) -> List[str]:
        """Concepts in this result not seen earlier in the session, in arrival order.

        Returns a list rather than a set so that ``_update_knowledge_graph`` can link the
        genuinely newest concept instead of whichever name happens to sort first.
        """
        concept_graph = deep_result.get("concept_graph", {}) or {}
        ordered = [str(c) for c in concept_graph.get("nodes", [])]

        if self.quantum_enabled:
            quantum_analysis = deep_result.get("quantum_analysis", {}) or {}
            ordered += [
                str(m["concept"])
                for m in quantum_analysis.get("quantum_measurements", [])
                if isinstance(m, dict) and "concept" in m
            ]

        seen: Set[str] = set()
        out: List[str] = []
        for concept in ordered:
            if concept not in known_concepts and concept not in seen:
                seen.add(concept)
                out.append(concept)
        return out

    def _update_knowledge_graph(self, deep_result: Dict, new_concepts: Iterable[str]) -> None:
        """Merge concepts and relationships into the session knowledge graph."""
        g = self.knowledge_graph
        new_concepts = list(new_concepts)
        for concept in new_concepts:
            if concept not in g:
                g.add_node(concept, type="concept")

        for edge in (deep_result.get("concept_graph", {}) or {}).get("edges", []):
            if not isinstance(edge, dict) or "source" not in edge or "target" not in edge:
                continue
            source, target = str(edge["source"]), str(edge["target"])
            weight = float(edge.get("weight", 0.5))
            if g.has_edge(source, target):
                g.edges[source, target]["weight"] = max(
                    g.edges[source, target].get("weight", 0), weight
                )
            else:
                g.add_edge(source, target, weight=weight, type=edge.get("type", "relationship"))

        # Link the most recently arrived concept to the current hubs. _extract_new_concepts
        # preserves arrival order, so this is the genuinely newest one; taking sorted(...)[0]
        # instead picked the alphabetically first name and skewed degree_centrality toward
        # concepts starting with digits or early letters.
        if new_concepts:
            latest_concept = new_concepts[-1]
            hubs = sorted(g.degree(), key=lambda x: (-x[1], str(x[0])))[:3]
            for concept, _degree in hubs:
                if concept != latest_concept:
                    g.add_edge(concept, latest_concept, weight=0.5, type="temporal")

    def _generate_refinement_questions(self, deep_result: Dict, current_iter: int,
                                       total_iter: int) -> List[str]:
        """Generate up to five questions to steer the next iteration."""
        questions: List[str] = []
        metrics = deep_result.get("metrics", {}) or {}
        intent = deep_result.get("intent_analysis", {}) or {}
        concepts = [str(c) for c in (deep_result.get("concept_graph", {}) or {}).get("nodes", [])]

        if metrics.get("coherence", 0) < 0.7:
            questions.append(
                "What are the missing connections needed to improve coherence "
                f"(L={metrics.get('coherence', 0):.2f})?"
            )
        if metrics.get("consciousness", 0) < 0.7:
            questions.append(
                "How can we better integrate these concepts "
                f"(Phi={metrics.get('consciousness', 0):.2f})?"
            )
        if self.quantum_enabled and metrics.get("quantum_entanglement", 0) < 0.5:
            questions.append(
                "Which concepts should be more strongly related to better model their "
                "relationships?"
            )

        # Prefer the least-explored concepts (lowest degree in the session graph)
        if concepts:
            g = self.knowledge_graph
            for concept in sorted(concepts, key=lambda c: (g.degree(c) if c in g else 0, c))[:3]:
                questions.append(f"What deeper insights can we gain about {concept}?")

        if current_iter < total_iter // 2:
            questions.append("What foundational principles need more exploration?")
        else:
            questions.append(
                "What higher-level syntheses can we develop from current understanding?"
            )

        domains = " ".join(str(d) for d in intent.get("domains", [])).lower()
        if "quantum" in domains:
            questions.append(
                "How do quantum principles specifically inform our understanding of this topic?"
            )
        if "cognitive" in domains:
            questions.append("What cognitive mechanisms best explain the observed patterns?")

        return questions[:5]

    @staticmethod
    def _select_question(questions: List[str], deep_result: Dict) -> str:
        """Pick the question that targets the weakest metric."""
        metrics = deep_result.get("metrics", {}) or {}

        def first_matching(words: Iterable[str]) -> Optional[str]:
            return next((q for q in questions if any(w in q.lower() for w in words)), None)

        if metrics.get("coherence", 0) < 0.6:
            return first_matching(["connection", "relationship", "link"]) or questions[0]
        if metrics.get("consciousness", 0) < 0.6:
            return first_matching(["integrate", "unify", "synthes"]) or questions[0]
        return questions[0]

    def _check_convergence(self, advance_chain: List[Dict], window: int = 3) -> bool:
        """Converged when metrics and new-concept counts are flat over ``window`` steps."""
        if len(advance_chain) < window:
            return False

        recent = advance_chain[-window:]
        metrics = [_step_metrics(step) for step in recent]
        if not any(metrics):
            return False  # no metrics reported -> cannot claim convergence

        def spread(key: str) -> float:
            vals = [float(m.get(key, 0) or 0) for m in metrics]
            return max(vals) - min(vals)

        new_counts = [len(step.get("new_concepts", [])) for step in recent]
        return (
            spread("coherence") < 0.05
            and spread("consciousness") < 0.05
            and max(new_counts) - min(new_counts) < 2
        )

    async def _generate_final_report(self, advance_chain: List[Dict],
                                     initial_prompt: str, final_prompt: str) -> Dict:
        """Generate a comprehensive final report."""
        return {
            "summary": self._generate_summary_report(advance_chain, initial_prompt, final_prompt),
            "knowledge_graph": self._generate_graph_report(),
            "metric_trends": self._generate_metric_trends(advance_chain),
            "key_insights": self._generate_key_insights(advance_chain),
            "recommendations": self._generate_final_recommendations(advance_chain),
        }

    def _generate_summary_report(self, advance_chain: List[Dict],
                                 initial_prompt: str, final_prompt: str) -> str:
        """Generate a summary of the auto-advance process."""
        summary = [
            "AUTO-ADVANCE SUMMARY REPORT",
            "=" * 50,
            f"\nInitial Prompt: {initial_prompt}",
            f"Final Prompt Length: {len(final_prompt)} characters",
            f"Iterations Completed: {len(advance_chain)}",
        ]
        if not advance_chain:
            summary.append("\nNo iterations completed (analysis failed on the first pass).")
            return "\n".join(summary)

        initial_metrics = _step_metrics(advance_chain[0])
        final_metrics = _step_metrics(advance_chain[-1])
        coherence_improvement = (
            final_metrics.get("coherence", 0) - initial_metrics.get("coherence", 0)
        )
        consciousness_improvement = (
            final_metrics.get("consciousness", 0) - initial_metrics.get("consciousness", 0)
        )

        summary.append("\nMetric Improvements:")
        summary.append(f"- Coherence (L): {coherence_improvement:+.3f}")
        summary.append(f"- Consciousness (Phi): {consciousness_improvement:+.3f}")

        all_concepts: Set[str] = set()
        for step in advance_chain:
            all_concepts.update(step.get("new_concepts", []))

        summary.append(f"\nKey Concepts Discovered: {len(all_concepts)}")
        top_concepts = sorted(
            all_concepts,
            key=lambda c: sum(1 for step in advance_chain if c in step.get("new_concepts", [])),
            reverse=True,
        )[:5]
        for concept in top_concepts:
            count = sum(1 for step in advance_chain if concept in step.get("new_concepts", []))
            summary.append(f"  - {concept} (mentioned in {count} iterations)")

        metrics = self._graph_metrics()
        summary.append("\nKnowledge Graph Growth:")
        summary.append(f"- Final Nodes: {metrics['nodes']}")
        summary.append(f"- Final Edges: {metrics['edges']}")
        summary.append(f"- Graph Density: {metrics['density']:.3f}")
        return "\n".join(summary)

    def _generate_graph_report(self) -> Dict:
        """Centrality and component report over the session knowledge graph."""
        if not self.knowledge_graph.nodes():
            return {
                "status": "empty",
                "metrics": self._graph_metrics(),
                "top_concepts": {},
                "strongly_connected_components": [],
            }

        nx = require_networkx()
        g = self.knowledge_graph
        degree_centrality = nx.degree_centrality(g)
        betweenness_centrality = nx.betweenness_centrality(g)
        closeness_centrality = nx.closeness_centrality(g)

        sccs = sorted(nx.strongly_connected_components(g), key=len, reverse=True)

        # Shared with _graph_metrics so the two reports cannot drift apart.
        metrics = self._graph_metrics()
        metrics["is_strongly_connected"] = nx.is_strongly_connected(g)

        return {
            "status": "success",
            "metrics": metrics,
            "top_concepts": {
                "degree_centrality": sorted(degree_centrality.items(), key=lambda x: -x[1])[:5],
                "betweenness_centrality": sorted(
                    betweenness_centrality.items(), key=lambda x: -x[1]
                )[:5],
                "closeness_centrality": sorted(
                    closeness_centrality.items(), key=lambda x: -x[1]
                )[:5],
            },
            "strongly_connected_components": [
                {"size": len(scc), "concepts": sorted(scc)} for scc in sccs[:3]
            ],
        }

    def _generate_metric_trends(self, advance_chain: List[Dict]) -> Dict:
        """Generate trends of metrics across iterations."""
        if not advance_chain:
            def empty() -> Dict:
                return {"values": [], "start": 0.0, "end": 0.0, "change": 0.0, "average": 0.0}
            return {
                "coherence": empty(),
                "consciousness": empty(),
                "quantum_entanglement": empty(),
                "new_concepts": {"values": [], "total": 0, "average": 0.0, "max": 0},
            }

        def series(key: str) -> List[float]:
            return [float(_step_metrics(step).get(key, 0) or 0) for step in advance_chain]

        def summarize(values: List[float]) -> Dict:
            return {
                "values": values,
                "start": values[0],
                "end": values[-1],
                "change": values[-1] - values[0],
                "average": sum(values) / len(values),
            }

        coherence_trend = series("coherence")
        consciousness_trend = series("consciousness")
        quantum_trend = series("quantum_entanglement")
        new_concepts_trend = [len(step.get("new_concepts", [])) for step in advance_chain]

        trends = {
            "coherence": summarize(coherence_trend),
            "consciousness": summarize(consciousness_trend),
            "quantum_entanglement": summarize(quantum_trend),
            "new_concepts": {
                "values": new_concepts_trend,
                "total": sum(new_concepts_trend),
                "average": sum(new_concepts_trend) / len(new_concepts_trend),
                "max": max(new_concepts_trend),
            },
        }

        if len(coherence_trend) > 1:
            trends["convergence"] = {
                "coherence_stable": abs(coherence_trend[-1] - coherence_trend[-2]) < 0.02,
                "consciousness_stable": abs(
                    consciousness_trend[-1] - consciousness_trend[-2]
                ) < 0.02,
                "concepts_stable": new_concepts_trend[-1] <= new_concepts_trend[-2],
            }
        return trends

    def _generate_key_insights(self, advance_chain: List[Dict]) -> List[str]:
        """Generate key insights from the auto-advance process."""
        insights: List[str] = []
        trends = self._generate_metric_trends(advance_chain)

        if trends.get("coherence", {}).get("change", 0) > 0.1:
            insights.append(
                f"Significant coherence improvement (dL={trends['coherence']['change']:.3f}) "
                "indicates better logical integration of concepts."
            )
        if trends.get("consciousness", {}).get("change", 0) > 0.1:
            insights.append(
                f"Consciousness metric improved (dPhi={trends['consciousness']['change']:.3f}) "
                "showing better integration of information."
            )
        if trends.get("quantum_entanglement", {}).get("change", 0) > 0.1:
            insights.append(
                "Increased quantum entanglement "
                f"({trends['quantum_entanglement']['change']:+.3f}) suggests stronger "
                "conceptual relationships were identified."
            )

        graph_report = self._generate_graph_report()
        if graph_report.get("metrics", {}).get("largest_scc_size", 0) > 5:
            insights.append(
                "Large strongly connected component "
                f"({graph_report['metrics']['largest_scc_size']} concepts) indicates a core "
                "set of interrelated ideas."
            )

        top_concepts = graph_report.get("top_concepts", {}).get("degree_centrality", [])
        if top_concepts:
            insights.append(
                f"Key central concepts identified: {', '.join(c[0] for c in top_concepts[:3])}"
            )

        all_questions: List[str] = []
        for step in advance_chain:
            all_questions.extend(step.get("refinement_questions", []))
        if all_questions:
            common_themes = self._find_common_themes(all_questions)
            if common_themes:
                insights.append(f"Recurring themes in refinement: {', '.join(common_themes[:3])}")

        if not insights:
            insights.extend([
                "Iterative refinement led to progressively deeper understanding",
                "Multiple perspectives were integrated through the process",
                "Conceptual relationships were systematically explored",
            ])
        return insights

    @staticmethod
    def _find_common_themes(questions: List[str]) -> List[str]:
        """Find common themes in refinement questions."""
        theme_keywords = {
            "connections": ["connection", "relationship", "link", "relate"],
            "integration": ["integrate", "unify", "combine", "synthesize"],
            "quantum": ["quantum", "entanglement", "superposition", "qubit"],
            "cognitive": ["cognitive", "reasoning", "understanding", "memory"],
            "application": ["apply", "application", "practical", "use"],
            "foundations": ["foundation", "basic", "principle", "fundamental"],
        }
        counts = {theme: 0 for theme in theme_keywords}
        for question in questions:
            q_lower = question.lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in q_lower for keyword in keywords):
                    counts[theme] += 1
        return [theme for theme, count in sorted(counts.items(), key=lambda x: -x[1]) if count > 0]

    def _generate_final_recommendations(self, advance_chain: List[Dict]) -> List[str]:
        """Generate final recommendations based on the auto-advance process."""
        recommendations: List[str] = []
        trends = self._generate_metric_trends(advance_chain)
        graph_report = self._generate_graph_report()
        last_step = advance_chain[-1] if advance_chain else {}

        if trends.get("coherence", {}).get("end", 0) < 0.7:
            recommendations.append(
                "Focus on strengthening logical connections between concepts to improve "
                "coherence. Try explicitly mapping relationships between key ideas."
            )
        if trends.get("consciousness", {}).get("end", 0) < 0.7:
            recommendations.append(
                "Work on integrating the concepts into a unified framework. Look for "
                "higher-level principles that can unify the different ideas."
            )
        if self.quantum_enabled and trends.get("quantum_entanglement", {}).get("end", 0) < 0.5:
            recommendations.append(
                "Consider increasing quantum entanglement strength to better model the "
                "relationships between concepts, especially for interconnected ideas."
            )
        if graph_report.get("metrics", {}).get("number_strongly_connected_components", 0) > 2:
            recommendations.append(
                "The knowledge graph shows multiple disconnected components. Focus on "
                "finding connections between these different concept clusters."
            )

        deep = last_step.get("deep_understanding", {}) or {}
        domains = " ".join(
            str(d) for d in (deep.get("intent_analysis", {}) or {}).get("domains", [])
        ).lower()
        if "quantum" in domains and "cognitive" in domains:
            recommendations.append(
                "The analysis spans both quantum and cognitive domains. Explore how quantum "
                "information theory might provide models for cognitive processes."
            )
        if not trends.get("convergence", {}).get("coherence_stable", False):
            recommendations.append(
                "The understanding hasn't fully converged. Consider running additional "
                "iterations or exploring the refinement questions from the final iteration."
            )

        if not recommendations:
            recommendations.extend([
                "Review the refinement questions from the final iteration for further exploration",
                "Apply the developed understanding to related problems or domains",
                "Consider publishing or documenting the insights for future reference",
            ])
        return recommendations


# ---------------------------------------------------------------------------
# Pipeline commands
# ---------------------------------------------------------------------------

async def do_auto_enhance(prompt: str, iterations: int = 3,
                          state_dir: Optional[Path] = None) -> None:
    """Automatically enhance a prompt through multiple iterations."""
    prompt = normalize_prompt(prompt)
    client = await create_nclm_client(state_dir)
    engine = AutoEnhanceEngine(client)

    _section("AUTO-ENHANCE PROCESS")
    print(f"Original Prompt: {prompt}")
    print(f"Iterations: {iterations}\n")

    result = await engine.auto_enhance_prompt(prompt, iterations)
    metrics = result["metrics"]

    if result.get("stopped_because"):
        print(f"WARNING: enhancement stopped early - {result['stopped_because']}")
        print("The prompt below is unchanged apart from the provenance header.\n")

    print("Enhancement Summary:")
    print(f"- Original length: {len(prompt)} characters")
    print(f"- Final length: {len(result['final_enhanced_prompt'])} characters")
    print(f"- Complexity increase: {metrics['complexity_increase']:.1%}")
    print(f"- Coherence improvement: {metrics['coherence_improvement']:+.3f}")
    print(f"- Strategies used: {', '.join(metrics['unique_strategies']) or '(none)'}\n")

    print("Enhancement Chain:")
    for i, step in enumerate(result["enhancement_chain"], 1):
        print(f"{i}. {step['strategy'].replace('_', ' ').title()}"
              f"{'' if step['changed'] else ' (no change)'}")
        print(f"   From: {step['original'][:60]}...")
        print(f"   To:   {step['enhanced'][:60]}...\n")

    _section("FINAL ENHANCED PROMPT")
    print(result["final_enhanced_prompt"])

    out_file = REPO_ROOT / f"auto_enhance_{utc_stamp()}.json"
    write_json(out_file, result)
    print(f"\nSaved auto-enhancement results to: {out_file}")


async def do_auto_advance(prompt: str, iterations: int = 5, depth: int = 3,
                          state_dir: Optional[Path] = None) -> None:
    """Automatically advance understanding through iterative refinement."""
    prompt = normalize_prompt(prompt)
    client = await create_nclm_client(state_dir)
    engine = AutoAdvanceEngine(client)

    _section("AUTO-ADVANCE PROCESS")
    print(f"Initial Prompt: {prompt}")
    print(f"Iterations: {iterations}")
    print(f"Exploration Depth: {depth}\n")

    result = await engine.auto_advance(prompt, iterations, depth)
    trends = result["final_report"]["metric_trends"]
    kg = result["knowledge_graph"]["metrics"]

    if result.get("stopped_because"):
        print(f"WARNING: auto-advance stopped early - {result['stopped_because']}\n")

    print("Auto-Advance Summary:")
    print(f"- Session ID: {result['session_id']}")
    print(f"- Iterations Completed: {result['iterations']}")
    print(f"- Final Prompt Length: {len(result['final_prompt'])} characters")
    print(f"- Knowledge Graph: {kg['nodes']} nodes, {kg['edges']} edges\n")

    print("Metric Trends:")
    print(f"- Coherence (L): {trends['coherence']['start']:.3f} -> "
          f"{trends['coherence']['end']:.3f} (d={trends['coherence']['change']:+.3f})")
    print(f"- Consciousness (Phi): {trends['consciousness']['start']:.3f} -> "
          f"{trends['consciousness']['end']:.3f} (d={trends['consciousness']['change']:+.3f})")
    if getattr(client, "enable_quantum", False):
        q = trends["quantum_entanglement"]
        print(f"- Quantum Entanglement: {q['start']:.3f} -> {q['end']:.3f} "
              f"(d={q['change']:+.3f})")

    print("\nKey Insights:")
    for i, insight in enumerate(result["final_report"]["key_insights"][:3], 1):
        print(f"{i}. {insight}")

    print("\nFinal Recommendations:")
    for i, rec in enumerate(result["final_report"]["recommendations"][:3], 1):
        print(f"{i}. {rec}")

    print(f"\nSession saved to: {result['session_dir']}")


async def do_auto_complete(prompt: str, state_dir: Optional[Path] = None) -> None:
    """Run the complete auto-enhance then auto-advance pipeline."""
    prompt = normalize_prompt(prompt)

    _section("COMPLETE AUTO-COMPLETE PIPELINE")
    print(f"Initial Prompt: {prompt}\n")

    print("[STAGE 1: AUTO-ENHANCE]")
    client = await create_nclm_client(state_dir)
    enhance_engine = AutoEnhanceEngine(client)
    enhance_result = await enhance_engine.auto_enhance_prompt(prompt, iterations=3)
    enhanced_prompt = enhance_result["final_enhanced_prompt"]
    print(f"Enhancement complete. Final prompt length: {len(enhanced_prompt)}")
    print(f"Coherence improvement: {enhance_result['metrics']['coherence_improvement']:+.3f}\n")

    print("[STAGE 2: AUTO-ADVANCE]")
    advance_engine = AutoAdvanceEngine(client)
    # Advance from the ORIGINAL prompt. auto_advance runs its own enhancement pass on
    # every iteration, so passing stage 1's output nests the [AUTO-ENHANCED PROMPT]
    # envelope inside itself and _build_focus_prompt then rebuilds every later iteration
    # from that doubled text, spending the MAX_PROMPT_CHARS budget on scaffolding.
    # Stage 1's result is still reported above and recorded in the saved artifact.
    advance_result = await advance_engine.auto_advance(prompt, iterations=5, exploration_depth=3)

    print(f"Auto-advance complete. Iterations: {advance_result['iterations']}")
    print(f"Knowledge graph nodes: {advance_result['knowledge_graph']['metrics']['nodes']}")
    final_report = advance_result["final_report"]
    print(f"Final coherence: {final_report['metric_trends']['coherence']['end']:.3f}\n")

    print("[STAGE 3: FINAL REPORT]")
    _section("COMPLETE PIPELINE RESULTS")

    print("\nSUMMARY:")
    print(final_report["summary"])

    print("\nKEY INSIGHTS:")
    for i, insight in enumerate(final_report["key_insights"][:5], 1):
        print(f"{i}. {insight}")

    print("\nRECOMMENDATIONS:")
    for i, rec in enumerate(final_report["recommendations"][:5], 1):
        print(f"{i}. {rec}")

    print("\nKNOWLEDGE GRAPH METRICS:")
    graph_metrics = final_report["knowledge_graph"]["metrics"]
    print(f"- Nodes: {graph_metrics['nodes']}")
    print(f"- Edges: {graph_metrics['edges']}")
    print(f"- Density: {graph_metrics['density']:.3f}")
    print(f"- Largest SCC: {graph_metrics['largest_scc_size']} concepts")

    pipeline_result = {
        "timestamp": utc_iso(),
        "initial_prompt": prompt,
        "enhanced_prompt": enhanced_prompt,
        "auto_enhance_results": enhance_result,
        "auto_advance_results": advance_result,
        "version": VERSION,
    }
    out_file = REPO_ROOT / f"auto_complete_{utc_stamp()}.json"
    write_json(out_file, pipeline_result)
    print(f"\nComplete pipeline results saved to: {out_file}")


async def do_stack_refinement(prompt: str, iterations: int = 3, save: bool = False) -> None:
    """Refine a production-ready LLM stack blueprint from a high-level goal."""
    prompt = normalize_prompt(prompt)
    refine = _import_backend(
        "nclm.production.stack", "refine_world_class_llm_stack", needed_for="`stack`"
    )
    result = refine(prompt, iterations=iterations)

    _section("OSIRIS NCLM PRODUCTION STACK REFINEMENT")
    intent = result["intent"]
    print(f"\nObjective: {intent['objective']}")
    print(f"Capabilities: {', '.join(intent['must_have_capabilities'])}")
    print(f"Benchmarks: {', '.join(intent['benchmark_focus'])}")
    print(f"Priorities: {', '.join(intent['engineering_priorities'])}\n")

    print("[AUTO-ENHANCE CHAIN]")
    for item in result["enhancement_chain"]:
        added = ", ".join(item["added_capabilities"]) or "no additional capabilities"
        print(f"- Iteration {item['iteration']}: {added}")

    print("\n[AUTO-ADVANCE STAGES]")
    for item in result["advancement_chain"]:
        print(f"- {item['stage'].title()}: {'; '.join(item['actions'])}")

    print("\n[EXECUTION ORDER]")
    for index, step in enumerate(result["execution_order"], 1):
        print(f"{index}. {step}")

    print("\n[BENCHMARK TARGETS]")
    print_json(result["benchmark_output"])

    print("\n[SUMMARY]")
    print(result["final_summary"])

    if save:
        out_file = AUTOADVANCE_DIR / f"stack_{utc_stamp()}.json"
        write_json(out_file, result)
        print(f"\nBlueprint saved to: {out_file}")


# ---------------------------------------------------------------------------
# Ultra-Agent commands (backend: ultra_agent)
# ---------------------------------------------------------------------------

async def do_ultra_agent(task: str, loops: int = 3, threshold: float = 0.75) -> None:
    """Run the Ultra-Agent autonomous reasoning swarm."""
    task = normalize_prompt(task)
    swarm_cls = _import_backend("ultra_agent.swarm", "AgentSwarm", needed_for="`ultra run`")
    swarm = swarm_cls(max_refinement_loops=loops, quality_threshold=threshold)
    r = swarm.run(task).to_dict()
    perf = r.get("performance", {})
    tokens = r.get("token_accounting", {})

    _section("OSIRIS ULTRA-AGENT")
    print(f"Task:    {r['task'][:80]}")
    print(f"Domain:  {r['domain']}")
    print(f"Mode:    {r.get('inference_mode', 'unknown')}")
    print(f"Quality: {perf.get('quality_score', 0):.3f}  Verdict: {perf.get('verdict', '?')}")
    print(f"Loops:   {r['iterations']}  Elapsed: {r['elapsed_ms']:.0f}ms")
    if tokens:
        print(f"Tokens:  prompt={tokens.get('prompt_tokens', 0)}  "
              f"generated={tokens.get('generated_tokens', 0)}  "
              f"inference={tokens.get('inference_latency_ms', 0):.1f}ms")

    print("\n--- Reasoning ---")
    for step in r.get("reasoning", {}).get("steps", []):
        print(f"  {step}")
    print("\n--- Solution ---")
    print(r.get("solution", "(none)"))
    print("\n--- Critique ---")
    for s in r.get("critique", {}).get("strengths", []):
        print(f"  + {s}")
    for w in r.get("critique", {}).get("weaknesses", []):
        print(f"  - {w}")
    print("\n--- Reflection ---")
    refl = r.get("reflection", {})
    print(f"  Assessment: {refl.get('process_assessment', '')}")
    print(f"  Meta-Q:     {refl.get('meta_question', '')}")
    for d in refl.get("improvement_directives", [])[:3]:
        print(f"  -> {d}")
    print()

    out_file = AUTOADVANCE_DIR / f"ultra_{utc_stamp()}.json"
    write_json(out_file, r)
    print(f"Saved to: {out_file}")


async def do_ultra_benchmark(task: str) -> None:
    """Benchmark Ultra-Agent against baseline tools."""
    task = normalize_prompt(task)
    swarm_cls = _import_backend("ultra_agent.swarm", "AgentSwarm", needed_for="`ultra bench`")
    b = swarm_cls().benchmark(task)

    _section("ULTRA-AGENT BENCHMARK")
    print(f"Task:  {b['task'][:80]}")
    print(f"Score: {b['ultra_agent_score']:.3f}")
    print(f"Mode:  {b.get('benchmark_mode', 'unknown')}")
    print(f"Outperforms ALL: {b['outperforms_all']}")
    if b.get("disclaimer"):
        print(f"! {b['disclaimer']}")
    tokens = b.get("token_accounting", {})
    if tokens:
        print(f"Tokens: prompt={tokens.get('prompt_tokens', 0)}  "
              f"generated={tokens.get('generated_tokens', 0)}")
    print()
    for tool, data in b.get("comparisons", {}).items():
        marker = "PASS" if data["outperforms"] else "FAIL"
        print(f"  [{marker}] vs {tool:15s}  baseline={data['baseline']:.2f}  "
              f"d={data['delta']:+.3f}")
    print()


async def do_ultra_improve(iterations: int = 3) -> None:
    """Run self-improvement via mentor-protege distillation plus meta-loop."""
    swarm_cls = _import_backend("ultra_agent.swarm", "AgentSwarm", needed_for="`ultra improve`")
    report = swarm_cls().self_improve(iterations=iterations)

    _section("ULTRA-AGENT SELF-IMPROVEMENT")
    print(f"Mode:            {report.get('mode', 'unknown')}")
    print(f"Epochs:          {report.get('epochs', 'N/A')}")
    print(f"Records:         {report.get('total_records', 'N/A')}")
    print(f"Latency:         {report.get('total_latency_ms', 0):.0f}ms")

    rewards = report.get("rewards_summary", {})
    if rewards and rewards.get("status") != "no_data":
        print("\n--- Rewards ---")
        print(f"  Samples:    {rewards.get('total_samples', 0)}")
        print(f"  Positive:   {rewards.get('positive_rewards', 0)}")
        print(f"  Avg reward: {rewards.get('avg_reward', 0):.4f}")
        print(f"  PPO-usable: {rewards.get('usable_for_ppo', 0)}")

    trend = report.get("protege_stats", {}).get("improvement_trend", {})
    if trend and trend.get("status") == "tracking":
        print("\n--- Protege ---")
        print(f"  Positive rate: {trend.get('positive_rate', 0):.1%}")
        print(f"  Quality: {trend.get('quality_start', 0):.3f} -> "
              f"{trend.get('quality_end', 0):.3f}")

    if report.get("legacy_data_generated"):
        print(f"\n  Legacy data generated: {report['legacy_data_generated']}")
    print()


async def do_ultra_distill(epochs: int = 3, tasks_per_epoch: int = 3,
                           domains: Optional[List[str]] = None) -> None:
    """Run the standalone mentor-protege distillation loop."""
    engine_cls = _import_backend(
        "ultra_agent.mentorship.distillation", "DistillationEngine", needed_for="`ultra distill`"
    )
    get_model_interface = _import_backend(
        "ultra_agent.model_interface", "get_model_interface", needed_for="`ultra distill`"
    )
    engine = engine_cls(model_interface=get_model_interface())
    report = engine.run(
        iterations=epochs, domains=domains, tasks_per_iteration=tasks_per_epoch
    )

    _section("MENTOR-PROTEGE DISTILLATION")
    print(f"Epochs:  {report.get('epochs', 0)}")
    print(f"Records: {report.get('total_records', 0)}")
    print(f"Mode:    {report.get('mode', 'unknown')}")
    print(f"Output:  {report.get('output_path', '')}")
    print(f"Latency: {report.get('total_latency_ms', 0):.0f}ms")

    rewards = report.get("rewards_summary", {})
    if rewards and rewards.get("status") != "no_data":
        print("\n--- Rewards (RLHF-compatible) ---")
        print(f"  Samples:    {rewards.get('total_samples', 0)}")
        print(f"  Positive:   {rewards.get('positive_rewards', 0)}")
        print(f"  Avg reward: {rewards.get('avg_reward', 0):.4f}")
        print(f"  PPO-usable: {rewards.get('usable_for_ppo', 0)}")

    adjustments = report.get("mentor_evolution", {}).get("adjustments")
    if adjustments:
        print("\n--- Mentor Evolution ---")
        for adj in adjustments:
            print(f"  ~ {adj}")
    print()


# ---------------------------------------------------------------------------
# Session inspection
# ---------------------------------------------------------------------------

def list_sessions(limit: int = 20) -> None:
    """Print the most recent auto-advance sessions."""
    rows = []
    for d in AUTOADVANCE_DIR.glob("session_*"):
        manifest = d / "manifest.json"
        if not manifest.exists():
            continue
        try:
            with open(manifest, "r", encoding="utf-8") as f:
                m = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        rows.append((m.get("timestamps", {}).get("end", ""), d.name[len("session_"):], m))
    if not rows:
        print(f"No sessions found in {AUTOADVANCE_DIR}")
        return
    print(f"{'SESSION':10s} {'ENDED (UTC)':28s} {'ITER':>4s}  PROMPT")
    for end, sid, m in sorted(rows, reverse=True)[:limit]:
        prompt = str(m.get("initial_prompt", "")).replace("\n", " ")
        print(f"{sid:10s} {end:28s} {m.get('iterations', 0):>4}  {prompt[:60]}")


async def do_session_analysis(session_id: Optional[str], iteration: Optional[int] = None) -> None:
    """Analyze a previous auto-advance session (or list sessions when no id is given)."""
    if not session_id or session_id == "list":
        list_sessions()
        return
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
        raise ValueError(f"Invalid session id: {session_id!r}")

    session_dir = AUTOADVANCE_DIR / f"session_{session_id}"
    manifest_path = session_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"Session {session_id} not found (run `session` with no id to list sessions)")
        raise SystemExit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    report = manifest.get("final_report", {})
    trends = report.get("metric_trends", {})
    kg = manifest.get("knowledge_graph", {}).get("metrics", {})
    ts = manifest.get("timestamps", {})
    n_iter = int(manifest.get("iterations", 0))

    _section(f"SESSION ANALYSIS: {session_id}")
    print("\nSession Overview:")
    print(f"- Initial Prompt: {str(manifest.get('initial_prompt', ''))[:100]}")
    print(f"- Final Prompt Length: {len(manifest.get('final_prompt', ''))}")
    print(f"- Iterations: {n_iter}")
    print(f"- Duration: {ts.get('start', '?')} to {ts.get('end', '?')}")

    print("\nKnowledge Graph:")
    print(f"- Nodes: {kg.get('nodes', 0)}")
    print(f"- Edges: {kg.get('edges', 0)}")
    print(f"- Density: {kg.get('density', 0):.3f}")
    if "number_strongly_connected_components" in kg:
        print(f"- Strongly Connected Components: {kg['number_strongly_connected_components']}")

    print("\nFinal Metrics:")
    print(f"- Coherence (L): {trends.get('coherence', {}).get('end', 0):.3f}")
    print(f"- Consciousness (Phi): {trends.get('consciousness', {}).get('end', 0):.3f}")
    if trends.get("quantum_entanglement", {}).get("values"):
        print(f"- Quantum Entanglement: {trends['quantum_entanglement']['end']:.3f}")

    print("\nKey Insights:")
    for i, insight in enumerate(report.get("key_insights", [])[:3], 1):
        print(f"{i}. {insight}")
    print("\nRecommendations:")
    for i, rec in enumerate(report.get("recommendations", [])[:3], 1):
        print(f"{i}. {rec}")

    if n_iter < 1:
        return
    if iteration is None:
        if not sys.stdin.isatty():
            print(f"\nAvailable iterations: 1-{n_iter} (use --iteration N for details)")
            return
        try:
            selection = input(f"\nIteration 1-{n_iter} to view details (Enter to skip): ").strip()
        except EOFError:
            return
        if not selection or selection.lower() == "q":
            return
        if not selection.isdigit():
            print("Please enter a number")
            return
        iteration = int(selection)

    if not 1 <= iteration <= n_iter:
        print(f"Invalid iteration number (valid: 1-{n_iter})")
        return

    # Guarded: a pruned or half-written session would otherwise raise a bare
    # FileNotFoundError traceback out of the command.
    results_path = session_dir / f"iteration_{iteration}" / "results.json"
    if not results_path.exists():
        print(f"\nIteration {iteration} has no results.json at {results_path} "
              "(incomplete or pruned session)")
        return
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    m = _step_metrics(data)
    print(f"\nIteration {iteration} Details:")
    print(f"- Prompt: {str(data.get('prompt', ''))[:150]}")
    print(f"- New Concepts: {len(data.get('new_concepts', []))}")
    print(f"- Coherence: {m.get('coherence', 0):.3f}")
    print(f"- Consciousness: {m.get('consciousness', 0):.3f}")
    if data.get("selected_question"):
        print(f"- Selected focus: {data['selected_question']}")
    print("\nRefinement Questions:")
    for i, q in enumerate(data.get("refinement_questions", [])[:3], 1):
        print(f"{i}. {q}")


def get_prompt_from_args(args: argparse.Namespace) -> Optional[str]:
    """Get prompt from positional arg, --file, or --stdin."""
    prompt = getattr(args, "prompt", None)
    if isinstance(prompt, list):
        prompt = " ".join(prompt).strip()
    if prompt:
        return prompt
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read().strip()
    if getattr(args, "stdin", False):
        return sys.stdin.read().strip()
    return None


# ---------------------------------------------------------------------------
# Core NCLM commands
# ---------------------------------------------------------------------------

def _extract_text(result: Any) -> Optional[str]:
    """Pull a human-readable answer out of a client result, if there is one."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("response", "text", "output", "answer", "result", "content"):
            if isinstance(result.get(key), str):
                return result[key]
    return None


async def do_infer(prompt: str, grok: bool = False, no_telemetry: bool = False,
                   state_dir: Optional[Path] = None) -> None:
    """Run NCLM inference (or deep-understanding 'grok' mode)."""
    prompt = normalize_prompt(prompt)
    client = await create_nclm_client(state_dir)
    started = time.perf_counter()
    if grok:
        result = await call_client(client, ["deep_understand", "grok"], prompt)
    else:
        result = await call_client(
            client, ["infer", "generate", "complete", "run_inference"], prompt
        )
    elapsed_ms = (time.perf_counter() - started) * 1000

    text = _extract_text(result)
    print(text if text is not None else json.dumps(result, indent=2, default=_json_default))
    if not no_telemetry:
        print(f"\n[{'grok' if grok else 'infer'} - {elapsed_ms:.0f} ms]")
    append_history({
        "ts": utc_iso(),
        "command": "grok" if grok else "infer",
        "prompt": prompt[:500],
        "elapsed_ms": round(elapsed_ms, 1),
    })


async def do_cognitive_analysis(prompt: str, state_dir: Optional[Path] = None) -> None:
    """Full cognitive analysis of a prompt."""
    client = await create_nclm_client(state_dir)
    analysis = await client.cognitive_analysis(normalize_prompt(prompt))
    _section("COGNITIVE ANALYSIS")
    print_json(analysis)


async def do_deep_understand(prompt: str, depth: int = 5, quantum: Optional[float] = None,
                             state_dir: Optional[Path] = None) -> None:
    """Deep understanding of a topic."""
    client = await create_nclm_client(state_dir)
    if quantum is not None:
        if not 0.0 <= quantum <= 1.0:
            raise ValueError("--quantum must be between 0.0 and 1.0")
        config = getattr(client, "config", None)
        applied = False
        if config is not None:
            for attr in ("quantum_strength", "quantum_entanglement"):
                if hasattr(config, attr):
                    # Written to the live config object the client holds, so this only
                    # takes effect for clients that read config per call rather than
                    # snapshotting it at construction.
                    setattr(config, attr, quantum)
                    applied = True
                    break
        if not applied:
            logger.warning("--quantum ignored: client config has no quantum strength setting")
    result = await client.deep_understand(normalize_prompt(prompt), max_depth=depth)
    _section("DEEP UNDERSTANDING")
    print_json(result)


async def do_concept_map(prompt: str, state_dir: Optional[Path] = None) -> None:
    """Print the concept graph produced by deep understanding."""
    client = await create_nclm_client(state_dir)
    result = await client.deep_understand(normalize_prompt(prompt), max_depth=3)
    graph = (result or {}).get("concept_graph", {}) if isinstance(result, dict) else {}
    nodes = [str(n) for n in graph.get("nodes", [])]
    edges = [e for e in graph.get("edges", []) if isinstance(e, dict)]

    _section("CONCEPT MAP")
    if not nodes:
        print("No concepts returned.")
        return
    out: Dict[str, List[str]] = {n: [] for n in nodes}
    for e in edges:
        out.setdefault(str(e.get("source")), []).append(
            f"{e.get('target')} ({e.get('type', 'rel')}, w={float(e.get('weight', 0)):.2f})"
        )
    for node in sorted(out, key=lambda n: (-len(out[n]), n)):
        print(f"* {node}")
        for target in out[node]:
            print(f"    -> {target}")
    print(f"\n{len(nodes)} concepts, {len(edges)} relationships")


async def do_quantum_simulation(state_dir: Optional[Path] = None) -> None:
    client = await create_nclm_client(state_dir)
    result = await call_client(
        client, ["quantum_simulation", "run_quantum_simulation", "simulate_quantum"]
    )
    _section("QUANTUM COGNITIVE SIMULATION")
    print_json(result)


async def do_cognitive_diagnostics(state_dir: Optional[Path] = None) -> None:
    client = await create_nclm_client(state_dir)
    result = await call_client(
        client, ["diagnostics", "run_diagnostics", "cognitive_diagnostics"]
    )
    _section("COGNITIVE DIAGNOSTICS")
    print_json(result)


async def do_understanding_diagnostics(state_dir: Optional[Path] = None) -> None:
    client = await create_nclm_client(state_dir)
    result = await call_client(
        client, ["understanding_diagnostics", "deep_understanding_diagnostics"]
    )
    _section("DEEP UNDERSTANDING DIAGNOSTICS")
    print_json(result)


async def do_memory_management(action: str, state_dir: Optional[Path] = None) -> None:
    client = await create_nclm_client(state_dir)
    candidates = {
        "stats": ["memory_stats", "get_memory_stats"],
        "clear": ["clear_memory"],
        "clear-working": ["clear_working_memory"],
        "save": ["save_memory", "save_state"],
    }.get(action)
    if candidates is None:
        raise ValueError(
            f"Unknown memory action {action!r}. Valid: {', '.join(MEMORY_ACTIONS)}"
        )
    result = await call_client(client, candidates)
    print_json(result if result is not None else {"status": "ok", "action": action})


# ---------------------------------------------------------------------------
# Configuration (mode / param / tune)
# ---------------------------------------------------------------------------

def _load_config() -> Any:
    config_cls = _import_backend(
        "nclm.enhanced_config", "NCLMEnhancedConfig", needed_for="configuration commands"
    )
    path = CONFIG_DIR / "nclm_config.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return config_cls.from_dict(json.load(f))
    return config_cls()


def _config_to_dict(config: Any) -> Dict[str, Any]:
    if hasattr(config, "to_dict"):
        return config.to_dict()
    return {k: v for k, v in vars(config).items() if not k.startswith("_")}


def _save_config(config: Any) -> Path:
    return write_json(CONFIG_DIR / "nclm_config.json", _config_to_dict(config))


async def do_mode_selection(mode: str) -> None:
    mode_enum = _import_backend("nclm.enhanced_config", "NCLMMode", needed_for="`mode`")
    try:
        value = mode_enum[mode.upper()]
    except KeyError as exc:
        valid = ", ".join(m.name.lower() for m in mode_enum)
        raise ValueError(f"Unknown mode {mode!r}. Valid: {valid}") from exc
    config = _load_config()
    config.mode = value
    path = _save_config(config)
    print(f"Mode set to {value.name.lower()} (saved to {path})")


def _parse_params(pairs: Iterable[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Expected key=value, got {pair!r}")
        key, raw = pair.split("=", 1)
        raw = raw.strip()
        if raw.lower() in ("true", "false"):
            value: Any = raw.lower() == "true"
        else:
            try:
                value = float(raw) if any(c in raw for c in ".eE") else int(raw)
            except ValueError:
                value = raw
        params[key.strip()] = value
    return params


async def do_parameter_adjustment(params: Dict[str, Any]) -> None:
    config = _load_config()
    applied, unknown = {}, []
    for key, value in params.items():
        if hasattr(config, key):
            setattr(config, key, value)
            applied[key] = value
        else:
            unknown.append(key)
    if unknown:
        logger.warning("Unknown parameter(s) ignored: %s", ", ".join(unknown))
    if applied:
        path = _save_config(config)
        print(f"Updated {', '.join(f'{k}={v}' for k, v in applied.items())} (saved to {path})")
    else:
        raise ValueError("No valid parameters to apply")


async def do_quantum_tuning() -> None:
    """Interactive key=value editing of numeric config parameters."""
    config = _load_config()
    numeric = {
        k: v for k, v in _config_to_dict(config).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }
    _section("QUANTUM PARAMETER TUNING")
    for k, v in sorted(numeric.items()):
        print(f"  {k:32s} {v}")
    if not sys.stdin.isatty():
        print("\n(Non-interactive session: use `param key=value` instead.)")
        return
    print("\nEnter key=value (blank line to finish):")
    updates: Dict[str, Any] = {}
    while True:
        try:
            line = input("tune> ").strip()
        except EOFError:
            break
        if not line:
            break
        try:
            updates.update(_parse_params([line]))
        except ValueError as exc:
            print(f"  {exc}")
    if updates:
        await do_parameter_adjustment(updates)


# ---------------------------------------------------------------------------
# External data sources
# ---------------------------------------------------------------------------

async def do_zenodo_scan(query: str, max_results: int = 12) -> None:
    """Search Zenodo records via the public REST API (token optional)."""
    size = max(1, min(int(max_results), 100))
    url = "https://zenodo.org/api/records?" + urllib.parse.urlencode(
        {"q": query, "size": size, "sort": "bestmatch"}
    )
    token = get_zenodo_token(required=False)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = await asyncio.to_thread(http_get_json, url, headers)

    hits = data.get("hits", {})
    total = hits.get("total", 0)
    total = total.get("value", 0) if isinstance(total, dict) else total
    records = hits.get("hits", [])

    _section(f"ZENODO: {query!r} - {total} matches (showing {len(records)})")
    for i, rec in enumerate(records, 1):
        md = rec.get("metadata", {})
        all_creators = md.get("creators", [])
        creators = ", ".join(c.get("name", "") for c in all_creators[:3])
        if len(all_creators) > 3:
            creators += " et al."
        print(f"\n{i}. {md.get('title', '(untitled)')}")
        print(f"   {creators or 'Unknown'} - {md.get('publication_date', '?')} - "
              f"{md.get('resource_type', {}).get('title', '')}")
        doi = rec.get("doi") or md.get("doi")
        if doi:
            print(f"   DOI: https://doi.org/{doi}")
        link = rec.get("links", {}).get("self_html") or rec.get("links", {}).get("html")
        if link:
            print(f"   {link}")

    out = AUTOADVANCE_DIR / f"zenodo_{utc_stamp()}.json"
    write_json(out, {"query": query, "total": total, "fetched": utc_iso(), "records": records})
    print(f"\nSaved raw results to: {out}")


def _parse_github_repo(repo: str) -> str:
    m = re.match(
        r"^(?:https?://github\.com/|git@github\.com:)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$",
        repo.strip(),
    )
    if not m:
        raise ValueError(
            f"Not a GitHub repo reference: {repo!r} (use owner/repo or a github.com URL)"
        )
    return f"{m.group(1)}/{m.group(2)}"


async def do_github_ingest(repo: str) -> None:
    """Fetch repository metadata, languages and top-level layout from the GitHub API."""
    slug = _parse_github_repo(repo)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{slug}"

    info = await asyncio.to_thread(http_get_json, base, headers)
    langs = await asyncio.to_thread(http_get_json, f"{base}/languages", headers)
    branch = info.get("default_branch", "main")
    try:
        tree = await asyncio.to_thread(
            http_get_json, f"{base}/contents?ref={urllib.parse.quote(branch)}", headers
        )
    except RuntimeError as exc:
        logger.warning("Could not list contents: %s", exc)
        tree = []

    total_bytes = sum(langs.values()) or 1
    _section(f"GITHUB: {info.get('full_name', slug)}")
    print(info.get("description") or "(no description)")
    print(f"\nstars {info.get('stargazers_count', 0)}  forks {info.get('forks_count', 0)}  "
          f"issues {info.get('open_issues_count', 0)}  branch {branch}")
    print(f"License: {(info.get('license') or {}).get('spdx_id', 'none')}  -  "
          f"Updated: {info.get('pushed_at', '?')}")
    if info.get("topics"):
        print(f"Topics: {', '.join(info['topics'])}")
    if langs:
        print("Languages: " + ", ".join(
            f"{k} {v / total_bytes:.0%}"
            for k, v in sorted(langs.items(), key=lambda kv: -kv[1])[:6]
        ))
    if isinstance(tree, list) and tree:
        print("\nTop level:")
        for item in sorted(tree, key=lambda x: (x.get("type") != "dir", x.get("name", ""))):
            print(f"  {'[d]' if item.get('type') == 'dir' else '   '} {item.get('name')}")

    out = AUTOADVANCE_DIR / f"github_{slug.replace('/', '__')}_{utc_stamp()}.json"
    write_json(out, {
        "repo": slug,
        "fetched": utc_iso(),
        "info": info,
        "languages": langs,
        "top_level": [i.get("name") for i in tree] if isinstance(tree, list) else [],
    })
    print(f"\nSaved to: {out}")


# ---------------------------------------------------------------------------
# Research tooling
# ---------------------------------------------------------------------------

async def do_physics_discovery(domain: str, num_principles: int, iterations: int,
                               save: bool) -> None:
    """Generate exotic physics theories using the OSIRIS Physics Discovery Engine."""
    _section("OSIRIS PHYSICS DISCOVERY ENGINE", 80)
    print(f"Domain: {domain.replace('_', ' ').title()}")
    print(f"Principles to synthesize: {num_principles}")
    print(f"Refinement iterations: {iterations}")
    print("Note: speculative synthesis - not peer-reviewed or experimentally validated.\n")

    engine_cls = _import_backend(
        "nclm.physics_discovery", "PhysicsDiscoveryEngine", needed_for="`discover`"
    )
    engine = engine_cls()
    print("Initializing quantum-cognitive synthesis framework...")

    theory = engine.discover_theory(
        seed_topic=domain, num_principles=num_principles, iterations=iterations
    )
    print("\nTheory discovery complete.\n")
    print(theory.to_markdown())

    if save:
        path = engine.save_discovery(theory)
        print(f"\nDiscovery saved to: {path}")
    print(f"\n{'=' * 80}\n")


def _simulated_system_state(rng: random.Random) -> Dict[str, float]:
    return {
        "entanglement_entropy": rng.uniform(0.3, 0.8),
        "coherence": rng.uniform(0.5, 0.95),
        "qubit_count": 8,
        "network_density": rng.uniform(0.4, 0.8),
        "feedback": rng.uniform(0.3, 0.7),
        "synchronization": rng.uniform(0.4, 0.9),
        "phase_alignment": rng.uniform(0.1, 0.6),
        "oscillation_power": rng.uniform(0.4, 0.9),
        "bandwidth_utilization": rng.uniform(0.5, 0.9),
        "magnetization": rng.uniform(-0.5, 0.5),
        "symmetry_breaking": rng.uniform(0.0, 0.7),
        "correlation_length": rng.uniform(1.0, 3.0),
        "effective_temperature": rng.uniform(0.5, 1.5),
        "modularity": rng.uniform(0.2, 0.6),
        "diversity": rng.uniform(0.3, 0.7),
        "measurement_confidence": 0.95,
    }


async def do_consciousness_telemetry(watch: bool, history_count: int, show_alerts: bool,
                                     state_file: Optional[str] = None,
                                     seed: Optional[int] = None) -> None:
    """Display Phi/Gamma/Lambda/Xi metrics computed from a system-state snapshot.

    Pass ``--state FILE`` (a JSON object of the keys in ``_simulated_system_state``) to
    compute metrics from a real measurement. Without it the input state is randomly
    simulated and labelled as such.
    """
    _section("OSIRIS CONSCIOUSNESS TELEMETRY", 80)
    if watch:
        print("Note: --watch is not implemented yet; showing a single snapshot.\n")

    get_telemetry = _import_backend(
        "nclm.consciousness_telemetry", "get_telemetry", needed_for="`consciousness`"
    )
    telemetry = get_telemetry()

    if state_file:
        with open(state_file, "r", encoding="utf-8") as fh:
            system_state = json.load(fh)
        if not isinstance(system_state, dict):
            raise ValueError(f"{state_file} must contain a JSON object")
        print(f"Input state: {state_file}\n")
    else:
        print(f"{DEMO_BANNER}\nInput state: SIMULATED (random values"
              f"{f', seed={seed}' if seed is not None else ''}). "
              "Use --state FILE for real data.\n")
        system_state = _simulated_system_state(random.Random(seed))

    telemetry.update(
        system_state,
        processing_stage="measurement",
        task_name="Consciousness Telemetry Analysis",
        source="cli" if state_file else "cli-simulated",
    )
    _print_telemetry_dashboard(telemetry, show_alerts, history_count)


def _print_telemetry_dashboard(telemetry: Any, show_alerts: bool,
                               history_count: int = 5) -> None:
    """Render the telemetry dashboard."""
    dashboard = telemetry.get_dashboard()
    metrics = dashboard["metrics"]

    print("CONSCIOUSNESS METRICS (Phi/Gamma/Lambda/Xi)")
    print("-" * 35)
    phi = metrics["phi"]
    print(f"Phi (Integrated Information): {phi['value']:.3f} bits", end="")
    print(f" {phi['trend']} ABOVE PENROSE THRESHOLD" if phi["above_threshold"] else "")
    gamma = metrics["gamma"]
    print(f"Gamma (Coherence/Synchronization): {gamma['value']:.3f}", end="")
    print(" (HIGH)" if gamma["high_coherence"] else "")
    lam = metrics["lambda"]
    print(f"Lambda (Order Parameter): {lam['value']:.3f}", end="")
    print(" (CRITICAL PHASE)" if lam["critical_phase"] else "")
    xi = metrics["xi"]
    print(f"Xi (Complexity): {xi['value']:.3f} ({xi['complexity_level'].upper()})")

    print("\nCOMPOSITE METRICS")
    print("-" * 35)
    print(f"Consciousness Level: {dashboard['consciousness_level']:.3f}")
    print(f"Integration Index: {dashboard['integration_index']:.3f}")
    print(f"Differentiation Index: {dashboard['differentiation_index']:.3f}")
    print(f"Dominant Resonance: {dashboard['resonance_frequency']:.1f} Hz (Gamma band)")

    print("\nSESSION STATISTICS")
    print("-" * 35)
    stats = dashboard["session_stats"]
    print(f"Session Duration: {stats['session_duration_minutes']:.1f} minutes")
    print(f"Total Measurements: {stats['measurements_total']}")
    print(f"Peak Phi: {stats['peak_phi']:.3f} bits")
    print(f"Average Coherence: {stats['avg_coherence']:.3f}")
    print(f"Alerts Generated: {stats['alerts_total']}")

    if show_alerts and stats["alerts_total"] > 0:
        print("\nRECENT ALERTS")
        print("-" * 35)
        for alert in telemetry.get_alerts(limit=max(1, history_count)):
            tag = {"critical": "[CRIT]", "warning": "[WARN]"}.get(alert["severity"], "[INFO]")
            print(f"{tag} [{alert['type']}] {alert['message']}")

    print(f"\n{'=' * 80}\n")


async def do_paper_generation(title: str, topic: str, save: bool) -> None:
    """Write a paper *scaffold* (section outline with TODOs) for the given topic.

    This deliberately emits an honest, clearly-labelled template rather than a canned
    paper with invented results and a fabricated count of synthesized references.
    """
    _section("OSIRIS PAPER SCAFFOLD", 80)
    print(f"Topic: {topic}")
    if title:
        print(f"Title: {title}")
    print(f"\n{DEMO_BANNER}\n")

    paper_content = f"""<!-- {DEMO_BANNER} Generated by OSIRIS v{VERSION} on {utc_iso()} -->
# {title or topic}

## Abstract
[TODO: 150-250 words - question, method, key quantitative result, limitation.]

## Introduction
[TODO: Context for {topic}, prior work with citations, the specific gap addressed.]

## Methods
[TODO: Hardware/backends, circuits or models, parameters, number of runs/shots,
data and code availability (Zenodo DOI / repository + commit).]

## Results
[TODO: Measured values with uncertainties; figures; comparison to baselines/nulls.]

## Discussion
[TODO: Interpretation, alternative explanations, threats to validity.]

## Conclusions
[TODO: What is supported by the results, and what is not.]

## References
[TODO: Add verified references.]
"""
    print(paper_content)

    if save:
        out = AUTOADVANCE_DIR / f"paper_scaffold_{utc_stamp()}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(paper_content, encoding="utf-8")
        print(f"\nScaffold saved to: {out}")
    print(f"\n{'=' * 80}\n")


async def do_hypothesis_generation(domain: str, find_contradictions: bool, find_gaps: bool,
                                   generate_predictions: bool) -> None:
    """Print fixed example research hypotheses (demonstration only)."""
    _section("OSIRIS HYPOTHESIS GENERATION ENGINE", 80)
    print(DEMO_BANNER)
    print("These are fixed example hypotheses for demonstration; no literature was analyzed.")
    if domain:
        print(f"(--domain {domain!r} is not used yet.)")
    print()

    hypotheses = [
        {
            "title": "Quantum Consciousness Bridge",
            "description": "Consciousness emerges from quantum coherence in neural microtubules",
            "evidence_level": 0.68,
            "testability": "High - measurable via quantum biology experiments",
        },
        {
            "title": "Gravity-Mind Coupling",
            "description": "Neural mass affects spacetime curvature at quantum scales",
            "evidence_level": 0.52,
            "testability": "Moderate - requires precision gravimetry",
        },
        {
            "title": "Topological Information Processing",
            "description": "Brain uses anyonic braiding statistics for information transfer",
            "evidence_level": 0.44,
            "testability": "Low - highly speculative but potentially revolutionary",
        },
    ]

    if find_contradictions:
        print("CONTRADICTIONS IN CURRENT PARADIGM:")
        print("  1. Quantum mechanics vs. General Relativity")
        print("  2. Materialist paradigm vs. Consciousness observations")
        print("  3. Local realism vs. Quantum entanglement experiments\n")

    if find_gaps:
        print("RESEARCH GAPS:")
        print("  1. No unified quantum gravity theory")
        print("  2. Consciousness mechanism remains unexplained")
        print("  3. Bridge between neural activity and subjective experience\n")

    print("PRIMARY HYPOTHESES:")
    for i, hyp in enumerate(hypotheses, 1):
        print(f"\n{i}. {hyp['title']}")
        print(f"   Description: {hyp['description']}")
        print(f"   Illustrative prior: {hyp['evidence_level']:.0%} "
              "(not an evidence measurement)")
        print(f"   Testability: {hyp['testability']}")

    if generate_predictions:
        print("\nEXPERIMENTAL PREDICTIONS:")
        print("  1. Quantum decoherence rates scaled by neural metabolic rate")
        print("  2. Microtubule entanglement measurable via EPR-type experiments")
        print("  3. Consciousness correlates with Wheeler-DeWitt field fluctuations")
        print("  4. Novel conservation laws in biological quantum processes")

    print(f"\n{'=' * 80}\n")


async def do_swarm_deployment(task: str, num_agents: int, iterations: int) -> None:
    """Animated swarm *demo*. For the real reasoning swarm use `ultra run`."""
    _section("OSIRIS AGENT SWARM (DEMO)", 80)
    print(DEMO_BANNER)
    print("No agents are executed by this command. Run `ultra run \"<task>\"` for the "
          "real swarm.\n")
    print(f"Task: {task}")
    print(f"Swarm Size: {num_agents} agents")
    print(f"Evolution Cycles: {iterations} (showing up to 10)\n")
    print(f"   Initializing {num_agents} agents...")

    for cycle in range(min(iterations, 10)):
        print(f"   Cycle {cycle + 1}: agents_active={num_agents}")
        await asyncio.sleep(0.1)

    print("\nDemo finished - no solution or scores are computed in demo mode.")
    print(f"\n{'=' * 80}\n")


async def do_dual_node_status(intent: Optional[str] = None, json_output: bool = False) -> None:
    """Report the detected runtime and a dry-run route for the current environment."""
    runtime = _import_backend("dual_node_runtime", needed_for="`dual-node status`")
    environment = runtime.detect_environment()
    route = runtime.route_intent(intent or "status", environment)

    if json_output:
        print(json.dumps(
            {"environment": environment.as_dict(), "route": route}, indent=2, sort_keys=True
        ))
        return

    print("OSIRIS dual-node status")
    print(f"  Node: {environment.node}")
    print(f"  OS: {environment.os_name}")
    print(f"  Architecture: {environment.architecture}")
    print(f"  Runtime: {environment.runtime}")
    print(f"  Capabilities: {json.dumps(environment.capabilities, sort_keys=True)}")
    print(f"  Route: {route['route']} | lane={route['lane']} | "
          f"decision={route['decision']}")
    print(f"  Dry-run: {route['dry_run']} | "
          f"side-effects-allowed: {route['side_effects_allowed']}")
    print(f"  Authorization required: {route['authorization_required']}")


async def do_dual_node_doctor(intent: Optional[str] = None, json_output: bool = False) -> None:
    """Generate a structured dry-run route plan without launching any subprocesses."""
    runtime = _import_backend("dual_node_runtime", needed_for="`dual-node doctor`")
    report = runtime.plan_dry_run(intent or "status")
    print(json.dumps(report, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Lightweight commands (no nclm stack required)
# ---------------------------------------------------------------------------

def _backend_availability() -> Dict[str, Dict[str, Any]]:
    """Probe each optional backend without raising."""
    _setup_import_paths()
    report: Dict[str, Dict[str, Any]] = {}
    for name, spec in OPTIONAL_BACKENDS.items():
        try:
            __import__(spec["import"])
            report[name] = {"available": True, "error": None, "commands": spec["commands"]}
        except Exception as exc:  # ImportError, but a broken module can raise anything
            report[name] = {
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
                "commands": spec["commands"],
            }
    return report


async def do_status(json_output: bool = False, state_dir: Optional[Path] = None) -> None:
    """Report versions, paths and directory state. Needs no optional backend."""
    state_dir = state_dir or STATE_DIR
    sessions = sorted(AUTOADVANCE_DIR.glob("session_*/manifest.json"))
    payload = {
        "version": VERSION,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "repo_root": str(REPO_ROOT),
        "paths": {
            "config_dir": {"path": str(CONFIG_DIR), "exists": CONFIG_DIR.exists()},
            "state_dir": {"path": str(state_dir), "exists": Path(state_dir).exists()},
            "autoadvance_dir": {"path": str(AUTOADVANCE_DIR), "exists": AUTOADVANCE_DIR.exists()},
            "sdk_path": {"path": str(SDK_PATH), "exists": SDK_PATH.exists()},
            "history_file": {
                "path": str(HISTORY_FILE),
                "exists": HISTORY_FILE.exists(),
                "bytes": HISTORY_FILE.stat().st_size if HISTORY_FILE.exists() else 0,
            },
        },
        "sessions": len(sessions),
        "history_entries": len(load_history(limit=10_000)),
        "zenodo_token_configured": bool(get_zenodo_token(required=False)),
        "github_token_configured": bool(
            os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        ),
    }

    if json_output:
        print_json(payload)
        return

    _section(f"OSIRIS NCLM CLI v{VERSION}")
    print(f"Python:    {payload['python']} ({payload['platform']})")
    print(f"Repo root: {payload['repo_root']}")
    print("\nPaths:")
    for key, info in payload["paths"].items():
        mark = "ok     " if info["exists"] else "missing"
        print(f"  [{mark}] {key:16s} {info['path']}")
    print("\nState:")
    print(f"  Auto-advance sessions: {payload['sessions']}")
    print(f"  History entries:       {payload['history_entries']}")
    print(f"  Zenodo token:          {'configured' if payload['zenodo_token_configured'] else 'not set'}")
    print(f"  GitHub token:          {'configured' if payload['github_token_configured'] else 'not set'}")
    print("\nRun `doctor` for backend availability.\n")


async def do_doctor(json_output: bool = False) -> None:
    """Report which optional backends are importable and which commands they gate."""
    report = _backend_availability()
    if json_output:
        print_json({"version": VERSION, "backends": report})
        return

    _section("OSIRIS NCLM CLI - BACKEND REPORT")
    width = max(len(name) for name in report)
    unavailable = []
    for name, info in report.items():
        mark = "ok     " if info["available"] else "MISSING"
        print(f"  [{mark}] {name:<{width}}  gates: {', '.join(info['commands'])}")
        if not info["available"]:
            unavailable.append((name, info))

    if not unavailable:
        print("\nAll optional backends are importable.\n")
        return

    print(f"\n{len(unavailable)} backend(s) unavailable in this checkout:")
    for name, info in unavailable:
        print(f"\n  {name}")
        print(f"    error:    {info['error']}")
        print(f"    affects:  {', '.join(info['commands'])}")
    print("\nCommands backed by a missing module exit with code 2 and a single-line "
          "message.\n")


async def do_history(limit: int = 20) -> None:
    """Print recent inference history."""
    entries = load_history(limit=limit)
    if not entries:
        print(f"No history yet ({HISTORY_FILE})")
        return
    _section(f"HISTORY (last {len(entries)})")
    for entry in entries:
        ts = str(entry.get("ts", "?"))[:19]
        cmd = str(entry.get("command", "?"))
        ms = entry.get("elapsed_ms")
        suffix = f"  {ms:.0f}ms" if isinstance(ms, (int, float)) else ""
        print(f"{ts}  {cmd:8s}  {str(entry.get('prompt', ''))[:60]}{suffix}")


async def do_interactive(state_dir: Optional[Path] = None) -> None:
    """Minimal REPL over this CLI's own subcommands.

    Lines are parsed with the same parser as the command line, so `infer hello` here and
    `osiris-nclm infer hello` outside behave identically.
    """
    import shlex

    parser = build_parser()
    print(f"OSIRIS NCLM CLI v{VERSION} interactive. "
          "Type a subcommand, `help`, or `quit`.")
    while True:
        try:
            line = input("osiris> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in ("quit", "exit", "q"):
            return
        if line in ("help", "?"):
            parser.print_help()
            continue
        try:
            args = parser.parse_args(shlex.split(line))
        except SystemExit:
            continue  # argparse already printed the error; stay in the loop
        if args.command in (None, "interactive"):
            print("Nothing to run (nested `interactive` is ignored).")
            continue
        try:
            await dispatch(args, state_dir)
        except NotAvailableError as exc:
            print(f"Not available: {exc}")
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"Error: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_prompt_args(p: argparse.ArgumentParser, help_text: str = "Prompt text") -> None:
    p.add_argument("prompt", nargs="*", help=f"{help_text} (quotes optional)")
    p.add_argument("--file", "-f", help="Read prompt from file")
    p.add_argument("--stdin", action="store_true", help="Read prompt from stdin")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osiris-nclm",
        description="OSIRIS NCLM CLI: auto-enhance and auto-advance pipelines, cognitive "
                    "analysis, and research tooling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  osiris-nclm infer "Explain quantum computing to a 5-year-old"
  osiris-nclm infer --grok "Develop a comprehensive theory of quantum cognition"
  osiris-nclm analyze "What are the implications of quantum computing for AI?"
  osiris-nclm understand "Quantum-cognitive relationships" --depth 4
  osiris-nclm enhance "Explain quantum entanglement" --iterations 4
  osiris-nclm advance "Explore quantum cognition" --iterations 5 --depth 3
  osiris-nclm complete "Investigate quantum AI applications"
  osiris-nclm session                      # list sessions
  osiris-nclm session <session_id> --iteration 2
  osiris-nclm zenodo "quantum computing" --max 10
  osiris-nclm github owner/repo
  osiris-nclm status --json
  osiris-nclm doctor                       # which backends are installed
  osiris-nclm interactive
""",
    )
    parser.add_argument("--version", action="version", version=f"OSIRIS v{VERSION}")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging (and tracebacks)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Only log warnings and errors")
    parser.add_argument("--state-dir", default=str(STATE_DIR),
                        help="Directory for persistent client state")

    sub = parser.add_subparsers(dest="command", required=False, metavar="COMMAND")

    p = sub.add_parser("infer", aliases=["grok"], help="Run NCLM inference (`grok` = --grok)")
    _add_prompt_args(p)
    p.add_argument("--grok", action="store_true", help="Use grok mode (deep understanding)")
    p.add_argument("--no-telemetry", action="store_true", help="Hide timing footer")

    _add_prompt_args(sub.add_parser("analyze", help="Comprehensive cognitive analysis"))

    p = sub.add_parser("understand", help="Deep understanding of a complex topic")
    _add_prompt_args(p, "Topic to understand")
    p.add_argument("--depth", type=int, default=5, help="Maximum depth of understanding")
    p.add_argument("--quantum", type=float, default=None,
                   help="Quantum processing strength (0.0-1.0)")

    p = sub.add_parser("enhance", help="Automatically enhance a prompt")
    _add_prompt_args(p, "Prompt to enhance")
    p.add_argument("--iterations", type=int, default=3,
                   help="Number of enhancement iterations")

    p = sub.add_parser("advance", help="Automatically advance understanding")
    _add_prompt_args(p, "Topic to advance")
    p.add_argument("--iterations", type=int, default=5, help="Number of advance iterations")
    p.add_argument("--depth", type=int, default=3, help="Exploration depth per iteration")

    _add_prompt_args(
        sub.add_parser("complete", help="Run auto-enhance + auto-advance pipeline"),
        "Topic to process completely",
    )

    p = sub.add_parser("stack", help="Recursively refine a production LLM stack blueprint")
    _add_prompt_args(p, "High-level stack objective")
    p.add_argument("--iterations", type=int, default=3, help="Number of refinement iterations")
    p.add_argument("--save", action="store_true", help="Persist the blueprint to disk")

    p = sub.add_parser("session", help="List sessions, or analyze one auto-advance session")
    p.add_argument("session_id", nargs="?", help="Session ID (omit to list sessions)")
    p.add_argument("--iteration", type=int, help="Show details for this iteration number")
    p.add_argument("--limit", type=int, default=20, help="Max sessions to list")

    _add_prompt_args(sub.add_parser("concept", help="Print the concept graph for a topic"),
                     "Topic to map")

    sub.add_parser("quantum", help="Run the quantum cognitive simulation")
    sub.add_parser("diagnostics", help="Run cognitive diagnostics")
    sub.add_parser("understand-diag", help="Run deep-understanding diagnostics")

    p = sub.add_parser("memory", help="Inspect or clear client memory")
    p.add_argument("action", choices=MEMORY_ACTIONS, help="Memory action to perform")

    p = sub.add_parser("mode", help="Set the NCLM processing mode")
    p.add_argument("mode", choices=NCLM_MODE_NAMES, help="Processing mode")

    p = sub.add_parser("param", help="Set config parameters (key=value ...)")
    p.add_argument("pairs", nargs="+", metavar="KEY=VALUE", help="Parameters to set")

    sub.add_parser("tune", help="Interactively tune numeric config parameters")

    p = sub.add_parser("zenodo", help="Search Zenodo records")
    p.add_argument("query", help="Search query")
    p.add_argument("--max", type=int, default=12, dest="max_results",
                   help="Maximum records to show (1-100)")

    p = sub.add_parser("github", help="Ingest GitHub repository metadata")
    p.add_argument("repo", help="owner/repo or a github.com URL")

    p = sub.add_parser("discover", help="Synthesize speculative physics principles")
    p.add_argument("domain", nargs="?", default="quantum_gravity", help="Seed domain")
    p.add_argument("--principles", type=int, default=3, dest="num_principles",
                   help="Principles to synthesize")
    p.add_argument("--iterations", type=int, default=2, help="Refinement iterations")
    p.add_argument("--save", action="store_true", help="Persist the discovery")

    p = sub.add_parser("consciousness", help="Show Phi/Gamma/Lambda/Xi telemetry")
    p.add_argument("--state", dest="state_file",
                   help="JSON file of real measurements (omit for a simulated state)")
    p.add_argument("--seed", type=int, default=None,
                   help="Seed for the simulated state (reproducible demo output)")
    p.add_argument("--watch", action="store_true", help="Not implemented yet")
    p.add_argument("--history", type=int, default=5, dest="history_count",
                   help="Alerts to show with --alerts")
    p.add_argument("--alerts", action="store_true", dest="show_alerts",
                   help="Show recent alerts")

    p = sub.add_parser("paper", help="Emit an honest paper scaffold (no invented results)")
    p.add_argument("topic", help="Paper topic")
    p.add_argument("--title", default="", help="Paper title")
    p.add_argument("--save", action="store_true", help="Save the scaffold as Markdown")

    p = sub.add_parser("hypothesis", help="Print example research hypotheses (demo)")
    p.add_argument("--domain", default="", help="Domain label (currently unused)")
    p.add_argument("--contradictions", action="store_true", dest="find_contradictions",
                   help="Include paradigm contradictions")
    p.add_argument("--gaps", action="store_true", dest="find_gaps",
                   help="Include research gaps")
    p.add_argument("--predictions", action="store_true", dest="generate_predictions",
                   help="Include experimental predictions")

    p = sub.add_parser("swarm", help="Animated swarm demo (see `ultra run` for the real one)")
    p.add_argument("task", help="Task description")
    p.add_argument("--agents", type=int, default=8, dest="num_agents", help="Swarm size")
    p.add_argument("--iterations", type=int, default=5, help="Evolution cycles")

    p = sub.add_parser("ultra", help="Ultra-Agent reasoning swarm")
    ultra_sub = p.add_subparsers(dest="ultra_command", required=True, metavar="ACTION")
    up = ultra_sub.add_parser("run", help="Run the swarm on a task")
    up.add_argument("task", help="Task description")
    up.add_argument("--loops", type=int, default=3, help="Max refinement loops")
    up.add_argument("--threshold", type=float, default=0.75, help="Quality threshold")
    up = ultra_sub.add_parser("bench", help="Benchmark against baseline tools")
    up.add_argument("task", help="Task description")
    up = ultra_sub.add_parser("improve", help="Run self-improvement")
    up.add_argument("--iterations", type=int, default=3, help="Improvement iterations")
    up = ultra_sub.add_parser("distill", help="Run mentor-protege distillation")
    up.add_argument("--epochs", type=int, default=3, help="Distillation epochs")
    up.add_argument("--tasks-per-epoch", type=int, default=3, dest="tasks_per_epoch",
                    help="Tasks generated per epoch")
    up.add_argument("--domains", nargs="*", default=None, help="Restrict to these domains")

    p = sub.add_parser("dual-node", help="Dual-node runtime routing")
    dn_sub = p.add_subparsers(dest="dual_node_command", required=True, metavar="ACTION")
    for action, helptext in (("status", "Show detected runtime and route"),
                             ("doctor", "Emit a structured dry-run route plan")):
        dp = dn_sub.add_parser(action, help=helptext)
        dp.add_argument("--intent", default=None, help="Intent to route")
        dp.add_argument("--json", action="store_true", dest="json_output", help="JSON output")

    p = sub.add_parser("status", help="Show versions, paths and directory state")
    p.add_argument("--json", action="store_true", dest="json_output", help="JSON output")

    p = sub.add_parser("doctor", help="Report which optional backends are installed")
    p.add_argument("--json", action="store_true", dest="json_output", help="JSON output")

    p = sub.add_parser("history", help="Show recent inference history")
    p.add_argument("--limit", type=int, default=20, help="Entries to show")

    sub.add_parser("interactive", help="Start an interactive REPL over these subcommands")

    return parser


def _require_prompt(args: argparse.Namespace, what: str = "A prompt") -> str:
    prompt = get_prompt_from_args(args)
    if not prompt:
        raise ValueError(f"{what} is required (pass it positionally, with --file, or --stdin)")
    return prompt


async def dispatch(args: argparse.Namespace, state_dir: Optional[Path] = None) -> None:
    """Route a parsed namespace to its command implementation."""
    cmd = args.command

    if cmd in ("infer", "grok"):
        grok = bool(getattr(args, "grok", False)) or cmd == "grok"
        await do_infer(_require_prompt(args), grok, args.no_telemetry, state_dir)
    elif cmd == "analyze":
        await do_cognitive_analysis(_require_prompt(args), state_dir)
    elif cmd == "understand":
        await do_deep_understand(
            _require_prompt(args, "A topic"), args.depth, args.quantum, state_dir
        )
    elif cmd == "enhance":
        await do_auto_enhance(_require_prompt(args), args.iterations, state_dir)
    elif cmd == "advance":
        await do_auto_advance(
            _require_prompt(args, "A topic"), args.iterations, args.depth, state_dir
        )
    elif cmd == "complete":
        await do_auto_complete(_require_prompt(args, "A topic"), state_dir)
    elif cmd == "stack":
        await do_stack_refinement(
            _require_prompt(args, "An objective"), args.iterations, args.save
        )
    elif cmd == "session":
        if args.session_id in (None, "list"):
            list_sessions(args.limit)
        else:
            await do_session_analysis(args.session_id, args.iteration)
    elif cmd == "concept":
        await do_concept_map(_require_prompt(args, "A topic"), state_dir)
    elif cmd == "quantum":
        await do_quantum_simulation(state_dir)
    elif cmd == "diagnostics":
        await do_cognitive_diagnostics(state_dir)
    elif cmd == "understand-diag":
        await do_understanding_diagnostics(state_dir)
    elif cmd == "memory":
        await do_memory_management(args.action, state_dir)
    elif cmd == "mode":
        await do_mode_selection(args.mode)
    elif cmd == "param":
        await do_parameter_adjustment(_parse_params(args.pairs))
    elif cmd == "tune":
        await do_quantum_tuning()
    elif cmd == "zenodo":
        await do_zenodo_scan(args.query, args.max_results)
    elif cmd == "github":
        await do_github_ingest(args.repo)
    elif cmd == "discover":
        await do_physics_discovery(
            args.domain, args.num_principles, args.iterations, args.save
        )
    elif cmd == "consciousness":
        await do_consciousness_telemetry(
            args.watch, args.history_count, args.show_alerts, args.state_file, args.seed
        )
    elif cmd == "paper":
        await do_paper_generation(args.title, args.topic, args.save)
    elif cmd == "hypothesis":
        await do_hypothesis_generation(
            args.domain, args.find_contradictions, args.find_gaps, args.generate_predictions
        )
    elif cmd == "swarm":
        await do_swarm_deployment(args.task, args.num_agents, args.iterations)
    elif cmd == "ultra":
        if args.ultra_command == "run":
            await do_ultra_agent(args.task, args.loops, args.threshold)
        elif args.ultra_command == "bench":
            await do_ultra_benchmark(args.task)
        elif args.ultra_command == "improve":
            await do_ultra_improve(args.iterations)
        elif args.ultra_command == "distill":
            await do_ultra_distill(args.epochs, args.tasks_per_epoch, args.domains)
        else:
            raise ValueError(f"Unknown ultra action: {args.ultra_command!r}")
    elif cmd == "dual-node":
        if args.dual_node_command == "status":
            await do_dual_node_status(args.intent, args.json_output)
        elif args.dual_node_command == "doctor":
            await do_dual_node_doctor(args.intent, args.json_output)
        else:
            raise ValueError(f"Unknown dual-node action: {args.dual_node_command!r}")
    elif cmd == "status":
        await do_status(args.json_output, state_dir)
    elif cmd == "doctor":
        await do_doctor(args.json_output)
    elif cmd == "history":
        await do_history(args.limit)
    elif cmd == "interactive":
        await do_interactive(state_dir)
    else:
        raise ValueError(f"Unknown command: {cmd!r}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)
    elif args.quiet:
        logger.setLevel(logging.WARNING)

    if not args.command:
        parser.print_help()
        return 0

    ensure_dirs()
    # Threaded through to create_nclm_client rather than rebound as a global: a plain
    # assignment here would create a local, and rebinding the global would still leave
    # CONFIG_DIR and AUTOADVANCE_DIR pointing at the original tree.
    state_dir = Path(args.state_dir).expanduser()

    try:
        asyncio.run(dispatch(args, state_dir))
    except NotAvailableError as exc:
        logger.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        print()
        return 130
    except SystemExit as exc:
        return int(exc.code or 0)
    except (ValueError, OSError, RuntimeError, EnvironmentError, ImportError) as exc:
        if args.debug:
            raise
        logger.error("%s: %s", type(exc).__name__, exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
