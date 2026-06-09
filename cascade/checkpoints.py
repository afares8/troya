"""Persistent checkpoint system for Cascade CLI — resume long tasks."""

import json
import time
from pathlib import Path
from typing import Any

CHECKPOINT_DIR = Path.home() / ".config" / "cascade-cli" / "checkpoints"


class CheckpointManager:
    """Save and resume agent state across sessions."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.checkpoint_file = CHECKPOINT_DIR / f"{task_id}.json"
        self.data: dict[str, Any] = {
            "task_id": task_id,
            "created": time.time(),
            "updated": time.time(),
            "status": "running",
            "objective": "",
            "plan": [],
            "current_step": 0,
            "results": [],
            "files_modified": [],
            "files_read": [],
            "context_files": [],
            "git_branch": None,
            "git_commit": None,
        }
        self._load()

    def _load(self) -> None:
        if self.checkpoint_file.exists():
            try:
                self.data = json.loads(self.checkpoint_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self.data["updated"] = time.time()
        self.checkpoint_file.write_text(json.dumps(self.data, indent=2))

    def update(self, **kwargs: Any) -> None:
        for key, val in kwargs.items():
            if key in self.data:
                self.data[key] = val
        self.save()

    def add_result(self, result: dict[str, Any]) -> None:
        self.data["results"].append(result)
        self.save()

    def add_file_modified(self, filepath: str) -> None:
        if filepath not in self.data["files_modified"]:
            self.data["files_modified"].append(filepath)
            self.save()

    def add_file_read(self, filepath: str) -> None:
        if filepath not in self.data["files_read"]:
            self.data["files_read"].append(filepath)
            self.save()

    def mark_complete(self) -> None:
        self.data["status"] = "completed"
        self.save()

    def mark_failed(self, error: str) -> None:
        self.data["status"] = "failed"
        self.data["error"] = error
        self.save()

    @staticmethod
    def list_checkpoints() -> list[tuple[str, str, float]]:
        """List all checkpoints."""
        checkpoints = []
        if CHECKPOINT_DIR.exists():
            for f in CHECKPOINT_DIR.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    checkpoints.append((
                        f.stem,
                        data.get("objective", "Unknown")[:50],
                        data.get("updated", 0)
                    ))
                except Exception:
                    pass
        checkpoints.sort(key=lambda x: x[2], reverse=True)
        return checkpoints

    @staticmethod
    def load_checkpoint(task_id: str) -> "CheckpointManager":
        """Load an existing checkpoint. Returns None if not found."""
        cp = CheckpointManager(task_id)
        if cp.checkpoint_file.exists():
            return cp
        return None

    def format_summary(self) -> str:
        from .ui import Colors

        lines = []
        lines.append(f"{Colors.CYAN}Checkpoint: {self.task_id}{Colors.RESET}")
        lines.append(f"  Status: {self.data['status']}")
        lines.append(f"  Objective: {self.data['objective'][:60]}")
        lines.append(f"  Step: {self.data['current_step']}/{len(self.data['plan'])}")
        lines.append(f"  Files modified: {len(self.data['files_modified'])}")
        lines.append(f"  Files read: {len(self.data['files_read'])}")
        return "\n".join(lines)
