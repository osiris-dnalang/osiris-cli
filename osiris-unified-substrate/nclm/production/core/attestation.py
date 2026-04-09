import hashlib
from pathlib import Path
from typing import Dict, Iterable


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_attestation_manifest(paths: Iterable[str | Path]) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    for path in paths:
        resolved = Path(path)
        manifest[str(resolved)] = sha256_file(resolved)
    return manifest