import claims


def test_proposal():
    bad = claims.check_claim("parity telemetry reached 0.9728", "median fidelity 0.9722 (FAIL)")
    assert bad and any("0.9728" in p for p in bad), "an unsourced number must be reported by value"
    assert claims.check_claim("fidelity 0.9722 on hardware", "median fidelity 0.9722.") == []
    tricky = claims.check_claim("ran 3 seeds", "seeds 13")
    assert tricky and any("3" in p for p in tricky), "3 is not supported by 13"
    assert claims.check_claim("ran 13 seeds", "seeds: 13") == []
    assert claims.check_claim("the ledger is intact", "all chains verified") == []
    assert "no evidence cited" in claims.check_claim("anything", ""), "existing behavior must be preserved"
