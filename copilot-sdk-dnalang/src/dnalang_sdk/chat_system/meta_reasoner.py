#!/usr/bin/env python3
"""
META REASONER — Confidence, Strategy Ranking, and Self-Improvement
=================================================================

Evaluates decisions after execution, ranks strategies, and feeds
learning back into the OSIRIS cognitive loop.
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class StrategyRecord:
    strategy: str
    successes: int = 1
    failures: int = 1
    last_outcome: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def score(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total else 0.0


class MetaReasoner:
    """
    Meta-reasoning engine to evaluate OSIRIS choices and improve over time.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = Path(state_dir) if state_dir else Path.home() / ".osiris" / "meta_reasoner"
        self.state_dir.mkdir(exist_ok=True, parents=True)
        self.strategy_records: Dict[str, StrategyRecord] = {}
        self._load_state()

    def evaluate_strategy(
        self,
        intent_label: str,
        strategy: str,
        outcome: Dict[str, Any],
    ) -> None:
        key = f"{intent_label}:{strategy}"
        record = self.strategy_records.get(key)
        if not record:
            record = StrategyRecord(strategy=strategy)
            self.strategy_records[key] = record

        if outcome.get("success", True):
            record.successes += 1
        else:
            record.failures += 1

        record.last_outcome = outcome.get("detail", "")
        record.metadata.update(outcome.get("metadata", {}))
        self._save_state()

    def rank_strategies(self, intent_label: str, strategies: List[str]) -> List[str]:
        scored = []
        for strategy in strategies:
            key = f"{intent_label}:{strategy}"
            record = self.strategy_records.get(key)
            if record:
                scored.append((strategy, record.score()))
            else:
                scored.append((strategy, 0.5))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [strategy for strategy, _ in scored]

    def get_confidence_threshold(self, intent_confidence: float) -> str:
        if intent_confidence >= 0.85:
            return "autonomous"
        if intent_confidence >= 0.6:
            return "assistive"
        return "passive"

    def _save_state(self) -> None:
        state_file = self.state_dir / "strategies.json"
        try:
            with open(state_file, "w") as f:
                json.dump({
                    key: {
                        "strategy": rec.strategy,
                        "successes": rec.successes,
                        "failures": rec.failures,
                        "last_outcome": rec.last_outcome,
                        "metadata": rec.metadata,
                    }
                    for key, rec in self.strategy_records.items()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save strategy records: {e}")

    def _load_state(self) -> None:
        state_file = self.state_dir / "strategies.json"
        if not state_file.exists():
            return
        try:
            with open(state_file) as f:
                state = json.load(f)
                for key, rec in state.items():
                    self.strategy_records[key] = StrategyRecord(
                        strategy=rec.get("strategy", key.split(":")[-1]),
                        successes=rec.get("successes", 1),
                        failures=rec.get("failures", 1),
                        last_outcome=rec.get("last_outcome"),
                        metadata=rec.get("metadata", {}),
                    )
        except Exception as e:
            logger.warning(f"Could not load strategy records: {e}")


# Factory

def create_meta_reasoner(state_dir: Optional[Path] = None) -> MetaReasoner:
    return MetaReasoner(state_dir=state_dir)
