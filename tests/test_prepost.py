"""Paired pre/post scoring: split, template masking, statistics and the decision rule."""
import math

from osiris_cli.prepost import (lesson, n_required, split, summarize, template_mask, unigram_bpb,
                                verdict, windows)


def test_split_follows_the_log_and_skips_unlearnable():
    rows = [{"user": "a", "reply": "r0", "heldout": True},
            {"user": "b", "reply": "r1", "heldout": False},
            {"user": "c", "reply": "r2", "heldout": False, "learnable": False},
            {"user": "d", "reply": "r3", "heldout": True, "learnable": False}]
    train, held = split(rows)
    assert train == [lesson(rows[1])] == ["User: b\nOSIRIS: r1\n"]
    assert [r["reply"] for r in held] == ["r0"]


def test_template_mask_marks_only_shared_long_strings():
    boiler = b"I'm OSIRIS, the living language model being built by Devin."
    train = b"User: x\nOSIRIS: " + boiler + b" Something else entirely.\n"
    text = boiler + b" The staggered sequence offsets odd qubits."
    mask = template_mask(text, train)
    assert all(mask[:len(boiler)]) and not any(mask[len(boiler) + 2:])
    assert not any(template_mask(b"short", b"short"))       # under the span: never template


def test_windows_cover_every_byte_once():
    data = list(range(300))
    import numpy as np
    w = windows(np.array(data), span=128, limit=100)
    covered = [s + 1 + t for s, _, y in w for t in range(y.shape[1])]
    assert covered == list(range(1, 300))


def test_unigram_is_fit_on_training_text_only():
    assert unigram_bpb("aaaa", b"aaaa" * 100) < 1.0 < unigram_bpb("zzzz", b"aaaa" * 100)


def test_summary_and_power():
    s = summarize([0.2, 0.1, 0.3, -0.1, 0.25])
    assert s["n"] == 5 and s["positive"] == 4 and math.isclose(s["mean"], 0.15)
    assert s["ci95"][0] <= s["lower95_one_sided"] <= s["mean"] <= s["ci95"][1]
    assert summarize([None]) == {"n": 0}
    assert n_required(0.10, 0.30) == 57                       # d = 0.33, alpha .05 one-sided, power .8
    assert n_required(0.10, 0.60) > n_required(0.10, 0.30)


def test_decision_rule():
    good = {"n": 60, "mean": 0.2, "ci95": [0.1, 0.3], "lower95_one_sided": 0.12}
    assert verdict(good, mpe=0.1, n_min=57) == "PASS"
    assert verdict(dict(good, n=10), mpe=0.1, n_min=57) == "INCONCLUSIVE"
    assert verdict(dict(good, mean=0.05), mpe=0.1, n_min=57) == "FAIL"     # significant, too small
    assert verdict({"n": 60, "mean": -0.3, "ci95": [-0.5, -0.1], "lower95_one_sided": -0.45},
                   mpe=0.1, n_min=57) == "REGRESSION"
