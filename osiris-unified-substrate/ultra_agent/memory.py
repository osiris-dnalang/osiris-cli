"""Persistent memory for Ultra-Agent learning across sessions.

Stores task results, critique signals, improvement plans, and
performance metrics as append-only JSONL with indexed retrieval.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """
    Single memory record for Ultra-Agent, including reasoning depth and quality.
    """
    """Single memory record."""
    task: str
    solution_hash: str
    quality_score: float
    reasoning_depth: int
    critique: str
    improvement: str
    domain: str
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentMemory:
    """
    Append-only JSONL memory with retrieval, stats, and compute throttling support.
    """
    """Append-only JSONL memory with simple retrieval."""

    def __init__(self, path: str = "artifacts/ultra_agent_memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: List[MemoryEntry] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        self._cache.append(MemoryEntry(**d))
                    except (json.JSONDecodeError, TypeError):
                        continue

    def store(self, entry: MemoryEntry) -> None:
        """Append a memory entry."""
        self._cache.append(entry)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def recent(self, n: int = 10) -> List[MemoryEntry]:
        return self._cache[-n:]

    def by_domain(self, domain: str) -> List[MemoryEntry]:
        return [e for e in self._cache if e.domain == domain]

    def best(self, n: int = 5) -> List[MemoryEntry]:
        return sorted(self._cache, key=lambda e: e.quality_score, reverse=True)[:n]

    def worst(self, n: int = 5) -> List[MemoryEntry]:
        return sorted(self._cache, key=lambda e: e.quality_score)[:n]

    def average_quality(self) -> float:
        if not self._cache:
            return 0.0
        return sum(e.quality_score for e in self._cache) / len(self._cache)

    def improvement_trend(self, window: int = 10) -> float:
        """Return quality improvement over the last N entries vs prior N."""
        if len(self._cache) < window * 2:
            return 0.0
        recent = self._cache[-window:]
        prior = self._cache[-window * 2:-window]
        avg_recent = sum(e.quality_score for e in recent) / len(recent)
        avg_prior = sum(e.quality_score for e in prior) / len(prior)
        return avg_recent - avg_prior

    def stats(self) -> Dict[str, Any]:
        domains = {}
        for e in self._cache:
            domains.setdefault(e.domain, []).append(e.quality_score)
        return {
            "total_entries": len(self._cache),
            "average_quality": self.average_quality(),
            "improvement_trend": self.improvement_trend(),
            "domains": {
                d: {"count": len(scores), "avg": sum(scores) / len(scores)}
                for d, scores in domains.items()
            },
        }

    def __len__(self) -> int:
        return len(self._cache)
