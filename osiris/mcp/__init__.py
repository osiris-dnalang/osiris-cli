"""
osiris.mcp — Model Context Protocol server & client
====================================================

Stdlib-only JSON-RPC 2.0 server over HTTP.  Binds to 127.0.0.1 only.
Zero external dependencies.
"""

import json
import threading
import time
import logging
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Dict, List, Optional

__all__ = ["MCPServer", "MCPClient", "MCPTool"]

logger = logging.getLogger(__name__)


class MCPTool:
    """Descriptor for a registered tool."""

    __slots__ = ("name", "description", "input_schema", "handler")

    def __init__(self, name: str, handler: Callable,
                 description: str = "", input_schema: Optional[Dict] = None):
        self.name = name
        self.handler = handler
        self.description = description
        self.input_schema = input_schema or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class _MCPRequestHandler(BaseHTTPRequestHandler):
    """JSON-RPC 2.0 handler."""

    server: "MCPServer"  # type: ignore[assignment]

    def log_message(self, fmt: str, *args):  # suppress default stderr logs
        logger.debug(fmt, *args)

    def do_POST(self):  # noqa: N802 — required by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            request = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._reply(400, {"error": "invalid JSON"})
            return

        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": self.server.name, "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            }
        elif method == "tools/list":
            result = {"tools": [t.to_dict() for t in self.server._tools.values()]}
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            tool = self.server._tools.get(tool_name)
            if tool is None:
                self._reply(200, {
                    "jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                })
                return
            try:
                output = tool.handler(**arguments)
                result = {"content": [{"type": "text", "text": json.dumps(output, default=str)}]}
            except Exception as exc:
                result = {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}
        elif method == "ping":
            result = {"status": "pong"}
        else:
            self._reply(200, {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            })
            return

        self._reply(200, {"jsonrpc": "2.0", "id": req_id, "result": result})

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._reply(200, {"status": "ok", "server": self.server.name,
                              "tools": len(self.server._tools), "uptime_s": self.server.uptime})
        else:
            self._reply(404, {"error": "not found"})

    def _reply(self, code: int, body: Any):
        payload = json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class MCPServer:
    """JSON-RPC 2.0 MCP server over HTTP (localhost only)."""

    def __init__(self, name: str = "osiris", host: str = "127.0.0.1", port: int = 3000):
        self.name = name
        self.host = host
        self.port = port
        self._tools: Dict[str, MCPTool] = {}
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._started_at: Optional[float] = None

    # -- Tool registration -------------------------------------------------

    def register_tool(self, name: str, handler: Callable,
                      description: str = "", input_schema: Optional[Dict] = None):
        self._tools[name] = MCPTool(name, handler, description, input_schema)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    # Backward-compatible dict access
    @property
    def tools(self) -> Dict[str, MCPTool]:
        return dict(self._tools)

    # -- Lifecycle ---------------------------------------------------------

    def start(self, blocking: bool = False):
        """Start serving.  *blocking=True* runs in foreground."""
        handler_cls = _MCPRequestHandler
        self._server = HTTPServer((self.host, self.port), handler_cls)
        self._server.name = self.name  # type: ignore[attr-defined]
        self._server._tools = self._tools  # type: ignore[attr-defined]
        self._started_at = time.time()
        if blocking:
            logger.info("MCP server %s listening on %s:%d", self.name, self.host, self.port)
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            logger.info("MCP server %s started on %s:%d (background)", self.name, self.host, self.port)

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None

    @property
    def uptime(self) -> float:
        return round(time.time() - self._started_at, 2) if self._started_at else 0.0

    @property
    def running(self) -> bool:
        return self._server is not None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()


class MCPClient:
    """Minimal JSON-RPC 2.0 client for MCPServer (stdlib only)."""

    def __init__(self, server_url: str = "http://127.0.0.1:3000"):
        self.server_url = server_url.rstrip("/")
        self._req_id = 0

    def _rpc(self, method: str, params: Optional[Dict] = None) -> Any:
        self._req_id += 1
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": method,
            "params": params or {},
        }).encode()
        req = urllib.request.Request(
            self.server_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def initialize(self) -> Dict:
        return self._rpc("initialize")

    def list_tools(self) -> List[Dict]:
        resp = self._rpc("tools/list")
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: Optional[Dict] = None) -> Any:
        resp = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        result = resp.get("result", {})
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except (json.JSONDecodeError, KeyError):
                return content[0].get("text", "")
        return result

    def ping(self) -> bool:
        try:
            resp = self._rpc("ping")
            return resp.get("result", {}).get("status") == "pong"
        except Exception:
            return False

    def health(self) -> Dict:
        req = urllib.request.Request(f"{self.server_url}/health")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}
