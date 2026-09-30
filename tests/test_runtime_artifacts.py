from pathlib import Path

import pytest

from osiris.runtime.artifacts import ArtifactRejected, classify_artifact


def test_classifies_text_dna_as_untrusted_input(tmp_path):
    path = tmp_path / "organism.dna"
    path.write_text("organism demo", encoding="utf-8")

    result = classify_artifact(path)

    assert result.kind == "text-dna"
    assert result.trusted
    assert not result.executable


def test_rejects_native_binary(tmp_path):
    path = tmp_path / "program"
    path.write_bytes(b"\x7fELF" + b"\0" * 32)

    result = classify_artifact(path)

    assert result.kind == "native-binary"
    assert not result.trusted
    assert result.executable


def test_rejects_oversized_artifact(tmp_path):
    path = tmp_path / "large.txt"
    path.write_bytes(b"x" * 32)

    with pytest.raises(ArtifactRejected):
        classify_artifact(path, max_bytes=16)


def test_rejects_invalid_json(tmp_path):
    path = tmp_path / "input.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ArtifactRejected, match="JSON"):
        classify_artifact(path)
