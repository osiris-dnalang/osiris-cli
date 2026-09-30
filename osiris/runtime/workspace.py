"""Explicit-root workspace and bounded repository tools."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


class WorkspaceError(ValueError):
    """Raised when a workspace request violates the local boundary."""


class Workspace:
    def __init__(self, root: Path, require_git: bool = True):
        candidate = Path(root).expanduser()
        if not candidate.is_dir():
            raise WorkspaceError("workspace root must be an existing directory")
        self.root = candidate.resolve(strict=True)
        if require_git and not (self.root / ".git").exists():
            raise WorkspaceError("workspace root must be a Git repository")

    def resolve_relative(self, relative_path: str, must_exist: bool = False) -> Path:
        if not relative_path or "\x00" in relative_path:
            raise WorkspaceError("path must be non-empty and contain no null bytes")
        requested = Path(relative_path)
        if requested.is_absolute():
            raise WorkspaceError("absolute paths are not allowed")
        if ".." in requested.parts:
            raise WorkspaceError("parent traversal is not allowed")
        resolved = (self.root / requested).resolve(strict=must_exist)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError("path escapes the workspace") from exc
        return resolved

    def read_bytes(self, relative_path: str, max_bytes: int = 100_000) -> bytes:
        path = self.resolve_relative(relative_path, must_exist=True)
        if not path.is_file():
            raise WorkspaceError("workspace path is not a regular file")
        if path.stat().st_size > max_bytes:
            raise WorkspaceError("file exceeds the read limit")
        return path.read_bytes()

    def write_bytes(self, relative_path: str, content: bytes, max_bytes: int = 100_000) -> str:
        if len(content) > max_bytes:
            raise WorkspaceError("content exceeds the write limit")
        path = self.resolve_relative(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".osiris-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return hashlib.sha256(content).hexdigest()

    def inventory(self, max_files: int = 1_000) -> List[str]:
        results: List[str] = []
        excluded = {".git", ".venv", "venv", "__pycache__", "node_modules"}
        for path in self.root.rglob("*"):
            if len(results) >= max_files:
                raise WorkspaceError("inventory exceeds the file limit")
            if path.is_dir() and path.name in excluded:
                continue
            if path.is_file() and not any(part in excluded for part in path.relative_to(self.root).parts):
                results.append(path.relative_to(self.root).as_posix())
        return sorted(results)

    def search(self, pattern: str, max_results: int = 100) -> List[Tuple[str, int, str]]:
        if not pattern or len(pattern) > 512:
            raise WorkspaceError("search pattern is empty or too large")
        expression = re.compile(pattern)
        matches: List[Tuple[str, int, str]] = []
        for relative in self.inventory():
            path = self.resolve_relative(relative, must_exist=True)
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                if expression.search(line):
                    matches.append((relative, line_number, line[:1_000]))
                    if len(matches) >= max_results:
                        return matches
        return matches
