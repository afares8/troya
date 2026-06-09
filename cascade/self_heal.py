"""Self-healing: auto-detect and fix broken Python code."""

import re
import traceback
from pathlib import Path
from typing import Any

from .llm import LLMClient
from .sandbox import format_result, run_sandboxed
from .ui import Colors, print_error, print_info, print_success, print_warning


def analyze_error(error_text: str) -> dict[str, Any]:
    """Parse Python traceback and extract key info."""
    result = {
        "error_type": None,
        "error_message": None,
        "file": None,
        "line": None,
        "snippet": None,
        "suggestion": None,
    }

    # Extract error type and message
    lines = error_text.strip().split("\n")
    for line in reversed(lines):
        if ":" in line and not line.startswith(" ") and not line.startswith("Traceback"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                result["error_type"] = parts[0].strip()
                result["error_message"] = parts[1].strip()
            break

    # Extract file and line
    traceback_match = re.search(r'File "([^"]+)", line (\d+)', error_text)
    if traceback_match:
        result["file"] = traceback_match.group(1)
        result["line"] = int(traceback_match.group(2))

    # Heuristic suggestions
    if result["error_type"]:
        err = result["error_type"]
        msg = result["error_message"] or ""
        if "NameError" in err:
            result["suggestion"] = f"Variable '{msg}' is not defined. Check spelling or import the module."
        elif "TypeError" in err and "takes" in msg and "positional argument" in msg:
            result["suggestion"] = "Function called with wrong number of arguments. Check the function signature."
        elif "TypeError" in err and "'NoneType'" in msg:
            result["suggestion"] = "A function returned None but you're trying to use it as another type. Check return values."
        elif "ImportError" in err or "ModuleNotFoundError" in err:
            result["suggestion"] = f"Module not found: {msg}. Install with pip or check the module name."
        elif "SyntaxError" in err:
            result["suggestion"] = "Invalid Python syntax. Check for missing colons, brackets, or quotes."
        elif "IndexError" in err:
            result["suggestion"] = "List index out of range. Check the list length before indexing."
        elif "KeyError" in err:
            result["suggestion"] = f"Dictionary key '{msg}' not found. Use .get() or check the key exists."
        elif "AttributeError" in err:
            result["suggestion"] = f"Object doesn't have attribute. Check the object type or attribute name."
        elif "ZeroDivisionError" in err:
            result["suggestion"] = "Division by zero. Add a check before dividing."
        else:
            result["suggestion"] = "Unknown error. Review the traceback carefully."

    return result


def generate_fix(code: str, error_info: dict[str, Any], client: LLMClient) -> str:
    """Use LLM to generate a fix for broken code."""
    prompt = f"""The following Python code has an error:

```python
{code}
```

Error: {error_info['error_type']}: {error_info['error_message']}
Suggestion: {error_info['suggestion']}

Please provide the corrected code. Only output the fixed code, no explanations:

```python
"""
    messages = [
        {"role": "system", "content": "You are a Python expert. Fix code errors precisely. Output only the corrected code."},
        {"role": "user", "content": prompt},
    ]
    response = client.chat(messages)
    # Extract code block
    match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()


def _apply_heuristic_fix(code: str, error_info: dict[str, Any]) -> str:
    """Apply simple heuristic fixes without LLM."""
    err_type = error_info.get("error_type", "")
    err_msg = error_info.get("error_message", "")
    lines = code.split("\n")

    if "NameError" in err_type:
        # Try to define missing variable
        missing = err_msg.strip().strip("'\"")
        return f"{missing} = None  # auto-defined by heuristic fix\n{code}"

    if "SyntaxError" in err_type:
        # Common syntax fixes
        fixed = code.replace("print ", "print(", 1)
        if fixed != code:
            return fixed

    if "IndentationError" in err_type:
        # Fix common indentation
        fixed_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                fixed_lines.append("    " + stripped)
            else:
                fixed_lines.append(line)
        return "\n".join(fixed_lines)

    if "ZeroDivisionError" in err_type:
        return code.replace("/ 0", "/ 1  # fixed div by zero", 1)

    return code


def heal_code(code: str, client: LLMClient, auto_apply: bool = False) -> dict[str, Any]:
    """Run code, detect errors, generate fix, optionally apply."""
    from .llm import LLMClient as RealLLMClient

    print_info("Running code in sandbox...")
    result = run_sandboxed(code)

    if result["success"]:
        print_success("Code executed successfully!")
        return {"fixed": False, "output": result["output"], "error": None, "fixed_code": code}

    print_error("Code failed. Analyzing error...")
    error_info = analyze_error(result["error"])
    print_info(f"Error: {error_info['error_type']}: {error_info['error_message']}")
    print_info(f"Suggestion: {error_info['suggestion']}")

    is_offline = not isinstance(client, RealLLMClient)
    if is_offline:
        print_warning("Offline mode — using heuristic fix (no LLM available)")
        fixed_code = _apply_heuristic_fix(code, error_info)
    else:
        print_info("Generating fix with AI...")
        fixed_code = generate_fix(code, error_info, client)

    print_info("Testing fixed code...")
    test_result = run_sandboxed(fixed_code)

    if test_result["success"]:
        print_success("Fix verified! Code now runs successfully.")
        if auto_apply:
            return {"fixed": True, "output": test_result["output"], "error": None, "fixed_code": fixed_code}
        return {"fixed": True, "output": test_result["output"], "error": None, "fixed_code": fixed_code, "needs_approval": True}
    else:
        print_error("Auto-fix also failed. Manual intervention needed.")
        return {"fixed": False, "output": result["output"], "error": result["error"], "fixed_code": fixed_code, "fix_error": test_result["error"]}


def heal_file(filepath: Path, client: LLMClient, auto_apply: bool = False) -> dict[str, Any]:
    """Heal a file by reading it, running it, and fixing errors."""
    try:
        code = filepath.read_text()
    except (OSError, UnicodeDecodeError) as e:
        return {"fixed": False, "error": f"Cannot read file: {e}"}
    return heal_code(code, client, auto_apply)
