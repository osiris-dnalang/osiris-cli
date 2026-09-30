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
PARALLEL = 3
HOURS = 3.0
UNIGRAM = 5.026
# pre-registered criterion
WINS_NEEDED, MIN_GAIN, GUARD = 2, 0.10, 0.10


def run_dirs(arm, seed):
    tag = f"{arm}_s{seed}"
    return os.path.join(WORK, "ckpt", tag), os.path.join(WORK, "runs", tag), os.path.join(WORK, "logs", tag + ".log")


def launch():
    jobs = [(a, s) for s in SEEDS for a in ARMS]
    running = []
    while jobs or running:
        while jobs and len(running) < PARALLEL:
            arm, seed = jobs.pop(0)
            ckpt, runs, log = run_dirs(arm, seed)
            for d in (ckpt, runs, os.path.dirname(log)):
                os.makedirs(d, exist_ok=True)
            env = dict(os.environ, OSIRIS_ORGANISM_HOME=ckpt, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
            cmd = [sys.executable, "-m", "osiris_cli.train", "--hours", str(HOURS), "--all", "--distill", "0",
                   "--seed", str(seed), "--mix", ARMS[arm], "--runs-home", runs, "--no-rescore"]
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
            "manifest_sha256": manifest.get("manifest_sha256"), "below_unigram": best["heldout_docs_bpb"] < UNIGRAM}


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
    lines += ["", f"Unigram baseline {UNIGRAM} bpb; runs below it: "
              + (", ".join(f"{r['arm']} s{r['seed']}" for r in rows.values() if r["below_unigram"]) or "none") + ".",
              "", "Per-run detail, manifests and stop reasons: `results.json`."]
    open(os.path.join(HERE, "RESULT.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    analyse() if "--analyse" in sys.argv else launch()
