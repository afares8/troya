"""Terminal UI utilities for Cascade CLI."""

import shutil
import sys
from typing import Any

try:
    from pygments import highlight
    from pygments.formatters import TerminalFormatter
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    width = shutil.get_terminal_size().columns
    print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'─' * min(len(text), width)}{Colors.RESET}\n")


def print_success(text: str) -> None:
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str) -> None:
    print(f"{Colors.RED}✗ {text}{Colors.RESET}", file=sys.stderr)


def print_warning(text: str) -> None:
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def print_command(cmd: str) -> None:
    print(f"{Colors.CYAN}$ {cmd}{Colors.RESET}")


def print_ai_response(text: str) -> None:
    """Print AI response with formatting."""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}Cascade:{Colors.RESET}")
    print(text)
    print()


def format_file_path(path: str) -> str:
    return f"{Colors.YELLOW}{path}{Colors.RESET}"


def format_code_block(language: str, code: str) -> str:
    return f"{Colors.DIM}```{language}{Colors.RESET}\n{code}\n{Colors.DIM}```{Colors.RESET}"


def highlight_code(code: str, language: str | None = None) -> str:
    """Highlight code with pygments if available."""
    if not PYGMENTS_AVAILABLE:
        return code
    try:
        if language:
            lexer = get_lexer_by_name(language)
        else:
            lexer = guess_lexer(code)
        return highlight(code, lexer, TerminalFormatter())
    except ClassNotFound:
        return code
    except Exception:
        return code


def render_markdown(text: str) -> str:
    """Simple markdown rendering for terminal: code blocks get syntax highlighting."""
    if not PYGMENTS_AVAILABLE:
        return text

    import re
    result = []
    i = 0
    pattern = re.compile(r"```(\w+)?\n(.*?)\n```", re.DOTALL)

    for m in pattern.finditer(text):
        start, end = m.span()
        result.append(text[i:start])
        lang = m.group(1) or "text"
        code = m.group(2)
        result.append(f"{Colors.DIM}```{lang}{Colors.RESET}")
        result.append(highlight_code(code, lang))
        result.append(f"{Colors.DIM}```{Colors.RESET}")
        i = end

    result.append(text[i:])
    return "".join(result)


def prompt_user(question: str, default: str = "") -> str:
    """Prompt user for input."""
    prompt_text = f"{Colors.CYAN}? {question}{Colors.RESET} "
    if default:
        prompt_text += f"[{default}] "
    try:
        response = input(prompt_text).strip()
        return response if response else default
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def confirm(question: str, default: bool = False) -> bool:
    """Ask yes/no confirmation."""
    default_str = "Y/n" if default else "y/N"
    try:
        response = input(f"{Colors.YELLOW}? {question} [{default_str}]{Colors.RESET} ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes", "1", "true")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def stream_chunk(chunk: str) -> None:
    """Print a streaming chunk without newline."""
    print(chunk, end="", flush=True)
