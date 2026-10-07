import json
import pytest
from osiris_cli import gemini_gateway as g

KEY = "AQ.FAKEKEYFAKEKEYFAKEKEYFAKEKEY"
ENV = {"GOOGLE_API_KEY": KEY, "OTHER_SECRET": "hunter2hunter2"}


@pytest.fixture
def parts(tmp_path):
    return g.Ledger(str(tmp_path / "l.jsonl")), g.Budget(str(tmp_path / "b.json"), limit=100000)


def fake(status=200, text="ok", tokens=10):
    sent = {}
    def t(url, headers, body):
        sent.update(url=url, headers=headers, body=body)
        return status, {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
                        "usageMetadata": {"totalTokenCount": tokens}, "modelVersion": "m"}
    return t, sent


def test_redacts_env_values_and_shapes_and_key_never_in_body(parts):
    led, bud = parts
    t, sent = fake()
    prompt = f"my key {KEY} and pw hunter2hunter2 and AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUM1 and postgres://u:pw1234@h/db"
    r = g.generate(prompt, purpose="t", transport=t, ledger=led, budget=bud, env=ENV)
    body = json.dumps(sent["body"])
    assert KEY not in body and "hunter2hunter2" not in body and "AIza" not in body and "pw1234" not in body
    assert r["redactions"]["env:GOOGLE_API_KEY"] == 1 and sent["headers"]["x-goog-api-key"] == KEY


def test_ledger_written_before_and_after_and_chain_verifies(parts):
    led, bud = parts
    t, _ = fake()
    g.generate("hello", purpose="t", transport=t, ledger=led, budget=bud, env=ENV)
    rows = [json.loads(x) for x in open(led.path)]
    assert [r["kind"] for r in rows] == ["GEMINI_CALL_SENT", "GEMINI_CALL_RESULT"]
    assert led.verify() == (True, "ok") and KEY not in open(led.path).read()


def test_ledger_tamper_detected(parts):
    led, bud = parts
    t, _ = fake()
    g.generate("hello", purpose="t", transport=t, ledger=led, budget=bud, env=ENV)
    lines = open(led.path).read().splitlines()
    row = json.loads(lines[0]); row["payload"]["purpose"] = "edited"; lines[0] = json.dumps(row)
    open(led.path, "w").write("\n".join(lines) + "\n")
    assert not led.verify()[0]


def test_budget_blocks_before_sending(parts):
    led, bud = parts
    t, sent = fake()
    with pytest.raises(g.BudgetExceeded):
        g.generate("x", purpose="t", max_output_tokens=500000, transport=t, ledger=led, budget=bud, env=ENV)
    import os
    assert not sent and not os.path.exists(led.path)


def test_budget_accumulates(parts):
    led, bud = parts
    t, _ = fake(tokens=40)
    g.generate("a", purpose="t", max_output_tokens=100, transport=t, ledger=led, budget=bud, env=ENV)
    assert bud.used() == 40


def test_model_allowlist_and_purpose_required(parts):
    led, bud = parts
    t, _ = fake()
    with pytest.raises(g.GatewayError):
        g.generate("a", purpose="t", model="gemini-9", transport=t, ledger=led, budget=bud, env=ENV)
    with pytest.raises(g.GatewayError):
        g.generate("a", purpose=" ", transport=t, ledger=led, budget=bud, env=ENV)


def test_dry_run_sends_nothing_and_writes_nothing(parts):
    led, bud = parts
    t, sent = fake()
    r = g.generate("a " + KEY, purpose="t", dry_run=True, transport=t, ledger=led, budget=bud, env=ENV)
    assert r["dry_run"] and not sent
    import os
    assert not os.path.exists(led.path)


def test_http_error_is_ledgered_and_raised(parts):
    led, bud = parts
    t, _ = fake(status=429)
    with pytest.raises(g.GatewayError):
        g.generate("a", purpose="t", transport=t, ledger=led, budget=bud, env=ENV)
    assert json.loads(open(led.path).read().splitlines()[-1])["payload"]["http"] == 429


def test_only_the_gateway_talks_to_google_apis():
    """Any future model call must go through osiris_cli.gemini_gateway (redaction, budget, ledger).
    gemini_bridge.py predates the gateway; it is listed here so it cannot spread, and is not imported."""
    import os
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hosts = re.compile(r"generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com")
    allowed = {os.path.join("osiris_cli", "gemini_gateway.py"), "gemini_bridge.py",
               os.path.join("tests", "test_gemini_gateway.py")}
    skip = {".git", ".venv", "build", "node_modules"}
    offenders = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in skip]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(d, f), root)
                if rel not in allowed and hosts.search(open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()):
                    offenders.append(rel)
    assert not offenders, f"direct Google API calls outside the gateway: {offenders}"


def test_legacy_bridge_is_not_imported_by_the_package():
    import os
    pkg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "osiris_cli")
    for f in os.listdir(pkg):
        if f.endswith(".py"):
            assert "gemini_bridge" not in open(os.path.join(pkg, f), encoding="utf-8").read(), f
