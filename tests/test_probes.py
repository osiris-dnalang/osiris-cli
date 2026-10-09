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
    assert verify_chain(o.log_path) == {"entries": 3, "intact": True, "broken_at": None, "forks": [],
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


def test_file_checks_are_capped_even_when_paths_are_missing(tmp_path):
    msg = " ".join(f"research/kit/f{i}.py" for i in range(30))
    assert len(Probes(str(tmp_path), base=str(tmp_path)).files(msg)) == 2


def _osiris(home):
    return Osiris(core=None, mentor=None, home=str(home), out=lambda s: None, background=False, tty=False)


def test_two_consoles_appending_alternately_keep_one_chain(tmp_path):
    a, b = _osiris(tmp_path), _osiris(tmp_path)          # each loads the same stats, then writes in turn
    for i in range(4):
        (a if i % 2 == 0 else b)._record({"user": f"m{i}", "reply": "r"})
    v = verify_chain(a.log_path)
    assert v["intact"] and v["entries"] == 4 and v["forks"] == []


def test_a_fork_is_reported_and_a_link_to_nothing_breaks_the_chain(tmp_path):
    import hashlib

    def row(prev, n):
        e = {"user": f"m{n}", "reply": "r", "prev": prev}
        e["hash"] = hashlib.sha256(json.dumps(e, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return e
    g = "0" * 64
    r0 = row(g, 0)
    r1 = row(r0["hash"], 1)
    r2 = row(r0["hash"], 2)                               # a second writer still at r0's head: a fork
    path = tmp_path / "x.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in (r0, r1, r2)))
    v = verify_chain(str(path))
    assert v["intact"] and v["forks"] == [2] and v["entries"] == 3
    r3 = row("f" * 64, 3)                                 # points at no entry (e.g. its parent was deleted)
    path.write_text("".join(json.dumps(r) + "\n" for r in (r0, r1, r3)))
    v = verify_chain(str(path))
    assert not v["intact"] and v["broken_at"] == 2


def test_the_writer_chains_to_the_file_not_to_its_own_memory(tmp_path):
    from osiris_cli import living
    o = _osiris(tmp_path)
    o._record({"user": "x" * 200000, "reply": "r"})      # a large last entry, read backwards in blocks
    o.stats["last_head"] = "0" * 64                       # stale in-memory head, as a second console would have
    o._record({"user": "next", "reply": "r"})
    v = verify_chain(o.log_path)
    assert v["intact"] and v["forks"] == [] and v["entries"] == 2
    with open(o.log_path, "rb") as f:
        assert living._last_hash(f) == o.stats["last_head"]
