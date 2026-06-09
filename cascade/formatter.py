"""Auto-formatter integration for Cascade CLI — black, ruff, prettier."""

import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success, print_warning


def check_tool(name: str) -> bool:
    """Check if a formatting tool is installed."""
    try:
        subprocess.run([name, "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def format_python_file(filepath: Path) -> dict[str, Any]:
    """Format a Python file using available tools."""
    result = {"formatted": False, "tool": None, "output": "", "error": ""}

    # Try ruff first (fastest)
    if check_tool("ruff"):
        try:
            r = subprocess.run(
                ["ruff", "format", str(filepath)],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                result["formatted"] = True
                result["tool"] = "ruff"
                result["output"] = r.stdout
                return result
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Try black
    if check_tool("black"):
        try:
            r = subprocess.run(
                ["black", "--quiet", str(filepath)],
                capture_output=True, text=True, timeout=60
            )
            if r.returncode == 0:
                result["formatted"] = True
                result["tool"] = "black"
                result["output"] = r.stdout
                return result
        except (subprocess.TimeoutExpired, OSError):
            pass

    result["error"] = "No Python formatter found. Install: pip install ruff black"
    return result


def format_js_file(filepath: Path) -> dict[str, Any]:
    """Format a JS/TS file using prettier."""
    result = {"formatted": False, "tool": None, "output": "", "error": ""}

    if check_tool("prettier"):
        try:
            r = subprocess.run(
                ["prettier", "--write", str(filepath)],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                result["formatted"] = True
                result["tool"] = "prettier"
                return result
        except (subprocess.TimeoutExpired, OSError):
            pass

    result["error"] = "prettier not found. Install: npm install -g prettier"
    return result


def format_file(filepath: Path) -> dict[str, Any]:
    """Auto-detect file type and format."""
    suffix = filepath.suffix.lower()
    if suffix in {".py"}:
        return format_python_file(filepath)
    elif suffix in {".js", ".ts", ".jsx", ".tsx", ".json", ".md", ".yaml", ".yml", ".css", ".html"}:
        return format_js_file(filepath)
    else:
        return {"formatted": False, "error": f"No formatter available for {suffix} files"}


def lint_python_file(filepath: Path) -> dict[str, Any]:
    """Lint a Python file using ruff or flake8."""
    result = {"issues": [], "tool": None}

    if check_tool("ruff"):
        try:
            r = subprocess.run(
                ["ruff", "check", str(filepath)],
                capture_output=True, text=True, timeout=30
            )
            result["tool"] = "ruff"
            if r.stdout:
                for line in r.stdout.strip().split("\n"):
                    if line.strip():
                        result["issues"].append(line)
            return result
        except (subprocess.TimeoutExpired, OSError):
            pass

    if check_tool("flake8"):
        try:
            r = subprocess.run(
                ["flake8", str(filepath)],
                capture_output=True, text=True, timeout=30
            )
            result["tool"] = "flake8"
            if r.stdout:
                for line in r.stdout.strip().split("\n"):
                    if line.strip():
                        result["issues"].append(line)
            return result
        except (subprocess.TimeoutExpired, OSError):
            pass

    return result


def format_result(result: dict[str, Any]) -> str:
    """Format formatter output for display."""
    if result.get("formatted"):
        return f"{Colors.GREEN}✓ Formatted with {result['tool']}{Colors.RESET}"
    if result.get("issues"):
        lines = [f"{Colors.YELLOW}Lint issues ({result['tool']}):{Colors.RESET}"]
        for issue in result["issues"][:10]:
            lines.append(f"  {issue}")
        return "\n".join(lines)
    if result.get("error"):
        return f"{Colors.RED}✗ {result['error']}{Colors.RESET}"
    return f"{Colors.GREEN}✓ Already formatted{Colors.RESET}"
