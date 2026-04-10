"""osiris.applications — Real-world quantum advantage applications."""
import importlib as _il
try:
    _m = _il.import_module("osiris_applications")
    globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
except ImportError:
    pass
