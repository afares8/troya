"""GitHub integration for Cascade CLI — PRs, issues, branches."""

import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


def _run_gh(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    """Run GitHub CLI command."""
    try:
        r = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=30,
            cwd=str(cwd) if cwd else None
        )
        return {
            "success": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
        }
    except FileNotFoundError:
        return {"success": False, "error": "GitHub CLI (gh) not installed"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}


def create_branch(branch_name: str, cwd: Path) -> dict[str, Any]:
    """Create a new git branch."""
    result = _run_gh(["repo", "view", "--json", "url"], cwd)
    if not result["success"]:
        return {"success": False, "error": "Not in a GitHub repo"}

    # Create branch locally
    try:
        r = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True, text=True, timeout=10, cwd=str(cwd)
        )
        if r.returncode == 0:
            return {"success": True, "branch": branch_name}
        return {"success": False, "error": r.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_pr(title: str, body: str = "", branch: str | None = None, cwd: Path | None = None) -> dict[str, Any]:
    """Create a pull request."""
    if not cwd:
        cwd = Path.cwd()

    args = ["pr", "create", "--title", title]
    if body:
        args.extend(["--body", body])
    if branch:
        args.extend(["--head", branch])

    result = _run_gh(args, cwd)
    if result["success"]:
        return {"success": True, "url": result["stdout"].strip()}
    return result


def list_prs(cwd: Path | None = None, state: str = "open") -> list[dict[str, Any]]:
    """List pull requests."""
    result = _run_gh(["pr", "list", "--state", state, "--json", "number,title,author,url"], cwd)
    if result["success"]:
        try:
            import json
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            pass
    return []


def review_pr(pr_number: int, comment: str, cwd: Path | None = None) -> dict[str, Any]:
    """Review a PR with a comment."""
    result = _run_gh(["pr", "review", str(pr_number), "--comment", "-b", comment], cwd)
    return result


def create_issue(title: str, body: str = "", labels: list[str] | None = None, cwd: Path | None = None) -> dict[str, Any]:
    """Create a GitHub issue."""
    args = ["issue", "create", "--title", title]
    if body:
        args.extend(["--body", body])
    if labels:
        for label in labels:
            args.extend(["--label", label])

    result = _run_gh(args, cwd)
    if result["success"]:
        return {"success": True, "url": result["stdout"].strip()}
    return result


def get_repo_info(cwd: Path | None = None) -> dict[str, Any]:
    """Get repository information."""
    result = _run_gh(["repo", "view", "--json", "name,owner,url,defaultBranch"], cwd)
    if result["success"]:
        try:
            import json
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            pass
    return {}


def is_gh_available() -> bool:
    """Check if GitHub CLI is installed and authenticated."""
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def format_pr_list(prs: list[dict[str, Any]]) -> str:
    if not prs:
        return f"{Colors.YELLOW}No pull requests found{Colors.RESET}"

    lines = [f"{Colors.CYAN}Pull Requests:{Colors.RESET}"]
    for pr in prs[:10]:
        author = pr.get("author", {}).get("login", "unknown")
        lines.append(f"  #{pr['number']} {pr['title']} by {author}")
        lines.append(f"    {Colors.DIM}{pr['url']}{Colors.RESET}")
    return "\n".join(lines)
