"""osiris.forge — Manufacturing and 3MF generation."""

import importlib as _il


def __getattr__(name):
    _map = {
        "forge": "osiris.forge.forge",
        "manufacturing_3mf": "osiris.forge.manufacturing_3mf",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.forge' has no attribute {name!r}")
