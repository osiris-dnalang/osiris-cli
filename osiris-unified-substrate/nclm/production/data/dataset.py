import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List


def iter_jsonl(path: str | Path) -> Iterator[Dict[str, object]]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_jsonl(path: str | Path, limit: int | None = None) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for index, record in enumerate(iter_jsonl(path)):
        if limit is not None and index >= limit:
            break
        records.append(record)
    return records


def take_records(records: Iterable[Dict[str, object]], count: int) -> List[Dict[str, object]]:
    limited: List[Dict[str, object]] = []
    for record in records:
        limited.append(record)
        if len(limited) >= count:
            break
    return limited