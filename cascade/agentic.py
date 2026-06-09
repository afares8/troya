"""Agentic reasoning for Cascade CLI - autonomously uses tools to accomplish tasks."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .search import grep_project
from .ui import Colors, confirm, print_error, print_info, print_success, print_warning

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file to understand code or configuration.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory to discover the project structure.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Directory path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a regex pattern across all project files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern"},
                    "file_pattern": {"type": "string", "description": "Glob pattern for files"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command and get the output. Use for testing, building, or checking system state.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file with new content. USE WITH CARE.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Finish the task and provide the final answer to the user.",
            "parameters": {
                "type": "object",
                "properties": {"answer": {"type": "string", "description": "Final answer for the user"}},
                "required": ["answer"],
            },
        },
    },
]

AGENTIC_SYSTEM_PROMPT = (
    "You are an autonomous AI coding assistant. You have access to tools. "
    "When given a task, think step by step and use tools to gather information. "
    "You can read files, search code, list directories, run shell commands, and write files. "
    "When you have enough information to answer, use the 'finish' tool. "
    "Be concise. Do not ask the user for clarification — act autonomously."
)


def execute_tool(name: str, arguments: dict[str, Any], cwd: Path) -> dict[str, Any]:
    """Execute a tool and return the result."""
    if name == "read_file":
        path = cwd / arguments["path"]
        if not path.exists():
            return {"error": f"File not found: {arguments['path']}"}
        try:
            return {"content": path.read_text(encoding="utf-8")[:4000]}
        except UnicodeDecodeError:
            return {"error": "Binary file"}

    elif name == "list_files":
        path = cwd / arguments.get("path", ".")
        if not path.exists():
            return {"error": f"Directory not found: {arguments.get('path', '.')}"}
        entries = []
        for entry in sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            entries.append({"name": entry.name, "is_dir": entry.is_dir(), "size": entry.stat().st_size if entry.is_file() else 0})
        return {"entries": entries}

    elif name == "search_code":
        results = grep_project(arguments["pattern"], root=str(cwd), file_pattern=arguments.get("file_pattern", "*"))
        return {"matches": [{"file": r[0], "line": r[1], "text": r[2]} for r in results[:20]]}

    elif name == "run_shell":
        cmd = arguments["command"]
        dangerous = {"rm -rf /", "dd if=/dev/zero", "mkfs", ":(){ :|:& };:"}
        if any(d in cmd for d in dangerous):
            return {"error": "Command blocked for safety"}
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=str(cwd))
            return {
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Timeout (30s)"}

    elif name == "write_file":
        path = cwd / arguments["path"]
        if not str(path.resolve()).startswith(str(cwd.resolve())):
            return {"error": "Cannot write outside project directory"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(arguments["content"], encoding="utf-8")
        return {"bytes_written": len(arguments["content"])}

    elif name == "finish":
        return {"done": True, "answer": arguments["answer"]}

    return {"error": f"Unknown tool: {name}"}


def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse tool calls from AI response."""
    calls = []
    # Match ```tool or <tool> blocks
    pattern = r'(?:```tool\s*\n|<tool>)(.*?)\n(?:```|</tool>)'
    for m in re.finditer(pattern, text, re.DOTALL):
        try:
            data = json.loads(m.group(1).strip())
            if "name" in data and "arguments" in data:
                calls.append(data)
        except json.JSONDecodeError:
            pass
    return calls


def run_agentic(client, context, executor, user_input: str, max_steps: int = 8) -> str:
    """Run agentic reasoning loop. Returns final answer."""
    print_info("🤖 Agentic mode: thinking step by step...")
    messages = [
        {"role": "system", "content": AGENTIC_SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    for step in range(max_steps):
        response = client.chat(messages)
        if not response:
            return "No response from LLM."

        # Check if it's a finish or contains tool calls
        tool_calls = parse_tool_calls(response)
        if not tool_calls:
            # Try to detect inline tool calls
            tool_calls = parse_tool_calls(response)

        if not tool_calls:
            # No tools called, just a normal response
            context.add_message("user", user_input)
            context.add_message("assistant", response)
            return response

        for tc in tool_calls:
            name = tc["name"]
            args = tc["arguments"]

            if name == "finish":
                context.add_message("user", user_input)
                context.add_message("assistant", args["answer"])
                print_success("✓ Task completed")
                return args["answer"]

            print(f"{Colors.CYAN}  → {name}({', '.join(f'{k}={repr(v)[:40]}' for k, v in args.items())}){Colors.RESET}")

            # For write_file, ask for confirmation
            if name == "write_file":
                if not confirm(f"Agent wants to write to {args.get('path')}. Allow?", default=False):
                    result = {"error": "User denied write"}
                else:
                    result = execute_tool(name, args, context.cwd)
            else:
                result = execute_tool(name, args, context.cwd)

            # Print result briefly
            if "error" in result:
                print_error(f"    Error: {result['error']}")
            elif "stdout" in result:
                out = result["stdout"].strip()[:200]
                if out:
                    print_info(f"    stdout: {out}")
            elif "content" in result:
                print_info(f"    Read {len(result['content'])} chars")
            elif "matches" in result:
                print_info(f"    Found {len(result['matches'])} matches")
            elif "bytes_written" in result:
                print_success(f"    Wrote {result['bytes_written']} bytes")

            messages.append({"role": "assistant", "content": f"Tool call: {name}({json.dumps(args)})\nResult: {json.dumps(result, default=str)[:800]}"})

    context.add_message("user", user_input)
    context.add_message("assistant", response)
    return response + "\n(Reached max steps)"
