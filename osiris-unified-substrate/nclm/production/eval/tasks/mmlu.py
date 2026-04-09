import re
from typing import Callable, Dict, Iterable


_ANSWER_RE = re.compile(r"\b([A-D])\b")
_CHOICE_LABELS = ["A", "B", "C", "D"]


def _format_prompt(sample: Dict[str, object]) -> str:
    """Format an MMLU sample into a multiple-choice prompt."""
    question = str(sample.get("question", ""))
    choices = sample.get("choices", [])
    if choices:
        for idx, choice in enumerate(choices):
            if idx < len(_CHOICE_LABELS):
                question += f"\n{_CHOICE_LABELS[idx]}. {choice}"
    question += "\nAnswer:"
    return question


def _extract_answer(text: str) -> str:
    """Extract the first A/B/C/D answer from model output."""
    text = text.strip()
    if text and text[0] in "ABCD":
        return text[0]
    match = _ANSWER_RE.search(text)
    return match.group(1) if match else text.strip()[:1].upper()


def _normalize_gold(answer: object) -> str:
    """Convert gold answer (int index or letter) to A/B/C/D."""
    if isinstance(answer, int) and 0 <= answer < 4:
        return _CHOICE_LABELS[answer]
    return str(answer).strip().upper()[:1]


def evaluate(predict_fn: Callable[[str], str], dataset: Iterable[Dict[str, object]]) -> float:
    correct = 0
    total = 0
    for sample in dataset:
        prompt = _format_prompt(sample)
        prediction = predict_fn(prompt)
        predicted = _extract_answer(prediction)
        gold = _normalize_gold(sample.get("answer", ""))
        if predicted == gold:
            correct += 1
        total += 1
    return correct / total if total else 0.0