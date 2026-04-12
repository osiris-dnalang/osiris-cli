import numpy as np

memory_store = []

def embed(text):
    """Embed text as a simple numeric mean (placeholder for real embedding)."""
    return np.mean([ord(c) for c in text])  # simple placeholder

def store(text):
    """Store text and its embedding in memory_store."""
    memory_store.append((text, embed(text)))

def retrieve(query, k=3):
    """Retrieve up to k closest matches to query from memory_store."""
    q = embed(query)
    scored = [(t, abs(q - e)) for t, e in memory_store]
    scored.sort(key=lambda x: x[1])
    return [t for t, _ in scored[:k]]
