"""Task runner for Cascade CLI — run make, npm, poetry, etc."""

import json
import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


def detect_task_runners(root: Path) -> dict[str, Any]:
    """Detect available task runners in project."""
    runners = {}

    # Makefile
    if (root / "Makefile").exists():
        runners["make"] = _parse_makefile(root / "Makefile")

    # npm
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if scripts:
                runners["npm"] = list(scripts.keys())
        except (json.JSONDecodeError, OSError):
            pass

    # Poetry
    if (root / "pyproject.toml").exists():
        runners["poetry"] = ["install", "build", "publish", "run"]

    # Justfile
    if (root / "justfile").exists() or (root / "Justfile").exists():
        runners["just"] = _parse_justfile(root / "justfile" if (root / "justfile").exists() else root / "Justfile")

    # Cargo
    if (root / "Cargo.toml").exists():
        runners["cargo"] = ["build", "test", "run", "check", "fmt", "clippy"]

    # pytest
    runners["pytest"] = ["test"]

    return runners


def _parse_makefile(path: Path) -> list[str]:
    """Parse Makefile for targets."""
    targets = []
    try:
        for line in path.read_text().split("\n"):
            if ":" in line and not line.startswith("\t") and not line.startswith("#"):
                target = line.split(":")[0].strip()
                if target and not target.startswith("."):
                    targets.append(target)
    except OSError:
        pass
    return targets


def _parse_justfile(path: Path) -> list[str]:
    """Parse justfile for recipes."""
    recipes = []
    try:
        for line in path.read_text().split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not line.startswith(" ") and not line.startswith("\t"):
                if ":" not in stripped:
                    recipes.append(stripped.split()[0])
    except OSError:
        pass
    return recipes


def run_task(runner: str, task: str, cwd: Path) -> dict[str, Any]:
    """Run a task using detected runner."""
    result = {"success": False, "output": "", "error": ""}

    commands = {
        "make": ["make", task],
        "npm": ["npm", "run", task],
        "poetry": ["poetry", "run", task] if task in {"run"} else ["poetry", task],
        "just": ["just", task],
        "cargo": ["cargo", task],
        "pytest": ["pytest"] if task == "test" else ["pytest", task],
    }

    cmd = commands.get(runner)
    if not cmd:
        result["error"] = f"Unknown runner: {runner}"
        return result

    try:
        print_info(f"Running: {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(cwd))
        result["success"] = r.returncode == 0
        result["output"] = r.stdout
        result["error"] = r.stderr
    except subprocess.TimeoutExpired:
        result["error"] = "Timed out after 5 minutes"
    except FileNotFoundError:
        result["error"] = f"'{runner}' not installed"
    except Exception as e:
        result["error"] = str(e)

    return result


def format_runners(runners: dict[str, Any]) -> str:
    """Format detected runners for display."""
    if not runners:
        return f"{Colors.YELLOW}No task runners detected{Colors.RESET}"

    lines = [f"{Colors.CYAN}Task Runners:{Colors.RESET}"]
    for runner, tasks in runners.items():
        lines.append(f"  {Colors.YELLOW}{runner}{Colors.RESET}")
        for task in tasks[:10]:
            lines.append(f"    - {task}")
        if len(tasks) > 10:
            lines.append(f"    ... and {len(tasks) - 10} more")
    return "\n".join(lines)


def format_result(result: dict[str, Any]) -> str:
    """Format task execution result."""
    if result["success"]:
        output = result["output"].strip()
        if output:
            return f"{Colors.GREEN}✓ Success{Colors.RESET}\n{output[:500]}"
        return f"{Colors.GREEN}✓ Success{Colors.RESET}"
    else:
        err = result["error"].strip() or result["output"].strip()
        return f"{Colors.RED}✗ Failed{Colors.RESET}\n{err[:500]}"
