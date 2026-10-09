"""Test-session setup shared by every test file.

The swarm and console call whatever Ollama server OLLAMA_HOST names (default
localhost:11434). A busy local Ollama made tests/test_integration.py hang for
minutes on a developer machine, while CI (no Ollama) passed. Tests therefore run
against an address nothing listens on, so every model call takes the documented
fallback path; set OSIRIS_TEST_LIVE_OLLAMA=1 to test against a real server.
"""
import os

if os.environ.get("OSIRIS_TEST_LIVE_OLLAMA") != "1":
    os.environ["OLLAMA_HOST"] = "http://127.0.0.1:9"      # discard port: connection refused at once
