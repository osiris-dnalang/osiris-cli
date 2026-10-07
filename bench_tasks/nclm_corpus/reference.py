import random


def split_corpus(files, test_ratio, seed):
    names = sorted(files)
    n = len(names)
    k = round(n * test_ratio)
    if n >= 2:
        k = min(max(k, 1), n - 1)
    shuffled = names[:]
    random.Random(seed).shuffle(shuffled)
    return sorted(shuffled[k:]), sorted(shuffled[:k])


def corpus_bytes(files, names):
    return b"\n".join(files[n] for n in sorted(names))
