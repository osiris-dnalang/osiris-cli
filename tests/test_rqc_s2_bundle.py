"""The committed S2 amendment-5 bundle manifest matches the files in this tree, the amendment cites the
implementation snapshot, the manifest stays a draft, and the hardware path refuses it."""
import importlib.util
import json
import os
import socket

import pytest

from rqc.control import verify_bundle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DRIVER = os.path.join(ROOT, "docs", "rqc", "S2", "s2_run_batched.py")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted during an offline test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def _driver():
    spec = importlib.util.spec_from_file_location("s2_run_batched", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_manifest_matches_this_tree():
    d = _driver()
    mp = os.path.join(ROOT, d.MANIFEST)
    assert verify_bundle(ROOT, mp, d.CODE_FILES, d.DOCUMENT_FILES) == []
    m = json.load(open(mp))
    import hashlib
    for p, h in m["supporting"].items():
        assert hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest() == h, p


def test_manifest_is_a_draft_and_hardware_refuses_it(tmp_path):
    d = _driver()
    m = json.load(open(os.path.join(ROOT, d.MANIFEST)))
    assert m["status"] == "draft" and m["amendment_doi"] is None
    assert "NOT APPROVED" in open(os.path.join(ROOT, m["amendment_path"]), encoding="utf-8").read()
    with pytest.raises(SystemExit, match="not 'deposited'"):
        d.main(["--prereg-doi", d.PREREG_DOI, "--amendment-doi", "10.5281/zenodo.1", "--out", str(tmp_path)])


def test_no_artifact_embeds_its_own_hash():
    d = _driver()
    m = json.load(open(os.path.join(ROOT, d.MANIFEST)))
    commit = m["implementation"]["commit"]
    for p in d.CODE_FILES:                                   # the snapshot does not cite itself
        assert commit not in open(os.path.join(ROOT, p), encoding="utf-8").read(), p
    amend = open(os.path.join(ROOT, m["amendment_path"]), encoding="utf-8").read()
    assert m["documents"][m["amendment_path"]] not in amend  # the amendment does not carry its own hash
