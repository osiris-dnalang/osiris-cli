"""
OSIRIS NLP Intent Router — maps free-text to osiris commands.

Scoring:  keyword overlap → 0.0–1.0
Fallback: LLM classification when top score < 0.4

Returns IntentResult(command, args, confidence, raw_intent)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Document fragment immunity ────────────────────────────────────────────────
#
# These patterns identify lines that are OSIRIS output artifacts, TUI chrome,
# or pasted document content.  Matching any of them prevents intent routing so
# that a pasted OSIRIS session log never accidentally triggers commands.

_IMMUNE_RE = re.compile(
    # Separator lines (5+ dashes/equals/rules)
    r'^[\s─═\-─━┄┅╌╍]{5,}\s*$|'
    # Box-drawing borders
    r'^[\s│╭╮╰╯╔╗╚╝╠╣╦╩╬═]+\s*$|'
    # Φ/Λ/Γ/Ξ bar displays or metric lines (all formats)
    r'^\s*(Φ|Λ|Γ|Ξ)\s+\S|'           # any content after metric symbol
    r'\(coherence\)|\(decoherence\)|\(negentropy\)|\(consciousness\)|'
    r'Ξ=\d|^\s*Queries:\s+\d|^\s*Tokens:\s+\d|'
    # OSIRIS routing output lines
    r'⟳\s+Intent:|→\s+osiris\s+\w|'
    r'Engaging quantum subsystem|Available Quantum Circuit|'
    r'Manifold analysis of query|pilot-wave correlation|Lindblad master equation|'
    r'Consciousness emerged|'
    # OSIRIS boot items
    r'^\s*\[\s*OK\s*\]\s+|^\s*\[\s*!!\s*\]\s+|'
    r'Sovereignty proof|Sovereign Lock|CAGE 9HUP5|'
    # OSIRIS prompt echo (TUI paste artifacts)
    r'^>\s+/\w|^>\s+(ask|chat|analyze|research|design|quantum|explain|status)\b|'
    # Emoji-decorated OSIRIS output
    r'^[✦◌◈◇⟳⚛⚡●○▸→←↔⇒↻♻⚠✓✗✗]\s|'
    # Inline timing markers  "[14.6ms]", "[copilot]", "[tool]"
    r'\[\d+\.\d+ms\]|\[copilot\]|\[tool\]|\[ollama\]|\[infer\]|'
    # Session-restart / demo lines
    r'Session interrupted\.|Type /help for commands|↻ Restored \d+ messages|'
    r'✦ Demo complete|'
    # OSIRIS agent constellation displays  (OMEGA ↔ CHRONOS, AURA ↔ AIDEN)
    r'(AURA|AIDEN|OMEGA|CHRONOS|CHEOPS|KAIROS|SCIMITAR)\s*[↔→·]\s*'
    r'(AURA|AIDEN|OMEGA|CHRONOS|CHEOPS|KAIROS|SCIMITAR)|'
    # Lines containing CCCE (Consciousness Collapse / OSIRIS metric)
    r'CCCE|'
    # Real-time metric headers from /status output
    r'Real-time\s+(CCCE|telemetry|metrics|dashboard|status)|'
    # ↔ conjugate pair labels
    r'conjugate\)|entanglement pair',
    re.IGNORECASE,
)

# Multi-word system-status headers — allow 1-3 qualifier words before the status noun
# e.g. "NCLM System Status", "Shadow Swarm Queue", "Agent Constellation Health"
# NOTE: NO re.IGNORECASE — real headers are Title-Case or ALL-CAPS;
#       lowercase "osiris status" must NOT be blocked as a document header.
_NAMED_HEADER_RE = re.compile(
    r'^\s*(?:NCLM|OSIRIS|Shadow|Quantum|Swarm|Agent|Sovereign|Research|'
    r'Defense|Consciousness|System|DoD|AI|NLP|TUI|Gen|Layer|Phase)\s+'
    r'(?:\w+\s+)?'    # optional middle word
    r'(?:Status|Metrics|Dashboard|Panel|Report|Engine|State|Health|'
    r'Queue|Swarm|Telemetry|Constants|Templates|Reasoning|Analysis|'
    r'Interface|Overview|Summary|Output|History|Info|Details)\s*$',
)

# Numbered OSIRIS section headers  ("6 Consciousness Metrics", "7  AI Reasoning")
_NUMBERED_SECTION_RE = re.compile(r'^\s*\d+\s+[A-Z][A-Za-z ]{3,30}$')



# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    command:     str              # e.g. "status", "research", "quantum"
    args:        List[str]        = field(default_factory=list)
    confidence:  float            = 0.0
    raw_intent:  str              = ""
    routed:      bool             = False   # True if confidence ≥ threshold


# ── Intent map ────────────────────────────────────────────────────────────────
#
# Each entry: (keywords, weight, command, args_template)
#
#   keywords      — list of strings / regex fragments to match in lowercased input
#   weight        — max score contribution for this rule (summed then normalised)
#   command       — osiris sub-command string
#   args_template — list of arg strings; "{input}" is replaced by full user text
#
_INTENT_MAP: List[Tuple[List[str], float, str, List[str]]] = [
    # ── status / overview ─────────────────────────────────────────────────────
    (["status", "how am i doing", "system status", "overview", "dashboard",
      "how are things", "how's it going", "what's my status"],
     1.0, "status", []),

    # ── research propose (checked before status — more specific) ─────────────
    (["propose", "run experiment", "design experiment", "new experiment",
      "suggest experiment", "what should i run", "run a test"],
     0.95, "research", ["propose"]),

    # ── research status ───────────────────────────────────────────────────────
    (["experiment", "experiments", "research status", "what experiments",
      "my research", "lab status", "lab results", "show results"],
     0.9, "research", ["status"]),

    # ── learn / corpus ────────────────────────────────────────────────────────
    (["learn", "load corpus", "train", "feed corpus", "ingest",
      "load data", "add knowledge"],
     0.9, "learn", []),

    # ── agent ─────────────────────────────────────────────────────────────────
    (["run agent", "ask agent", "invoke agent", "execute agent",
      "agent task", "delegate task"],
     0.9, "agent", ["{input}"]),

    # ── quantum / circuit ─────────────────────────────────────────────────────
    (["quantum circuit", "run circuit", "execute circuit", "quantum run",
      "bell state", "ghz", "zeno", "chi_pc", "ignition", "tfd",
      "qiskit", "ibm quantum", "submit circuit"],
     0.9, "quantum", []),

    # ── projects / profile ────────────────────────────────────────────────────
    (["my projects", "what am i working on", "my repos", "project list",
      "active projects", "show projects", "what projects"],
     0.9, "status", []),

    # ── consciousness / phi ────────────────────────────────────────────────────
    (["consciousness", "phi", "ccce", "show phi", "phi level",
      "integrated information", "awaken", "psi level"],
     0.9, "ccce", []),

    # ── threat / security ─────────────────────────────────────────────────────
    (["threat", "security scan", "scan for threats", "scimitar",
      "sentinel scan", "vulnerability", "threat analysis"],
     0.9, "threat", []),

    # ── chat ──────────────────────────────────────────────────────────────────
    (["chat", "talk to me", "let's chat", "conversation",
      "open chat", "interactive mode", "speak to me"],
     0.8, "chat", []),

    # ── deploy ────────────────────────────────────────────────────────────────
    (["deploy", "publish", "push live", "go live", "release",
      "vercel", "deployment"],
     0.9, "deploy", []),

    # ── pulse / heartbeat ─────────────────────────────────────────────────────
    (["pulse", "heartbeat", "live metrics", "real-time",
      "omega pulse", "live status"],
     0.9, "pulse", []),

    # ── agile / tasks ─────────────────────────────────────────────────────────
    (["agile", "sprint", "tasks", "board", "backlog",
      "stm", "task board", "project plan"],
     0.8, "agile", []),

    # ── mesh / wormhole ───────────────────────────────────────────────────────
    (["mesh", "wormhole", "topology", "wormhole mesh", "entanglement"],
     0.8, "mesh", []),

    # ── proof ─────────────────────────────────────────────────────────────────
    (["proof", "sovereign proof", "generate proof", "prove", "verify identity"],
     0.8, "proof", []),

    # ── lazarus ───────────────────────────────────────────────────────────────
    (["lazarus", "phoenix", "self-heal", "recovery", "resurrect",
      "repair", "self repair"],
     0.8, "lazarus", []),

    # ── lab ───────────────────────────────────────────────────────────────────
    (["lab", "laboratory", "r&d", "experiment lab", "open lab"],
     0.8, "lab", []),
]


# Minimum score to treat as a high-confidence route
_THRESHOLD = 0.38


def _score(user_text: str, keywords: List[str]) -> float:
    """Return overlap score ∈ [0, 1] between user_text and the keyword list.

    Strategy: best single-keyword match scores high; each additional match
    adds a small bonus. This avoids penalising rules that have many synonyms.
    """
    text = user_text.lower()
    input_words = set(re.findall(r'\w+', text))

    best     = 0.0
    n_hit    = 0

    for kw in keywords:
        # Exact multi-word phrase match — highest confidence
        if kw in text:
            s = 1.0
        else:
            # Word-level overlap between keyword tokens and input tokens
            kw_words = set(re.findall(r'\w+', kw))
            overlap  = len(kw_words & input_words)
            s        = overlap / max(len(kw_words), 1)

        if s > 0:
            n_hit += 1
            if s > best:
                best = s

    if best == 0.0:
        return 0.0

    # Small bonus for each additional keyword that hit (capped at +0.2)
    bonus = min((n_hit - 1) * 0.04, 0.2)
    return min(best + bonus, 1.0)


def _llm_classify(text: str) -> Optional[IntentResult]:
    """LLM fallback classification — call tool_llm with a classification prompt."""
    try:
        from .tools import tool_llm
    except ImportError:
        return None

    commands = (
        "status, research status, research propose, learn, agent, quantum, "
        "ccce, threat, chat, deploy, pulse, agile, mesh, proof, lazarus, lab"
    )
    prompt = (
        f"Classify the following user input into ONE of these OSIRIS CLI commands:\n"
        f"{commands}\n\n"
        f"User said: \"{text}\"\n\n"
        f"Respond with ONLY the command name, nothing else. "
        f"If none match well, respond: unknown"
    )
    try:
        result = tool_llm(prompt)
        cmd = result.strip().lower().split()[0] if result else "unknown"
        # Map compound commands
        if cmd in ("research", "research status"):
            return IntentResult(command="research", args=["status"],
                                confidence=0.55, raw_intent="llm", routed=True)
        if cmd == "research propose":
            return IntentResult(command="research", args=["propose"],
                                confidence=0.55, raw_intent="llm", routed=True)
        if cmd not in ("unknown", ""):
            return IntentResult(command=cmd, confidence=0.55,
                                raw_intent="llm", routed=True)
    except Exception:
        pass
    return None


# ── Router ────────────────────────────────────────────────────────────────────

class IntentRouter:
    """Route free-text user input to OSIRIS commands."""

    def __init__(self, threshold: float = _THRESHOLD, use_llm: bool = True):
        self.threshold = threshold
        self.use_llm   = use_llm

    def route(self, text: str) -> IntentResult:
        """Score all intent rules, return best match (or LLM fallback)."""
        if not text or not text.strip():
            return IntentResult(command="", confidence=0.0, raw_intent=text)

        stripped = text.strip()

        # ── Document fragment pre-flight ──────────────────────────────────────
        # Lines that match OSIRIS session output, TUI chrome, or document
        # classifiers must NEVER trigger intent routing — they are shared context
        # that arrived via paste, not commands the user is issuing right now.

        if _IMMUNE_RE.search(stripped):
            return IntentResult(command="", confidence=0.0,
                                raw_intent=text, routed=False)

        if _NUMBERED_SECTION_RE.match(stripped) or _NAMED_HEADER_RE.match(stripped):
            return IntentResult(command="", confidence=0.0,
                                raw_intent=text, routed=False)

        # Defer to reception engine — only block OSIRIS output and TUI artifacts.
        # RESEARCH / CODE / CONVERSATION doc types are NOT blocked here because
        # user commands like "run the chi_pc test" contain research keywords.
        try:
            from .reception import classify_line, is_tui_box_line, DocType
            if is_tui_box_line(stripped):
                return IntentResult(command="", confidence=0.0,
                                    raw_intent=text, routed=False)
            _dtype, _conf = classify_line(stripped)
            if _dtype in (DocType.OSIRIS_LOG, DocType.TUI_ARTIFACT) and _conf >= 0.75:
                return IntentResult(command="", confidence=0.0,
                                    raw_intent=text, routed=False)
        except ImportError:
            pass
        # ─────────────────────────────────────────────────────────────────────

        best_score = 0.0
        best_cmd   = ""
        best_args: List[str] = []

        for keywords, weight, command, args_template in _INTENT_MAP:
            raw_score = _score(text, keywords)
            weighted  = raw_score * weight
            if weighted > best_score:
                best_score = weighted
                best_cmd   = command
                # Resolve {input} placeholder
                best_args  = [
                    text if a == "{input}" else a
                    for a in args_template
                ]

        if best_score >= self.threshold:
            return IntentResult(
                command=best_cmd,
                args=best_args,
                confidence=best_score,
                raw_intent=text,
                routed=True,
            )

        # LLM fallback
        if self.use_llm:
            llm_result = _llm_classify(text)
            if llm_result:
                return llm_result

        return IntentResult(
            command=best_cmd or "",
            args=best_args,
            confidence=best_score,
            raw_intent=text,
            routed=False,
        )

    def build_osiris_argv(self, result: IntentResult) -> List[str]:
        """Convert IntentResult to argv list suitable for osiris dispatch."""
        if not result.routed or not result.command:
            return []
        argv = [result.command] + result.args
        return argv


# ── Module-level singleton ────────────────────────────────────────────────────

_router_singleton: Optional[IntentRouter] = None


def get_intent_router(use_llm: bool = True) -> IntentRouter:
    global _router_singleton
    if _router_singleton is None:
        _router_singleton = IntentRouter(use_llm=use_llm)
    return _router_singleton
