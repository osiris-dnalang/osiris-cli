#!/usr/bin/env python3
"""
nclm_aer_evaluator.py -- NCLM-guided DD-sequence pilot vs. bridge's real baselines.

Reuses bridge/dnalang-core's actual genome space, DNA compiler, Aer noise model, and
verification-scoring function unmodified (see DD_SEARCH_PREREGISTRATION.md, committed
before this script was ever run, for the pre-registered criterion this implements).

Standalone: `python3 nclm_aer_evaluator.py --budget 8`
Also invoked by /dd search in the osiris REPL (subprocess, same convention as verify_ledger.py).
"""
import argparse
import json
import os
import random
import re
import sys
import time

ORGANISM_SRC = "/data/data/com.termux/files/home/crsm/osiris-cli"
DNALANG_SRC = "/data/data/com.termux/files/home/.osiris/src/dnalang-core"
ORGANISM_SIM_SRC = "/data/data/com.termux/files/home/.osiris/src/organism_sim"
BRIDGE_SRC = "/data/data/com.termux/files/home/.osiris/src/bridge"
for p in (ORGANISM_SRC, DNALANG_SRC, ORGANISM_SIM_SRC, BRIDGE_SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

DD_HOME = os.path.join(os.path.expanduser("~"), ".osiris", "nclm_organism", "dd_search")
TELEMETRY_HOME = os.path.join(os.path.expanduser("~"), ".osiris", "telemetry")
TELEMETRY_LOG = os.path.join(TELEMETRY_HOME, "dd_search.log")
RESULT_JSON = os.path.join(TELEMETRY_HOME, "dd_search_result.json")

# Same geometry as osiris's live Engine 3, but this is a SEPARATE checkpoint dedicated to
# DD-genome syntax -- mixing it into Engine 3's conversational checkpoint would corrupt both
# tasks. See DD_SEARCH_PREREGISTRATION.md for the reasoning.
GEOMETRY = dict(dim=128, n_layers=4, n_heads=4, ff_dim=256, max_seq_len=128)

GENOME_RE = re.compile(r"([IXY]{8})\|([IXY]{8})\|(0\.0|0\.25|0\.5)")

CKPT_NPZ = os.path.join(DD_HOME, "dd_checkpoint.npz")
CKPT_META = os.path.join(DD_HOME, "dd_checkpoint.json")


def save_checkpoint(model, optimizer, meta: dict):
    """Atomic checkpoint save (temp file + rename), same pattern as Engine 3's in bin/osiris."""
    import numpy as np
    os.makedirs(DD_HOME, exist_ok=True)
    arrays = {}
    for i, p in enumerate(model.parameters()):
        arrays[f"p{i}"] = p.data
        arrays[f"m{i}"] = optimizer._m[i]
        arrays[f"v{i}"] = optimizer._v[i]
    tmp = CKPT_NPZ + ".tmp"
    with open(tmp, "wb") as f:
        np.savez(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CKPT_NPZ)
    with open(CKPT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def load_checkpoint(model, optimizer) -> bool:
    """Best-effort checkpoint load. Returns True iff a checkpoint was found and applied."""
    import numpy as np
    if not (os.path.exists(CKPT_NPZ) and os.path.exists(CKPT_META)):
        return False
    try:
        with np.load(CKPT_NPZ) as blob:
            for i, p in enumerate(model.parameters()):
                p.data[...] = blob[f"p{i}"]
                optimizer._m[i][...] = blob[f"m{i}"]
                optimizer._v[i][...] = blob[f"v{i}"]
        return True
    except Exception as e:
        print(f"[!] DD checkpoint unreadable ({e}); using an unwarmed model.")
        return False


def build_seed_genomes(space, rng, mutants_per_baseline: int = 4, mutate_rate: float = 0.2):
    """Baselines plus light mutations, so training sees the *structure* of the space
    (alphabet, delimiter, even-parity-per-sublattice, allowed offsets) rather than
    memorizing a handful of exact strings verbatim."""
    seed_genomes = list(space.baselines().values())
    for base in list(space.baselines().values()):
        for _ in range(mutants_per_baseline):
            seed_genomes.append(space.mutate(base, rng, rate=mutate_rate))
    return seed_genomes


def _telemetry(line: str):
    os.makedirs(TELEMETRY_HOME, exist_ok=True)
    with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {line}\n")
        f.flush()


def _build_model():
    from osiris.nclm import AdamW, LRSchedule, SovereignConfig, SovereignTransformerV2
    cfg = SovereignConfig(vocab_size=256, dropout=0.0, torsion_lock=True,
                           phase_conjugate=True, fractal_embedding=False, **GEOMETRY)
    model = SovereignTransformerV2(cfg)
    optimizer = AdamW(params=model.parameters(), lr=3e-4, weight_decay=0.01,
                       schedule=LRSchedule(warmup_steps=10, total_steps=1000))
    return model, optimizer


def _condition(model, optimizer, seed_texts, steps_per_text=8):
    """Short real conditioning pass (actual gradient steps) on valid genome-key strings, so
    generation has better than near-zero odds of producing well-formed syntax. Not a claim
    of a trained search policy -- see DD_SEARCH_PREREGISTRATION.md."""
    import numpy as np
    from osiris.nclm import cross_entropy_loss
    from osiris.nclm.autograd import clip_grad_norm

    losses = []
    for text in seed_texts:
        raw = text.encode("utf-8")
        seq_len = min(GEOMETRY["max_seq_len"] - 1, len(raw) - 1)
        if seq_len < 4:
            continue
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.int64)
        x, y = data[:seq_len][None, :], data[1:seq_len + 1][None, :]
        for _ in range(steps_per_text):
            optimizer.zero_grad()
            logits = model.forward(x)
            loss = cross_entropy_loss(logits, y)
            loss.backward()
            clip_grad_norm(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.data))
    return losses


# --- Pivot (2026-09-22): end-to-end generation of the full "8chars|8chars|offset" string
# was tried with full-alphabet grammar-forcing plus a warm-up checkpoint (bin/warmup_nclm.py)
# and still produced 0/8 GENOME_RE-valid strings -- the model learned the right alphabet but
# not the rigid positional structure (delimiter placement, fixed field widths). Diagnosis:
# character-level masking constrains WHAT bytes can appear, not WHERE they must appear.
# Fix: separate search (NCLM explores sublattice pulse patterns) from syntax (a deterministic
# Python wrapper assembles the delimiters/offset field) -- the model is never asked to emit
# punctuation or field boundaries at all, so malformed syntax is structurally impossible.
SUBLATTICE_ALLOWED_BYTES = frozenset(ord(c) for c in "IXY")

# --- Parity masking (2026-09-22): DDSpace.screen() requires X-count EVEN *and* Y-count
# EVEN independently per sublattice (dnalang/evolve/space.py:56 -- not "total active pulses
# even", which was the original hypothesis). A single reserved final token can only correct
# one parity; if the first K-2 free tokens leave BOTH X-count and Y-count odd, one symbol
# can never fix both at once (X/Y/I each touch at most one of the two counts). Two reserved
# tokens are provably sufficient for any parity combination -- enumerated below -- so the
# last two positions are reserved instead of one. At the first reserved slot, the *set* of
# symbols consistent with at least one valid completion is computed and the model samples
# freely (masked logits, real softmax choice) among them; the second slot is then always
# exactly one symbol, forced by construction, not a free choice.
#
# needed_x, needed_y = (parity of X-count, parity of Y-count) among the first K-2 tokens.
# Table below: for each (needed_x, needed_y), which single-token choices at the first
# reserved slot leave a completable second slot, and what that second slot must be.
_PARITY_S6_OPTIONS = {
    (0, 0): {"I": "I", "X": "X", "Y": "Y"},   # any of I/X/Y works; forced partner shown
    (1, 0): {"I": "X", "X": "I"},             # Y at this slot would be uncompletable
    (0, 1): {"I": "Y", "Y": "I"},              # X at this slot would be uncompletable
    (1, 1): {"X": "Y", "Y": "X"},              # I at this slot would be uncompletable
}


def _sample_masked(model, ids, allowed_chars, rng, temperature=0.9, top_k=40):
    """One manual forward+sample step, masked to `allowed_chars` (subset of I/X/Y/etc as
    single-char strings). Mirrors SovereignTransformerV2.generate()'s own masking/sampling
    math exactly, but exposed per-step so parity constraints can pick the allowed set fresh
    at each of the last two positions -- generate() only supports one fixed mask for a
    whole call, which can't express "the allowed set depends on what came before"."""
    import numpy as np
    from osiris.nclm.autograd import no_grad

    ctx = ids[-model.config.max_seq_len:]
    x = np.array([ctx], dtype=np.int64)
    with no_grad():
        logits = model.forward(x)
    next_logits = logits.data[0, -1, :].copy()

    mask = np.zeros(model.config.vocab_size, dtype=bool)
    mask[[ord(c) for c in allowed_chars]] = True
    next_logits = np.where(mask, next_logits, -1e9)

    if len(allowed_chars) == 1:
        return ord(next(iter(allowed_chars)))  # forced slot: nothing to sample

    next_logits = next_logits / temperature
    if 0 < top_k < model.config.vocab_size:
        drop = np.argsort(next_logits)[:-top_k]
        next_logits[drop] = -1e9
    probs = np.exp(next_logits - np.max(next_logits))
    probs = probs / probs.sum()
    return int(np.random.choice(model.config.vocab_size, p=probs))


def _generate_sublattice(model, rng, seed) -> str:
    """Ask the model for exactly K=8 pulse tokens, constrained to {I,X,Y} only -- no
    delimiter, digit, or period ever enters this call's alphabet, so there is nothing for
    the model to get wrong positionally: the wrapper decides where '|' and the offset go.
    The final two tokens are jointly parity-masked (see _PARITY_S6_OPTIONS) so every
    returned sublattice passes DDSpace.screen()'s even-X/even-Y constraint by construction,
    with the model still choosing freely among whichever options remain valid."""
    import numpy as np
    np.random.seed(seed)
    model.eval()
    seed_char = rng.choice(["I", "X", "Y"])
    ids = list(seed_char.encode("utf-8"))
    K = 8
    free_steps = K - 2
    generated = []
    for _ in range(free_steps):
        tid = _sample_masked(model, ids, "IXY", rng)
        ids.append(tid)
        generated.append(chr(tid))

    x_count = generated.count("X")
    y_count = generated.count("Y")
    needed = (x_count % 2, y_count % 2)
    options = _PARITY_S6_OPTIONS[needed]

    s6_choices = "".join(options.keys())
    t6 = _sample_masked(model, ids, s6_choices, rng)
    ids.append(t6)
    s6 = chr(t6)
    generated.append(s6)

    s7 = options[s6]
    t7 = _sample_masked(model, ids, s7, rng)
    ids.append(t7)
    generated.append(chr(t7))

    model.train()
    return "".join(generated)


def _generate_dd_template(model, space, rng, seed, max_attempts=5):
    """Template-filling candidate generation: NCLM fills the two 8-pulse sublattices
    (search), a Python wrapper assembles 'even|odd|offset' deterministically (syntax) --
    see pivot note above. GENOME_RE match is now guaranteed by construction; the only
    thing that can still fail is DDSpace.screen()'s parity constraint (even X/Y counts
    per sublattice), which is a physics constraint, not a syntax one -- retry on that."""
    for attempt in range(max_attempts):
        even = _generate_sublattice(model, rng, seed * 1000 + attempt * 2)
        odd = _generate_sublattice(model, rng, seed * 1000 + attempt * 2 + 1)
        offset = rng.choice(space.offsets)
        g = {"even": list(even), "odd": list(odd), "offset": offset}
        assert GENOME_RE.fullmatch(space.key(g)), \
            f"template assembly produced non-matching key: {space.key(g)!r}"  # should be impossible
        if space.screen(g) is None:
            return g, False, space.key(g)
    return space.sample(rng), True, None


def run_pilot(budget: int = 8, seed: int = 0):
    from dnalang.evolve.space import DDSpace
    from bridge.compare import HARD, verify

    space = DDSpace(n_qubits=8, K=8)
    model, optimizer = _build_model()
    rng = random.Random(seed)

    _telemetry(
        "MODE template-filling (NCLM fills 2x8 pulse sublattices under {I,X,Y}-only grammar "
        "masking; Python wrapper assembles even|odd|offset deterministically) -- pivoted from "
        "end-to-end full-string generation after that approach scored 0/8 GENOME_RE-valid even "
        "with full-alphabet masking and warm-up training. See bin/nclm_aer_evaluator.py top of "
        "file for the fuller diagnosis. [PROVENANCE: COMPUTED]"
    )
    warmed_up = load_checkpoint(model, optimizer)
    if warmed_up:
        cond_losses = []
        print("[*] Loaded warmed-up DD checkpoint (see bin/warmup_nclm.py) -- "
              "skipping per-run conditioning.")
    else:
        # No warm-up checkpoint yet: fall back to the original per-run conditioning pass
        # (real result from before warmup_nclm.py existed: 32 steps/4 baselines alone
        # produced 0/8 valid generations -- see DD_SEARCH_PREREGISTRATION.md/report).
        seed_genomes = build_seed_genomes(space, rng)
        seed_texts = [space.key(g) for g in seed_genomes]
        cond_losses = _condition(model, optimizer, seed_texts, steps_per_text=12)

    candidates = []
    for i in range(budget):
        g, fell_back, raw_text = _generate_dd_template(model, space, rng, seed=seed + i)
        score = verify(space, g, HARD, shots=1024, batches=8, seed=90_000 + seed + i)
        rec = {"index": i, "genome_key": space.key(g), "fallback_used": fell_back,
               "verify_score": score}
        candidates.append(rec)
        _telemetry(
            f"CANDIDATE index={i} genome={space.key(g)} verify={score:.4f} "
            f"fallback={fell_back} [PROVENANCE: SIMULATED]"
        )

    best = max(candidates, key=lambda r: r["verify_score"])
    baseline_key = "xy4_stag"
    baseline_genome = space.baselines()[baseline_key]
    baseline_score = verify(space, baseline_genome, HARD, shots=1024, batches=8, seed=90_000 + seed)

    margin = 0.02
    verdict = "PASS" if best["verify_score"] >= baseline_score + margin else "NULL"

    result = {
        "budget": budget, "seed": seed,
        "conditioning_final_loss": cond_losses[-1] if cond_losses else None,
        "candidates": candidates, "best": best,
        "baseline": baseline_key, "baseline_score": baseline_score,
        "margin": margin, "verdict": verdict,
    }
    os.makedirs(TELEMETRY_HOME, exist_ok=True)
    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    _telemetry(
        f"VERDICT {verdict} best={best['genome_key']} best_score={best['verify_score']:.4f} "
        f"baseline={baseline_key} baseline_score={baseline_score:.4f} margin={margin} "
        f"[PROVENANCE: SIMULATED]"
    )
    return result


def _parse_genome_key(s: str):
    m = GENOME_RE.fullmatch(s.strip())
    if not m:
        raise ValueError(f"not a valid genome key: {s!r}")
    even, odd, offset = m.group(1), m.group(2), float(m.group(3))
    return {"even": list(even), "odd": list(odd), "offset": offset}


def evaluate_sequences(sequences, seed: int = 0, source: str = "external"):
    """Evaluate a list of pre-made genome-key strings (e.g. from
    algorithmic_dd_generator.py) through the SAME real Aer evaluation path and
    baseline comparison as run_pilot() -- reused, not duplicated. Each result is
    logged with `source=<source>` so /dd search (NCLM-sourced) and /dd programmatic
    (algorithmically-sourced) candidates are distinguishable in the shared ledger
    without needing a new provenance tag (a fidelity score from Aer is correctly
    [PROVENANCE: SIMULATED] regardless of what generated the candidate)."""
    from dnalang.evolve.space import DDSpace
    from bridge.compare import HARD, verify

    space = DDSpace(n_qubits=8, K=8)
    candidates = []
    for i, s in enumerate(sequences):
        g = _parse_genome_key(s)
        score = verify(space, g, HARD, shots=1024, batches=8, seed=90_000 + seed + i)
        rec = {"index": i, "genome_key": space.key(g), "verify_score": score}
        candidates.append(rec)
        _telemetry(
            f"CANDIDATE index={i} genome={space.key(g)} verify={score:.4f} "
            f"source={source} [PROVENANCE: SIMULATED]"
        )

    best = max(candidates, key=lambda r: r["verify_score"])
    baseline_key = "xy4_stag"
    baseline_genome = space.baselines()[baseline_key]
    baseline_score = verify(space, baseline_genome, HARD, shots=1024, batches=8, seed=90_000 + seed)

    margin = 0.02
    verdict = "PASS" if best["verify_score"] >= baseline_score + margin else "NULL"

    result = {
        "budget": len(sequences), "seed": seed, "source": source,
        "candidates": candidates, "best": best,
        "baseline": baseline_key, "baseline_score": baseline_score,
        "margin": margin, "verdict": verdict,
    }
    _telemetry(
        f"VERDICT {verdict} source={source} best={best['genome_key']} "
        f"best_score={best['verify_score']:.4f} baseline={baseline_key} "
        f"baseline_score={baseline_score:.4f} margin={margin} [PROVENANCE: SIMULATED]"
    )
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sequences-file", default=None,
                     help="Evaluate pre-made genome-key strings (one per line, "
                          "EVEN|ODD|OFFSET format) instead of NCLM-generating them.")
    ap.add_argument("--source", default="nclm",
                     help="Label for the ledger's source= field (e.g. 'algorithmic').")
    args = ap.parse_args()

    if args.sequences_file:
        with open(args.sequences_file, encoding="utf-8") as f:
            sequences = [ln.strip() for ln in f if ln.strip()]
        result = evaluate_sequences(sequences, seed=args.seed, source=args.source)
        print(f"\nDD evaluation ({args.source}) -- {len(sequences)} sequence(s)")
    else:
        result = run_pilot(args.budget, args.seed)
        print(f"\nNCLM DD-search pilot -- budget={result['budget']}")

    for c in result["candidates"]:
        flag = " (fallback: random sample, NCLM did not produce valid syntax)" if c.get("fallback_used") else ""
        print(f"  [{c['index']}] {c['genome_key']}  verify={c['verify_score']:.4f}{flag}")
    print(f"\nBaseline ({result['baseline']}): {result['baseline_score']:.4f}")
    print(f"Best candidate: {result['best']['genome_key']}  verify={result['best']['verify_score']:.4f}")
    print(f"Pre-registered criterion: best >= baseline + {result['margin']}")
    print(f"VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
