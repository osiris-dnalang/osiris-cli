"""Re-export from osiris_cli for backward compatibility."""
import importlib as _il
_m = _il.import_module("osiris_cli")
globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
