"""Capability-pack, plugin, and MCP boundary registries.

All registries are inert until an operator explicitly installs and approves an
entry. No extension can add permissions dynamically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class CapabilityPack:
    name: str
    version: str
    manifest_hash: str
    allowed_tools: Tuple[str, ...] = ()
    approved: bool = False

    def validate(self) -> None:
        if not self.name or not self.version or len(self.manifest_hash) != 64:
            raise ValueError("capability pack identity is invalid")
        if any(not tool or ":" in tool for tool in self.allowed_tools):
            raise ValueError("capability pack contains an invalid tool name")


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    protocol_version: str
    requested_capabilities: Tuple[str, ...] = ()
    approved_capabilities: Tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.name or not self.version or self.protocol_version != "1.0":
            raise ValueError("unsupported plugin manifest")
        if not set(self.approved_capabilities).issubset(self.requested_capabilities):
            raise ValueError("plugin approval exceeds its request")


@dataclass(frozen=True)
class MCPServerRegistration:
    name: str
    transport: str
    command: Tuple[str, ...] = ()
    enabled: bool = False
    approved_tools: Tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.name or self.transport not in {"stdio", "http"}:
            raise ValueError("invalid MCP registration")
        if self.enabled:
            raise PermissionError("MCP registration requires an explicit gateway approval")


class ExtensionRegistry:
    def __init__(self):
        self.packs: Dict[str, CapabilityPack] = {}
        self.plugins: Dict[str, PluginManifest] = {}
        self.mcp_servers: Dict[str, MCPServerRegistration] = {}

    def register_pack(self, pack: CapabilityPack) -> None:
        pack.validate()
        if not pack.approved:
            raise PermissionError("capability pack is not approved")
        self.packs[pack.name] = pack

    def register_plugin(self, plugin: PluginManifest) -> None:
        plugin.validate()
        self.plugins[plugin.name] = plugin

    def register_mcp(self, server: MCPServerRegistration) -> None:
        server.validate()
        self.mcp_servers[server.name] = server
