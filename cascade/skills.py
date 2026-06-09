"""Skill learning system for Cascade CLI — learn patterns from corrections."""

import json
from pathlib import Path
from typing import Any

from .ui import Colors, print_info, print_success

SKILLS_FILE = Path.home() / ".config" / "cascade-cli" / "skills.json"


class SkillManager:
    """Manage learned skills and patterns."""

    def __init__(self) -> None:
        self.skills: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if SKILLS_FILE.exists():
            try:
                self.skills = json.loads(SKILLS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self.skills = {}

    def _save(self) -> None:
        SKILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SKILLS_FILE.write_text(json.dumps(self.skills, indent=2))

    def learn_skill(self, name: str, pattern: str, context: str = "", examples: list[str] | None = None) -> None:
        """Learn a new skill from a successful pattern."""
        self.skills[name] = {
            "pattern": pattern,
            "context": context,
            "examples": examples or [],
            "uses": 0,
        }
        self._save()
        print_success(f"Learned skill: {name}")

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """Get a learned skill."""
        skill = self.skills.get(name)
        if skill:
            skill["uses"] = skill.get("uses", 0) + 1
            self._save()
        return skill

    def find_relevant(self, context: str) -> list[tuple[str, dict[str, Any]]]:
        """Find skills relevant to a context."""
        context_lower = context.lower()
        results = []
        for name, skill in self.skills.items():
            score = 0
            if context_lower in name.lower():
                score += 10
            if context_lower in skill.get("context", "").lower():
                score += 5
            if skill.get("uses", 0) > 5:
                score += 2
            if score > 0:
                results.append((name, skill, score))
        results.sort(key=lambda x: x[2], reverse=True)
        return [(n, s) for n, s, _ in results[:10]]

    def list_skills(self) -> list[tuple[str, str]]:
        """List all skills with descriptions."""
        return [(name, skill.get("context", "")[:50]) for name, skill in self.skills.items()]

    def format_skills(self) -> str:
        """Format skills for display."""
        if not self.skills:
            return f"{Colors.YELLOW}No skills learned yet{Colors.RESET}"

        lines = [f"{Colors.CYAN}Learned Skills:{Colors.RESET}"]
        for name, skill in self.skills.items():
            uses = skill.get("uses", 0)
            context = skill.get("context", "")[:40]
            lines.append(f"  {Colors.YELLOW}{name}{Colors.RESET} (used {uses}x) — {context}")
        return "\n".join(lines)
