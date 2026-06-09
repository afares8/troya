"""File editing with diff preview and apply/reject."""

import difflib
import re
from pathlib import Path
from typing import Any

from .ui import Colors, confirm, print_error, print_info, print_success, print_warning


def extract_file_edits(text: str) -> list[dict[str, str]]:
    """Extract file path and code blocks from AI response for editing.

    Looks for patterns like:
    ```python path/to/file.py
    code here
    ```
    Or:
    ```python
    # File: path/to/file.py
    code here
    ```
    """
    edits = []

    # Pattern 1: language with filepath in fence
    pattern1 = re.compile(
        r"```(?:\w+)?\s+([^\n`]+)\n(.*?)\n```",
        re.DOTALL,
    )

    # Pattern 2: File: comment inside block
    pattern2 = re.compile(
        r"```(?:\w+)?\n(?:#\s*File:\s*([^\n]+)\n)?(.*?)\n```",
        re.DOTALL,
    )

    for match in pattern1.finditer(text):
        filepath = match.group(1).strip()
        code = match.group(2)
        if looks_like_path(filepath):
            edits.append({"path": filepath, "code": code})

    # Deduplicate
    seen = set()
    unique = []
    for e in edits:
        key = (e["path"], e["code"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def looks_like_path(s: str) -> bool:
    """Heuristic to detect if a string looks like a file path."""
    if not s:
        return False
    # Has extension or slash
    return "/" in s or "." in s.split("/")[-1]


def show_diff(original: str, modified: str, filepath: str = "") -> None:
    """Print a unified diff between original and modified content."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    # Ensure lines end with newline for diff
    if original_lines and not original_lines[-1].endswith("\n"):
        original_lines[-1] += "\n"
    if modified_lines and not modified_lines[-1].endswith("\n"):
        modified_lines[-1] += "\n"

    diff = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
        )
    )

    if not diff:
        print_info("No changes detected.")
        return

    print()
    if filepath:
        print(f"{Colors.CYAN}Diff for {Colors.YELLOW}{filepath}{Colors.RESET}:")

    for line in diff:
        line = line.rstrip("\n")
        if line.startswith("+") and not line.startswith("+++"):
            print(f"{Colors.GREEN}{line}{Colors.RESET}")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"{Colors.RED}{line}{Colors.RESET}")
        elif line.startswith("@@"):
            print(f"{Colors.CYAN}{line}{Colors.RESET}")
        elif line.startswith("---") or line.startswith("+++"):
            print(f"{Colors.DIM}{line}{Colors.RESET}")
        else:
            print(line)
    print()


def apply_edit(filepath: str, new_content: str, cwd: Path | None = None) -> bool:
    """Apply an edit to a file, showing diff first and asking for confirmation."""
    target = (cwd or Path.cwd()) / filepath
    target = target.resolve()

    # Security: prevent writing outside cwd or home
    try:
        target.relative_to(Path.cwd())
    except ValueError:
        try:
            target.relative_to(Path.home())
        except ValueError:
            print_error(f"Refusing to write outside project/home: {filepath}")
            return False

    # Read existing content
    original = ""
    if target.exists():
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                original = f.read()
        except Exception as e:
            print_error(f"Cannot read {filepath}: {e}")
            return False

    # Show diff
    show_diff(original, new_content, filepath)

    # Confirm
    action = "Overwrite" if target.exists() else "Create"
    if not confirm(f"{action} {filepath}?", default=False):
        print_info("Edit cancelled.")
        return False

    # Write
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        print_success(f"{'Overwritten' if original else 'Created'} {filepath}")
        return True
    except Exception as e:
        print_error(f"Failed to write {filepath}: {e}")
        return False


def handle_edits_from_response(text: str, cwd: Path | None = None) -> int:
    """Detect and handle all file edits in an AI response.

    Returns number of edits applied.
    """
    edits = extract_file_edits(text)
    if not edits:
        return 0

    print()
    print_warning(f"Detected {len(edits)} file edit suggestion(s)")

    applied = 0
    for edit in edits:
        print()
        print_info(f"Suggested edit: {Colors.YELLOW}{edit['path']}{Colors.RESET}")
        if apply_edit(edit["path"], edit["code"], cwd):
            applied += 1

    return applied


def read_file_for_edit(filepath: str, cwd: Path | None = None) -> str:
    """Read a file safely for editing context."""
    target = (cwd or Path.cwd()) / filepath
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        print_error(f"Cannot read {filepath}: {e}")
        return ""
