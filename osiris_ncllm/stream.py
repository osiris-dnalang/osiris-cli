import numpy as np

def softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()

def sample(probs, temperature=1.0):
    probs = np.log(probs + 1e-9) / temperature
    probs = softmax(probs)
    return np.random.choice(len(probs), p=probs)

def generate_stream(model, tokenizer, prompt, max_tokens=100, temperature=1.0):
    tokens = tokenizer.encode(prompt)
    for _ in range(max_tokens):
        logits = model.forward(tokens)
        probs = softmax(logits[-1])
        next_token = sample(probs, temperature)
        tokens.append(next_token)
        yield tokenizer.decode([next_token])
