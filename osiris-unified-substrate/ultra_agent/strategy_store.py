"""Strategy embeddings — embed, store, and retrieve reasoning strategies.

Uses numpy cosine similarity over TF-IDF-like bag-of-words vectors.
When ``sentence-transformers`` is available, upgrades to dense embeddings.
Falls back gracefully so the system works without GPU dependencies.

This is the "meta-reasoning learning" component: the system learns
HOW to think, not just what to output.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class StrategyStore:
    """Persistent store for strategy embeddings with retrieval.

    Stores strategies as structured records with vector representations.
    Retrieves top-k most relevant strategies for a new task.
    """

    def __init__(
        self,
        path: str = "artifacts/strategy_store.jsonl",
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []
        self._vectors: List[np.ndarray] = []
        self._vocab: Dict[str, int] = {}
        self._dense_encoder: Optional[Any] = None
        self._use_dense = False
        self._load()
        self._try_dense_encoder()

    def _try_dense_encoder(self) -> None:
        """Try to load sentence-transformers for dense embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            self._dense_encoder = SentenceTransformer(
                "all-MiniLM-L6-v2", device="cpu"
            )
            self._use_dense = True
            # Re-embed existing entries with dense encoder
            if self._entries:
                texts = [e["strategy_text"] for e in self._entries]
                self._vectors = list(self._dense_encoder.encode(texts))
        except ImportError:
            self._use_dense = False

    def _load(self) -> None:
        """Load existing strategies from disk."""
        if not self._path.exists():
            return
        for line in self._path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                self._entries.append(entry)
                self._vectors.append(
                    self._embed(entry["strategy_text"])
                )
            except (json.JSONDecodeError, KeyError):
                continue

    def store(
        self,
        strategy_text: str,
        task: str,
        domain: str,
        quality_score: float,
        reusable_patterns: Optional[List[str]] = None,
    ) -> None:
        """Store a new strategy with its embedding."""
        entry = {
            "strategy_text": strategy_text,
            "task": task[:200],
            "domain": domain,
            "quality_score": round(quality_score, 4),
            "reusable_patterns": reusable_patterns or [],
        }
        self._entries.append(entry)
        self._vectors.append(self._embed(strategy_text))

        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def retrieve(
        self, task: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve top-k most relevant strategies for a task.

        Returns entries sorted by cosine similarity, each augmented
        with a ``similarity`` field.
        """
        if not self._entries:
            return []

        query_vec = self._embed(task)
        similarities = []

        for i, vec in enumerate(self._vectors):
            sim = self._cosine(query_vec, vec)
            similarities.append((sim, i))

        similarities.sort(reverse=True)
        results = []
        for sim, idx in similarities[:top_k]:
            entry = dict(self._entries[idx])
            entry["similarity"] = round(float(sim), 4)
            results.append(entry)

        return results

    def inject_prompt(self, task: str, top_k: int = 3) -> str:
        """Build an augmented prompt with retrieved strategies.

        Prepends relevant strategies to the task description
        for strategy-augmented reasoning.
        """
        strategies = self.retrieve(task, top_k=top_k)
        if not strategies:
            return task

        parts = ["Use the following strategies:"]
        for i, s in enumerate(strategies, 1):
            parts.append(
                f"  {i}. {s['strategy_text']} "
                f"(domain={s['domain']}, quality={s['quality_score']:.2f})"
            )
            if s.get("reusable_patterns"):
                parts.append(
                    f"     Patterns: {', '.join(s['reusable_patterns'])}"
                )
        parts.append(f"\nTask: {task}")
        return "\n".join(parts)

    def stats(self) -> Dict[str, Any]:
        """Return store statistics."""
        if not self._entries:
            return {"total": 0, "encoder": "none"}

        domains = Counter(e["domain"] for e in self._entries)
        qualities = [e["quality_score"] for e in self._entries]

        return {
            "total": len(self._entries),
            "encoder": "dense" if self._use_dense else "tfidf",
            "domains": dict(domains),
            "avg_quality": round(sum(qualities) / len(qualities), 4),
        }

    # ---- embedding methods ----

    def _embed(self, text: str) -> np.ndarray:
        """Produce a vector for text."""
        if self._use_dense and self._dense_encoder is not None:
            return self._dense_encoder.encode(text)
        return self._tfidf_embed(text)

    def _tfidf_embed(self, text: str) -> np.ndarray:
        """Simple TF-IDF-like embedding using word frequency."""
        tokens = self._tokenize(text)
        # Build/extend vocab
        for tok in tokens:
            if tok not in self._vocab:
                self._vocab[tok] = len(self._vocab)

        vec = np.zeros(max(len(self._vocab), 1), dtype=np.float32)
        counts = Counter(tokens)
        for tok, count in counts.items():
            if tok in self._vocab:
                # TF = log(1 + count)
                vec[self._vocab[tok]] = math.log1p(count)

        # Pad existing vectors to match new vocab size
        self._pad_vectors()
        return vec

    def _pad_vectors(self) -> None:
        """Ensure all stored vectors have the same dimensionality."""
        if not self._vectors:
            return
        max_dim = len(self._vocab)
        for i, v in enumerate(self._vectors):
            if len(v) < max_dim:
                padded = np.zeros(max_dim, dtype=np.float32)
                padded[: len(v)] = v
                self._vectors[i] = padded

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple word tokenization."""
        return re.findall(r"[a-z]+", text.lower())

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two vectors."""
        # Handle different lengths
        min_len = min(len(a), len(b))
        a = a[:min_len]
        b = b[:min_len]
        dot = float(np.dot(a, b))
        norm = float(np.linalg.norm(a) * np.linalg.norm(b))
        if norm < 1e-10:
            return 0.0
        return dot / norm
