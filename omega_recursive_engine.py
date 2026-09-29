#!/usr/bin/env python3
"""
Ω-RECURSIVE INTENT-DEDUCTION ENGINE v1.1.0-ΛΦ

Upgrade:
- streaming per-item indexing (no whole-corpus memory blowups)
- evidence backreferences: IntentVector -> top-K line anchors
- additional outputs: capability_matrix.json, resource_analysis.json, project_plan.json, intent_backrefs.json
- secret-safe redaction (hash kept, text removed)

Stdlib-only core; adapters unchanged.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

# ──────────────────────────────────────────────────────────────────────────────
# 0) ΛΦ / CCCE CONSTANTS (stable, auditable)
# ──────────────────────────────────────────────────────────────────────────────

class Φ:
    LAMBDA_PHI: float = 2.176435e-8
    THETA_LOCK_DEG: float = 51.843
    PHI_THRESHOLD: float = 0.7734
    EPS: float = 1e-12

    @classmethod
    def ccce(cls, Λ: float, Φ_val: float, Γ: float) -> float:
        return (Λ * cls.LAMBDA_PHI) / max(Γ, cls.EPS)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _sha256_text(s: str) -> str:
    return _sha256_bytes(s.encode("utf-8", errors="ignore"))

def json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, bytes):
        return {"__bytes__": True, "sha256": _sha256_bytes(obj), "len": len(obj)}
    if isinstance(obj, Path):
        return str(obj)
    if dataclasses.is_dataclass(obj):
        return {k: json_safe(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.name
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON-serializable")

# ──────────────────────────────────────────────────────────────────────────────
# 1) Types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Provenance:
    source: str
    locator: str
    sha256: str
    size_bytes: int = 0
    mtime: Optional[float] = None
    order: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StreamLine:
    item_id: str
    k: int
    text: str
    prov: Provenance
    scope: str = ""
    lex_class: str = ""
    syntax_role: str = ""
    tags: List[str] = field(default_factory=list)
    future_tags: List[str] = field(default_factory=list)

@dataclass
class EvidenceLineRef:
    item_id: str
    k: int
    sha256_line: str
    locator: str
    lex: str
    syntax: str
    tags: List[str]
    text: str  # may be redacted

@dataclass
class ItemIndexSummary:
    L: int
    tag_counts: Dict[str, int]
    syntax_counts: Dict[str, int]
    sample_down: Dict[int, str]
    sample_up: Dict[int, str]
    sample_fused: Dict[int, Tuple[str, str]]
    top_evidence: List[EvidenceLineRef]  # strongest anchors

@dataclass
class CorpusStats:
    total_items: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    genesis_hash: str = ""
    files_or_msgs: List[str] = field(default_factory=list)

# ──────────────────────────────────────────────────────────────────────────────
# 2) Input adapters
# ──────────────────────────────────────────────────────────────────────────────

class ChatSessionAdapter:
    def __init__(self, path: Path):
        self.path = path

    def iter_items(self) -> Iterator[Tuple[str, str]]:
        suffix = self.path.suffix.lower()
        raw = self.path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".jsonl":
            for i, line in enumerate(raw.splitlines(), start=1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                mid = str(obj.get("id") or obj.get("message_id") or f"msg-{i:06d}")
                content = str(obj.get("content") or obj.get("text") or "")
                yield mid, content
            return

        if suffix == ".json":
            obj = json.loads(raw)
            msgs = obj.get("messages") if isinstance(obj, dict) else obj
            if not isinstance(msgs, list):
                raise ValueError("JSON chat must contain a list of messages or {messages:[...]} object.")
            for i, m in enumerate(msgs, start=1):
                mid = str(m.get("id") or m.get("message_id") or f"msg-{i:06d}")
                content = str(m.get("content") or m.get("text") or "")
                yield mid, content
            return

        yield f"msg-{1:06d}", raw

    def iter_lines(self) -> Iterator[StreamLine]:
        order = 0
        for mid, content in self.iter_items():
            order += 1
            lines = content.splitlines()
            joined = "\n".join(lines)
            prov = Provenance(
                source="chat",
                locator=f"{self.path.name}::{mid}",
                sha256=_sha256_text(joined),
                size_bytes=len(joined.encode("utf-8", errors="ignore")),
                mtime=self.path.stat().st_mtime,
                order=order,
            )
            for k, t in enumerate(lines, start=1):
                yield StreamLine(item_id=mid, k=k, text=t, prov=prov)

class ZipCorpusAdapter:
    def __init__(self, zip_path: Path, include_globs: Optional[List[str]] = None):
        self.zip_path = zip_path
        self.include_globs = include_globs or ["**/*"]

    def iter_lines(self) -> Iterator[StreamLine]:
        order = 0
        with zipfile.ZipFile(self.zip_path, "r") as zf:
            members = [m for m in zf.namelist() if not m.endswith("/")]
            members.sort()
            for member in members:
                if self.include_globs and not any(Path(member).match(g) for g in self.include_globs):
                    continue
                order += 1
                b = zf.read(member)
                text = b.decode("utf-8", errors="ignore")
                prov = Provenance(
                    source="zip",
                    locator=f"{self.zip_path.name}::{member}",
                    sha256=_sha256_bytes(b),
                    size_bytes=len(b),
                    mtime=None,
                    order=order,
                    extra={"zip_member": member},
                )
                for k, line in enumerate(text.splitlines(), start=1):
                    yield StreamLine(item_id=member, k=k, text=line, prov=prov)

class DirectoryCorpusAdapter:
    def __init__(self, root: Path, include_suffixes: Optional[List[str]] = None):
        self.root = root
        self.include_suffixes = [s.lower() for s in (include_suffixes or [".py", ".sh", ".md", ".txt", ".json", ".yaml", ".yml"])]

    def iter_lines(self) -> Iterator[StreamLine]:
        order = 0
        files = [p for p in self.root.rglob("*") if p.is_file() and p.suffix.lower() in self.include_suffixes]
        files.sort(key=lambda p: str(p).lower())
        for p in files:
            order += 1
            b = p.read_bytes()
            text = b.decode("utf-8", errors="ignore")
            prov = Provenance(
                source="dir",
                locator=str(p),
                sha256=_sha256_bytes(b),
                size_bytes=len(b),
                mtime=p.stat().st_mtime,
                order=order,
            )
            for k, line in enumerate(text.splitlines(), start=1):
                yield StreamLine(item_id=str(p), k=k, text=line, prov=prov)

# ──────────────────────────────────────────────────────────────────────────────
# 3) Indexer (streaming per-item) + evidence anchors
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class IndexConfig:
    max_sample_lines: int = 8
    max_evidence_lines: int = 12
    PATTERNS: Dict[str, List[str]] = field(default_factory=lambda: {
        "quantum": [r"\bqiskit\b", r"\bqiskit_ibm_", r"\bibm_", r"\bQuantumCircuit\b"],
        "crypto": [r"\bsha256\b", r"\bhashlib\b", r"\bHMAC\b"],
        "secrets": [r"API[_-]?KEY", r"SECRET", r"BEGIN\s+PRIVATE\s+KEY", r"IBM_QUANTUM_TOKEN"],
        "io_file": [r"\bopen\(", r"\bread_text\b", r"\bzipfile\b", r"\brglob\("],
        "net": [r"\brequests\b", r"\bsocket\b", r"\bhttp\b"],
        "cli": [r"\bargparse\b", r"^#!", r"\bsys\.argv\b"],
        "physics": [r"\bLAMBDA_PHI\b", r"\bTHETA_LOCK\b", r"\bW_?2\b", r"[ΓΦΛΞ]"],
        "plan": [r"\bmilestone\b", r"\broadway\b", r"\bLOE\b", r"\bCI\b", r"\bgate\b"],
        "legal_ip": [r"\blicense\b", r"\bCAGE\b", r"\bpreservation\b", r"\bcease\b", r"\baffidavit\b"],
    })

class CorpusIndexer:
    def __init__(self, cfg: Optional[IndexConfig] = None):
        self.cfg = cfg or IndexConfig()
        self.stats = CorpusStats()
        self._genesis_acc = hashlib.sha256()

    def _classify_lex(self, s: str) -> str:
        t = s.strip()
        if not t:
            return "blank"
        if t.startswith("#") or t.startswith("//"):
            return "comment"
        return "code"

    def _classify_syntax(self, s: str) -> str:
        t = s.strip()
        if not t:
            return "blank"
        if t.startswith("import ") or t.startswith("from "):
            return "import"
        if t.startswith("class "):
            return "class_def"
        if t.startswith("def "):
            return "def"
        if t.startswith("BEGIN:VEVENT") or t.startswith("RRULE:"):
            return "ical"
        if t.startswith("$ ") or t.startswith("sudo ") or t.startswith("cd "):
            return "command"
        return "stmt"

    def _tags(self, s: str) -> List[str]:
        out: List[str] = []
        for tag, pats in self.cfg.PATTERNS.items():
            for pat in pats:
                if re.search(pat, s):
                    out.append(tag)
                    break
        return out

    def _evidence_score(self, ln: StreamLine) -> float:
        # conservative, auditable heuristic (no semantics hallucination)
        score = 0.0
        if ln.syntax_role in ("def", "class_def", "command"):
            score += 2.0
        if "secrets" in ln.tags:
            score += 10.0  # high-importance risk anchor
        score += 0.5 * len(ln.tags)
        if len(ln.text.strip()) > 0:
            score += 0.1
        return score

    def index_stream(self, stream: Iterable[StreamLine], out_jsonl: Optional[Path] = None) -> Tuple[CorpusStats, Dict[str, ItemIndexSummary]]:
        writer = out_jsonl.open("w", encoding="utf-8") if out_jsonl else None
        per_item: Dict[str, ItemIndexSummary] = {}

        cur_id: Optional[str] = None
        buf: List[StreamLine] = []

        def flush():
            nonlocal buf, cur_id
            if cur_id is None or not buf:
                return

            self.stats.total_items += 1
            self.stats.files_or_msgs.append(cur_id)

            # Genesis accumulator (order-stable)
            prov0 = buf[0].prov
            self._genesis_acc.update((prov0.source + "|" + prov0.locator + "|" + prov0.sha256 + "|" + str(prov0.order)).encode("utf-8", errors="ignore"))

            # Forward annotate
            tag_counts: Dict[str, int] = {}
            syntax_counts: Dict[str, int] = {}
            scored: List[Tuple[float, EvidenceLineRef]] = []

            for ln in buf:
                ln.lex_class = self._classify_lex(ln.text)
                ln.syntax_role = self._classify_syntax(ln.text)
                ln.tags = self._tags(ln.text)

                for t in ln.tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
                syntax_counts[ln.syntax_role] = syntax_counts.get(ln.syntax_role, 0) + 1

                # evidence anchor candidate
                sha_line = _sha256_text(ln.text)
                redacted = "[REDACTED]" if "secrets" in ln.tags else ln.text
                ref = EvidenceLineRef(
                    item_id=ln.item_id,
                    k=ln.k,
                    sha256_line=sha_line,
                    locator=ln.prov.locator,
                    lex=ln.lex_class,
                    syntax=ln.syntax_role,
                    tags=ln.tags,
                    text=redacted,
                )
                scored.append((self._evidence_score(ln), ref))

            # Backward future tags
            future: set[str] = set()
            for ln in reversed(buf):
                ln.future_tags = sorted(future)
                future |= set(ln.tags)

            # Samples
            L = len(buf)
            sample_n = min(self.cfg.max_sample_lines, L)
            idx = list(range(1, sample_n + 1))
            down = {k: buf[k - 1].text for k in idx}
            up = {k: buf[L - k].text for k in idx}
            fused = {k: (down[k], up[k]) for k in idx}

            # Top evidence lines
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [ref for _, ref in scored[: self.cfg.max_evidence_lines]]

            per_item[cur_id] = ItemIndexSummary(
                L=L,
                tag_counts=tag_counts,
                syntax_counts=syntax_counts,
                sample_down=down,
                sample_up=up,
                sample_fused=fused,
                top_evidence=top,
            )

            # Emit JSONL index
            if writer:
                for ln in buf:
                    record = {
                        "L0": {"item_id": ln.item_id, "k": ln.k, "text": ln.text, "sha256_line": _sha256_text(ln.text)},
                        "L1": {"prov": json_safe(ln.prov), "lex": ln.lex_class, "syntax": ln.syntax_role},
                        "L2": {"scope": ln.scope},
                        "L3": {"tags": ln.tags, "future_tags": ln.future_tags},
                    }
                    writer.write(json.dumps(record, ensure_ascii=False) + "\n")

            buf = []

        try:
            for ln in stream:
                self.stats.total_lines += 1
                self.stats.total_bytes += len(ln.text.encode("utf-8", errors="ignore"))

                if cur_id is None:
                    cur_id = ln.item_id

                if ln.item_id != cur_id:
                    flush()
                    cur_id = ln.item_id

                buf.append(ln)

            flush()

            # finalize genesis hash
            self.stats.files_or_msgs.sort()
            self.stats.genesis_hash = self._genesis_acc.hexdigest()[:16]
        finally:
            if writer:
                writer.close()

        return self.stats, per_item

# ──────────────────────────────────────────────────────────────────────────────
# 4) L2–L7: intents + capability + resources + plan (minimal real)
# ──────────────────────────────────────────────────────────────────────────────

class IntentCategory(Enum):
    META_SYSTEM = auto()
    QUANTUM_FRAMEWORK = auto()
    HARDWARE_VALIDATION = auto()
    SECURITY_DEFENSE = auto()
    PUBLICATION_IP = auto()
    THEORETICAL_PHYSICS = auto()
    ORGANISM_CREATION = auto()
    COMMERCIAL_DEPLOYMENT = auto()

@dataclass
class IntentVector:
    id: str
    item_id: str
    category: IntentCategory
    explicit: str
    implicit: str = ""
    Λ: float = 0.0
    Φv: float = 0.0
    Γ: float = 0.0
    priority: str = "MEDIUM"

    @property
    def Ξ(self) -> float:
        return Φ.ccce(self.Λ, self.Φv, self.Γ)

class IntentDeducer:
    def _cat_from_tags(self, tags: Dict[str, int]) -> IntentCategory:
        if tags.get("secrets", 0) > 0 or tags.get("crypto", 0) > 0:
            return IntentCategory.SECURITY_DEFENSE
        if tags.get("quantum", 0) > 0:
            return IntentCategory.HARDWARE_VALIDATION
        if tags.get("physics", 0) > 0:
            return IntentCategory.THEORETICAL_PHYSICS
        if tags.get("plan", 0) > 0:
            return IntentCategory.META_SYSTEM
        if tags.get("legal_ip", 0) > 0:
            return IntentCategory.PUBLICATION_IP
        return IntentCategory.META_SYSTEM

    def deduce_individual(self, stats: CorpusStats, items: Dict[str, ItemIndexSummary]) -> Tuple[List[IntentVector], Dict[str, List[EvidenceLineRef]]]:
        intents: List[IntentVector] = []
        backrefs: Dict[str, List[EvidenceLineRef]] = {}

        for i, (item_id, summ) in enumerate(sorted(items.items(), key=lambda kv: kv[0])):
            cat = self._cat_from_tags(summ.tag_counts)

            # conservative scalar proxies (auditable, not mystical):
            # Λ ~ code density; Φv ~ tag diversity; Γ ~ risk density (secrets/net)
            code = summ.syntax_counts.get("def", 0) + summ.syntax_counts.get("class_def", 0) + summ.syntax_counts.get("stmt", 0)
            L = max(summ.L, 1)
            tag_div = len([t for t, c in summ.tag_counts.items() if c > 0])
            risk = summ.tag_counts.get("secrets", 0) + summ.tag_counts.get("net", 0)

            Λ = min(1.0, code / L)
            Φv = min(1.0, tag_div / 8.0)
            Γ = min(1.0, risk / max(1, L))

            priority = "CRITICAL" if summ.tag_counts.get("secrets", 0) > 0 else ("HIGH" if summ.tag_counts.get("quantum", 0) > 0 else "MEDIUM")

            iv = IntentVector(
                id=f"IV-{i:04d}",
                item_id=item_id,
                category=cat,
                explicit=f"Analyze {item_id} ({cat.name})",
                implicit="Provenance-anchored indexing + actionable synthesis",
                Λ=round(Λ, 6),
                Φv=round(Φv, 6),
                Γ=round(Γ, 6),
                priority=priority,
            )
            intents.append(iv)
            backrefs[iv.id] = summ.top_evidence

        return intents, backrefs

    def synthesize_collective(self, intents: List[IntentVector], stats: CorpusStats) -> Dict[str, Any]:
        if not intents:
            return {"unified_intent": "", "aggregate": {}, "genesis_hash": stats.genesis_hash}
        Λm = sum(iv.Λ for iv in intents) / len(intents)
        Φm = sum(iv.Φv for iv in intents) / len(intents)
        Γm = sum(iv.Γ for iv in intents) / len(intents)
        return {
            "unified_intent": "Corpus → provenance index → intent vectors → capability/resources → CI-gated plan.",
            "aggregate": {"Λ": round(Λm, 6), "Φ": round(Φm, 6), "Γ": round(Γm, 6), "Ξ": round(Φ.ccce(Λm, Φm, Γm), 12)},
            "genesis_hash": stats.genesis_hash,
        }

class ProjectPlanner:
    def capability_matrix(self, items: Dict[str, ItemIndexSummary]) -> Dict[str, Any]:
        # aggregate tag/syntax counts
        tag_tot: Dict[str, int] = {}
        syn_tot: Dict[str, int] = {}
        for s in items.values():
            for t, c in s.tag_counts.items():
                tag_tot[t] = tag_tot.get(t, 0) + c
            for k, c in s.syntax_counts.items():
                syn_tot[k] = syn_tot.get(k, 0) + c

        # simple scores (0..1)
        def norm(x): return float(x) / float(max(1, sum(syn_tot.values())))
        scores = {
            "code_authoring": min(1.0, norm(syn_tot.get("def", 0) + syn_tot.get("class_def", 0))),
            "cli_ops": min(1.0, norm(syn_tot.get("command", 0))),
            "security_awareness": min(1.0, float(tag_tot.get("secrets", 0) + tag_tot.get("crypto", 0)) / max(1, sum(tag_tot.values()))),
            "quantum_ops": min(1.0, float(tag_tot.get("quantum", 0)) / max(1, sum(tag_tot.values()))),
        }

        return {"tag_totals": tag_tot, "syntax_totals": syn_tot, "scores": {k: round(v, 6) for k, v in scores.items()}}

    def resource_analysis(self, stats: CorpusStats, cap: Dict[str, Any]) -> Dict[str, Any]:
        # LOE heuristic: bytes/lines scale + risk overhead
        base = max(1.0, stats.total_lines / 250.0)
        risk = 1.0 + 2.0 * cap["scores"].get("security_awareness", 0.0)
        loe = base * risk
        return {
            "loe_hours_est": round(loe * 2.0, 2),  # coarse
            "constraints": ["stdlib-first core", "fail-closed provenance", "secret-safe redaction"],
            "risk_budget_Gamma": {
                "Γ_operational": round(min(1.0, 0.1 + 0.5 * cap["scores"].get("security_awareness", 0.0)), 6),
                "notes": "Higher secrets/net signal => higher operational Γ budget allocation.",
            },
        }

    def plan(self, intents: List[IntentVector], cap: Dict[str, Any]) -> Dict[str, Any]:
        # minimal CI-gated milestones
        return {
            "milestones": [
                {"id": "M01", "name": "Emit line_index.jsonl + genesis_hash", "ci_gate": "hash-chain reproducible", "priority": "CRITICAL"},
                {"id": "M02", "name": "Emit intent_backrefs.json (IV→evidence)", "ci_gate": ">=1 anchor per IV", "priority": "CRITICAL"},
                {"id": "M03", "name": "Capability + resource reports", "ci_gate": "schemas validate", "priority": "HIGH"},
                {"id": "M04", "name": "Downstream prompt transforms (L6) + execution plan (L7)", "ci_gate": "operator-approved", "priority": "HIGH"},
            ],
            "critical_path": ["M01", "M02", "M03", "M04"],
            "capability_scores": cap.get("scores", {}),
            "intent_count": len(intents),
        }

# ──────────────────────────────────────────────────────────────────────────────
# 5) Engine orchestrator
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EngineOutput:
    metadata: Dict[str, Any]
    corpus: Dict[str, Any]
    items: Dict[str, Any]
    intents: Dict[str, Any]
    capability: Dict[str, Any]
    resources: Dict[str, Any]
    plan: Dict[str, Any]
    quantum_synthesis: Optional[Dict[str, Any]] = None

class OmegaRecursiveEngine:
    def __init__(self, out_dir: Path, cfg: Optional[IndexConfig] = None):
        self.out_dir = out_dir
        self.cfg = cfg or IndexConfig()
        self.indexer = CorpusIndexer(self.cfg)
        self.deducer = IntentDeducer()
        self.planner = ProjectPlanner()

    def run_quantum_synthesis(self) -> Dict[str, Any]:
        """
        Sprint 2: Boots 14.007 GHz Tetrahedral Drive simulation, calibrates
        Lambda-Phi cross-domain symmetry, and generates IBM Fez quantum capsule.
        """
        try:
            from osiris_quantum_bridge import (
                TetrahedralDriveSimulator,
                calibrate_lambda_phi_symmetry,
                IBMFezQuantumBridge,
                HAS_QISKIT
            )
            calibration = calibrate_lambda_phi_symmetry()
            sim = TetrahedralDriveSimulator().evaluate_drive_trajectory(t_max_ns=2.0, steps=10)

            qiskit_info = None
            if HAS_QISKIT:
                bridge = IBMFezQuantumBridge()
                qiskit_info = bridge.generate_qiskit_capsule()

            return {
                "status": "SYNTHESIZED",
                "calibration": calibration,
                "tetrahedral_drive_sim": sim,
                "qiskit_bridge": qiskit_info,
                "timestamp_utc": _utc_now_iso()
            }
        except Exception as e:
            return {
                "status": "DEGRADED",
                "error": str(e),
                "timestamp_utc": _utc_now_iso()
            }

    def run(self, adapter: Union[ChatSessionAdapter, ZipCorpusAdapter, DirectoryCorpusAdapter]) -> EngineOutput:
        self.out_dir.mkdir(parents=True, exist_ok=True)

        line_index_path = self.out_dir / "line_index.jsonl"
        stats, items = self.indexer.index_stream(adapter.iter_lines(), out_jsonl=line_index_path)

        intents, backrefs = self.deducer.deduce_individual(stats, items)
        collective = self.deducer.synthesize_collective(intents, stats)

        capability = self.planner.capability_matrix(items)
        resources = self.planner.resource_analysis(stats, capability)
        plan = self.planner.plan(intents, capability)
        quantum_synth = self.run_quantum_synthesis()

        # Persist JSON artifacts
        (self.out_dir / "intent_backrefs.json").write_text(
            json.dumps({k: [json_safe(x) for x in v] for k, v in backrefs.items()}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.out_dir / "capability_matrix.json").write_text(json.dumps(json_safe(capability), indent=2, ensure_ascii=False), encoding="utf-8")
        (self.out_dir / "resource_analysis.json").write_text(json.dumps(json_safe(resources), indent=2, ensure_ascii=False), encoding="utf-8")
        (self.out_dir / "project_plan.json").write_text(json.dumps(json_safe(plan), indent=2, ensure_ascii=False), encoding="utf-8")
        (self.out_dir / "quantum_synthesis.json").write_text(json.dumps(json_safe(quantum_synth), indent=2, ensure_ascii=False), encoding="utf-8")

        summary_path = self.out_dir / "omega_recursive_analysis.json"
        out = EngineOutput(
            metadata={
                "engine_version": "Ω-Recursive v1.1.0-ΛΦ",
                "timestamp_utc": _utc_now_iso(),
                "lambda_phi": Φ.LAMBDA_PHI,
                "theta_lock_deg": Φ.THETA_LOCK_DEG,
                "output_dir": str(self.out_dir),
            },
            corpus={
                "total_items": stats.total_items,
                "total_lines": stats.total_lines,
                "total_bytes": stats.total_bytes,
                "genesis_hash": stats.genesis_hash,
                "index_jsonl": str(line_index_path),
            },
            items={k: json_safe(v) for k, v in items.items()},
            intents={
                "individual_vectors": [json_safe(iv) for iv in intents],
                "collective_synthesis": collective,
            },
            capability=capability,
            resources=resources,
            plan=plan,
            quantum_synthesis=quantum_synth,
        )
        summary_path.write_text(json.dumps(json_safe(out), indent=2, ensure_ascii=False), encoding="utf-8")
        return out

# ──────────────────────────────────────────────────────────────────────────────
# 6) CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Ω-Recursive Intent Engine v1.1.0 — chat/zip/dir → index → intent+evidence → plan")
    p.add_argument("--mode", choices=["chat", "zip", "dir"], required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--out", default="./omega_out")
    p.add_argument("--include-suffix", action="append", default=None)
    p.add_argument("--include-glob", action="append", default=None)
    p.add_argument("--sample-lines", type=int, default=8)
    p.add_argument("--evidence-lines", type=int, default=12)
    return p

def main(argv: Optional[List[str]] = None) -> int:
    args = build_argparser().parse_args(argv)
    out_dir = Path(args.out).expanduser().resolve()

    cfg = IndexConfig(
        max_sample_lines=max(1, int(args.sample_lines)),
        max_evidence_lines=max(1, int(args.evidence_lines)),
    )
    engine = OmegaRecursiveEngine(out_dir=out_dir, cfg=cfg)

    in_path = Path(args.input).expanduser().resolve()
    if args.mode == "chat":
        adapter = ChatSessionAdapter(in_path)
    elif args.mode == "zip":
        adapter = ZipCorpusAdapter(in_path, include_globs=args.include_glob)
    else:
        adapter = DirectoryCorpusAdapter(in_path, include_suffixes=args.include_suffix)

    out = engine.run(adapter)

    print(json.dumps({
        "ok": True,
        "genesis_hash": out.corpus["genesis_hash"],
        "total_items": out.corpus["total_items"],
        "total_lines": out.corpus["total_lines"],
        "outputs": {
            "line_index_jsonl": out.corpus["index_jsonl"],
            "summary_json": str(Path(out.metadata["output_dir"]) / "omega_recursive_analysis.json"),
            "intent_backrefs": str(Path(out.metadata["output_dir"]) / "intent_backrefs.json"),
            "capability_matrix": str(Path(out.metadata["output_dir"]) / "capability_matrix.json"),
            "resource_analysis": str(Path(out.metadata["output_dir"]) / "resource_analysis.json"),
            "project_plan": str(Path(out.metadata["output_dir"]) / "project_plan.json"),
        },
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
