"""Code explanation engine — step-by-step execution flow analysis."""

import ast
from pathlib import Path
from typing import Any

from .ui import Colors, print_info


def explain_function(filepath: Path, func_name: str) -> str:
    """Explain a function step by step."""
    try:
        tree = ast.parse(filepath.read_text())
    except (SyntaxError, OSError) as e:
        return f"Could not parse file: {e}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return _explain_function_node(node, filepath.name)

    return f"Function '{func_name}' not found in {filepath}"


def _explain_function_node(node: ast.FunctionDef | ast.AsyncFunctionDef, filename: str) -> str:
    """Generate step-by-step explanation of a function."""
    lines = []
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}Function: {node.name}(){Colors.RESET}")
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"File: {filename}")
    lines.append(f"Line: {node.lineno}")
    lines.append("")

    # Parameters
    params = []
    for arg in node.args.args:
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        params.append(param)
    if node.args.kwarg:
        params.append(f"**{node.args.kwarg.arg}")
    if node.args.vararg:
        params.append(f"*{node.args.vararg.arg}")

    lines.append(f"Parameters: {', '.join(params) if params else 'none'}")
    lines.append("")

    # Step by step
    lines.append(f"{Colors.YELLOW}Execution flow:{Colors.RESET}")
    step = 1
    for stmt in node.body:
        explanation = _explain_statement(stmt)
        if explanation:
            lines.append(f"  {Colors.GREEN}{step}.{Colors.RESET} {explanation}")
            step += 1

    # Return value
    returns = [stmt for stmt in node.body if isinstance(stmt, ast.Return)]
    if returns:
        lines.append("")
        lines.append(f"Returns: {ast.unparse(returns[-1].value) if returns[-1].value else 'None'}")
    else:
        lines.append("")
        lines.append("Returns: None (implicit)")

    return "\n".join(lines)


def _explain_statement(stmt: ast.AST) -> str:
    """Explain a single statement."""
    if isinstance(stmt, ast.Expr):
        return f"Evaluate expression: {ast.unparse(stmt.value)[:60]}"
    elif isinstance(stmt, ast.Assign):
        targets = ", ".join(ast.unparse(t) for t in stmt.targets)
        return f"Assign: {targets} = {ast.unparse(stmt.value)[:40]}"
    elif isinstance(stmt, ast.AnnAssign):
        return f"Assign: {ast.unparse(stmt.target)} = {ast.unparse(stmt.value)[:40]}"
    elif isinstance(stmt, ast.Return):
        if stmt.value:
            return f"Return: {ast.unparse(stmt.value)[:50]}"
        return "Return None"
    elif isinstance(stmt, ast.If):
        return f"Branch: if {ast.unparse(stmt.test)[:40]}"
    elif isinstance(stmt, ast.For):
        return f"Loop: for {ast.unparse(stmt.target)} in {ast.unparse(stmt.iter)[:40]}"
    elif isinstance(stmt, ast.While):
        return f"Loop: while {ast.unparse(stmt.test)[:40]}"
    elif isinstance(stmt, ast.Try):
        return "Try/except block"
    elif isinstance(stmt, ast.With):
        return f"Context manager: {ast.unparse(stmt.items[0].context_expr)[:40]}"
    elif isinstance(stmt, ast.Raise):
        return f"Raise exception: {ast.unparse(stmt.exc)[:40]}" if stmt.exc else "Raise exception"
    elif isinstance(stmt, ast.Assert):
        return f"Assert: {ast.unparse(stmt.test)[:40]}"
    elif isinstance(stmt, ast.Import) or isinstance(stmt, ast.ImportFrom):
        return f"Import: {ast.unparse(stmt)[:50]}"
    elif isinstance(stmt, ast.Pass):
        return None
    else:
        return f"Execute: {ast.unparse(stmt)[:60]}"


def explain_file(filepath: Path) -> str:
    """Explain top-level structure of a file."""
    try:
        tree = ast.parse(filepath.read_text())
    except (SyntaxError, OSError) as e:
        return f"Could not parse file: {e}"

    lines = []
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}File Structure: {filepath.name}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")

    functions = []
    classes = []
    imports = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            functions.append(f"  def {node.name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append(f"  class {node.name}")
            for m in methods[:5]:
                classes.append(f"    - {m}()")
            if len(methods) > 5:
                classes.append(f"    - ... and {len(methods) - 5} more")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(f"  {ast.unparse(node)[:60]}")

    if imports:
        lines.append(f"{Colors.YELLOW}Imports ({len(imports)}):{Colors.RESET}")
        lines.extend(imports[:10])
        if len(imports) > 10:
            lines.append(f"  ... and {len(imports) - 10} more")
        lines.append("")

    if classes:
        lines.append(f"{Colors.YELLOW}Classes ({len([c for c in tree.body if isinstance(c, ast.ClassDef)])}):{Colors.RESET}")
        lines.extend(classes)
        lines.append("")

    if functions:
        lines.append(f"{Colors.YELLOW}Functions ({len(functions)}):{Colors.RESET}")
        lines.extend(functions)
        lines.append("")

    if not classes and not functions:
        lines.append("No classes or functions at top level.")

    return "\n".join(lines)


def explain_class(filepath: Path, class_name: str) -> str:
    """Explain a class structure."""
    try:
        tree = ast.parse(filepath.read_text())
    except (SyntaxError, OSError) as e:
        return f"Could not parse file: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            lines = []
            lines.append(f"{Colors.CYAN}Class: {class_name}{Colors.RESET}")
            lines.append(f"Line: {node.lineno}")

            bases = [ast.unparse(b) for b in node.bases]
            if bases:
                lines.append(f"Inherits: {', '.join(bases)}")

            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            lines.append(f"Methods: {len(methods)}")

            for m in methods:
                args = [arg.arg for arg in m.args.args]
                is_dunder = m.name.startswith("__") and m.name.endswith("__")
                color = Colors.DIM if is_dunder else Colors.YELLOW
                lines.append(f"  {color}- {m.name}({', '.join(args)}){Colors.RESET}")

            return "\n".join(lines)

    return f"Class '{class_name}' not found in {filepath}"
