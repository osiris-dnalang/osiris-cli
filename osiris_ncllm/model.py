import numpy as np

class MiniNCLLM:
    def __init__(self, vocab_size=256, d_model=64, n_heads=4):
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.embeddings = np.random.randn(vocab_size, d_model) * 0.01
        self.Wq = np.random.randn(n_heads, d_model, self.head_dim)
        self.Wk = np.random.randn(n_heads, d_model, self.head_dim)
        self.Wv = np.random.randn(n_heads, d_model, self.head_dim)
        self.Wo = np.random.randn(d_model, vocab_size)
    def forward(self, tokens):
        x = self.embeddings[tokens]  # (T, d)
        heads_out = []
        for h in range(self.n_heads):
            Q = x @ self.Wq[h]
            K = x @ self.Wk[h]
            V = x @ self.Wv[h]
            scores = Q @ K.T / np.sqrt(self.head_dim)
            weights = np.exp(scores) / np.sum(np.exp(scores), axis=-1, keepdims=True)
            heads_out.append(weights @ V)
        multi_head = np.concatenate(heads_out, axis=-1)
        logits = multi_head @ self.Wo
        return logits

class KVCache:
    def __init__(self, n_heads=4):
        self.keys = [[] for _ in range(n_heads)]
        self.values = [[] for _ in range(n_heads)]
