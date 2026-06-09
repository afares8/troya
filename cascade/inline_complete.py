"""Inline completions — Copilot-style suggestions in the REPL."""

from typing import Any

from .ui import Colors, print_info

COMPLETION_CACHE: dict[str, str] = {}


def get_inline_suggestion(client, text_before_cursor: str, context_files: dict[str, str]) -> str:
    """Ask the LLM for a completion of the current line."""
    if not text_before_cursor.strip():
        return ""

    # Build mini-context from open files
    file_context = ""
    for path, content in list(context_files.items())[:3]:
        file_context += f"\n--- {path} ---\n{content[:500]}\n"

    messages = [
        {"role": "system", "content": (
            "You are an intelligent code completion assistant. Given partial code, "
            "suggest the next 1-3 lines of code. Respond with ONLY the completion, "
            "no explanations, no markdown."
        )},
        {"role": "user", "content": f"{file_context}\n\nCurrent line:\n{text_before_cursor}\n\nComplete the code:"},
    ]

    try:
        response = client.chat(messages)
        if response:
            # Clean up
            suggestion = response.strip()
            if suggestion.startswith("```"):
                lines = suggestion.splitlines()
                # Remove code fences
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                suggestion = "\n".join(lines).strip()
            return suggestion
    except Exception:
        pass
    return ""


def render_suggestion(suggestion: str) -> str:
    """Render suggestion in dim color for display."""
    if not suggestion:
        return ""
    lines = suggestion.splitlines()
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1] + " ..."
    return f"{Colors.DIM}{' | '.join(lines)}{Colors.RESET}"
