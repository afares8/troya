"""Clipboard integration for Cascade CLI."""

import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard."""
    # macOS
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"), timeout=5)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Linux (xclip)
    try:
        proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"), timeout=5)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Linux (xsel)
    try:
        proc = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"), timeout=5)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Windows (clip)
    try:
        proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
        proc.communicate(text.encode("utf-8"), timeout=5)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Python fallback (pyperclip)
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    return False


def paste_from_clipboard() -> str:
    """Paste text from system clipboard."""
    # macOS
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Linux (xclip)
    try:
        result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Python fallback
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        pass

    return ""
