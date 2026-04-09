"""
NCLM chat module disabled for offline-only build.
"""

class NCLMChat:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: nclm.chat disabled")

class NCLMResponseGenerator:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: nclm.chat disabled")

async def run_chat(*args, **kwargs):
    raise RuntimeError("Offline NCLM build: nclm.chat disabled")
