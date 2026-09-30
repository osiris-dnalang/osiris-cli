"""Authoritative local evidence persistence for PCRB-style records.

This adapter is deliberately local-only. It does not submit jobs, contact
providers, or fall back to filesystem writes when persistence fails.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


SCHEMA_VERSION = "evidence-1"


class EvidenceStoreError(RuntimeError):
    """Raised when an evidence operation cannot be completed atomically."""


@dataclass(frozen=True)
class EvidenceCapsule:
    run_id: str
    task_id: str
    plan_hash: str
    circuit_hash: str
    backend: str
    execution_mode: str
    status: str = "proposed"
    capsule_id: str = field(default_factory=lambda: "capsule_" + uuid.uuid4().hex)
    event_id: str = field(default_factory=lambda: "event_" + uuid.uuid4().hex)
    approval_id: Optional[str] = None
    classification: str = "internal"
    payload: Mapping[str, Any] = field(default_factory=dict)
    counts: Mapping[str, int] = field(default_factory=dict)
    job_id: Optional[str] = None
    shots: Optional[int] = None
    fidelity: Optional[float] = None
    gamma: Optional[float] = None
    lambda_value: Optional[float] = None
    phi: Optional[float] = None
    xi: Optional[float] = None

    def validate(self) -> None:
        for name, value in (
            ("run_id", self.run_id),
            ("task_id", self.task_id),
            ("plan_hash", self.plan_hash),
            ("circuit_hash", self.circuit_hash),
            ("backend", self.backend),
            ("execution_mode", self.execution_mode),
        ):
            if not isinstance(value, str) or not value or len(value) > 512:
                raise ValueError("{} must be a bounded non-empty string".format(name))
        for name, value in (("plan_hash", self.plan_hash), ("circuit_hash", self.circuit_hash)):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError("{} must be a lowercase SHA-256 digest".format(name))
        if self.shots is not None and self.shots < 0:
            raise ValueError("shots cannot be negative")
        if len(json.dumps(self.payload, default=str)) > 32 * 1024:
            raise ValueError("capsule payload exceeds 32 KiB")


class EvidenceStore:
    """SQLite-backed local system of record for evidence and outbox state."""

    def __init__(self, path: str = ":memory:"):
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at_utc REAL NOT NULL,
                checksum TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_capsules (
                capsule_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                schema_version TEXT NOT NULL,
                created_at_utc REAL NOT NULL,
                status TEXT NOT NULL,
                plan_hash TEXT NOT NULL,
                circuit_hash TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                backend TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                approval_id TEXT,
                classification TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS capsule_artifacts (
                capsule_id TEXT NOT NULL,
                artifact_uri TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                content_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                PRIMARY KEY (capsule_id, artifact_uri),
                FOREIGN KEY (capsule_id) REFERENCES evidence_capsules(capsule_id)
            );
            CREATE TABLE IF NOT EXISTS hardware_results (
                capsule_id TEXT PRIMARY KEY,
                job_id TEXT,
                backend TEXT NOT NULL,
                shots INTEGER,
                counts_json TEXT NOT NULL,
                raw_result_ref TEXT,
                fidelity REAL,
                gamma REAL,
                lambda_value REAL,
                phi_value REAL,
                xi_value REAL,
                FOREIGN KEY (capsule_id) REFERENCES evidence_capsules(capsule_id)
            );
            CREATE TABLE IF NOT EXISTS provenance_events (
                event_id TEXT PRIMARY KEY,
                capsule_id TEXT NOT NULL,
                causation_id TEXT,
                event_type TEXT NOT NULL,
                producer TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at_utc REAL NOT NULL,
                FOREIGN KEY (capsule_id) REFERENCES evidence_capsules(capsule_id)
            );
            CREATE TABLE IF NOT EXISTS outbox (
                outbox_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                payload_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at_utc REAL NOT NULL,
                updated_at_utc REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_capsules_run ON evidence_capsules(run_id);
            CREATE INDEX IF NOT EXISTS idx_capsules_task ON evidence_capsules(task_id);
            CREATE INDEX IF NOT EXISTS idx_events_type ON provenance_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_capsules_backend ON evidence_capsules(backend);
            CREATE INDEX IF NOT EXISTS idx_capsules_created ON evidence_capsules(created_at_utc);
            """
        )
        checksum = hashlib.sha256(SCHEMA_VERSION.encode("ascii")).hexdigest()
        self.connection.execute(
            "INSERT OR IGNORE INTO schema_migrations VALUES (?, ?, ?)",
            (SCHEMA_VERSION, time.time(), checksum),
        )
        self.connection.commit()

    def insert_capsule(self, capsule: EvidenceCapsule) -> str:
        capsule.validate()
        payload_json = json.dumps(capsule.payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO evidence_capsules (
                        capsule_id, run_id, task_id, event_id, schema_version,
                        created_at_utc, status, plan_hash, circuit_hash, payload_hash,
                        backend, execution_mode, approval_id, classification, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        capsule.capsule_id, capsule.run_id, capsule.task_id,
                        capsule.event_id, SCHEMA_VERSION, time.time(), capsule.status,
                        capsule.plan_hash, capsule.circuit_hash, payload_hash,
                        capsule.backend, capsule.execution_mode, capsule.approval_id,
                        capsule.classification, payload_json,
                    ),
                )
                self.connection.execute(
                    """
                    INSERT INTO hardware_results (
                        capsule_id, job_id, backend, shots, counts_json, raw_result_ref,
                        fidelity, gamma, lambda_value, phi_value, xi_value
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                    """,
                    (
                        capsule.capsule_id, capsule.job_id, capsule.backend, capsule.shots,
                        json.dumps(capsule.counts, sort_keys=True), capsule.fidelity,
                        capsule.gamma, capsule.lambda_value, capsule.phi, capsule.xi,
                    ),
                )
                self.connection.execute(
                    """
                    INSERT INTO provenance_events (
                        event_id, capsule_id, causation_id, event_type, producer,
                        payload_json, payload_hash, created_at_utc
                    ) VALUES (?, ?, NULL, 'evidence.capsule.recorded', 'osiris', ?, ?, ?)
                    """,
                    (capsule.event_id, capsule.capsule_id, payload_json, payload_hash, time.time()),
                )
        except sqlite3.IntegrityError as exc:
            raise EvidenceStoreError("capsule already exists or violates schema constraints") from exc
        except sqlite3.DatabaseError as exc:
            raise EvidenceStoreError("evidence transaction failed") from exc
        return capsule.capsule_id

    def get_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            "SELECT capsule_id, run_id, task_id, event_id, status, backend, execution_mode, payload_hash "
            "FROM evidence_capsules WHERE capsule_id = ?",
            (capsule_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(zip(
            ("capsule_id", "run_id", "task_id", "event_id", "status", "backend",
             "execution_mode", "payload_hash"),
            row,
        ))

    def register_artifact(
        self,
        capsule_id: str,
        artifact_uri: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Register immutable artifact bytes after calculating their digest."""
        if not artifact_uri or len(artifact_uri) > 512:
            raise ValueError("artifact_uri must be bounded and non-empty")
        if not content_type or len(content_type) > 128:
            raise ValueError("content_type must be bounded and non-empty")
        if self.get_capsule(capsule_id) is None:
            raise EvidenceStoreError("capsule does not exist")
        digest = hashlib.sha256(content).hexdigest()
        try:
            with self.connection:
                existing = self.connection.execute(
                    "SELECT sha256, byte_size FROM capsule_artifacts "
                    "WHERE capsule_id = ? AND artifact_uri = ?",
                    (capsule_id, artifact_uri),
                ).fetchone()
                if existing is not None:
                    if existing != (digest, len(content)):
                        raise EvidenceStoreError("artifact identity collision")
                    return digest
                self.connection.execute(
                    """
                    INSERT INTO capsule_artifacts (
                        capsule_id, artifact_uri, sha256, content_type, byte_size
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (capsule_id, artifact_uri, digest, content_type, len(content)),
                )
        except sqlite3.IntegrityError as exc:
            raise EvidenceStoreError("artifact registration violated schema constraints") from exc
        except sqlite3.DatabaseError as exc:
            raise EvidenceStoreError("artifact registration failed") from exc
        return digest

    def summary(self, run_id: str, limit: int = 100) -> list:
        """Return bounded metadata only; payloads are never loaded."""
        if not run_id or not 1 <= limit <= 1_000:
            raise ValueError("run_id and bounded limit are required")
        rows = self.connection.execute(
            """
            SELECT capsule_id, task_id, status, backend, execution_mode,
                   created_at_utc, payload_hash
            FROM evidence_capsules
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()
        keys = (
            "capsule_id", "task_id", "status", "backend",
            "execution_mode", "created_at_utc", "payload_hash",
        )
        return [dict(zip(keys, row)) for row in rows]

    def add_outbox(self, operation_type: str, idempotency_key: str, payload_ref: str) -> bool:
        try:
            with self.connection:
                cursor = self.connection.execute(
                    """
                    INSERT OR IGNORE INTO outbox (
                        outbox_id, operation_type, idempotency_key, payload_ref,
                        status, attempts, created_at_utc, updated_at_utc
                    ) VALUES (?, ?, ?, ?, 'pending', 0, ?, ?)
                    """,
                    ("outbox_" + uuid.uuid4().hex, operation_type, idempotency_key,
                     payload_ref, time.time(), time.time()),
                )
        except sqlite3.DatabaseError as exc:
            raise EvidenceStoreError("outbox transaction failed") from exc
        return cursor.rowcount == 1

    def close(self) -> None:
        self.connection.close()
