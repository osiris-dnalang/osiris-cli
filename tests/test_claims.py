"""The claims register and physics checks: OSIRIS deciding what is legit, by code, before a model speaks."""
import math
import re

import pytest

from osiris_cli import claims
from osiris_cli import physics_checks as pc
from osiris_cli.living import Osiris

from tests.test_living import FakeCore, ScriptedMentor


# ── physics checks against known values ──────────────────────────────────────

def test_radiation_thrust_bound():
    c = pc.radiation_thrust(1.1e6, 18500)
    assert c.verdict == "RULED_OUT"
    assert math.isclose(1.1e6 / pc.C, 3.669e-3, rel_tol=1e-3)
    assert "4.944e+07" in c.quantities["shortfall factor"]
    assert pc.radiation_thrust(1e12, 1.0).verdict == "CONSISTENT"


def test_rim_speed_and_planck_mass():
    r = pc.rim_speed(8.8e10, 0.05)
    assert r.verdict == "RULED_OUT" and r.quantities["v / c"] == "14.68"
    assert pc.rim_speed(100.0, 0.05).verdict == "CONSISTENT"
    m = math.sqrt(pc.HBAR * pc.C / pc.G)
    assert math.isclose(m, 2.176434e-8, rel_tol=1e-6)
    assert pc.same_number(2.176435e-8, m, "Planck mass").verdict == "MATCH"


def test_static_metric_mass():
    c = pc.static_metric_mass(1.297e-19, 0.05)
    assert c.verdict == "IMPLIED" and c.quantities["implied mass"] == "4.366e+06 kg"
    assert pc.static_metric_mass(1.297e-19, 0.05, 4.4e6, 3.15576e7).verdict == "RULED_OUT"
    assert pc.static_metric_mass(1e-40, 0.05, 1e4, 1.0).verdict == "CONSISTENT"   # 3.4e3 J needed, 1e4 J supplied


@pytest.mark.parametrize("s,verdict,word", [(3.0, "RULED_OUT", "Tsirelson"), (2.5, "CONSISTENT", "Violates"),
                                            (0.106, "CONSISTENT", "No Bell violation")])
def test_chsh_bounds(s, verdict, word):
    c = pc.chsh(s)
    assert c.verdict == verdict and word in c.why


def test_efficiency_and_entropy_ceiling():
    assert pc.efficiency(1.94).verdict == "RULED_OUT" and pc.efficiency(0.4).verdict == "CONSISTENT"
    assert pc.entropy_ceiling(1e6, 19.9316).verdict == "RULED_OUT"      # the 136-bit "gap"
    assert pc.entropy_ceiling(1e6, 12.0).verdict == "CONSISTENT"
    assert pc.entropy_ceiling(1e6, 25.0).verdict == "RULED_OUT"


def test_dd_window_reproduces_the_d6_worked_example():
    c = pc.dd_window(2e-6, 35.55e-9, 8)                                     # XY8 at 2 us
    assert c.verdict == "FEASIBLE"
    assert c.quantities["pulse train D_p"] == "0.2844 us" and c.quantities["window / D_p"] == "7.032"
    assert c.quantities["edge gap T_f/2n"] == "0.1072 us" and c.quantities["inner gap T_f/n"] == "0.2145 us"
    assert pc.dd_window(0.5e-6, 35.55e-9, 8).verdict == "MARGINAL"          # fits, ratio 1.76 < 2
    assert pc.dd_window(0.2e-6, 35.55e-9, 8).verdict == "NOT_FEASIBLE"      # tau_k < D_p


@pytest.mark.parametrize("text,value", [("1.1MW", 1.1e6), ("35.55ns", 3.555e-8), ("18,500kg", 18500.0),
                                        ("5cm", 0.05), ("194%", 1.94), ("2us", 2e-6), ("8.8e10", 8.8e10),
                                        ("14GHz", 1.4e10), ("1yr", 3.15576e7), ("3mW", 3e-3)])
def test_parse_quantity(text, value):
    assert math.isclose(pc.parse_quantity(text), value, rel_tol=1e-12)


@pytest.mark.parametrize("text", ["5mw", "12 furlongs", "abc"])
def test_parse_quantity_refuses_ambiguous_or_unknown(text):
    with pytest.raises(ValueError):
        pc.parse_quantity(text)


def test_physics_command():
    assert "RULED_OUT" in pc.run_command("thrust power=1.1MW mass=18500kg")
    assert "FEASIBLE" in pc.run_command("dd window=2us pulse=35.55ns n=8")
    assert "rim speed: RULED_OUT" in pc.run_command("rim freq=14.007GHz radius=5cm")
    assert pc.run_command("") == pc.USAGE
    assert "missing power" in pc.run_command("thrust mass=1kg")
    assert "unknown check" in pc.run_command("warp factor=9")


# ── the register ─────────────────────────────────────────────────────────────

def test_register_is_well_formed():
    ids = [c.id for c in claims.REGISTER]
    assert len(ids) == len(set(ids)) >= 30
    for c in claims.REGISTER:
        assert c.verdict in claims.VERDICTS, c.id
        assert c.patterns and all(re.compile(p) for p in c.patterns), c.id
        for kind, ref, note in c.evidence:
            assert kind in ("doi", "file", "commit") and note, c.id
            if kind == "doi":
                assert re.fullmatch(r"10\.5281/zenodo\.\d+", ref), ref
            if kind == "file":
                assert not ref.startswith("/") and ".." not in ref, ref
        # an absence of evidence cannot cite a record; every other verdict must rest on one
        assert c.evidence or c.checks or c.verdict == "NO_EVIDENCE", \
            f"{c.id} has neither a record nor a computation behind it"


def test_computed_verdicts_agree_with_the_register():
    """A RULED_OUT entry must be ruled out by its own computation, every time it is shown."""
    for c in claims.REGISTER:
        for name, args in c.checks:
            lines = claims._check_lines(name, args)
            assert lines, c.id
            if c.verdict == "RULED_OUT":
                assert "RULED_OUT" in lines[0], (c.id, lines[0])


PAPER = (r"net integrated Poynting flux ... phase-locked to a geometric angle of $\theta_{lock} = 51.843^\circ$"
         r" ... $$\omega = 8.8 \times 10^{10} \text{ rad/s}$$ ... $$h_{tt} = -1.297 \times 10^{-19}$$ ..."
         r" without the expulsion of standard reaction mass ... Target Lift Capacity: 18,500 kg")


def test_matching_on_real_texts():
    assert {"POYNTING_PROPULSION", "METRIC_PERTURBATION", "RIM_SPEED", "THETA_LOCK"} <= \
        {c.id for c in claims.match(PAPER)}
    assert [c.id for c in claims.match("is the 51.843 theta lock real?")] == ["THETA_LOCK"]
    assert [c.id for c in claims.match("tell me about the tau-phase anomaly at 46 µs")][0] == "TAU_PHASE"
    assert claims.match("the 136-bit negentropy gap")[0].id == "NEGENTROPY_136"


@pytest.mark.parametrize("text", ["hello osiris", "what's the weather like", "write a unit test for the parser",
                                  "please summarise my notes from yesterday", "run git status"])
def test_ordinary_chat_matches_nothing(text):
    assert claims.match(text) == []


def test_rendering_shows_evidence_and_computations(tmp_path):
    lines = "\n".join(claims.render(claims.by_id("LAMBDA_PHI"), base=str(tmp_path)))
    assert "NOT_MEASURED" in lines and "Planck mass" in lines and "MATCH" in lines
    assert "not on this machine" in lines                       # file evidence missing under tmp_path
    theta = "\n".join(claims.render(claims.by_id("THETA_LOCK")))
    assert "arctan(14/11) = 51.8428 degrees" in theta and "doi:10.5281/zenodo.18781261" in theta


def test_legit_command():
    assert claims.command("list").startswith("Claims register:")
    assert "REFUTED" in claims.command("theta_lock")
    assert "RULED_OUT" in claims.command("can a Poynting asymmetry lift a bus?")
    assert "not that it is legit" in claims.command("my cat can fly")


# ── chat: code answers first, the model is held to it ────────────────────────

def make(tmp_path, mentor=None):
    out = []
    o = Osiris(core=FakeCore(), mentor=mentor or ScriptedMentor(), home=str(tmp_path), out=out.append,
               background=False, knowledge=None, tty=False)
    return o, out


def test_verdict_is_printed_before_the_mentor_and_given_to_it(tmp_path):
    mentor = ScriptedMentor(reply="It was refuted.")
    o, out = make(tmp_path, mentor)
    o.converse("is the 51.843 theta lock real?")
    text = "".join(out)
    assert text.index("REFUTED") < text.index("It was refuted.")
    last = mentor.calls[0][-1]["content"]
    assert "[Claims register" in last and "THETA_LOCK" in last


def test_no_block_for_ordinary_chat(tmp_path):
    mentor = ScriptedMentor()
    o, out = make(tmp_path, mentor)
    o.converse("hello osiris")
    assert "Claims register" not in "".join(out) and "[Claims register" not in mentor.calls[0][-1]["content"]


def test_verdict_shown_even_when_no_model_is_reachable(tmp_path):
    class NoMentor(ScriptedMentor):
        def model(self):
            return None
    o, out = make(tmp_path, NoMentor())
    o.converse("does a Poynting asymmetry give propellantless thrust?")
    text = "".join(out)
    assert "RULED_OUT" in text and "no mentor model is reachable" in text
