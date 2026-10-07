"""nclm_analysis labels rows by ledger index and never issues its own gate verdict."""

import json

import nclm_analysis
from nclm_analysis import LedgerAnalyzer


def test_rows_matched_by_hash_prefix_and_labelled_by_ledger_index(tmp_path, monkeypatch):
    full = "c1b9ab9b50312ddfc32250cbb77d7088c239b96c9cbb02a0a356c47f8b32023d"
    (tmp_path / "stats.json").write_text(json.dumps({"heldout_scores": {full: [9.1113, 4.63, 12, 5]}}))
    (tmp_path / "unigram_baseline.json").write_text(json.dumps({"bits_per_byte": 5.080468410658388}))
    monkeypatch.setattr(LedgerAnalyzer, "STATS_PATH", tmp_path / "stats.json")
    rows = [{"index": i, "hash": "x" * 40, "t": f"t{i}"} for i in range(5)]
    rows.append({"index": 5, "hash": full[:40], "t": "2026-10-07T08:38:58"})
    values = LedgerAnalyzer.extract_bpb(rows)
    assert values == [(5, 9.1113, "2026-10-07T08:38:58")]
    stats = LedgerAnalyzer.compute_learning_curve(values)
    assert stats["heldout_scored"] == 1
    assert stats["baseline"] == 5.080468410658388
    assert "NCLM-1_v1_evaluate.py" in stats["gate_status"]
    assert "PASS" not in stats["gate_status"] and "FAIL" not in stats["gate_status"]
    out = tmp_path / "r.csv"
    nclm_analysis.ReportGenerator.save_csv(rows, values, str(out))
    assert out.read_text().splitlines() == ["exchange_index,core_bpb,t", "5,9.1113,2026-10-07T08:38:58"]
