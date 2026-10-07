import nclm_corpus

FILES = {f"mod_{i:02d}.py": f"print({i})".encode() for i in range(20)}


def test_proposal():
    tr1, te1 = nclm_corpus.split_corpus(FILES, 0.2, seed=1)
    tr2, te2 = nclm_corpus.split_corpus(dict(reversed(list(FILES.items()))), 0.2, seed=1)
    assert (tr1, te1) == (tr2, te2), "split must not depend on dict insertion order"
    assert tr1 == sorted(tr1) and te1 == sorted(te1)
    assert not set(tr1) & set(te1) and set(tr1) | set(te1) == set(FILES)
    assert len(te1) == 4
    splits = {tuple(nclm_corpus.split_corpus(FILES, 0.2, seed=s)[1]) for s in range(1, 7)}
    assert len(splits) > 1, "different seeds should give different splits"
    tr, te = nclm_corpus.split_corpus({"a": b"1", "b": b"2"}, 0.1, seed=0)
    assert len(te) == 1 and len(tr) == 1
    tr, te = nclm_corpus.split_corpus({"a": b"1", "b": b"2"}, 0.99, seed=0)
    assert len(te) == 1 and len(tr) == 1
    assert nclm_corpus.corpus_bytes({"b": b"2", "a": b"1"}, ["b", "a"]) == b"1\n2"
