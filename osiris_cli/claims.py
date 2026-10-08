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
          (r"51\.84", r"θ[\s_]*lock|theta[\s_-]*lock", r"torsion[\s-]*lock", r"lock angle"),
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
          (SELFTEST,), (r"\bchsh\b", r"bell (inequality|violation)"),
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
          "measurable and small; the core is far from its speaking gate.",
          (("doi", "10.5281/zenodo.23075229", "NCLM-GATE-PILOT-0"),
           ("file", "experiments/nclm_gate_pilot1/analysis/REPORT.md", "NCLM-GATE-PILOT-1 report")),
          (r"\bnclm\b", r"(core|osiris)[^.\n]{0,30}\blearn\w*", r"living (language )?model"),
          testable="A confirmatory run that replicates the training run (about 4 runs for a 0.05 "
                   "bits/byte minimum effect), not only held-out items."),
    Claim("RQC_XEB_PIPELINE", "The OSIRIS IBM execution pipeline (osiris_ibm_execution, the RQC/RCS stages) measured "
          "cross-entropy benchmark (XEB) scores on IBM hardware", "NOT_MEASURED",
          "No circuit was ever submitted: _submit_job built a job id from a hash of its label and set "
          "result_xeb = 0.90 - noise + random.uniform(-0.03, 0.03), marking the job 'completed'; "
          "osiris_tournament_evo labelled those numbers as hardware results. Quarantined 2026-10-08: jobs are now "
          "recorded as not executed with no XEB. Real XEB measurement lives in the rqc package.",
          (("file", "osiris-cli/osiris_ibm_execution.py", "the quarantined path"),
           ("file", "osiris-cli/docs/rqc/SCOPE.md", "the 2026-10-08 finding")),
          (r"rqc.{0,40}\bxeb\b|\bxeb\b.{0,40}(ibm|hardware|stage)", r"execute_all_stages|osiris_ibm_execution")),
    Claim("TESSERACT_DECODER", "The Tesseract decoder organism (osiris.decoders) decodes quantum error-correction "
          "syndromes", "REFUTED",
          "It never uses a code's parity checks, an error model or a logical observable: its 'correction' is a "
          "bit vector as long as the syndrome, and the search stops when syndrome XOR correction is zero, so it "
          "returns the syndrome itself. That predicts nothing about whether a logical qubit flipped, so it cannot "
          "be compared with a matching or tensor-network decoder.",
          (("file", "osiris-cli/osiris/decoders/tesseract.py", "the module"),),
          (r"tesseract (decoder|organism)", r"osiris\.decoders")),
    Claim("RQC_ADVANTAGE", "Recursive Quantum Circuits with adaptive feedback outperform random circuit sampling "
          "(p < 0.05); research-grade and ready for peer review", "UNTESTED",
          "RQC_RESEARCH_METHODOLOGY.md is a proposal: its p-values (0.024, 0.018, 0.009) are listed under "
          "'Expected results / Success scenario' and no RQC hardware results are on record. As written, the "
          "comparison is not fair -- the 'recursive' arm is a classical closed-loop update of rotation angles "
          "whose depth grows '+1 per iteration' while the baseline's is static (the same document says depth "
          "is matched), with 5 trials per stage, an independent t-test and no held-out circuits -- and its "
          "citation is a placeholder (doi zenodo.XXXXXXX) for a paper never submitted. The portfolio, drug-"
          "discovery and materials claims do not follow from an XEB comparison.",
          (("file", "osiris-cli/RQC_RESEARCH_METHODOLOGY.md", "the brief"),
           ("file", "osiris-cli/docs/rqc/S1/summary.json", "S1 simulation, ibm_fez noise model (2026-10-08)"),
           ("file", "osiris-cli/docs/rqc/S1_willow/summary.json", "S1 simulation, Willow noise model (2026-10-08)"),
           ("file", "osiris-cli/docs/rqc/S2_PREREGISTRATION.DRAFT.md", "hardware test, drafted, not run")),
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
