#!/usr/bin/env python3
"""NCLM-ARCH-1 driver and analysis. See PRE_REGISTRATION.md (committed before any run).

  python experiments/nclm_arch1/run.py --check      # preflight only: code, corrector fix, parameter counts, seeds
  python experiments/nclm_arch1/run.py              # launch the 16 runs (one at a time) and wait
  python experiments/nclm_arch1/run.py --analyse    # verdict -> results.json, RESULT.md
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
WORK = os.path.join(os.path.expanduser("~"), ".osiris", "experiments", "nclm_arch1")
ARMS = ("crsm", "standard")             # names in osiris_termux_console.ORGANISM_ARCHES
MIX = "0.5,0.3,0.2"                     # docs, lessons, archive: the trainer's default, set explicitly
SEEDS = list(range(200, 208))
PARALLEL = int(os.environ.get("NCLM_ARCH1_PARALLEL", "1"))
HOURS = 72.0                            # wall clock is not a stopping rule; MAX_STEPS is
MAX_STEPS = 12000
QUIET_LOAD = 3.0
N_PARAMS = {"crsm": 726304, "standard": 725760}
PREREG = "experiments/nclm_arch1/PRE_REGISTRATION.md"
WATCHED = ("osiris/nclm", "osiris_termux_console.py", "osiris_cli/train.py", "osiris_cli/living.py")
# pre-registered criterion
DELTA, GUARD, MIN_CHAT_WINDOWS = 0.05, 0.10, 8
WINS_NEEDED = math.ceil(2 * len(SEEDS) / 3)                                   # 6 of 8
T95 = {7: 1.895, 6: 1.943, 5: 2.015, 4: 2.132, 3: 2.353, 2: 2.920, 1: 6.314}  # one-sided 95 % t quantiles


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True).stdout.strip()


def run_dirs(arm, seed):
    tag = f"{arm}_s{seed}"
    return os.path.join(WORK, "ckpt", tag), os.path.join(WORK, "runs", tag), os.path.join(WORK, "logs", tag + ".log")


def preflight():
    """Refuse to launch on the wrong code, a missing corrector fix, or a used seed."""
    sys.path.insert(0, REPO)
    import numpy as np

    import osiris.nclm
    import osiris_termux_console as otc
    from osiris.nclm import cross_entropy_loss
    from osiris.nclm.autograd import no_grad
    where = os.path.dirname(os.path.dirname(os.path.abspath(osiris.nclm.__file__)))
    if where != REPO:
        raise SystemExit(f"osiris.nclm imported from {where}, not {REPO} (see nclm_mix1/EXECUTION.md)")
    reg = git("log", "--diff-filter=A", "--format=%H", "--", PREREG)
    if not reg:
        raise SystemExit("PRE_REGISTRATION.md is not committed")
    changed = "\n".join(filter(None, (git("diff", "--name-only", reg, "HEAD", "--", *WATCHED),
                                      git("status", "--porcelain", "--", *WATCHED))))
    if changed:
        raise SystemExit("model or trainer code differs from the pre-registration commit:\n" + changed)
    data = np.frombuffer(open(os.path.join(REPO, "README.md"), "rb").read()[:128], dtype=np.uint8).astype(np.int64)
    x, y = data[None, :-1], data[None, 1:]
    params = {}
    for arm in ARMS:
        np.random.seed(0)
        model, _ = otc._organism_build(arm)
        params[arm] = model.num_parameters()
        if params[arm] != N_PARAMS[arm]:
            raise SystemExit(f"{arm}: {params[arm]} parameters, registered {N_PARAMS[arm]}")
        trained = float(cross_entropy_loss(model.forward(x), y).data)
        with no_grad():
            scored = float(cross_entropy_loss(model.forward(x), y).data)
        if abs(trained - scored) > 1e-5:
            raise SystemExit(f"{arm}: training and scoring passes differ ({trained:.5f} vs {scored:.5f}); "
                             "this code lacks the v4.5.2 corrector fix")
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
    info = {"prereg_commit": reg, "head": git("rev-parse", "HEAD"), "params": params}
    print("preflight", json.dumps(info), flush=True)
    return info


def freeze_inputs():
    """One snapshot of the corpus and lessons for every run (as NCLM-Mix-1); later launches check it."""
    snap = os.path.join(WORK, "inputs")
    record = os.path.join(WORK, "inputs.sha256.json")
    if not os.path.isdir(snap):
        os.makedirs(snap)
        live = os.path.join(os.path.expanduser("~"), ".osiris", "living")
        for name in ("corpus.json", "exchanges.jsonl", "distill.jsonl"):
            shutil.copy2(os.path.join(live, name), os.path.join(snap, name))
        sys.path.insert(0, REPO)
        from osiris_cli import train
        info = train.freeze_corpus(os.path.join(snap, "frozen_corpus.json"), living_home=snap, archive_roots=["."])
        print("frozen corpus", json.dumps(info), flush=True)
    digest = {n: hashlib.sha256(open(os.path.join(snap, n), "rb").read()).hexdigest()
              for n in sorted(os.listdir(snap))}
    if os.path.exists(record):
        if json.load(open(record)) != digest:
            raise SystemExit(f"{snap} changed since it was frozen; see {record}")
    else:
        json.dump(digest, open(record, "w"), indent=1)
    print("inputs", json.dumps(digest), flush=True)
    return snap


def finished(arm, seed):
    _, runs, _ = run_dirs(arm, seed)
    for path in glob.glob(os.path.join(runs, "*", "progress.jsonl")):
        if any(json.loads(line).get("kind") == "end" for line in open(path) if line.strip()):
            return True
    return False


def launch():
    preflight()
    snap = freeze_inputs()
    jobs = [(a, s) for s in SEEDS for a in ARMS if not finished(a, s)]
    running = []
    while jobs or running:
        while jobs and len(running) < PARALLEL:
            waited = 0
            while os.getloadavg()[0] > QUIET_LOAD:   # start only on a quiet machine (as NCLM-Mix-1)
                if waited % 600 == 0:
                    print(time.strftime("%H:%M:%S"), f"waiting: load {os.getloadavg()[0]:.1f} > {QUIET_LOAD}", flush=True)
                time.sleep(30)
                waited += 30
            arm, seed = jobs.pop(0)
            ckpt, runs, log = run_dirs(arm, seed)
            if os.path.exists(os.path.join(ckpt, "organism.npz")) or glob.glob(os.path.join(runs, "*", "progress.jsonl")):
                raise SystemExit(f"{arm} s{seed}: an unfinished run is in {ckpt} / {runs}; set it aside "
                                 "(EXECUTION.md) and relaunch")
            for d in (ckpt, runs, os.path.dirname(log)):
                os.makedirs(d, exist_ok=True)
            with open(os.path.join(ckpt, "arch.json"), "w", encoding="utf-8") as f:
                json.dump({"arch": arm}, f)     # read by _organism_build in the run, and by anyone who opens it later
            # PYTHONPATH = this repo only; no thread caps (nclm_mix1/EXECUTION.md, third launch)
            env = {k: v for k, v in os.environ.items() if k not in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")}
            env.update(OSIRIS_ORGANISM_HOME=ckpt, PYTHONPATH=REPO)
            cmd = [sys.executable, "-m", "osiris_cli.train", "--hours", str(HOURS), "--max-steps", str(MAX_STEPS),
                   "--all", "--distill", "0", "--seed", str(seed), "--mix", MIX, "--runs-home", runs, "--no-rescore",
                   "--living-home", snap, "--frozen-corpus", os.path.join(snap, "frozen_corpus.json")]
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


def _finite(v):
    return v is not None and math.isfinite(v)


def _num(v):
    return float("nan") if v is None else v


def summarise(arm, seed):
    _, runs, _ = run_dirs(arm, seed)
    [run_id] = sorted(d for d in os.listdir(runs) if os.path.isdir(os.path.join(runs, d)))[-1:]
    rows = [json.loads(line) for line in open(os.path.join(runs, run_id, "progress.jsonl")) if line.strip()]
    evals = [r for r in rows if r.get("kind") == "eval"]
    end = next((r for r in rows if r.get("kind") == "end"), {})
    manifest = json.load(open(os.path.join(runs, run_id, "manifest.json")))
    diverged = (any(not _finite(r.get("heldout_docs_bpb")) for r in evals)
                or any(r.get("kind") == "train" and not _finite(r.get("loss")) for r in rows))
    best = min((r for r in evals if _finite(r.get("heldout_docs_bpb"))), key=lambda r: r["heldout_docs_bpb"])
    model = manifest.get("model") or {}
    return {"arm": arm, "seed": seed, "run_id": run_id, "arch": model.get("arch"), "n_params": model.get("n_params"),
            "best_docs_bpb": best["heldout_docs_bpb"], "chat_bpb_at_best": best.get("heldout_chat_bpb"),
            "best_step": best["step"], "final_docs_bpb": evals[-1].get("heldout_docs_bpb") if evals else None,
            "unigram_docs_bpb": best.get("unigram_docs_bpb"), "unigram_chat_bpb": best.get("unigram_chat_bpb"),
            "stop_reason": end.get("reason"), "steps": end.get("steps"), "hours": end.get("hours"),
            "hit_step_cap": end.get("reason") in ("deadline", "max steps"), "diverged": diverged,
            "chat_windows": (manifest.get("eval_windows") or {}).get("chat", 0),
            "inputs": {k: manifest.get(k) for k in ("bytes", "chat_train", "chat_heldout", "distill_lessons")},
            "pool_weights": manifest.get("pool_weights"), "code": manifest.get("code"),
            "manifest_sha256": manifest.get("manifest_sha256")}


def problems(rows):
    """Validity (PRE_REGISTRATION.md): every run on its registered arm, the frozen inputs, the mix, one commit."""
    out = []
    ref = rows[(ARMS[0], SEEDS[0])]
    mix = [float(w) for w in MIX.split(",")]
    for (arm, seed), r in rows.items():
        tag = f"{arm} s{seed}"
        if r["arch"] != arm or r["n_params"] != N_PARAMS[arm]:
            out.append(f"{tag}: built {r['arch']} with {r['n_params']} parameters")
        if r["inputs"] != ref["inputs"]:
            out.append(f"{tag}: inputs differ from {ref['arm']} s{ref['seed']}")
        if r["pool_weights"] != mix:
            out.append(f"{tag}: pool weights {r['pool_weights']}")
        if (r["code"] or {}).get("git_head") != (ref["code"] or {}).get("git_head"):
            out.append(f"{tag}: code {(r['code'] or {}).get('git_head')} differs")
        if not r["stop_reason"]:
            out.append(f"{tag}: no end record")
    return out


def decide(pairs, chat_judged):
    """pairs: one per seed, {"seed", "gain": standard - crsm best docs bpb (+ favours crsm) or None when a run
    diverged, "winner": "crsm" | "standard" | None, "chat_change": crsm - standard held-out chat bpb at best}."""
    used = [p for p in pairs if p["gain"] is not None]
    excluded = len(pairs) - len(used)
    wins = {a: sum(p["winner"] == a for p in pairs) for a in ARMS}
    gains = [p["gain"] for p in used]
    n = len(gains)
    if excluded > 1:
        return {"verdict": "NO-DIFFERENCE", "label": "inconclusive: more than one pair has a diverged run",
                "n_pairs": n, "excluded_pairs": excluded, "wins": wins, "wins_needed": WINS_NEEDED,
                "mean_gain": statistics.mean(gains) if gains else None, "sd_gain": None,
                "one_sided_95": [None, None], "chat_judged": False, "mean_chat_change": None}
    mean = statistics.mean(gains)
    half = T95[n - 1] * statistics.stdev(gains) / math.sqrt(n)
    lo, hi = mean - half, mean + half
    chats = [p["chat_change"] for p in used if _finite(p["chat_change"])]
    chat_mean = statistics.mean(chats) if chat_judged and chats else None
    docs_pass = mean >= DELTA and lo > 0 and wins["crsm"] >= WINS_NEEDED
    docs_fail = mean <= -DELTA and hi < 0 and wins["standard"] >= WINS_NEEDED
    if docs_pass and (chat_mean is None or chat_mean <= GUARD):
        verdict, label = "PASS", "the CRSM arm predicts held-out documents better"
    elif docs_fail and (chat_mean is None or chat_mean >= -GUARD):
        verdict, label = "FAIL", "the standard arm predicts held-out documents better"
    elif docs_pass or docs_fail:
        verdict, label = "NO-DIFFERENCE", "mixed: documents favour one arm, held-out chat the other beyond the guard"
    elif -DELTA < lo and hi < DELTA:
        verdict, label = "NO-DIFFERENCE", f"equivalent within ±{DELTA} bits/byte"
    else:
        verdict, label = "NO-DIFFERENCE", "inconclusive at this size"
    return {"verdict": verdict, "label": label, "n_pairs": n, "excluded_pairs": excluded, "wins": wins,
            "wins_needed": WINS_NEEDED, "mean_gain": mean, "sd_gain": statistics.stdev(gains),
            "one_sided_95": [lo, hi], "chat_judged": chat_mean is not None, "mean_chat_change": chat_mean}


def analyse():
    rows = {(a, s): summarise(a, s) for a in ARMS for s in SEEDS}
    bad = problems(rows)
    if bad:
        raise SystemExit("no verdict: invalid runs (re-run them per PRE_REGISTRATION.md)\n" + "\n".join(bad))
    pairs = []
    for s in SEEDS:
        c, d = rows[("crsm", s)], rows[("standard", s)]
        if c["diverged"] or d["diverged"]:
            winner = None if (c["diverged"] and d["diverged"]) else ("standard" if c["diverged"] else "crsm")
            pairs.append({"seed": s, "gain": None, "winner": winner, "chat_change": None})
            continue
        gain = d["best_docs_bpb"] - c["best_docs_bpb"]
        chat = (c["chat_bpb_at_best"] - d["chat_bpb_at_best"]
                if _finite(c["chat_bpb_at_best"]) and _finite(d["chat_bpb_at_best"]) else None)
        pairs.append({"seed": s, "gain": gain, "chat_change": chat,
                      "winner": "crsm" if gain > 0 else ("standard" if gain < 0 else None)})
    chat_judged = all(r["chat_windows"] >= MIN_CHAT_WINDOWS for r in rows.values())
    v = decide(pairs, chat_judged)
    out = {"experiment": "nclm_arch1", "arms": ARMS, "seeds": SEEDS, "mix": MIX, "runs": list(rows.values()),
           "pairs": pairs, "decision": v, "verdict": v["verdict"]}
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=2)
    lo, hi = v["one_sided_95"]
    lo, hi = _num(lo), _num(hi)
    chat = (f"not judged (fewer than {MIN_CHAT_WINDOWS} held-out chat windows)" if not v["chat_judged"]
            else f"{v['mean_chat_change']:+.3f} bpb (crsm − standard; PASS needs ≤ +{GUARD}, FAIL ≥ −{GUARD})")
    lines = [f"# NCLM-ARCH-1 result: **{v['verdict']}** — {v['label']}", "",
             f"Mean paired gain (standard − crsm, best held-out documents) {_num(v['mean_gain']):+.3f} "
             f"bits/byte, SD {_num(v['sd_gain']):.3f}, n = {v['n_pairs']}; one-sided 95 % bounds "
             f"[{lo:+.3f}, {hi:+.3f}] "
             f"(minimum effect ±{DELTA}). Wins: crsm {v['wins']['crsm']}, standard {v['wins']['standard']} "
             f"of {len(SEEDS)} (need {WINS_NEEDED}). Held-out chat guard: {chat}.", "",
             "| seed | crsm best @ step | standard best @ step | gain | chat change | crsm steps | standard steps |",
             "|---|---|---|---|---|---|---|"]
    for p in pairs:
        c, d = rows[("crsm", p["seed"])], rows[("standard", p["seed"])]
        g = "diverged" if p["gain"] is None else f"{p['gain']:+.3f}"
        ch = "n/a" if p["chat_change"] is None else f"{p['chat_change']:+.3f}"
        lines.append(f"| {p['seed']} | {c['best_docs_bpb']:.3f} @ {c['best_step']} | {d['best_docs_bpb']:.3f} @ "
                     f"{d['best_step']} | {g} | {ch} | {c['steps']} | {d['steps']} |")
    capped = [f"{r['arm']} s{r['seed']}" for r in rows.values() if r["hit_step_cap"]]
    if capped:
        lines += ["", "**Caveat:** these runs hit the 12,000-step cap before early stopping, so their best may be "
                  "understated: " + ", ".join(capped) + "."]
    below = [f"{r['arm']} s{r['seed']}" for r in rows.values() if r["best_docs_bpb"] < r["unigram_docs_bpb"]]
    ref = rows[(ARMS[0], SEEDS[0])]
    lines += ["", f"Unigram baseline (train split) {ref['unigram_docs_bpb']:.3f} bpb on held-out documents; runs "
              "below it: " + (", ".join(below) or "none") + ".",
              f"Parameters: crsm {N_PARAMS['crsm']:,}, standard {N_PARAMS['standard']:,}. "
              f"Code {(ref['code'] or {}).get('git_head')}.", "",
              "Per-run detail, manifests, final-eval scores and stop reasons: `results.json`."]
    open(os.path.join(HERE, "RESULT.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if "--analyse" in sys.argv:
        analyse()
    elif "--check" in sys.argv:
        preflight()
    else:
        launch()
