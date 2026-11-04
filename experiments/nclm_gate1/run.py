#!/usr/bin/env python3
"""NCLM-GATE-1 driver and Speaking Gate monitor. See PRE_REGISTRATION.md.

  python experiments/nclm_gate1/run.py --check      # preflight: parameters, checkpoint, inputs
  python experiments/nclm_gate1/run.py              # launch 16,000-step training sweep
  python experiments/nclm_gate1/run.py --analyse    # generate results.json and RESULT.md
"""

import glob
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_gate1")
SOURCE_CKPT = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_scale1", "ckpt", "standard_scale512_s301")
INPUTS_SOURCE = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_scale1", "inputs")

ARCH = "standard_scale512"
N_PARAMS = 4077568
MAX_STEPS = 16000
BATCH_SIZE = 2
SEQ_LEN = 512
MIX = "0.1,0.8,0.1"
SPEAK_GATE_BPB = 2.0000
SEED = 301


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True).stdout.strip()


def run_dirs():
    tag = "gate_standard512"
    return os.path.join(WORK, "ckpt", tag), os.path.join(WORK, "runs", tag), os.path.join(WORK, "logs", tag + ".log")


def preflight():
    """Verify parameters, configuration integrity, source checkpoint, and inputs."""
    sys.path.insert(0, REPO)
    import osiris_termux_console as otc

    model, _ = otc._organism_build(ARCH)
    params = model.num_parameters()
    if params != N_PARAMS:
        raise SystemExit(f"{ARCH}: {params} parameters, expected {N_PARAMS}")
    if model.config.max_seq_len != SEQ_LEN:
        raise SystemExit(f"{ARCH}: max_seq_len is {model.config.max_seq_len}, expected {SEQ_LEN}")

    src_weights = os.path.join(SOURCE_CKPT, "organism.best.npz")
    src_meta = os.path.join(SOURCE_CKPT, "organism.best.json")
    if not (os.path.exists(src_weights) and os.path.exists(src_meta)):
        raise SystemExit(f"Source checkpoint missing: {src_weights} or {src_meta}")

    frozen_corpus = os.path.join(INPUTS_SOURCE, "frozen_corpus.json")
    if not os.path.exists(frozen_corpus):
        raise SystemExit(f"Source frozen corpus missing: {frozen_corpus}")

    info = {
        "status": "preflight_ok",
        "arch": ARCH,
        "params": params,
        "max_seq_len": SEQ_LEN,
        "batch_size": BATCH_SIZE,
        "mix": MIX,
        "max_steps": MAX_STEPS,
        "source_checkpoint": src_weights,
        "speaking_gate_target_bpb": SPEAK_GATE_BPB,
        "head": git("rev-parse", "HEAD")
    }
    print("preflight", json.dumps(info), flush=True)
    return info


def setup_workspace():
    """Initialize inputs and starting checkpoint from standard_scale512_s301."""
    ckpt_dir, runs_dir, log_file = run_dirs()
    os.makedirs(ckpt_dir, exist_ok=True)
    os.makedirs(runs_dir, exist_ok=True)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    snap = os.path.join(WORK, "inputs")
    os.makedirs(snap, exist_ok=True)
    for item in os.listdir(INPUTS_SOURCE):
        src_file = os.path.join(INPUTS_SOURCE, item)
        dst_file = os.path.join(snap, item)
        if os.path.isfile(src_file) and not os.path.exists(dst_file):
            shutil.copy2(src_file, dst_file)

    target_weights = os.path.join(ckpt_dir, "organism.npz")
    target_meta = os.path.join(ckpt_dir, "organism.json")
    target_arch = os.path.join(ckpt_dir, "arch.json")

    if not os.path.exists(target_weights):
        shutil.copy2(os.path.join(SOURCE_CKPT, "organism.best.npz"), target_weights)
        shutil.copy2(os.path.join(SOURCE_CKPT, "organism.best.json"), target_meta)
        # Also copy best weights as baseline
        shutil.copy2(os.path.join(SOURCE_CKPT, "organism.best.npz"), os.path.join(ckpt_dir, "organism.best.npz"))
        shutil.copy2(os.path.join(SOURCE_CKPT, "organism.best.json"), os.path.join(ckpt_dir, "organism.best.json"))
        with open(target_arch, "w", encoding="utf-8") as f:
            json.dump({"arch": ARCH}, f, indent=2)
        print(f"Initialized starting weights from step 6,000 checkpoint: {target_weights}")

    # Remove any stale lock
    lock = os.path.join(ckpt_dir, "train.lock")
    if os.path.exists(lock):
        try:
            pid = json.load(open(lock)).get("pid")
            os.kill(pid, 0)
        except (OSError, ValueError):
            os.remove(lock)

    return snap, ckpt_dir, runs_dir, log_file


def is_finished():
    _, runs_dir, _ = run_dirs()
    for p in glob.glob(os.path.join(runs_dir, "*", "progress.jsonl")):
        for line in open(p):
            if line.strip() and json.loads(line).get("kind") == "end":
                return True
    return False


def launch():
    preflight()
    snap, ckpt_dir, runs_dir, log_file = setup_workspace()

    if is_finished():
        print("Run already finished. Use --analyse to inspect.")
        return

    env = {k: v for k, v in os.environ.items() if k not in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")}
    env.update(OSIRIS_ORGANISM_HOME=ckpt_dir, PYTHONPATH=REPO)

    cmd = [
        sys.executable, "-m", "osiris_cli.train",
        "--hours", "72.0",
        "--batch", str(BATCH_SIZE),
        "--seq", str(SEQ_LEN),
        "--max-steps", str(MAX_STEPS),
        "--all", "--distill", "0",
        "--seed", str(SEED),
        "--mix", MIX,
        "--patience", "0",
        "--runs-home", runs_dir,
        "--no-rescore",
        "--living-home", snap,
        "--frozen-corpus", os.path.join(snap, "frozen_corpus.json")
    ]

    f_log = open(log_file, "a")
    p = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=f_log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    print(time.strftime("%H:%M:%S"), f"start {ARCH} seed {SEED} pid {p.pid}", flush=True)

    gate_tripped = False
    seen_steps = set()

    try:
        while p.poll() is None:
            time.sleep(20)
            for p_file in glob.glob(os.path.join(runs_dir, "*", "progress.jsonl")):
                for line in open(p_file):
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("kind") == "eval":
                        s = rec.get("step")
                        if s not in seen_steps:
                            seen_steps.add(s)
                            c_bpb = rec.get("heldout_chat_bpb")
                            d_bpb = rec.get("heldout_docs_bpb")
                            c_str = f"{c_bpb:.4f}" if c_bpb is not None else "n/a"
                            d_str = f"{d_bpb:.4f}" if d_bpb is not None else "n/a"
                            print(f"[{time.strftime('%H:%M:%S')}] eval step {s}: chat {c_str} bpb · docs {d_str} bpb", flush=True)
                            if c_bpb is not None and c_bpb <= SPEAK_GATE_BPB and not gate_tripped:
                                gate_tripped = True
                                print(f"\n{'='*70}\n*** SYS-026 SPEAKING GATE OPEN: heldout_chat_bpb = {c_bpb:.4f} <= {SPEAK_GATE_BPB:.4f} ***\n{'='*70}\n", flush=True)
    finally:
        f_log.close()

    print(time.strftime("%H:%M:%S"), f"done {ARCH} exit {p.returncode}", flush=True)


def analyse():
    _, runs_dir, _ = run_dirs()
    evals = []
    end_rec = None
    for p_file in sorted(glob.glob(os.path.join(runs_dir, "*", "progress.jsonl"))):
        for line in open(p_file):
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("kind") == "eval":
                evals.append(rec)
            elif rec.get("kind") == "end":
                end_rec = rec

    if not evals:
        print("No evaluation records found.")
        return

    best_chat = min(e.get("heldout_chat_bpb", 999.0) for e in evals)
    best_docs = min(e.get("heldout_docs_bpb", 999.0) for e in evals)
    best_chat_ev = min(evals, key=lambda e: e.get("heldout_chat_bpb", 999.0))
    best_docs_ev = min(evals, key=lambda e: e.get("heldout_docs_bpb", 999.0))
    gate_open = best_chat <= SPEAK_GATE_BPB

    summary = {
        "experiment": "NCLM-GATE-1",
        "arch": ARCH,
        "n_params": N_PARAMS,
        "max_seq_len": SEQ_LEN,
        "mix": MIX,
        "initial_step": 6000,
        "max_steps": MAX_STEPS,
        "start_eval": {
            "chat_bpb": evals[0].get("heldout_chat_bpb"),
            "docs_bpb": evals[0].get("heldout_docs_bpb"),
            "step": evals[0].get("step")
        },
        "best_chat": {
            "bpb": best_chat,
            "step": best_chat_ev.get("step")
        },
        "best_docs": {
            "bpb": best_docs,
            "step": best_docs_ev.get("step")
        },
        "final_eval": {
            "chat_bpb": evals[-1].get("heldout_chat_bpb"),
            "docs_bpb": evals[-1].get("heldout_docs_bpb"),
            "step": evals[-1].get("step")
        },
        "speaking_gate_bpb_target": SPEAK_GATE_BPB,
        "speaking_gate_status": "OPEN (AUTONOMOUS)" if gate_open else "CLOSED",
        "total_evals": len(evals),
        "stop_reason": end_rec.get("reason") if end_rec else None
    }

    res_path = os.path.join(HERE, "results.json")
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    status_str = "**OPEN (AUTONOMOUS)**" if gate_open else "**CLOSED**"
    md_lines = [
        "# NCLM-GATE-1 Result: SYS-026 Speaking Gate Evaluation",
        "",
        f"- **Model Architecture:** `{ARCH}` (4,077,568 params, 512-byte context)",
        f"- **Curriculum Pool Mix:** `{MIX}` (10% docs, 80% chat lessons, 10% archive)",
        f"- **Initial Checkpoint:** Step 6,000 (`standard_scale512_s301`)",
        f"- **Best Held-Out Chat BPB:** **`{best_chat:.4f}`** @ step {best_chat_ev.get('step')}",
        f"- **Best Held-Out Docs BPB:** **`{best_docs:.4f}`** @ step {best_docs_ev.get('step')}",
        f"- **SYS-026 Speaking Gate Status:** {status_str} (Threshold: $\\le {SPEAK_GATE_BPB:.4f}$ BPB)",
        "",
        "### Training Trajectory",
        "",
        "| Step | Held-Out Chat BPB | Held-Out Docs BPB | Gate Status |",
        "| :---: | :---: | :---: | :---: |"
    ]
    for ev in evals:
        s = ev.get("step")
        c = ev.get("heldout_chat_bpb")
        d = ev.get("heldout_docs_bpb")
        c_str = f"{c:.4f}" if c is not None else "n/a"
        d_str = f"{d:.4f}" if d is not None else "n/a"
        st = "OPEN" if c is not None and c <= SPEAK_GATE_BPB else "CLOSED"
        md_lines.append(f"| {s} | {c_str} | {d_str} | {st} |")

    md_path = os.path.join(HERE, "RESULT.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Results written to {res_path} and {md_path}")
    print(f"SYS-026 Speaking Gate: {status_str} (Best Chat: {best_chat:.4f} BPB)")


if __name__ == "__main__":
    if "--check" in sys.argv:
        preflight()
    elif "--analyse" in sys.argv:
        analyse()
    else:
        launch()
