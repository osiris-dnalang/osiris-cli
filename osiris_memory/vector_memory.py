import numpy as np

memory_store = []

def embed(text):
    return np.mean([ord(c) for c in text])  # simple placeholder

def store(text):
    memory_store.append((text, embed(text)))

def retrieve(query, k=3):
    q = embed(query)
    scored = [(t, abs(q - e)) for t, e in memory_store]
    scored.sort(key=lambda x: x[1])
    return [t for t, _ in scored[:k]]
