"""Code quality analyzer for Cascade CLI self-improvement."""

import ast
import sys
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success, print_warning


def analyze_file(filepath: Path) -> dict[str, Any]:
    """Analyze a Python file for quality issues."""
    issues = []
    metrics = {"lines": 0, "functions": 0, "classes": 0, "imports": 0}

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {"issues": [{"level": "error", "message": f"Cannot read: {e}"}], "metrics": metrics}

    lines = source.split("\n")
    metrics["lines"] = len(lines)

    # Check for long lines
    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append({
                "level": "warning",
                "line": i,
                "message": f"Line too long ({len(line)} chars)",
                "type": "style",
            })

    # Parse AST
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        issues.append({
            "level": "error",
            "line": e.lineno or 0,
            "message": f"Syntax error: {e.msg}",
            "type": "syntax",
        })
        return {"issues": issues, "metrics": metrics}

    # AST analysis
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            metrics["functions"] += 1
            # Check function complexity (simple heuristic: number of statements)
            stmt_count = len([n for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try))])
            if stmt_count > 15:
                issues.append({
                    "level": "warning",
                    "line": node.lineno,
                    "message": f"Function '{node.name}' may be too complex ({stmt_count} branches)",
                    "type": "complexity",
                })
            # Check missing docstring
            if not ast.get_docstring(node):
                issues.append({
                    "level": "info",
                    "line": node.lineno,
                    "message": f"Function '{node.name}' missing docstring",
                    "type": "documentation",
                })

        elif isinstance(node, ast.ClassDef):
            metrics["classes"] += 1
            if not ast.get_docstring(node):
                issues.append({
                    "level": "info",
                    "line": node.lineno,
                    "message": f"Class '{node.name}' missing docstring",
                    "type": "documentation",
                })

        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            metrics["imports"] += 1
            # Check for wildcard imports
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
                issues.append({
                    "level": "warning",
                    "line": node.lineno,
                    "message": "Wildcard import used",
                    "type": "style",
                })

        elif isinstance(node, ast.ExceptHandler):
            # Check for bare except
            if node.type is None:
                issues.append({
                    "level": "warning",
                    "line": node.lineno,
                    "message": "Bare 'except:' clause — should specify exception type",
                    "type": "error_handling",
                })

        elif isinstance(node, ast.Call):
            # Check for print statements (should use logging in production)
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                # Only flag in non-test, non-ui files
                if "ui.py" not in str(filepath) and "test_" not in str(filepath):
                    issues.append({
                        "level": "info",
                        "line": node.lineno,
                        "message": "Consider using structured logging instead of print",
                        "type": "logging",
                    })

    return {"issues": issues, "metrics": metrics}


def analyze_project(root: Path, max_files: int = 50) -> dict[str, Any]:
    """Analyze all Python files in the project."""
    results = {}
    total_issues = {"error": 0, "warning": 0, "info": 0}

    py_files = list(root.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    for filepath in py_files[:max_files]:
        result = analyze_file(filepath)
        rel = str(filepath.relative_to(root))
        results[rel] = result
        for issue in result["issues"]:
            total_issues[issue["level"]] = total_issues.get(issue["level"], 0) + 1

    return {
        "files": results,
        "total_files": len(py_files),
        "analyzed": len(results),
        "total_issues": total_issues,
    }


def format_report(report: dict[str, Any]) -> str:
    """Format quality report for display."""
    lines = []
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}Code Quality Report{Colors.RESET}")
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"Files analyzed: {report['analyzed']} / {report['total_files']}")
    lines.append(f"Issues: {report['total_issues'].get('error', 0)} errors, {report['total_issues'].get('warning', 0)} warnings, {report['total_issues'].get('info', 0)} info")
    lines.append("")

    for filename, result in report["files"].items():
        if not result["issues"]:
            continue
        lines.append(f"{Colors.YELLOW}{filename}{Colors.RESET}")
        metrics = result["metrics"]
        lines.append(f"  {Colors.DIM}lines: {metrics['lines']}, functions: {metrics['functions']}, classes: {metrics['classes']}{Colors.RESET}")
        for issue in result["issues"][:5]:  # Show max 5 per file
            color = {
                "error": Colors.RED,
                "warning": Colors.YELLOW,
                "info": Colors.DIM,
            }.get(issue["level"], Colors.RESET)
            line_info = f"line {issue['line']}" if issue.get("line") else ""
            lines.append(f"  {color}[{issue['level'].upper()}]{Colors.RESET} {line_info} {issue['message']}")
        if len(result["issues"]) > 5:
            lines.append(f"  {Colors.DIM}... and {len(result['issues']) - 5} more{Colors.RESET}")
        lines.append("")

    return "\n".join(lines)
