"""The frozen probe set, milestone checkpoints, and whole-reply scoring (scorer 3)."""
import json

import pytest

from osiris_cli import living, osiris_repl, prepost, probeset, train
from osiris_cli.living import NclmCore, Osiris

otc = osiris_repl.otc
needs_core = pytest.mark.skipif(otc is None, reason="osiris_termux_console not importable")


@pytest.fixture
def organism(tmp_path, monkeypatch):
    monkeypatch.setattr(otc, "ORGANISM_HOME", str(tmp_path / "organism"))
    monkeypatch.setattr(otc, "ORGANISM_MILESTONE_EVERY", 1000)
    monkeypatch.setattr(otc, "_organism_state", {"model": None, "optimizer": None, "step": 0, "history": []})
    return tmp_path / "organism"


def ledger(home, n, reply=lambda i: f"reply {i}: " + "the quick brown fox jumps over the lazy dog. " * 4):
    o = Osiris(core=None, home=str(home), out=lambda s: None, background=False)
    voices = ["mentor:gemini-2.5-flash"] * 4 + ["mentor:qwen2.5:7b"]
    for i in range(n):
        o._record({"heldout": i % 5 == 0, "learnable": True, "voice": voices[(i // 5) % 5], "user": f"q{i}",
                   "reply": reply(i), "index": i})
    return o


# -- whole-reply scoring --------------------------------------------------------

def test_every_byte_after_the_first_is_scored_once():
    text = "".join(chr(97 + i % 26) for i in range(2000))
    wins = living.text_windows(text, 128)
    assert len(wins) == 16 and living.SCORE_WINDOWS is None
    assert living.scored_bytes(text, 128) == text.encode()[1:]
    assert living.scored_bytes(text[:130], 128) == text.encode()[1:128]   # a 3-byte tail fills no window


def test_the_unigram_is_scored_on_the_bytes_the_core_predicts(tmp_path):
    class Core:
        name = "fake"

        def step(self):
            return 0

        def bits_per_byte(self, text):
            return 3.0

        def scored_bytes(self, text):
            return text.encode()[1:4]

    o = Osiris(core=Core(), home=str(tmp_path), out=lambda s: None, background=False, tty=False)
    o.stats["unigram"] = {str(b): 50 for b in b"abc"}
    o._after("lesson", "zabcxyz", True, "k", 0)
    assert o.stats["heldout_scores"]["k"][1] == round(o.unigram_bpb(b"abc"), 4)
    assert o.stats["heldout_scores"]["k"][1] < round(o.unigram_bpb("zabcxyz"), 4)
    assert o.heldout_unigram("zabcxyz") == o.unigram_bpb(b"abc")         # train.py re-scores through this too


def test_the_held_out_baseline_is_defined_once():
    """A second heldout_unigram later in the class body silently replaces the first, and with it the gate's
    baseline (a whole-reply alias did, on an unmerged branch)."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(living))
    body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Osiris").body
    names = [n.name for n in body if isinstance(n, ast.FunctionDef)]
    assert names.count("heldout_unigram") == 1 and names.count("unigram_bpb") == 1


@needs_core
def test_the_core_is_scored_past_the_first_two_windows(organism):
    core = NclmCore(otc)
    head = "OSIRIS here. " * 30                                   # 390 bytes: past two windows
    a, b = core.bits_per_byte(head + "a" * 300), core.bits_per_byte(head + "\x01\x02" * 150)
    assert a != b
    assert core.scorer() == living.SCORER == 3


# -- milestones -------------------------------------------------------------------

@needs_core
def test_one_milestone_is_kept_per_thousand_steps_and_never_rotated(organism, monkeypatch):
    monkeypatch.setattr(otc, "ORGANISM_MAX_BACKUPS", 1)
    model, opt = otc._organism_build()
    for step in (999, 1003, 1500, 1990, 2001):
        otc._organism_save(model, opt, step, [1.0], rotate=True)
    kept = probeset.milestones(str(organism))
    assert [probeset.checkpoint_step(m) for _, m in kept] == [1003, 2001]
    assert [c.rsplit("/", 1)[1] for c, _ in kept] == ["organism.milestone1000.npz", "organism.milestone2000.npz"]
    assert len(list(organism.glob("organism.step*.npz"))) == 1 and not list(organism.glob("*.tmp"))


@needs_core
def test_experiment_folders_keep_no_milestones(organism, monkeypatch):
    monkeypatch.setattr(otc, "ORGANISM_MILESTONE_EVERY", 0)
    model, opt = otc._organism_build()
    otc._organism_save(model, opt, 5000, [1.0], rotate=False)
    assert probeset.milestones(str(organism)) == []


# -- drawing and freezing the set -------------------------------------------------

def test_every_voice_is_represented_and_the_draw_spans_the_ledger():
    voices = {"g": 200, "q1": 9, "q3": 4, "q7": 2}
    rows, i = [], 0
    for v, n in voices.items():
        for _ in range(n):
            rows.append({"index": i, "hash": f"h{i}", "heldout": True, "learnable": True, "voice": v,
                         "reply": "a reply of some length"})
            i += 1
    rows += [{"index": 999, "hash": "x", "heldout": False, "learnable": True, "voice": "g", "reply": "trained"},
             {"index": 998, "hash": "y", "heldout": True, "learnable": False, "voice": "g", "reply": "cut short"},
             {"index": 997, "hash": "z", "heldout": True, "learnable": True, "voice": "core", "reply": "own voice"},
             {"index": 996, "hash": "w", "heldout": True, "learnable": True, "voice": "g", "reply": "short"},
             {"index": None, "hash": "v", "heldout": True, "learnable": True, "voice": "g", "reply": "no index"}]
    picked = probeset.select(rows, 100)
    by = {v: sum(r["voice"] == v for r in picked) for v in voices}
    assert len(picked) == 100 and by == {"g": 87, "q1": 7, "q3": 4, "q7": 2}
    g = [r["index"] for r in picked if r["voice"] == "g"]
    assert g[0] == 0 and g[-1] == 199 and len(set(g)) == 87
    assert [r["index"] for r in picked] == sorted(r["index"] for r in picked)
    assert probeset.select(list(reversed(rows)), 100) == picked
    assert not {r["index"] for r in picked} & {996, 997, 998, 999}


def test_the_set_is_frozen_once_and_records_its_ledger(tmp_path):
    ledger(tmp_path, 200)
    info = probeset.freeze(str(tmp_path), size=30)
    body = json.load(open(info["path"]))
    assert info["n"] == 30 and info["sha256"] == prepost.file_sha256(info["path"])
    assert body["ledger"]["intact"] and body["ledger"]["rows"] == 200 and body["ledger"]["candidates"] == 40
    assert all(it["index"] % 5 == 0 for it in body["items"])
    with pytest.raises(FileExistsError):
        probeset.freeze(str(tmp_path), size=30)
    assert prepost.file_sha256(info["path"]) == info["sha256"]


def test_too_few_heldout_replies_are_not_frozen(tmp_path):
    ledger(tmp_path, 20)
    with pytest.raises(ValueError):
        probeset.freeze(str(tmp_path))
    assert probeset.load_set(str(tmp_path)) is None and probeset.status_line(str(tmp_path)) is None


# -- scoring checkpoints ----------------------------------------------------------

@needs_core
def test_each_milestone_is_scored_once_with_the_gate_scorer(organism, tmp_path):
    living_home = tmp_path / "living"
    ledger(living_home, 160)
    probeset.freeze(str(living_home), size=30)
    model, opt = otc._organism_build()
    otc._organism_save(model, opt, 1004, [1.0], rotate=False)
    assert len(probeset.pending(str(living_home), str(organism))) == 1

    rows = probeset.score_pending(str(living_home), str(organism))
    assert len(rows) == 1 and probeset.pending(str(living_home), str(organism)) == []
    row = rows[0]
    assert (row["step"], row["n"], row["scorer"], row["checkpoint"]) == (1004, 30, 3, "organism.milestone1000.npz")
    probe, sha = probeset.load_set(str(living_home))
    gate = NclmCore(otc)                                          # the live core, same weights
    assert row["items"][0] == round(gate.bits_per_byte(probe["items"][0]["reply"]), 4)
    assert row["probe_set_sha256"] == sha and set(row["by_voice"]) == {"mentor:gemini-2.5-flash", "mentor:qwen2.5:7b"}
    assert "step 1004" in probeset.status_line(str(living_home))
    assert probeset.score_pending(str(living_home), str(organism)) == []


def test_the_conversation_does_not_wait_for_probe_scoring(tmp_path, monkeypatch):
    calls = []

    class Core:
        name = "fake"

        def organism_dir(self):
            return str(tmp_path / "organism")

    monkeypatch.setattr(probeset, "pending", lambda home, where: [("m.npz", "m.json")])
    monkeypatch.setattr(probeset, "score_pending", lambda home, where: calls.append(where))
    o = Osiris(core=Core(), home=str(tmp_path), out=lambda s: None, background=False, tty=False)
    o._score_probes()
    o._probing.join(5)
    assert calls == [str(tmp_path / "organism")]


def test_a_failed_probe_scoring_does_not_end_a_training_run_badly(tmp_path, monkeypatch):
    class Core:
        def organism_dir(self):
            return str(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("stale model code")

    monkeypatch.setattr(probeset, "score_pending", boom)
    said = []
    assert train.score_probes(Core(), str(tmp_path), said.append) == 0
    assert said == ["probe set not scored: stale model code"]
