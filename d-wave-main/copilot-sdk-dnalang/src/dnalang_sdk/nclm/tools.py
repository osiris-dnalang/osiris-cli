"""
NCLM tools module disabled for offline-only build.
"""

def dispatch_tool(*args, **kwargs):
    raise RuntimeError("Offline NCLM build: nclm.tools is disabled")

# For compatibility, define basic no-op command set
def available_tools():
    return []

