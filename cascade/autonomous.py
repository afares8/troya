"""Autonomous agent mode for Cascade CLI — closest thing to Devin AI."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .editor import handle_edits_from_response
from .planner import create_plan
from .sandbox import run_sandboxed
from .self_heal import heal_code
from .ui import Colors, print_error, print_header, print_info, print_success, print_warning


class AutonomousAgent:
    """An agent that works autonomously on a task."""

    def __init__(self, client, context, executor) -> None:
        self.client = client
        self.context = context
        self.executor = executor
        self.plan: list[dict[str, Any]] = []
        self.current_step = 0
        self.results: list[dict[str, Any]] = []
        self.max_iterations = 10
        self.auto_commit = False
        self.auto_test = True

    def run(self, objective: str) -> dict[str, Any]:
        """Execute an objective autonomously."""
        print_header(f"🤖 Autonomous Agent: {objective}")
        print_info(f"Max iterations: {self.max_iterations}")
        print_info(f"Auto-test: {self.auto_test}")
        print()

        # Phase 1: Plan
        print(f"{Colors.CYAN}Phase 1: Planning...{Colors.RESET}")
        self.plan = create_plan(self.client, objective)
        if not self.plan or len(self.plan) == 1 and "step" in self.plan[0]:
            print_warning("Simple plan, treating as single step")
            self.plan = [{"step": 1, "description": objective, "action": "implement"}]

        print(f"Plan ({len(self.plan)} steps):")
        for i, step in enumerate(self.plan, 1):
            desc = step.get("description", step.get("action", "unknown"))
            print(f"  {i}. {desc}")
        print()

        # Phase 2: Execute
        print(f"{Colors.CYAN}Phase 2: Execution...{Colors.RESET}")
        for i, step in enumerate(self.plan[:self.max_iterations], 1):
            self.current_step = i
            print(f"\n{Colors.YELLOW}Step {i}/{min(len(self.plan), self.max_iterations)}:{Colors.RESET}")
            desc = step.get("description", step.get("action", "unknown"))
            print(f"  {desc}")

            result = self._execute_step(step)
            self.results.append(result)

            if result["success"]:
                print_success(f"  ✓ Step {i} complete")
            else:
                print_error(f"  ✗ Step {i} failed: {result.get('error', 'unknown error')}")
                # Try to heal if it's a code error
                if result.get("type") == "code_error":
                    print_info("  Attempting auto-heal...")
                    healed = self._try_heal(result)
                    if healed:
                        print_success("  ✓ Auto-heal successful")
                        result["healed"] = True
                    else:
                        print_error("  ✗ Auto-heal failed")

        # Phase 3: Verify
        if self.auto_test:
            print(f"\n{Colors.CYAN}Phase 3: Verification...{Colors.RESET}")
            self._run_tests()

        # Phase 4: Summary
        return self._generate_summary()

    def _execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute a single plan step."""
        desc = step.get("description", "").lower()
        action = step.get("action", "").lower()

        # Determine action type
        if any(kw in desc for kw in ["read", "look", "find", "search", "explore"]):
            return self._action_read(desc)
        elif any(kw in desc for kw in ["write", "create", "implement", "add", "build"]):
            return self._action_write(desc)
        elif any(kw in desc for kw in ["test", "run", "verify", "check", "execute"]):
            return self._action_test(desc)
        elif any(kw in desc for kw in ["fix", "debug", "repair", "heal"]):
            return self._action_fix(desc)
        elif any(kw in desc for kw in ["install", "setup", "configure"]):
            return self._action_shell(desc)
        else:
            # Default: ask LLM what to do
            return self._action_llm(desc)

    def _action_read(self, desc: str) -> dict[str, Any]:
        """Read and understand files."""
        # Find relevant files from context
        files = list(self.context.cwd.rglob("*.py"))
        files = [f for f in files if "__pycache__" not in str(f) and ".git" not in str(f)]
        files = files[:20]  # Limit

        # Ask LLM which files to read
        prompt = (
            f"Task: {desc}\n"
            f"Available files: {[str(f.relative_to(self.context.cwd)) for f in files[:10]]}\n"
            "Which files should I read to understand the codebase?"
            "Respond with just filenames, one per line."
        )
        response = self.client.chat([{"role": "user", "content": prompt}])

        read_files = []
        if response:
            for line in response.split("\n"):
                fname = line.strip().lstrip("- ")
                fpath = self.context.cwd / fname
                if fpath.exists() and fpath.is_file():
                    try:
                        self.context.read_file(fpath)
                        read_files.append(str(fpath))
                    except Exception:
                        pass

        return {"success": len(read_files) > 0, "type": "read", "files": read_files}

    def _action_write(self, desc: str) -> dict[str, Any]:
        """Write or modify code."""
        # Build context
        context_str = self.context.build_prompt()

        prompt = (
            f"You are an expert programmer. Task: {desc}\n\n"
            f"Current codebase context:\n{context_str}\n\n"
            "Generate the code changes needed. Use @filepath syntax to specify files."
            "Provide complete file contents or specific edits with context."
        )

        response = self.client.chat([
            {"role": "system", "content": "You are a code generator. Always specify file paths with @filepath syntax."},
            {"role": "user", "content": prompt}
        ])

        if not response:
            return {"success": False, "type": "write", "error": "No response from LLM"}

        # Apply edits
        edits = self._extract_edits(response)
        applied = 0
        for edit in edits:
            try:
                filepath = self.context.cwd / edit["file"]
                if edit["type"] == "replace":
                    content = filepath.read_text()
                    content = content.replace(edit["old"], edit["new"])
                    filepath.write_text(content)
                    applied += 1
                elif edit["type"] == "create":
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(edit["content"])
                    applied += 1
            except Exception as e:
                return {"success": False, "type": "write", "error": str(e)}

        return {"success": applied > 0, "type": "write", "edits": applied}

    def _action_test(self, desc: str) -> dict[str, Any]:
        """Run tests."""
        return self._run_tests()

    def _run_tests(self) -> dict[str, Any]:
        """Run available tests."""
        results = []

        # Try pytest
        try:
            r = subprocess.run(
                ["python3", "-m", "pytest", "-x", "-q"],
                capture_output=True, text=True, timeout=120, cwd=str(self.context.cwd)
            )
            results.append({"tool": "pytest", "returncode": r.returncode, "output": r.stdout + r.stderr})
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try unittest
        if not results or results[0]["returncode"] != 0:
            try:
                r = subprocess.run(
                    ["python3", "-m", "unittest", "discover", "-q"],
                    capture_output=True, text=True, timeout=120, cwd=str(self.context.cwd)
                )
                results.append({"tool": "unittest", "returncode": r.returncode, "output": r.stdout + r.stderr})
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Check if any passed
        passed = any(r["returncode"] == 0 for r in results)
        output = "\n".join(r["output"][:500] for r in results)

        return {
            "success": passed,
            "type": "test",
            "output": output,
            "error": "" if passed else "Tests failed"
        }

    def _action_fix(self, desc: str) -> dict[str, Any]:
        """Fix code errors."""
        # Try to find broken code
        for filepath in self.context.cwd.rglob("*.py"):
            if "__pycache__" in str(filepath):
                continue
            try:
                result = heal_code(filepath.read_text(), str(filepath))
                if result.get("fix"):
                    filepath.write_text(result["fix"])
                    return {"success": True, "type": "fix", "file": str(filepath)}
            except Exception:
                pass

        return {"success": False, "type": "fix", "error": "No fixable errors found"}

    def _action_shell(self, desc: str) -> dict[str, Any]:
        """Run shell commands."""
        # Ask LLM what command to run
        prompt = f"What shell command should I run to: {desc}? Respond with just the command, nothing else."
        response = self.client.chat([{"role": "user", "content": prompt}])

        if not response:
            return {"success": False, "type": "shell", "error": "No command suggested"}

        command = response.strip().strip("`")
        print_info(f"  Running: {command}")

        try:
            r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60, cwd=str(self.context.cwd))
            return {
                "success": r.returncode == 0,
                "type": "shell",
                "command": command,
                "output": r.stdout,
                "error": r.stderr if r.returncode != 0 else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "type": "shell", "error": "Timeout"}
        except Exception as e:
            return {"success": False, "type": "shell", "error": str(e)}

    def _action_llm(self, desc: str) -> dict[str, Any]:
        """Fallback: let LLM decide action."""
        context_str = self.context.build_prompt()
        prompt = f"Task: {desc}\n\nContext:\n{context_str}\n\nWhat should I do next? Be specific."
        response = self.client.chat([{"role": "user", "content": prompt}])

        if response:
            print_info(f"  LLM suggests: {response[:100]}...")
            return {"success": True, "type": "llm", "suggestion": response}

        return {"success": False, "type": "llm", "error": "No suggestion"}

    def _try_heal(self, result: dict[str, Any]) -> bool:
        """Attempt to auto-heal a failed step."""
        # Look at recent edits and try to fix
        for filepath in self.context.cwd.rglob("*.py"):
            if "__pycache__" in str(filepath):
                continue
            try:
                content = filepath.read_text()
                healed = heal_code(content, str(filepath))
                if healed.get("fix"):
                    filepath.write_text(healed["fix"])
                    return True
            except Exception:
                pass
        return False

    def _extract_edits(self, response: str) -> list[dict[str, Any]]:
        """Extract file edits from LLM response."""
        edits = []
        lines = response.split("\n")
        current_file = None
        in_code_block = False
        code_content = []

        for line in lines:
            # File path detection
            if line.startswith("@") or (line.startswith("```") and "." in line):
                if in_code_block and current_file and code_content:
                    edits.append({
                        "type": "create",
                        "file": current_file,
                        "content": "\n".join(code_content)
                    })
                    code_content = []
                current_file = line.lstrip("@`).").strip()
                in_code_block = False

            # Code block
            elif line.startswith("```"):
                if in_code_block and current_file and code_content:
                    edits.append({
                        "type": "create",
                        "file": current_file,
                        "content": "\n".join(code_content)
                    })
                    code_content = []
                in_code_block = not in_code_block
                if not in_code_block:
                    current_file = None

            elif in_code_block:
                code_content.append(line)

        return edits

    def _generate_summary(self) -> dict[str, Any]:
        """Generate final summary."""
        successful = sum(1 for r in self.results if r["success"])
        total = len(self.results)

        lines = []
        lines.append(f"\n{Colors.CYAN}{'─' * 50}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Autonomous Agent Summary{Colors.RESET}")
        lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
        lines.append(f"Steps completed: {successful}/{total}")
        lines.append(f"Success rate: {successful/total*100:.0f}%" if total > 0 else "N/A")

        if successful == total:
            lines.append(f"{Colors.GREEN}✓ All steps completed successfully{Colors.RESET}")
        elif successful > 0:
            lines.append(f"{Colors.YELLOW}⚠ Partial completion{Colors.RESET}")
        else:
            lines.append(f"{Colors.RED}✗ No steps completed{Colors.RESET}")

        print("\n".join(lines))

        return {
            "success": successful == total,
            "steps_total": total,
            "steps_successful": successful,
            "results": self.results,
        }
