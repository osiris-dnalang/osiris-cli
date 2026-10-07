import random


def split_corpus(files, test_ratio, seed):
    # Plausible but order-dependent: shuffles in dict insertion order.
    names = list(files)
    k = min(max(round(len(names) * test_ratio), 1), max(len(names) - 1, 1))
    random.Random(seed).shuffle(names)
    return sorted(names[k:]), sorted(names[:k])


def corpus_bytes(files, names):
    return b"\n".join(files[n] for n in sorted(names))
