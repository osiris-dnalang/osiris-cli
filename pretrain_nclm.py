#!/usr/bin/env python3
"""
pretrain_nclm.py -- train the DD-focused NCLM checkpoint on the Aer-filtered elite corpus
(~/.osiris/data/dd_elite_corpus.jsonl, built by build_dd_corpus.py) rather than the hand-picked
textbook baselines warmup_nclm.py uses. Same separate-checkpoint discipline as warmup_nclm.py
and nclm_aer_evaluator.py: this trains ~/.osiris/nclm_organism/dd_search/dd_checkpoint.npz only,
never Engine 3's conversational checkpoint.

No Aer/proot dependency -- pure classical gradient descent on already-scored genome strings,
runs standalone under native Termux Python.

Usage: python3 pretrain_nclm.py [--steps-per-text N]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nclm_aer_evaluator as ev  # noqa: E402  (reuse model/checkpoint/condition code, don't duplicate)

CORPUS_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "data", "dd_elite_corpus.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps-per-text", type=int, default=40)
    args = ap.parse_args()

    if not os.path.exists(CORPUS_PATH):
        print(f"[!] No corpus found at {CORPUS_PATH}. Run build_dd_corpus.py first.")
        return 1

    seed_texts = []
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            seed_texts.append(rec["genome_key"])

    if not seed_texts:
        print(f"[!] {CORPUS_PATH} exists but is empty (build_dd_corpus.py found no candidates "
              f"above its fidelity threshold) -- honest outcome, nothing to train on. "
              f"Not touching the checkpoint.")
        return 1

    print(f"[*] Pretraining DD checkpoint on {len(seed_texts)} real Aer-verified elite "
          f"sequences ({args.steps_per_text} steps/text)...")

    model, optimizer = ev._build_model()
    had_prior = ev.load_checkpoint(model, optimizer)
    print(f"[*] {'Continuing from existing' if had_prior else 'Starting fresh (no existing)'} "
          f"DD checkpoint.")

    t0 = time.time()
    losses = ev._condition(model, optimizer, seed_texts, steps_per_text=args.steps_per_text)
    elapsed = time.time() - t0

    meta = {
        "source": "dd_elite_corpus.jsonl",
        "seed_count": len(seed_texts),
        "steps_per_text": args.steps_per_text,
        "total_steps": len(losses),
        "final_loss": losses[-1] if losses else None,
        "elapsed_s": round(elapsed, 1),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "continued_from_checkpoint": had_prior,
    }
    ev.save_checkpoint(model, optimizer, meta)

    final_loss_str = f"{meta['final_loss']:.4f}" if meta["final_loss"] is not None else "n/a"
    ev._telemetry(
        f"PRETRAIN source=elite_corpus n={meta['seed_count']} steps={meta['total_steps']} "
        f"final_loss={final_loss_str} elapsed_s={meta['elapsed_s']} [PROVENANCE: COMPUTED]"
    )
    print(f"[+] Pretrain complete: {meta['total_steps']} real gradient steps on elite corpus, "
          f"final loss {final_loss_str}, {meta['elapsed_s']}s.")
    print(f"[+] Checkpoint saved to {ev.CKPT_NPZ}")
    print("Final loss:", final_loss_str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
