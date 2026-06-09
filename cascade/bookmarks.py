"""Bookmark system for Cascade CLI — save important functions/files for quick access."""

import json
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success

BOOKMARKS_FILE = Path.home() / ".config" / "cascade-cli" / "bookmarks.json"


class BookmarkManager:
    """Manage bookmarks for functions, files, and code locations."""

    def __init__(self) -> None:
        self.bookmarks: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if BOOKMARKS_FILE.exists():
            try:
                self.bookmarks = json.loads(BOOKMARKS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self.bookmarks = []

    def _save(self) -> None:
        BOOKMARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        BOOKMARKS_FILE.write_text(json.dumps(self.bookmarks, indent=2))

    def add(self, name: str, filepath: Path, line: int = 0, description: str = "") -> None:
        """Add a bookmark."""
        # Remove existing with same name
        self.bookmarks = [b for b in self.bookmarks if b["name"] != name]
        self.bookmarks.append({
            "name": name,
            "file": str(filepath),
            "line": line,
            "description": description,
        })
        self._save()
        print_success(f"Bookmarked '{name}' → {filepath}:{line}")

    def remove(self, name: str) -> bool:
        """Remove a bookmark by name."""
        original_len = len(self.bookmarks)
        self.bookmarks = [b for b in self.bookmarks if b["name"] != name]
        if len(self.bookmarks) < original_len:
            self._save()
            print_success(f"Removed bookmark '{name}'")
            return True
        print_error(f"Bookmark '{name}' not found")
        return False

    def list(self, project_root: Path | None = None) -> list[dict[str, Any]]:
        """List bookmarks, optionally filtered by project."""
        if project_root:
            project_str = str(project_root)
            return [b for b in self.bookmarks if b["file"].startswith(project_str)]
        return self.bookmarks

    def jump(self, name: str) -> dict[str, Any] | None:
        """Get bookmark location for jumping."""
        for b in self.bookmarks:
            if b["name"] == name:
                return b
        return None

    def format_list(self, project_root: Path | None = None) -> str:
        """Format bookmarks for display."""
        bookmarks = self.list(project_root)
        if not bookmarks:
            return f"{Colors.YELLOW}No bookmarks saved{Colors.RESET}"

        lines = [f"{Colors.CYAN}Bookmarks:{Colors.RESET}"]
        for i, b in enumerate(bookmarks, 1):
            filepath = b["file"]
            if project_root:
                try:
                    filepath = str(Path(filepath).relative_to(project_root))
                except ValueError:
                    pass
            line_info = f":{b['line']}" if b["line"] else ""
            desc = f" — {b['description']}" if b["description"] else ""
            lines.append(f"  {Colors.YELLOW}{i}.{Colors.RESET} {b['name']} → {filepath}{line_info}{desc}")
        return "\n".join(lines)


def add_bookmark_at_cursor(context, name: str) -> None:
    """Add bookmark at current position using context."""
    bm = BookmarkManager()
    # Try to find the current file from context
    current_file = None
    for f in context.files:
        current_file = Path(f)
        break

    if current_file:
        bm.add(name, current_file, description="Added from CLI")
    else:
        print_error("No file in context. Use /read <file> first.")
