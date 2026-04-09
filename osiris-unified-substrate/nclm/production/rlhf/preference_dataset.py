import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List


@dataclass
class PreferenceSample:
    prompt: str
    chosen: str
    rejected: str
    metadata: Dict[str, object] | None = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def format_pair(chosen: str, rejected: str, prompt: str = "", metadata: Dict[str, object] | None = None) -> Dict[str, object]:
    return PreferenceSample(prompt=prompt, chosen=chosen, rejected=rejected, metadata=metadata).to_dict()


def load_preference_jsonl(path: str | Path) -> List[PreferenceSample]:
    samples: List[PreferenceSample] = []
    for record in iter_preference_jsonl(path):
        samples.append(record)
    return samples


def iter_preference_jsonl(path: str | Path) -> Iterator[PreferenceSample]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            yield PreferenceSample(
                prompt=payload.get("prompt", ""),
                chosen=payload["chosen"],
                rejected=payload["rejected"],
                metadata=payload.get("metadata"),
            )


def save_preference_jsonl(path: str | Path, samples: Iterable[PreferenceSample]) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
    return file_path