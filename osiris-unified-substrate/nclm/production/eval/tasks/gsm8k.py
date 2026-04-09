import re
from typing import Callable, Dict, Iterable


_NUMBER_RE = re.compile(r"-?[\d,]+\.?\d*")


def _extract_numeric(text: str) -> str:
    """Extract the final numeric value from model output or gold answer.

    GSM8K gold answers have the form '...#### <number>'.
    Model outputs may contain chain-of-thought followed by a boxed or final number.
    """
    # Try #### marker first (gold format)
    if "####" in text:
        after = text.split("####")[-1].strip()
        match = _NUMBER_RE.search(after)
        if match:
            return match.group().replace(",", "")

    # Try \\boxed{} (common model format)
    boxed = re.search(r"\\boxed\{([^}]+)\}", text)
    if boxed:
        inner = boxed.group(1).strip()
        match = _NUMBER_RE.search(inner)
        if match:
            return match.group().replace(",", "")

    # Fall back to last number in the text
    matches = _NUMBER_RE.findall(text)
    if matches:
        return matches[-1].replace(",", "")
    return text.strip()


def evaluate(predict_fn: Callable[[str], str], dataset: Iterable[Dict[str, object]]) -> float:
    correct = 0
    total = 0
    for sample in dataset:
        question = str(sample.get("question", ""))
        prompt = f"{question}\nLet's solve this step by step.\n"
        prediction = predict_fn(prompt)
        predicted = _extract_numeric(prediction)
        gold = _extract_numeric(str(sample.get("answer", "")))
        if predicted == gold:
            correct += 1
        total += 1
    return correct / total if total else 0.0