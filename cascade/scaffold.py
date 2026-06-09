"""Project scaffolding — generate project templates from descriptions."""

import json
import re
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success

TEMPLATES: dict[str, dict[str, Any]] = {
    "react": {
        "dirs": ["src/components", "src/hooks", "src/pages", "public"],
        "files": {
            "package.json": json.dumps({
                "name": "{{name}}", "version": "1.0.0", "private": True,
                "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
                "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-react": "^4.0.0"},
                "scripts": {"dev": "vite", "build": "vite build"}
            }, indent=2),
            "index.html": "<!DOCTYPE html>\n<html>\n<head><title>{{name}}</title></head>\n<body><div id=\"root\"></div><script type=\"module\" src=\"/src/main.jsx\"></script></body>\n</html>",
            "vite.config.js": "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({ plugins: [react()] });",
            "src/main.jsx": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nReactDOM.createRoot(document.getElementById('root')).render(<App />);",
            "src/App.jsx": "export default function App() {\n  return <div><h1>{{name}}</h1></div>;\n}",
        },
    },
    "fastapi": {
        "dirs": ["app/routers", "app/models", "tests"],
        "files": {
            "requirements.txt": "fastapi>=0.110.0\nuvicorn[standard]>=0.29.0\npydantic>=2.0.0\nhttpx>=0.27.0\n",
            "main.py": "from fastapi import FastAPI\nfrom app.routers import api\n\napp = FastAPI(title=\"{{name}}\")\napp.include_router(api.router, prefix=\"/api\")\n\n@app.get(\"/\")\ndef root():\n    return {\"message\": \"Welcome to {{name}}\"}\n",
            "app/__init__.py": "",
            "app/routers/__init__.py": "",
            "app/routers/api.py": "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get(\"/items\")\ndef list_items():\n    return [{\"id\": 1, \"name\": \"item\"}]\n",
            "tests/__init__.py": "",
            "tests/test_api.py": "from fastapi.testclient import TestClient\nfrom main import app\n\nclient = TestClient(app)\n\ndef test_root():\n    resp = client.get(\"/\")\n    assert resp.status_code == 200\n",
        },
    },
    "python-cli": {
        "dirs": ["src/{{name}}", "tests"],
        "files": {
            "pyproject.toml": "[build-system]\nrequires = [\"setuptools>=61\", \"wheel\"]\nbuild-backend = \"setuptools.build_meta\"\n\n[project]\nname = \"{{name}}\"\nversion = \"0.1.0\"\ndependencies = []\n\n[project.scripts]\n{{name}} = \"{{name}}.cli:main\"\n",
            "src/{{name}}/__init__.py": "__version__ = \"0.1.0\"\n",
            "src/{{name}}/cli.py": "import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument(\"--version\", action=\"store_true\")\n    args = parser.parse_args()\n    if args.version:\n        print(\"0.1.0\")\n\nif __name__ == \"__main__\":\n    main()\n",
            "tests/__init__.py": "",
            "tests/test_cli.py": "from {{name}}.cli import main\n\ndef test_main():\n    assert main is not None\n",
        },
    },
    "flask": {
        "dirs": ["app/templates", "app/static", "tests"],
        "files": {
            "requirements.txt": "flask>=3.0.0\ngunicorn>=21.0.0\n",
            "app.py": "from flask import Flask, render_template\n\napp = Flask(__name__)\n\n@app.route(\"/\")\ndef home():\n    return render_template(\"index.html\")\n\nif __name__ == \"__main__\":\n    app.run(debug=True)\n",
            "app/templates/index.html": "<!DOCTYPE html>\n<html><head><title>{{name}}</title></head>\n<body><h1>{{name}}</h1></body></html>",
            "tests/__init__.py": "",
            "tests/test_app.py": "from app import app\n\ndef test_home():\n    with app.test_client() as c:\n        resp = c.get(\"/\")\n        assert resp.status_code == 200\n",
        },
    },
}


def scaffold_project(template_name: str, project_name: str, target_dir: Path) -> int:
    """Generate a project from a template."""
    if template_name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        print_error(f"Unknown template '{template_name}'. Available: {available}")
        return 0

    template = TEMPLATES[template_name]
    root = target_dir / project_name
    count = 0

    for d in template.get("dirs", []):
        path = root / d.replace("{{name}}", project_name)
        path.mkdir(parents=True, exist_ok=True)

    for rel_path, content in template.get("files", {}).items():
        path = root / rel_path.replace("{{name}}", project_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.replace("{{name}}", project_name), encoding="utf-8")
        count += 1

    print_success(f"Scaffolded '{project_name}' from '{template_name}' template ({count} files)")
    print_info(f"Location: {root}")
    return count


def list_templates() -> list[str]:
    return list(TEMPLATES.keys())


def scaffold_from_ai(client, description: str, target_dir: Path) -> int:
    """Ask the AI to design a custom scaffold based on description."""
    print_info("Asking AI to design project structure...")
    messages = [
        {"role": "system", "content": (
            "You are a project scaffolding assistant. Given a description, output a JSON "
            "object with 'dirs' (list of directories) and 'files' (dict of path->content). "
            "Generate complete, runnable code. Respond with ONLY the JSON."
        )},
        {"role": "user", "content": f"Create a project scaffold for: {description}"},
    ]
    response = client.chat(messages)
    if not response:
        print_error("No response from LLM")
        return 0

    # Extract JSON block
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if not match:
        print_error("Could not parse scaffold JSON from response")
        return 0

    try:
        scaffold = json.loads(match.group())
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
        return 0

    # Generate project
    project_name = "generated_project"
    root = target_dir / project_name
    count = 0
    for d in scaffold.get("dirs", []):
        (root / d).mkdir(parents=True, exist_ok=True)
    for rel_path, content in scaffold.get("files", {}).items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        count += 1

    print_success(f"AI-generated scaffold: {count} files in {root}")
    return count
