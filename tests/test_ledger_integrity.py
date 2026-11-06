"""E-24: the exchange-log check names the file it read and tells an empty log, a tampered one and an unreadable one
apart, each with its own exit code (0, 1, 2), from the REPL probe and from `osiris check`."""
import json
import os
import subprocess
import sys
from pathlib import Path

from osiris_cli import probes
from osiris_cli.living import Osiris
from osiris_cli.probes import Probes, verify_chain

REPO = Path(__file__).resolve().parents[1]


def _osiris(home, n=3):
    o = Osiris(core=None, mentor=None, home=str(home), out=lambda s: None, background=False, tty=False)
    for i in range(n):
        o._record({"user": f"m{i}", "reply": "r"})
    return o


def _append(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def test_a_missing_or_empty_log_is_empty_and_passes(tmp_path):
    for path in (tmp_path / "none.jsonl", tmp_path / "empty.jsonl"):
        if path.name == "empty.jsonl":
            path.write_text("")
        v = verify_chain(str(path))
        assert (v["status"], v["exit_code"], v["intact"], v["entries"]) == ("EMPTY", 0, True, 0)
        assert v["resolved_path"] == str(path) and v["broken_at"] is None


def test_an_intact_log_names_the_absolute_file_it_read(tmp_path, monkeypatch):
    o = _osiris(tmp_path)
    v = verify_chain(o.log_path)
    assert (v["status"], v["exit_code"], v["entries"]) == ("INTACT", 0, 3)
    assert v["resolved_path"] == os.path.abspath(o.log_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert verify_chain("~/exchanges.jsonl")["resolved_path"] == os.path.join(str(tmp_path), "exchanges.jsonl")
    monkeypatch.chdir(tmp_path)
    v = verify_chain("exchanges.jsonl")
    assert v["resolved_path"] == os.path.join(os.getcwd(), "exchanges.jsonl") and v["entries"] == 3


def test_an_entry_that_fails_its_hash_or_links_nowhere_is_tampered(tmp_path):
    import hashlib
    o = _osiris(tmp_path)
    lines = open(o.log_path).read().splitlines()
    edited = json.loads(lines[1])
    edited["reply"] = "edited"
    open(o.log_path, "w").write("\n".join([lines[0], json.dumps(edited), lines[2]]) + "\n")
    v = verify_chain(o.log_path)
    assert (v["status"], v["exit_code"], v["intact"], v["broken_at"]) == ("TAMPERED", 1, False, 1)
    assert "hash" in v["error"]

    orphan = json.loads(lines[2])                         # a correct hash over a prev that names no entry
    orphan.pop("hash")
    orphan["prev"] = "f" * 64
    orphan["hash"] = hashlib.sha256(json.dumps(orphan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    open(o.log_path, "w").write("\n".join([lines[0], lines[1], json.dumps(orphan)]) + "\n")
    v = verify_chain(o.log_path)
    assert (v["status"], v["exit_code"], v["broken_at"]) == ("TAMPERED", 1, 2) and "links to no" in v["error"]


def test_a_line_that_is_json_but_not_an_entry_is_tampered(tmp_path):
    o = _osiris(tmp_path)
    _append(o.log_path, "[1, 2]")
    v = verify_chain(o.log_path)
    assert (v["status"], v["exit_code"], v["entries"], v["broken_at"]) == ("TAMPERED", 1, 3, 3)


def test_a_line_that_is_not_json_is_unreadable(tmp_path):
    o = _osiris(tmp_path)
    _append(o.log_path, '{"user": "cut off')
    v = verify_chain(o.log_path)
    assert (v["status"], v["exit_code"], v["intact"], v["entries"], v["broken_at"]) == ("UNREADABLE", 2, False, 3, 3)
    assert "line 4 is not JSON" in v["error"]


def test_a_file_that_cannot_be_read_or_decoded_is_unreadable(tmp_path, monkeypatch):
    path = tmp_path / "exchanges.jsonl"
    path.write_bytes(b'{"user": "\xff\xfe"}\n')
    v = verify_chain(str(path))
    assert (v["status"], v["exit_code"], v["broken_at"]) == ("UNREADABLE", 2, None)
    assert v["error"].startswith("UnicodeDecodeError")

    def denied(*a, **k):
        raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(probes, "open", denied, raising=False)  # root under PRoot reads a mode-000 file anyway
    v = verify_chain(str(path))
    assert (v["status"], v["exit_code"]) == ("UNREADABLE", 2) and v["error"].startswith("PermissionError")


def test_the_ledger_probe_names_the_data_home_and_says_when_it_has_no_log(tmp_path):
    home = tmp_path / "living"
    res = Probes(str(home)).ledger()
    path = str(home / "exchanges.jsonl")
    assert (res["status"], res["exit_code"], res["resolved_path"]) == ("EMPTY", 0, path)
    assert f"verify {path} hash chain" == res["cmd"]
    assert f"Data Home:    {path}" in res["out"] and "reading another data home" in res["out"]

    _osiris(home)
    res = Probes(str(home)).ledger()
    assert (res["status"], res["exit_code"]) == ("INTACT", 0)
    assert "Entries:      3 verified" in res["out"] and "Note:" not in res["out"]

    _append(path, "not json")
    res = Probes(str(home)).ledger()
    assert (res["status"], res["exit_code"]) == ("UNREADABLE", 2)
    assert "FAIL (UNREADABLE)" in res["out"] and "Broken At:    entry 3 (line 4 is not JSON" in res["out"]


def _check(tmp_path, *args):
    env = dict(os.environ, HOME=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join(p for p in [str(REPO), os.environ.get("PYTHONPATH", "")] if p)
    return subprocess.run([sys.executable, "-m", "osiris_cli", "check", *args], capture_output=True, text=True,
                          env=env, cwd=str(tmp_path), timeout=120)


def test_osiris_check_exits_with_the_status_of_the_log_it_names(tmp_path):
    home = tmp_path / "termux_living"
    r = _check(tmp_path, "ledger", "--home", str(home))
    assert r.returncode == 0, r.stderr
    assert f"Data Home:    {home / 'exchanges.jsonl'}" in r.stdout and "Status:       EMPTY" in r.stdout

    o = _osiris(home)
    lines = open(o.log_path).read().splitlines()
    open(o.log_path, "w").write("\n".join([lines[0], lines[1].replace('"r"', '"edited"'), lines[2]]) + "\n")
    r = _check(tmp_path, "ledger", "--home", str(home))
    assert r.returncode == 1 and "Status:       TAMPERED" in r.stdout, (r.stdout, r.stderr)

    open(o.log_path, "w").write("\n".join(lines) + "\nnot json\n")
    r = _check(tmp_path, "ledger", "--home", str(home))
    assert r.returncode == 2 and "Status:       UNREADABLE" in r.stdout, (r.stdout, r.stderr)


def test_osiris_check_refuses_a_home_flag_without_a_directory(tmp_path):
    r = _check(tmp_path, "--home")
    assert r.returncode == 1 and "--home needs a directory" in r.stderr
