import json
import os

ELO_FILE = "agent_elo.json"

def load_elo():
    if not os.path.exists(ELO_FILE):
        return {"refactor_agent": 1000}
    return json.load(open(ELO_FILE))

def save_elo(data):
    json.dump(data, open(ELO_FILE, "w"), indent=2)

def update_elo(agent, success):
    elo = load_elo()

    current = elo.get(agent, 1000)

    if success:
        current += 10
    else:
        current -= 10

    elo[agent] = current
    save_elo(elo)
