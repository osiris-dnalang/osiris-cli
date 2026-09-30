"""OSIRIS's read-only checks: routing, the ledger check, and the secrets fence."""
import json

from osiris_cli.living import Osiris
from osiris_cli.probes import Probes, safe_path, verify_chain


def test_routing_picks_checks_from_the_message():
    p = Probes("/nonexistent")
    assert p.select("how is training going?") == ["trainer"]
    assert "git" in p.select("what did we commit today?")
    assert p.select("tell me about yourself") == ["trainer"]
    assert p.select("I like tea") == []


def test_ledger_check_detects_tampering(tmp_path):
    o = Osiris(core=None, mentor=None, home=str(tmp_path), out=lambda s: None, background=False, tty=False)
    for i in range(3):
        o._record({"user": f"m{i}", "reply": "r"})
    assert verify_chain(o.log_path) == {"entries": 3, "intact": True, "broken_at": None,
                                        "head": o.stats["last_head"][:12]}
    lines = open(o.log_path).read().splitlines()
    row = json.loads(lines[1])
    row["reply"] = "edited"
    lines[1] = json.dumps(row)
    open(o.log_path, "w").write("\n".join(lines) + "\n")
    v = verify_chain(o.log_path)
    assert not v["intact"] and v["broken_at"] == 1


def test_files_are_read_only_under_home_and_never_secrets(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "NOTE.md").write_text("hello")
    (tmp_path / ".env.txt").write_text("KEY=1")
    (tmp_path / ".osiris").mkdir()
    (tmp_path / ".osiris" / "ibm.env").write_text("KEY=1")
    base = str(tmp_path)
    assert safe_path("docs/NOTE.md", base)
    assert safe_path(".env.txt", base) is None
    assert safe_path(".osiris/ibm.env", base) is None
    assert safe_path("/etc/passwd", base) is None
    out = Probes(base, base=base).files("see docs/NOTE.md and .osiris/ibm.env")
    assert out[0]["out"] == "hello" and "not read" in out[1]["out"]


def test_failed_probe_is_reported_not_invented(tmp_path):
    def boom():
        raise RuntimeError("x")
    r = Probes(str(tmp_path), base=str(tmp_path), trainer_status=boom).run("training?")
    assert r == [{"name": "trainer", "cmd": "trainer", "out": "(probe failed: RuntimeError)"}]


def test_evidence_quotes_the_results_file_and_its_hash(tmp_path):
    import hashlib
    d = tmp_path / "organism_sim" / "results"
    d.mkdir(parents=True)
    body = json.dumps({"rows": [1, 2], "verdict": {"outcome": "A and B", "A": True}})
    (d / "m3c_eval_seeds70-74.json").write_text(body)
    (d / "m3b_eval_seeds60-64.json").write_text(json.dumps({"verdict": True}))
    (d / "m3_eval_seeds20-24.json").write_text(json.dumps({"verdict": False}))
    p = Probes(str(tmp_path), base=str(tmp_path))
    assert p.select("what is the m3c ablation?") == ["evidence"]
    out = p.evidence("what is the m3c ablation?")["out"]
    assert hashlib.sha256(body.encode()).hexdigest()[:16] in out
    assert '"outcome":"A and B"' in out and "m3b" not in out and "rows" not in out
    listing = p.evidence("show me the scorecard evidence")["out"].splitlines()
    assert listing[0].endswith("verdict: FAIL") and listing[1].endswith("verdict: PASS")
    assert "not run, or not recorded" in p.evidence("and M6?")["out"]
