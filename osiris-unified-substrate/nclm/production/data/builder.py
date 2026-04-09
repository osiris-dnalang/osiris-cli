from typing import Dict, Iterable, Iterator, List

from ..rlhf.preference_dataset import PreferenceSample


def build_sft_records(conversations: Iterable[Dict[str, object]], prompt_key: str = "prompt", response_key: str = "response") -> Iterator[Dict[str, str]]:
    for conversation in conversations:
        yield {
            "text": f"User: {conversation[prompt_key]}\nAssistant: {conversation[response_key]}",
        }


def build_preference_records(comparisons: Iterable[Dict[str, object]]) -> List[PreferenceSample]:
    samples: List[PreferenceSample] = []
    for comparison in comparisons:
        samples.append(
            PreferenceSample(
                prompt=str(comparison.get("prompt", "")),
                chosen=str(comparison["chosen"]),
                rejected=str(comparison["rejected"]),
                metadata=dict(comparison.get("metadata", {})),
            )
        )
    return samples