"""
Tests verifying status dashboard and /ignite command truthfulness:
- Enforces SYS-024 Claims Firewall: No refuted or unmeasured claims presented as physical invariants.
- Enforces SYS-026 NCLM Speaking Gate telemetry reporting.
- Enforces agreement between /ignite banner and metamorphosis engine.
"""

import io
import sys
from unittest.mock import patch
import pytest

from osiris_cli import claims
from osiris_cli.osiris_repl import (OsirisReplState, claims_summary, display_status, execute_ignite,
                                    substrate_label)


def _profile(**overrides):
    """A detected-hardware profile; the defaults describe an x86_64 workstation."""
    from osiris_hardware_mesh import HardwareProfile, NodeType

    fields = dict(node_type=NodeType.BETA_COMPUTE, machine_arch="x86_64", cpu_model="Intel(R) Core(TM) Ultra 7",
                  cpu_cores=8, is_termux=False, is_android=False, has_intel_arc=False, has_neon=False,
                  has_avx2=True, has_avx_vnni=True, execution_timeout_s=1800.0, allow_extended_horizons=True)
    fields.update(overrides)
    return HardwareProfile(**fields)


def _alpha():
    from osiris_hardware_mesh import NodeType
    return _profile(node_type=NodeType.ALPHA_MOBILE, machine_arch="aarch64", cpu_model="ARMv8",
                    is_termux=True, is_android=True, has_neon=True, has_avx2=False, has_avx_vnni=False,
                    execution_timeout_s=300.0, allow_extended_horizons=False)


def _status(state):
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        display_status(state)
    return buf.getvalue()


def test_display_status_truthfulness_and_claims_firewall():
    """Verify that display_status does not emit refuted or unmeasured claims as live invariants."""
    state = OsirisReplState()
    buf = io.StringIO()
    
    with patch("sys.stdout", buf):
        display_status(state)
        
    output = buf.getvalue()

    # SYS-024 Claims Firewall: Refuted/unmeasured claims must NOT appear as live invariants
    assert "Resonance Angle: 51.843°" not in output
    assert "Pyramid face slope arctan(14/11)" not in output
    assert "Memory Invariant: Λ_Φ" not in output
    assert "Peak Fidelity  : F_max" not in output
    assert "Substrate State: COLD (Run /ignite)" not in output
    assert "11D CRSM" not in output

    # Must report real empirical telemetry: the node is the one detected on this machine
    assert f"Substrate Node : {substrate_label(state.hardware_profile)}" in output
    assert "AST Firewall   :" in output
    assert "SYS-025" in output
    assert "Coherence Floor:" in output
    assert "Genome State   :" in output
    assert "Mentor Engine  :" in output
    assert "NCLM-1 Voice   :" in output
    assert "SYS-026" in output
    assert f"Claims Firewall: {claims_summary()} (SYS-024 Enforced)" in output
    assert "Gemma-native" not in output and "Γ <= 0.092" not in output
    assert "configured threshold, not a measured invariant" in output


@pytest.mark.parametrize("make, expected, absent", [
    (lambda: _profile(), "Node Beta (compute workstation) | x86_64", "Node Alpha"),
    (_alpha, "Node Alpha (mobile edge) | aarch64 | Termux | SIMD: NEON", "Node Beta"),
])
def test_status_names_the_detected_node(make, expected, absent):
    state = OsirisReplState()
    state.hardware_profile = make()
    output = _status(state)
    assert expected in output and absent not in output
    assert "Fold7" not in output


def test_status_without_detection_says_so():
    state = OsirisReplState()
    state.hardware_profile = None
    assert "Substrate Node : undetected" in _status(state)


def test_claims_summary_is_counted_from_the_register():
    counts = {}
    for c in claims.REGISTER:
        counts[c.verdict] = counts.get(c.verdict, 0) + 1
    top_verdict, top_n = max(counts.items(), key=lambda kv: kv[1])
    summary = claims_summary()
    assert summary.startswith(f"{len(claims.REGISTER)} registered claims | {top_n} {top_verdict}")
    with patch.object(claims, "REGISTER", claims.REGISTER[:1]):
        assert claims_summary() == f"1 registered claims | 1 {claims.REGISTER[0].verdict}"


def test_status_recomputes_both_chains_and_names_the_exchange_log(tmp_path):
    """E-25: /status names the exchange log it read and recomputes both hash chains instead of asserting them."""
    import json
    import os

    from osiris_cli import journal
    from osiris_cli.living import Osiris

    o = Osiris(core=None, mentor=None, home=str(tmp_path / "living"), out=lambda s: None, background=False, tty=False)
    for i in range(2):
        o._record({"user": f"m{i}", "reply": "r"})
    j = journal.OperationalMerkleLedger(tmp_path / "journal.jsonl")
    j.append("test", {"n": 1})
    with patch("osiris_cli.osiris_repl.get_living", return_value=o), \
            patch.object(journal, "DEFAULT_JOURNAL_PATH", j.path):
        out = _status(OsirisReplState())
        assert (f"Exchange Log   : INTACT (2 entries, head {o.stats['last_head'][:12]}) · "
                f"{os.path.abspath(o.log_path)}") in out
        assert "Evidence Events: 1 in the operational journal (hash chain intact)" in out
        assert "Merkle ledger" not in out
        assert f"Claims Firewall: {claims_summary()} (SYS-024 Enforced)" in out

        entry = json.loads(j.path.read_text().splitlines()[0])
        entry["n"] = 2                                    # payload fields sit at the top level
        j.path.write_text(json.dumps(entry) + "\n")
        lines = open(o.log_path).read().splitlines()
        open(o.log_path, "w").write(lines[0].replace('"r"', '"edited"') + "\n" + lines[1] + "\n")
        out = _status(OsirisReplState())
        assert "Exchange Log   : TAMPERED (0 entries" in out
        assert "Evidence Events: 1 in the operational journal (hash chain TAMPERED (Entry 0:" in out

    with patch("osiris_cli.osiris_repl.get_living", side_effect=RuntimeError("no core")), \
            patch.object(journal, "DEFAULT_JOURNAL_PATH", tmp_path / "absent.jsonl"):
        state = OsirisReplState()
        out = _status(state)
    assert "Exchange Log   : unavailable (no core)" in out
    assert (f"Evidence Events: {len(state.evidence_ledger)} this session, in memory "
            "(no operational journal in this install)") in out
    assert not (tmp_path / "absent.jsonl").exists()


def test_execute_ignite_truthfulness_and_banner_harmony():
    """Verify that execute_ignite banner does not emit contradictory 11D CRSM claims."""
    state = OsirisReplState()
    buf = io.StringIO()
    
    with patch("sys.stdout", buf):
        res = execute_ignite(state)
        
    output = buf.getvalue()

    # Contradictory pseudo-scientific claims must NOT appear
    assert "11D CRSM Substrate LOCKED & OPERATIONAL" not in output
    assert "Clifford Substrate: Cl(3,0)" not in output
    assert "Locking Resonance: θ_lock = 51.843°" not in output
    assert "Memory Invariant: Λ_Φ" not in output

    # Substrate and mesh verification must agree with the node actually detected
    assert f"Physical Substrate: {substrate_label(state.hardware_profile)}" in output
    assert "Gemma-native" not in output
    assert "AST Firewall:     CIL L0-L6 Interposition Active [SYS-025 ENFORCED FAIL-CLOSED]" in output
    assert "Cognitive Substrate: Mentor Engine & NCLM-1 Speaking Gate" in output
    assert "SYS-026" in output
    assert "DELIBERATIVE MESH READY" in output
    assert res["status"] == "SUCCESS"
    assert "event_hash" in res


def test_execute_ignite_dry_run():
    """Verify that execute_ignite with dry_run=True applies zero mutations and does not log events."""
    state = OsirisReplState()
    initial_ledger_len = len(state.evidence_ledger)
    buf = io.StringIO()

    with patch("sys.stdout", buf):
        res = execute_ignite(state, dry_run=True)

    output = buf.getvalue()

    assert "[IGNITION::DRY-RUN]" in output
    assert "Edge substrate verified; zero mutations applied." in output
    assert res["status"] == "DRY_RUN"
    assert res["verified"] is True
    assert res["promoted_count"] == 0
    assert len(state.evidence_ledger) == initial_ledger_len
    assert state.ignited is False
