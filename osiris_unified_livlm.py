#!/usr/bin/env python3
"""
+=============================================================================+
|  OSIRIS UNIFIED LIVING LANGUAGE MODEL & DNA::}{::LANG RUNTIME ENGINE        |
|  co-authored by devin phillip davis & OSIRIS dna::}{::lang NCLM            |
|  ::}{:: TORSION FRAME ::}{:: POLARIZED INSULATION ::}{:: SOVEREIGN CORE    |
+=============================================================================+

Unifies:
  1. osiris_livlm: Sovereign 8-qubit qByte Quantum Living Language Model
  2. osiris_ncllm_swarm: 9-Agent Autopoietic Deliberative Consensus Swarm
  3. osiris-governance: Fail-Closed Capability Governor & Dynamic Evidence Ledger
  4. dnalang-core: Genome Language, Quantum Circuit Compiler & AST Verification
  5. organism_sim: Neuro-Symbolic ALife Simulation, GRN & Action DSL
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import logging
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Ensure core repository directories are on sys.path
_SEARCH_PATHS = [
    Path("/home/enki/osiris-governance/src"),
    Path("/home/enki/dnalang-core"),
    Path("/home/enki/organism_sim"),
    Path("/home/enki/bridge"),
    Path("/home/enki/flywheel-2026"),
    Path("/home/enki/osiris-cli"),
    Path("/home/enki/qbyte_system"),
    Path("/home/enki"),
]

for p in _SEARCH_PATHS:
    p_str = str(p)
    if os.path.exists(p_str) and p_str not in sys.path:
        sys.path.insert(0, p_str)

logger = logging.getLogger("OSIRIS_UNIFIED")


class EngineMode(str, Enum):
    QUANTUM = "quantum"              # Raw 8-qubit quantum circuit text generation
    SWARM = "swarm"                  # 9-agent autopoietic swarm deliberation
    GOVERNED = "governed"            # Formal capability governor & evidence ledger
    NEURO_SYMBOLIC = "neuro_symbolic"# DNA gene synthesis -> verification -> ALife GRN


@dataclasses.dataclass
class GenerationResult:
    mode: EngineMode
    prompt: str
    output: str
    elapsed_ms: float
    quantum_metrics: Optional[Dict[str, Any]] = None
    swarm_details: Optional[Dict[str, Any]] = None
    governance_record: Optional[Dict[str, Any]] = None
    dnalang_verification: Optional[Dict[str, Any]] = None


class UnifiedLivLMEngine:
    """
    Central operational engine unifying the quantum living language model,
    the 9-agent non-causal swarm, the fail-closed governance control plane,
    the dnalang compiler, and the organism ALife simulation.
    """

    def __init__(self, default_mode: EngineMode = EngineMode.QUANTUM, ledger_id: str = "unified-livlm-01"):
        self.default_mode = default_mode
        self.ledger_id = ledger_id

        # Lazy-loaded component instances
        self._livlm = None
        self._swarm = None
        self._governance = None
        self._organism_runtime = None
        self._initialized = False

    def initialize(self):
        """Pre-warm models and components."""
        if self._initialized:
            return
        logger.info("Initializing Unified OSIRIS Living Language Model Engine...")

        # 1. Initialize Quantum LivLM
        try:
            from osiris_livlm import create_livlm, LivLMConfig
            config = LivLMConfig(n_layers=2, max_corpus_files=20, max_corpus_bytes=100000)
            self._livlm = create_livlm(n_layers=2)
            if hasattr(self._livlm, "auto_load") and self._livlm.auto_load():
                pass
            else:
                self._livlm.load_corpus()
            logger.info("LivLM quantum engine ready (%d parameters, %d layers)",
                        self._livlm.gen_circuit.n_params, self._livlm.gen_circuit.n_layers)
        except Exception as e:
            logger.warning("Could not initialize LivLM: %s", e)

        # 2. Initialize Governance Service
        try:
            from osiris_governance.livlm_service import LivLMService
            self._governance = LivLMService(ledger_id=self.ledger_id)
            logger.info("OSIRIS Governance control plane & DynamicEvidenceLedger active")
        except Exception as e:
            logger.warning("Could not initialize Governance service: %s", e)

        self._initialized = True

    @property
    def livlm(self):
        if self._livlm is None:
            self.initialize()
        return self._livlm

    @property
    def swarm(self):
        if self._swarm is None:
            from osiris_ncllm_swarm import NCLLMSwarm
            self._swarm = NCLLMSwarm()
        return self._swarm

    @property
    def governance(self):
        if self._governance is None:
            self.initialize()
        return self._governance

    def generate(self, prompt: str, mode: Optional[EngineMode] = None,
                 length: int = 64, temperature: float = 0.8,
                 max_rounds: int = 1) -> GenerationResult:
        """
        Execute unified generation or reasoning under the selected mode.
        """
        self.initialize()
        active_mode = mode or self.default_mode
        start_time = time.time()

        if active_mode == EngineMode.QUANTUM:
            # Quantum circuit forward execution and phase memory sampling
            output = self.livlm.respond(prompt, max_length=length)
            elapsed_ms = (time.time() - start_time) * 1000.0
            metrics = self.livlm.status()
            return GenerationResult(
                mode=active_mode,
                prompt=prompt,
                output=output,
                elapsed_ms=elapsed_ms,
                quantum_metrics=metrics,
            )

        elif active_mode == EngineMode.SWARM:
            # 9-agent deliberative consensus
            res = self.swarm.solve(prompt, max_rounds=max_rounds)
            elapsed_ms = (time.time() - start_time) * 1000.0
            return GenerationResult(
                mode=active_mode,
                prompt=prompt,
                output=res.final_output,
                elapsed_ms=elapsed_ms,
                swarm_details={
                    "quality_score": res.quality_score,
                    "agents_used": res.agents_used,
                    "rounds": len(res.rounds),
                    "total_swarm_ms": res.total_elapsed_ms,
                },
            )

        elif active_mode == EngineMode.GOVERNED:
            # Governed execution: normalized JSON hashing + DynamicEvidenceLedger
            gov_res = self.governance.handle_intent(prompt)
            elapsed_ms = (time.time() - start_time) * 1000.0
            output_text = (
                gov_res.get("result", {}).get("generated_text")
                or gov_res.get("result", {}).get("message")
                or json.dumps(gov_res.get("result", {}), indent=2)
            )
            return GenerationResult(
                mode=active_mode,
                prompt=prompt,
                output=str(output_text),
                elapsed_ms=elapsed_ms,
                quantum_metrics=gov_res.get("result", {}).get("quantum_metrics"),
                governance_record={
                    "execution_id": gov_res.get("execution_id"),
                    "request_hash": gov_res.get("request_hash"),
                    "evidence_digest": gov_res.get("evidence_digest"),
                    "intent": gov_res.get("intent"),
                    "chain_valid": gov_res.get("governance", {}).get("chain_valid"),
                },
            )

        elif active_mode == EngineMode.NEURO_SYMBOLIC:
            # DNA generation -> dnalang parse/check -> GRN injection
            from organism_sim.chat_bridge import LivLMClient, extract_dna, gate, Runtime
            client = LivLMClient()
            raw_reply = client.complete("System", [{"role": "user", "content": prompt}])
            dna_block = extract_dna(raw_reply)

            v_result = {"extracted_dna": bool(dna_block), "verified": False, "report": ""}
            if dna_block:
                if self._organism_runtime is None:
                    self._organism_runtime = Runtime.demo(seed=0)
                gate_res = gate(dna_block, self._organism_runtime.grn)
                v_result["verified"] = gate_res.ok
                v_result["stage"] = gate_res.stage
                v_result["report"] = gate_res.report()
                if gate_res.ok:
                    self._organism_runtime.grn.add_genes(gate_res.genes)
                    v_result["active_genes"] = len(self._organism_runtime.grn.genome.genes)

            elapsed_ms = (time.time() - start_time) * 1000.0
            return GenerationResult(
                mode=active_mode,
                prompt=prompt,
                output=raw_reply,
                elapsed_ms=elapsed_ms,
                dnalang_verification=v_result,
            )

        raise ValueError(f"Unknown mode: {active_mode}")

    def autopoietic_learn(self, corpus_path: Optional[str] = None,
                          generations: int = 10, verbose: bool = True) -> Dict[str, Any]:
        """
        Continuous online adaptation without backpropagation:
        ingest local codebase, update n-gram transition statistics,
        and genetically optimize quantum gate rotation angles θ with phase-conjugate healing.
        """
        self.initialize()
        start = time.time()
        if corpus_path:
            self.livlm.load_corpus(root_dir=corpus_path)
        else:
            self.livlm.load_corpus()

        if generations:
            self.livlm.config.max_generations = generations
            if hasattr(self.livlm, "_evolution_config"):
                self.livlm._evolution_config.max_generations = generations
            if hasattr(self.livlm, "_evolution") and hasattr(self.livlm._evolution, "config"):
                self.livlm._evolution.config.max_generations = generations

        res = self.livlm.evolve(verbose=verbose)
        self.livlm.save_genome("livlm_genome.json")
        res["evolution_time_s"] = time.time() - start
        return res

    def get_audit_trail(self) -> Dict[str, Any]:
        """Retrieve verified cryptographic governance evidence trail."""
        self.initialize()
        raw_events = self.governance.ledger.events
        events = []
        for e in raw_events:
            d = dataclasses.asdict(e)
            if hasattr(e.event_type, "value"):
                d["event_type"] = e.event_type.value
            if hasattr(e.plane, "value"):
                d["plane"] = e.plane.value
            events.append(d)
        chain_valid = self.governance.ledger.verify_chain_integrity()
        latest_digest = self.governance.ledger.latest_digest
        return {
            "events_count": len(events),
            "chain_valid": chain_valid,
            "latest_digest": latest_digest,
            "events": events[-10:],  # last 10 events
        }

    def status(self) -> Dict[str, Any]:
        """Aggregate system status across all unified layers."""
        self.initialize()
        status_dict = {
            "version": "OSIRIS-LIVLM-UNIFIED-0.1.0",
            "active_mode": self.default_mode.value,
            "livlm": self.livlm.status() if self.livlm else None,
            "governance": {
                "ledger_id": self.governance.ledger.ledger_id if self.governance else None,
                "chain_valid": self.governance.ledger.verify_chain_integrity() if self.governance else None,
                "total_events": len(self.governance.ledger.events) if self.governance else 0,
            },
            "agents_count": 9,
        }
        return status_dict


def main():
    parser = argparse.ArgumentParser(description="OSIRIS Unified Living Language Model Engine")
    parser.add_argument("--mode", choices=[m.value for m in EngineMode], default="quantum")
    parser.add_argument("--prompt", type=str, default="Synthesize quantum dynamical decoupling protocol")
    parser.add_argument("--length", type=int, default=64)
    parser.add_argument("--learn", action="store_true", help="Run autopoietic genetic adaptation before generating")
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--audit", action="store_true", help="Display cryptographic evidence audit trail")
    args = parser.parse_args()

    engine = UnifiedLivLMEngine(default_mode=EngineMode(args.mode))
    engine.initialize()

    if args.learn:
        print("\n--- Executing Autopoietic Adaptation (Zero-Backprop Quantum Evolution) ---")
        learn_res = engine.autopoietic_learn(generations=args.generations, verbose=True)
        print(f"Adaptation complete: Φ={learn_res.get('best_phi', 0):.4f}, State={learn_res.get('consciousness_state')}\n")

    if args.audit:
        audit = engine.get_audit_trail()
        print(json.dumps(audit, indent=2))
        return 0

    print(f"\n--- Generating under Mode: {args.mode.upper()} ---")
    res = engine.generate(args.prompt, length=args.length)
    print(f"Prompt: {res.prompt}")
    print(f"Elapsed: {res.elapsed_ms:.2f} ms")
    print(f"Output:\n{res.output}\n")
    if res.quantum_metrics:
        print(f"Quantum Metrics: {res.quantum_metrics}")
    if res.governance_record:
        print(f"Governance: {res.governance_record}")
    if res.dnalang_verification:
        print(f"DNA Verification: {res.dnalang_verification}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
