"""osiris.core — Shell, CLI, launcher, intent engine, health, orchestrator."""

import importlib as _il


def __getattr__(name):
    _map = {
        "shell": "osiris.core.shell",
        "cli": "osiris.core.cli",
        "launcher": "osiris.core.launcher",
        "intent_engine": "osiris.core.intent_engine",
        "master_prompt": "osiris.core.master_prompt",
        "health": "osiris.core.health",
        "license": "osiris.core.license",
        "verify": "osiris.core.verify",
        "orchestrator": "osiris.core.orchestrator",
        "fei_demo": "osiris.core.fei_demo",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.core' has no attribute {name!r}")
