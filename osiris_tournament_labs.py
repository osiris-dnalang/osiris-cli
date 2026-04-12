# OSIRIS Tournament Labs

"""
This module implements the Tournament Labs extension for OSIRIS:
- Multiple labs (populations) with different strategies evolve in parallel
- Each lab maintains its own memory and population
- After each generation, labs' Pareto frontiers are compared
- The best-performing labs propagate their strategies, others are replaced
"""

import random
import json
import os
import copy

MEMORY_FILE = "osiris_tournament_memory.json"

class Lab:
    def __init__(self, strategy, pop_size=4):
        self.strategy = strategy  # e.g., 'explorer', 'conservative', 'cost-min'
        self.memory = []
        self.population = self.init_population(pop_size)
        self.pop_size = pop_size

    def init_population(self, size):
        return [
            {"shots": random.choice([128, 256, 512, 1024, 2048, 4096]),
             "depth": random.choice([5, 10, 20, 40])}
            for _ in range(size)
        ]

    def run_experiment(self, shots, depth):
        base_error = (1 / (shots ** 0.5)) + (depth * 0.002)
        noise = random.uniform(0.0, 0.01)
        error = base_error + noise
        cost = shots
        time = shots * 0.001
        return {"error": error, "cost": cost, "time": time}

    def experimentalist(self, config):
        result = self.run_experiment(config["shots"], config["depth"])
        return {**config, **result}

    def theorist(self, population):
        best = sorted(population, key=lambda x: x["error"])[:2]
        children = []
        for b in best:
            if self.strategy == 'explorer':
                children.append({
                    "shots": max(128, int(b["shots"] * random.uniform(0.5, 1.5))),
                    "depth": max(1, int(b["depth"] * random.uniform(0.5, 1.5)))
                })
            elif self.strategy == 'conservative':
                children.append({
                    "shots": max(128, int(b["shots"] * random.uniform(0.9, 1.1))),
                    "depth": max(1, int(b["depth"] * random.uniform(0.9, 1.1)))
                })
            elif self.strategy == 'cost-min':
                children.append({
                    "shots": max(128, int(b["shots"] * random.uniform(0.5, 1.0))),
                    "depth": max(1, int(b["depth"] * random.uniform(0.7, 1.0)))
                })
            else:
                children.append({
                    "shots": max(128, int(b["shots"] * random.uniform(0.7, 1.3))),
                    "depth": max(1, int(b["depth"] * random.uniform(0.7, 1.3)))
                })
        return children

    def challenger(self, best):
        return {
            "shots": max(128, int(best["shots"] * random.uniform(0.3, 0.7))),
            "depth": max(1, int(best["depth"] * random.uniform(1.5, 2.5)))
        }

    def dominates(self, a, b):
        return (
            a["error"] <= b["error"] and
            a["cost"] <= b["cost"] and
            (a["error"] < b["error"] or a["cost"] < b["cost"])
        )

    def pareto_frontier(self, population):
        frontier = []
        for p in population:
            if not any(self.dominates(other, p) for other in population if other != p):
                frontier.append(p)
        return frontier

    def judge(self, results):
        frontier = self.pareto_frontier(results)
        best = min(frontier, key=lambda x: x["error"])
        cheapest = min(frontier, key=lambda x: x["cost"])
        return frontier, best, cheapest

    def meta_controller(self):
        if len(self.memory) < 5:
            return "explore"
        last = self.memory[-5:]
        errors = [x["error"] for x in last]
        if errors[-1] >= errors[0]:
            return "disrupt"
        return "stabilize"

    def evolve(self):
        results = [self.experimentalist(p) for p in self.population]
        self.memory.extend(results)
        frontier, best, cheapest = self.judge(results)
        mode = self.meta_controller()
        next_population = self.theorist(results)
        if mode == "disrupt":
            next_population.append(self.challenger(best))
            next_population.append(self.challenger(best))
        while len(next_population) < self.pop_size:
            next_population.append({
                "shots": random.choice([128, 256, 512, 1024, 2048, 4096]),
                "depth": random.choice([5, 10, 20, 40])
            })
        self.population = next_population
        return frontier, best, cheapest


def save_labs_memory(labs):
    data = {lab.strategy: lab.memory for lab in labs}
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_labs_memory(strategies):
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
        labs = []
        for s in strategies:
            lab = Lab(s)
            lab.memory = data.get(s, [])
            labs.append(lab)
        return labs
    else:
        return [Lab(s) for s in strategies]

def run_tournament_labs(generations=15, pop_size=4, strategies=None):
    if strategies is None:
        strategies = ['explorer', 'conservative', 'cost-min', 'default']
    labs = load_labs_memory(strategies)
    for lab in labs:
        lab.pop_size = pop_size
        lab.population = lab.init_population(pop_size)
    for gen in range(generations):
        print(f"\n🏆 Generation {gen+1}")
        lab_frontiers = []
        for lab in labs:
            frontier, best, cheapest = lab.evolve()
            lab_frontiers.append((lab.strategy, frontier, best, cheapest))
            print(f"Lab [{lab.strategy}] - Best error: {best['error']:.5f}, Cheapest: {cheapest['cost']}, Pareto: {len(frontier)} configs")
        # Tournament selection: keep top 2 labs by best error
        sorted_labs = sorted(lab_frontiers, key=lambda x: x[2]['error'])
        survivors = [x[0] for x in sorted_labs[:2]]
        # Replace losing labs with mutated survivors
        for i, lab in enumerate(labs):
            if lab.strategy not in survivors:
                donor = labs[[l.strategy for l in labs].index(survivors[i%2])]
                lab.population = copy.deepcopy(donor.population)
                lab.memory = copy.deepcopy(donor.memory)
        save_labs_memory(labs)
    print("\n🏆 Tournament complete. Final lab frontiers:")
    for lab in labs:
        frontier = lab.pareto_frontier([lab.experimentalist(p) for p in lab.population])
        print(f"Lab [{lab.strategy}] Pareto configs:")
        for p in frontier:
            print(f"  shots={p['shots']}, depth={p['depth']}, error={p['error']:.5f}, cost={p['cost']}, time={p['time']:.3f}")

if __name__ == "__main__":
    run_tournament_labs()
