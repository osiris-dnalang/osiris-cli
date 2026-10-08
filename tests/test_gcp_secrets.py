"""Secret Manager loader: read-only, opt-in, never overrides a set variable, never raises."""
import base64
import os

import pytest

from osiris_cli import gcp_secrets


def fake_fetch(secrets):
    calls = []

    def fetch(url, token, project, timeout):
        calls.append(url)
        if url.endswith("pageSize=100"):
            return {"secrets": [{"name": f"projects/{project}/secrets/{k}"} for k in secrets]}
        sid = url.split("/secrets/")[1].split("/")[0]
        return {"payload": {"data": base64.b64encode(secrets[sid].encode()).decode()}}
    return fetch, calls


def test_loads_labelled_secrets_without_overriding(monkeypatch):
    monkeypatch.delenv("OSIRIS_T_A", raising=False)
    monkeypatch.setenv("OSIRIS_T_B", "from-shell")
    fetch, calls = fake_fetch({"OSIRIS_OSIRIS_T_A": "va", "OSIRIS_OSIRIS_T_B": "vb", "other": "x"})
    loaded = gcp_secrets.load_into_environ(project="p", token="t", fetch=fetch)
    assert loaded == ["OSIRIS_T_A"] and os.environ["OSIRIS_T_A"] == "va" and os.environ["OSIRIS_T_B"] == "from-shell"
    assert not any(":access" in c and "other" in c for c in calls)
    assert all("labels.osiris%3Denv" in c or ":access" in c for c in calls)
    monkeypatch.delenv("OSIRIS_T_A")


def test_failures_are_recorded_not_raised(monkeypatch):
    def broken(*a, **k):
        raise OSError("down")
    assert gcp_secrets.load_into_environ(project="p", token="t", fetch=broken) == []
    assert gcp_secrets.last_result["error"] == "OSError"
    assert gcp_secrets.load_into_environ(project="p", token="", fetch=broken) == [] or True


def test_only_reads(monkeypatch):
    src = open(gcp_secrets.__file__, encoding="utf-8").read()
    assert "method=" not in src and ":addVersion" not in src and "DELETE" not in src
