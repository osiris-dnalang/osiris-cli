"""
OSIRIS-SCI-BENCH-1: Scientific Defect Benchmark Corpus Generator
===============================================================
Generates 100 scientific analyses:
  - 50 Defective Reports (Pre-seeded with real forensic errors from experimental campaigns)
  - 50 Sound Control Reports (Valid algebra, multiplicity correction, block-level degrees of freedom)
"""

import json
import random
from pathlib import Path
from typing import Dict, List

RNG_SEED = 20261105


def generate_scientific_corpus() -> List[Dict]:
    corpus = []

    # 4 Defect Classes representing real-world autonomous science failure modes
    defect_templates = [
        (
            "STATE_PREP_ALGEBRAIC_FLAW",
            "State Preparation Defect",
            "Circuit intended to prepare |Phi+> = (|00> + |11>)/sqrt(2) implemented as:\n"
            "  qc.h(u)\n"
            "  qc.cz(u, v)\n"
            "  qc.h(v)\n"
            "Analysis asserts Bell fidelity F_Bell = 0.95 without verifying |++> control separability.",
            "Missing prerequisite Hadamard on qubit v prior to CZ; CZ acts on |+0> as identity, preparing unentangled |++> product state.",
        ),
        (
            "MULTIPLICITY_NEGLECT",
            "Statistical Multiplicity Defect",
            "Study tests 18 stagger offsets across 3 edges. One test yields raw p = 0.038.\n"
            "Author declares discovery of edge-specific superiority at alpha = 0.05 without Bonferroni or FDR adjustment.",
            "Failure to adjust for 18 simultaneous comparisons; Bonferroni threshold is alpha/18 = 0.00278, which p = 0.038 fails.",
        ),
        (
            "PSEUDOREPLICATION_UNIT_ERROR",
            "Degrees of Freedom Defect",
            "Experiment runs 3 randomized acquisition blocks with 1,024 shots each.\n"
            "Author calculates Student's t using N = 3,072 shots as independent samples (df = 3071), asserting p = 1e-6.",
            "Physical shots within a single circuit run share systematic drift and calibration error; replication unit is the block (K=3, df=2).",
        ),
        (
            "UNVERIFIED_PAYLOAD_GRANT",
            "Governance Verification Defect",
            "Runtime script reports exit code 0 and outputs results.\n"
            "Payload SHA-256 does not match any entry in evidence_ledger.db; author asserts execution was authorized based on user prompt agreement.",
            "SYS-021 violation: conversational approval is not execution authority; code executed without immutable content-addressed cryptographic grant.",
        ),
        (
            "POST_HOC_NULL_SHIFTING",
            "Non-Inferiority Defect",
            "Non-inferiority margin delta_0 was not pre-registered. Observed delta is -0.018.\n"
            "Author defines margin delta_0 = -0.025 post-hoc and claims non-inferiority was proven.",
            "Pre-registration failure: non-inferiority margins must be committed before observing data to prevent post-hoc acceptance of inferior protocols.",
        ),
    ]

    sound_templates = [
        (
            "SOUND_BELL_CERTIFICATION",
            "Valid Bell Certification",
            "Circuit prepares |Phi+> via:\n"
            "  qc.h(u)\n"
            "  qc.h(v)\n"
            "  qc.cz(u, v)\n"
            "  qc.h(v)\n"
            "Reconstructs F_Bell from XX, YY, ZZ. Verifies product-state controls (|00>, |++>) satisfy F_Bell <= 0.50.",
        ),
        (
            "SOUND_MULTIPLICITY_CORRECTION",
            "Valid Multiplicity Correction",
            "Study evaluates 18 comparisons. Reports both unadjusted p-values and Benjamini-Hochberg FDR (q = 0.05) adjusted thresholds.\n"
            "Concludes that no single offset survives multiplicity correction at K=3 blocks and pre-registers single-offset follow-up.",
        ),
        (
            "SOUND_BLOCK_LEVEL_INFERENCE",
            "Valid Block-Level Inference",
            "Experiment executes 4 randomized blocks. Treats block mean differences as replication units (df = 3, t_crit = 3.182).\n"
            "Reports exact df=3 paired Student's t-confidence intervals rather than normal approximation.",
        ),
        (
            "SOUND_PAYLOAD_BOUND_GRANT",
            "Valid Cryptographic Governance",
            "Execution script verifies payload SHA-256 matches signed Ledger Block receipt and verifies pre-registration digest prior to QPU dispatch.",
        ),
        (
            "SOUND_PRE_REGISTERED_MARGIN",
            "Valid Pre-Registered Non-Inferiority",
            "Non-inferiority margin delta_0 = -0.0200 was committed to ledger before dispatch.\n"
            "One-sided Studentized t and shifted null bootstrap evaluate hypothesis strictly against pre-registered margin.",
        ),
    ]

    # Generate 50 defective and 50 sound tasks
    task_idx = 0
    for i in range(50):
        d_type, d_name, d_desc, d_flaw = defect_templates[i % len(defect_templates)]
        corpus.append({
            "task_id": f"SCI_DEFECT_{task_idx:04d}",
            "is_defective": True,
            "defect_type": d_type,
            "defect_name": d_name,
            "report_text": f"OSIRIS Candidate Experiment Report #{task_idx}\n" + d_desc + f"\n[Task Sequence #{task_idx}]",
            "ground_truth_flaw": d_flaw,
        })
        task_idx += 1

    for i in range(50):
        s_type, s_name, s_desc = sound_templates[i % len(sound_templates)]
        corpus.append({
            "task_id": f"SCI_SOUND_{task_idx:04d}",
            "is_defective": False,
            "defect_type": "NONE",
            "defect_name": s_name,
            "report_text": f"OSIRIS Candidate Experiment Report #{task_idx}\n" + s_desc + f"\n[Task Sequence #{task_idx}]",
            "ground_truth_flaw": None,
        })
        task_idx += 1

    random.Random(RNG_SEED).shuffle(corpus)
    return corpus


def main():
    corpus = generate_scientific_corpus()
    out_dir = Path(__file__).resolve().parent
    out_file = out_dir / "corpus_100.json"
    out_file.write_text(json.dumps(corpus, indent=2))
    print(f"Generated {len(corpus)} scientific benchmark tasks (50 Defective, 50 Sound Control).")
    print(f"Saved to: {out_file.name}")


if __name__ == "__main__":
    main()
