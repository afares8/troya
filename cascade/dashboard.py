"""Embedded web dashboard for Cascade CLI — launched via /dashboard command."""

import threading
from pathlib import Path
from typing import Any

from .ui import print_error, print_info, print_success

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cascade CLI Dashboard</title>
<style>
:root{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--border:#30363d;--fg:#c9d1d9;--accent:#58a6ff;--accent2:#238636;--warn:#f59e0b;--danger:#ef4444;--font:14px/1.5 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font:var(--font);background:var(--bg);color:var(--fg);height:100vh;display:flex;flex-direction:column;overflow:hidden;}
header{height:52px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;}
header h1{font-size:16px;font-weight:700;display:flex;align-items:center;gap:8px;}
main{flex:1;display:flex;overflow:hidden;}
.panel{flex:1;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;min-width:280px;}
.panel:last-child{border-right:none;}
.panel-header{padding:10px 14px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--fg);opacity:.5;font-weight:700;border-bottom:1px solid var(--border);}
.panel-content{flex:1;overflow:auto;padding:14px;}
.stat{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:10px;text-align:center;margin-bottom:8px;}
.stat .value{font-size:20px;font-weight:700;color:var(--accent);}
.stat .label{font-size:10px;opacity:.6;margin-top:2px;}
.agent-card{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px;display:flex;align-items:center;gap:10px;}
.agent-card .avatar{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;background:var(--accent);}
.agent-card .info{flex:1;}
.agent-card .name{font-weight:600;font-size:13px;}
.agent-card .role{font-size:11px;opacity:.5;}
.agent-card .status{font-size:10px;padding:2px 6px;border-radius:4px;background:var(--bg);}
.agent-card .status.working{background:var(--warn);color:#000;}
.task{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px;}
.task .title{font-weight:600;margin-bottom:4px;}
.task .status{font-size:10px;padding:2px 8px;border-radius:4px;display:inline-block;}
.task .status.completed{background:var(--accent2);color:#fff;}
.task .status.pending{background:var(--warn);color:#000;}
.task .status.in_progress{background:var(--accent);color:#fff;}
::-webkit-scrollbar{width:8px;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px;}
</style>
</head>
<body>
<header><h1>🚀 Cascade CLI Dashboard</h1><span id="status">LIVE</span></header>
<main>
<div class="panel">
<div class="panel-header">Stats</div>
<div class="panel-content" id="stats"></div>
</div>
<div class="panel">
<div class="panel-header">Agents</div>
<div class="panel-content" id="agents"></div>
</div>
<div class="panel">
<div class="panel-header">Tasks</div>
<div class="panel-content" id="tasks"></div>
</div>
</main>
<script>
async function refresh() {
  try {
    const r = await fetch("/api/stats");
    const data = await r.json();
    document.getElementById("stats").innerHTML = `
      <div class="stat"><div class="value">${data.total_tasks||0}</div><div class="label">Tasks</div></div>
      <div class="stat"><div class="value">${data.completed||0}</div><div class="label">Done</div></div>
      <div class="stat"><div class="value">${data.failed||0}</div><div class="label">Failed</div></div>
      <div class="stat"><div class="value">${data.total_agents||0}</div><div class="label">Agents</div></div>
    `;
  } catch(e) {}
  try {
    const r2 = await fetch("/api/agents");
    const agents = await r2.json();
    document.getElementById("agents").innerHTML = agents.map(a => `
      <div class="agent-card">
        <div class="avatar">${a.role==="coder"?"💻":a.role==="researcher"?"🔍":"👁"}</div>
        <div class="info">
          <div class="name">${a.name}</div>
          <div class="role">${a.role} — ${a.model}</div>
        </div>
        <span class="status ${a.status}">${a.status}</span>
      </div>
    `).join("");
  } catch(e) {}
  try {
    const r3 = await fetch("/api/tasks");
    const tasks = await r3.json();
    document.getElementById("tasks").innerHTML = tasks.slice(0,10).map(t => `
      <div class="task">
        <div class="title">#${t.id} ${t.title}</div>
        <span class="status ${t.status}">${t.status}</span>
        <div style="opacity:.5;font-size:11px;margin-top:4px">${t.assigned_to||"unassigned"}</div>
      </div>
    `).join("");
  } catch(e) {}
}
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>'''

_server_thread: threading.Thread | None = None


def _make_app():
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        from fastapi.staticfiles import StaticFiles
        from .agents.db import get_stats, list_agents, list_tasks, init_db
        app = FastAPI(title="Cascade Dashboard")
        app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
        init_db()
        @app.get("/", response_class=HTMLResponse)
        def index():
            return DASHBOARD_HTML
        @app.get("/api/stats")
        def stats():
            return get_stats()
        @app.get("/api/agents")
        def agents():
            return list_agents()
        @app.get("/api/tasks")
        def tasks():
            return list_tasks()
        return app
    except ImportError:
        return None


def start_dashboard(host: str = "127.0.0.1", port: int = 8767) -> bool:
    """Start the embedded dashboard server in a background thread."""
    global _server_thread
    try:
        import uvicorn
    except ImportError:
        print_error("uvicorn not installed. Run: pip install uvicorn")
        return False

    app = _make_app()
    if app is None:
        print_error("fastapi not installed. Run: pip install fastapi")
        return False

    def run():
        uvicorn.run(app, host=host, port=port, log_level="warning")

    if _server_thread and _server_thread.is_alive():
        print_info(f"Dashboard already running at http://{host}:{port}")
        return True

    _server_thread = threading.Thread(target=run, daemon=True)
    _server_thread.start()
    print_success(f"Dashboard started at http://{host}:{port}")
    print_info("Press Ctrl+C in the CLI to stop")
    return True
