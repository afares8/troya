"""Safe command execution with user approval."""

import shlex
import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, confirm, print_command, print_error, print_info, print_success

# Commands that are always safe to run without confirmation
SAFE_COMMANDS = {
    "ls", "pwd", "echo", "cat", "head", "tail", "less", "more",
    "git status", "git log", "git branch", "git diff", "git show",
    "git remote", "git config", "npm list", "pip list", "pip freeze",
    "python --version", "node --version", "go version", "rustc --version",
    "which", "whereis", "file", "stat", "du", "df", "uname", "whoami",
    "date", "uptime", "env", "printenv", "id", "groups",
}

# Commands that are potentially destructive and always need confirmation
DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r", "rm -f",
    "mkfs", "dd if=", "fdisk",
    "> /dev/sda", "> /dev/disk",
    "chmod -R", "chown -R",
    "curl .*\\|.*sh", "wget .*\\|.*sh",
    "sudo",
]


class CommandExecutor:
    """Executes shell commands with safety checks."""

    def __init__(self, auto_confirm: bool = False):
        self.auto_confirm = auto_confirm
        self.history: list[dict[str, Any]] = []

    def is_safe(self, command: str) -> bool:
        """Check if a command is in the safe list."""
        cmd_lower = command.strip().lower()
        for safe in SAFE_COMMANDS:
            if cmd_lower.startswith(safe.lower()):
                return True
        return False

    def is_dangerous(self, command: str) -> bool:
        """Check if a command matches dangerous patterns."""
        cmd_lower = command.strip().lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in cmd_lower:
                return True
        return False

    def execute(self, command: str, cwd: Path | None = None) -> dict[str, Any]:
        """Execute a command with user approval."""
        command = command.strip()
        if not command:
            return {"success": False, "output": "", "error": "Empty command"}

        result = {
            "command": command,
            "success": False,
            "output": "",
            "error": "",
            "approved": False,
        }

        # Check if dangerous
        if self.is_dangerous(command):
            print_error("This command is potentially dangerous and requires explicit approval.")
            if not confirm(f"Run: {command}", default=False):
                print_info("Cancelled.")
                return result
            result["approved"] = True

        # Check if safe or needs confirmation
        elif not self.is_safe(command) and not self.auto_confirm:
            if not confirm(f"Run: {command}", default=False):
                print_info("Cancelled.")
                return result
            result["approved"] = True
        else:
            result["approved"] = True

        # Execute
        print_command(command)
        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=cwd or Path.cwd(),
                capture_output=True,
                text=True,
                timeout=300,
            )
            result["success"] = process.returncode == 0
            result["output"] = process.stdout
            result["error"] = process.stderr

            if result["success"]:
                if process.stdout:
                    print(process.stdout)
                print_success(f"Exit code: {process.returncode}")
            else:
                if process.stderr:
                    print_error(process.stderr)
                print_error(f"Exit code: {process.returncode}")

        except subprocess.TimeoutExpired:
            result["error"] = "Command timed out after 300 seconds"
            print_error(result["error"])
        except Exception as e:
            result["error"] = str(e)
            print_error(f"Execution failed: {e}")

        self.history.append(result)
        return result

    def parse_command_from_response(self, text: str) -> str | None:
        """Extract bash command from AI response markdown."""
        import re

        # Look for ```bash or ```sh blocks
        patterns = [
            r"```(?:bash|sh|shell|zsh)\n(.*?)\n```",
            r"```\n\$ (.*?)\n```",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Look for inline `$ command`
        inline = re.search(r"(?m)^\$\s+(.+)$", text)
        if inline:
            return inline.group(1).strip()

        return None
