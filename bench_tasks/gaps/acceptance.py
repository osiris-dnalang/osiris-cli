import gaps

LONG = "a hash-chained ledger that records " + "every genome, backlog and prompt change " * 5 + "with tamper detection"


def test_proposal():
    assert len(LONG) > 200
    assert gaps.extract_gaps([f"We have a capability gap: {LONG}. Unrelated text follows."]) == [LONG], \
        "a long gap must come out whole"
    assert gaps.extract_gaps(["capability gap: a ledger for genome changes. Also this."]) == \
        ["a ledger for genome changes"], "a gap must stop at the end of its sentence"
    assert gaps.extract_gaps(["Capability Gap: export 0.97 fidelity values. More."]) == \
        ["export 0.97 fidelity values"], "a decimal point is not the end of a sentence"
    assert gaps.extract_gaps(["capability gap: parse logs\nnext line"]) == ["parse logs"]
    assert gaps.extract_gaps(["capability gap: no trailing period"]) == ["no trailing period"]
    assert gaps.extract_gaps(["nothing here", "capability gap: one.", "capability gap: two."]) == ["one", "two"]
