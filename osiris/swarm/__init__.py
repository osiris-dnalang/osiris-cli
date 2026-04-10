"""osiris.swarm — NCLLM swarm, cognitive mesh, introspection, ultra-coder, ELO."""

import importlib as _il


def __getattr__(name):
    _map = {
        "cognitive_mesh": "osiris.swarm.cognitive_mesh",
        "ncllm_swarm": "osiris.swarm.ncllm_swarm",
        "feedback_bus": "osiris.swarm.feedback_bus",
        "introspection": "osiris.swarm.introspection",
        "ultra_coder": "osiris.swarm.ultra_coder",
        "elo_tournament": "osiris.swarm.elo_tournament",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.swarm' has no attribute {name!r}")
