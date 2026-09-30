"""Overnight batch training for OSIRIS's core.

    osiris train --hours 8                 # run in this terminal
    osiris train --hours 8 --detach        # run in the background (setsid), survive logout
    osiris train --status                  # what the last run did
    osiris train --stop                    # ask a running trainer to save and stop

What it learns from (the train split only):
  docs      your own verified text: the roots in ~/.osiris/living/corpus.json
            (created with defaults on first run -- edit it to add or remove folders)
  chat      every learnable, non-held-out exchange you have had with OSIRIS
  archive   with --all (or "archive_roots" in corpus.json): the rest of your home
            directory, de-duplicated, sampled at "archive_share" (default 0.2) so
            your verified work stays the main diet. A byte model cannot tell a
            refuted claim from a measured one; it learns what it reads most.
  distill   grounded mentor lessons: a local Ollama model answers a question
            using only an excerpt of your own writing, and OSIRIS trains on it

What it never learns from: held-out files (1 in 10, chosen by a hash of the
path, so a file never changes sides), held-out chat exchanges, files that
look like secrets or console transcripts, and anything outside the roots.

How it is judged: bits per byte on held-out docs and held-out chat, against a
unigram baseline estimated on the train split. At the end the held-out chat
exchanges are rescored with the new weights so the speaking gate reflects
what OSIRIS can do now. A run manifest (every file and its SHA-256, seed and
parameters) is written before the first step; progress goes to
progress.jsonl in the same run directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from osiris_cli.living import (CHAT_MARKER, CHAT_QUIET_SECONDS, HELDOUT_EVERY, LIVING_HOME,
                               OllamaMentor, Osiris)

HOME = os.path.expanduser("~")
RUNS_HOME = os.path.join(LIVING_HOME, "train_runs")
CORPUS_CONFIG = os.path.join(LIVING_HOME, "corpus.json")
DISTILL_LOG = os.path.join(LIVING_HOME, "distill.jsonl")

DEFAULT_ROOTS = [
    "docs", "organism_sim", "dnalang-core", "bridge", "osiris-governance",
    "osiris-mobile-termux", "experiments", "fold/osiris", "analysis/nclm-manifest",
]
DEFAULT_EXTENSIONS = [".md", ".py", ".dna", ".txt", ".toml"]
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache",
                "results", "osiris_advantage_marrakesh", ".osiris_data", "site-packages",
                "dist-packages", "osiris_env", "osiris-venv", "osiris-venvs", "vvenv", "osiris_deps",
                "antigravity-sdk-python", "build", "dist"}
# Never part of the archive: third-party code, caches, backups, other businesses.
ARCHIVE_EXCLUDE_TOP = {"google-cloud-sdk", "snap", "dwave-cloud-client", "dwave-optimization",
                       "dwave-gate", "osiris-crypto", "josh", "dreamchaser", "Raw-3d-model-library",
                       "downloads", "OSIRIS_ARCHIVE", "manufacturing_output", "zenodo_archive"}
ARCHIVE_SHARE = 0.2
MAX_FILE_BYTES = 1_000_000
SEQ = 128                     # model context; windows are SEQ bytes (SEQ-1 predictions)
CHAT_SHARE = 0.3
PATIENCE = 5                  # periodic evals without a held-out gain before stopping
MIN_GAIN_BPB = 0.01              # fraction of each batch drawn from chat + distill lessons

SECRET_RE = re.compile(r"(AIza[0-9A-Za-z_\-]{30,}|ghp_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{30,}|"
                       r"sk-[0-9A-Za-z]{32,}|sbp_[0-9a-f]{30,}|postgres(ql)?://[^\s:]+:[^\s@]+@|"
                       r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                       r"(TOKEN|API_KEY|SECRET|PASSWORD)\s*=\s*['\"]?[0-9A-Za-z_\-]{24,})")
TRANSCRIPT_RE = re.compile(r"^[╭╰│━┌└├─]|osiris(::\}\{)?>\s|^\[\*\] Running|MENTOR ROUND|ENGINE COUNCIL")


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

@dataclass
class Doc:
    path: str
    sha256: str
    text: str
    heldout: bool


def load_corpus_config(path: str = CORPUS_CONFIG) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {"roots": DEFAULT_ROOTS, "extensions": DEFAULT_EXTENSIONS,
               "note": "Roots are relative to your home directory. Only your own verified text "
                       "belongs here: whatever OSIRIS reads, it learns to say."}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    return cfg


def is_heldout_path(rel: str) -> bool:
    return int(hashlib.sha256(rel.encode()).hexdigest(), 16) % 10 == 0


def looks_like_transcript(text: str) -> bool:
    lines = [ln for ln in text.splitlines()[:200] if ln.strip()]
    if not lines:
        return False
    return sum(1 for ln in lines if TRANSCRIPT_RE.search(ln.strip())) / len(lines) > 0.15


def build_corpus(roots: List[str], extensions: List[str], base: str = HOME,
                 seen: Optional[set] = None) -> Dict[str, list]:
    """Returns {"docs": [Doc], "skipped": [(path, reason)]}. Files whose bytes
    were already taken (``seen``) are skipped, so copies are learned once."""
    docs, skipped = [], []
    seen = set() if seen is None else seen
    for root in roots:
        top = os.path.join(base, root)
        if not os.path.isdir(top):
            skipped.append((root, "missing"))
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            at_home = os.path.abspath(dirpath) == os.path.abspath(base)
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")
                                 and "venv" not in d and not d.endswith((".egg-info", ".dist-info"))
                                 and not (at_home and d in ARCHIVE_EXCLUDE_TOP))
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, base)
                if name.startswith(".env") or not any(name.endswith(e) for e in extensions):
                    continue
                try:
                    if os.path.getsize(full) > MAX_FILE_BYTES:
                        skipped.append((rel, "too large"))
                        continue
                    raw = open(full, "rb").read()
                    text = raw.decode("utf-8")
                except (OSError, UnicodeDecodeError):
                    skipped.append((rel, "unreadable or not UTF-8"))
                    continue
                if SECRET_RE.search(text):
                    skipped.append((rel, "secret-like content"))
                    continue
                if looks_like_transcript(text):
                    skipped.append((rel, "console transcript"))
                    continue
                if len(text.strip()) < 64:
                    continue
                digest = hashlib.sha256(raw).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                docs.append(Doc(rel, digest, text, is_heldout_path(rel)))
    return {"docs": docs, "skipped": skipped}


def chat_lessons(log_path: str) -> Dict[str, List[str]]:
    """Train and held-out lesson texts from the conversation log."""
    train, held = [], []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not r.get("learnable") or r.get("voice") == "core":
                    continue
                lesson = f"User: {r['user']}\nOSIRIS: {r['reply']}\n"
                (held if r.get("heldout") else train).append(lesson)
    except OSError:
        pass
    return {"train": train, "heldout": held}


def distill_lessons(path: str = DISTILL_LOG) -> List[str]:
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    out.append(f"User: {r['question']}\nOSIRIS: {r['answer']}\n")
                except (ValueError, KeyError):
                    continue
    except OSError:
        pass
    return out


# ---------------------------------------------------------------------------
# Grounded distillation: the mentor answers from your own text
# ---------------------------------------------------------------------------

def _excerpts(docs: List[Doc], rng: random.Random, n: int) -> List[tuple]:
    pool = [d for d in docs if not d.heldout and d.path.endswith((".md", ".txt"))]
    out = []
    for _ in range(n * 3):
        if not pool or len(out) >= n:
            break
        d = rng.choice(pool)
        paras = [p.strip() for p in re.split(r"\n\s*\n", d.text) if 200 <= len(p.strip()) <= 1500]
        if paras:
            out.append((d.path, rng.choice(paras)))
    return out


def chat_active(living_home: str, now: Optional[float] = None) -> bool:
    try:
        age = (now or time.time()) - os.path.getmtime(os.path.join(living_home, CHAT_MARKER))
    except OSError:
        return False
    return age < CHAT_QUIET_SECONDS


def wait_for_quiet_chat(living_home: str, log: Callable[[str], None], poll: float = 10.0,
                        sleep: Callable[[float], None] = time.sleep) -> None:
    """Distillation runs the same mentor model as the chat on the same CPU; a
    chat queued behind it took 40-95 s a reply (2026-09-29). Wait it out."""
    if not chat_active(living_home):
        return
    log(f"distill: paused while you chat (resumes {CHAT_QUIET_SECONDS} s after the last message)")
    while chat_active(living_home):
        sleep(poll)
    log("distill: resumed")


def distill(mentor: OllamaMentor, docs: List[Doc], n: int, rng: random.Random,
            log: Callable[[str], None], path: str = DISTILL_LOG) -> int:
    """Ask the mentor n grounded questions; append each Q/A lesson to distill.jsonl."""
    if n <= 0 or mentor.model() is None:
        return 0
    made = 0
    for src, excerpt in _excerpts(docs, rng, n):
        wait_for_quiet_chat(os.path.dirname(path), log)
        try:
            q = "".join(mentor.stream([{"role": "user", "content":
                "Write one short question a researcher might ask about this passage. Output only "
                "the question.\n\nPassage:\n" + excerpt}])).strip().splitlines()[0][:300]
            a = "".join(mentor.stream([{"role": "system", "content":
                "You are OSIRIS. Answer only from the passage. If the passage does not say, answer "
                "that it does not say. Be concise and plain."},
                {"role": "user", "content": f"Passage (from {src}):\n{excerpt}\n\nQuestion: {q}"}])).strip()
        except (OSError, ConnectionError, ValueError, IndexError) as e:
            log(f"distill: mentor failed ({e}); stopping distillation")
            break
        if not q or not a:
            continue
        rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": mentor.model(), "source": src,
               "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(), "question": q, "answer": a}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        made += 1
        log(f"distill {made}/{n}: {src}")
    return made


# ---------------------------------------------------------------------------
# Sampling and evaluation
# ---------------------------------------------------------------------------

def to_bytes(texts: List[str]):
    import numpy as np
    blob = "\n\n".join(texts).encode("utf-8", errors="ignore")
    return np.frombuffer(blob, dtype=np.uint8).astype(np.int64)


def sample_batch(pools, weights, batch: int, rng: random.Random):
    import numpy as np
    rows = []
    for _ in range(batch):
        data = rng.choices(pools, weights=weights)[0]
        start = rng.randrange(0, len(data) - SEQ)
        rows.append(data[start:start + SEQ])
    arr = np.stack(rows)
    return arr[:, :-1], arr[:, 1:]


def eval_windows(data, limit: int):
    out = []
    if data is None or len(data) <= SEQ:
        return out
    stride = max(SEQ, (len(data) - SEQ) // max(limit, 1))
    for start in range(0, len(data) - SEQ, stride)[:limit]:
        w = data[start:start + SEQ]
        out.append((w[:-1][None, :], w[1:][None, :]))
    return out


def unigram_bpb(train_data, windows) -> Optional[float]:
    import numpy as np
    if not windows:
        return None
    counts = np.bincount(train_data, minlength=256).astype(float) + 1.0
    logp = np.log(counts / counts.sum())
    nats = [float(-logp[y[0]].mean()) for _, y in windows]
    return sum(nats) / len(nats) / math.log(2)


def core_bpb(core, windows) -> Optional[float]:
    if not windows:
        return None
    return sum(core.eval_batch(x, y) for x, y in windows) / len(windows) / math.log(2)


# ---------------------------------------------------------------------------
# Power (Termux): pause on battery below 20 %, resume at 35 %
# ---------------------------------------------------------------------------

def battery_ok(state: dict) -> bool:
    try:
        out = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=10)
        b = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return True  # not a phone, or Termux:API missing: nothing to protect
    plugged = b.get("plugged", "UNPLUGGED") != "UNPLUGGED"
    pct = int(b.get("percentage", 100))
    if plugged:
        state["paused"] = False
    elif pct < 20:
        state["paused"] = True
    elif pct >= 35:
        state["paused"] = False
    return not state.get("paused", False)


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

class Stop(Exception):
    pass


def run(core, *, hours: float, batch: int = 8, max_steps: Optional[int] = None, distill_n: int = 0,
        seed: Optional[int] = None, mentor: Optional[OllamaMentor] = None, runs_home: str = RUNS_HOME,
        mix: Optional[List[float]] = None, rescore: bool = True,
        living_home: str = LIVING_HOME, base: str = HOME, roots: Optional[List[str]] = None,
        eval_every: int = 200, save_every: int = 50, log_every: int = 10, patience: int = PATIENCE,
        log: Callable[[str], None] = print, power: Callable[[dict], bool] = battery_ok,
        archive_roots: Optional[List[str]] = None) -> dict:
    cfg = load_corpus_config(os.path.join(living_home, "corpus.json"))
    seed = seed if seed is not None else int(time.time())
    rng = random.Random(seed)
    import numpy as np
    np.random.seed(seed % 2 ** 32)   # weight init draws from numpy's global RNG: seeded, runs reproduce
    run_id = time.strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join(runs_home, run_id)
    os.makedirs(run_dir, exist_ok=True)
    progress_path = os.path.join(run_dir, "progress.jsonl")

    def progress(rec: dict) -> None:
        rec["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(progress_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    exts = cfg.get("extensions", DEFAULT_EXTENSIONS)
    seen: set = set()
    corpus = build_corpus(roots or cfg["roots"], exts, base, seen)
    docs = corpus["docs"]
    archive_roots = archive_roots if archive_roots is not None else cfg.get("archive_roots", [])
    archive = build_corpus(archive_roots, exts, base, seen) if archive_roots else {"docs": [], "skipped": []}
    arch_docs = archive["docs"]
    if distill_n and mentor is not None:
        distill(mentor, docs, distill_n, rng, log, os.path.join(living_home, "distill.jsonl"))
        if hasattr(mentor, "unload"):
            mentor.unload()  # a 7B mentor left in RAM cut training throughput ~25x on this machine
    chat = chat_lessons(os.path.join(living_home, "exchanges.jsonl"))
    lessons = chat["train"] + distill_lessons(os.path.join(living_home, "distill.jsonl"))

    doc_train = to_bytes([d.text for d in docs if not d.heldout])
    doc_held = to_bytes([d.text for d in docs if d.heldout])
    lesson_train = to_bytes(lessons) if lessons else None
    chat_held = to_bytes(chat["heldout"]) if chat["heldout"] else None
    if len(doc_train) <= SEQ:
        raise SystemExit("OSIRIS train: the corpus is empty -- check ~/.osiris/living/corpus.json")
    arch_train = to_bytes([d.text for d in arch_docs if not d.heldout]) if arch_docs else None
    arch_share = float(cfg.get("archive_share", ARCHIVE_SHARE))
    pools, weights = [doc_train], [1.0]
    if lesson_train is not None and len(lesson_train) > SEQ:
        pools.append(lesson_train)
        weights.append(CHAT_SHARE)
    if arch_train is not None and len(arch_train) > SEQ:
        pools.append(arch_train)
        weights.append(arch_share)
    weights[0] = max(0.05, 1.0 - sum(weights[1:]))
    if mix is not None:   # explicit docs / lessons / archive weights (an experiment arm)
        if len(mix) != 3 or len(pools) != 3:
            raise SystemExit(f"--mix needs docs,lessons,archive and all three pools present (have {len(pools)})")
        weights = [float(w) for w in mix]
    ev_docs = eval_windows(doc_held, 48)
    ev_chat = eval_windows(chat_held, 48)
    train_all = to_bytes([d.text for d in docs if not d.heldout] + lessons)
    uni_docs, uni_chat = unigram_bpb(train_all, ev_docs), unigram_bpb(train_all, ev_chat)

    planned = max_steps or int(hours * 3600 / 1.5)
    start_step = core.step()
    manifest = {
        "run_id": run_id, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": seed,
        "hours": hours, "batch": batch, "seq": SEQ, "max_steps": max_steps, "core_step_start": start_step,
        "chat_share": CHAT_SHARE, "heldout_rule": "sha256(relative path) % 10 == 0; chat: every "
        f"{HELDOUT_EVERY}th exchange", "roots": roots or cfg["roots"],
        "files": [{"path": d.path, "sha256": d.sha256, "heldout": d.heldout} for d in docs],
        "skipped": corpus["skipped"], "archive_roots": archive_roots,
        "archive_files": [{"path": d.path, "sha256": d.sha256, "heldout": d.heldout} for d in arch_docs],
        "archive_skipped": archive["skipped"], "pool_weights": weights, "chat_train": len(chat["train"]), "chat_heldout": len(chat["heldout"]),
        "distill_lessons": len(lessons) - len(chat["train"]),
        "bytes": {"doc_train": int(len(doc_train)), "doc_heldout": int(len(doc_held)),
                  "lessons": int(0 if lesson_train is None else len(lesson_train)),
                  "archive_train": int(0 if arch_train is None else len(arch_train))},
    }
    body = json.dumps(manifest, sort_keys=True).encode()
    manifest["manifest_sha256"] = hashlib.sha256(body).hexdigest()
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    log(f"OSIRIS train {run_id}: {len(docs)} verified files ({sum(d.heldout for d in docs)} held out), "
        f"{len(arch_docs)} archive files, "
        f"{len(chat['train'])} chat lessons, {manifest['distill_lessons']} distilled; "
        f"core step {start_step}; up to {hours} h")

    def evaluate(tag: str) -> dict:
        rec = {"kind": "eval", "tag": tag, "step": core.step(),
               "heldout_docs_bpb": core_bpb(core, ev_docs), "unigram_docs_bpb": uni_docs,
               "heldout_chat_bpb": core_bpb(core, ev_chat), "unigram_chat_bpb": uni_chat}
        progress(rec)
        d = rec["heldout_docs_bpb"]
        c = rec["heldout_chat_bpb"]
        log(f"eval [{tag}] step {rec['step']}: held-out docs "
            + ("n/a" if d is None else f"{d:.3f} bpb (unigram {uni_docs:.3f})")
            + ("" if c is None else f" · held-out chat {c:.3f} bpb (unigram {uni_chat:.3f})"))
        return rec

    stopping = {"flag": False}

    def on_signal(*_):
        stopping["flag"] = True

    old = {s: signal.signal(s, on_signal) for s in (signal.SIGTERM, signal.SIGINT)}
    lock = core.lock_path()
    with open(lock, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "run_id": run_id}, f)
    deadline = time.time() + hours * 3600
    first = evaluate("start")
    # Early stopping on held-out documents (2026-09-30: an 8 h run drove held-out
    # from 7.2 to 9.9 bits/byte -- worse than uniform -- while training loss fell;
    # rotation had already discarded the good weights). The best checkpoint is kept
    # and restored at the end; the run stops after `patience` evals without a gain.
    best = {"bpb": first["heldout_docs_bpb"], "step": first["step"], "since": 0}
    can_keep = hasattr(core, "save_best") and best["bpb"] is not None
    if can_keep:
        core.save_best()
    core.restart_schedule(planned)
    reason, steps, t0, power_state, loss_acc = "deadline", 0, time.time(), {}, []
    try:
        while True:
            if stopping["flag"]:
                reason = "stopped by signal"
                break
            if time.time() >= deadline:
                break
            if max_steps is not None and steps >= max_steps:
                reason = "max steps"
                break
            if not power(power_state):
                progress({"kind": "paused", "reason": "battery"})
                time.sleep(60)
                continue
            x, y = sample_batch(pools, weights, batch, rng)
            loss_acc.append(core.train_batch(x, y))
            steps += 1
            if steps % log_every == 0:
                rate = steps * batch * (SEQ - 1) / max(time.time() - t0, 1e-9)
                progress({"kind": "train", "step": core.step(), "loss": sum(loss_acc) / len(loss_acc),
                          "lr": core.current_lr(), "bytes_per_s": round(rate)})
                loss_acc = []
            if steps % save_every == 0:
                core.save(rotate=(steps % (save_every * 20) == 0))
            if steps % eval_every == 0:
                d = evaluate("periodic")["heldout_docs_bpb"]
                if d is not None and best["bpb"] is not None and d < best["bpb"] - MIN_GAIN_BPB:
                    best.update(bpb=d, step=core.step(), since=0)
                    if can_keep:
                        core.save_best()
                elif d is not None:
                    best["since"] += 1
                    if patience and best["since"] >= patience:
                        reason = f"held-out stopped improving (best {best['bpb']:.3f} bpb at step {best['step']})"
                        break
    finally:
        core.save(rotate=True)
        last = evaluate("end")
        restored = None
        if can_keep and last["heldout_docs_bpb"] is not None and last["heldout_docs_bpb"] > best["bpb"]:
            restored = core.restore_best()
            if restored is not None:
                log(f"restored the best held-out checkpoint (step {restored}, {best['bpb']:.3f} bpb); "
                    f"the final weights ({last['heldout_docs_bpb']:.3f} bpb) stay in the rotated backups")
        rescored = rescore_chat(core, living_home) if rescore else 0
        summary = {"kind": "end", "reason": reason, "steps": steps, "core_step_end": core.step(),
                   "hours": round((time.time() - t0) / 3600, 3), "rescored_heldout_exchanges": rescored,
                   "start": first, "end": last, "best": best, "restored_best_step": restored}
        progress(summary)
        try:
            os.remove(lock)
        except OSError:
            pass
        for s, h in old.items():
            signal.signal(s, h)
        log(f"OSIRIS train {run_id} finished ({reason}): {steps} steps, core now at step {core.step()}")
    return summary


def rescore_chat(core, living_home: str) -> int:
    """Score every held-out exchange with the current weights, for the speaking gate."""
    o = Osiris(core=core, home=living_home, out=lambda s: None, background=False)
    n = 0
    try:
        with open(o.log_path, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError):
        return 0
    step = int(core.step())
    for r in rows:
        if not r.get("heldout") or not r.get("learnable") or r.get("voice") == "core":
            continue
        bpb = core.bits_per_byte(r["reply"])
        if bpb is None:
            continue
        o.stats["heldout_scores"][r["hash"]] = [round(bpb, 4), round(o.unigram_bpb(r["reply"]), 4),
                                                step, int(r.get("index", 0))]
        n += 1
    o._save_stats()
    return n


# ---------------------------------------------------------------------------
# Status, stop, CLI
# ---------------------------------------------------------------------------

def latest_run(runs_home: str = RUNS_HOME) -> Optional[str]:
    try:
        runs = sorted(d for d in os.listdir(runs_home) if os.path.isdir(os.path.join(runs_home, d)))
    except OSError:
        return None
    return os.path.join(runs_home, runs[-1]) if runs else None


def status_lines(runs_home: str = RUNS_HOME, lock_path: Optional[str] = None) -> List[str]:
    run_dir = latest_run(runs_home)
    if run_dir is None:
        return ["no training run yet -- start one with: osiris train --hours 8 --detach"]
    lines = [f"last run      {os.path.basename(run_dir)}"]
    running = False
    if lock_path and os.path.exists(lock_path):
        try:
            os.kill(int(json.load(open(lock_path))["pid"]), 0)
            running = True
        except (OSError, ValueError, KeyError):
            pass
    evals, trains, end = [], [], None
    try:
        for line in open(os.path.join(run_dir, "progress.jsonl"), encoding="utf-8"):
            r = json.loads(line)
            if r["kind"] == "eval":
                evals.append(r)
            elif r["kind"] == "train":
                trains.append(r)
            elif r["kind"] == "end":
                end = r
    except (OSError, ValueError):
        pass
    lines.append("state         " + ("RUNNING" if running else (f"finished: {end['reason']}, {end['steps']} "
                 f"steps in {end['hours']} h" if end else "not running (no end record: interrupted?)")))
    if trains:
        t = trains[-1]
        lines.append(f"training      step {t['step']} · loss {t['loss']:.3f} nats/byte · "
                     f"{t['bytes_per_s']} bytes/s · lr {t['lr']:.2e}")
    if evals:
        a, b = evals[0], evals[-1]

        def fmt(r, k):
            v = r.get(k)
            return "n/a" if v is None else f"{v:.3f}"
        lines.append(f"held-out docs {fmt(a, 'heldout_docs_bpb')} -> {fmt(b, 'heldout_docs_bpb')} bpb "
                     f"(unigram {fmt(b, 'unigram_docs_bpb')})")
        if b.get("heldout_chat_bpb") is not None:
            lines.append(f"held-out chat {fmt(a, 'heldout_chat_bpb')} -> {fmt(b, 'heldout_chat_bpb')} bpb "
                         f"(unigram {fmt(b, 'unigram_chat_bpb')})")
    lines.append(f"files         {run_dir}")
    return lines


def stop(lock_path: str) -> str:
    try:
        pid = int(json.load(open(lock_path))["pid"])
        os.kill(pid, signal.SIGTERM)
        return f"asked trainer pid {pid} to save and stop"
    except (OSError, ValueError, KeyError):
        return "no trainer is running"


def detach(argv: List[str]) -> str:
    os.makedirs(RUNS_HOME, exist_ok=True)
    out = os.path.join(RUNS_HOME, "trainer.log")
    cmd = [sys.executable, "-m", "osiris_cli.train"] + [a for a in argv if a != "--detach"]
    with open(out, "a") as log_f:
        p = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    return f"trainer started (pid {p.pid}); log: {out}; check with: osiris train --status"


def make_core():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import osiris_termux_console as otc
    from osiris_cli.living import NclmCore
    return NclmCore(otc)


def main(argv: Optional[List[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="osiris train", description="Overnight batch training for OSIRIS's core.")
    ap.add_argument("--hours", type=float, default=8.0)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--distill", type=int, default=40, help="grounded mentor lessons to create first (0 = none)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--mix", default=None, help="docs,lessons,archive pool weights, e.g. 0.8,0.15,0.05")
    ap.add_argument("--runs-home", default=RUNS_HOME, help="where run manifests and progress go")
    ap.add_argument("--no-rescore", action="store_true",
                    help="experiment runs: do not rescore the live chat's held-out exchanges")
    ap.add_argument("--all", action="store_true",
                    help="also learn from the rest of your home directory as a de-duplicated archive "
                         "(sampled at archive_share; third-party code, venvs and backups excluded)")
    ap.add_argument("--detach", action="store_true", help="run in the background and return")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true")
    args = ap.parse_args(argv)
    core = make_core()
    if args.status:
        print("\n".join(status_lines(lock_path=core.lock_path())))
        return
    if args.stop:
        print(stop(core.lock_path()))
        return
    if core.training_locked():
        print("OSIRIS train: a trainer is already running (osiris train --status)")
        return
    if args.detach:
        print(detach(argv))
        return
    run(core, hours=args.hours, batch=args.batch, max_steps=args.max_steps, distill_n=args.distill,
        seed=args.seed, mentor=OllamaMentor() if args.distill else None,
        log=lambda s: print(s, flush=True), archive_roots=["."] if args.all else None,
        mix=[float(x) for x in args.mix.split(",")] if args.mix else None,
        runs_home=args.runs_home, rescore=not args.no_rescore)


if __name__ == "__main__":
    main()
