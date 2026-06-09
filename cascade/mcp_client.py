"""MCP (Model Context Protocol) client — connect to external tool servers."""

import json
import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


class MCPClient:
    """Client for MCP servers via stdio transport."""

    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process: subprocess.Popen | None = None
        self.tools: list[dict[str, Any]] = []

    def connect(self) -> bool:
        """Start the MCP server process."""
        try:
            env = {**subprocess.os.environ, **self.env}
            self.process = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            # Initialize
            init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "cascade-cli", "version": "2.6.0"}}}
            self._send(init_request)
            init_response = self._recv()
            if init_response and "result" in init_response:
                # Send initialized notification
                self._send({"jsonrpc": "2.0", "method": "initialized"})
                # List tools
                self._send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                tools_response = self._recv()
                if tools_response and "result" in tools_response:
                    self.tools = tools_response["result"].get("tools", [])
                print_success(f"MCP connected: {len(self.tools)} tools available")
                return True
            return False
        except Exception as e:
            print_error(f"MCP connection failed: {e}")
            return False

    def _send(self, msg: dict[str, Any]) -> None:
        if self.process and self.process.stdin:
            data = json.dumps(msg) + "\n"
            self.process.stdin.write(data)
            self.process.stdin.flush()

    def _recv(self) -> dict[str, Any] | None:
        if self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return None
        return None

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool."""
        if not self.process:
            return {"error": "Not connected"}
        request = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        self._send(request)
        response = self._recv()
        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            return {"error": response["error"]}
        return {"error": "No response"}

    def disconnect(self) -> None:
        if self.process:
            self.process.terminate()
            self.process = None

    def list_tools(self) -> list[dict[str, Any]]:
        return self.tools


def load_mcp_servers(config: dict[str, Any]) -> list[MCPClient]:
    """Load MCP servers from config."""
    clients = []
    mcp_config = config.get("mcp_servers", {})
    for name, server in mcp_config.items():
        cmd = server.get("command", "")
        args = server.get("args", [])
        env = server.get("env", {})
        if cmd:
            client = MCPClient(cmd, args, env)
            if client.connect():
                clients.append(client)
                print_info(f"MCP server '{name}' connected")
    return clients
