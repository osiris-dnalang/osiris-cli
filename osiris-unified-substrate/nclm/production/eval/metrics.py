from typing import Iterable, Sequence


def accuracy(predictions: Sequence[object], labels: Sequence[object]) -> float:
    if not labels:
        return 0.0
    return sum(pred == label for pred, label in zip(predictions, labels)) / len(labels)


def exact_match(predictions: Sequence[str], labels: Sequence[str]) -> float:
    normalized_preds = [prediction.strip() for prediction in predictions]
    normalized_labels = [label.strip() for label in labels]
    return accuracy(normalized_preds, normalized_labels)


def pass_at_k(results: Iterable[Sequence[bool]], k: int = 1) -> float:
    results = list(results)
    if not results:
        return 0.0
    return sum(any(candidate[:k]) for candidate in results) / len(results)


def mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)