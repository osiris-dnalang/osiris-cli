import json
import os

MEMORY_FILE = "osiris_memory.json"

def store_experience(entry):
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w") as f:
            json.dump([], f)

    with open(MEMORY_FILE, "r") as f:
        data = json.load(f)

    data.append(entry)

    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)
