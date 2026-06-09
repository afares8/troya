"""Time tracking for Cascade CLI — track time spent per project and file."""

import json
import time
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success

TRACKING_FILE = Path.home() / ".config" / "cascade-cli" / "time_tracking.json"


class TimeTracker:
    """Track time spent on files and projects."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {"sessions": [], "files": {}, "projects": {}}
        self._load()
        self._current_file: Path | None = None
        self._current_project: Path | None = None
        self._start_time: float | None = None

    def _load(self) -> None:
        if TRACKING_FILE.exists():
            try:
                self.data = json.loads(TRACKING_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRACKING_FILE.write_text(json.dumps(self.data, indent=2))

    def start_session(self, project_root: Path) -> None:
        self._current_project = project_root
        self._start_time = time.time()
        self.data["sessions"].append({
            "project": str(project_root),
            "start": self._start_time,
            "end": None,
            "duration": 0,
        })
        self._save()

    def end_session(self) -> dict[str, Any]:
        if self._start_time is None:
            return {"duration": 0}

        end_time = time.time()
        duration = end_time - self._start_time

        # Update last session
        if self.data["sessions"]:
            self.data["sessions"][-1]["end"] = end_time
            self.data["sessions"][-1]["duration"] = duration

        # Update project total
        if self._current_project:
            key = str(self._current_project)
            self.data["projects"][key] = self.data["projects"].get(key, 0) + duration

        self._save()

        return {
            "duration": duration,
            "project": str(self._current_project) if self._current_project else None,
        }

    def switch_file(self, filepath: Path) -> None:
        """Record time spent on previous file and switch to new one."""
        now = time.time()

        if self._current_file and self._start_time:
            duration = now - self._start_time
            key = str(self._current_file)
            self.data["files"][key] = self.data["files"].get(key, 0) + duration

        self._current_file = filepath
        self._start_time = now
        self._save()

    def get_stats(self, project_root: Path | None = None) -> dict[str, Any]:
        """Get time tracking statistics."""
        total_session_time = sum(s.get("duration", 0) for s in self.data["sessions"])

        # Top files
        file_times = [(k, v) for k, v in self.data["files"].items()]
        file_times.sort(key=lambda x: x[1], reverse=True)

        # Top projects
        project_times = [(k, v) for k, v in self.data["projects"].items()]
        project_times.sort(key=lambda x: x[1], reverse=True)

        return {
            "total_sessions": len(self.data["sessions"]),
            "total_time": total_session_time,
            "top_files": file_times[:10],
            "top_projects": project_times[:5],
            "current_project": str(project_root) if project_root else None,
        }

    def format_stats(self, stats: dict[str, Any]) -> str:
        lines = []
        lines.append(f"{Colors.CYAN}{'─' * 40}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Time Tracking{Colors.RESET}")
        lines.append(f"{Colors.CYAN}{'─' * 40}{Colors.RESET}")
        lines.append(f"Total sessions: {stats['total_sessions']}")
        lines.append(f"Total time: {self._format_duration(stats['total_time'])}")
        lines.append("")

        if stats["top_projects"]:
            lines.append(f"{Colors.YELLOW}Top Projects:{Colors.RESET}")
            for project, duration in stats["top_projects"]:
                name = Path(project).name or project
                lines.append(f"  {name}: {self._format_duration(duration)}")
            lines.append("")

        if stats["top_files"]:
            lines.append(f"{Colors.YELLOW}Top Files:{Colors.RESET}")
            for filepath, duration in stats["top_files"][:5]:
                name = Path(filepath).name
                lines.append(f"  {name}: {self._format_duration(duration)}")

        return "\n".join(lines)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
