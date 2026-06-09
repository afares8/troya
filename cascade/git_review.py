"""Git diff analyzer for Cascade CLI — review PRs and commits from terminal."""

import re
import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success, print_warning


def get_diff(branch: str | None = None, commit: str | None = None) -> str:
    """Get git diff for review."""
    if commit:
        result = subprocess.run(
            ["git", "diff", f"{commit}^", commit],
            capture_output=True, text=True, cwd=str(Path.cwd())
        )
    elif branch:
        result = subprocess.run(
            ["git", "diff", f"origin/{branch}...{branch}"],
            capture_output=True, text=True, cwd=str(Path.cwd())
        )
    else:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, cwd=str(Path.cwd())
        )

    if result.returncode != 0:
        return ""
    return result.stdout


def parse_diff(diff_text: str) -> list[dict[str, Any]]:
    """Parse git diff into per-file hunks."""
    files = []
    current_file = None
    current_hunks = []
    current_hunk_lines = []

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_hunk_lines:
                current_hunks.append("\n".join(current_hunk_lines))
                current_hunk_lines = []
            if current_file:
                files.append({"file": current_file, "hunks": current_hunks})
                current_hunks = []
            # Extract filename
            match = re.search(r'b/(.+)', line)
            current_file = match.group(1) if match else "unknown"

        elif line.startswith("@@"):
            if current_hunk_lines:
                current_hunks.append("\n".join(current_hunk_lines))
                current_hunk_lines = []
            current_hunk_lines.append(line)

        elif current_file is not None:
            current_hunk_lines.append(line)

    if current_file and current_hunk_lines:
        current_hunks.append("\n".join(current_hunk_lines))
    if current_file:
        files.append({"file": current_file, "hunks": current_hunks})

    return files


def analyze_diff(diff_text: str) -> dict[str, Any]:
    """Analyze diff for common issues without LLM."""
    issues = []
    stats = {"files_changed": 0, "insertions": 0, "deletions": 0, "tests_added": 0}

    files = parse_diff(diff_text)
    stats["files_changed"] = len(files)

    for file_data in files:
        filepath = file_data["file"]
        for hunk in file_data["hunks"]:
            for line in hunk.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    stats["insertions"] += 1
                    # Check for issues in added lines
                    clean = line[1:].strip()
                    if re.search(r'(?i)password\s*=\s*["\'][^"\']+["\']', clean):
                        issues.append({"file": filepath, "line": "?", "type": "secret", "message": "Possible hardcoded password"})
                    if re.search(r'(?i)print\(', clean) and "test" not in filepath:
                        issues.append({"file": filepath, "line": "?", "type": "debug", "message": "Debug print statement"})
                    if re.search(r'(?i)TODO|FIXME|HACK|XXX', clean):
                        issues.append({"file": filepath, "line": "?", "type": "todo", "message": f"Found marker: {clean.strip()[:50]}"})
                    if "test" in filepath.lower():
                        stats["tests_added"] += 1

                elif line.startswith("-") and not line.startswith("---"):
                    stats["deletions"] += 1

    return {"stats": stats, "issues": issues, "files": files}


def format_review(report: dict[str, Any]) -> str:
    """Format diff analysis as review comments."""
    lines = []
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}Diff Review{Colors.RESET}")
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")

    stats = report["stats"]
    lines.append(f"Files changed: {stats['files_changed']}")
    lines.append(f"Insertions: {Colors.GREEN}+{stats['insertions']}{Colors.RESET}")
    lines.append(f"Deletions: {Colors.RED}-{stats['deletions']}{Colors.RESET}")
    lines.append(f"Tests touched: {stats['tests_added']}")
    lines.append("")

    if report["issues"]:
        lines.append(f"{Colors.YELLOW}Issues found:{Colors.RESET}")
        for issue in report["issues"]:
            color = {"secret": Colors.RED, "debug": Colors.YELLOW, "todo": Colors.CYAN}.get(issue["type"], Colors.YELLOW)
            lines.append(f"  {color}[{issue['type'].upper()}]{Colors.RESET} {issue['file']}")
            lines.append(f"    → {issue['message']}")
    else:
        lines.append(f"{Colors.GREEN}✓ No obvious issues detected{Colors.RESET}")

    return "\n".join(lines)


def review_commit(commit_hash: str | None = None) -> str:
    """Review a specific commit or HEAD."""
    diff = get_diff(commit=commit_hash)
    if not diff:
        return f"{Colors.RED}No diff found. Are you in a git repo?{Colors.RESET}"
    report = analyze_diff(diff)
    return format_review(report)
