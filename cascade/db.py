"""SQLite persistence for multi-agent system."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "agents.db"


def init_db() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            assigned_to TEXT,
            result TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            role TEXT,
            model TEXT,
            status TEXT DEFAULT 'idle',
            total_tasks INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            agent_name TEXT,
            role TEXT,
            content TEXT,
            tool_calls TEXT,
            created_at TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            agent_name TEXT,
            tool_name TEXT,
            arguments TEXT,
            result TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def create_task(title: str, description: str = "") -> int:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO tasks (title, description, status, created_at) VALUES (?, ?, ?, ?)",
              (title, description, "pending", now))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id: int, **kwargs: Any) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE tasks SET {key} = ? WHERE id = ?", (val, task_id))
    if "status" in kwargs and kwargs["status"] in ("completed", "failed"):
        c.execute("UPDATE tasks SET completed_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), task_id))
    conn.commit()
    conn.close()


def get_task(task_id: int) -> dict[str, Any] | None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,))
    else:
        c.execute("SELECT * FROM tasks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def register_agent(name: str, role: str, model: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("INSERT OR IGNORE INTO agents (name, role, model, created_at) VALUES (?, ?, ?, ?)",
              (name, role, model, now))
    conn.commit()
    conn.close()


def update_agent(name: str, **kwargs: Any) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE agents SET {key} = ? WHERE name = ?", (val, name))
    if "status" in kwargs and kwargs["status"] == "idle":
        c.execute("UPDATE agents SET total_tasks = total_tasks + 1 WHERE name = ?", (name,))
    conn.commit()
    conn.close()


def list_agents() -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM agents ORDER BY total_tasks DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_message(task_id: int, agent_name: str, role: str, content: str, tool_calls: list | None = None) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    tc = json.dumps(tool_calls) if tool_calls else None
    c.execute("INSERT INTO messages (task_id, agent_name, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (task_id, agent_name, role, content, tc, now))
    conn.commit()
    conn.close()


def get_messages(task_id: int) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE task_id = ? ORDER BY id", (task_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_tool_call(task_id: int, agent_name: str, tool_name: str, arguments: dict, result: Any) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO tool_calls (task_id, agent_name, tool_name, arguments, result, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (task_id, agent_name, tool_name, json.dumps(arguments), json.dumps(result), now))
    conn.commit()
    conn.close()


def get_stats() -> dict[str, Any]:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    completed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
    failed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM agents")
    total_agents = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages")
    total_messages = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tool_calls")
    total_tools = c.fetchone()[0]
    conn.close()
    return {
        "total_tasks": total_tasks,
        "completed": completed,
        "failed": failed,
        "total_agents": total_agents,
        "total_messages": total_messages,
        "total_tool_calls": total_tools,
    }
