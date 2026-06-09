"""File watcher for Cascade CLI - monitors changes and proactively suggests actions."""

import time
from pathlib import Path
from typing import Any, Callable

from .ui import Colors, print_info, print_warning


def get_file_snapshot(root: Path, patterns: tuple[str, ...] = ("*.py", "*.js", "*.ts", "*.html", "*.css", "*.md")) -> dict[str, float]:
    """Get mtimes of matching files."""
    snapshot = {}
    for pat in patterns:
        for path in root.rglob(pat):
            if path.is_file():
                snapshot[str(path.relative_to(root))] = path.stat().st_mtime
    return snapshot


def watch_project(root: Path, on_change: Callable, interval: float = 2.0) -> None:
    """Watch project files for changes and call on_change when detected."""
    print_info(f"👁  Watching {root} for changes (Ctrl+C to stop)")
    snapshot = get_file_snapshot(root)
    try:
        while True:
            time.sleep(interval)
            new_snapshot = get_file_snapshot(root)
            changes = []
            for path, mtime in new_snapshot.items():
                if path not in snapshot:
                    changes.append(("created", path))
                elif snapshot[path] != mtime:
                    changes.append(("modified", path))
            for path in snapshot:
                if path not in new_snapshot:
                    changes.append(("deleted", path))
            if changes:
                on_change(changes)
            snapshot = new_snapshot
    except KeyboardInterrupt:
        print_info("\nStopped watching.")


def suggest_on_change(client, context, changes: list[tuple[str, str]]) -> None:
    """Ask the AI what to do about detected changes."""
    desc = "\n".join(f"- {kind}: {path}" for kind, path in changes[:5])
    user_msg = f"Files changed in the project:\n{desc}\n\nShould I take any action? (e.g., run tests, format code, review changes)"
    messages = context.get_messages(user_msg)
    response = client.chat(messages)
    if response:
        print_info("Cascade suggests:")
        print(response)
        context.add_message("user", user_msg)
        context.add_message("assistant", response)
