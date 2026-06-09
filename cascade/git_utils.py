"""Git integration for Cascade CLI."""

import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, confirm, print_error, print_info, print_success, print_warning


def run_git(args: list[str], cwd: Path | None = None) -> tuple[bool, str, str]:
    """Run a git command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd or Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except FileNotFoundError:
        return False, "", "git not found"
    except Exception as e:
        return False, "", str(e)


def is_git_repo(cwd: Path | None = None) -> bool:
    """Check if current directory is inside a git repo."""
    success, _, _ = run_git(["rev-parse", "--git-dir"], cwd)
    return success


def get_repo_info(cwd: Path | None = None) -> dict[str, Any]:
    """Get git repository info."""
    info = {
        "is_repo": False,
        "branch": "",
        "commit": "",
        "remote": "",
        "status": "",
        "modified": [],
        "untracked": [],
        "staged": [],
    }

    if not is_git_repo(cwd):
        return info

    info["is_repo"] = True

    # Branch
    success, stdout, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if success:
        info["branch"] = stdout.strip()

    # Short commit hash
    success, stdout, _ = run_git(["rev-parse", "--short", "HEAD"], cwd)
    if success:
        info["commit"] = stdout.strip()

    # Remote URL
    success, stdout, _ = run_git(["remote", "get-url", "origin"], cwd)
    if success:
        info["remote"] = stdout.strip()

    # Status
    success, stdout, _ = run_git(["status", "--porcelain"], cwd)
    if success:
        info["status"] = stdout
        for line in stdout.splitlines():
            if len(line) >= 2:
                index_status = line[0]
                worktree_status = line[1]
                filepath = line[3:]

                if index_status in ("M", "A", "D", "R", "C"):
                    info["staged"].append(f"{index_status} {filepath}")
                if worktree_status in ("M", "D"):
                    info["modified"].append(f"{worktree_status} {filepath}")
                if worktree_status == "?":
                    info["untracked"].append(filepath)

    return info


def print_repo_status(cwd: Path | None = None) -> None:
    """Print formatted git repository status."""
    info = get_repo_info(cwd)

    if not info["is_repo"]:
        print_warning("Not a git repository.")
        return

    print(f"{Colors.CYAN}Git Repository:{Colors.RESET}")
    print(f"  Branch: {Colors.GREEN}{info['branch']}{Colors.RESET}")
    print(f"  Commit: {Colors.DIM}{info['commit']}{Colors.RESET}")
    if info["remote"]:
        print(f"  Remote: {Colors.DIM}{info['remote']}{Colors.RESET}")

    if info["staged"]:
        print(f"\n  {Colors.GREEN}Staged ({len(info['staged'])}):{Colors.RESET}")
        for f in info["staged"][:10]:
            print(f"    + {f}")
        if len(info["staged"]) > 10:
            print(f"    ... and {len(info['staged']) - 10} more")

    if info["modified"]:
        print(f"\n  {Colors.YELLOW}Modified ({len(info['modified'])}):{Colors.RESET}")
        for f in info["modified"][:10]:
            print(f"    ~ {f}")
        if len(info["modified"]) > 10:
            print(f"    ... and {len(info['modified']) - 10} more")

    if info["untracked"]:
        print(f"\n  {Colors.RED}Untracked ({len(info['untracked'])}):{Colors.RESET}")
        for f in info["untracked"][:10]:
            print(f"    ? {f}")
        if len(info["untracked"]) > 10:
            print(f"    ... and {len(info['untracked']) - 10} more")

    if not info["staged"] and not info["modified"] and not info["untracked"]:
        print(f"\n  {Colors.GREEN}Working tree clean{Colors.RESET}")


def get_diff(cwd: Path | None = None, staged: bool = False) -> str:
    """Get git diff output."""
    args = ["diff", "--no-color"]
    if staged:
        args.append("--staged")

    success, stdout, stderr = run_git(args, cwd)
    if not success:
        return stderr or "No diff available"
    return stdout


def commit_changes(message: str, cwd: Path | None = None) -> bool:
    """Stage all changes and commit."""
    if not confirm(f"Stage all and commit with message: '{message}'?", default=False):
        print_info("Commit cancelled.")
        return False

    success, _, stderr = run_git(["add", "-A"], cwd)
    if not success:
        print_error(f"Git add failed: {stderr}")
        return False

    success, _, stderr = run_git(["commit", "-m", message], cwd)
    if not success:
        print_error(f"Git commit failed: {stderr}")
        return False

    print_success("Committed successfully!")
    return True


def get_log(n: int = 5, cwd: Path | None = None) -> str:
    """Get recent commit log."""
    success, stdout, _ = run_git(
        ["log", "--oneline", "--decorate", f"-{n}"], cwd
    )
    if not success:
        return "No commits available"
    return stdout


def git_context_for_llm(cwd: Path | None = None) -> str:
    """Generate a git context summary for the LLM prompt."""
    info = get_repo_info(cwd)
    if not info["is_repo"]:
        return ""

    parts = ["Git context:"]
    parts.append(f"Current branch: {info['branch']}")
    parts.append(f"Latest commit: {info['commit']}")

    if info["modified"]:
        parts.append(f"Modified files: {', '.join(m.split(' ', 1)[1] for m in info['modified'][:5])}")
    if info["untracked"]:
        parts.append(f"Untracked files: {', '.join(info['untracked'][:5])}")
    if info["staged"]:
        parts.append(f"Staged files: {', '.join(s.split(' ', 1)[1] for s in info['staged'][:5])}")

    # Add diff if there are changes
    if info["modified"] or info["untracked"] or info["staged"]:
        diff = get_diff(cwd, staged=False)
        if diff:
            # Truncate diff to avoid overwhelming context
            lines = diff.splitlines()
            if len(lines) > 100:
                diff = "\n".join(lines[:100]) + f"\n... ({len(lines) - 100} more lines)"
            parts.append(f"\nDiff:\n{diff}")

    return "\n".join(parts)
