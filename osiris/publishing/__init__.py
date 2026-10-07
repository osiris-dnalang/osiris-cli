"""osiris.publishing — Zenodo, auto-discovery."""

import importlib as _il


def __getattr__(name):
    _map = {
        "zenodo": "osiris.publishing.zenodo",
        "auto_discovery": "osiris.publishing.auto_discovery",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.publishing' has no attribute {name!r}")
