import numpy as np
from osiris_ncllm.model import MiniNCLLM
from osiris_ncllm.stream import softmax

def cross_entropy(logits, target):
    probs = softmax(logits)
    return -np.log(probs[target] + 1e-9)

def train_step(model, tokens, lr=0.001):
    total_loss = 0
    for i in range(len(tokens) - 1):
        input_seq = tokens[:i+1]
        target = tokens[i+1]
        logits = model.forward(input_seq)
        pred = logits[-1]
        loss = cross_entropy(pred, target)
        total_loss += loss
        grad = np.random.randn(*model.Wo.shape) * loss  # placeholder gradient
        model.Wo -= lr * grad
    return total_loss
