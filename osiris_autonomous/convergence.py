def convergence_loop(task, generator_agent, evaluator_agent, repair_agent, benchmark, update_memory, update_agent_weights, max_iters=3, score_threshold=0.9):
    best_output = None
    best_score = float('-inf')
    for i in range(max_iters):
        candidate = generator_agent(task)
        critique = evaluator_agent(candidate)
        improved = repair_agent(candidate, critique)
        score = benchmark(improved)
        update_memory(task, improved, score)
        update_agent_weights(score)
        if score > best_score:
            best_score = score
            best_output = improved
        if score >= score_threshold:
            break
    return best_output, best_score
