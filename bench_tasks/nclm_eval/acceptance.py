import math
import nclm_eval

EX = [b"ignite genome trait " * 4, b"sprint execute apply " * 4, b"capability gap scan " * 4,
      b"held out evaluation " * 4, b"update step loss " * 4]


def test_proposal():
    loss = nclm_eval.compute_unigram_loss(b"", bytes(range(256)))
    assert abs(loss - math.log(256)) < 1e-6, f"uniform byte loss must be ln(256) nats, got {loss}"
    try:
        nclm_eval.compute_unigram_loss(b"abc", b"")
        raise AssertionError("empty test set must raise ValueError")
    except ValueError:
        pass
    try:
        nclm_eval.evaluate_held_out(EX, None)
        raise AssertionError("a missing model must raise ValueError")
    except ValueError:
        pass
    worse = nclm_eval.evaluate_held_out(EX, lambda tr, te: math.log(256))
    assert worse["nclm_advantage"] < 0, worse
    better = nclm_eval.evaluate_held_out(EX, lambda tr, te: 0.5)
    assert better["nclm_advantage"] > 0, better
    assert abs(better["unigram_loss"] - better["nclm_loss"] - better["nclm_advantage"]) < 1e-9
