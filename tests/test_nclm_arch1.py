"""NCLM-ARCH-1's decision rule (experiments/nclm_arch1/run.py decide()) does what the pre-registration says."""
import importlib.util
from pathlib import Path

import pytest

RUN = Path(__file__).resolve().parents[1] / "experiments" / "nclm_arch1" / "run.py"
spec = importlib.util.spec_from_file_location("nclm_arch1_run", RUN)
arch1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arch1)


def pairs(gains, chat=0.0):
    return [{"seed": s, "gain": g, "chat_change": chat,
             "winner": None if g is None else ("crsm" if g > 0 else "standard")}
            for s, g in zip(arch1.SEEDS, gains)]


def test_registered_constants():
    assert arch1.SEEDS == list(range(200, 208)) and arch1.ARMS == ("crsm", "standard")
    assert (arch1.DELTA, arch1.GUARD, arch1.WINS_NEEDED, arch1.MIX) == (0.05, 0.10, 6, "0.5,0.3,0.2")
    assert arch1.N_PARAMS == {"crsm": 726_304, "standard": 725_760}


def test_a_clear_crsm_win_passes_and_its_mirror_fails():
    win = [0.08, 0.09, 0.07, 0.10, 0.06, 0.08, 0.09, 0.07]
    assert arch1.decide(pairs(win), True)["verdict"] == "PASS"
    assert arch1.decide(pairs([-g for g in win]), True)["verdict"] == "FAIL"


def test_the_chat_guard_turns_a_document_win_into_mixed():
    v = arch1.decide(pairs([0.08, 0.09, 0.07, 0.10, 0.06, 0.08, 0.09, 0.07], chat=0.2), True)
    assert v["verdict"] == "NO-DIFFERENCE" and v["label"].startswith("mixed")
    assert arch1.decide(pairs([0.08, 0.09, 0.07, 0.10, 0.06, 0.08, 0.09, 0.07], chat=0.2), False)["verdict"] == "PASS"


def test_small_tight_differences_are_equivalent_and_noisy_ones_inconclusive():
    v = arch1.decide(pairs([0.01, -0.01, 0.0, 0.01, -0.01, 0.005, -0.005, 0.0]), True)
    assert v["verdict"] == "NO-DIFFERENCE" and v["label"].startswith("equivalent")
    v = arch1.decide(pairs([0.3, -0.2, 0.25, -0.3, 0.1, -0.1, 0.2, -0.15]), True)
    assert v["verdict"] == "NO-DIFFERENCE" and v["label"].startswith("inconclusive")


def test_a_mean_above_delta_without_six_wins_does_not_pass():
    v = arch1.decide(pairs([0.30, 0.25, 0.20, 0.22, 0.28, -0.01, -0.02, -0.01]), True)
    assert v["wins"]["crsm"] == 5 and v["verdict"] != "PASS"


def test_divergence_one_pair_is_excluded_two_make_it_inconclusive():
    gains = [None, 0.08, 0.09, 0.07, 0.10, 0.06, 0.08, 0.09]
    p = pairs(gains)
    p[0]["winner"] = "crsm"                      # the standard run diverged
    v = arch1.decide(p, True)
    assert v["n_pairs"] == 7 and v["excluded_pairs"] == 1 and v["verdict"] == "PASS"
    p[1].update(gain=None, winner="crsm")
    v = arch1.decide(p, True)
    assert v["verdict"] == "NO-DIFFERENCE" and "diverged" in v["label"]


@pytest.mark.parametrize("n", [7, 8])
def test_the_t_quantile_matches_the_pair_count(n):
    assert arch1.T95[n - 1] == {7: 1.943, 8: 1.895}[n]


def test_common_step_is_the_last_eval_both_runs_reached():
    c = {"seed": 200, "evals": [(0, 9.0), (200, 6.0), (400, 5.5), (600, 5.4)]}
    d = {"seed": 200, "evals": [(0, 9.1), (200, 5.9), (400, 5.6)]}
    assert arch1.common_step(c, d) == {"seed": 200, "step": 400, "crsm": 5.5, "standard": 5.6}
