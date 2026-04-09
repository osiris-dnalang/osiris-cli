"""
Gemini integration intentionally disabled in offline-only NCLM build.

This module is kept as a placeholder stub and always raises if used.
"""

class GeminiModelProvider:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: Gemini provider disabled")

class GeminiConfig:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: Gemini provider disabled")

class GeminiMessage:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: Gemini provider disabled")

async def gemini_infer_simple(*args, **kwargs):
    raise RuntimeError("Offline NCLM build: Gemini provider disabled")
