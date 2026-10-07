"""The gateway is the only path to Google's model APIs: it redacts, budgets and ledgers
every request, and gemini_bridge (Synthesizer, /lab discovery, vision) goes through it."""
import json
import os
import re

import pytest

from osiris_cli import gemini_gateway as g

DEV_KEY = "AIzaFAKEFAKEFAKEFAKEFAKEFAKEFAKE12345"
VTX_KEY = "AQ.FAKEKEYFAKEKEYFAKEKEYFAKEKEY"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OSIRIS_GEMINI_BACKEND", "GEMINI_MODEL", "GEMINI_VERTEX_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(g, "ENV_PATH", str(tmp_path / "no.env"))
    monkeypatch.setattr(g, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(g, "BUDGET_PATH", str(tmp_path / "budget.json"))
    monkeypatch.setattr(g, "load_env", lambda path=None: {})


def fake(status=200, text="ok", tokens=10):
    sent = {}

    def t(url, headers, body, timeout):
        sent.update(url=url, headers=headers, body=body)
        return status, {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
                        "usageMetadata": {"totalTokenCount": tokens}, "modelVersion": "m"}
    return t, sent


def test_backend_choice_follows_the_key_type(monkeypatch):
    assert g.choose_backend() is None
    monkeypatch.setenv("GOOGLE_API_KEY", VTX_KEY)
    assert g.choose_backend() == "vertex"
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    assert g.choose_backend() == "developer" and g.backend_key("developer", {}) == DEV_KEY
    monkeypatch.setenv("OSIRIS_GEMINI_BACKEND", "vertex")
    assert g.choose_backend() == "vertex" and g.backend_key("vertex", {}) == VTX_KEY


def test_agent_platform_key_in_gemini_api_key_goes_to_vertex(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", VTX_KEY)            # AQ-type: the Developer API answers 401
    assert g.choose_backend() == "vertex"
    t, sent = fake()
    g.generate("hi", purpose="t", transport=t)
    assert "aiplatform" in sent["url"] and sent["headers"]["x-goog-api-key"] == VTX_KEY


def test_redacts_keys_and_secret_shapes_and_key_only_in_header(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    t, sent = fake()
    prompt = f"key {DEV_KEY} and AKIAABCDEFGHIJKLMNOP and postgres://u:pw1234@h/db"
    r = g.generate(prompt, purpose="t", system=f"sys {VTX_KEY}", transport=t)
    body = json.dumps(sent["body"])
    assert DEV_KEY not in body and VTX_KEY not in body and "AKIA" not in body and "pw1234" not in body
    assert sent["headers"]["x-goog-api-key"] == DEV_KEY and "generativelanguage" in sent["url"]
    assert r["redactions"]


def test_ledger_rows_before_and_after_and_tamper_is_detected(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", VTX_KEY)
    t, _ = fake()
    g.generate("hello", purpose="t", transport=t)
    led = g.Ledger()
    rows = [json.loads(x) for x in open(led.path)]
    assert [r["kind"] for r in rows] == ["GEMINI_CALL_SENT", "GEMINI_CALL_RESULT"]
    assert led.verify() == (True, "ok") and VTX_KEY not in open(led.path).read()
    rows[0]["payload"]["purpose"] = "edited"
    open(led.path, "w").write("\n".join(json.dumps(r) for r in rows) + "\n")
    assert not led.verify()[0]


def test_budget_refuses_before_sending(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    t, sent = fake()
    with pytest.raises(g.BudgetExceeded):
        g.generate("x", purpose="t", max_output_tokens=10_000_000, transport=t)
    assert not sent and not os.path.exists(g.LEDGER_PATH)


def test_no_key_and_bad_model_are_refused(monkeypatch):
    with pytest.raises(g.GatewayError, match="no Gemini key"):
        g.generate("x", purpose="t", transport=fake()[0])
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    with pytest.raises(g.GatewayError):
        g.generate("x", purpose="t", model="gpt-4", transport=fake()[0])
    with pytest.raises(g.GatewayError):
        g.generate("x", purpose=" ", transport=fake()[0])


def test_http_error_is_ledgered_and_raised(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    with pytest.raises(g.GatewayError, match="HTTP 429"):
        g.generate("a", purpose="t", transport=fake(status=429)[0])
    assert json.loads(open(g.LEDGER_PATH).read().splitlines()[-1])["payload"]["http"] == 429


def test_bridge_goes_through_the_gateway(monkeypatch):
    import gemini_bridge
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    t, sent = fake(text="synthesized")
    monkeypatch.setattr(g, "_post", t)
    monkeypatch.setattr(g.send, "__kwdefaults__", dict(g.send.__kwdefaults__, transport=t))
    assert gemini_bridge.is_configured()
    out = gemini_bridge.query("system", f"write code; my key is {DEV_KEY}")
    assert out == "synthesized" and DEV_KEY not in json.dumps(sent["body"])
    rows = [json.loads(x) for x in open(g.LEDGER_PATH)]
    assert rows[0]["payload"]["purpose"] == "gemini_bridge.query"


def test_bridge_failure_is_gemini_unavailable_for_the_ollama_fallback(monkeypatch):
    import gemini_bridge
    with pytest.raises(gemini_bridge.GeminiUnavailable):
        gemini_bridge.query("s", "p")                      # no key at all
    monkeypatch.setenv("GEMINI_API_KEY", DEV_KEY)
    t, _ = fake(status=403)
    monkeypatch.setattr(g.send, "__kwdefaults__", dict(g.send.__kwdefaults__, transport=t))
    with pytest.raises(gemini_bridge.GeminiUnavailable, match="HTTP 403"):
        gemini_bridge.query("s", "p")


def test_only_the_gateway_talks_to_google_model_apis():
    hosts = re.compile(r"generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com")
    allowed = {os.path.join("osiris_cli", "gemini_gateway.py"), os.path.join("tests", "test_gemini_gateway.py")}
    skip = {".git", ".venv", "build", "node_modules", "results"}
    offenders = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in skip]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(d, f), ROOT)
                src = open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()
                if rel not in allowed and hosts.search(src) and "urlopen" in src:
                    offenders.append(rel)
    assert not offenders, f"direct calls to Google model APIs outside the gateway: {offenders}"
