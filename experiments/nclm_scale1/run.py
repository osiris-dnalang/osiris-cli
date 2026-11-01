#!/usr/bin/env python3
"""NCLM-SCALE-1 driver and analysis. See PRE_REGISTRATION.md.

  python experiments/nclm_scale1/run.py --check      # preflight only: shapes, parameter counts, seeds
  python experiments/nclm_scale1/run.py              # launch the scaling runs and wait
  python experiments/nclm_scale1/run.py --analyse    # verdict -> results.json, RESULT.md
"""

import glob
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_scale1")
INPUTS_SOURCE = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_arch1", "inputs")

ARMS = ("standard_scale512", "crsm_scale512")
SEEDS = [300, 301]
MAX_STEPS = 6000
QUIET_LOAD = 3.0
SPEAK_GATE_BPB = 2.000

N_PARAMS = {
    "standard_scale512": 4077568,
    "crsm_scale512": 4079152,
}


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True).stdout.strip()


def run_dirs(arm, seed):
    tag = f"{arm}_s{seed}"
    return os.path.join(WORK, "ckpt", tag), os.path.join(WORK, "runs", tag), os.path.join(WORK, "logs", tag + ".log")


def preflight():
    """Verify parameters, configuration integrity, and seed freshness."""
    sys.path.insert(0, REPO)
    import osiris_termux_console as otc

    params = {}
    for arm in ARMS:
        model, _ = otc._organism_build(arm)
        params[arm] = model.num_parameters()
        if params[arm] != N_PARAMS[arm]:
            raise SystemExit(f"{arm}: {params[arm]} parameters, expected {N_PARAMS[arm]}")
        if model.config.max_seq_len != 512:
            raise SystemExit(f"{arm}: max_seq_len is {model.config.max_seq_len}, expected 512")

    home = os.path.join(os.path.expanduser("~"), ".osiris")
    used = set()
    for m in (glob.glob(os.path.join(home, "living", "train_runs", "*", "manifest.json"))
              + glob.glob(os.path.join(home, "experiments", "*", "runs", "*", "*", "manifest.json"))):
        if m.startswith(WORK + os.sep):
            continue
        try:
            used.add(json.load(open(m)).get("seed"))
        except (OSError, ValueError):
            pass
    if used & set(SEEDS):
        raise SystemExit(f"seeds already used by earlier runs: {sorted(used & set(SEEDS))}")

    info = {"status": "preflight_ok", "params": params, "seeds": SEEDS, "max_steps": MAX_STEPS, "seq": 512}
    print("preflight", json.dumps(info), flush=True)
    return info


def setup_inputs():
    """Bind to frozen inputs snapshot from NCLM-ARCH-1."""
    snap = os.path.join(WORK, "inputs")
    if not os.path.isdir(snap):
        os.makedirs(snap, exist_ok=True)
        for item in os.listdir(INPUTS_SOURCE):
            src_file = os.path.join(INPUTS_SOURCE, item)
            dst_file = os.path.join(snap, item)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
    return snap


def finished(arm, seed):
    _, runs, _ = run_dirs(arm, seed)
    for path in glob.glob(os.path.join(runs, "*", "progress.jsonl")):
        if any(json.loads(line).get("kind") == "end" for line in open(path) if line.strip()):
            return True
    return False


def launch():
    preflight()
    snap = setup_inputs()
    jobs = [(a, s) for s in SEEDS for a in ARMS if not finished(a, s)]
    running = []

    print(f"NCLM-SCALE-1 starting: {len(jobs)} runs queued.", flush=True)
    while jobs or running:
        while jobs and len(running) < 1:
            waited = 0
            while os.getloadavg()[0] > QUIET_LOAD:
                if waited % 600 == 0:
                    print(time.strftime("%H:%M:%S"), f"waiting for quiet load: {os.getloadavg()[0]:.2f} > {QUIET_LOAD}", flush=True)
                time.sleep(15)
                waited += 15

            arm, seed = jobs.pop(0)
            ckpt, runs, log = run_dirs(arm, seed)
            for d in (ckpt, runs, os.path.dirname(log)):
                os.makedirs(d, exist_ok=True)

            with open(os.path.join(ckpt, "arch.json"), "w", encoding="utf-8") as f:
                json.dump({"arch": arm}, f, indent=2)

            env = {k: v for k, v in os.environ.items() if k not in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")}
            env.update(OSIRIS_ORGANISM_HOME=ckpt, PYTHONPATH=REPO)

            cmd = [
                sys.executable, "-m", "osiris_cli.train",
                "--hours", "72.0",
                "--batch", "2",
                "--seq", "512",
                "--max-steps", str(MAX_STEPS),
                "--all", "--distill", "0",
                "--seed", str(seed),
                "--mix", "0.5,0.3,0.2",
                "--runs-home", runs,
                "--no-rescore",
                "--living-home", snap,
                "--frozen-corpus", os.path.join(snap, "frozen_corpus.json")
            ]

            f_log = open(log, "a")
            p = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=f_log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            running.append((arm, seed, p, f_log))
            print(time.strftime("%H:%M:%S"), "start", arm, seed, "pid", p.pid, flush=True)

        for item in list(running):
            arm, seed, p, f_log = item
            if p.poll() is not None:
                f_log.close()
                running.remove(item)
                print(time.strftime("%H:%M:%S"), "done", arm, seed, "exit", p.returncode, flush=True)
        time.sleep(15)


def analyse():
    rows = {}
    for arm in ARMS:
        for seed in SEEDS:
            _, runs, _ = run_dirs(arm, seed)
            evals = []
            for p in glob.glob(os.path.join(runs, "*", "progress.jsonl")):
                for line in open(p):
                    if line.strip():
                        rec = json.loads(line)
                        if rec.get("kind") == "eval":
                            evals.append(rec)
            if evals:
                best_chat = min(e.get("heldout_chat_bpb", 999.0) for e in evals)
                best_docs = min(e.get("heldout_docs_bpb", 999.0) for e in evals)
                rows[(arm, seed)] = {
                    "arm": arm, "seed": seed, "best_chat_bpb": best_chat,
                    "best_docs_bpb": best_docs, "eval_count": len(evals),
                    "speaks_autonomously": (best_chat <= SPEAK_GATE_BPB)
                }

    res_path = os.path.join(HERE, "results.json")
    res_rows = {f"{k[0]}_s{k[1]}": v for k, v in rows.items()}
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(res_rows, f, indent=2, default=str)

    md_lines = [
        "# NCLM-SCALE-1 Results (< 2.0 BPB Target)",
        "",
        "| Arm | Seed | Best Held-Out Chat BPB | Best Held-Out Docs BPB | Speaking Gate (< 2.0 BPB) |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for (arm, seed), data in sorted(rows.items()):
        status = "OPEN" if data["speaks_autonomously"] else "CLOSED"
        md_lines.append(f"| `{arm}` | {seed} | {data['best_chat_bpb']:.4f} | {data['best_docs_bpb']:.4f} | **{status}** |")

    md_path = os.path.join(HERE, "RESULT.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Analysis saved to {res_path} and {md_path}")


if __name__ == "__main__":
    if "--check" in sys.argv:
        preflight()
    elif "--analyse" in sys.argv:
        analyse()
    else:
        launch()
