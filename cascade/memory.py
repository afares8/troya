"""Knowledge base / memory for Cascade CLI — learns from corrections and preferences."""

import json
import re
from pathlib import Path
from typing import Any

from .ui import Colors, print_info, print_success

MEMORY_FILE = Path.home() / ".config" / "cascade-cli" / "memory.json"


class MemoryStore:
    """Persistent memory for the CLI — corrections, preferences, facts."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {
            "corrections": [],  # User corrections to LLM outputs
            "preferences": {},  # User preferences per project
            "facts": [],  # Learned facts about codebase
            "patterns": {},  # Code patterns the user likes
        }
        self._load()

    def _load(self) -> None:
        if MEMORY_FILE.exists():
            try:
                self.data = json.loads(MEMORY_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_FILE.write_text(json.dumps(self.data, indent=2))

    def add_correction(self, original: str, correction: str, context: str = "") -> None:
        """Remember a correction the user made."""
        self.data["corrections"].append({
            "original": original[:200],
            "correction": correction[:200],
            "context": context,
        })
        # Keep only last 100
        self.data["corrections"] = self.data["corrections"][-100:]
        self._save()

    def set_preference(self, key: str, value: str, project: str = "global") -> None:
        """Set a user preference."""
        if project not in self.data["preferences"]:
            self.data["preferences"][project] = {}
        self.data["preferences"][project][key] = value
        self._save()

    def get_preference(self, key: str, project: str = "global", default: str = "") -> str:
        """Get a user preference."""
        return self.data["preferences"].get(project, {}).get(key, default)

    def add_fact(self, subject: str, fact: str) -> None:
        """Remember a fact about the codebase."""
        self.data["facts"].append({"subject": subject, "fact": fact})
        self.data["facts"] = self.data["facts"][-200:]
        self._save()

    def find_facts(self, query: str) -> list[dict[str, str]]:
        """Find facts matching a query."""
        query_lower = query.lower()
        results = []
        for fact in self.data["facts"]:
            if query_lower in fact["subject"].lower() or query_lower in fact["fact"].lower():
                results.append(fact)
        return results

    def get_relevant_context(self, query: str, project: str = "global") -> str:
        """Get relevant memory context for a query."""
        parts = []

        # Preferences
        prefs = self.data["preferences"].get(project, {})
        if prefs:
            parts.append("User preferences:")
            for k, v in prefs.items():
                parts.append(f"  - {k}: {v}")

        # Corrections
        relevant_corrections = []
        query_lower = query.lower()
        for c in self.data["corrections"][-10:]:
            if query_lower in c["original"].lower() or query_lower in c["correction"].lower():
                relevant_corrections.append(c)

        if relevant_corrections:
            parts.append("Recent corrections:")
            for c in relevant_corrections[:3]:
                parts.append(f"  - '{c['original'][:60]}...' → '{c['correction'][:60]}...'")

        # Facts
        facts = self.find_facts(query)
        if facts:
            parts.append("Known facts:")
            for f in facts[:3]:
                parts.append(f"  - {f['subject']}: {f['fact'][:100]}")

        return "\n".join(parts) if parts else ""

    def format_memory(self) -> str:
        """Format memory contents for display."""
        lines = []
        lines.append(f"{Colors.CYAN}{'─' * 40}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Memory Store{Colors.RESET}")
        lines.append(f"{Colors.CYAN}{'─' * 40}{Colors.RESET}")
        lines.append(f"Corrections: {len(self.data['corrections'])}")
        lines.append(f"Preferences: {sum(len(v) for v in self.data['preferences'].values())}")
        lines.append(f"Facts: {len(self.data['facts'])}")

        if self.data["preferences"]:
            lines.append("")
            lines.append(f"{Colors.YELLOW}Preferences:{Colors.RESET}")
            for project, prefs in self.data["preferences"].items():
                lines.append(f"  [{project}]")
                for k, v in prefs.items():
                    lines.append(f"    {k}: {v}")

        if self.data["facts"]:
            lines.append("")
            lines.append(f"{Colors.YELLOW}Recent facts:{Colors.RESET}")
            for f in self.data["facts"][-5:]:
                lines.append(f"  • {f['subject']}: {f['fact'][:80]}")

        return "\n".join(lines)
