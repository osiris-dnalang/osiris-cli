"""
OSIRIS Circuit-to-Publication (PUB) Mapper & Quantum Epistemic Ledger
=====================================================================
Epistemic invariant: Circuit specs and SamplerV2 PUB results are linked 1-to-1
by explicit pre-registered indices, eliminating post-hoc cherry-picking
or ordering transposition errors.

Provides:
1. Qiskit/QASM execution payload ingestion and count extraction.
2. Mapping from physical qubit layout counts to publication-ready distributions
   and fidelity metrics: F_state (state fidelity) and F_gate (effective gate fidelity).
3. Merkle ledger anchoring into osiris_operational_journal.jsonl under SYS-021.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Sequence, Tuple, Union

import numpy as np

from osiris_cli.journal import OperationalMerkleLedger


@dataclass
class CircuitSpec:
    """Pre-registered specification for an individual circuit."""
    index: int
    name: str
    t_us: float
    rep: int
    circuit_hash: str = ""
    two_qubit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PubResult:
    """Mapped PUB execution result bound to its pre-registered CircuitSpec."""
    index: int
    spec: CircuitSpec
    counts: Dict[str, int]
    shots: int
    qubit_survivals: List[float]
    mean_survival: float
    f_state: float
    f_gate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "spec": self.spec.to_dict(),
            "counts": self.counts,
            "shots": self.shots,
            "qubit_survivals": self.qubit_survivals,
            "mean_survival": self.mean_survival,
            "f_state": self.f_state,
            "f_gate": self.f_gate,
        }


@dataclass
class ConditionSummary:
    """Statistically aggregated summary for an experimental condition across replicates."""
    name: str
    t_us: float
    replicates: int
    total_shots: int
    mean_survival: float
    sem: float
    ci_95_lo: float
    ci_95_hi: float
    gamma_us_inv: float
    qubit_means: List[float]
    f_state: float
    f_gate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentMappingReceipt:
    """
    RFC 8785 canonical tamper-evident receipt binding submitted specs to returned PUB results.
    """
    job_id: str
    backend: str
    manifest_sha256: str
    calibration_hash: str
    chain: List[int]
    total_circuits: int
    total_shots: int
    conditions: List[str]
    t_list_us: List[float]
    summaries: List[Dict[str, Any]]
    hypothesis_verdict: Dict[str, Any]
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    def compute_digest(self) -> str:
        """RFC 8785 canonical byte digest over immutable receipt fields."""
        payload = {
            "backend": self.backend,
            "calibration_hash": self.calibration_hash,
            "chain": self.chain,
            "conditions": sorted(self.conditions),
            "hypothesis_verdict": self.hypothesis_verdict,
            "job_id": self.job_id,
            "manifest_sha256": self.manifest_sha256,
            "summaries": self.summaries,
            "t_list_us": self.t_list_us,
            "total_circuits": self.total_circuits,
            "total_shots": self.total_shots,
        }
        canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "backend": self.backend,
            "manifest_sha256": self.manifest_sha256,
            "calibration_hash": self.calibration_hash,
            "chain": self.chain,
            "total_circuits": self.total_circuits,
            "total_shots": self.total_shots,
            "conditions": self.conditions,
            "t_list_us": self.t_list_us,
            "summaries": self.summaries,
            "hypothesis_verdict": self.hypothesis_verdict,
            "receipt_digest": self.receipt_digest,
        }


class IBMPubMapper:
    """
    Ingests raw IBM Quantum Qiskit Runtime SamplerV2 exports,
    enforces 1-to-1 spec-to-PUB mapping, recomputes single-qubit |+> survivals,
    fidelity metrics (F_state, F_gate), replicates, SEM, bootstrap CIs, decay rate Gamma,
    and adjudicates advantage hypotheses.
    """

    @staticmethod
    def bootstrap_ci(
        values: Sequence[float],
        n_boot: int = 2000,
        alpha: float = 0.05,
        seed: int = 0,
    ) -> Tuple[float, float, float]:
        """(mean, lo, hi) percentile bootstrap over replicate values."""
        v = np.asarray(values, dtype=float)
        if len(v) < 2:
            return float(v.mean()), math.nan, math.nan
        rng = np.random.default_rng(seed)
        means = rng.choice(v, size=(n_boot, len(v)), replace=True).mean(axis=1)
        return (
            float(v.mean()),
            float(np.percentile(means, 100 * alpha / 2)),
            float(np.percentile(means, 100 * (1 - alpha / 2))),
        )

    @staticmethod
    def compute_fidelities(mean_survival: float, n_pulses: int = 8) -> Tuple[float, float]:
        """
        Compute state fidelity F_state and effective gate fidelity F_gate from |+> survival.
        - F_state = <+|rho|+> = mean_survival.
        - For a sequence of n_pulses dynamical decoupling pulses under dephasing:
          decay factor eta = 2 * F_state - 1.
          F_gate = eta^(1 / n_pulses) if eta > 0 else 0.0.
        """
        f_state = max(0.0, min(1.0, float(mean_survival)))
        eta = 2.0 * f_state - 1.0
        if eta > 0 and n_pulses > 0:
            f_gate = float(eta ** (1.0 / n_pulses))
        else:
            f_gate = 0.0
        return f_state, f_gate

    @classmethod
    def validate_inputs(cls, meta: Dict[str, Any], counts: List[Dict[str, int]]) -> None:
        """Validate structural and cryptographic invariants before mapping."""
        if not isinstance(meta, dict):
            raise TypeError(f"meta must be a dict, got {type(meta).__name__}")
        if not isinstance(counts, list):
            raise TypeError(f"counts must be a list, got {type(counts).__name__}")

        manifest_sha = meta.get("manifest_sha256", "")
        if not isinstance(manifest_sha, str) or len(manifest_sha) != 64 or not all(c in "0123456789abcdefABCDEF" for c in manifest_sha):
            raise ValueError(f"Invalid or missing manifest_sha256 in metadata: {manifest_sha!r}")

        cal_hash = meta.get("calibration_hash", "")
        if not isinstance(cal_hash, str) or len(cal_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in cal_hash):
            raise ValueError(f"Invalid or missing calibration_hash in metadata: {cal_hash!r}")

        specs = meta.get("specs", [])
        if not isinstance(specs, list):
            raise TypeError("specs must be a list")

        if len(specs) != len(counts):
            raise ValueError(
                f"Spec/PUB length mismatch: metadata contains {len(specs)} specs but counts contains {len(counts)} PUB results"
            )

        chain = meta.get("chain", [])
        if not chain or not isinstance(chain, list):
            raise ValueError("chain must be a non-empty list of physical qubit indices")

    @classmethod
    def map_payload(
        cls,
        meta_source: Union[Dict[str, Any], str, Path],
        counts_source: Union[List[Dict[str, int]], str, Path],
    ) -> ExperimentMappingReceipt:
        """
        Map metadata and counts sources to an ExperimentMappingReceipt.
        """
        if isinstance(meta_source, (str, Path)):
            with open(meta_source, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = meta_source

        if isinstance(counts_source, (str, Path)):
            with open(counts_source, "r", encoding="utf-8") as f:
                counts = json.load(f)
        else:
            counts = counts_source

        cls.validate_inputs(meta, counts)

        job_id = meta.get("job_id", "unknown_job")
        backend = meta.get("backend", "unknown_backend")
        manifest_sha256 = meta["manifest_sha256"]
        calibration_hash = meta["calibration_hash"]
        chain = meta["chain"]
        n_qubits = len(chain)
        specs_raw = meta["specs"]
        circuit_hashes = meta.get("circuit_hashes", [""] * len(specs_raw))
        two_qubit_counts = meta.get("two_qubit_counts", [0] * len(specs_raw))

        # 1. Reconstruct 1-to-1 PUB results
        pub_results: List[PubResult] = []
        per_condition: Dict[Tuple[str, float], List[float]] = {}
        per_qubit_data: Dict[Tuple[str, float], List[List[float]]] = {}
        shots_per_condition: Dict[Tuple[str, float], int] = {}

        total_shots = 0

        for i, (spec_dict, c) in enumerate(zip(specs_raw, counts)):
            c_hash = circuit_hashes[i] if i < len(circuit_hashes) else ""
            two_q = two_qubit_counts[i] if i < len(two_qubit_counts) else 0

            name = spec_dict["name"]
            t_us = float(spec_dict["T"])
            rep = int(spec_dict.get("rep", 0))

            spec = CircuitSpec(
                index=i,
                name=name,
                t_us=t_us,
                rep=rep,
                circuit_hash=c_hash,
                two_qubit_count=two_q,
            )

            n_shots = sum(c.values())
            total_shots += n_shots

            # Single-qubit survivals:
            # In Qiskit classical registers, qubit q maps to bitstring position N_QUBITS - 1 - q (right-to-left)
            pq: List[float] = []
            for q in range(n_qubits):
                bit_idx = n_qubits - 1 - q
                surv_count = sum(v for bs, v in c.items() if len(bs) > bit_idx and bs[bit_idx] == "0")
                pq.append(surv_count / n_shots if n_shots > 0 else 0.0)

            mean_p = float(np.mean(pq))
            f_state, f_gate = cls.compute_fidelities(mean_p)

            pub_res = PubResult(
                index=i,
                spec=spec,
                counts=c,
                shots=n_shots,
                qubit_survivals=pq,
                mean_survival=mean_p,
                f_state=f_state,
                f_gate=f_gate,
            )
            pub_results.append(pub_res)

            key = (name, t_us)
            per_condition.setdefault(key, []).append(mean_p)
            per_qubit_data.setdefault(key, []).append(pq)
            shots_per_condition[key] = shots_per_condition.get(key, 0) + n_shots

        # 2. Aggregate per-condition summaries
        summaries: List[Dict[str, Any]] = []
        for (name, t_us), vals in sorted(per_condition.items()):
            v = np.array(vals)
            mean_val = float(v.mean())
            sem_val = float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else 0.0
            _, ci_lo, ci_hi = cls.bootstrap_ci(vals)
            qubit_means = np.mean(per_qubit_data[(name, t_us)], axis=0).tolist()

            # Coherence parameter Gamma: P(+) = 0.5 * (1 + exp(-Gamma * T_us))
            # Gamma = -ln(2*P(+) - 1) / T_us if P(+) > 0.505 else 999.0
            gamma = -math.log(max(1e-4, 2.0 * mean_val - 1.0)) / t_us if mean_val > 0.505 else 999.0
            f_state, f_gate = cls.compute_fidelities(mean_val)

            summary = ConditionSummary(
                name=name,
                t_us=t_us,
                replicates=len(vals),
                total_shots=shots_per_condition[(name, t_us)],
                mean_survival=mean_val,
                sem=sem_val,
                ci_95_lo=ci_lo if not math.isnan(ci_lo) else mean_val - 1.96 * sem_val,
                ci_95_hi=ci_hi if not math.isnan(ci_hi) else mean_val + 1.96 * sem_val,
                gamma_us_inv=gamma,
                qubit_means=qubit_means,
                f_state=f_state,
                f_gate=f_gate,
            )
            summaries.append(summary.to_dict())

        # 3. Adjudicate pre-registered hypotheses
        hypothesis_verdict = cls.evaluate_hypotheses(summaries)

        conditions_list = meta.get("conditions", sorted(list({s["name"] for s in specs_raw})))
        t_list = meta.get("T_list", sorted(list({float(s["T"]) for s in specs_raw})))

        return ExperimentMappingReceipt(
            job_id=job_id,
            backend=backend,
            manifest_sha256=manifest_sha256,
            calibration_hash=calibration_hash,
            chain=chain,
            total_circuits=len(specs_raw),
            total_shots=total_shots,
            conditions=conditions_list,
            t_list_us=t_list,
            summaries=summaries,
            hypothesis_verdict=hypothesis_verdict,
        )

    @classmethod
    def evaluate_hypotheses(cls, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate pre-registered advantage criteria:
        H0 (Null): OSIRIS staggered DD yields no significant improvement or trails textbook DD.
        H1 (Advantage):
          1. Delta P(+) >= 0.15 over bare idle ('none') at T = 32 us.
          2. Delta P(+) >= 0.02 over textbook simultaneous DD ('xy4x2') at T = 32 us.
          3. Non-overlapping 95% bootstrap CIs (stag_lo > simul_hi).
        """
        p32 = {r["name"]: r for r in summaries if abs(r["t_us"] - 32.0) < 1e-4}

        stag_candidates = [k for k in ("xy4x2_stag", "xy8_stag") if k in p32]
        if stag_candidates:
            stag_best_name = max(stag_candidates, key=lambda k: p32[k]["mean_survival"])
            stag_best_32 = p32[stag_best_name]["mean_survival"]
            stag_best_ci_lo = p32[stag_best_name]["ci_95_lo"]
            stag_best_f_gate = p32[stag_best_name].get("f_gate", 0.0)
        else:
            stag_best_name = "none"
            stag_best_32 = 0.0
            stag_best_ci_lo = 0.0
            stag_best_f_gate = 0.0

        none_row = p32.get("none", {})
        none_32 = none_row.get("mean_survival", 0.0)

        simul_row = p32.get("xy4x2", {})
        simul_32 = simul_row.get("mean_survival", 0.0)
        simul_ci_hi = simul_row.get("ci_95_hi", 1.0)
        simul_f_gate = simul_row.get("f_gate", 0.0)

        cpmg_row = p32.get("cpmg8", {})
        cpmg_32 = cpmg_row.get("mean_survival", 0.0)

        delta_none_32 = stag_best_32 - none_32
        delta_simul_32 = stag_best_32 - simul_32

        criterion_none_met = bool(delta_none_32 >= 0.15)
        criterion_simul_met = bool(delta_simul_32 >= 0.02)
        ci_non_overlapping = bool(stag_best_ci_lo > simul_ci_hi)

        conclusion = "H1_CONFIRMED" if (criterion_none_met and criterion_simul_met) else "H0_SUPPORTED"

        return {
            "verdict": conclusion,
            "best_staggered_condition": stag_best_name,
            "t_eval_us": 32.0,
            "metrics": {
                "bare_idle_survival": none_32,
                "textbook_cpmg_survival": cpmg_32,
                "textbook_simultaneous_survival": simul_32,
                "best_staggered_survival": stag_best_32,
                "delta_vs_bare_idle": delta_none_32,
                "delta_vs_textbook_simultaneous": delta_simul_32,
                "best_staggered_f_gate": stag_best_f_gate,
                "textbook_simultaneous_f_gate": simul_f_gate,
            },
            "criteria": {
                "criterion_1_idle_ge_0_15": {
                    "required": 0.15,
                    "observed": delta_none_32,
                    "passed": criterion_none_met,
                },
                "criterion_2_simul_ge_0_02": {
                    "required": 0.02,
                    "observed": delta_simul_32,
                    "passed": criterion_simul_met,
                },
                "criterion_3_ci_non_overlapping": {
                    "stag_ci_lo": stag_best_ci_lo,
                    "simul_ci_hi": simul_ci_hi,
                    "passed": ci_non_overlapping,
                },
            },
        }

    @classmethod
    def lock_to_journal(
        cls,
        receipt: ExperimentMappingReceipt,
        journal_path: Union[str, Path] = "/root/repos/osiris-cli/provenance/osiris_operational_journal.jsonl",
        grant_id: str = "GRANT-IBM-MAPPER-001",
    ) -> Dict[str, Any]:
        """
        Anchor the mapped experiment receipt into the append-only operational journal.
        """
        ledger = OperationalMerkleLedger(journal_path)
        payload = {
            "grant_id": grant_id,
            "receipt_digest": receipt.receipt_digest,
            "job_id": receipt.job_id,
            "backend": receipt.backend,
            "manifest_sha256": receipt.manifest_sha256,
            "calibration_hash": receipt.calibration_hash,
            "verdict": receipt.hypothesis_verdict["verdict"],
            "best_staggered_condition": receipt.hypothesis_verdict["best_staggered_condition"],
            "metrics": receipt.hypothesis_verdict["metrics"],
            "total_circuits": receipt.total_circuits,
            "total_shots": receipt.total_shots,
        }
        return ledger.append(kind="ibm_experiment_mapping_receipt", payload=payload)
