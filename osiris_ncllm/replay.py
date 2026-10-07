from osiris_learning.memory import load_memory
from osiris_ncllm.trainer import train_step

def replay_train(model, tokenizer):
    data = load_memory()
    for sample in data:
        tokens = tokenizer.encode(sample["improved"])
        train_step(model, tokens)
