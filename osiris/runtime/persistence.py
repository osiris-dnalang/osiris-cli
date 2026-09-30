"""Local SQLite sessions, artifacts, receipts, checkpoints, and evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional


class SessionStore:
    def __init__(self, path: str = ":memory:"):
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                workspace_root TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                sha256 TEXT PRIMARY KEY,
                content BLOB NOT NULL,
                content_type TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                commit_sha TEXT,
                snapshot_ref TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self.connection.commit()

    def start_session(self, session_id: str, workspace_root: str) -> None:
        now = time.time()
        self.connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            (session_id, workspace_root, "active", now, now),
        )
        self.connection.commit()

    def put_artifact(self, content: bytes, content_type: str = "application/octet-stream") -> str:
        digest = hashlib.sha256(content).hexdigest()
        self.connection.execute(
            "INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?, ?)",
            (digest, content, content_type, time.time()),
        )
        self.connection.commit()
        return digest

    def get_artifact(self, digest: str) -> bytes:
        row = self.connection.execute(
            "SELECT content FROM artifacts WHERE sha256 = ?", (digest,)
        ).fetchone()
        if row is None:
            raise KeyError("artifact not found")
        content = bytes(row[0])
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("artifact integrity check failed")
        return content

    def record(self, receipt_id: str, session_id: str, kind: str, payload: Dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO receipts VALUES (?, ?, ?, ?, ?)",
            (receipt_id, session_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )
        self.connection.commit()

    def checkpoint(
        self, checkpoint_id: str, session_id: str, commit_sha: Optional[str], snapshot_ref: str
    ) -> None:
        self.connection.execute(
            "INSERT INTO checkpoints VALUES (?, ?, ?, ?, ?)",
            (checkpoint_id, session_id, commit_sha, snapshot_ref, time.time()),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
