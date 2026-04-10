"""Re-export from osiris_elo_tournament."""
import importlib as _il
_m = _il.import_module("osiris_elo_tournament")
globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
