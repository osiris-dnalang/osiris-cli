"""The claims register and physics checks: OSIRIS deciding what is legit, by code, before a model speaks."""
import math
import re
from pathlib import Path

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
            if kind == "doi":                       # a Zenodo record, or a published paper's DOI
                assert re.fullmatch(r"10\.5281/zenodo\.\d+", ref) if ref.startswith("10.5281/") else \
                    re.fullmatch(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", ref), ref
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
    assert claims.match("RQC beats RCS with p < 0.05, ready for peer review")[0].id == "RQC_ADVANTAGE"


@pytest.mark.parametrize("text", [
    "the tau-phase anomaly at 46 µs", "τ₀ ≈ 46.0 μs", "τ₀ ≈ 46.0 µs", "a revival at 46 μs",
    "an oscillation period of 46.98 µs", "τ0 = 46.9 us", "the 46 µs anomaly", "46 microseconds: the revival",
    "tau_0 = 46.000 μs", "phase folded at 46 µsec", "the revival near   46.0   μs",
    "CRSM Coherence Revival Period (τ₀) τ₀ ≈ 46.0 μs Davis (6D-CRSM, 2025)"])
def test_tau_phase_duration_spellings_are_recognised(text):
    assert "TAU_PHASE" in [c.id for c in claims.match(text)], text


@pytest.mark.parametrize("text", [
    "set the idle delay to 46 µs", "a 46 μs Ramsey delay", "T2 was 146 µs at the revival check",
    "the revival window is 460 µs", "a revival after 4.46 µs", "46,000 µs of phase drift",
    "46 users saw the anomaly", "46 microphones and a phase meter", "the anomaly: 46 ms, not microseconds",
    "a revival at 46 ns", "period 46.3 µs"])
def test_tau_phase_duration_does_not_overmatch(text):
    assert "TAU_PHASE" not in [c.id for c in claims.match(text)], text


def test_a_reference_is_not_an_endorsement():
    # criticism and negation reference the claim too; the verdict, not the match, says it is not legit
    for text in ("The τ-phase claim was an artifact of the server clock.",
                 "There is no revival at 46.0 μs; that was T1 decay."):
        hits = [c.id for c in claims.match(text)]
        assert "TAU_PHASE" in hits or "K8_REVIVAL" in hits, text
    assert claims.by_id("TAU_PHASE").verdict == "ARTIFACT"


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


# ── v4.5.2 entries: F_max, coherence quantization, the core's physics names, the quantum-LLM roadmap ──

NEW_V452 = {"F_MAX": "REFUTED", "COHERENCE_QUANTIZATION": "OVERCLAIM", "NCLM_MECHANICS": "NOT_MEASURED",
            "NCLM_PC_CORRECTOR": "NOT_MEASURED", "QUANTUM_LM": "NO_EVIDENCE", "QEC_LLM_SAFETY": "RULED_OUT",
            "CRSM_ARCH": "UNTESTED"}


def test_v452_entries_and_verdicts():
    assert {i: claims.by_id(i).verdict for i in NEW_V452} == NEW_V452
    assert "v4.5.2" in claims.by_id("NCLM_PC_CORRECTOR").finding and "v4.5.2" in claims.by_id("NCLM_CORE").finding
    papers = {r for k, r, _ in claims.by_id("F_MAX").evidence if k == "doi"}
    assert {"10.1038/nphys961", "10.1103/PhysRevLett.117.060504", "10.1103/PhysRevLett.117.060505"} <= papers


def test_repetition_code_sees_flips_not_values():
    c = pc.repetition_code(3)
    assert c.verdict == "RULED_OUT"
    assert c.quantities["syndrome of encoded 0"] == c.quantities["syndrome of encoded 1"] == "00"
    assert c.quantities["flip patterns flagged"] == "6 of 7"          # flipping all three gives the other codeword


def test_v452_computations():
    phi = (1 + math.sqrt(5)) / 2
    bound = claims._check_lines("one_minus_phi_power", (8, (0.993, 0.999, 0.9992)))
    assert bound[0] == f"1 - phi^-8 = {1 - phi ** -8:.6f}" == "1 - phi^-8 = 0.978714"
    assert bound[1].startswith("3 of the 3 cited Bell-state or Bell-derived gate fidelities exceed it")
    cover = claims._check_lines("multiple_coverage", (46.0, 0.10, 100.0, 300.0))
    assert "79% of 100-300 µs" in cover[0] and "from n = 5" in cover[1] and "above 207.0 µs" in cover[1]
    wide = claims._check_lines("multiple_coverage", (46.0, 0.15, 100.0, 300.0))
    assert "94% of 100-300 µs" in wide[0] and "from n = 3" in wide[1] and "above 117.3 µs" in wide[1]
    table = claims._check_lines("phi_positional", (128, 51.843, 0.946))
    assert "sine 0.305-0.786" in table[0] and "cosine 0.227-0.584" in table[0]
    assert "longest period 27.7 positions" in table[1] and "span 2.58x" in table[1] and "8,660x" in table[1]


def test_f_max_statistics_as_the_finding_states():
    def p_three(r):                     # two-sided p of a Pearson r from 3 points: t with 1 d.o.f. is Cauchy
        return 1 - 2 / math.pi * math.atan(r / math.sqrt(1 - r * r))
    pred, meas = (0.985, 0.982, 0.977), (0.900, 0.880, 0.869)   # falsifiable_predictions.md, Prediction 2 table
    mp, mm = sum(pred) / 3, sum(meas) / 3
    r = sum((a - mp) * (b - mm) for a, b in zip(pred, meas)) / math.sqrt(
        sum((a - mp) ** 2 for a in pred) * sum((b - mm) ** 2 for b in meas))
    assert round(r, 2) == 0.95 and round(p_three(r), 2) == 0.20
    assert round(p_three(0.90), 2) == 0.29 and round(p_three(0.99996), 3) == 0.006
    assert max(pred[:2]) > 1 - ((1 + math.sqrt(5)) / 2) ** -8    # the document's own predictions break its bound


@pytest.mark.parametrize("text,first", [
    ("Bell fidelity bound (F_max = 0.9787) — validated ✓", "F_MAX"),
    ("H1: Bell fidelity bound (F_max = 0.9787) — validated", "F_MAX"),
    ("F_max = 1 - φ^{-8} = 0.9787 bound **100% validated**", "F_MAX"),
    ("Prediction 1 (Coherence Quantization) validated; 2–4 pending", "COHERENCE_QUANTIZATION"),
    ("Insight: If coherence quantizes at τ_base × n, then memory cells could naturally align",
     "COHERENCE_QUANTIZATION"),
    ("#### 1. Hybrid Pilot-Wave + Transformer Architecture", "QUANTUM_LM"),
    ("Layer 2: Hybrid attention (quantum phase coherence guides attention scores)", "QUANTUM_LM"),
    ("Quantum-guided attention using phase information", "QUANTUM_LM"),
    ("Hypothesis: Quantum saves 20–40% token budget on multi-turn reasoning", "QUANTUM_LM"),
    ("Non-Causal Temporal Quantum Memory (NCQM)", "QUANTUM_LM"),
    ("#### 7. Entanglement-Assisted Error Correction for LLM Outputs", "QEC_LLM_SAFETY"),
    ("Encode each token in a 3-qubit GHZ state for error detection", "QEC_LLM_SAFETY"),
    ("LLM safety as a quantum error correction problem", "QEC_LLM_SAFETY"),
    ("Pilot-wave attention modulation (non-local correlation factor)", "NCLM_MECHANICS"),
    ("Torsion-Locked Attention (T-Lock) prevents information manifold collapse", "NCLM_MECHANICS"),
    ("Phase-Conjugate Error Correction: F_purified = 1 - 10^{-5}", "NCLM_PC_CORRECTOR"),
    ("constraints=[hardware_calibration_drift, CHSH_bounds]", "CHSH_TEST"),
    ("H2: θ-lock angle (51.843°) — prior P(H2|data) = ?", "THETA_LOCK"),
    ("θ_lock = 51.8° ± 0.3° (95% credible interval, posterior)", "THETA_LOCK"),
    ("H3: Phase-conjugate efficiency (χ_pc = 0.946)", "CHI_PC"),
    ("Does the CRSM architecture beat a standard transformer? NCLM-ARCH-1 will say.", "CRSM_ARCH")])
def test_roadmap_texts_lead_with_their_entry(text, first):
    assert claims.match(text)[0].id == first, [c.id for c in claims.match(text)]


@pytest.mark.parametrize("text,also", [
    ("Benefit: Quantum advantage in attention pattern discovery", {"QUANTUM_ADVANTAGE", "QUANTUM_LM"}),
    ("#### 6. Quantum Advantage in In-Context Learning", {"QUANTUM_ADVANTAGE", "QUANTUM_LM"}),
    ("Time-series quantum state encoding: τ_mem ≈ 46 μs becomes a learned metric.",
     {"TAU_PHASE", "COHERENCE_QUANTIZATION"}),
    ("Phase-conjugate positional encoding (θ_lock = 51.843°)", {"THETA_LOCK", "NCLM_MECHANICS"}),
    ("NCLM Engine — Non-Local Non-Causal Language Model", {"NCLM_CORE", "NCLM_MECHANICS"})])
def test_roadmap_texts_that_touch_two_entries(text, also):
    assert also <= {c.id for c in claims.match(text)}, text


@pytest.mark.parametrize("text", [
    "Please pay attention to the phase of the project plan.",
    "The attention mechanism in a standard transformer uses softmax over scaled dot products.",
    "We added positional encoding to the model.", "Quantum computing is interesting; can you explain qubits?",
    "Error correction in our database layer retries failed writes.", "The fidelity of the translation was high.",
    "Run the benchmark again in the next phase.", "Add a learning-rate warmup and a cosine schedule.",
    "This sentence mentions a pilot and a wave at the beach.", "The tokenizer encodes each token as an integer id.",
    # legitimate physics and machine learning that share words with the new entries
    "Explain de Broglie-Bohm pilot-wave theory.", "BERT is a non-causal language model.",
    "Entanglement-assisted quantum error-correcting codes need pre-shared ebits.",
    "Use a 3-qubit repetition code to protect against bit flips.", "Bell state fidelity on ibm_fez was 0.91",
    "We fine-tuned a transformer on quantum chemistry data; its attention weights look sparse.",
    "4-bit quantization reduces the coherence of long answers.", "How does in-context learning work?",
    "Error correction for LLM-generated code: retry on syntax errors.",
    "A phase-conjugate mirror corrects aberrations in the laser beam.", "The token budget is 4,000 tokens.",
    # found by review after the first draft (2026-10-08)
    "a glass of purified water", "fraction of purified protein", "Gemma 2 uses hybrid attention with sliding windows",
    "Quantum optimal control draws attention from industry", "the T2 instance was slow after 8-bit quantization",
    "There is a T-lock on this door"])
def test_v452_entries_do_not_overmatch(text):
    assert not set(NEW_V452) & {c.id for c in claims.match(text)}, text


def test_nclm_entries_describe_the_code():
    np = pytest.importorskip("numpy")
    import inspect

    from osiris.nclm import positions
    from osiris.nclm import sovereign_mechanics as sm
    pw = sm.TorsionLockedAttention._pilot_wave_factor(128)[0, 0]
    assert round(float(pw.min()), 2) == 1.37 and float(pw.max()) == 2.0      # a fixed multiplier, no parameter
    assert round(float(sm.TorsionLockedAttention._pilot_wave_factor(8)[0, 0, 0, 5]), 2) == 1.54
    assert round(float(pw[0, 5]), 2) == 1.96                                  # same distance, longer context
    pe = positions.phase_conjugate_positional_encoding(128, 128).data
    pos = np.arange(128, dtype=np.float32)[:, None]
    freqs = 1.0 / (positions.PHI_GOLDEN ** (np.arange(0, 128, 2, dtype=np.float32) * 2.0 / 128))
    plus = math.cos(positions.THETA_RAD) * positions.CHI_PC                   # the source uses minus this
    assert np.allclose(pe[:, 1::2], np.cos(pos * freqs * plus), atol=1e-6)   # cos is even: the sign does nothing
    corr = sm.PhaseConjugateCorrector(128)
    assert 4 * sum(t.data.size for t in (corr.conj_gate.weight, corr.conj_gate.bias_param,
                                         corr.theta_proj.weight)) == 131_584
    body = inspect.getsource(sm.PhaseConjugateCorrector)
    assert "FIDELITY_TARGET" not in body and "self.zero_point" not in inspect.getsource(
        sm.PhaseConjugateCorrector.__call__)
    assert "1::2" in body and "theta_proj" in body                            # sign flip, then a learned map


def test_the_users_own_framing_gets_the_verdict():
    """The phrase the core is described with is checked like any other claim."""
    ids = {c.id for c in claims.match("the non causal living language model and the dnalang framework")}
    assert "NCLM_MECHANICS" in ids and "NCLM_CORE" in ids


def test_crsm_arch_points_at_its_pre_registration():
    c = claims.by_id("CRSM_ARCH")
    [(kind, ref, _)] = c.evidence
    assert kind == "file" and ref == "osiris-cli/experiments/nclm_arch1/PRE_REGISTRATION.md"
    assert (Path(__file__).resolve().parents[1] / "experiments" / "nclm_arch1" / "PRE_REGISTRATION.md").exists()


def test_the_chsh_shell_command_is_not_the_chsh_test():
    assert "CHSH_TEST" not in {c.id for c in claims.match("run chsh -s /bin/zsh to change your shell")}
    assert "CHSH_TEST" in {c.id for c in claims.match("our CHSH value was 2.4")}


def test_rendering_the_v452_entries(tmp_path):
    f_max = "\n".join(claims.render(claims.by_id("F_MAX"), base=str(tmp_path)))
    assert "[computed] 1 - phi^-8 = 0.978714" in f_max and "doi:10.1103/PhysRevLett.117.060504" in f_max
    qec = "\n".join(claims.render(claims.by_id("QEC_LLM_SAFETY")))
    assert "[computed] repetition code: RULED_OUT" in qec and "syndrome of encoded 1 = 00" in qec
    assert "COHERENCE_QUANTIZATION" in claims.list_all()

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
