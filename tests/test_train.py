"""Overnight trainer: corpus hygiene, held-out discipline, write-ahead manifest."""
import json
import os
import random

import numpy as np

from osiris_cli import train
from osiris_cli.living import Osiris

HELD_MARK = "HELDOUT-ONLY-MARKER"


def write(base, rel, text):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def corpus_tree(base):
    body = "Staggered dynamical decoupling refocuses static ZZ coupling on a chain. " * 20
    for i in range(40):
        write(base, f"docs/note{i}.md", f"# Note {i}\n\n{body}\n")
    write(base, "docs/.env", "IBM_QUANTUM_TOKEN=abcdefghijklmnopqrstuvwxyz0123456789")
    write(base, "docs/keys.md", "config: AIza" + "x" * 35 + "\n" + body)
    write(base, "docs/session.md", "\n".join(["╭─ ENGINE COUNCIL ─╮", "│ Architect │", "osiris> hi"] * 20))
    write(base, "docs/.git/HEAD", "ref: refs/heads/main")


class FakeCore:
    name = "fake"

    def __init__(self, lock):
        self._step, self.batches, self.saved, self._lock = 0, [], 0, lock

    def step(self):
        return self._step

    def lock_path(self):
        return self._lock

    def restart_schedule(self, total):
        self.total = total

    def train_batch(self, x, y):
        self.batches.append(x.copy())
        self._step += 1
        return 5.0 - 0.01 * self._step

    def eval_batch(self, x, y):
        return 3.0

    def bits_per_byte(self, text):
        return 2.5

    def save(self, rotate=False):
        self.saved += 1

    def current_lr(self):
        return 1e-4


def test_corpus_excludes_secrets_env_transcripts_and_git(tmp_path):
    corpus_tree(str(tmp_path))
    c = train.build_corpus(["docs"], train.DEFAULT_EXTENSIONS, str(tmp_path))
    paths = {d.path for d in c["docs"]}
    reasons = dict(c["skipped"])
    assert "docs/.env" not in paths and "docs/.git/HEAD" not in paths
    assert reasons["docs/keys.md"] == "secret-like content"
    assert reasons["docs/session.md"] == "console transcript"
    assert len(paths) == 40


def test_heldout_split_is_stable_and_by_path():
    assert train.is_heldout_path("docs/a.md") == train.is_heldout_path("docs/a.md")
    share = sum(train.is_heldout_path(f"docs/f{i}.md") for i in range(2000)) / 2000
    assert 0.07 < share < 0.13


def test_run_writes_manifest_first_never_trains_heldout_and_releases_lock(tmp_path):
    base, living_home = str(tmp_path / "home"), str(tmp_path / "living")
    corpus_tree(base)
    held = sorted(f"docs/note{i}.md" for i in range(40) if train.is_heldout_path(f"docs/note{i}.md"))
    assert held, "fixture needs at least one held-out file"
    write(base, held[0], f"# held\n\n{HELD_MARK} " * 200)
    os.makedirs(living_home, exist_ok=True)
    core = FakeCore(str(tmp_path / "train.lock"))
    summary = train.run(core, hours=1, max_steps=30, batch=4, roots=["docs"], base=base,
                        living_home=living_home, runs_home=str(tmp_path / "runs"),
                        log=lambda s: None, power=lambda st: True, eval_every=10, save_every=5)
    assert summary["reason"] == "max steps" and summary["steps"] == 30
    assert not os.path.exists(core.lock_path())
    run_dir = train.latest_run(str(tmp_path / "runs"))
    manifest = json.load(open(os.path.join(run_dir, "manifest.json")))
    assert any(f["heldout"] for f in manifest["files"]) and manifest["manifest_sha256"]
    seen = b"".join(bytes(row.astype(np.uint8)) for b in core.batches for row in b)
    assert HELD_MARK.encode() not in seen
    kinds = [json.loads(line)["kind"] for line in open(os.path.join(run_dir, "progress.jsonl"))]
    assert kinds[0] == "eval" and kinds[-1] == "end" and "train" in kinds


def test_chat_lessons_keep_heldout_and_unlearnable_out(tmp_path):
    log = tmp_path / "exchanges.jsonl"
    rows = [{"user": "a", "reply": "b", "learnable": True, "heldout": False, "voice": "mentor:x"},
            {"user": "c", "reply": "d", "learnable": True, "heldout": True, "voice": "mentor:x"},
            {"user": "e", "reply": "f", "learnable": False, "heldout": False, "voice": "mentor:x"},
            {"user": "g", "reply": "h", "learnable": True, "heldout": False, "voice": "core"}]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    out = train.chat_lessons(str(log))
    assert out["train"] == ["User: a\nOSIRIS: b\n"] and out["heldout"] == ["User: c\nOSIRIS: d\n"]


class ScriptedMentor:
    def __init__(self):
        self.prompts = []

    def model(self):
        return "scripted"

    def stream(self, messages):
        self.prompts.append(messages[-1]["content"])
        yield "What does staggering cancel?" if len(self.prompts) % 2 else "Static ZZ coupling."


def test_distillation_is_grounded_in_train_split_excerpts(tmp_path):
    corpus_tree(str(tmp_path))
    docs = train.build_corpus(["docs"], train.DEFAULT_EXTENSIONS, str(tmp_path))["docs"]
    mentor, out = ScriptedMentor(), str(tmp_path / "distill.jsonl")
    made = train.distill(mentor, docs, 3, random.Random(0), lambda s: None, out)
    rows = [json.loads(line) for line in open(out)]
    assert made == 3 and len(rows) == 3
    held = {d.path for d in docs if d.heldout}
    assert all(r["source"] not in held for r in rows)
    assert all("Passage" in p for p in mentor.prompts)


def test_rescore_updates_heldout_exchange_scores(tmp_path):
    o = Osiris(core=None, home=str(tmp_path), out=lambda s: None, background=False)
    key = o._record({"heldout": True, "learnable": True, "voice": "mentor:x", "user": "q",
                     "reply": "an answer long enough to score", "index": 0})
    o._save_stats()
    n = train.rescore_chat(FakeCore(str(tmp_path / "l")), str(tmp_path))
    stats = json.load(open(o.stats_path))
    assert n == 1 and stats["heldout_scores"][key][0] == 2.5


def test_archive_tier_dedupes_and_skips_third_party(tmp_path):
    base = str(tmp_path)
    corpus_tree(base)
    body = open(os.path.join(base, "docs/note1.md")).read()
    write(base, "copy/note1.md", body)                     # a duplicate of a verified file
    write(base, "google-cloud-sdk/lib/x.py", "print('vendor code')\n" * 20)
    write(base, "proj/.venv/lib/y.py", "print('venv')\n" * 20)
    write(base, "proj/idea.md", "# idea\n\n" + "An archive note about the 2025 claims. " * 10)
    seen = set()
    verified = train.build_corpus(["docs"], train.DEFAULT_EXTENSIONS, base, seen)["docs"]
    archive = train.build_corpus(["."], train.DEFAULT_EXTENSIONS, base, seen)["docs"]
    paths = {d.path for d in archive}
    assert "proj/idea.md" in paths
    assert "copy/note1.md" not in paths and not any(p.startswith("docs/") for p in paths)
    assert not any("google-cloud-sdk" in p or ".venv" in p for p in paths)
    assert len(verified) == 40


def test_distillation_waits_while_a_chat_is_active(tmp_path):
    marker = tmp_path / "chat.active"
    marker.write_text("1")
    naps, logs = [], []

    def sleep(t):
        naps.append(t)
        os.utime(marker, (0, 0))    # the chat goes quiet

    train.wait_for_quiet_chat(str(tmp_path), logs.append, sleep=sleep)
    assert naps and "paused" in logs[0] and logs[-1] == "distill: resumed"
    train.wait_for_quiet_chat(str(tmp_path), logs.append, sleep=lambda t: 1 / 0)  # quiet: no wait
