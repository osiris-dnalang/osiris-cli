"""osiris.scimitar — SCIMITAR SSE system.

Re-exports SCIMITAR agent from osiris.agents.
"""

try:
    from osiris.agents.scimitar import SCIMITARAgent
except ImportError:
    pass
