import pytest

from osiris.runtime.adapters import default_adapters
from osiris.runtime.extensions import (
    CapabilityPack,
    ExtensionRegistry,
    MCPServerRegistration,
    PluginManifest,
)


def test_extensions_do_not_gain_permissions_dynamically():
    registry = ExtensionRegistry()
    with pytest.raises(PermissionError):
        registry.register_pack(CapabilityPack("safe", "1.0", "0" * 64, ("read",)))

    plugin = PluginManifest("plugin", "1.0", "1.0", ("workspace.read",), ())
    registry.register_plugin(plugin)
    assert registry.plugins["plugin"] == plugin


def test_mcp_registration_is_disabled_by_default():
    registry = ExtensionRegistry()
    registration = MCPServerRegistration("local", "stdio", ("server",))
    registry.register_mcp(registration)
    assert registry.mcp_servers["local"].enabled is False

    with pytest.raises(PermissionError):
        registry.register_mcp(MCPServerRegistration("enabled", "stdio", enabled=True))


def test_external_adapters_are_disabled():
    adapters = default_adapters()
    assert set(adapters) == {"ollama", "vertex_ai", "cloud_run", "pubsub", "quantum", "research"}
    with pytest.raises(PermissionError):
        adapters["vertex_ai"].execute({"prompt": "synthetic"})
