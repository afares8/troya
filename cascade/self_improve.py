"""Self-improvement module — Cascade can analyze and improve its own code."""

import inspect
import pkgutil
from pathlib import Path
from typing import Any

from .editor import handle_edits_from_response
from .ui import Colors, confirm, print_error, print_header, print_info, print_success, print_warning


def get_source_files(package_dir: Path) -> list[Path]:
    """List all Python source files in the cascade package."""
    files = []
    for f in sorted(package_dir.glob("*.py")):
        if f.name.startswith("_") and f.name != "__init__.py":
            continue
        files.append(f)
    return files


def read_own_source(path: Path) -> str:
    """Read source of a cascade module."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"Error reading {path}: {e}"


def build_self_context(query: str, max_chars: int = 8000) -> str:
    """Build context from own source code relevant to the query."""
    package_dir = Path(__file__).parent
    files = get_source_files(package_dir)

    # Simple relevance: include files whose names match keywords in query
    query_lower = query.lower()
    relevant = []
    for f in files:
        name = f.stem.lower()
        if any(kw in query_lower for kw in [name, name.replace("_", " ")]):
            relevant.append(f)

    # If none matched, include main modules
    if not relevant:
        relevant = files[:6]

    parts = ["This is the source code of Cascade CLI itself. You can propose improvements."]
    total = 0
    for f in relevant:
        content = read_own_source(f)
        snippet = content[:1500]
        total += len(snippet)
        if total > max_chars:
            break
        parts.append(f"\n--- File: {f.name} ---\n{snippet}\n---")

    return "\n".join(parts)


def analyze_self(client, query: str) -> str:
    """Ask the AI to analyze Cascade's own code and suggest improvements."""
    print_header("🔧 Self-Improvement Mode")
    print_info(f"Analyzing own code for: {query}")

    context = build_self_context(query)
    messages = [
        {"role": "system", "content": (
            "You are a senior software engineer reviewing the Cascade CLI codebase. "
            "Analyze the provided source code and suggest concrete improvements. "
            "When suggesting file changes, output the FULL file content inside a code block "
            "with the file path as the language specifier, like: ```python path/to/file.py. "
            "Focus on bugs, performance, clean code, and missing features."
        )},
        {"role": "user", "content": f"{context}\n\nTask: {query}"},
    ]

    response = client.chat(messages)
    if not response:
        return "No response from LLM."

    return response


def apply_self_improvements(response: str, package_dir: Path) -> int:
    """Apply any file edits suggested in the self-improvement response."""
    return handle_edits_from_response(response, package_dir)
