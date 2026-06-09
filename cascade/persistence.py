"""Conversation persistence and export."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success

SESSIONS_DIR = Path.home() / ".config" / "cascade-cli" / "sessions"


def ensure_sessions_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def generate_session_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:8]}"


def save_session(
    session_id: str,
    messages: list[dict[str, str]],
    files: dict[str, str],
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Save a conversation session to disk."""
    ensure_sessions_dir()
    filepath = SESSIONS_DIR / f"{session_id}.json"

    data = {
        "id": session_id,
        "timestamp": datetime.now().isoformat(),
        "messages": messages,
        "files": files,
        "metadata": metadata or {},
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def load_session(session_id: str) -> dict[str, Any] | None:
    """Load a conversation session from disk."""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print_error(f"Failed to load session: {e}")
        return None


def list_sessions() -> list[dict[str, Any]]:
    """List all saved sessions."""
    ensure_sessions_dir()
    sessions = []

    for filepath in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "id": data.get("id", filepath.stem),
                    "timestamp": data.get("timestamp", ""),
                    "message_count": len(data.get("messages", [])),
                    "file_count": len(data.get("files", {})),
                })
        except Exception:
            continue

    return sessions


def export_to_markdown(
    session_id: str,
    output_path: Path | None = None,
) -> Path | None:
    """Export a session to a markdown file."""
    session = load_session(session_id)
    if not session:
        print_error(f"Session not found: {session_id}")
        return None

    if output_path is None:
        output_path = Path.cwd() / f"cascade_session_{session_id}.md"

    lines = [
        f"# Cascade Session: {session_id}",
        f"",
        f"**Date:** {session.get('timestamp', 'unknown')}",
        f"",
        "---",
        "",
    ]

    # Files
    if session.get("files"):
        lines.append("## Files in Context\n")
        for path, content in session["files"].items():
            lines.append(f"### `{path}`")
            lines.append("```")
            lines.append(content)
            lines.append("```")
            lines.append("")

    # Messages
    if session.get("messages"):
        lines.append("## Conversation\n")
        for msg in session["messages"]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system":
                continue
            elif role == "user":
                lines.append(f"### 👤 User")
            elif role == "assistant":
                lines.append(f"### 🤖 Assistant")
            else:
                lines.append(f"### {role.title()}")

            lines.append(content)
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print_success(f"Exported to {output_path}")
    return output_path


def print_sessions_list() -> None:
    """Print a formatted list of saved sessions."""
    sessions = list_sessions()
    if not sessions:
        print_info("No saved sessions found.")
        return

    print(f"{Colors.CYAN}Saved Sessions:{Colors.RESET}")
    for s in sessions[:20]:
        ts = s.get("timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                ts = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass
        print(
            f"  {Colors.YELLOW}{s['id']}{Colors.RESET}  "
            f"({s['message_count']} msgs, {s['file_count']} files)  "
            f"{Colors.DIM}{ts}{Colors.RESET}"
        )

    if len(sessions) > 20:
        print(f"  ... and {len(sessions) - 20} more")
