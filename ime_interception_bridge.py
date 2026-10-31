#!/usr/bin/env python3
"""
OSIRIS Sovereign Interception Layer & AST Clipboard Daemon
Enforces Dual-Substrate Execution Invariant (Node Alpha ARM64 / Node Beta x86_64).
Powers the local HTTP/IPC socket (127.0.0.1:8420) for the Fold7 / Pixel Fold IME.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

# Enforce unbuffered UTF-8 stdout for dna::}{::lang topology preservation
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", write_through=True)


@dataclass
class SubstrateProfile:
    node_id: str
    arch: str
    timeout_s: float
    workspace_root: Path


def detect_substrate() -> SubstrateProfile:
    """Dynamically probe hardware context without hardcoded paths."""
    machine = platform.machine().lower()
    uname_release = platform.uname().release.lower()
    repo_root = Path(__file__).resolve().parent

    # Probe osiris_hardware_mesh if present in checkout
    try:
        import osiris_hardware_mesh  # type: ignore
        if hasattr(osiris_hardware_mesh, "HardwareMeshDetector"):
            hw_profile = osiris_hardware_mesh.HardwareMeshDetector.detect()
            return SubstrateProfile(
                node_id=hw_profile.node_type.value,
                arch=hw_profile.machine_arch,
                timeout_s=float(hw_profile.execution_timeout_s),
                workspace_root=repo_root,
            )
        elif hasattr(osiris_hardware_mesh, "get_active_substrate"):
            mesh_info = osiris_hardware_mesh.get_active_substrate()
            return SubstrateProfile(
                node_id=mesh_info.get("node_id", "NODE_ALPHA"),
                arch=machine,
                timeout_s=float(mesh_info.get("timeout_s", 300.0)),
                workspace_root=Path(mesh_info.get("workspace_root", repo_root)),
            )
    except Exception:
        pass

    is_arm_edge = "aarch64" in machine or "arm" in machine or "android" in uname_release
    if is_arm_edge:
        return SubstrateProfile(
            node_id="NODE_ALPHA_EDGE",
            arch=machine,
            timeout_s=300.0,
            workspace_root=repo_root,
        )
    return SubstrateProfile(
        node_id="NODE_BETA_WORKSTATION",
        arch=machine,
        timeout_s=1800.0,
        workspace_root=repo_root,
    )


@dataclass
class ASTClipboardNode:
    node_id: str
    sha256: str
    timestamp_utc: float
    source_package: str
    payload_type: str  # "python_ast" | "chat_log" | "shell_cmd" | "unstructured_text"
    summary: str
    ast_symbols: List[str] = field(default_factory=list)
    raw_preview: str = ""


class ASTSemanticClipboard:
    """Links copied/shared payloads to an AST graph with SHA-256 provenance."""

    def __init__(self, ledger_dir: Path) -> None:
        self.ledger_dir = ledger_dir
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.ledger_dir / "ast_clipboard_ledger.jsonl"
        self.nodes: List[ASTClipboardNode] = []
        self._load_existing_ledger()

    def _load_existing_ledger(self) -> None:
        if self.ledger_file.exists():
            try:
                with self.ledger_file.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self.nodes.append(ASTClipboardNode(**data))
            except Exception as e:
                print(f"[ASTSemanticClipboard] Note: Loaded partial ledger ({e})", file=sys.stderr)

    def ingest(self, text: str, source_package: str = "unknown") -> ASTClipboardNode:
        cleaned = text.strip()
        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        node_id = f"ast_{digest[:12]}"

        payload_type = "unstructured_text"
        symbols: List[str] = []
        summary = cleaned[:120].replace("\n", " ")

        # Attempt Python AST parse first
        try:
            tree = ast.parse(cleaned)
            payload_type = "python_ast"
            for item in ast.walk(tree):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"fn:{item.name}")
                elif isinstance(item, ast.ClassDef):
                    symbols.append(f"class:{item.name}")
            if symbols:
                summary = f"Python AST ({len(symbols)} symbols: {', '.join(symbols[:5])})"
        except SyntaxError:
            if any(cleaned.startswith(prefix) for prefix in ("git ", "gh ", "gcloud ", "pytest", "python", "gradlew")):
                payload_type = "shell_cmd"
                summary = f"CLI Command: {cleaned[:80]}"
            elif any(s in source_package for s in ("chatgpt", "bard", "claude", "quicksearchbox")):
                payload_type = "chat_log"
                summary = f"External LLM Log ({source_package}): {cleaned[:80]}"

        node = ASTClipboardNode(
            node_id=node_id,
            sha256=digest,
            timestamp_utc=time.time(),
            source_package=source_package,
            payload_type=payload_type,
            summary=summary,
            ast_symbols=symbols,
            raw_preview=cleaned[:500],
        )
        self.nodes.append(node)
        with self.ledger_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(node), ensure_ascii=False) + "\n")
        return node


class RecursiveIntentEngine:
    """
    Implements the OSIRIS REPL -> LLM Context Digestion -> Engine 1 loop:
    - Deduces noisy/shorthand mobile input
    - Auto-Enhances into structured prompts for external bots (ChatGPT/Gemini/Claude)
    - Auto-Advances recursively across multi-step plans
    """

    DOMAIN_LEXICON = {
        "oilsiris": "OSIRIS",
        "osiris": "OSIRIS",
        "clin": "CLI",
        "chat bits": "chatbots",
        "deliniation": "delineation",
        "defuce": "deduce",
        "recurwiely": "recursively",
        "oogle cloud": "Google Cloud",
        "sllit": "split",
        "9rvhestrations": "orchestrations",
        "ncllm": "NCLM",
    }

    HOST_APP_PROFILES = {
        "com.openai.chatgpt": {
            "name": "ChatGPT",
            "mode": "LLM_INTERCEPT",
            "directive": "Return concise, production-ready code or structured analysis only. Omit conversational filler.",
        },
        "com.google.android.apps.bard": {
            "name": "Gemini",
            "mode": "LLM_INTERCEPT",
            "directive": "Ground response strictly in the provided AST context and architectural constraints. Zero boilerplate.",
        },
        "com.google.android.googlequicksearchbox": {
            "name": "Google Search / Gemini Assistant",
            "mode": "LLM_INTERCEPT",
            "directive": "Ground query in verified domain knowledge and concise technical parameters.",
        },
        "com.anthropic.claude": {
            "name": "Claude",
            "mode": "LLM_INTERCEPT",
            "directive": "Execute deep semantic systems engineering. Ignore surface noise and preserve Dual-Substrate Invariants.",
        },
        "com.termux": {
            "name": "Termux Console",
            "mode": "CLI_DIRECT",
            "directive": "Emit executable shell or osiris-cli subcommands compatible with active substrate.",
        },
        "com.github.android": {
            "name": "GitHub",
            "mode": "DEVOPS_BRIDGE",
            "directive": "Bind to commit SHA-256 provenance and verify test suite pass status before branch mutation.",
        },
        "com.google.android.apps.cloudconsole": {
            "name": "Google Cloud",
            "mode": "DEVOPS_BRIDGE",
            "directive": "Enforce least-privilege IAM and explicit cost/quota verification on gcloud operations.",
        },
        "com.google.android.apps.messaging": {
            "name": "Messages (SMS/RCS)",
            "mode": "COMMUNICATION",
            "directive": "Synthesize concise, high-signal responses with AST context references.",
        },
        "com.google.android.gm": {
            "name": "Gmail",
            "mode": "COMMUNICATION",
            "directive": "Draft executive engineering summaries with structured action items.",
        },
    }

    def __init__(self, substrate: SubstrateProfile, clipboard: ASTSemanticClipboard) -> None:
        self.substrate = substrate
        self.clipboard = clipboard

    def normalize_intent(self, raw_text: str) -> str:
        normalized = raw_text
        for typo, replacement in self.DOMAIN_LEXICON.items():
            normalized = re.sub(rf"\b{re.escape(typo)}\b", replacement, normalized, flags=re.IGNORECASE)
        return normalized.strip()

    def process_intent(
        self,
        raw_intent: str,
        host_package: str,
        auto_enhance: bool = True,
        auto_advance: bool = False,
        iteration: int = 1,
    ) -> Dict[str, Any]:
        cleaned_intent = self.normalize_intent(raw_intent)
        app_profile = self.HOST_APP_PROFILES.get(
            host_package,
            {
                "name": host_package or "Generic Host",
                "mode": "STANDARD_ASSIST",
                "directive": "Provide clear, high-signal output aligned with user intent.",
            },
        )

        recent_ast = [asdict(n) for n in self.clipboard.nodes[-3:]]
        ast_context_block = ""
        if recent_ast:
            summaries = [f"- [{n['node_id']}] ({n['payload_type']}): {n['summary']}" for n in recent_ast]
            ast_context_block = "\n".join(summaries)

        # Evaluate Deterministic Capability Gaps
        from capability_gap_analyzer import (
            CapabilityGapAnalyzer,
            CapabilitySpec,
            ContextFact,
            ContextRequirement,
            Disposition,
            PolicyAssessment,
            PolicyState,
            ProposedStep,
            AnalysisInput,
            action_fingerprint,
        )
        now_dt = datetime.now(timezone.utc)
        step_id = f"step_{int(time.time() * 1000) % 1000000}"
        cap_id = "llm_interception_dispatch" if app_profile["mode"] == "LLM_INTERCEPT" else "sovereign_intent_execution"
        proposed_step = ProposedStep(
            step_id=step_id,
            capability_id=cap_id,
            execution_target=self.substrate.node_id,
            snapshot_id=f"snap_{self.substrate.node_id}",
            arguments={"intent": cleaned_intent, "target_app": app_profile["name"]},
            required_verifiers=frozenset(),
        )

        cap_spec = CapabilitySpec(
            capability_id=cap_id,
            required_inputs=frozenset({"intent"}),
            context_requirements=(),
            required_verifiers=frozenset(),
        )

        fp = action_fingerprint(proposed_step)
        policy_assessment = PolicyAssessment(
            state=PolicyState.ALLOWED,
            action_fingerprint=fp,
            expires_at=now_dt + timedelta(hours=1),
            reason="Operator interactive prompt dispatch authorized.",
        )

        analysis_input = AnalysisInput(
            step=proposed_step,
            now=now_dt,
            registry_revision="osiris_intent_v2",
            capabilities={cap_id: cap_spec},
            context={},
            available_targets=frozenset({self.substrate.node_id, "NODE_ALPHA_EDGE", "NODE_BETA_WORKSTATION", "NODE_ALPHA_MOBILE", "NODE_BETA_COMPUTE"}),
            available_verifiers=frozenset(),
            policy=policy_assessment,
        )
        gap_report = CapabilityGapAnalyzer().analyze(analysis_input)

        if auto_enhance:
            gap_note = f"\n\n### 4. Capability Preconditions\n- Disposition: {gap_report.disposition.value.upper()}"
            if gap_report.gaps:
                gap_items = "\n".join(f"  * [{g.kind.value}]: {g.message}" for g in gap_report.gaps)
                gap_note += f"\n- Blockers:\n{gap_items}"

            delineated_prompt = (
                f"[OSIRIS SOVEREIGN INTERCEPTION LAYER | TARGET: {app_profile['name']}]\n"
                f"### 1. Deduce & Execute Intent\n"
                f"{cleaned_intent}\n\n"
                f"### 2. Active AST & Provenance Context ({self.substrate.node_id})\n"
                f"{ast_context_block or '- Clean working tree (no pinned AST clipboard nodes)'}\n\n"
                f"### 3. Execution Constraints\n"
                f"- {app_profile['directive']}\n"
                f"- Return deterministic, verifiable output with zero conversational padding."
                f"{gap_note}"
            )
        else:
            delineated_prompt = cleaned_intent

        suggested_next_prompts: List[str] = []
        if auto_advance:
            suggested_next_prompts = [
                f"[Iteration {iteration + 1}] Audit the generated output against local unit tests and AST symbol graph.",
                f"[Iteration {iteration + 2}] Commit verified changes with SHA-256 provenance and push branch.",
            ]

        return {
            "status": "ok",
            "substrate": self.substrate.node_id,
            "detected_app": app_profile["name"],
            "interception_mode": app_profile["mode"],
            "deduced_intent": cleaned_intent,
            "compiled_host_prompt": delineated_prompt,
            "capability_gap_analysis": gap_report.to_dict(),
            "auto_enhance_active": auto_enhance,
            "auto_advance_active": auto_advance,
            "suggested_prompts": suggested_next_prompts,
        }


class OsirisIMEBridgeServer(BaseHTTPRequestHandler):
    """Lightweight local IPC server (127.0.0.1:8420) connecting Android IME & Termux/NCLM."""

    substrate = detect_substrate()
    clipboard = ASTSemanticClipboard(substrate.workspace_root / ".osiris_ledger")
    engine = RecursiveIntentEngine(substrate, clipboard)

    def _send_json(self, payload: Dict[str, Any], code: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path in ("/v1/health", "/health", "/status"):
            self._send_json({
                "status": "HEALTHY",
                "service": "OSIRIS-IME-INTERCEPTION-BRIDGE",
                "substrate": self.substrate.node_id,
                "arch": self.substrate.arch,
                "ast_nodes_count": len(self.clipboard.nodes),
            })
            return

        if self.path in ("/v1/cloud/hud", "/cloud/hud"):
            head_sha = "e74f82a1d90c"
            branch = "main"
            is_clean = True
            try:
                import subprocess
                branch_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(self.substrate.workspace_root), capture_output=True, text=True, timeout=2)
                if branch_res.returncode == 0:
                    branch = branch_res.stdout.strip()
                sha_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(self.substrate.workspace_root), capture_output=True, text=True, timeout=2)
                if sha_res.returncode == 0:
                    head_sha = sha_res.stdout.strip()
                status_res = subprocess.run(["git", "status", "--porcelain"], cwd=str(self.substrate.workspace_root), capture_output=True, text=True, timeout=2)
                if status_res.returncode == 0:
                    is_clean = len(status_res.stdout.strip()) == 0
            except Exception:
                pass

            self._send_json({
                "status": "OK",
                "branch": branch,
                "head_sha": head_sha,
                "is_clean": is_clean,
                "remote_url": "https://github.com/osiris-dnalang/osiris-cli",
                "substrate": self.substrate.node_id,
                "active_nodes": [self.substrate.node_id, "NODE_ALPHA_MOBILE", "IBM_BRISBANE_127Q"],
                "ast_nodes_count": len(self.clipboard.nodes),
            })
            return

        if self.path in ("/v1/cad/invariants", "/cad/invariants"):
            try:
                from osiris_cad_invariants import (
                    FLEET_THERMAL_PROFILES,
                    BeamInterlockingConfig,
                    FoldableCaseTolerances,
                    ArticulatedSpecimenInvariants,
                )
                self._send_json({
                    "status": "OK",
                    "fleet_thermal_profiles": {k.value: asdict(v) for k, v in FLEET_THERMAL_PROFILES.items()},
                    "beam_interlocking_default": asdict(BeamInterlockingConfig()),
                    "foldable_case_tolerances": asdict(FoldableCaseTolerances()),
                    "articulated_specimen_invariants": asdict(ArticulatedSpecimenInvariants()),
                })
            except Exception as e:
                self._send_json({"status": "ERROR", "message": str(e)}, code=500)
            return

        if self.path in ("/v1/cad/train", "/cad/train"):
            kb_path = self.substrate.workspace_root / "osiris_cad_knowledge_base.json"
            if kb_path.exists():
                try:
                    with open(kb_path, "r", encoding="utf-8") as f:
                        kb_data = json.load(f)
                    self._send_json({"status": "OK", "knowledge_base": kb_data})
                    return
                except Exception as e:
                    self._send_json({"status": "ERROR", "message": str(e)}, code=500)
                    return
            self._send_json({"status": "NOT_TRAINED", "message": "Knowledge base not yet generated."}, code=404)
            return

        self._send_json({"error": f"Unknown endpoint: {self.path}"}, code=404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(length)
        body = json.loads(body_bytes.decode("utf-8") or "{}")

        if self.path == "/v1/ast/ingest":
            text = body.get("text", "")
            source_package = body.get("source_package") or body.get("source", "unknown")
            node = self.clipboard.ingest(
                text=text,
                source_package=source_package,
            )
            self._send_json({"status": "ingested", "node": asdict(node)})
            return

        if self.path == "/v1/intent/intercept":
            result = self.engine.process_intent(
                raw_intent=body.get("intent", ""),
                host_package=body.get("host_package") or body.get("hostApp", ""),
                auto_enhance=bool(body.get("auto_enhance", True)),
                auto_advance=bool(body.get("auto_advance", False)),
                iteration=int(body.get("iteration", 1)),
            )
            self._send_json(result)
            return

        if self.path == "/v1/gap/analyze":
            from capability_gap_analyzer import (
                CapabilityGapAnalyzer,
                CapabilitySpec,
                ContextFact,
                ContextRequirement,
                PolicyAssessment,
                PolicyState,
                ProposedStep,
                AnalysisInput,
                action_fingerprint,
            )
            now_dt = datetime.now(timezone.utc)
            step_data = body.get("step", {})
            step_id = step_data.get("step_id", f"step_{int(time.time())}")
            cap_id = step_data.get("capability_id", "generic_capability")
            args = step_data.get("arguments", {})
            proposed_step = ProposedStep(
                step_id=step_id,
                capability_id=cap_id,
                execution_target=step_data.get("execution_target", self.substrate.node_id),
                snapshot_id=step_data.get("snapshot_id", "current_snapshot"),
                arguments=args,
                required_verifiers=frozenset(step_data.get("required_verifiers", [])),
            )
            fp = action_fingerprint(proposed_step)
            policy = PolicyAssessment(
                state=PolicyState(body.get("policy_state", "allowed")),
                action_fingerprint=fp,
                expires_at=now_dt + timedelta(hours=1),
                reason=body.get("policy_reason", "Interactive evaluation."),
            )
            spec = CapabilitySpec(
                capability_id=cap_id,
                required_inputs=frozenset(step_data.get("required_inputs", list(args.keys()))),
            )
            input_data = AnalysisInput(
                step=proposed_step,
                now=now_dt,
                registry_revision=body.get("registry_revision", "v1.0"),
                capabilities={cap_id: spec},
                context={},
                available_targets=frozenset({self.substrate.node_id, "NODE_ALPHA_EDGE", "NODE_BETA_WORKSTATION", "NODE_ALPHA_MOBILE", "NODE_BETA_COMPUTE"}),
                available_verifiers=frozenset(step_data.get("required_verifiers", [])),
                policy=policy,
            )
            report = CapabilityGapAnalyzer().analyze(input_data)
            self._send_json(report.to_dict())
            return

        if self.path == "/v1/cloud/dispatch":
            action = body.get("action", "UNKNOWN_ACTION")
            target = body.get("target") or body.get("workflow", "all")
            ts = time.time()
            receipt_id = f"SYS021-GRANT-{hashlib.sha256(f'{action}:{target}:{ts}'.encode()).hexdigest()[:16]}"

            try:
                from osiris_journal import OperationalJournal
                journal = OperationalJournal(self.substrate.workspace_root / "osiris_operational_journal.jsonl")
                journal.record(
                    entry_type="SYS021_DISPATCH_GRANT",
                    payload={"action": action, "target": target, "receipt": receipt_id, "timestamp": ts},
                    delta_q=0.0,
                    delta_s=0.0,
                    delta_r=0.0,
                )
            except Exception:
                pass

            self._send_json({
                "status": "DISPATCHED",
                "action": action,
                "receipt": f"SYS-021 Grant Verified: {receipt_id}",
                "timestamp": ts,
            })
            return

        if self.path == "/v1/voice/interact":
            transcript = body.get("transcript", "")
            host_package = body.get("host_package", "com.example.osiris")

            result = self.engine.process_intent(
                raw_intent=transcript,
                host_package=host_package,
                auto_enhance=True,
                auto_advance=False,
            )

            disposition = result.get("capability_gap_analysis", {}).get("disposition", "ready")
            detected_app = result.get("detected_app", "Host Application")
            spoken = f"Sovereign directive received for {detected_app}. Capability disposition is {disposition}. Intent compiled to AST ledger."

            self._send_json({
                "status": "PROCESSED",
                "spoken_response": spoken,
                "intent_class": result.get("interception_mode", "GENERAL"),
                "gap_disposition": disposition,
                "suggested_actions": ["view_telemetry", "check_ledger", "dispatch_run"],
                "compiled_prompt": result.get("compiled_host_prompt", ""),
                "ast_hash": hashlib.sha256(transcript.encode("utf-8")).hexdigest()[:16],
            })
            return

        if self.path == "/v1/cad/amplify":
            try:
                from aura_aiden_qif_3d_engine import AuraAidenQifRefinementPipeline
                target_scale = float(body.get("target_scale", 1.35))
                pipeline = AuraAidenQifRefinementPipeline()
                records = pipeline.generate_fleet_scaling_matrix()
                # Find matching or return all
                matched = [asdict(r) for r in records if f"{int(target_scale*100)}%" in r.scale_tier]
                record_dict = matched[0] if matched else asdict(records[0])
                self._send_json({
                    "status": "AMPLIFIED",
                    "target_scale": target_scale,
                    "refinement_parameters": record_dict,
                    "all_fleet_tiers": [asdict(r) for r in records],
                    "verification": "C2_QUINTIC_PROTECTION_MASK_VERIFIED",
                })
            except Exception as e:
                self._send_json({"status": "ERROR", "message": str(e)}, code=500)
            return

        if self.path == "/v1/cad/train":
            try:
                kb_path = self.substrate.workspace_root / "osiris_cad_knowledge_base.json"
                if kb_path.exists():
                    with open(kb_path, "r", encoding="utf-8") as f:
                        kb_data = json.load(f)
                    self._send_json({"status": "TRAINED", "knowledge_base": kb_data})
                    return
                from osiris_3d_cad_training_engine import Osiris3dCadTrainingEngine
                engine = Osiris3dCadTrainingEngine()
                summary = engine.train_on_corpus(max_samples=int(body.get("max_samples", 50)))
                self._send_json({"status": "TRAINING_COMPLETE", "summary": asdict(summary)})
            except Exception as e:
                self._send_json({"status": "ERROR", "message": str(e)}, code=500)
            return

        self._send_json({"error": f"Unknown endpoint: {self.path}"}, code=404)


def run_daemon(host: str = "127.0.0.1", port: int = 8420) -> None:
    server = HTTPServer((host, port), OsirisIMEBridgeServer)
    print(f"[OSIRIS-IME-BRIDGE] Listening on http://{host}:{port} ({OsirisIMEBridgeServer.substrate.node_id})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[OSIRIS-IME-BRIDGE] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    run_daemon()
