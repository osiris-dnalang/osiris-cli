from collections import Counter
from typing import Dict, Iterable, List


def majority_vote(outputs: Iterable[Dict[str, object]]) -> str:
    texts = [str(output.get("output", "")).strip() for output in outputs if output.get("output")]
    if not texts:
        return ""
    return Counter(texts).most_common(1)[0][0]


def score_outputs(outputs: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    ranked: List[Dict[str, object]] = []
    for output in outputs:
        ranked.append(
            {
                **output,
                "score": float(output.get("score", 0.0)) + float(output.get("confidence", 0.0)),
            }
        )
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def select_best_output(outputs: Iterable[Dict[str, object]]) -> Dict[str, object]:
    ranked = score_outputs(outputs)
    return ranked[0] if ranked else {"output": "", "score": 0.0}