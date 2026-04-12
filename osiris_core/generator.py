from osiris_ncllm.model import MiniNCLLM
from osiris_ncllm.tokenizer import SimpleTokenizer
from osiris_ncllm.generator import generate

model = MiniNCLLM()
tokenizer = SimpleTokenizer()

def generate_code(prompt):
    return generate(model, tokenizer, prompt, max_tokens=200)
