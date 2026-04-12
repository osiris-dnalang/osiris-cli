import random
import json
import os

MEMORY_FILE = "osiris_lab_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def run_experiment(shots, depth):
    base_error = (1 / (shots ** 0.5)) + (depth * 0.002)
    noise = random.uniform(0.0, 0.01)
    error = base_error + noise
    cost = shots
    time = shots * 0.001  # fake runtime
    return {"error": error, "cost": cost, "time": time}

def experimentalist(config):
    result = run_experiment(config["shots"], config["depth"])
    return {**config, **result}

def theorist(population):
    best = sorted(population, key=lambda x: x["error"])[:2]
    children = []
    for b in best:
        children.append({
            "shots": max(128, int(b["shots"] * random.uniform(0.7, 1.3))),
            "depth": max(1, int(b["depth"] * random.uniform(0.7, 1.3)))
        })
    return children

def challenger(best):
    return {
        "shots": max(128, int(best["shots"] * random.uniform(0.3, 0.7))),
        "depth": max(1, int(best["depth"] * random.uniform(1.5, 2.5)))
    }

def dominates(a, b):
    return (
        a["error"] <= b["error"] and
        a["cost"] <= b["cost"] and
        (a["error"] < b["error"] or a["cost"] < b["cost"])
    )

def pareto_frontier(population):
    frontier = []
    for p in population:
        if not any(dominates(other, p) for other in population if other != p):
            frontier.append(p)
    return frontier

def judge(results):
    frontier = pareto_frontier(results)
    # For reporting, pick lowest error and highest cost extremes
    best = min(frontier, key=lambda x: x["error"])
    cheapest = min(frontier, key=lambda x: x["cost"])
    return frontier, best, cheapest

def meta_controller(memory):
    if len(memory) < 5:
        return "explore"
    last = memory[-5:]
    errors = [x["error"] for x in last]
    if errors[-1] >= errors[0]:
        return "disrupt"
    return "stabilize"

def init_population(size=4):
    return [
        {
            "shots": random.choice([128, 256, 512, 1024]),
            "depth": random.choice([5, 10, 20])
        }
        for _ in range(size)
    ]

def run_lab(generations=20):
    memory = load_memory()
    population = init_population()
    best_ever = None
    for gen in range(generations):
        print(f"\n⚛️ Generation {gen+1}")
        results = [experimentalist(p) for p in population]
        memory.extend(results)
        frontier, best, cheapest = judge(results)
        if best_ever is None or best["error"] < best_ever["error"]:
            best_ever = best
        print(f"Pareto frontier ({len(frontier)} configs):")
        for p in frontier:
            print(f"  shots={p['shots']}, depth={p['depth']}, error={p['error']:.5f}, cost={p['cost']}, time={p['time']:.3f}")
        print(f"Best error: {best['error']:.5f} | Cheapest: cost={cheapest['cost']}, error={cheapest['error']:.5f}")
        mode = meta_controller(memory)
        print(f"Mode: {mode}")
        next_population = []
        next_population += theorist(results)
        if mode == "disrupt":
            next_population.append(challenger(best))
            next_population.append(challenger(best))
        while len(next_population) < 4:
            next_population.append({
                "shots": random.choice([128, 256, 512, 1024, 2048]),
                "depth": random.choice([5, 10, 20, 40])
            })
        population = next_population
    save_memory(memory)
    print("\n🚀 BEST EVER FOUND")
    print(best_ever)
    print("\nPareto frontier (final generation):")
    for p in frontier:
        print(f"  shots={p['shots']}, depth={p['depth']}, error={p['error']:.5f}, cost={p['cost']}, time={p['time']:.3f}")

if __name__ == "__main__":
    run_lab()
