"""Smart project detection — auto-detect project type and load relevant context."""

from pathlib import Path
from typing import Any

from .ui import Colors, print_info

PROJECT_TYPES = {
    "python": {
        "indicators": ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"],
        "context_files": ["README.md", "pyproject.toml", "requirements.txt"],
        "system_hint": "This is a Python project.",
    },
    "node": {
        "indicators": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
        "context_files": ["package.json", "README.md", "tsconfig.json"],
        "system_hint": "This is a Node.js/JavaScript project.",
    },
    "rust": {
        "indicators": ["Cargo.toml", "Cargo.lock"],
        "context_files": ["Cargo.toml", "README.md"],
        "system_hint": "This is a Rust project.",
    },
    "go": {
        "indicators": ["go.mod", "go.sum"],
        "context_files": ["go.mod", "README.md"],
        "system_hint": "This is a Go project.",
    },
    "react": {
        "indicators": ["src/App.jsx", "src/App.tsx", "src/App.js", "public/index.html"],
        "context_files": ["package.json", "src/App.jsx", "src/App.tsx"],
        "system_hint": "This is a React project.",
    },
    "django": {
        "indicators": ["manage.py", "settings.py"],
        "context_files": ["requirements.txt", "manage.py"],
        "system_hint": "This is a Django project.",
    },
    "flask": {
        "indicators": ["app.py", "wsgi.py"],
        "context_files": ["requirements.txt", "app.py"],
        "system_hint": "This is a Flask project.",
    },
    "docker": {
        "indicators": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
        "context_files": ["Dockerfile", "docker-compose.yml", "README.md"],
        "system_hint": "This project uses Docker.",
    },
}


def detect_project(root: Path) -> tuple[str, dict[str, Any]]:
    """Detect project type and return relevant metadata."""
    for ptype, meta in PROJECT_TYPES.items():
        for indicator in meta["indicators"]:
            if (root / indicator).exists():
                return ptype, meta
    return "generic", {"context_files": ["README.md"], "system_hint": ""}


def get_project_hint(root: Path) -> str:
    """Get a short hint about the detected project type."""
    ptype, meta = detect_project(root)
    hint = meta.get("system_hint", "")
    if hint:
        return f"{hint} Detected project type: {ptype}."
    return ""


def auto_context_files(root: Path, max_files: int = 5) -> dict[str, str]:
    """Automatically read relevant context files based on project type."""
    ptype, meta = detect_project(root)
    context = {}
    for fname in meta.get("context_files", []):
        path = root / fname
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                context[str(path.relative_to(root))] = content
            except (UnicodeDecodeError, OSError):
                continue
        if len(context) >= max_files:
            break
    return context
