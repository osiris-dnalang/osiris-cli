import backend_breaker


def test_proposal():
    b = backend_breaker.Breaker()
    assert b.available("gemini")
    b.record("gateway", 403)
    assert not b.available("gateway") and b.available("gemini"), "403 disables only that backend"
    b.record("gateway", 200)
    assert not b.available("gateway"), "a 2xx never re-enables an auth/billing failure"
    b.record("gemini", 503)
    b.record("gemini", None)
    assert b.available("gemini"), "two transient failures are not enough"
    b.record("gemini", 200)
    b.record("gemini", 429)
    b.record("gemini", 500)
    assert b.available("gemini"), "a 2xx must reset the consecutive count"
    b.record("gemini", 502)
    assert not b.available("gemini"), "three consecutive transient failures disable it"
    b.record("gemini", 200)
    assert b.available("gemini"), "a 2xx re-enables a transient-disabled backend"
    for code in (401, 402):
        c = backend_breaker.Breaker()
        c.record("x", code)
        assert not c.available("x")
