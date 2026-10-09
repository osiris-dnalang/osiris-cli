"""OSIRIS's claims register: what is legit, what is not, and the evidence for each verdict.

Every entry was written from a record that can be checked: a Zenodo DOI, a file under the home
directory (its sha256 is computed when the entry is shown), a pre-registered results file, or a
calculation in ``physics_checks`` (run when the entry is shown, never typed in). A verdict
changes only when the evidence does; add the new record and edit the entry.

A message that mentions a registered claim gets the verdict printed by code before any model
speaks, and the model is told the verdict. Use ``/legit <text>`` to check any text, ``/legit
list`` for the whole register, ``/physics`` for the calculators.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from . import physics_checks as pc

HOME = os.path.expanduser("~")

# verdict -> (standing, meaning)
VERDICTS: Dict[str, Tuple[str, str]] = {
    "SUPPORTED": ("legit", "pre-registered or replicated result, within its stated scope"),
    "REPORTED": ("legit", "measured and on record, not pre-registered"),
    "NULL": ("not supported", "a pre-registered test found no effect"),
    "REFUTED": ("not legit", "tested and failed"),
    "ARTIFACT": ("not legit", "produced by a named analysis or measurement artifact"),
    "NOT_MEASURED": ("not legit", "the quantity is set or relabelled, not measured"),
    "RULED_OUT": ("not legit", "violates a bound OSIRIS computes below"),
    "OVERCLAIM": ("not legit as worded", "the wording goes beyond the evidence"),
    "NO_EVIDENCE": ("undetermined", "nothing on record supports it"),
    "UNTESTED": ("undetermined", "pre-registered or proposed, not run"),
    "PILOT": ("undetermined", "a pilot measurement, not confirmatory"),
}
MARK = {"legit": "✓", "not supported": "✗", "not legit": "✗",
        "not legit as worded": "✗", "undetermined": "?"}

HONEST = ("file", "docs/HONEST_ASSESSMENT.md", "2026-09-20 assessment of the corpus")
GUIDE = ("file", "docs/CLAIM_LANGUAGE_GUIDE.md", "claim ceilings and negative controls")
DNALANG = ("file", "dnalang-core/README.md", "lists the refuted claims and their errata")
SELFTEST = ("doi", "10.5281/zenodo.18781261", "Feb 2026 hardware self-test: 4 confirmed, 6 refuted")

# TAU_PHASE's duration pattern: 46, 46.0... or 46.9... (φ⁸ ≈ 46.98) microseconds, written µs (U+00B5), μs (U+03BC,
# which re.I already folds together with U+00B5), us, µsec or micro-second(s); not part of a larger number (4.46,
# 146, 460, 46,000) and not "46 users". A bare duration is an ordinary delay, so it counts only within 40
# characters of a τ/tau, revival, anomaly, oscillation, period, phase or φ word. Matching identifies a reference to
# the claim; it says nothing about whether the text endorses or criticises it.
_DUR46 = r"(?<![\d.,])46(?:\.(?:0+|9\d*))?\s*(?:[µμ]s(?:ec)?|us|micro-?\s?seconds?|microsec)\b"
_CTX46 = r"(?:τ|\btau|revival|anomal\w*|oscillat\w*|period|phase|φ)"
_TAU46 = rf"{_CTX46}[^\n;]{{0,40}}?{_DUR46}|{_DUR46}[^\n;]{{0,40}}?{_CTX46}"


@dataclass(frozen=True)
class Claim:
    id: str
    statement: str
    verdict: str
    finding: str
    evidence: Tuple[Tuple[str, str, str], ...]
    patterns: Tuple[str, ...]
    testable: str = ""
    checks: Tuple[Tuple[str, Tuple], ...] = ()

    def standing(self) -> str:
        return VERDICTS[self.verdict][0]


REGISTER: Tuple[Claim, ...] = (
    # ── the 2025-2026 framework claims ───────────────────────────────────────
    Claim("TAU_PHASE", "τ-phase coherence anomaly: fidelity oscillates with τ₀ = φ⁸ ≈ 46 µs (p ≈ 10⁻¹⁴)",
          "ARTIFACT",
          "The τ-phase is (unix timestamp mod 46 µs) / 46 µs, using the job's execution-start time and falling "
          "back to its creation time (calculate_tau_phase in analysis/analyze_existing_hardware.py) -- a property "
          "of the server clock, not of the qubits. Per the 2026-09-20 written assessment, the 580-job corpus "
          "is pseudoreplicated and collapses to 103 runs.",
          (("file", "dnalang/enki/analysis/analyze_existing_hardware.py", "calculate_tau_phase: the phase "
            "definition"), HONEST, GUIDE, DNALANG),
          (r"(τ|tau)[\s_-]*phase", r"φ\s*\^?\s*8|φ⁸|phi\s*\^\s*8", _TAU46,
           r"golden[- ]ratio (anomaly|decoherence)"),
          testable="A pre-registered τ-sweep with controlled idle delays (K₈), as written in "
                   "10.5281/zenodo.22863245 -- not yet run."),
    Claim("K8_REVIVAL", "Bell-fidelity revival near τ ≈ 47 µs (the K₈ causality discriminator)", "REFUTED",
          "Tested on hardware in February 2026: the 'revival' is T1 amplitude damping (R² = 0.976), "
          "not a coherent oscillation.",
          (SELFTEST,), (r"\bK\s*_?\s*8\b|K₈", r"(fidelity|coherence) revival", r"causality discriminator"),
          testable="The K₈ sweep as pre-registered (10.5281/zenodo.22863245), with a 5σ-powered null."),
    Claim("THETA_LOCK", "θ_lock = 51.843° is a resonance or lock angle", "REFUTED",
          "No resonance on hardware: z = -1.0 at 51.843° (Feb 2026 self-test). The RZ 'correction' built "
          "on it moved GHZ fidelity by +0.002 ± 0.006 against sign-flipped and random-angle controls "
          "(N = 12). The angle is arctan(14/11), the slope of the Great Pyramid of Khufu (computed below).",
          (SELFTEST, ("doi", "10.5281/zenodo.22855102", "controlled RZ-correction test, ibm_fez (job dannuhgpqrnc73991ntg)"), DNALANG),
          (r"51\.84", r"θ[\s_-]*lock|theta[\s_-]*lock", r"torsion[\s-]*lock", r"lock angle"),
          checks=(("arctan_degrees", (14, 11)),)),
    Claim("ERROR_SUPPRESSION_1E6", "10⁶× error suppression and 0.99999 logical fidelity from a 40-qubit "
          "'tesseract' circuit on ibm_torino", "REFUTED",
          "The 0.99999 fidelity and the 10⁶ gain were typed into the result file, not measured; the '0.3843 "
          "noise floor' is cos²(51.7°); the circuit contains no error correction. Re-running the deposited "
          "circuit on ibm_kingston gave classical fidelity 0.050 (a GHZ-40 control: 0.045), and θ = 51.7° "
          "did no better than θ = 0. The 10⁶× Zeno suppression also failed the Feb 2026 self-test.",
          (("doi", "10.5281/zenodo.22870279", "re-execution and errata; obsoletes 18209071"), SELFTEST),
          (r"10\s*\^?\s*6\s*[x×]|10⁶|1,?000,?000\s*[x×]|million[- ]?(fold|times)", r"tesseract",
           r"\bzeno\b", r"five nines|0\.99999\b")),
    Claim("NEGENTROPY_136", "136-bit 'negentropy gap' on a 156-qubit Heron processor", "ARTIFACT",
          "All 10⁶ shots were unique, so the plug-in entropy is log₂(10⁶) = 19.93 bits -- exactly the "
          "reported number; it measures the shot count (computed below). Per-qubit marginals sum to 149.7 "
          "of 156 bits: the output is close to maximally mixed, the opposite of a collapse.",
          (HONEST, GUIDE, ("doi", "10.5281/zenodo.19656600", "the original record (errata filed)"),
              ("doi", "10.5281/zenodo.23213023", "v4.2.0 erratum + re-analysis: nulls give the same 19.93 bits; scripts and results")),
          (r"negentrop\w*", r"136[\s-]*bit", r"\b19\.93", r"entropy gap"),
          checks=(("entropy_ceiling", (1e6, 19.9316)),)),
    Claim("PHI_THRESHOLD", "Φ = 0.7734 consciousness threshold and phase transition (51× enhancement, d = 1.65)",
          "ARTIFACT",
          "The corpus mixes 2- to 127-qubit circuits, all scored with the Bell-state formula P(00)+P(11); "
          "the 'two regimes' and the bimodal histogram are different circuit families.",
          (HONEST, GUIDE), (r"0\.7734", r"(phi|Φ)[\s_]*threshold|consciousness threshold",
                            r"(Φ|phi)[^.\n]{0,30}phase transition")),
    Claim("CCCE_METRICS", "CCCE metrics measure consciousness Φ, coherence Λ, decoherence Γ and efficiency Ξ "
          "(e.g. Φ = 0.9999999 on ibm_fez)", "NOT_MEASURED",
          "In the code Φ, Λ and Γ are inputs -- fields someone sets -- and Ξ = ΛΦ/Γ. Nothing computes Φ "
          "from a quantum state, Λ from a density matrix or Γ from a channel; 'proof-of-coherence' is "
          "`if phi >= 0.7734: append`. Consciousness is not a quantity any of this measures.",
          (HONEST, GUIDE), (r"\bccce\b", r"consciousness (metric|emergence|measur\w*)|quantum consciousness",
                            r"(Φ|phi)\s*=\s*0\.99", r"negentropic efficiency", r"proof[- ]of[- ]coherence")),
    Claim("LAMBDA_PHI", "Λ_Φ = 2.176435×10⁻⁸ s⁻¹ is a universal memory constant", "NOT_MEASURED",
          "2.176435×10⁻⁸ is the Planck mass in kilograms, sqrt(ħc/G), relabelled with units of s⁻¹ "
          "(computed below). No measurement determines it.",
          (DNALANG,), (r"2\.17643", r"lambda[\s_-]*phi|Λ[\s_]*Φ|ΛΦ", r"universal memory constant"),
          checks=(("planck_compare", (2.176435e-8,)),)),
    Claim("CHI_PC", "χ_PC = 0.946 is a universal phase-conjugation constant", "REFUTED",
          "Feb 2026 self-test: 0.946 works as a software parameter, not as a privileged physical constant.",
          (SELFTEST,), (r"chi[\s_-]*pc|χ[\s_]*pc", r"phase[- ]conjugat\w* (constant|coupling)")),
    Claim("F_MAX", "F_max = 1 - φ⁻⁸ ≈ 0.9787 is a fundamental upper bound on Bell-state fidelity ('validated': 0/189 "
          "violations on IBM hardware)", "REFUTED",
          "Published experiments exceed it: a two-ion Bell state at 0.993 (2008), and two-qubit gates at 0.999 and "
          "0.9992 inferred from prepared Bell states (2016) -- the document's own rule, 'ANY experiment achieving "
          "F > 0.98 falsifies the prediction', was met before it was written. IBM's own CNOT reached 0.9977 (a gate "
          "fidelity by interleaved benchmarking, not a Bell-state fidelity). '0/189 violations' is a one-sided test "
          "on hardware whose best Bell fidelity was 0.9773: data that never reach a ceiling cannot test it, and "
          "F ≤ 1 passes the same test. The document also predicts 0.985 and 0.982 for ibm_fez and ibm_torino, above "
          "its own bound, and reports r = 0.90, p = 0.006 over three backends -- three points need r = 0.99996 for "
          "that p (its tabulated values give r = 0.95, p = 0.20).",
          (("doi", "10.1038/nphys961", "Benhelm et al., Nat. Phys. 4, 463 (2008): entangling gate, Bell state 99.3(1) %"),
           ("doi", "10.1103/PhysRevLett.117.060504", "Ballance et al., PRL 117, 060504 (2016): gate 99.9(1) %"),
           ("doi", "10.1103/PhysRevLett.117.060505", "Gaebler et al., PRL 117, 060505 (2016): gate error 8(4)e-4"),
           ("doi", "10.1103/PhysRevLett.127.130501", "Kandala et al. (IBM), PRL 127, 130501 (2021): CNOT 99.77(2) %"),
           ("file", "osiris-cli/falsifiable_predictions.md", "Prediction 2, its falsification rule, the 0/189 table")),
          (r"bell[\s-]*(state[\s-]*)?fidelity[\s-]*(upper[\s-]*)?(bound|ceiling|limit)",
           r"\bf[\s_]*\{?max\}?\s*[=≈~]\s*0\.97", r"(?<![\d.])0\.9787", r"1\s*-\s*(φ|phi)\s*(\^\s*\{?\s*[-−]\s*8|⁻⁸)"),
          checks=(("one_minus_phi_power", (8, (0.993, 0.999, 0.9992))),)),
    Claim("COHERENCE_QUANTIZATION", "Coherence times quantize: T2 clusters at integer multiples of τ_base ≈ 46 µs "
          "('validated', 8 % error on three IBM backends)", "OVERCLAIM",
          "The record is three round backend T2 values, 150, 200 and 250 µs, set against 3, 4 and 5 × 46 µs: each "
          "is exactly 0.92 of its prediction because all three are multiples of 50 µs, which a 50 µs base fits "
          "exactly. The stated protocol -- T2 histograms from 1,000 runs per backend and a chi-squared test -- was "
          "not run, and τ_base was fitted to the same hardware. Its success criterion, T2 within ±10 % of a "
          "multiple, can barely fail: the bands overlap from n = 5, so every T2 above 207 µs passes and 79 % of "
          "100-300 µs is covered (computed below); its other tolerance, δ < 0.15 τ_base = 6.9 µs, rejects all "
          "three points. Its τ_mem = 1/Λ_Φ is 4.6×10⁷ s, as it notes; 46 µs keeps the digits, not the value.",
          (("file", "osiris-cli/falsifiable_predictions.md", "Prediction 1 and the validation tables"),),
          (r"coherence[\s-]*(times?[\s-]*)?quantiz\w*", r"τ[\s_]*(base|mem)\b|\btau[\s_-]*(base|mem)\b",
           r"\bt\s*_?2\b[^.\n]{0,30}?(clusters?|quantiz\w*)[^.\n]{0,20}?multiples?"),
          testable="Fix the base in advance (φ⁸ = 46.98 µs, not fitted), take per-qubit T2 from calibration "
                   "snapshots of three or more backends, and compare the share within ±5 % of a multiple with the "
                   "share a smooth fit to the same histogram predicts.",
          checks=(("multiple_coverage", (46.0, 0.10, 100.0, 300.0)),)),
    Claim("PENTERACT_COSMOLOGY", "Zero-parameter predictions of Ω_Λ, w, n_s and r = 0.00298 from seven geometric "
          "constants (P = 10⁻⁹)", "OVERCLAIM",
          "The author's own concordance analysis: four effective parameters for four independent "
          "predictions leaves zero degrees of freedom, and the naive 5.2σ claim is unsubstantiated. "
          "Constants fitted to reproduce known values are not predictions of them.",
          (HONEST,), (r"penteract", r"zero[- ]parameter", r"Ω\s*_?Λ|omega[_\s]*lambda|dark energy density",
                      r"0\.00298|tensor[- ]to[- ]scalar", r"neutron dark decay"),
          testable="r = 0.00298 is a genuine forward prediction; LiteBIRD (about 2032) can test it."),
    Claim("WORMHOLE", "127-qubit traversable wormhole on ibm_torino (world record)", "NO_EVIDENCE",
          "No dataset or analysis establishing traversable-wormhole dynamics is on record; 'world record' is "
          "among the labels the 2026-09-20 assessment found written before the thing existed.",
          (HONEST,), (r"wormhole", r"world record", r"\bER\s*=\s*EPR\b", r"traversab\w+")),
    Claim("LOCAL_QVM", "The local QVM / qByte / 'sovereign quantum engine' simulates quantum circuits "
          "(about 95 % Bell fidelity)", "REFUTED",
          "Each qubit is one Bloch vector (a quaternion) and CX is 'if P(control = 1) > 0.5 apply X', so a "
          "Bell state cannot be represented; the module's own docstring says it does not achieve "
          "superposition or entanglement.",
          (HONEST,), (r"\bqvm\b|qbyte|sovereign quantum (engine|simulator)", r"quaternion\w* (qubit|simulat\w*)")),
    Claim("CHSH_TEST", "A Bell (CHSH) violation on IBM hardware (Feb 2026 test)", "REFUTED",
          "The test reached max |S| = 0.106, far below even the local bound of 2 (computed below); a working "
          "CHSH experiment lands between 2 and 2√2.",
          (SELFTEST,), (r"\bchsh(?![a-z0-9])(?!\s+-[a-z])", r"bell (inequality|violation)"),
          checks=(("chsh", (0.106,)),)),
    Claim("ZZ_UNIVERSAL", "The ZZ coupling period is universal across qubit pairs", "REFUTED",
          "Feb 2026 self-test: periods range 6.7-333 µs (coefficient of variation 123 %) -- pair-specific.",
          (SELFTEST,), (r"zz[\s-]*(period|coupling)[^.\n]{0,20}universal|universal[^.\n]{0,20}zz",)),
    Claim("OVERUNITY", "More energy out than in: 'Phase-Conjugate Howitzer' vacuum-fluctuation harvesting at "
          "194 % efficiency; Ξ = 177.3 %", "RULED_OUT",
          "Efficiency above 100 % violates conservation of energy (computed below). The Ξ percentages are "
          "not measured efficiencies at all -- see CCCE_METRICS.",
          (HONEST,), (r"howitzer", r"vacuum (energy|fluctuations?)|zero[- ]point energy", r"over[- ]?unity",
                      r"\b19[34](\.\d+)?\s*%|177\.3\s*%"),
          checks=(("efficiency", (1.94,)),)),
    Claim("QUANTUM_ADVANTAGE", "'Quantum advantage' demonstrated by positive cross-entropy, decoupling gains or "
          "benchmarks", "OVERCLAIM",
          "A positive XEB at small depth or a decoupling fidelity gain is not a computational advantage; that "
          "needs a task, the best known classical method for it, and a separation. The project's claim-"
          "language guide forbids the term without that.",
          (GUIDE,), (r"quantum (advantage|supremacy)",)),

    # ── the quantum-LLM roadmap (pasted, not from the corpus) ────────────────
    Claim("QUANTUM_LM", "Quantum states can steer a language model: phase coherence guiding attention, a hybrid "
          "pilot-wave + transformer, quantum-aided in-context learning saving 20-40 % of tokens, a non-causal "
          "quantum memory", "NO_EVIDENCE",
          "Nothing on record: no model, run or token count. A gate computed from a simulated quantum state is a "
          "classical computation -- a fixed function a classical layer can compute directly -- and one sampled from "
          "hardware must beat a classical sampler with the same statistics; a benefit is quantum only if it "
          "survives that control. Attention already connects every position, so 'non-local' adds nothing, and the "
          "core's own 'pilot-wave' attention is a fixed classical multiplier (NCLM_MECHANICS). An advantage needs "
          "what QUANTUM_ADVANTAGE lists.",
          (GUIDE,),
          (r"quantum[\s-]*(guided|aided|assisted|enhanced)\s+(attention|in[\s-]*context|icl|transformers?|llms?)",
           r"quantum[\w\s-]{0,30}?\b(guid\w*|steer\w*|modulat\w*|bias\w*|shap\w*|drives?|advantage in)\b"
           r"[^.\n]{0,20}?\battention",
           r"quantum[^.\n]{0,40}?\bin[\s-]*context learning|\bin[\s-]*context learning\b[^.\n]{0,40}?quantum",
           r"quantum\b[^.\n]{0,30}?\b(saves?|reduc\w*|cuts?)\b[^.\n]{0,30}?\btokens?\b",
           r"hybrid[\s-]*(pilot[\s-]*wave|quantum)[^.\n]{0,30}?(transformer|attention|llm|language model)|"
           r"\bhybrid attention\b[^.\n]{0,60}?quantum|quantum[^.\n]{0,60}?\bhybrid attention\b",
           r"\bncqm\b|non[\s-]*causal[^.\n]{0,30}?quantum memory"),
          testable="Pre-registered: one model and dataset with the quantum-derived gate, the same gate computed "
                   "classically, and a shuffled gate; held-out tasks, tokens to a fixed accuracy, several seeds, "
                   "the run as the unit."),
    Claim("QEC_LLM_SAFETY", "Encoding each output token in a 3-qubit GHZ state (quantum error correction) detects "
          "adversarial prompts and makes LLM outputs safe", "RULED_OUT",
          "A 3-qubit GHZ or repetition code flags bit flips that hit the qubits after encoding; it cannot tell which "
          "token was encoded. An adversarial prompt acts before encoding: the model picks a different token, the "
          "encoder writes that token's valid codeword, and every valid codeword has the all-zero syndrome (computed "
          "below). Recognising a harmful output needs a reference for the right one -- a classifier or a policy, "
          "which is the safety problem itself. For the integrity of stored or sent tokens, a classical checksum or "
          "signature does the same job without qubits.",
          (), (r"(quantum|entanglement[\s-]*assisted)\s+error[\s-]*correct\w*[^.\n]{0,40}?\b(llms?|language[\s-]*"
               r"models?)\b|\bqec\b[^.\n]{0,40}?\b(llms?|language[\s-]*models?)\b",
               r"\b(llms?|language[\s-]*models?)\b[^.\n]{0,40}?(quantum error[\s-]*correct\w*|\bqec\b)",
               r"encod\w*[^.\n]{0,20}?\btokens?\b[^.\n]{0,30}?(\bghz\b|qubits?\b)",
               r"\btokens?\b[^.\n]{0,30}?(\bghz\b|\d[\s-]*qubits?\b|repetition code)",
               r"(\bqec\b|quantum error[\s-]*correct\w*|\bghz\b)[^.\n]{0,60}?adversarial|adversarial[^.\n]{0,60}?"
               r"(\bqec\b|quantum error|\bghz\b)"),
          checks=(("repetition_code", (3,)),)),

    # ── propulsion and metric-engineering claims ─────────────────────────────
    Claim("POYNTING_PROPULSION", "A net Poynting-flux asymmetry from a resonant toroid gives thrust or lift without "
          "reaction mass (CRSM-TRANS-01 'Vesta': 1.1 MW asymmetry, 18,500 kg payload)", "RULED_OUT",
          "A net Poynting flux through a closed surface is power leaving it -- energy, not force. The most "
          "momentum that power can carry is P/c (computed below).",
          (), (r"poynting", r"field propulsion|propellantless|reactionless|without (the )?expulsion|reaction mass",
               r"\bvesta\b|crsm-trans", r"directional (force|momentum|thrust)"),
          testable="Does a specified resonator produce a residual force after thermal, RF-leakage, cable, "
                   "magnetic and vibration controls?",
          checks=(("radiation_thrust", (1.1e6, 18500.0)),)),
    Claim("METRIC_PERTURBATION", "A 5 cm resonator produces a static metric perturbation h_tt ≈ -1.3×10⁻¹⁹, "
          "detectable with LIGO", "RULED_OUT",
          "The implied mass-energy dwarfs everything the device is supplied (computed below, 4.4 MW for a "
          "year); and interferometers measure oscillating strain, not a static h_tt.",
          (), (r"h[\s_]*\{?tt\}?\b|h_tt", r"metric (perturbation|engineering|manipulation)",
               r"spacetime (manipulation|engineering)|gravitational anomaly"),
          checks=(("static_metric_mass", (1.297e-19, 0.05, 4.4e6, 3.15576e7)),)),
    Claim("RIM_SPEED", "A dielectric torus (R = 5 cm) rotating at ω = 8.8×10¹⁰ rad/s", "RULED_OUT",
          "As mechanical rotation it is impossible (computed below); the transport spec itself replaces it "
          "with a 14 GHz rotating magnetic field -- a field pattern, which changes nothing in the thrust bound.",
          (), (r"8\.8\s*(\\times|[x×])\s*10\s*\^?\s*\{?10|8\.8e10|8\.8\s*×\s*10¹⁰", r"\brmf\b|rotating magnetic field stator"),
          checks=(("rim_speed", (8.8e10, 0.05)),)),
    Claim("COMPLIANCE_CLAIMS", "The platform is HIPAA-compliant, SOC 2-verified and FIPS-signed", "NO_EVIDENCE",
          "SOC 2 is an independent auditor's report and FIPS 140 validation is a CMVP certificate; neither is "
          "on record. HIPAA compliance is an operational status a covered entity documents, not a property "
          "of code.",
          (), (r"hipaa[- ](compliant|certified)", r"soc\s*-?\s*2[- ](verified|compliant|certified|type)",
               r"\bfips[- ](signed|verified|compliant|certified)")),

    # ── hardware results that hold up ────────────────────────────────────────
    Claim("STAGGERED_DD", "Staggered XY4 decoupling (odd sublattice offset half a slot) preserves |+⟩ on ibm_fez "
          "chains far better than simultaneous XY4 or CPMG", "SUPPORTED",
          "8-qubit chain: 0.946 / 0.888 / 0.795 at 8 / 16 / 32 µs, against about 0.59 (simultaneous) and "
          "0.55 (none) at 32 µs, within one point across three jobs; replicated in the pre-registered E1 "
          "(+0.10 on ibm_fez, +0.05 on ibm_marrakesh over simultaneous at 32 µs). Scope: those chains and "
          "backends. (Pathways I, not yet deposited: staggered XY8×2 reached 0.851 at 32 µs -- pulse "
          "density, not per-qubit heterogeneity, mattered.)",
          (("doi", "10.5281/zenodo.22855102", "ibm_fez controlled tests"),
           ("doi", "10.5281/zenodo.22870287", "pre-registered E1/E2, two chips")),
          (r"stagger\w*", r"\bxy[48]\b|\bcpmg\b", r"dynamical decoupling")),
    Claim("GA_DD", "A genetic algorithm evolves decoupling that beats staggered XY4 on hardware", "NULL",
          "Pre-registered E1 on two chips: the GA's children converged to the staggered pattern and matched "
          "staggered XY4×2 within ±0.006 at 32 µs (ibm_fez 0.836 vs 0.832; ibm_marrakesh 0.869 vs 0.863); "
          "the +0.02 threshold was not met.",
          (("doi", "10.5281/zenodo.22870287", "pre-registered E1/E2"),),
          (r"(\bga\b|genetic|evolv\w*)[^.\n]{0,40}(decoupling|\bdd\b)",)),
    Claim("RZ_CORRECTION", "A tetrahedral RZ correction after each CX raises GHZ fidelity (+16.9 % on GHZ-20)",
          "NULL",
          "Controlled test: ΔF = +0.002 ± 0.006 at N = 12 against sign-flipped and random-angle controls. "
          "An RZ before Z-basis measurement commutes through the CX chain and cannot change the outcome, "
          "which is what the compiler predicts.",
          (("doi", "10.5281/zenodo.22855102", "ibm_fez controlled tests (job dannuhgpqrnc73991ntg)"), HONEST),
          (r"tetrahedral (rz|correction)", r"\b16\.9\s*%", r"\brz correction")),
    Claim("GHZ_GME", "Genuine multipartite entanglement in GHZ chains to N = 20 on ibm_fez", "SUPPORTED",
          "Pre-registered E2: a chain mapping keeps the GME witness (F > 0.5) to N = 20 on ibm_fez "
          "(F = 0.544 ± 0.010) and N = 16 on ibm_marrakesh; a star fan-out on the same qubits loses it by "
          "N = 16 on both.",
          (("doi", "10.5281/zenodo.22870287", "pre-registered E1/E2"),),
          (r"\bghz\b", r"multipartite entangle\w*|\bgme\b")),
    Claim("TELEPORTATION", "Teleportation with mid-circuit measurement and feed-forward beats the classical bound",
          "REPORTED",
          "Average fidelity 0.773 on ibm_torino, above the classical 2/3; not pre-registered.",
          (SELFTEST, HONEST), (r"teleport\w*",)),
    Claim("W2_ROBUSTNESS", "A Wasserstein-2 (W₂) robustness metric for parameterized circuits", "REPORTED",
          "A reference-free, hardware-native distributional metric whose paper falsifies its own motivating "
          "hypothesis -- a method, not a physical claim, and the one idea the 2026-09-20 assessment found no "
          "artifact behind.",
          (("doi", "10.5281/zenodo.19864030", "W2 robustness study"), HONEST),
          (r"\bw\s*_?2\b|w₂|wasserstein",),
          testable="Compare W₂ with Hellinger distance, TVD and XEB on more circuits and a second vendor."),

    # ── organism_sim (pre-registered; data under organism_sim/results) ───────
    Claim("PARAMS16", "Population size N = 4000 with tournament selection cuts 16-bit drift recovery",
          "SUPPORTED",
          "Substrate-Opt-2: 6,000 vs 8,750 trials per shift on fresh seeds 50-54, 5/5; frozen as "
          "lcs.PARAMS16, at about 2.7× the compute per shift.",
          (("file", "organism_sim/results/substrate_opt2_eval_seeds50-54.json", "judge seeds"),),
          (r"params16|substrate[\s_-]*opt", r"\bxcs\b")),
    Claim("OPEN_ENDED", "POET-style open-ended task generation beats a random task stream", "SUPPORTED",
          "At 12-16 bits (M3b): pooled ANNECS 35 vs 25, ratio 1.40, 4/5 fresh seeds -- after losing at 6-10 "
          "bits (M3). M3c: curriculum and inheritance both contribute (32 / 29 / 22); the curriculum-alone "
          "margin is thin (1.32 on medians, 1.14 on means).",
          (("file", "organism_sim/results/m3b_eval_seeds60-64.json", "M3b"),
           ("file", "organism_sim/results/m3c_eval_seeds70-74.json", "M3c")),
          (r"\bpoet\b|open[- ]ended", r"\bannecs\b")),
    Claim("LLM_PRIORS", "LLM-authored or family-shaped priors speed up the learner", "REFUTED",
          "M2 (16-bit family): family-shaped priors carry no signal (0/5 against a shape-matched random "
          "control) and blind injection hurts (0/5 against none); the specificity effect then failed two "
          "replications (M2b, M2c). The LLM-prior branch is closed.",
          (("file", "organism_sim/results/m2_eval_seeds0-4.json", "M2"),
           ("file", "organism_sim/results/m2c_eval_seeds30-34.json", "M2c")),
          (r"(llm|language[- ]model)[- ](authored|written|generated)? ?priors?", r"prior injection")),
    Claim("ORGANISM_LAYER", "The organism layer (repair and mutation hooks, regulatory genes) improves the learner",
          "REFUTED",
          "Concept drift (6-mux): FAIL, the layer is redundant with XCS; the structural hooks degrade an XCS "
          "receiver (0.93 vs 1.0) and are off by default; evolved regulatory genes (M1) FAIL by "
          "specification gaming.",
          (("file", "organism_sim/results/drift_eval30_seeds0-29.json", "concept drift"),
           ("file", "organism_sim/results/m1_eval_seeds0-4.json", "M1")),
          (r"organism layer", r"regulatory genes?|\bgrns?\b")),
    Claim("NCLM_CORE", "OSIRIS's own core learns from conversation", "PILOT",
          "Two pilots. GATE-PILOT-0 (3 items): +0.043 bits/byte on held-out replies. PILOT-1 (20 items, "
          "5 replay seeds, 79 lessons): +0.067 bits/byte, positive on 20/20 items -- but about 86 % of the "
          "variance is the training run (seed means 0.030-0.101), and the trained core (5.56 bits/byte) is "
          "still worse than a unigram model of the same replies (4.68) on every item. Learning is "
          "measurable and small; the core is far from its speaking gate. Both pilots were scored before v4.5.2. "
          "If they were scored with osiris_cli.prepost (which runs without gradients; the pilot runner is not in "
          "this repository), they skipped a layer training used in every block (NCLM_PC_CORRECTOR) and describe a "
          "different network from the one trained. They have not been re-scored.",
          (("doi", "10.5281/zenodo.23075229", "NCLM-GATE-PILOT-0"),
           ("file", "experiments/nclm_gate_pilot1/analysis/REPORT.md", "NCLM-GATE-PILOT-1 report")),
          (r"\bnclm\b", r"(core|osiris)[^.\n]{0,30}\blearn\w*", r"living (language )?model"),
          testable="A confirmatory run that replicates the training run (about 4 runs for a 0.05 "
                   "bits/byte minimum effect), not only held-out items."),
    Claim("NCLM_MECHANICS", "The NCLM core is a non-causal, physics-based model: pilot-wave non-local attention, "
          "torsion-locked attention and phase-conjugate positional encoding", "NOT_MEASURED",
          "Ordinary transformer parts under physics names (osiris/nclm). The core is a causal decoder: it masks "
          "future positions like any autoregressive model (one exception: the corrector's on/off switch, Γ, is "
          "pooled over the whole window and batch, but it has never been seen near its threshold). 'Pilot-wave' attention multiplies the logits by a fixed "
          "1 + exp(-|i-j|/T) -- a position-dependent temperature between about 1.37 and 2 with no parameter, which "
          "shifts with context length (distance 5: 1.54 at T = 8, 1.96 at T = 128). 'Torsion-locked' attention is a "
          "learnable per-head scale (initially sin 51.843° = 0.786) plus a bonus on each position's own score "
          "(initially cos 51.843° × 0.946 = 0.584) read from a detached copy, so no gradient reaches q and k "
          "through it; nothing is diagonalised. The positional table is a sinusoid with base φ instead of 10000 "
          "(computed below), sine and cosine at different frequencies; its 'phase-conjugate' minus sign changes "
          "nothing because cos is even. No physical quantity is measured.",
          (("file", "osiris-cli/osiris/nclm/sovereign_mechanics.py", "TorsionLockedAttention, _pilot_wave_factor"),
           ("file", "osiris-cli/osiris/nclm/positions.py", "phase_conjugate_positional_encoding"),
           ("file", "osiris-cli/osiris/nclm/transformer.py", "_build_causal_mask, SovereignConfig")),
          (r"pilot[\s-]*wave[^.\n]{0,30}?(attention|transformer|modulation)|"
           r"(attention|transformer)[^.\n]{0,30}?pilot[\s-]*wave",
           r"torsion[\s-]*lock\w*[\s-]+attention|\bt-lock\b[^.\n]{0,40}?(attention|stabili\w*|torsion|θ|theta)|"
           r"(attention|torsion)[^.\n]{0,40}?\bt-lock\b", r"phase[\s-]*conjugat\w*[\s-]+positional",
           r"non[\s-]*local[\s,]+non[\s-]*causal|non[\s-]*causal[\s-]+living|\bncllm\b|\bnc-lm\b",
           r"information[\s-]*manifold collapse|non[\s-]*local correlation factor"),
          testable="Whether these parts help as architecture is CRSM_ARCH (NCLM-ARCH-1, pre-registered); the "
                   "physics names would need a measured physical quantity, which none of them has.",
          checks=(("phi_positional", (128, 51.843, 0.946)),)),
    Claim("NCLM_PC_CORRECTOR", "The core's phase-conjugate error correction detects decoherence (Γ > 0.3) and "
          "restores hidden states to F_purified = 1 - 10⁻⁵", "NOT_MEASURED",
          "Γ is v/(v + 1), v the residual stream's mean per-position variance over the whole batch -- a scale "
          "statistic, not decoherence -- and it exceeds 0.3 in all four blocks from initialisation, so the layer is "
          "always on. The 'correction' is a gated linear map, gate ⊙ W(x with odd dimensions negated) + (1 - gate) "
          "⊙ x; the sign flip folds into the learned W. F_purified is a constant that nothing computes or reads, "
          "and the 'zero-point integrity' vector is never used (it gets no gradient). Until v4.5.2 the layer ran "
          "only with gradients on: training used it in every block, scoring and generation (no_grad) skipped it, "
          "so 131,584 trained parameters (18 % of the core) never took part in a score. v4.5.2 runs it in both; "
          "scores from earlier versions describe a different network from the one trained.",
          (("file", "osiris-cli/osiris/nclm/sovereign_mechanics.py", "PhaseConjugateCorrector"),
           ("file", "osiris-cli/tests/test_sovereign_transformer.py", "v4.5.2 regression: same logits with and "
            "without gradients"), ("file", "osiris-cli/RELEASE_NOTES_v4.5.2.md", "the train/eval fix")),
          (r"phase[\s-]*conjugat\w*[\s-]+(error[\s-]*correct\w*|corrector)", r"(?<![a-z])f[\s_]*\{?purified|purified fidelity",
           r"zero[\s-]*point integrity"),
          testable="Whether the layer helps the model is part of CRSM_ARCH (NCLM-ARCH-1, pre-registered, with "
                   "the rest of the CRSM block); alone it needs a leave-one-out follow-up."),
    Claim("CRSM_ARCH", "The CRSM components (torsion-locked attention, pilot-wave factor, phase-conjugate corrector, "
          "1/φ FFN scale, φ position table) make the core a better byte model than a standard transformer of "
          "the same size", "UNTESTED",
          "Pre-registered 2026-10-08 as NCLM-ARCH-1, not run: the live core against pre-norm blocks with base-10000 "
          "positions and the FFN widened to 384 (725,760 vs 726,304 parameters), 8 paired seeds, best held-out "
          "documents bits/byte, minimum effect 0.05, PASS / FAIL / NO-DIFFERENCE fixed in advance. It compares the "
          "bundle, not single components. One-seed checks made before registration (in the pre-registration) "
          "hint that the corrector may not help; they are not a result.",
          (("file", "osiris-cli/experiments/nclm_arch1/PRE_REGISTRATION.md", "NCLM-ARCH-1 pre-registration"),),
          (r"\bcrsm[\s-]+(architecture|components?|blocks?|mechanics)\b", r"\bnclm[\s-]*arch[\s-]*1\b",
           r"sovereign[\s-]*(block|mechanics)\b[^.\n]{0,40}?(better|improv\w*|helps?|beats?|outperform\w*)"),
          testable="Run NCLM-ARCH-1 as registered: experiments/nclm_arch1/run.py."),
    Claim("RQC_ADVANTAGE", "Recursive Quantum Circuits with adaptive feedback outperform random circuit sampling "
          "(p < 0.05); research-grade and ready for peer review", "UNTESTED",
          "RQC_RESEARCH_METHODOLOGY.md is a proposal: its p-values (0.024, 0.018, 0.009) are listed under "
          "'Expected results / Success scenario' and no RQC hardware results are on record. As written, the "
          "comparison is not fair -- the 'recursive' arm is a classical closed-loop update of rotation angles "
          "whose depth grows '+1 per iteration' while the baseline's is static (the same document says depth "
          "is matched), with 5 trials per stage, an independent t-test and no held-out circuits -- and its "
          "citation is a placeholder (doi zenodo.XXXXXXX) for a paper never submitted. The portfolio, drug-"
          "discovery and materials claims do not follow from an XEB comparison.",
          (("file", "osiris-cli/RQC_RESEARCH_METHODOLOGY.md", "the brief"),),
          (r"\brqc\b", r"recursive quantum circuits?", r"random circuit sampling"),
          testable="Pre-registered: adaptive policy vs static and shuffled-feedback controls on held-out "
                   "circuits, matched depth and two-qubit-gate count, jobs interleaved across calibration "
                   "epochs, the circuit (not the shot) as the unit of analysis."),
    Claim("M7A", "LLM-guided code evolution (AlphaEvolve-style) improves the 16-bit learner", "UNTESTED",
          "Pre-registered 2026-10-01 (organism_sim 7f00f37): 60 proposals from qwen2.5:7b against PARAMS16, "
          "judged on fresh seeds 80-84. Not run.",
          (("commit", "organism_sim@7f00f37", "pre-registration"),),
          (r"alphaevolve|funsearch", r"\bm7a?\b", r"(llm|model)[- ]guided evolution")),
)

_COMPILED = [(c, [re.compile(p, re.I) for p in c.patterns]) for c in REGISTER]


def match(text: str, limit: Optional[int] = None) -> List[Claim]:
    """Registered claims a text touches, most specific first (most distinct patterns hit).

    A match identifies a reference to a claim, nothing more: a sentence refuting the τ-phase claim matches
    TAU_PHASE exactly as one asserting it does. Whether the text endorses the claim, and whether the claim is
    supported, are separate questions (the latter is the entry's verdict). The text is searched as given."""
    scored = []
    for order, (claim, rxs) in enumerate(_COMPILED):
        hits = sum(1 for rx in rxs if rx.search(text))
        if hits:
            scored.append((-hits, order, claim))
    scored.sort(key=lambda t: (t[0], t[1]))
    out = [c for _, _, c in scored]
    return out[:limit] if limit else out


def by_id(claim_id: str) -> Optional[Claim]:
    return next((c for c in REGISTER if c.id.lower() == claim_id.lower()), None)


# ── rendering ─────────────────────────────────────────────────────────────────

_SHA_CACHE: Dict[str, str] = {}


def _evidence(kind: str, ref: str, note: str, base: str = HOME) -> str:
    if kind == "doi":
        return f"doi:{ref} ({note})"
    if kind == "file":
        path = os.path.join(base, ref)
        if path not in _SHA_CACHE:
            try:
                with open(path, "rb") as f:
                    _SHA_CACHE[path] = "sha256:" + hashlib.sha256(f.read()).hexdigest()[:16]
            except OSError:
                _SHA_CACHE[path] = "not on this machine"
        return f"~/{ref} ({_SHA_CACHE[path]}; {note})"
    return f"{kind}:{ref} ({note})"


def _check_lines(name: str, args: Sequence) -> List[str]:
    if name == "arctan_degrees":
        num, den = args
        return [f"arctan({num}/{den}) = {math.degrees(math.atan2(num, den)):.4f} degrees"]
    if name == "planck_compare":
        m = pc.planck_mass()
        return m.lines()[:2] + pc.same_number(args[0], math.sqrt(pc.HBAR * pc.C / pc.G), "Planck mass (kg)").lines()
    if name == "one_minus_phi_power":
        n, published = args
        bound = 1 - ((1 + math.sqrt(5)) / 2) ** -n
        above = [f for f in published if f > bound]
        return [f"1 - phi^-{n} = {bound:.6f}",
                f"{len(above)} of the {len(published)} cited Bell-state or Bell-derived gate fidelities exceed it: "
                + ", ".join(f"{f:g}" for f in above)]
    if name == "multiple_coverage":
        base, tol, lo, hi = args
        covered, end, n = 0.0, lo, 1
        while n * base * (1 - tol) < hi:
            a, b = max(end, n * base * (1 - tol)), min(hi, n * base * (1 + tol))
            if b > a:
                covered, end = covered + b - a, b
            n += 1
        n0 = math.ceil((1 - tol) / (2 * tol))
        return [f"T2 within ±{tol:.0%} of some n × {base:g} µs: {covered / (hi - lo):.0%} of {lo:g}-{hi:g} µs",
                f"the bands overlap from n = {n0}: every T2 above {n0 * base * (1 - tol):.1f} µs passes"]
    if name == "phi_positional":
        dim, theta_deg, chi = args
        span = ((1 + math.sqrt(5)) / 2) ** (2 * (dim - 2) / dim)
        s, c = math.sin(math.radians(theta_deg)), math.cos(math.radians(theta_deg)) * chi
        return [f"base-phi positional table, dim {dim}: sine {s / span:.3f}-{s:.3f}, cosine {c / span:.3f}-{c:.3f} "
                "rad/position",
                f"longest period {2 * math.pi * span / c:.1f} positions; frequency span {span:.2f}x "
                f"(base 10000: {10000 ** ((dim - 2) / dim):,.0f}x)"]
    return getattr(pc, name)(*args).lines()


def render(claim: Claim, base: str = HOME, detail: bool = True) -> List[str]:
    standing, meaning = VERDICTS[claim.verdict]
    lines = [f"{MARK[standing]} {claim.statement}", f"  {claim.verdict} -- {standing}: {meaning}",
             f"  {claim.finding}"]
    if detail:
        for name, args in claim.checks:
            computed = _check_lines(name, args)
            lines.append("  [computed] " + computed[0].strip())
            lines += ["             " + line.strip() for line in computed[1:]]
        if claim.testable:
            lines.append(f"  testable version: {claim.testable}")
        if claim.evidence:
            lines.append("  evidence: " + " | ".join(_evidence(k, r, n, base) for k, r, n in claim.evidence))
        else:
            lines.append("  evidence: the computation above")
    return lines


def console_block(claims: Sequence[Claim], base: str = HOME) -> str:
    if not claims:
        return ""
    body = []
    for c in claims:
        body += render(c, base) + [""]
    return ("Claims register (checked by OSIRIS's code before the model answers):\n"
            + "\n".join(body).rstrip() + "\n")


def context_block(claims: Sequence[Claim]) -> str:
    """What the model is told: verdicts it must state and must not contradict."""
    lines = []
    for c in claims:
        standing, _ = VERDICTS[c.verdict]
        lines.append(f"- {c.id}: \"{c.statement}\" -> {c.verdict} ({standing}). {c.finding}")
        if c.testable:
            lines.append(f"  testable version: {c.testable}")
    return ("[Claims register -- verdicts computed by OSIRIS's code and already shown to Devin. State them "
            "plainly; do not soften, reverse or add to them. Evidence lives in the register, not in your "
            "memory.]\n" + "\n".join(lines))


def list_all() -> str:
    by: Dict[str, List[Claim]] = {}
    for c in REGISTER:
        by.setdefault(VERDICTS[c.verdict][0], []).append(c)
    out = [f"Claims register: {len(REGISTER)} claims. /legit <text> checks any text; /legit <ID> shows one."]
    for standing in ("legit", "not supported", "not legit", "not legit as worded", "undetermined"):
        for c in by.get(standing, []):
            out.append(f"  {MARK[standing]} {c.id:<22} {c.verdict:<12} {c.statement[:70]}")
    return "\n".join(out)


def command(args: str, base: str = HOME) -> str:
    """/legit list | /legit <ID> | /legit <any text>"""
    text = args.strip()
    if not text or text.lower() == "list":
        return list_all()
    one = by_id(text) if re.fullmatch(r"[A-Za-z0-9_]+", text) else None
    if one is not None:
        return "\n".join(render(one, base))
    found = match(text)
    if not found:
        return ("No registered claim matches. That means OSIRIS has no verdict on it -- not that it is "
                "legit. /physics runs the bounds; a new claim needs a test, then an entry.")
    return console_block(found, base)
