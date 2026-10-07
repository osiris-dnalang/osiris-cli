"""Re-export from osiris_zenodo_publisher."""
import importlib as _il
_m = _il.import_module("osiris_zenodo_publisher")
globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
