"""Re-export from osiris_auto_discovery."""
import importlib as _il
_m = _il.import_module("osiris_auto_discovery")
globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
