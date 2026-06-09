"""Project search utilities (tree, grep)."""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info

# Default patterns to ignore
DEFAULT_IGNORE = {
    ".git", ".svn", ".hg",
    "node_modules", "vendor", "venv", ".venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build", ".next", "out",
    ".idea", ".vscode", ".vs",
    "*.pyc", "*.pyo", "*.so", "*.dylib", "*.dll",
    "*.egg-info", ".DS_Store", "Thumbs.db",
}


def should_ignore(path: Path, ignore_patterns: set[str] | None = None) -> bool:
    """Check if a path should be ignored."""
    patterns = ignore_patterns or DEFAULT_IGNORE
    name = path.name
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern) or name == pattern:
            return True
    return False


def build_tree(
    root: Path | str = ".",
    max_depth: int = 3,
    prefix: str = "",
    current_depth: int = 0,
    ignore: set[str] | None = None,
) -> str:
    """Build an ASCII tree of a directory."""
    root = Path(root).resolve()
    if not root.is_dir():
        return f"Not a directory: {root}"

    if current_depth > max_depth:
        return ""

    lines = []
    try:
        entries = [
            e for e in root.iterdir()
            if not should_ignore(e, ignore)
        ]
    except PermissionError:
        return ""

    entries = sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower()))

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{Colors.CYAN}{entry.name}/{Colors.RESET}")
            extension = "    " if is_last else "│   "
            subtree = build_tree(
                entry, max_depth, prefix + extension, current_depth + 1, ignore
            )
            if subtree:
                lines.append(subtree)
        else:
            size = entry.stat().st_size
            size_str = f" {Colors.DIM}({format_size(size)}){Colors.RESET}"
            lines.append(f"{prefix}{connector}{entry.name}{size_str}")

    return "\n".join(lines)


def format_size(size: int) -> str:
    """Format byte size to human readable."""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def grep_project(
    pattern: str,
    root: Path | str = ".",
    file_pattern: str = "*",
    max_results: int = 30,
    ignore: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Search for a regex pattern across project files."""
    root = Path(root).resolve()
    results = []
    compiled = re.compile(pattern, re.IGNORECASE)

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter ignored directories inline
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore(Path(dirpath) / d, ignore)
        ]

        for filename in filenames:
            if not fnmatch.fnmatch(filename, file_pattern):
                continue
            filepath = Path(dirpath) / filename
            if should_ignore(filepath, ignore):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        if compiled.search(line):
                            rel = str(filepath.relative_to(root))
                            results.append({
                                "file": rel,
                                "line": lineno,
                                "text": line.rstrip("\n"),
                            })
                            if len(results) >= max_results:
                                return results
            except (IOError, OSError):
                continue

    return results


def print_grep_results(results: list[dict[str, Any]], pattern: str) -> None:
    """Print grep results formatted."""
    if not results:
        print_info(f"No matches found for '{pattern}'")
        return

    print(f"{Colors.CYAN}Found {len(results)} match(es) for '{pattern}':{Colors.RESET}\n")

    for r in results:
        print(
            f"{Colors.YELLOW}{r['file']}:{r['line']}{Colors.RESET}  "
            f"{r['text'][:120]}"
        )


def get_project_stats(root: Path | str = ".") -> dict[str, Any]:
    """Get basic project statistics."""
    root = Path(root).resolve()
    stats = {
        "total_files": 0,
        "total_dirs": 0,
        "total_size": 0,
        "languages": {},
    }

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore(Path(dirpath) / d)
        ]

        stats["total_dirs"] += len(dirnames)

        for filename in filenames:
            filepath = Path(dirpath) / filename
            if should_ignore(filepath):
                continue

            stats["total_files"] += 1
            try:
                size = filepath.stat().st_size
                stats["total_size"] += size
            except OSError:
                pass

            ext = filepath.suffix.lower()
            if ext:
                stats["languages"][ext] = stats["languages"].get(ext, 0) + 1

    return stats
