"""Preference pipeline — converts distillation records into RLHF preference pairs.

Bridges the gap between structural learning (distillation) and
parametric learning (PPO weight updates).  Only records where
the improvement exceeds a configurable threshold are emitted,
preventing noise training.

Output format matches ``nclm.production.rlhf.preference_dataset.PreferenceSample``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


def distillation_to_preferences(
    records_path: str = "artifacts/distillation_records.jsonl",
    output_path: str = "artifacts/preference_pairs.jsonl",
    reward_threshold: float = 0.02,
) -> Dict[str, Any]:
    """Convert distillation JSONL into RLHF preference pairs.

    Parameters
    ----------
    records_path : str
        Path to distillation_records.jsonl (from DistillationEngine).
    output_path : str
        Path to write preference_pairs.jsonl.
    reward_threshold : float
        Minimum ``improvement_score`` required.  Records below this
        threshold are discarded (prevents noise training).

    Returns
    -------
    dict
        Summary statistics.
    """
    in_path = Path(records_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    accepted = 0
    rejected = 0

    with out_path.open("w", encoding="utf-8") as fh:
        for record in _iter_records(in_path):
            total += 1
            reward = record.get("improvement_score", 0)

            if reward < reward_threshold:
                rejected += 1
                continue

            pair = {
                "prompt": record["task"],
                "chosen": record["improved_solution"],
                "rejected": record["initial_solution"],
                "metadata": {
                    "reward": round(reward, 4),
                    "strategy": record.get("strategy", ""),
                    "failure_modes": record.get("failure_modes", []),
                    "teaching_points": record.get("teaching_points", []),
                    "mode": record.get("mode", "simulation"),
                    "iteration": record.get("iteration", 0),
                },
            }
            fh.write(json.dumps(pair, ensure_ascii=False) + "\n")
            accepted += 1

    return {
        "total_records": total,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_rate": round(accepted / total, 3) if total else 0.0,
        "reward_threshold": reward_threshold,
        "output_path": str(out_path),
        "ready_for_ppo": accepted > 0,
    }


def load_preference_pairs(
    path: str = "artifacts/preference_pairs.jsonl",
) -> List[Dict[str, Any]]:
    """Load preference pairs for PPO training."""
    pairs = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            pairs.append(json.loads(line))
    return pairs


def _iter_records(path: Path) -> Iterator[Dict[str, Any]]:
    """Stream distillation records."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
