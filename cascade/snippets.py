"""Snippet manager for Cascade CLI — save and reuse code snippets."""

import json
import re
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_success

SNIPPETS_FILE = Path.home() / ".config" / "cascade-cli" / "snippets.json"


class SnippetManager:
    """Manage reusable code snippets."""

    def __init__(self) -> None:
        self.snippets: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if SNIPPETS_FILE.exists():
            try:
                self.snippets = json.loads(SNIPPETS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self.snippets = {}

    def _save(self) -> None:
        SNIPPETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNIPPETS_FILE.write_text(json.dumps(self.snippets, indent=2))

    def add(self, name: str, code: str, language: str = "python", tags: list[str] | None = None) -> None:
        """Add a snippet."""
        self.snippets[name] = {
            "code": code,
            "language": language,
            "tags": tags or [],
        }
        self._save()
        print_success(f"Snippet '{name}' saved")

    def get(self, name: str) -> dict[str, Any] | None:
        """Get a snippet by name."""
        return self.snippets.get(name)

    def remove(self, name: str) -> bool:
        """Remove a snippet."""
        if name in self.snippets:
            del self.snippets[name]
            self._save()
            print_success(f"Snippet '{name}' removed")
            return True
        print_error(f"Snippet '{name}' not found")
        return False

    def search(self, query: str, language: str | None = None) -> list[tuple[str, dict[str, Any]]]:
        """Search snippets by query and optional language."""
        query_lower = query.lower()
        results = []
        for name, snippet in self.snippets.items():
            if language and snippet.get("language") != language:
                continue
            if query_lower in name.lower() or query_lower in snippet["code"].lower():
                results.append((name, snippet))
        return results

    def list_all(self, language: str | None = None) -> list[tuple[str, dict[str, Any]]]:
        """List all snippets."""
        if language:
            return [(n, s) for n, s in self.snippets.items() if s.get("language") == language]
        return list(self.snippets.items())

    def format_snippet(self, name: str) -> str:
        """Format a snippet for display."""
        snippet = self.snippets.get(name)
        if not snippet:
            return f"{Colors.RED}Snippet '{name}' not found{Colors.RESET}"

        lines = []
        lines.append(f"{Colors.CYAN}{'─' * 40}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}{name}{Colors.RESET}  {Colors.DIM}[{snippet['language']}]{Colors.RESET}")
        lines.append(f"{Colors.CYAN}{'─' * 40}{Colors.RESET}")
        if snippet.get("tags"):
            lines.append(f"Tags: {', '.join(snippet['tags'])}")
        lines.append("```" + snippet["language"])
        lines.append(snippet["code"])
        lines.append("```")
        return "\n".join(lines)

    def format_list(self, language: str | None = None) -> str:
        """Format snippet list for display."""
        snippets = self.list_all(language)
        if not snippets:
            lang_msg = f" [{language}]" if language else ""
            return f"{Colors.YELLOW}No snippets{lang_msg}{Colors.RESET}"

        lines = [f"{Colors.CYAN}Snippets:{Colors.RESET}"]
        for name, snippet in snippets:
            tags = f" {Colors.DIM}({', '.join(snippet['tags'])}){Colors.RESET}" if snippet.get("tags") else ""
            lines.append(f"  {Colors.YELLOW}{name}{Colors.RESET} [{snippet['language']}]{tags}")
        return "\n".join(lines)
