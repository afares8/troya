"""File diff comparison for Cascade CLI — side-by-side or unified."""

import difflib
from pathlib import Path
from typing import Any

from .ui import Colors, print_error


def diff_files(file_a: Path, file_b: Path, context: int = 3) -> str:
    """Compare two files and return unified diff."""
    try:
        lines_a = file_a.read_text().splitlines()
        lines_b = file_b.read_text().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return f"Error reading files: {e}"

    diff = difflib.unified_diff(
        lines_a, lines_b,
        fromfile=str(file_a), tofile=str(file_b),
        lineterm="", n=context
    )
    return "\n".join(diff)


def diff_strings(name_a: str, text_a: str, name_b: str, text_b: str, context: int = 3) -> str:
    """Compare two strings."""
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    diff = difflib.unified_diff(
        lines_a, lines_b,
        fromfile=name_a, tofile=name_b,
        lineterm="", n=context
    )
    return "\n".join(diff)


def side_by_side_diff(lines_a: list[str], lines_b: list[str], width: int = 40) -> str:
    """Generate a side-by-side diff."""
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    result = []
    result.append(f"{Colors.CYAN}{'─' * (width * 2 + 7)}{Colors.RESET}")
    result.append(f"{Colors.CYAN}{'Left':<{width}} │ {'Right':<{width}}{Colors.RESET}")
    result.append(f"{Colors.CYAN}{'─' * (width * 2 + 7)}{Colors.RESET}")

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in lines_a[i1:i2]:
                left = line[:width]
                right = line[:width]
                result.append(f" {left:<{width}}│{right:<{width}}")
        elif tag == "delete":
            for line in lines_a[i1:i2]:
                left = line[:width]
                result.append(f"{Colors.RED}-{left:<{width}}{Colors.RESET}│{'':<{width}}")
        elif tag == "insert":
            for line in lines_b[j1:j2]:
                right = line[:width]
                result.append(f"{'':<{width}}│{Colors.GREEN}+{right:<{width}}{Colors.RESET}")
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                left = lines_a[i1 + k][:width] if i1 + k < i2 else ""
                right = lines_b[j1 + k][:width] if j1 + k < j2 else ""
                result.append(f"{Colors.YELLOW}~{left:<{width}}{Colors.RESET}│{Colors.YELLOW}~{right:<{width}}{Colors.RESET}")

    return "\n".join(result)


def format_diff(diff_text: str) -> str:
    """Format diff with colors."""
    lines = []
    for line in diff_text.split("\n"):
        if line.startswith("+"):
            lines.append(f"{Colors.GREEN}{line}{Colors.RESET}")
        elif line.startswith("-"):
            lines.append(f"{Colors.RED}{line}{Colors.RESET}")
        elif line.startswith("@@"):
            lines.append(f"{Colors.CYAN}{line}{Colors.RESET}")
        elif line.startswith("---") or line.startswith("+++"):
            lines.append(f"{Colors.YELLOW}{line}{Colors.RESET}")
        else:
            lines.append(line)
    return "\n".join(lines)


def word_diff(text_a: str, text_b: str) -> str:
    """Show word-level diff."""
    words_a = text_a.split()
    words_b = text_b.split()
    matcher = difflib.SequenceMatcher(None, words_a, words_b)

    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append(" ".join(words_a[i1:i2]))
        elif tag == "delete":
            result.append(f"{Colors.RED}[- {' '.join(words_a[i1:i2])} -]{Colors.RESET}")
        elif tag == "insert":
            result.append(f"{Colors.GREEN}{{+ {' '.join(words_b[j1:j2])} +}}{Colors.RESET}")
        elif tag == "replace":
            result.append(f"{Colors.YELLOW}[- {' '.join(words_a[i1:i2])} -]{{+ {' '.join(words_b[j1:j2])} +}}{Colors.RESET}")

    return " ".join(result)
