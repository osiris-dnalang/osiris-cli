#!/usr/bin/env python3
"""NCLM-Mix-1 driver and analysis. See PRE_REGISTRATION.md (committed before any run).

  python experiments/nclm_mix1/run.py              # launch the 6 runs (3 at a time) and wait
  python experiments/nclm_mix1/run.py --analyse    # verdict -> results.json, RESULT.md
"""

import json
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_mix1")
ARMS = {"control": "0.5,0.3,0.2", "docs-heavy": "0.8,0.15,0.05"}
SEEDS = [0, 1, 2]
PARALLEL = int(os.environ.get("NCLM_MIX1_PARALLEL", "1"))  # see EXECUTION.md
HOURS = 3.0
UNIGRAM = 5.026
QUIET_LOAD = 3.0
# pre-registered criterion
WINS_NEEDED, MIN_GAIN, GUARD = 2, 0.10, 0.10


def run_dirs(arm, seed):
    tag = f"{arm}_s{seed}"
    return os.path.join(WORK, "ckpt", tag), os.path.join(WORK, "runs", tag), os.path.join(WORK, "logs", tag + ".log")


def freeze_inputs():
    """One snapshot of the lessons and corpus config for every run (EXECUTION.md, 2026-10-01)."""
    import hashlib
    import shutil
    snap = os.path.join(WORK, "inputs")
    if not os.path.isdir(snap):
        os.makedirs(snap)
        live = os.path.join(os.path.expanduser("~"), ".osiris", "living")
        for name in ("corpus.json", "exchanges.jsonl", "distill.jsonl"):
            shutil.copy2(os.path.join(live, name), os.path.join(snap, name))
        sys.path.insert(0, REPO)
        from osiris_cli import train
        info = train.freeze_corpus(os.path.join(snap, "frozen_corpus.json"), living_home=snap,
                                   archive_roots=["."])
        print("frozen corpus", json.dumps(info), flush=True)
    digest = {n: hashlib.sha256(open(os.path.join(snap, n), "rb").read()).hexdigest()
              for n in sorted(os.listdir(snap))}
    print("inputs", json.dumps(digest), flush=True)
    return snap


def launch():
    snap = freeze_inputs()
    jobs = [(a, s) for s in SEEDS for a in ARMS]
    running = []
    while jobs or running:
        while jobs and len(running) < PARALLEL:
            waited = 0
            while os.getloadavg()[0] > QUIET_LOAD:   # start only on a quiet machine (EXECUTION.md)
                if waited % 600 == 0:
                    print(time.strftime("%H:%M:%S"), f"waiting: load {os.getloadavg()[0]:.1f} > {QUIET_LOAD}", flush=True)
                time.sleep(30)
                waited += 30
            arm, seed = jobs.pop(0)
            ckpt, runs, log = run_dirs(arm, seed)
            for d in (ckpt, runs, os.path.dirname(log)):
                os.makedirs(d, exist_ok=True)
            # PYTHONPATH = this repo only: an inherited /home/enki entry imported a stale copy of
            # osiris.nclm on the third launch (EXECUTION.md). No thread caps: runs are sequential.
            env = {k: v for k, v in os.environ.items() if k not in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")}
            env.update(OSIRIS_ORGANISM_HOME=ckpt, PYTHONPATH=REPO)
            cmd = [sys.executable, "-m", "osiris_cli.train", "--hours", str(HOURS), "--all", "--distill", "0",
                   "--seed", str(seed), "--mix", ARMS[arm], "--runs-home", runs, "--no-rescore", "--living-home", snap,
                   "--frozen-corpus", os.path.join(snap, "frozen_corpus.json")]
            f = open(log, "a")
            p = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            running.append((arm, seed, p, f))
            print(time.strftime("%H:%M:%S"), "start", arm, seed, "pid", p.pid, flush=True)
        for item in list(running):
            arm, seed, p, f = item
            if p.poll() is not None:
                f.close()
                running.remove(item)
                print(time.strftime("%H:%M:%S"), "done", arm, seed, "exit", p.returncode, flush=True)
        time.sleep(20)


def summarise(arm, seed):
    _, runs, _ = run_dirs(arm, seed)
    [run_id] = sorted(d for d in os.listdir(runs) if os.path.isdir(os.path.join(runs, d)))[-1:]
    rows = [json.loads(line) for line in open(os.path.join(runs, run_id, "progress.jsonl"))]
    evals = [r for r in rows if r.get("kind") == "eval" and r.get("heldout_docs_bpb") is not None]
    best = min(evals, key=lambda r: r["heldout_docs_bpb"])
    end = next((r for r in rows if r.get("kind") == "end"), {})
    manifest = json.load(open(os.path.join(runs, run_id, "manifest.json")))
    return {"arm": arm, "seed": seed, "run_id": run_id, "best_docs_bpb": best["heldout_docs_bpb"],
            "chat_bpb_at_best": best.get("heldout_chat_bpb"), "best_step": best["step"],
            "stop_reason": end.get("reason"), "steps": end.get("steps"), "pool_weights": manifest.get("pool_weights"),
            "manifest_sha256": manifest.get("manifest_sha256"), "below_unigram": best["heldout_docs_bpb"] < UNIGRAM,
            "hit_time_cap": end.get("reason") == "deadline", "code": manifest.get("code")}


def analyse():
    rows = {(a, s): summarise(a, s) for a in ARMS for s in SEEDS}
    pairs = []
    for s in SEEDS:
        c, d = rows[("control", s)], rows[("docs-heavy", s)]
        pairs.append({"seed": s, "gain": c["best_docs_bpb"] - d["best_docs_bpb"],
                      "chat_change": (d["chat_bpb_at_best"] or 0) - (c["chat_bpb_at_best"] or 0)})
    wins = sum(p["gain"] > 0 for p in pairs)
    med_gain = statistics.median(p["gain"] for p in pairs)
    med_chat = statistics.median(p["chat_change"] for p in pairs)
    c1, c2, c3 = wins >= WINS_NEEDED, med_gain >= MIN_GAIN, med_chat <= GUARD
    verdict = "PASS" if (c1 and c2 and c3) else "FAIL"
    out = {"experiment": "nclm_mix1", "arms": ARMS, "seeds": SEEDS, "runs": list(rows.values()), "pairs": pairs,
           "criteria": {"C1_wins": f"{wins}/3", "C1": c1, "C2_median_gain": med_gain, "C2": c2,
                        "C3_median_chat_change": med_chat, "C3": c3},
           "verdict": verdict}
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=2)
    lines = [f"# NCLM-Mix-1 result: **{verdict}**", "",
             f"C1 docs-heavy wins {wins}/3 (need ≥ {WINS_NEEDED}) → {c1} · "
             f"C2 median gain {med_gain:+.3f} bpb (need ≥ {MIN_GAIN}) → {c2} · "
             f"C3 median chat change {med_chat:+.3f} bpb (need ≤ +{GUARD}) → {c3}", "",
             "| seed | control best | docs-heavy best | gain | chat change | control stop | docs-heavy stop |",
             "|---|---|---|---|---|---|---|"]
    for p in pairs:
        c, d = rows[("control", p["seed"])], rows[("docs-heavy", p["seed"])]
        lines.append(f"| {p['seed']} | {c['best_docs_bpb']:.3f} @ {c['best_step']} | {d['best_docs_bpb']:.3f} @ "
                     f"{d['best_step']} | {p['gain']:+.3f} | {p['chat_change']:+.3f} | {c['steps']} | {d['steps']} |")
    capped = [f"{r['arm']} s{r['seed']}" for r in rows.values() if r["hit_time_cap"]]
    if capped:
        lines += ["", "**Caveat:** these runs hit the 3-hour cap before early stopping, so their best may be "
                  "understated: " + ", ".join(capped) + "."]
    lines += ["", f"Unigram baseline {UNIGRAM} bpb; runs below it: "
              + (", ".join(f"{r['arm']} s{r['seed']}" for r in rows.values() if r["below_unigram"]) or "none") + ".",
              "", "Per-run detail, manifests and stop reasons: `results.json`."]
    open(os.path.join(HERE, "RESULT.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    analyse() if "--analyse" in sys.argv else launch()
