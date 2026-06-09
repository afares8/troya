"""Tool registry for multi-agent system."""

import json
import os
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Callable


def tool(name: str, description: str, params: dict[str, Any]) -> Callable:
    """Decorator to register a tool."""
    def decorator(func: Callable) -> Callable:
        func._tool_name = name
        func._tool_desc = description
        func._tool_params = params
        return func
    return decorator


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, Callable] = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_tool_name"):
                self.tools[attr._tool_name] = attr

    def get_definitions(self) -> list[dict[str, Any]]:
        defs = []
        for name, fn in self.tools.items():
            defs.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": fn._tool_desc,
                    "parameters": {
                        "type": "object",
                        "properties": fn._tool_params,
                        "required": list(fn._tool_params.keys()),
                    },
                },
            })
        return defs

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self.tools:
            return {"error": f"Tool '{name}' not found"}
        try:
            return self.tools[name](**arguments)
        except Exception as e:
            return {"error": str(e)}

    # ===== Tool Implementations =====

    @tool("read_file", "Read contents of a file", {"path": {"type": "string", "description": "Relative file path"}})
    def read_file(self, path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        try:
            content = p.read_text(encoding="utf-8")
            return {"path": path, "content": content, "size": len(content)}
        except UnicodeDecodeError:
            return {"error": "Binary file, cannot read as text"}

    @tool("write_file", "Write content to a file", {
        "path": {"type": "string", "description": "Relative file path"},
        "content": {"type": "string", "description": "Content to write"},
    })
    def write_file(self, path: str, content: str) -> dict[str, Any]:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content)}

    @tool("list_files", "List files in a directory", {"path": {"type": "string", "description": "Directory path"}})
    def list_files(self, path: str = ".") -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"error": f"Directory not found: {path}"}
        entries = []
        for entry in sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            entries.append({"name": entry.name, "is_dir": entry.is_dir(), "size": entry.stat().st_size if entry.is_file() else 0})
        return {"path": path, "entries": entries}

    @tool("run_shell", "Execute a shell command", {"command": {"type": "string", "description": "Shell command to run"}})
    def run_shell(self, command: str) -> dict[str, Any]:
        dangerous = {"rm -rf /", "dd if=/dev/zero", "mkfs", ":(){ :|:& };:"}
        if any(d in command for d in dangerous):
            return {"error": "Command blocked for safety"}
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return {
                "command": command,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 30s"}

    @tool("run_python", "Execute Python code and return result", {"code": {"type": "string", "description": "Python code to execute"}})
    def run_python(self, code: str) -> dict[str, Any]:
        dangerous_keywords = {"import os", "import subprocess", "open(", "__import__", "exec(", "eval(", "compile("}
        lowered = code.lower()
        for kw in dangerous_keywords:
            if kw in lowered:
                return {"error": f"Potentially unsafe code detected: {kw.strip()} blocked in sandbox"}
        try:
            # Restricted execution
            safe_globals = {"__builtins__": {k: v for k, v in __builtins__.__dict__.items() if k in (
                "abs", "all", "any", "bin", "bool", "chr", "dict", "enumerate", "filter", "float",
                "format", "frozenset", "hex", "int", "isinstance", "issubclass", "iter", "len",
                "list", "map", "max", "min", "next", "oct", "ord", "pow", "print", "range",
                "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple", "type",
                "zip", "Exception", "True", "False", "None",
            )}}
            local_ns = {}
            exec(textwrap.dedent(code), safe_globals, local_ns)
            output = local_ns.get("result", "Code executed successfully (no 'result' variable set)")
            return {"output": str(output)[:2000]}
        except Exception as e:
            return {"error": str(e)}

    @tool("search_text", "Search for a regex pattern in files", {
        "pattern": {"type": "string", "description": "Regex pattern to search"},
        "path": {"type": "string", "description": "Directory or file to search"},
    })
    def search_text(self, pattern: str, path: str = ".") -> dict[str, Any]:
        import re
        results = []
        p = Path(path)
        targets = [p] if p.is_file() else list(p.rglob("*"))
        for target in targets:
            if not target.is_file() or target.stat().st_size > 1_000_000:
                continue
            try:
                text = target.read_text(encoding="utf-8")
                for i, line in enumerate(text.splitlines(), 1):
                    if re.search(pattern, line):
                        results.append({"file": str(target), "line": i, "text": line.strip()[:100]})
            except (UnicodeDecodeError, OSError):
                continue
        return {"pattern": pattern, "matches": results[:50]}

    @tool("get_environment", "Get environment info", {})
    def get_environment(self) -> dict[str, Any]:
        return {
            "cwd": str(Path.cwd()),
            "user": os.getenv("USER", "unknown"),
            "python_version": os.sys.version.split()[0],
            "platform": os.sys.platform,
        }
