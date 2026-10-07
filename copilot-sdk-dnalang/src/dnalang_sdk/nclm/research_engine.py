"""
OSIRIS Physics Research Engine — Self-Learning Workload Pre-Processor

Integrates past experiments, conversations, and code examples from the
DNA-Lang training corpus as live context for engineering new physics
discoveries. Continuously designs, tests, and proposes hardware experiments.

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from __future__ import annotations
import os, json, time, hashlib, threading, re
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

LAMBDA_PHI    = 2.176435e-8
THETA_LOCK    = 51.843
PHI_THRESHOLD = 0.7734
CHI_PC        = 0.946

_HOME = os.path.expanduser("~")
_TRAINING_SEARCH_PATHS = [
    "/media/live/26F5-3744/omega_master_v4/dnalang_training_full.json",
    os.path.join(_HOME, "copilot-sdk-dnalang/dnalang/src/dnalang_sdk/data/training.json"),
    os.path.join(_HOME, ".osiris/training_cache.json"),
]
_EXPERIMENT_LOG = os.path.join(_HOME, ".osiris", "physics_research_log.jsonl")
_CONFIDENCE_DB  = os.path.join(_HOME, ".osiris", "hypothesis_confidence.json")

# ── DATA CLASSES ──────────────────────────────────────────────────────────────

@dataclass
class Experiment:
    id: str
    title: str
    hypothesis: str
    circuit_template: str
    backend: str
    confidence: float           # 0-1 epistemic confidence
    evidence: List[str]         # supporting experiment IDs
    status: str                 # pending | proposed | submitted | validated
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: Optional[Dict] = None

@dataclass
class ResearchContext:
    relevant_experiments: List[Dict]
    code_examples: List[Dict]
    key_constants: Dict[str, float]
    hypothesis_chain: List[str]
    confidence: float

# ── RESEARCH ENGINE ───────────────────────────────────────────────────────────

class PhysicsResearchEngine:
    """
    Self-learning workload pre-processor for OSIRIS.

    Loads training corpus, indexes experiments by topic, and:
    1. Provides relevant context for every query
    2. Continuously refines hypotheses based on accumulated evidence
    3. Proposes hardware-ready experiment designs when confidence ≥ threshold
    """

    CONFIDENCE_THRESHOLD = 0.75   # propose to hardware above this
    MIN_EVIDENCE_COUNT   = 3      # minimum experiments to support a hypothesis

    def __init__(self):
        self._corpus: Optional[Dict] = None
        self._conversations: List[Dict] = []
        self._code_examples: List[Dict] = []
        self._governing_equations: List[Dict] = []
        self._index: Dict[str, List[int]] = {}   # keyword → [conv indices]
        self._experiments: List[Experiment] = []
        self._hypothesis_db: Dict[str, float] = {}
        self._loaded = False
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(_EXPERIMENT_LOG), exist_ok=True)
        self._load_confidence_db()

    # ── CORPUS LOADING ────────────────────────────────────────────────────────

    def load_corpus(self, path: Optional[str] = None) -> bool:
        """Load the DNA-Lang training corpus. Auto-discovers if path not given."""
        candidates = ([path] if path else []) + _TRAINING_SEARCH_PATHS
        for p in candidates:
            if p and os.path.exists(p):
                try:
                    with open(p) as f:
                        data = json.load(f)
                    with self._lock:
                        self._corpus = data
                        self._conversations = data.get("conversations", [])
                        self._code_examples = data.get("code_examples", [])
                        self._governing_equations = data.get("governing_equations", [])
                        self._build_index()
                        self._loaded = True
                    return True
                except Exception:
                    continue
        return False

    def _build_index(self):
        """Build keyword → conversation index for fast retrieval."""
        idx: Dict[str, List[int]] = {}
        for i, conv in enumerate(self._conversations):
            text = (conv.get("instruction", "") + " " +
                    conv.get("response", "")).lower()
            for word in re.findall(r'\b\w{4,}\b', text):
                idx.setdefault(word, []).append(i)
        self._index = idx

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "conversations": len(self._conversations),
            "code_examples": len(self._code_examples),
            "equations": len(self._governing_equations),
            "experiments_proposed": len(self._experiments),
            "hypotheses": len(self._hypothesis_db),
        }

    # ── CONTEXT RETRIEVAL ─────────────────────────────────────────────────────

    def get_context_for_query(self, query: str, top_k: int = 5) -> ResearchContext:
        """
        Given a query, retrieve the most relevant past experiments and code
        as pre-processor context for the LLM.
        """
        if not self._loaded:
            return ResearchContext([], [], self._physics_constants(), [], 0.0)

        # Score conversations by keyword overlap
        q_words = set(re.findall(r'\b\w{4,}\b', query.lower()))
        scores: Dict[int, int] = {}
        for word in q_words:
            for idx in self._index.get(word, []):
                scores[idx] = scores.get(idx, 0) + 1

        top_convs = sorted(scores, key=scores.get, reverse=True)[:top_k]  # type: ignore
        relevant = [self._conversations[i] for i in top_convs]

        # Find relevant code examples
        relevant_code = [
            ce for ce in self._code_examples
            if any(w in ce.get("description", "").lower() for w in q_words)
        ][:3]

        # Extract hypothesis chain from relevant conversations
        hyp_chain = self._extract_hypothesis_chain(relevant)

        # Compute aggregate confidence
        confidence = min(len(relevant) / max(top_k, 1), 1.0)

        return ResearchContext(
            relevant_experiments=relevant,
            code_examples=relevant_code,
            key_constants=self._physics_constants(),
            hypothesis_chain=hyp_chain,
            confidence=confidence,
        )

    def _physics_constants(self) -> Dict[str, float]:
        return {
            "LAMBDA_PHI": LAMBDA_PHI,
            "THETA_LOCK": THETA_LOCK,
            "PHI_THRESHOLD": PHI_THRESHOLD,
            "CHI_PC": CHI_PC,
        }

    def _extract_hypothesis_chain(self, conversations: List[Dict]) -> List[str]:
        """Extract key scientific claims from conversation history."""
        hypotheses = []
        for conv in conversations:
            resp = conv.get("response", "")
            # Extract sentences with experimental claims
            for sentence in re.split(r'[.!?]\s+', resp):
                if any(kw in sentence.lower() for kw in [
                    "breakthrough", "validated", "p =", "σ", "fidelity",
                    "chi_pc", "negentropy", "coherence", "discovered"
                ]):
                    clean = sentence.strip()[:200]
                    if clean and clean not in hypotheses:
                        hypotheses.append(clean)
            if len(hypotheses) >= 5:
                break
        return hypotheses[:5]

    # ── EXPERIMENT DESIGN ─────────────────────────────────────────────────────

    def design_experiment(
        self,
        hypothesis: str,
        template: str = "chi_pc",
        backend: str = "ibm_fez",
        evidence_ids: Optional[List[str]] = None,
    ) -> Experiment:
        """
        Design a new quantum hardware experiment to test a hypothesis.
        Returns an Experiment object ready for hardware submission.
        """
        exp_id = "EXP-" + hashlib.md5(
            f"{hypothesis}{time.time()}".encode()
        ).hexdigest()[:8].upper()

        # Compute initial confidence from evidence chain
        evidence = evidence_ids or []
        confidence = self._compute_confidence(hypothesis, evidence)

        exp = Experiment(
            id=exp_id,
            title=f"OSIRIS Auto-Design: {hypothesis[:60]}",
            hypothesis=hypothesis,
            circuit_template=template,
            backend=backend,
            confidence=confidence,
            evidence=evidence,
            status="proposed" if confidence >= self.CONFIDENCE_THRESHOLD else "pending",
        )

        with self._lock:
            self._experiments.append(exp)
        self._log_experiment(exp)
        return exp

    def _compute_confidence(self, hypothesis: str, evidence: List[str]) -> float:
        """
        Compute epistemic confidence for a hypothesis based on:
        - Keyword overlap with validated breakthroughs in corpus
        - Number of supporting experiment IDs
        - Prior confidence from hypothesis_db
        """
        base = self._hypothesis_db.get(
            hashlib.md5(hypothesis.encode()).hexdigest()[:8], 0.3
        )
        # Boost for corpus support
        if self._loaded:
            q_words = set(re.findall(r'\b\w{4,}\b', hypothesis.lower()))
            corpus_hits = sum(
                1 for conv in self._conversations
                if any(w in conv.get("response", "").lower() for w in q_words)
            )
            corpus_boost = min(corpus_hits / max(len(self._conversations), 1) * 10, 0.4)
        else:
            corpus_boost = 0.0

        # Boost for evidence chain
        evidence_boost = min(len(evidence) * 0.05, 0.3)

        return min(base + corpus_boost + evidence_boost, 1.0)

    def update_confidence(self, hypothesis: str, delta: float):
        """Update hypothesis confidence based on new experimental evidence."""
        key = hashlib.md5(hypothesis.encode()).hexdigest()[:8]
        current = self._hypothesis_db.get(key, 0.3)
        self._hypothesis_db[key] = max(0.0, min(1.0, current + delta))
        self._save_confidence_db()

    # ── AUTO-PROPOSE ──────────────────────────────────────────────────────────

    def auto_propose_from_corpus(self) -> List[Experiment]:
        """
        Scan the training corpus and auto-generate experiment proposals
        for the most promising hypotheses (those with high evidence density).
        Returns list of proposed experiments above confidence threshold.
        """
        if not self._loaded:
            return []

        # Cluster conversations by quantum topic
        topics = {
            "phase_conjugation": ["chi_pc", "phase conjugat", "χ_pc", "0.946"],
            "negentropy": ["negentropy", "negentropic", "ξ", "xi_", "127.4"],
            "shapiro_delay": ["shapiro", "delay", "Δt", "negative"],
            "area_law": ["area-law", "entropy", "s₂", "boundary"],
            "non_reciprocal": ["non-reciprocal", "j_lr", "information flow"],
            "zeno": ["zeno", "1.25 mhz", "zeno freq", "stabiliz"],
        }

        proposed = []
        for topic, keywords in topics.items():
            evidence = [
                conv["id"] for conv in self._conversations
                if any(kw in conv.get("response", "").lower() for kw in keywords)
            ]
            if len(evidence) >= self.MIN_EVIDENCE_COUNT:
                hypothesis = self._synthesize_hypothesis(topic, evidence)
                exp = self.design_experiment(
                    hypothesis=hypothesis,
                    template=self._topic_to_template(topic),
                    evidence_ids=evidence[:5],
                )
                if exp.confidence >= self.CONFIDENCE_THRESHOLD:
                    proposed.append(exp)

        return proposed

    def _synthesize_hypothesis(self, topic: str, evidence: List[str]) -> str:
        """Generate a testable hypothesis string from a topic cluster."""
        templates = {
            "phase_conjugation": f"χ_PC exceeds theoretical bound (0.946 > 0.869) on ibm_fez, validatable via Bell witness with θ_lock={THETA_LOCK}°",
            "negentropy": f"Negentropic efficiency Ξ ≥ 127.4× at ΛΦ={LAMBDA_PHI:.3e} in 5-qubit GHZ circuit",
            "shapiro_delay": f"Negative Shapiro delay Δt=-2.3ns measurable via time-reversed entanglement (Loschmidt echo)",
            "area_law": f"Area-law entropy scaling S₂(A)∝|∂A| observable in 20+ qubit chain on heavy-hex topology",
            "non_reciprocal": f"Non-reciprocal info flow J_LR/J_RL=1.34 measurable via asymmetric CNOT chains",
            "zeno": f"Quantum Zeno stabilization at f_Zeno=1.25MHz extends coherence 5× in TFD circuit",
        }
        return templates.get(topic, f"Testable prediction from {topic} cluster ({len(evidence)} evidence points)")

    def _topic_to_template(self, topic: str) -> str:
        mapping = {
            "phase_conjugation": "chi_pc",
            "negentropy": "ghz",
            "shapiro_delay": "tfd",
            "area_law": "ghz",
            "non_reciprocal": "bell",
            "zeno": "zeno",
        }
        return mapping.get(topic, "bell")

    # ── HARDWARE SUBMISSION READINESS ─────────────────────────────────────────

    def get_hardware_ready(self) -> List[Experiment]:
        """Return experiments that are ready for IBM Quantum hardware submission."""
        return [
            e for e in self._experiments
            if e.confidence >= self.CONFIDENCE_THRESHOLD and e.status == "proposed"
        ]

    def format_for_submission(self, exp: Experiment) -> str:
        """Format an experiment as a hardware-ready submission brief."""
        return (
            f"=== HARDWARE SUBMISSION BRIEF ===\n"
            f"ID:         {exp.id}\n"
            f"Hypothesis: {exp.hypothesis}\n"
            f"Template:   {exp.circuit_template}\n"
            f"Backend:    {exp.backend}\n"
            f"Confidence: {exp.confidence:.1%}\n"
            f"Evidence:   {len(exp.evidence)} prior experiments\n"
            f"Created:    {exp.created}\n"
            f"\nTo submit: osiris lab run --template {exp.circuit_template} --backend {exp.backend}\n"
            f"           osiris quantum submit {exp.circuit_template} {exp.backend}"
        )

    # ── CONTEXT STRING FOR LLM ────────────────────────────────────────────────

    def build_llm_context(self, query: str) -> str:
        """
        Build a concise context string to prepend to LLM calls,
        incorporating actual measured experiment data from disk.
        """
        parts = [
            f"RESEARCH CONTEXT: ΛΦ={LAMBDA_PHI:.3e} | θ_lock={THETA_LOCK}° | "
            f"Φ_threshold={PHI_THRESHOLD} | χ_PC={CHI_PC}",
        ]

        # Inject real measured data (not hardcoded strings)
        try:
            from .analysis import get_analyzer
            az = get_analyzer()
            parts.append(az.llm_context_block())
        except Exception:
            pass

        # Corpus-based hypothesis context (if corpus loaded)
        if self._loaded:
            ctx = self.get_context_for_query(query, top_k=3)
            if ctx.hypothesis_chain:
                parts.append("Relevant corpus results:")
                for h in ctx.hypothesis_chain[:2]:
                    parts.append(f"  • {h[:120]}")

        proposed = self.get_hardware_ready()
        if proposed:
            parts.append(f"{len(proposed)} hardware-ready experiment(s):")
            for e in proposed[:2]:
                parts.append(f"  [{e.id}] {e.hypothesis[:80]} (conf={e.confidence:.0%})")

        return "\n".join(parts)

    # ── PERSISTENCE ───────────────────────────────────────────────────────────

    def _log_experiment(self, exp: Experiment):
        try:
            with open(_EXPERIMENT_LOG, "a") as f:
                record = {
                    "id": exp.id, "title": exp.title,
                    "hypothesis": exp.hypothesis,
                    "template": exp.circuit_template,
                    "backend": exp.backend,
                    "confidence": exp.confidence,
                    "status": exp.status,
                    "created": exp.created,
                }
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    def _load_confidence_db(self):
        try:
            if os.path.exists(_CONFIDENCE_DB):
                with open(_CONFIDENCE_DB) as f:
                    self._hypothesis_db = json.load(f)
        except Exception:
            self._hypothesis_db = {}

    def _save_confidence_db(self):
        try:
            os.makedirs(os.path.dirname(_CONFIDENCE_DB), exist_ok=True)
            with open(_CONFIDENCE_DB, "w") as f:
                json.dump(self._hypothesis_db, f, indent=2)
        except Exception:
            pass


# ── SINGLETON ─────────────────────────────────────────────────────────────────

_engine: Optional[PhysicsResearchEngine] = None
_engine_lock = threading.Lock()


def get_research_engine(auto_load: bool = True) -> PhysicsResearchEngine:
    """Get the singleton PhysicsResearchEngine, optionally auto-loading corpus."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = PhysicsResearchEngine()
            if auto_load:
                _engine.load_corpus()
    return _engine
