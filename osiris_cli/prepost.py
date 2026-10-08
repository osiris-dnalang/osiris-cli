"""Paired pre/post scoring of OSIRIS's core on held-out exchanges.

The live speaking gate scores each held-out exchange once, at whatever step the
core had reached when it arrived. That mixes two things -- how hard the item is
and how far training had got -- so a falling average cannot be read as learning.
Here every held-out item is scored twice by the same procedure: by a frozen
snapshot taken before the training window ("pre") and by the core after it
("post"). The unit of analysis is the item:

    d_j = bpb_pre(j) - bpb_post(j)      positive = the trained core predicts j better

Template confound: mentor replies repeat long stretches ("I'm OSIRIS, the living
language model being built by ..."). A drop in held-out bpb can come from
memorising that template rather than from anything general, so each item is also
scored with every byte that lies inside a TEMPLATE_SPAN-byte string occurring in
the training text masked out, and the covered fraction is reported.

Nothing here writes to the live checkpoint. Snapshots are files with a sha256.

    python -m osiris_cli.prepost freeze DIR                      # copy the live core as "pre"
    python -m osiris_cli.prepost score --pre DIR --post DIR|live --exchanges FILE --out FILE
    python -m osiris_cli.prepost plan RESULTS.json --mpe 0.10    # held-out items needed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
from statistics import NormalDist
from typing import Dict, List, Optional, Sequence

TEMPLATE_SPAN = 24          # bytes; a shared string this long is template, not prediction
BOOTSTRAP = 10000
BOOTSTRAP_SEED = 0
LN2 = math.log(2)


# ---------------------------------------------------------------------------
# Exchanges and the training/held-out split
# ---------------------------------------------------------------------------

def read_exchanges(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def lesson(row: dict) -> str:
    """The text the live core trains on for one exchange (Osiris.converse)."""
    return f"User: {row['user']}\nOSIRIS: {row['reply']}\n"


def split(rows: Sequence[dict]):
    """(training lessons, held-out items) exactly as the exchange log marked them.
    Interrupted or pasted exchanges (learnable False) are neither."""
    train = [lesson(r) for r in rows if not r.get("heldout") and r.get("learnable", True)]
    held = [r for r in rows if r.get("heldout") and r.get("learnable", True)]
    return train, held


# ---------------------------------------------------------------------------
# Template coverage
# ---------------------------------------------------------------------------

def template_mask(text: bytes, train: bytes, span: int = TEMPLATE_SPAN) -> List[bool]:
    """mask[i] is True when byte i lies inside a span-byte string that also occurs
    in the training text."""
    grams = {train[i:i + span] for i in range(len(train) - span + 1)}
    mask = [False] * len(text)
    for i in range(len(text) - span + 1):
        if text[i:i + span] in grams:
            for k in range(i, i + span):
                mask[k] = True
    return mask


# ---------------------------------------------------------------------------
# Scoring (needs numpy and osiris.nclm)
# ---------------------------------------------------------------------------

def windows(data, span: int, limit: int):
    """(x, y) teacher-forcing windows over a byte array -- the live core's scheme."""
    out = []
    for start in range(0, max(0, len(data) - 1), span - 1):
        chunk = data[start:start + span]
        if len(chunk) >= 8:
            out.append((start, chunk[:-1][None, :], chunk[1:][None, :]))
        if len(out) >= limit:
            break
    return out


def byte_nats(model, text: str, span: int) -> Dict[int, float]:
    """Loss in nats for every predicted byte position of text (no training)."""
    import numpy as np
    from osiris.nclm.autograd import no_grad
    data = np.frombuffer(text.encode("utf-8", errors="ignore"), dtype=np.uint8).astype(np.int64)
    out: Dict[int, float] = {}
    with no_grad():
        for start, x, y in windows(data, span, limit=10 ** 6):
            logits = model.forward(x).data[0].astype(np.float64)
            logits -= logits.max(axis=-1, keepdims=True)
            logp = logits - np.log(np.exp(logits).sum(axis=-1, keepdims=True))
            for t, target in enumerate(y[0]):
                out.setdefault(start + 1 + t, float(-logp[t, target]))
    return out


def score_item(model, text: str, train_bytes: bytes, span: int) -> dict:
    nats = byte_nats(model, text, span)
    mask = template_mask(text.encode("utf-8", errors="ignore"), train_bytes)
    novel = [v for pos, v in nats.items() if not mask[pos]]
    return {"bytes": len(nats), "bpb": sum(nats.values()) / len(nats) / LN2 if nats else None,
            "novel_bytes": len(novel), "bpb_novel": sum(novel) / len(novel) / LN2 if novel else None,
            "template_fraction": round(1 - len(novel) / len(nats), 4) if nats else None}


def unigram_bpb(text: str, train_bytes: bytes) -> float:
    """Add-one byte unigram fit on the training text only (the gate's baseline)."""
    counts = [1] * 256
    for b in train_bytes:
        counts[b] += 1
    total = sum(counts)
    data = text.encode("utf-8", errors="ignore")
    return sum(-math.log(counts[b] / total) for b in data) / max(1, len(data)) / LN2


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def _console():
    import osiris_termux_console as otc
    return otc


def _version():
    try:
        from osiris_cli import __version__
        return __version__
    except Exception:  # noqa: BLE001 - provenance is recorded, never fatal
        return None


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def live_paths():
    return _console()._organism_checkpoint_paths()


def freeze(dest: str) -> dict:
    """Copy the live checkpoint into dest as an immutable snapshot."""
    ckpt, meta = live_paths()
    os.makedirs(dest, exist_ok=True)
    shutil.copy2(ckpt, os.path.join(dest, "organism.npz"))
    shutil.copy2(meta, os.path.join(dest, "organism.json"))
    info = snapshot_info(dest)
    with open(os.path.join(dest, "SNAPSHOT.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    return info


def snapshot_paths(where: str):
    if where == "live":
        return live_paths()
    return os.path.join(where, "organism.npz"), os.path.join(where, "organism.json")


def snapshot_info(where: str) -> dict:
    ckpt, meta = snapshot_paths(where)
    with open(meta, encoding="utf-8") as f:
        step = int(json.load(f).get("step", 0))
    return {"path": os.path.abspath(ckpt), "sha256": file_sha256(ckpt), "step": step}


def load(where: str, with_optimizer: bool = False):
    """(model, optimizer, step) from a snapshot directory or "live"; the same
    architecture and loader as the live core."""
    import numpy as np
    otc = _console()
    ckpt, meta = snapshot_paths(where)
    model, opt = otc._organism_build(otc._organism_arch(os.path.dirname(ckpt)))
    with open(meta, encoding="utf-8") as f:
        m = json.load(f)
    with np.load(ckpt) as blob:
        for i, p in enumerate(model.parameters()):
            p.data[...] = blob[f"p{i}"]
            if with_optimizer:
                opt._m[i][...] = blob[f"m{i}"]
                opt._v[i][...] = blob[f"v{i}"]
    opt.step_count = int(m.get("step_count", 0))
    return model, opt, int(m.get("step", 0))


def weights_sha256(model) -> str:
    h = hashlib.sha256()
    for p in model.parameters():
        h.update(p.data.tobytes())
    return h.hexdigest()


def train_like_live(model, opt, lessons: Sequence[str], steps: int, seed: int) -> int:
    """Replay the live core's online regime (Osiris._after -> NclmCore.learn):
    `steps` updates per lesson on randomly chosen windows, grad clip 1.0."""
    import numpy as np
    from osiris.nclm import cross_entropy_loss
    from osiris.nclm.autograd import clip_grad_norm
    rng = random.Random(seed)
    span = _console().ORGANISM_GEOMETRY["max_seq_len"]
    n = 0
    for text in lessons:
        data = np.frombuffer(text.encode("utf-8", errors="ignore"), dtype=np.uint8).astype(np.int64)
        wins = windows(data, span, 64)
        if not wins:
            continue
        for _ in range(steps):
            _, x, y = rng.choice(wins)
            opt.zero_grad()
            out = cross_entropy_loss(model.forward(x), y)
            out.backward()
            clip_grad_norm(model.parameters(), 1.0)
            opt.step()
            n += 1
    return n


# ---------------------------------------------------------------------------
# Paired analysis
# ---------------------------------------------------------------------------

def score_pairs(pre_model, post_model, held: Sequence[dict], train: Sequence[str]) -> List[dict]:
    span = _console().ORGANISM_GEOMETRY["max_seq_len"]
    train_bytes = "".join(train).encode("utf-8", errors="ignore")
    rows = []
    for r in held:
        pre = score_item(pre_model, r["reply"], train_bytes, span)
        post = score_item(post_model, r["reply"], train_bytes, span)
        rows.append({
            "index": r.get("index"), "hash": r.get("hash"), "bytes": pre["bytes"],
            "template_fraction": pre["template_fraction"],
            "bpb_pre": pre["bpb"], "bpb_post": post["bpb"],
            "d": None if pre["bpb"] is None else pre["bpb"] - post["bpb"],
            "bpb_pre_novel": pre["bpb_novel"], "bpb_post_novel": post["bpb_novel"],
            "d_novel": None if pre["bpb_novel"] is None else pre["bpb_novel"] - post["bpb_novel"],
            "bpb_unigram": unigram_bpb(r["reply"], train_bytes),
        })
    return rows


def summarize(values: Sequence[float], seed: int = BOOTSTRAP_SEED) -> dict:
    """Mean, SD, sign count and a percentile bootstrap of the mean. The one-sided
    95% lower bound is the 5th percentile."""
    xs = [v for v in values if v is not None]
    n = len(xs)
    if n == 0:
        return {"n": 0}
    mean = sum(xs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1)) if n > 1 else None
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(xs) for _ in range(n)) / n for _ in range(BOOTSTRAP))
    q = lambda p: boots[min(BOOTSTRAP - 1, int(p * BOOTSTRAP))]  # noqa: E731
    return {"n": n, "mean": mean, "sd": sd, "positive": sum(x > 0 for x in xs),
            "ci95": [q(0.025), q(0.975)], "lower95_one_sided": q(0.05)}


def n_required(mpe: float, sd: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Held-out items for a one-sided paired test to detect a mean difference of
    mpe with the given power (normal approximation plus the usual t correction)."""
    za = NormalDist().inv_cdf(1 - alpha)
    zb = NormalDist().inv_cdf(power)
    return math.ceil(((za + zb) * sd / mpe) ** 2 + za ** 2 / 2)


def verdict(primary: dict, mpe: float, n_min: int) -> str:
    """The pre-registered decision rule for a confirmatory run (not used on pilots):
    PASS needs n >= n_min, mean d >= MPE and the one-sided 95% lower bound > 0;
    REGRESSION when the trained core is reliably worse (upper 95% bound < 0)."""
    if primary.get("n", 0) < n_min:
        return "INCONCLUSIVE"
    if primary["ci95"][1] < 0:
        return "REGRESSION"
    if primary["mean"] >= mpe and primary["lower95_one_sided"] > 0:
        return "PASS"
    return "FAIL"


def analyse(rows: List[dict]) -> dict:
    return {"primary_d": summarize([r["d"] for r in rows]),
            "secondary_d_novel": summarize([r["d_novel"] for r in rows]),
            "secondary_post_vs_unigram": summarize(
                [None if r["bpb_post"] is None else r["bpb_unigram"] - r["bpb_post"] for r in rows]),
            "template_fraction_mean": (sum(r["template_fraction"] for r in rows) / len(rows)) if rows else None}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m osiris_cli.prepost", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze", help="snapshot the live core as the pre-training baseline")
    f.add_argument("dest")
    s = sub.add_parser("score", help="paired pre/post scores of the held-out exchanges")
    s.add_argument("--pre", required=True)
    s.add_argument("--post", default="live")
    s.add_argument("--exchanges", default=os.path.expanduser("~/.osiris/living/exchanges.jsonl"))
    s.add_argument("--out", required=True)
    p = sub.add_parser("plan", help="held-out items needed for a given minimum effect")
    p.add_argument("results")
    p.add_argument("--mpe", type=float, required=True)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.80)
    a = ap.parse_args(argv)

    if a.cmd == "freeze":
        print(json.dumps(freeze(a.dest), indent=1))
        return 0
    if a.cmd == "score":
        rows = read_exchanges(a.exchanges)
        train, held = split(rows)
        pre_model, _, _ = load(a.pre)
        post_model, _, _ = load(a.post)
        pairs = score_pairs(pre_model, post_model, held, train)
        nclm = sys.modules.get("osiris.nclm")
        out = {"code": {"osiris_cli": _version(), "nclm_path": os.path.dirname(getattr(nclm, "__file__", "") or ""),
                        "scoring_forward": int(getattr(nclm, "SCORING_FORWARD", 1))},
               "pre": snapshot_info(a.pre), "post": snapshot_info(a.post),
               "exchanges": {"path": os.path.abspath(a.exchanges), "sha256": file_sha256(a.exchanges),
                             "n": len(rows), "train": len(train), "heldout": len(held)},
               "template_span": TEMPLATE_SPAN, "items": pairs, "analysis": analyse(pairs)}
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        print(json.dumps(out["analysis"], indent=1))
        return 0
    with open(a.results, encoding="utf-8") as fh:
        primary = json.load(fh)["analysis"]["primary_d"]
    if not primary.get("sd"):
        print("need at least two held-out items with scores to estimate the SD")
        return 1
    print(json.dumps({"sd_pilot": primary["sd"], "mpe": a.mpe, "alpha_one_sided": a.alpha,
                      "power": a.power, "n_heldout_required": n_required(a.mpe, primary["sd"], a.alpha, a.power)},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
