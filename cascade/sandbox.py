"""Safe code execution sandbox for Cascade CLI — cross-platform."""

import ast
import contextlib
import io
import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success, print_warning


def is_safe_code(code: str) -> tuple[bool, str]:
    """Parse AST and block dangerous operations."""
    dangerous = {
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",
        "os.system",
        "subprocess",
        "shutil",
        "sys.exit",
        "importlib",
        "compile",
        "__builtins__",
    }
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in dangerous:
                return False, f"Blocked: {node.func.id}() is not allowed"
            if isinstance(node.func, ast.Attribute):
                attr_chain = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    attr_chain.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    attr_chain.append(current.id)
                full = ".".join(reversed(attr_chain))
                if full in dangerous or any(d in full for d in dangerous):
                    return False, f"Blocked: {full} is not allowed"

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {
                    "os",
                    "subprocess",
                    "shutil",
                    "sys",
                    "socket",
                    "urllib",
                    "http",
                }:
                    return False, f"Blocked import: {alias.name}"

        if isinstance(node, ast.ImportFrom):
            if node.module in {"os", "subprocess", "shutil", "sys", "socket"}:
                return False, f"Blocked import: {node.module}"

    return True, ""


def _run_with_timeout(code: str, timeout: int) -> dict[str, Any]:
    """Execute code with thread-based timeout (cross-platform)."""
    result_container = {}
    stdout = io.StringIO()
    stderr = io.StringIO()

    def target():
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                restricted_globals = {
                    "__builtins__": {
                        "abs": abs,
                        "all": all,
                        "any": any,
                        "bin": bin,
                        "bool": bool,
                        "bytearray": bytearray,
                        "bytes": bytes,
                        "chr": chr,
                        "dict": dict,
                        "dir": dir,
                        "divmod": divmod,
                        "enumerate": enumerate,
                        "filter": filter,
                        "float": float,
                        "format": format,
                        "frozenset": frozenset,
                        "getattr": getattr,
                        "globals": lambda: {},
                        "hasattr": hasattr,
                        "hash": hash,
                        "hex": hex,
                        "id": id,
                        "input": input,
                        "int": int,
                        "isinstance": isinstance,
                        "issubclass": issubclass,
                        "iter": iter,
                        "len": len,
                        "list": list,
                        "locals": lambda: {},
                        "map": map,
                        "max": max,
                        "memoryview": memoryview,
                        "min": min,
                        "next": next,
                        "object": object,
                        "oct": oct,
                        "ord": ord,
                        "pow": pow,
                        "print": print,
                        "property": property,
                        "range": range,
                        "repr": repr,
                        "reversed": reversed,
                        "round": round,
                        "set": set,
                        "setattr": setattr,
                        "slice": slice,
                        "sorted": sorted,
                        "staticmethod": staticmethod,
                        "str": str,
                        "sum": sum,
                        "super": super,
                        "tuple": tuple,
                        "type": type,
                        "vars": vars,
                        "zip": zip,
                        "Exception": Exception,
                        "BaseException": BaseException,
                        "ArithmeticError": ArithmeticError,
                        "AssertionError": AssertionError,
                        "AttributeError": AttributeError,
                        "ImportError": ImportError,
                        "IndexError": IndexError,
                        "KeyError": KeyError,
                        "LookupError": LookupError,
                        "MemoryError": MemoryError,
                        "NameError": NameError,
                        "NotImplementedError": NotImplementedError,
                        "OSError": OSError,
                        "OverflowError": OverflowError,
                        "RecursionError": RecursionError,
                        "ReferenceError": ReferenceError,
                        "RuntimeError": RuntimeError,
                        "StopIteration": StopIteration,
                        "SyntaxError": SyntaxError,
                        "SystemError": SystemError,
                        "TypeError": TypeError,
                        "ValueError": ValueError,
                        "ZeroDivisionError": ZeroDivisionError,
                        "True": True,
                        "False": False,
                        "None": None,
                        "json": __import__("json"),
                        "math": __import__("math"),
                        "random": __import__("random"),
                        "datetime": __import__("datetime"),
                        "re": __import__("re"),
                        "collections": __import__("collections"),
                        "itertools": __import__("itertools"),
                        "functools": __import__("functools"),
                        "statistics": __import__("statistics"),
                        "decimal": __import__("decimal"),
                        "fractions": __import__("fractions"),
                        "typing": __import__("typing"),
                        "string": __import__("string"),
                        "hashlib": __import__("hashlib"),
                    }
                }
                exec(code, restricted_globals)
                result_container["success"] = True
            except Exception as e:
                result_container["success"] = False
                result_container["exception"] = traceback.format_exc()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return {
            "success": False,
            "output": stdout.getvalue(),
            "error": f"Execution timed out after {timeout}s",
        }

    output = stdout.getvalue()
    error = stderr.getvalue()
    if not result_container.get("success", False):
        return {
            "success": False,
            "output": output,
            "error": result_container.get("exception", error),
        }
    return {"success": True, "output": output, "error": error}


def run_sandboxed(code: str, timeout: int = 10) -> dict[str, Any]:
    """Execute Python code in a restricted cross-platform environment."""
    safe, reason = is_safe_code(code)
    if not safe:
        return {"success": False, "output": "", "error": reason}

    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            result = _run_with_timeout(code, timeout)
        finally:
            os.chdir(old_cwd)
        return result


def format_result(result: dict[str, Any]) -> str:
    """Format sandbox execution result for display."""
    lines = []
    if result["success"]:
        if result["output"]:
            lines.append(f"{Colors.GREEN}Output:{Colors.RESET}")
            lines.append(result["output"])
        else:
            lines.append(
                f"{Colors.GREEN}✓ Executed successfully (no output){Colors.RESET}"
            )
    else:
        lines.append(f"{Colors.RED}✗ Execution failed:{Colors.RESET}")
        if result["error"]:
            lines.append(result["error"])
    return "\n".join(lines)
