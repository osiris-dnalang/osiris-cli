"""Tests for osiris_nclm_cli: parser wiring, prompt plumbing, and the regressions
the module was reviewed for.

Deliberately free of any nclm dependency except where a test says otherwise, so the
module's lazy-import contract is actually exercised rather than assumed.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import osiris_nclm_cli as cli  # noqa: E402


# --------------------------------------------------------------------------- parser

def test_parser_builds_and_exposes_every_command():
    parser = cli.build_parser()
    actions = [a for a in parser._actions if a.dest == "command"]
    assert actions, "no subparser group found"
    names = set(actions[0].choices)
    for expected in (
        "infer", "grok", "analyze", "understand", "enhance", "advance", "complete",
        "stack", "session", "concept", "quantum", "diagnostics", "understand-diag",
        "memory", "mode", "param", "tune", "zenodo", "github", "discover",
        "consciousness", "paper", "hypothesis", "swarm", "ultra", "dual-node",
        "status", "doctor", "history", "interactive",
    ):
        assert expected in names, f"{expected} missing from the parser"


def test_every_command_has_a_dispatch_branch():
    """dispatch() must not fall through to 'Unknown command' for a parseable command."""
    parser = cli.build_parser()
    names = set(next(a for a in parser._actions if a.dest == "command").choices)
    source = Path(cli.__file__).read_text()
    dispatch_src = source.split("async def dispatch(", 1)[1].split("\ndef main(", 1)[0]
    for name in names:
        if name == "grok":  # handled together with infer
            continue
        assert f'"{name}"' in dispatch_src, f"dispatch() has no branch for {name!r}"


def test_version_flag_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["--version"])
    assert exc.value.code == 0


def test_memory_action_choices_are_constrained():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["memory", "not-an-action"])


# ------------------------------------------------------------------ prompt plumbing

def test_normalize_prompt_collapses_spaces_and_keeps_newlines():
    assert cli.normalize_prompt("a   b\t\tc") == "a b c"
    assert cli.normalize_prompt("a\n\nb") == "a\n\nb"


def test_normalize_prompt_caps_length():
    assert len(cli.normalize_prompt("x" * (cli.MAX_PROMPT_CHARS + 500))) == cli.MAX_PROMPT_CHARS


def test_get_prompt_from_args_joins_positional_words():
    args = cli.build_parser().parse_args(["infer", "hello", "world"])
    assert cli.get_prompt_from_args(args) == "hello world"


def test_get_prompt_from_args_reads_file(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text("from a file")
    args = cli.build_parser().parse_args(["infer", "--file", str(f)])
    assert cli.get_prompt_from_args(args) == "from a file"


def test_require_prompt_raises_when_absent():
    args = cli.build_parser().parse_args(["enhance"])
    with pytest.raises(ValueError, match="required"):
        cli._require_prompt(args)


# ------------------------------------------------------------------- context helpers

def test_append_context_adds_block_once():
    block = "[MEMORY CONTEXT]\nMemory 1: x"
    once = cli._append_context("base", block)
    assert once.count("[MEMORY CONTEXT]") == 1
    # Re-appending the same block is a no-op: the header is already present.
    assert cli._append_context(once, block) == once


def test_append_context_does_not_duplicate_the_prompt():
    """Regression: an earlier version returned prompt + context + prompt."""
    out = cli._append_context("UNIQUE_BASE", "[H]\nbody")
    assert out.count("UNIQUE_BASE") == 1


def test_history_overlaps_requires_real_word_overlap():
    # Shares 'quantum' and 'entanglement' -> relevant.
    assert cli.AutoEnhanceEngine._history_overlaps(
        "explain quantum entanglement", ["quantum entanglement basics"]
    )
    # Shares nothing -> not relevant, even though it is not a substring either.
    assert not cli.AutoEnhanceEngine._history_overlaps(
        "explain quantum entanglement", ["banana bread recipe"]
    )


def test_parse_params_coerces_types():
    out = cli._parse_params(["a=1", "b=2.5", "c=true", "d=false", "e=text"])
    assert out == {"a": 1, "b": 2.5, "c": True, "d": False, "e": "text"}
    assert isinstance(out["a"], int) and isinstance(out["b"], float)


def test_parse_params_rejects_bare_token():
    with pytest.raises(ValueError, match="key=value"):
        cli._parse_params(["novalue"])


@pytest.mark.parametrize("ref", [
    "owner/repo",
    "https://github.com/owner/repo",
    "https://github.com/owner/repo.git",
    "git@github.com:owner/repo.git",
])
def test_parse_github_repo_accepts_known_forms(ref):
    assert cli._parse_github_repo(ref) == "owner/repo"


@pytest.mark.parametrize("ref", ["not a repo", "", "https://gitlab.com/o/r"])
def test_parse_github_repo_rejects_junk(ref):
    with pytest.raises(ValueError):
        cli._parse_github_repo(ref)


# ------------------------------------------------------------- lazy-import contract

def test_module_imports_without_optional_backends():
    """Importing the module must not pull in networkx or nclm."""
    source = Path(cli.__file__).read_text()
    header = source.split("# ---------------------------------------------------------------------------\n# Lazy third-party", 1)[0]
    assert "import networkx" not in header, "networkx must not be imported at module scope"
    assert "\nfrom nclm" not in header and "\nimport nclm" not in header


def test_backend_availability_reports_shape():
    report = cli._backend_availability()
    assert set(report) == set(cli.OPTIONAL_BACKENDS)
    for info in report.values():
        assert set(info) == {"available", "error", "commands"}
        assert isinstance(info["available"], bool)
        assert info["commands"]


def test_missing_backend_exits_two(monkeypatch, capsys):
    """A command whose backend is absent exits 2, not with a traceback."""
    def boom(module, attr=None, *, needed_for):
        raise cli.NotAvailableError(f"{needed_for} needs '{module}'")
    monkeypatch.setattr(cli, "_import_backend", boom)
    assert cli.main(["stack", "an objective"]) == 2


def test_status_json_runs_with_no_backends(capsys):
    assert cli.main(["status", "--json"]) == 0
    out = capsys.readouterr().out
    assert '"version"' in out and cli.VERSION in out


def test_doctor_json_runs_with_no_backends(capsys):
    assert cli.main(["doctor", "--json"]) == 0
    assert '"backends"' in capsys.readouterr().out


# --------------------------------------------------------------- reviewed regressions

class _FakeClient:
    """Minimal stand-in: cognitive_analysis always fails, as a stubbed backend would."""
    enable_quantum = False

    def __init__(self):
        self.state_dir = None

    async def cognitive_analysis(self, prompt):
        return {"status": "failed", "error": "stub backend", "prompt": prompt}

    async def deep_understand(self, prompt, max_depth=3):
        return {"metrics": {}, "concept_graph": {"nodes": [], "edges": []}}


def test_enhance_surfaces_the_backend_failure_reason():
    """Regression: a failed analysis used to look like 'no changes needed'."""
    engine = cli.AutoEnhanceEngine(_FakeClient())
    result = asyncio.run(engine.auto_enhance_prompt("topic", iterations=2))
    assert result["stopped_because"], "the backend's error must be carried out"
    assert "stub backend" in result["stopped_because"]
    assert result["enhancement_chain"] == []


def test_auto_complete_advances_from_the_original_prompt(monkeypatch):
    """Regression: do_auto_complete used to hand auto_advance an already-enhanced
    prompt, nesting the [AUTO-ENHANCED PROMPT] envelope inside itself."""
    pytest.importorskip("networkx")
    seen = {}

    async def fake_client(state_dir=None):
        return _FakeClient()

    class FakeAdvance:
        def __init__(self, client):
            pass

        async def auto_advance(self, initial_prompt, iterations=5, exploration_depth=3):
            seen["initial_prompt"] = initial_prompt
            return {
                "iterations": 0,
                "final_prompt": initial_prompt,
                "knowledge_graph": {"metrics": {
                    "nodes": 0, "edges": 0, "density": 0.0, "largest_scc_size": 0,
                }},
                "final_report": {
                    "summary": "",
                    "knowledge_graph": {"metrics": {
                        "nodes": 0, "edges": 0, "density": 0.0, "largest_scc_size": 0,
                    }},
                    "metric_trends": {"coherence": {"end": 0.0}},
                    "key_insights": [],
                    "recommendations": [],
                },
                "session_dir": "",
                "stopped_because": None,
            }

    monkeypatch.setattr(cli, "create_nclm_client", fake_client)
    monkeypatch.setattr(cli, "AutoAdvanceEngine", FakeAdvance)
    monkeypatch.setattr(cli, "write_json", lambda path, data: Path(str(path)))

    asyncio.run(cli.do_auto_complete("a raw topic"))

    assert seen["initial_prompt"] == "a raw topic"
    assert "[AUTO-ENHANCED PROMPT]" not in seen["initial_prompt"]


def test_state_dir_is_threaded_to_the_client(monkeypatch, tmp_path):
    """Regression: --state-dir was accepted and then silently ignored."""
    captured = {}

    async def fake_client(state_dir=None):
        captured["state_dir"] = state_dir
        return _FakeClient()

    monkeypatch.setattr(cli, "create_nclm_client", fake_client)
    monkeypatch.setattr(cli, "write_json", lambda path, data: Path(str(path)))

    target = tmp_path / "custom_state"
    assert cli.main(["--state-dir", str(target), "enhance", "topic"]) == 0
    assert captured["state_dir"] == target


# ------------------------------------------------------- knowledge-graph behaviour

def test_extract_new_concepts_preserves_order_and_skips_known():
    pytest.importorskip("networkx")
    engine = cli.AutoAdvanceEngine(_FakeClient())
    deep = {"concept_graph": {"nodes": ["zeta", "alpha", "zeta", "mid"]}}
    assert engine._extract_new_concepts(deep, {"alpha"}) == ["zeta", "mid"]


def test_update_knowledge_graph_links_the_newest_not_the_alphabetical_first():
    """Regression: sorted(new_concepts)[0] picked the alphabetically first concept and
    skewed degree_centrality toward names starting with early letters."""
    pytest.importorskip("networkx")
    engine = cli.AutoAdvanceEngine(_FakeClient())
    g = engine.knowledge_graph
    g.add_node("hub", type="concept")
    g.add_edge("hub", "other", weight=1.0)

    # 'alpha' sorts first; 'zeta' arrived last and is the genuinely newest.
    engine._update_knowledge_graph({"concept_graph": {"edges": []}}, ["alpha", "zeta"])

    assert g.has_edge("hub", "zeta"), "the newest concept should be linked to the hub"
    assert g.edges["hub", "zeta"]["type"] == "temporal"


def test_graph_metrics_empty_graph_is_safe():
    pytest.importorskip("networkx")
    engine = cli.AutoAdvanceEngine(_FakeClient())
    m = engine._graph_metrics()
    assert m["nodes"] == 0 and m["edges"] == 0
    assert m["density"] == 0.0 and m["average_degree"] == 0.0


def test_graph_report_on_empty_graph_reports_empty():
    pytest.importorskip("networkx")
    engine = cli.AutoAdvanceEngine(_FakeClient())
    assert engine._generate_graph_report()["status"] == "empty"


def test_metric_trends_on_empty_chain_has_full_shape():
    pytest.importorskip("networkx")
    engine = cli.AutoAdvanceEngine(_FakeClient())
    trends = engine._generate_metric_trends([])
    for key in ("coherence", "consciousness", "quantum_entanglement"):
        assert set(trends[key]) == {"values", "start", "end", "change", "average"}
    assert trends["new_concepts"]["total"] == 0


def test_convergence_needs_metrics_to_claim_convergence():
    pytest.importorskip("networkx")
    engine = cli.AutoAdvanceEngine(_FakeClient())
    flat = [{"deep_understanding": {"metrics": {}}, "new_concepts": []} for _ in range(3)]
    assert engine._check_convergence(flat) is False


# ------------------------------------------------------------------------- history

def test_append_and_load_history_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "HISTORY_FILE", tmp_path / "h.jsonl")
    cli.append_history({"ts": "t1", "command": "infer", "prompt": "a"})
    cli.append_history({"ts": "t2", "command": "grok", "prompt": "b"})
    rows = cli.load_history(limit=10)
    assert [r["ts"] for r in rows] == ["t1", "t2"]


def test_load_history_skips_malformed_lines(monkeypatch, tmp_path):
    h = tmp_path / "h.jsonl"
    h.write_text('{"ts": "ok"}\nnot json\n{"ts": "ok2"}\n')
    monkeypatch.setattr(cli, "HISTORY_FILE", h)
    assert [r["ts"] for r in cli.load_history()] == ["ok", "ok2"]


def test_history_rotates_past_the_size_cap(monkeypatch, tmp_path):
    h = tmp_path / "h.jsonl"
    monkeypatch.setattr(cli, "HISTORY_FILE", h)
    monkeypatch.setattr(cli, "HISTORY_MAX_BYTES", 50)
    for i in range(20):
        cli.append_history({"ts": f"t{i}", "prompt": "x" * 20})
    assert h.with_suffix(".jsonl.1").exists(), "the oversized log should be rotated"
    assert h.stat().st_size <= 200


# -------------------------------------------------------------------- json writing

def test_write_json_is_atomic_and_leaves_no_temp(tmp_path):
    out = cli.write_json(tmp_path / "x.json", {"a": {1, 2}, "p": tmp_path})
    assert out.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_json_default_handles_sets_and_paths():
    assert cli._json_default({3, 1, 2}) == [1, 2, 3]
    assert cli._json_default(Path("/a/b")) == "/a/b"
