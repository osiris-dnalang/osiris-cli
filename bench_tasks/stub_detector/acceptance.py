import stub_detector

SRC = """
def a():
    pass

def b():
    \"\"\"doc\"\"\"
    ...

class C:
    def m(self):
        raise NotImplementedError()

    def n(self):
        return None

    def k(self):
        raise NotImplementedError

def real(x):
    if x:
        pass
    return x + 1

def only_doc():
    \"\"\"just a docstring\"\"\"

async def e():
    return

def value():
    return 0
"""


def test_proposal():
    assert stub_detector.find_stubs(SRC) == ["a", "b", "m", "n", "k", "only_doc", "e"], \
        stub_detector.find_stubs(SRC)
    assert stub_detector.find_stubs("def ok(x):\n    return x * 2\n") == []
    try:
        stub_detector.find_stubs("def broken(:\n")
        raise AssertionError("invalid source must raise SyntaxError")
    except SyntaxError:
        pass
