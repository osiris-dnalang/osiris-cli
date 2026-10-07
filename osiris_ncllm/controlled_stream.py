def controlled_generate(model, tokenizer, prompt, agents):
    from osiris_ncllm.stream import generate_stream
    output = ""
    for token in generate_stream(model, tokenizer, prompt):
        output += token
        print(token, end="", flush=True)
        for agent in agents:
            decision = agent.observe(output)
            if decision == "STOP":
                return output
            if decision == "MODIFY":
                output = agent.modify(output)
    return output
