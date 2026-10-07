"""Re-export from osiris_tui_core (Textual TUI)."""
import importlib as _il
_m = _il.import_module("osiris_tui_core")
globals().update({k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")})
