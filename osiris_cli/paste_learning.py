"""osiris_cli/paste_learning.py -- Governed learning and provenance for user-pasted data.

Core Governance Principle:
Records every exchange in the hash-chained ledger; learns only from eligible material
you explicitly approve. Ledger recording (L0), retrieval notes, candidate facts,
training queue candidacy, and actual weight training are separate, independent states.

Two-Step Review-and-Confirm Workflow:
1. /learn last [notes|facts|training] creates ONLY a pending proposal in the proposal store
   (learning_proposals.jsonl). It does not write notes.jsonl, candidate_facts.jsonl,
   training_queue.jsonl, or learning_ledger.jsonl.
2. /learn confirm <proposal-id> is required for promotion into those destination stores
   and records the corresponding learning audit receipt in learning_ledger.jsonl.
3. /learn cancel <proposal-id> marks the proposal cancelled without writing to destination
   stores or the audit ledger.
4. /unlearn <id> displays a preview confirmation card; /unlearn <id> --confirm executes the tombstone.

Governed-Learning Proposal Specification:
By default, learning_proposals.jsonl stores ONLY:
- proposal ID
- source exchange ID/hash & index
- content hash (SHA-256 of candidate user input)
- proposed destination (notes, facts, or training)
- user-visible title or minimal transformed metadata
- scan summary and scanner version
- timestamps (created_at, expires_at), expiry, and status
- transport & shape heuristics (input_transport, multiline, char/line counts)

Pending proposals do NOT duplicate the complete raw user paste or full mentor reply.
When /learn confirm <proposal-id> runs:
1. The proposal record is retrieved and validated (pending, not expired, not quarantined).
2. The source exchange is reread from exchanges.jsonl.
3. The content hash is recalculated and verified against the proposal's content_hash.
   If mismatched or missing, confirmation fails closed immediately.
4. The destination record is created directly from verified source exchange data.
5. The SHA-256 audit receipt is appended to learning_ledger.jsonl.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

PROPOSAL_TTL_SECONDS = 3600.0  # Proposals expire after 1 hour


@dataclass
class SecurityFinding:
    severity: str  # "BLOCK" | "WARN"
    description: str
    matched_pattern: str
    quarantine: bool = True


@dataclass
class PasteCandidate:
    exchange_hash: str
    index: int
    timestamp: str
    text: str
    reply: str
    voice: str
    char_count: int
    line_count: int
    input_transport: str  # "bracketed_paste" | "typed" | "unknown"
    is_multiline: bool
    source_type: str  # alias for backward compatibility
    findings: List[Dict[str, Any]]
    quarantined: bool


@dataclass
class LearningProposal:
    proposal_id: str
    exchange_hash: str
    exchange_index: int
    content_hash: str
    target: str  # "notes" | "facts" | "training"
    metadata: Dict[str, Any]
    scan_summary: Dict[str, Any]
    created_at: str
    expires_at: float
    status: str  # "pending" | "confirmed" | "cancelled" | "expired" | "tombstoned"
    input_transport: str
    is_multiline: bool
    char_count: int
    line_count: int
    quarantined: bool = False


def compute_content_hash(text: str) -> str:
    """Computes SHA-256 hash of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_candidate_facts(text: str) -> List[str]:
    """Deterministic extraction of proposition statements from candidate text."""
    extracted = []
    for line in text.splitlines():
        line_clean = line.strip().lstrip("-*#0123456789. ")
        if not line_clean:
            continue
        if re.search(r"\b(is|are|was|were|has|have|defined as|set to|measured at|equals|=)\b", line_clean, re.I):
            extracted.append(line_clean)
    if not extracted and text.strip():
        extracted = [text.strip()]
    return extracted


def get_exchange_by_hash(living_home: str, exchange_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieves a source exchange record from exchanges.jsonl by its hash."""
    exchanges_file = os.path.join(living_home, "exchanges.jsonl")
    if not os.path.exists(exchanges_file):
        return None
    try:
        with open(exchanges_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("hash") == exchange_hash:
                    return rec
    except Exception:
        return None
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-PROMOTION SECURITY AUDIT (SECRETS, CREDENTIALS, INJECTIONS)
# ═══════════════════════════════════════════════════════════════════════════════

SENSITIVE_PATTERNS = [
    ("private_key", re.compile(r"-----\s*BEGIN[ A-Z0-9_-]*PRIVATE KEY\s*-----", re.IGNORECASE)),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("openai_api_key", re.compile(r"\bsk-[a-zA-Z0-9]{32,64}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b")),
    ("aws_access_key", re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b")),
    ("generic_secret_assignment", re.compile(r"(?i)(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]")),
    ("destructive_command", re.compile(r"\b(rm\s+-rf\s+[/~]|dd\s+if=|mkfs\.|:(){:|:&};:)")),
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)disregard\s+(all\s+)?(previous|prior)\s+constraints"),
    re.compile(r"(?i)you\s+are\s+now\s+(in\s+)?(DAN|developer|jailbreak|unrestricted)\s+mode"),
    re.compile(r"(?i)reveal\s+(your\s+)?(system\s+prompt|core\s+instructions)"),
]


def assess_security(text: str) -> List[SecurityFinding]:
    """Evaluates text against known risk patterns (credentials, destructive commands, or prompt injections).
    Known-pattern scans quarantine detected risks; no match is not a safety, privacy, or training-suitability guarantee.
    """
    findings = []
    for name, pattern in SENSITIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(SecurityFinding(
                severity="BLOCK",
                description=f"Detected pattern match: {name}",
                matched_pattern=match.group(0)[:20] + "...",
                quarantine=True
            ))

    for pattern in PROMPT_INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(SecurityFinding(
                severity="BLOCK",
                description="Detected prompt-injection pattern match",
                matched_pattern=match.group(0),
                quarantine=True
            ))

    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER AND AUDIT RECEIPT INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

def get_learning_ledger_path(living_home: str) -> str:
    return os.path.join(living_home, "learning_ledger.jsonl")


def get_proposals_path(living_home: str) -> str:
    return os.path.join(living_home, "learning_proposals.jsonl")


def append_learning_ledger(living_home: str, action: str, details: Dict[str, Any]) -> str:
    """Appends an immutable SHA-256 hash-chained entry to learning_ledger.jsonl."""
    ledger_path = get_learning_ledger_path(living_home)
    prev_hash = "0" * 64
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if lines:
                    last_rec = json.loads(lines[-1])
                    prev_hash = last_rec.get("hash", prev_hash)
        except Exception:
            pass

    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "epoch": time.time(),
        "action": action,
        "details": details,
        "prev_hash": prev_hash
    }
    canon_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    entry_hash = hashlib.sha256(canon_bytes).hexdigest()
    payload["hash"] = entry_hash

    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

    return entry_hash


# ═══════════════════════════════════════════════════════════════════════════════
# CANDIDATE RESOLUTION AND REVIEW CARD
# ═══════════════════════════════════════════════════════════════════════════════

def get_last_paste_candidate(living_home: str) -> Optional[PasteCandidate]:
    """Finds the most recent pasted or unverified exchange from exchanges.jsonl."""
    exchanges_file = os.path.join(living_home, "exchanges.jsonl")
    if not os.path.exists(exchanges_file):
        return None

    last_record = None
    try:
        with open(exchanges_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                # Check for bracketed_paste, unknown transport, or unconsented records
                transport = rec.get("input_transport") or rec.get("source_type") or "unknown"
                is_paste = (transport in ("bracketed_paste", "paste") or
                            rec.get("pasted") is True or
                            rec.get("learnable") is False)
                if is_paste:
                    last_record = rec
    except Exception:
        return None

    if not last_record:
        return None

    text = last_record.get("user", "")
    findings = assess_security(text)
    quarantined = any(f.quarantine for f in findings)
    transport = last_record.get("input_transport") or (
        "bracketed_paste" if last_record.get("pasted") else (
            "typed" if last_record.get("source_type") == "typed" else "unknown"
        )
    )
    is_multiline = last_record.get("is_multiline", "\n" in text.strip())

    return PasteCandidate(
        exchange_hash=last_record.get("hash", ""),
        index=last_record.get("index", 0),
        timestamp=last_record.get("t", ""),
        text=text,
        reply=last_record.get("reply", ""),
        voice=last_record.get("voice", "unknown"),
        char_count=last_record.get("char_count", len(text)),
        line_count=last_record.get("line_count", len(text.splitlines()) if text else 0),
        input_transport=transport,
        is_multiline=is_multiline,
        source_type=transport,
        findings=[asdict(f) for f in findings],
        quarantined=quarantined
    )


def format_review_card(candidate: PasteCandidate) -> str:
    """Renders the governed learning review card with explicit memory states."""
    findings_str = "None (clean)"
    if candidate.findings:
        findings_str = "\n".join(f"    - [{f['severity']}] {f['description']} (match: {f['matched_pattern']})"
                                   for f in candidate.findings)

    preview_text = candidate.text
    if len(preview_text) > 280:
        preview_text = preview_text[:280] + f" ... [{len(candidate.text) - 280} chars truncated]"

    card = f"""╔══════════════════════════════════════════════════════════════════════════════╗
║                    GOVERNED LEARNING CANDIDATE REVIEW                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
  Source Exchange    : {candidate.exchange_hash[:16]}... (index #{candidate.index})
  Recorded At        : {candidate.timestamp}
  Input Transport    : {candidate.input_transport}
  Content Shape      : multiline={candidate.is_multiline} · {candidate.line_count} lines · {candidate.char_count} chars
  Security Scan      : {findings_str}
  Quarantine Status  : {'QUARANTINED (Promotion Blocked)' if candidate.quarantined else 'CLEAN (Eligible for Proposal)'}
  Scan Advisory      : Known-pattern scans quarantine detected risks; no match is not a safety, privacy, or training-suitability guarantee.

  Candidate Excerpt:
    {preview_text}

  Separate Memory States:
    1. Ledger Recording (L0) : Immutable hash-chained audit log (already recorded).
    2. Retrieval Notes       : Attributable background notes for prompt context.
    3. Candidate Facts       : Extracted assertions labeled 'user-provided (unverified)'.
    4. Training Candidacy    : Staged in training queue; no immediate retraining occurs.
    5. Actual Retraining     : Offline batch training on verified datasets only.

  Propose Promotion (Step 1 of 2 -- writes only proposal store):
    /learn last notes [title] : Propose storing as attributable retrieval note
    /learn last facts         : Propose extracting candidate facts
    /learn last training      : Propose staging in training queue

  [!] Proposal creation writes only the proposal store (learning_proposals.jsonl).
      It does not write notes.jsonl, candidate_facts.jsonl, training_queue.jsonl, or learning_ledger.jsonl.
      Confirmation is required for promotion into those destination stores and for the corresponding learning audit receipt:
        /learn confirm <proposal-id>
╚══════════════════════════════════════════════════════════════════════════════╝"""
    return card


# ═══════════════════════════════════════════════════════════════════════════════
# TWO-STEP PROPOSAL WORKFLOW (PROPOSE -> CONFIRM / CANCEL)
# ═══════════════════════════════════════════════════════════════════════════════

def _save_proposal(living_home: str, proposal: LearningProposal) -> None:
    proposals_path = get_proposals_path(living_home)
    os.makedirs(os.path.dirname(proposals_path), exist_ok=True)
    with open(proposals_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(proposal)) + "\n")


def _update_proposal_status(living_home: str, proposal_id: str, new_status: str,
                            extra_fields: Optional[Dict[str, Any]] = None) -> bool:
    proposals_path = get_proposals_path(living_home)
    if not os.path.exists(proposals_path):
        return False
    records = []
    updated = False
    with open(proposals_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("proposal_id") == proposal_id:
                rec["status"] = new_status
                if extra_fields:
                    rec.update(extra_fields)
                updated = True
            records.append(rec)
    if updated:
        with open(proposals_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
    return updated


def get_pending_proposals(living_home: str) -> List[Dict[str, Any]]:
    proposals_path = get_proposals_path(living_home)
    if not os.path.exists(proposals_path):
        return []
    pending = []
    now = time.time()
    with open(proposals_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("status") == "pending":
                if now > rec.get("expires_at", 0):
                    rec["status"] = "expired"
                else:
                    pending.append(rec)
    return pending


def format_proposal_card(proposal: Any) -> str:
    if isinstance(proposal, LearningProposal):
        prop_id = proposal.proposal_id
        target = proposal.target
        exchange_hash = proposal.exchange_hash
        exchange_index = proposal.exchange_index
        content_hash = proposal.content_hash
        metadata = proposal.metadata
        input_transport = proposal.input_transport
        is_multiline = proposal.is_multiline
        line_count = proposal.line_count
        char_count = proposal.char_count
    else:
        prop_id = proposal.get("proposal_id", "unknown")
        target = proposal.get("target", "unknown")
        exchange_hash = proposal.get("exchange_hash", "unknown")
        exchange_index = proposal.get("exchange_index", 0)
        content_hash = proposal.get("content_hash", "")
        metadata = proposal.get("metadata", proposal.get("payload", {}))
        input_transport = proposal.get("input_transport", "unknown")
        is_multiline = proposal.get("is_multiline", False)
        line_count = proposal.get("line_count", 0)
        char_count = proposal.get("char_count", 0)

    target_meta = ""
    if target == "notes":
        target_meta = f"  Proposed Title     : {metadata.get('title', 'Untitled')}\n"
    elif target == "facts":
        target_meta = f"  Extracted Facts    : {metadata.get('fact_count', 0)} proposition(s)\n"
    elif target == "training":
        target_meta = f"  Training Model     : {metadata.get('voice', 'default')}\n"

    card = f"""╔══════════════════════════════════════════════════════════════════════════════╗
║                    PENDING GOVERNED LEARNING PROPOSAL                        ║
║                 Proposal ID: {prop_id} (Status: PENDING)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
  Target Destination : {target}
{target_meta}  Source Exchange    : {exchange_hash[:16]}... (exchange #{exchange_index})
  Content SHA-256    : {content_hash[:16]}...
  Transport / Shape  : {input_transport} · multiline={is_multiline} ({line_count} lines, {char_count} chars)
  TTL Expiration     : 60 minutes from creation
  Raw Text Retention : None (metadata only; confirmation rereads and verifies source)

  [!] Proposal creation writes only the proposal store (learning_proposals.jsonl).
      It does not write notes.jsonl, candidate_facts.jsonl, training_queue.jsonl, or learning_ledger.jsonl.
      Confirmation is required for promotion into those destination stores and for the corresponding learning audit receipt:
        /learn confirm {prop_id}

  To discard this proposal without making any changes, run:
    /learn cancel {prop_id}
╚══════════════════════════════════════════════════════════════════════════════╝"""
    return card


def propose_notes(living_home: str, candidate: PasteCandidate, title: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """Step 1: Creates a pending proposal to store a retrieval note.
    Writes only the proposal store (learning_proposals.jsonl); does not write destination stores or ledger.
    """
    if candidate.quarantined:
        return False, "[!] Cannot create proposal: candidate is quarantined due to sensitive findings.", None

    prop_id = f"prop-{hashlib.sha256(f'{candidate.exchange_hash}:notes:{time.time()}'.encode('utf-8')).hexdigest()[:8]}"
    note_title = title.strip() if title else f"Pasted Note {candidate.exchange_hash[:8]}"
    content_hash = compute_content_hash(candidate.text)
    proposal = LearningProposal(
        proposal_id=prop_id,
        exchange_hash=candidate.exchange_hash,
        exchange_index=candidate.index,
        content_hash=content_hash,
        target="notes",
        metadata={"title": note_title},
        scan_summary={"scanned": True, "quarantined": False, "findings_count": len(candidate.findings), "scanner_version": "1.0.0"},
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        expires_at=time.time() + PROPOSAL_TTL_SECONDS,
        status="pending",
        input_transport=candidate.input_transport,
        is_multiline=candidate.is_multiline,
        char_count=candidate.char_count,
        line_count=candidate.line_count,
        quarantined=candidate.quarantined
    )
    _save_proposal(living_home, proposal)
    return True, format_proposal_card(proposal), prop_id


def propose_facts(living_home: str, candidate: PasteCandidate) -> Tuple[bool, str, Optional[str]]:
    """Step 1: Creates a pending proposal to extract candidate facts.
    Writes only the proposal store (learning_proposals.jsonl); does not write destination stores or ledger.
    """
    if candidate.quarantined:
        return False, "[!] Cannot create proposal: candidate is quarantined due to sensitive findings.", None

    extracted = extract_candidate_facts(candidate.text)
    content_hash = compute_content_hash(candidate.text)
    prop_id = f"prop-{hashlib.sha256(f'{candidate.exchange_hash}:facts:{time.time()}'.encode('utf-8')).hexdigest()[:8]}"
    proposal = LearningProposal(
        proposal_id=prop_id,
        exchange_hash=candidate.exchange_hash,
        exchange_index=candidate.index,
        content_hash=content_hash,
        target="facts",
        metadata={"fact_count": len(extracted)},
        scan_summary={"scanned": True, "quarantined": False, "findings_count": len(candidate.findings), "scanner_version": "1.0.0"},
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        expires_at=time.time() + PROPOSAL_TTL_SECONDS,
        status="pending",
        input_transport=candidate.input_transport,
        is_multiline=candidate.is_multiline,
        char_count=candidate.char_count,
        line_count=candidate.line_count,
        quarantined=candidate.quarantined
    )
    _save_proposal(living_home, proposal)
    return True, format_proposal_card(proposal), prop_id


def propose_training(living_home: str, candidate: PasteCandidate) -> Tuple[bool, str, Optional[str]]:
    """Step 1: Creates a pending proposal to stage an exchange in the training queue.
    Writes only the proposal store (learning_proposals.jsonl); does not write destination stores or ledger.
    """
    if candidate.quarantined:
        return False, "[!] Cannot create proposal: candidate is quarantined due to sensitive findings.", None

    content_hash = compute_content_hash(candidate.text)
    prop_id = f"prop-{hashlib.sha256(f'{candidate.exchange_hash}:training:{time.time()}'.encode('utf-8')).hexdigest()[:8]}"
    proposal = LearningProposal(
        proposal_id=prop_id,
        exchange_hash=candidate.exchange_hash,
        exchange_index=candidate.index,
        content_hash=content_hash,
        target="training",
        metadata={"voice": candidate.voice},
        scan_summary={"scanned": True, "quarantined": False, "findings_count": len(candidate.findings), "scanner_version": "1.0.0"},
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        expires_at=time.time() + PROPOSAL_TTL_SECONDS,
        status="pending",
        input_transport=candidate.input_transport,
        is_multiline=candidate.is_multiline,
        char_count=candidate.char_count,
        line_count=candidate.line_count,
        quarantined=candidate.quarantined
    )
    _save_proposal(living_home, proposal)
    return True, format_proposal_card(proposal), prop_id


def confirm_proposal(living_home: str, proposal_id: str) -> Tuple[bool, str]:
    """Step 2: Executes durable write to target file and records ledger audit receipt.
    Rereads source exchange from exchanges.jsonl and verifies content SHA-256 hash before writing.
    """
    proposals_path = get_proposals_path(living_home)
    if not os.path.exists(proposals_path):
        return False, f"[!] Proposal {proposal_id} not found (no proposals recorded)."

    target_proposal = None
    with open(proposals_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("proposal_id") == proposal_id:
                target_proposal = rec

    if not target_proposal:
        return False, f"[!] Proposal {proposal_id} not found."

    if not isinstance(target_proposal, dict):
        return False, f"[!] Proposal {proposal_id} is malformed. Cannot confirm."

    target = target_proposal.get("target")
    if target not in ("notes", "facts", "training"):
        return False, f"[!] Proposal {proposal_id} is malformed: invalid target '{target}'."

    status = target_proposal.get("status")
    if status != "pending":
        return False, f"[!] Proposal {proposal_id} is already {status}. No changes made."

    if time.time() > target_proposal.get("expires_at", 0):
        _update_proposal_status(living_home, proposal_id, "expired")
        return False, f"[!] Proposal {proposal_id} has expired (exceeded TTL). No changes made."

    scan_summary = target_proposal.get("scan_summary", {})
    if scan_summary.get("quarantined") or target_proposal.get("quarantined"):
        return False, f"[!] Proposal {proposal_id} is quarantined due to security findings. Cannot confirm."

    exchange_hash = target_proposal.get("exchange_hash", "")
    source_rec = get_exchange_by_hash(living_home, exchange_hash)
    if not source_rec:
        return False, f"[!] Source exchange {exchange_hash[:16]} not found in exchanges.jsonl. Cannot confirm."

    # Content hash verification: reread source exchange and verify hash match
    actual_hash = compute_content_hash(source_rec.get("user", ""))
    expected_hash = target_proposal.get("content_hash", "")
    if expected_hash and actual_hash != expected_hash:
        return False, f"[!] Content hash mismatch for source exchange (expected {expected_hash[:12]}, got {actual_hash[:12]}). Confirmation blocked due to potential tampering."

    metadata = target_proposal.get("metadata", {})
    if not metadata and "payload" in target_proposal:
        metadata = target_proposal["payload"]

    created_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    if target == "notes":
        note_id = f"note-{exchange_hash[:8]}"
        note_title = metadata.get("title", f"Note {exchange_hash[:8]}")
        note_content = source_rec.get("user", "")
        record = {
            "id": note_id,
            "title": note_title,
            "content": note_content,
            "exchange_hash": exchange_hash,
            "content_hash": actual_hash,
            "source_type": target_proposal.get("input_transport", "bracketed_paste"),
            "input_transport": target_proposal.get("input_transport", "bracketed_paste"),
            "status": "active",
            "created_at": created_at
        }
        notes_path = os.path.join(living_home, "notes.jsonl")
        os.makedirs(os.path.dirname(notes_path), exist_ok=True)
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        ledger_hash = append_learning_ledger(living_home, "AUTHORIZE_NOTE", {
            "proposal_id": proposal_id,
            "note_id": note_id,
            "title": record["title"],
            "exchange_hash": exchange_hash,
            "content_hash": actual_hash,
            "input_transport": target_proposal.get("input_transport")
        })
        _update_proposal_status(living_home, proposal_id, "confirmed", {"confirmed_at": created_at, "ledger_hash": ledger_hash})
        return True, f"[OSIRIS] Proposal {proposal_id} confirmed. Promoted to retrieval note '{record['title']}' (ID: {note_id}, ledger: {ledger_hash[:12]})."

    elif target == "facts":
        facts_path = os.path.join(living_home, "candidate_facts.jsonl")
        os.makedirs(os.path.dirname(facts_path), exist_ok=True)
        facts_list = extract_candidate_facts(source_rec.get("user", ""))
        fact_ids = []
        with open(facts_path, "a", encoding="utf-8") as f:
            for idx, fact_text in enumerate(facts_list):
                fact_id = f"fact-{exchange_hash[:6]}-{idx}"
                fact_ids.append(fact_id)
                rec = {
                    "id": fact_id,
                    "fact": fact_text,
                    "label": "user-provided (unverified)",
                    "exchange_hash": exchange_hash,
                    "content_hash": actual_hash,
                    "source_type": target_proposal.get("input_transport", "bracketed_paste"),
                    "input_transport": target_proposal.get("input_transport", "bracketed_paste"),
                    "status": "active",
                    "created_at": created_at
                }
                f.write(json.dumps(rec) + "\n")

        ledger_hash = append_learning_ledger(living_home, "AUTHORIZE_FACTS", {
            "proposal_id": proposal_id,
            "fact_ids": fact_ids,
            "count": len(fact_ids),
            "exchange_hash": exchange_hash,
            "content_hash": actual_hash,
            "input_transport": target_proposal.get("input_transport")
        })
        _update_proposal_status(living_home, proposal_id, "confirmed", {"confirmed_at": created_at, "ledger_hash": ledger_hash})
        return True, f"[OSIRIS] Proposal {proposal_id} confirmed. Authorized {len(fact_ids)} candidate facts labeled 'user-provided (unverified)' (ledger: {ledger_hash[:12]})."

    elif target == "training":
        queue_path = os.path.join(living_home, "training_queue.jsonl")
        os.makedirs(os.path.dirname(queue_path), exist_ok=True)
        candidate_id = f"train-{exchange_hash[:8]}"
        record = {
            "id": candidate_id,
            "exchange_hash": exchange_hash,
            "content_hash": actual_hash,
            "user": source_rec.get("user", ""),
            "reply": source_rec.get("reply", ""),
            "voice": metadata.get("voice", source_rec.get("voice", "unpromoted_assistant")),
            "source_type": target_proposal.get("input_transport", "bracketed_paste"),
            "input_transport": target_proposal.get("input_transport", "bracketed_paste"),
            "status": "active",
            "created_at": created_at
        }
        with open(queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        ledger_hash = append_learning_ledger(living_home, "STAGE_TRAINING", {
            "proposal_id": proposal_id,
            "candidate_id": candidate_id,
            "exchange_hash": exchange_hash,
            "content_hash": actual_hash,
            "input_transport": target_proposal.get("input_transport")
        })
        _update_proposal_status(living_home, proposal_id, "confirmed", {"confirmed_at": created_at, "ledger_hash": ledger_hash})
        return True, f"[OSIRIS] Proposal {proposal_id} confirmed. Staged candidate into training queue (ID: {candidate_id}, ledger: {ledger_hash[:12]}). (Actual model training remains deferred until batch execution)."

    return False, f"[!] Unknown target: {target}"


def cancel_proposal(living_home: str, proposal_id: str) -> Tuple[bool, str]:
    """Cancels a pending proposal.
    Writes only status update to proposal store (learning_proposals.jsonl); does not write destination stores or ledger.
    """
    proposals_path = get_proposals_path(living_home)
    if not os.path.exists(proposals_path):
        return False, f"[!] Proposal {proposal_id} not found."

    target_proposal = None
    with open(proposals_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("proposal_id") == proposal_id:
                target_proposal = rec

    if not target_proposal:
        return False, f"[!] Proposal {proposal_id} not found."

    if target_proposal.get("status") == "confirmed":
        return False, f"[!] Proposal {proposal_id} is already confirmed and cannot be cancelled. Use /unlearn to tombstone."

    ok = _update_proposal_status(living_home, proposal_id, "cancelled", {"cancelled_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    if ok:
        return True, f"[OSIRIS] Proposal {proposal_id} cancelled. Destination stores and audit ledger were not written."
    return False, f"[!] Failed to cancel proposal {proposal_id}."


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS REPORTING AND WITHDRAWAL (UNLEARN)
# ═══════════════════════════════════════════════════════════════════════════════

def get_learning_status(living_home: str) -> Dict[str, Any]:
    """Gathers status across all distinct governed learning destinations."""
    status = {
        "ledger_total": 0,
        "ledger_unconsented_pastes": 0,
        "pending_proposals": 0,
        "notes": [],
        "candidate_facts": [],
        "training_queue": [],
        "quarantined": 0,
        "tombstoned": 0,
    }

    # 1. Exchanges ledger
    exchanges_file = os.path.join(living_home, "exchanges.jsonl")
    if os.path.exists(exchanges_file):
        try:
            with open(exchanges_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    status["ledger_total"] += 1
                    rec = json.loads(line)
                    transport = rec.get("input_transport") or rec.get("source_type") or "unknown"
                    if transport in ("bracketed_paste", "paste") or rec.get("pasted") is True or rec.get("learnable") is False:
                        status["ledger_unconsented_pastes"] += 1
        except Exception:
            pass

    # 2. Proposals
    proposals_path = get_proposals_path(living_home)
    if os.path.exists(proposals_path):
        try:
            with open(proposals_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("status") == "pending":
                        status["pending_proposals"] += 1
        except Exception:
            pass

    # 3. Notes
    notes_path = os.path.join(living_home, "notes.jsonl")
    if os.path.exists(notes_path):
        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("status") == "tombstoned":
                        status["tombstoned"] += 1
                    else:
                        status["notes"].append(rec)
        except Exception:
            pass

    # 4. Candidate Facts
    facts_path = os.path.join(living_home, "candidate_facts.jsonl")
    if os.path.exists(facts_path):
        try:
            with open(facts_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("status") == "tombstoned":
                        status["tombstoned"] += 1
                    else:
                        status["candidate_facts"].append(rec)
        except Exception:
            pass

    # 5. Training Queue
    queue_path = os.path.join(living_home, "training_queue.jsonl")
    if os.path.exists(queue_path):
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("status") == "tombstoned":
                        status["tombstoned"] += 1
                    else:
                        status["training_queue"].append(rec)
        except Exception:
            pass

    return status


def format_learning_status(st: Dict[str, Any]) -> str:
    """Formats human-readable status across all 5 memory states."""
    out = [
        "╔══════════════════════════════════════════════════════════════════════════════╗",
        "║                     GOVERNED LEARNING DESTINATION STATUS                     ║",
        "╠══════════════════════════════════════════════════════════════════════════════╣",
        "  records every exchange; learns only from eligible material you explicitly approve.",
        f"  Total Exchanges Recorded (L0)    : {st['ledger_total']}",
        f"  Ledger-Only Unapproved Inputs    : {st['ledger_unconsented_pastes']}",
        f"  Pending Proposals (Unconfirmed)  : {st['pending_proposals']}",
        f"  Active Attributable Notes        : {len(st['notes'])}",
        f"  Active Candidate Facts           : {len(st['candidate_facts'])}",
        f"  Active Training Queue Items      : {len(st['training_queue'])}",
        f"  Tombstoned / Withdrawn Items     : {st['tombstoned']}",
        "  Scan Advisory                    : Known-pattern scans quarantine detected risks; no match is not a safety, privacy, or training-suitability guarantee.",
        "╠══════════════════════════════════════════════════════════════════════════════╣",
        "  Separate Memory State Invariants:",
        "    1. Ledger Recording (L0) : Immutable hash-chained audit of every raw interaction.",
        "    2. Retrieval Notes       : Attributable background reference notes (cited by file).",
        "    3. Candidate Facts       : Extracted assertions labeled 'user-provided (unverified)'.",
        "    4. Training Candidacy    : Staged queue items awaiting batch distillation.",
        "    5. Actual Training       : Offline batch weight optimization (/train start).",
        "    - To withdraw any active item: /unlearn <id> --confirm",
        "╚══════════════════════════════════════════════════════════════════════════════╝"
    ]
    return "\n".join(out)


def unlearn(living_home: str, target_id: str, reason: str = "user_request", confirm: bool = False) -> Tuple[bool, str]:
    """Tombstones an authorized item with cryptographic receipt. Requires confirm=True."""
    if not target_id:
        return False, "[!] Usage: /unlearn <target-id> [--confirm]"

    destinations = [
        ("notes", os.path.join(living_home, "notes.jsonl")),
        ("candidate_facts", os.path.join(living_home, "candidate_facts.jsonl")),
        ("training_queue", os.path.join(living_home, "training_queue.jsonl")),
        ("proposals", get_proposals_path(living_home)),
    ]

    target_found = None
    target_dest = None

    for dest_name, path in destinations:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    match = (
                        rec.get("id") == target_id or
                        rec.get("proposal_id") == target_id or
                        rec.get("exchange_hash") == target_id
                    )
                    if match:
                        target_found = rec
                        target_dest = (dest_name, path)
                        break
        except Exception:
            pass
        if target_found:
            break

    if not target_found:
        return False, f"[!] Item '{target_id}' not found in any active learning destination."

    if target_found.get("status") == "tombstoned":
        return False, f"[!] Item '{target_id}' is already tombstoned."

    # Two-step confirmation requirement
    if not confirm:
        card = f"""╔══════════════════════════════════════════════════════════════════════════════╗
║                     UNLEARN CONFIRMATION REQUIRED                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
  Target ID        : {target_id}
  Destination      : {target_dest[0]}
  Current Status   : active -> proposed TOMBSTONE
  Reason           : {reason}

  [!] This will withdraw the item from active retrieval/training and append
      an immutable cryptographic tombstone receipt in learning_ledger.jsonl.

  To execute, rerun with --confirm:
    /unlearn {target_id} --confirm
╚══════════════════════════════════════════════════════════════════════════════╝"""
        return False, card

    # Execute tombstone
    dest_name, dest_path = target_dest
    lines = []
    with open(dest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            match = (
                rec.get("id") == target_id or
                rec.get("proposal_id") == target_id or
                rec.get("exchange_hash") == target_id
            )
            if match:
                rec["status"] = "tombstoned"
                rec["tombstoned_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                rec["tombstone_reason"] = reason
                if dest_name == "proposals":
                    if "payload" in rec:
                        rec["payload"] = {"tombstoned": True, "reason": reason}
                    rec["metadata"] = {"tombstoned": True, "reason": reason}
            lines.append(rec)

    with open(dest_path, "w", encoding="utf-8") as f:
        for rec in lines:
            f.write(json.dumps(rec) + "\n")

    # Also neutralize any matching proposal metadata/payload in proposal store to ensure unlearn privacy
    prop_path = get_proposals_path(living_home)
    if os.path.exists(prop_path) and dest_name != "proposals":
        try:
            prop_lines = []
            prop_modified = False
            with open(prop_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    prec = json.loads(line)
                    match_prop = (
                        prec.get("proposal_id") == target_id or
                        prec.get("exchange_hash") == target_id or
                        prec.get("exchange_hash") == target_found.get("exchange_hash")
                    )
                    if match_prop:
                        prec["status"] = "tombstoned"
                        prec["tombstoned_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                        if "payload" in prec:
                            prec["payload"] = {"tombstoned": True, "reason": reason}
                        prec["metadata"] = {"tombstoned": True, "reason": reason}
                        prop_modified = True
                    prop_lines.append(prec)
            if prop_modified:
                with open(prop_path, "w", encoding="utf-8") as f:
                    for prec in prop_lines:
                        f.write(json.dumps(prec) + "\n")
        except Exception:
            pass

    ledger_hash = append_learning_ledger(living_home, "TOMBSTONE_UNLEARN", {
        "target_id": target_id,
        "destination": dest_name,
        "reason": reason
    })

    return True, f"[OSIRIS] Successfully unlearned/tombstoned item '{target_id}' in {dest_name}. Receipt logged in learning ledger ({ledger_hash[:12]})."
