import repl_commands


def test_proposal():
    n = repl_commands.normalize_command
    assert n("apply") == "/apply"
    assert n("//APPLY.") == "/apply"
    assert n("  sprint   execute ") == "/sprint execute"
    assert n("/Sprint Review!") == "/sprint review"
    assert n("hello") is None
    assert n("apply now") is None
    s = repl_commands.suggest
    assert s("aply") == "/apply"
    assert s("igntie") == "/ignite"
    assert s("sprint exectue") == "/sprint execute"
    assert s("sprint execute") == "/sprint execute"
    assert s("hello") is None
    assert s("banana") is None
