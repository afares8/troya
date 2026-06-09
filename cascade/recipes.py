"""Recipe system for Cascade CLI — declarative workflow automation."""

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .ui import Colors, print_error, print_info, print_success, print_warning

RECIPES_DIR = Path.home() / ".config" / "cascade-cli" / "recipes"


class RecipeRunner:
    """Execute declarative recipes for common workflows."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd
        self.env: dict[str, str] = {}
        self.results: list[dict[str, Any]] = []

    def _resolve(self, value: str) -> str:
        """Resolve template variables in strings."""
        for key, val in self.env.items():
            value = value.replace(f"{{{{{key}}}}}", str(val))
        return value

    def _run_step(self, step: dict[str, Any], step_num: int) -> dict[str, Any]:
        """Execute a single recipe step."""
        step_type = step.get("type", "shell")
        name = step.get("name", f"step_{step_num}")
        result = {"name": name, "success": False, "output": "", "error": ""}

        if step_type == "shell":
            cmd = self._resolve(step["cmd"])
            try:
                r = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=step.get("timeout", 300), cwd=str(self.cwd)
                )
                result["success"] = r.returncode == 0
                result["output"] = r.stdout
                result["error"] = r.stderr
                if result["success"]:
                    print_success(f"  ✓ {name}")
                else:
                    print_error(f"  ✗ {name} (exit: {r.returncode})")
            except subprocess.TimeoutExpired:
                result["error"] = "Timed out"
                print_error(f"  ✗ {name} (timeout)")
            except Exception as e:
                result["error"] = str(e)
                print_error(f"  ✗ {name}: {e}")

        elif step_type == "prompt":
            question = self._resolve(step.get("question", "Continue?"))
            default = step.get("default", "")
            try:
                response = input(f"  {question} [{default}]: ").strip() or default
            except (EOFError, OSError):
                response = default
                print_info(f"  Using default: {default}")
            self.env[step.get("var", "response")] = response
            result["success"] = True
            result["output"] = response
            print_success(f"  ✓ {name}: {response}")

        elif step_type == "file":
            path = self.cwd / self._resolve(step["path"])
            content = self._resolve(step.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            result["success"] = True
            result["output"] = f"Wrote {len(content)} chars to {path}"
            print_success(f"  ✓ {name}: {path.name}")

        elif step_type == "append":
            path = self.cwd / self._resolve(step["path"])
            content = self._resolve(step.get("content", ""))
            with open(path, "a") as f:
                f.write(content)
            result["success"] = True
            result["output"] = f"Appended to {path}"
            print_success(f"  ✓ {name}")

        elif step_type == "mkdir":
            path = self.cwd / self._resolve(step["path"])
            path.mkdir(parents=True, exist_ok=True)
            result["success"] = True
            result["output"] = f"Created {path}"
            print_success(f"  ✓ {name}")

        elif step_type == "copy":
            src = self.cwd / self._resolve(step["src"])
            dst = self.cwd / self._resolve(step["dst"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text())
            result["success"] = True
            print_success(f"  ✓ {name}: {src.name} → {dst.name}")

        elif step_type == "set":
            self.env[step["var"]] = self._resolve(step["value"])
            result["success"] = True
            print_success(f"  ✓ {name}: {step['var']} = {step['value']}")

        elif step_type == "if":
            condition = self._resolve(step.get("condition", ""))
            # Simple condition evaluation
            if self.env.get(condition, ""):
                for sub_step in step.get("then", []):
                    sub_result = self._run_step(sub_step, step_num)
                    self.results.append(sub_result)
                result["success"] = True
            else:
                for sub_step in step.get("else", []):
                    sub_result = self._run_step(sub_step, step_num)
                    self.results.append(sub_result)
                result["success"] = True
            print_success(f"  ✓ {name}")

        return result

    def run(self, recipe: dict[str, Any]) -> dict[str, Any]:
        """Execute a complete recipe."""
        print_info(f"Running recipe: {recipe.get('name', 'unnamed')}")
        print_info(f"Description: {recipe.get('description', '')}")
        print()

        # Set initial env vars
        for key, val in recipe.get("env", {}).items():
            self.env[key] = str(val)

        steps = recipe.get("steps", [])
        for i, step in enumerate(steps, 1):
            result = self._run_step(step, i)
            self.results.append(result)

        success = all(r["success"] for r in self.results)
        return {
            "success": success,
            "steps_run": len(self.results),
            "results": self.results,
        }


def list_recipes() -> list[tuple[str, str]]:
    """List available recipes."""
    recipes = []
    RECIPES_DIR.mkdir(parents=True, exist_ok=True)

    # Built-in recipes
    recipes.append(("setup-python", "Initialize Python project (venv, git, .gitignore)"))
    recipes.append(("setup-node", "Initialize Node.js project (package.json, git)"))
    recipes.append(("deploy-static", "Deploy static site to GitHub Pages"))
    recipes.append(("release-python", "Release Python package (bump, build, upload)"))

    # User recipes
    for f in RECIPES_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text())
            recipes.append((f.stem, data.get("description", "No description")))
        except Exception:
            pass

    return recipes


def get_recipe(name: str) -> dict[str, Any] | None:
    """Load a recipe by name."""
    # Built-in recipes
    builtins = {
        "setup-python": {
            "name": "setup-python",
            "description": "Initialize Python project with venv, git, and .gitignore",
            "env": {"project_name": "my_project"},
            "steps": [
                {"type": "prompt", "name": "project_name", "question": "Project name", "var": "project_name"},
                {"type": "shell", "name": "create_venv", "cmd": "python3 -m venv venv"},
                {"type": "shell", "name": "init_git", "cmd": "git init"},
                {"type": "file", "name": "gitignore", "path": ".gitignore", "content": "__pycache__/\n*.pyc\n.venv/\nvenv/\ndist/\nbuild/\n*.egg-info/\n.env\n"},
                {"type": "file", "name": "main_py", "path": "{{project_name}}/__init__.py", "content": """\"\"\"{{project_name}} package.\"\"\"\n__version__ = \"0.1.0\"\n"""},
                {"type": "file", "name": "setup_py", "path": "setup.py", "content": """from setuptools import setup\n\nsetup(\n    name=\"{{project_name}}\",\n    version=\"0.1.0\",\n    packages=[\"{{project_name}}\"],\n)\n"""},
                {"type": "shell", "name": "first_commit", "cmd": "git add . && git commit -m 'Initial commit'"},
            ],
        },
        "setup-node": {
            "name": "setup-node",
            "description": "Initialize Node.js project",
            "env": {"project_name": "my-app"},
            "steps": [
                {"type": "prompt", "name": "project_name", "question": "Project name", "var": "project_name"},
                {"type": "shell", "name": "init_npm", "cmd": "npm init -y"},
                {"type": "shell", "name": "init_git", "cmd": "git init"},
                {"type": "file", "name": "gitignore", "path": ".gitignore", "content": "node_modules/\ndist/\n.env\n"},
                {"type": "shell", "name": "first_commit", "cmd": "git add . && git commit -m 'Initial commit'"},
            ],
        },
        "deploy-static": {
            "name": "deploy-static",
            "description": "Deploy static site to GitHub Pages",
            "steps": [
                {"type": "shell", "name": "build", "cmd": "npm run build || echo 'No build step'"},
                {"type": "shell", "name": "deploy", "cmd": "npx gh-pages -d dist || echo 'Install gh-pages: npm i -D gh-pages'"},
            ],
        },
        "release-python": {
            "name": "release-python",
            "description": "Release Python package to PyPI",
            "steps": [
                {"type": "shell", "name": "clean", "cmd": "rm -rf dist/ build/ *.egg-info/"},
                {"type": "shell", "name": "build", "cmd": "python3 -m build"},
                {"type": "shell", "name": "upload", "cmd": "python3 -m twine upload dist/*"},
            ],
        },
    }

    if name in builtins:
        return builtins[name]

    # Try user recipe
    recipe_file = RECIPES_DIR / f"{name}.yaml"
    if recipe_file.exists():
        try:
            return yaml.safe_load(recipe_file.read_text())
        except Exception:
            return None

    return None
