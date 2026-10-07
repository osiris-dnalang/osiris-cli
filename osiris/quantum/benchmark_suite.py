"""Re-export from osiris_benchmark_suite."""
import importlib as _il
_m = _il.import_module("osiris_benchmark_suite")
globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
