import backlog


def test_proposal():
    b = backlog.Backlog()
    first = b.add("Fix the parser")
    again = b.add("Fix the parser")
    assert again == first, "adding an open story twice must return the existing id"
    assert len(b.stories) == 1, "a duplicate must not be stored"
    other = b.add("Write the docs", source="vision")
    assert other != first and len(b.stories) == 2
    assert b.stories[-1]["source"] == "vision", "the source argument must still be honored"
    assert b.set_status(first, "active") is True and b.set_status(999, "done") is False
    assert [s["id"] for s in b.open_stories()] == [first, other]
    b.set_status(other, "done")
    assert [s["id"] for s in b.open_stories()] == [first], "existing behavior must be preserved"
