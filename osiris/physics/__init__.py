"""osiris.physics — Torsion core, bridges, validators."""

import importlib as _il


def __getattr__(name):
    _map = {
        "torsion_core": "osiris.physics.torsion_core",
        "bridges": "osiris.physics.bridges",
        "bridge_validator": "osiris.physics.bridge_validator",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.physics' has no attribute {name!r}")
