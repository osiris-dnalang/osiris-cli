"""Bounded classification for untrusted runtime artifacts."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ArtifactRejected(ValueError):
    """Raised when an artifact cannot safely enter a runtime workflow."""


@dataclass(frozen=True)
class ArtifactClassification:
    kind: str
    trusted: bool
    executable: bool
    reason: str


def classify_artifact(path: Path, max_bytes: int = 1_000_000) -> ArtifactClassification:
    path = Path(path)
    if not path.is_file():
        raise ArtifactRejected("artifact must be a regular file")
    size = path.stat().st_size
    if size > max_bytes:
        raise ArtifactRejected("artifact exceeds the size limit")
    with path.open("rb") as handle:
        prefix = handle.read(8)
    if prefix.startswith(b"\x7fELF") or prefix.startswith(b"MZ"):
        return ArtifactClassification("native-binary", False, True, "native executable rejected")
    if prefix.startswith(b"PK\x03\x04"):
        if zipfile.is_zipfile(path):
            return ArtifactClassification("archive", False, True, "archive requires explicit review")
        return ArtifactClassification("unknown-binary", False, True, "invalid archive signature")
    suffix = path.suffix.lower()
    if suffix == ".dna":
        return ArtifactClassification("text-dna", True, False, "text artifact; parse before use")
    if suffix in {".py", ".json", ".jsonl", ".md", ".txt"}:
        if suffix in {".json", ".jsonl"}:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ArtifactRejected("invalid JSON artifact") from exc
        return ArtifactClassification("text", True, False, "non-executable content")
    if any(byte < 9 or 13 < byte < 32 for byte in prefix):
        return ArtifactClassification("unknown-binary", False, True, "unknown binary rejected")
    return ArtifactClassification("unknown", False, False, "unrecognized artifact requires review")
