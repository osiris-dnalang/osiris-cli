"""OSIRIS NCLM Web Dashboard.

A lightweight Flask-free dashboard using only the Python standard library.
Serves a single-page application that shows:
  - Stack blueprint status
  - Evaluation scores over time
  - Meta-loop iteration history
  - Training progress
  - Dataset statistics

Usage:
    python -m nclm.production.dashboard [--port 8411]
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs


# ---- Data collectors ----

def _read_json(path: str) -> Dict[str, Any]:
    """Safely read a JSON file, returning empty dict on failure."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def collect_dashboard_state(root: Optional[str] = None) -> Dict[str, Any]:
    """Gather all available state for the dashboard."""
    root = root or os.getcwd()
    base = Path(root)

    # Latest stack blueprint
    autoadvance = base / ".autoadvance"
    blueprints = sorted(autoadvance.glob("stack_*.json")) if autoadvance.exists() else []
    latest_blueprint = _read_json(str(blueprints[-1])) if blueprints else {}

    # Eval results
    eval_path = base / "artifacts" / "eval" / "results.json"
    eval_results = _read_json(str(eval_path))

    # Meta-loop state
    meta_path = base / "artifacts" / "meta_loop_state.json"
    meta_state = _read_json(str(meta_path))

    # Dataset stats
    data_dir = base / "data"
    dataset_files = list(data_dir.glob("*.jsonl")) if data_dir.exists() else []
    dataset_stats = {}
    for f in dataset_files:
        try:
            count = sum(1 for line in f.open() if line.strip())
            dataset_stats[f.name] = count
        except Exception:
            dataset_stats[f.name] = 0

    # Training artifacts
    sft_dir = base / "artifacts" / "sft"
    training_status = "not started"
    if sft_dir.exists() and list(sft_dir.glob("*")):
        training_status = "completed"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "blueprint": latest_blueprint,
        "eval_results": eval_results,
        "meta_loop": meta_state,
        "datasets": dataset_stats,
        "training_status": training_status,
        "blueprint_count": len(blueprints),
    }


# ---- HTML template ----

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSIRIS NCLM Dashboard</title>
<style>
  :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9;
          --accent: #58a6ff; --green: #3fb950; --yellow: #d29922; --red: #f85149; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--text); padding: 20px; }
  .header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
  .header h1 { font-size: 24px; color: var(--accent); }
  .header .status { padding: 4px 12px; border-radius: 12px; font-size: 12px;
                    font-weight: 600; background: var(--green); color: #000; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
          gap: 16px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
          padding: 20px; }
  .card h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;
             color: var(--accent); margin-bottom: 12px; }
  .metric { display: flex; justify-content: space-between; padding: 8px 0;
            border-bottom: 1px solid var(--border); }
  .metric:last-child { border-bottom: none; }
  .metric .label { color: #8b949e; }
  .metric .value { font-weight: 600; font-family: 'SF Mono', 'Fira Code', monospace; }
  .bar-container { background: var(--border); border-radius: 4px; height: 8px;
                   margin-top: 4px; overflow: hidden; }
  .bar { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
  .bar.green { background: var(--green); }
  .bar.yellow { background: var(--yellow); }
  .bar.red { background: var(--red); }
  .history-item { padding: 8px 0; border-bottom: 1px solid var(--border);
                  font-size: 13px; }
  .history-item:last-child { border-bottom: none; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px;
         font-size: 11px; margin: 2px; }
  .tag.weakness { background: rgba(248,81,73,0.2); color: var(--red); }
  .tag.strength { background: rgba(63,185,80,0.2); color: var(--green); }
  .refresh-btn { position: fixed; bottom: 20px; right: 20px; padding: 10px 20px;
                 background: var(--accent); color: #000; border: none; border-radius: 6px;
                 cursor: pointer; font-weight: 600; font-size: 14px; }
  .refresh-btn:hover { opacity: 0.9; }
  pre { background: #0d1117; padding: 12px; border-radius: 6px; overflow-x: auto;
        font-size: 12px; border: 1px solid var(--border); margin-top: 8px; }
  .empty { color: #484f58; font-style: italic; }
</style>
</head>
<body>
<div class="header">
  <h1>OSIRIS NCLM</h1>
  <span class="status" id="status">LOADING</span>
  <span style="color:#8b949e;font-size:13px" id="timestamp"></span>
</div>
<div class="grid">
  <div class="card">
    <h2>Benchmark Scores</h2>
    <div id="benchmarks"><span class="empty">No evaluation data yet</span></div>
  </div>
  <div class="card">
    <h2>Stack Blueprint</h2>
    <div id="blueprint"><span class="empty">No blueprint generated</span></div>
  </div>
  <div class="card">
    <h2>Meta-Loop Progress</h2>
    <div id="metaloop"><span class="empty">Meta-loop not started</span></div>
  </div>
  <div class="card">
    <h2>Datasets</h2>
    <div id="datasets"><span class="empty">No datasets found</span></div>
  </div>
  <div class="card">
    <h2>Training Status</h2>
    <div id="training"><span class="empty">Not started</span></div>
  </div>
  <div class="card">
    <h2>Meta-Loop History</h2>
    <div id="history"><span class="empty">No iterations yet</span></div>
  </div>
</div>
<button class="refresh-btn" onclick="refresh()">Refresh</button>
<script>
function barColor(v) { return v >= 0.6 ? 'green' : v >= 0.3 ? 'yellow' : 'red'; }

function renderBenchmarks(data) {
  const el = document.getElementById('benchmarks');
  if (!data || Object.keys(data).length === 0) return;
  el.innerHTML = Object.entries(data).map(([k,v]) => {
    const pct = (typeof v === 'number' ? v * 100 : 0).toFixed(1);
    return `<div class="metric"><span class="label">${k}</span><span class="value">${pct}%</span></div>
    <div class="bar-container"><div class="bar ${barColor(v)}" style="width:${pct}%"></div></div>`;
  }).join('');
}

function renderBlueprint(data) {
  const el = document.getElementById('blueprint');
  if (!data || !data.intent) return;
  el.innerHTML = `
    <div class="metric"><span class="label">Objective</span><span class="value">${data.intent.objective||''}</span></div>
    <div class="metric"><span class="label">Capabilities</span><span class="value">${(data.intent.must_have_capabilities||[]).join(', ')}</span></div>
    <div class="metric"><span class="label">Generated</span><span class="value">${data.generated_at||'—'}</span></div>
  `;
}

function renderMetaLoop(data) {
  const el = document.getElementById('metaloop');
  if (!data || !data.objective) return;
  const h = data.history || [];
  el.innerHTML = `
    <div class="metric"><span class="label">Iterations</span><span class="value">${h.length}</span></div>
    <div class="metric"><span class="label">Converged</span><span class="value">${data.converged ? 'Yes' : 'No'}</span></div>
    <div class="metric"><span class="label">Data Generated</span><span class="value">${data.total_data_generated||0}</span></div>
    <div class="metric"><span class="label">Train Steps</span><span class="value">${data.total_train_steps||0}</span></div>
  `;
}

function renderDatasets(data) {
  const el = document.getElementById('datasets');
  if (!data || Object.keys(data).length === 0) return;
  el.innerHTML = Object.entries(data).map(([k,v]) =>
    `<div class="metric"><span class="label">${k}</span><span class="value">${v} samples</span></div>`
  ).join('');
}

function renderTraining(status) {
  const el = document.getElementById('training');
  const colors = {'completed':'green','in_progress':'yellow','not started':'red'};
  el.innerHTML = `<div class="metric"><span class="label">Status</span><span class="value" style="color:var(--${colors[status]||'text'})">${status}</span></div>`;
}

function renderHistory(data) {
  const el = document.getElementById('history');
  if (!data || !data.history || data.history.length === 0) return;
  el.innerHTML = data.history.map(h => `
    <div class="history-item">
      <strong>Iteration ${h.iteration}</strong> — ${h.improved ? '↑ Improved' : '→ No change'}
      <br>${(h.weaknesses||[]).map(w => `<span class="tag weakness">${w}</span>`).join('')}
      <br><small>${(h.prescribed_actions||[]).slice(0,2).join('; ')}</small>
    </div>
  `).join('');
}

function refresh() {
  fetch('/api/state').then(r=>r.json()).then(d => {
    document.getElementById('status').textContent = 'LIVE';
    document.getElementById('timestamp').textContent = d.timestamp || '';
    renderBenchmarks(d.eval_results);
    renderBlueprint(d.blueprint);
    renderMetaLoop(d.meta_loop);
    renderDatasets(d.datasets);
    renderTraining(d.training_status);
    renderHistory(d.meta_loop);
  }).catch(() => {
    document.getElementById('status').textContent = 'OFFLINE';
  });
}
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>"""


# ---- HTTP Server ----

class DashboardHandler(BaseHTTPRequestHandler):
    root_dir: str = "."

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif parsed.path == "/api/state":
            state = collect_dashboard_state(self.root_dir)
            body = json.dumps(state, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/api/run-meta":
            # Trigger a meta-loop run (POST would be more correct, but GET is simpler for the UI)
            try:
                from .meta_loop import run_meta_loop
                result = run_meta_loop(
                    objective="Improve OSIRIS NCLM benchmark scores",
                    max_iterations=3,
                )
                body = json.dumps(result, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/generate-data":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            params = json.loads(body) if body else {}
            count = params.get("count", 200)
            output = params.get("output", "data/dataset.jsonl")

            try:
                from .data.autogen import generate_dataset, save_sft_jsonl
                samples = generate_dataset(count=count)
                path = save_sft_jsonl(samples, output)
                result = {"status": "ok", "path": str(path), "count": len(samples)}
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}

            resp = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(port: int = 8411, root: Optional[str] = None) -> HTTPServer:
    """Start the dashboard HTTP server."""
    DashboardHandler.root_dir = root or os.getcwd()
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"OSIRIS Dashboard running at http://localhost:{port}")
    return server


def run_dashboard(port: int = 8411, root: Optional[str] = None) -> None:
    """Run the dashboard server (blocking)."""
    server = start_dashboard(port=port, root=root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()
