"""Context and conversation management."""

import os
from pathlib import Path
from typing import Any

from .git_utils import git_context_for_llm, is_git_repo, print_repo_status
from .search import build_tree, get_project_stats, grep_project, print_grep_results
from .ui import Colors, print_error, print_info, print_success


class ContextManager:
    """Manages conversation history and file context."""

    def __init__(self, system_prompt: str, max_files: int = 20):
        self.system_prompt = system_prompt
        self.max_files = max_files
        self.messages: list[dict[str, str]] = []
        self.files: dict[str, str] = {}
        self.cwd = Path.cwd()

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append({"role": role, "content": content})
        # Keep last 50 messages to manage context window
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]

    def read_file(self, path: str) -> bool:
        """Read a file and add it to context."""
        file_path = self.cwd / path
        try:
            file_path = file_path.resolve()
            if not file_path.exists():
                print_error(f"File not found: {path}")
                return False
            if not file_path.is_file():
                print_error(f"Not a file: {path}")
                return False

            # Check file size (max 500KB)
            size = file_path.stat().st_size
            if size > 500_000:
                print_error(f"File too large ({size / 1024:.0f} KB). Max: 500KB")
                return False

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            relative = str(file_path.relative_to(Path.cwd())) if file_path.is_relative_to(Path.cwd()) else str(file_path)
            self.files[relative] = content
            print_success(f"Read {relative} ({len(content)} chars, {size} bytes)")
            return True
        except PermissionError:
            print_error(f"Permission denied: {path}")
            return False
        except Exception as e:
            print_error(f"Error reading {path}: {e}")
            return False

    def list_directory(self, path: str = ".") -> str:
        """List directory contents."""
        dir_path = self.cwd / path
        try:
            entries = []
            for entry in sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
                prefix = "📁" if entry.is_dir() else "📄"
                size = ""
                if entry.is_file():
                    size = f"  ({entry.stat().st_size:,} bytes)"
                entries.append(f"{prefix} {entry.name}{size}")
            return "\n".join(entries) if entries else "(empty directory)"
        except Exception as e:
            return f"Error: {e}"

    def change_directory(self, path: str) -> bool:
        """Change working directory."""
        try:
            new_path = (self.cwd / path).resolve()
            if not new_path.exists():
                print_error(f"Directory not found: {path}")
                return False
            if not new_path.is_dir():
                print_error(f"Not a directory: {path}")
                return False
            os.chdir(new_path)
            self.cwd = new_path
            print_info(f"Changed to: {new_path}")
            return True
        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def clear(self) -> None:
        """Clear conversation and file context."""
        self.messages = []
        self.files = {}
        print_info("Context cleared.")

    def build_prompt(self, user_input: str) -> str:
        """Build the full prompt with context."""
        parts = []

        # Add git context
        git_ctx = git_context_for_llm(self.cwd)
        if git_ctx:
            parts.append(git_ctx)

        # Add file context
        if self.files:
            parts.append("Files in context:")
            for path, content in list(self.files.items())[: self.max_files]:
                parts.append(f"\n--- {path} ---\n{content}\n---")

        # Add user input
        parts.append(user_input)
        return "\n\n".join(parts)

    def get_messages(self, user_input: str) -> list[dict[str, str]]:
        """Get messages formatted for LLM API."""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.messages)

        # Build content with file context
        content = self.build_prompt(user_input)
        messages.append({"role": "user", "content": content})
        return messages

    def show_tree(self, path: str = ".", max_depth: int = 3) -> None:
        """Show directory tree."""
        tree = build_tree(path, max_depth=max_depth)
        print(tree)

    def grep(self, pattern: str, file_pattern: str = "*") -> None:
        """Search for pattern in project files."""
        results = grep_project(pattern, root=self.cwd, file_pattern=file_pattern)
        print_grep_results(results, pattern)

    def show_stats(self) -> None:
        """Show project statistics."""
        stats = get_project_stats(self.cwd)
        print(f"{Colors.CYAN}Project Stats:{Colors.RESET}")
        print(f"  Files: {stats['total_files']}")
        print(f"  Directories: {stats['total_dirs']}")
        print(f"  Total size: {stats['total_size']:,} bytes")
        if stats["languages"]:
            print(f"  Languages (by extension):")
            for ext, count in sorted(stats["languages"].items(), key=lambda x: -x[1])[:10]:
                print(f"    {ext}: {count}")

    def show_context(self) -> None:
        """Display current context info."""
        print(f"{Colors.CYAN}Working directory:{Colors.RESET} {self.cwd}")
        print(f"{Colors.CYAN}Messages in history:{Colors.RESET} {len(self.messages)}")
        print(f"{Colors.CYAN}Files in context:{Colors.RESET} {len(self.files)}")
        if self.files:
            for path in self.files:
                print(f"  {Colors.YELLOW}{path}{Colors.RESET}")
        if is_git_repo(self.cwd):
            print()
            print_repo_status(self.cwd)
