"""osiris.discovery — Quantum discovery engine."""

import importlib as _il
try:
    _m = _il.import_module("osiris_auto_discovery")
    globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
except ImportError:
    pass
