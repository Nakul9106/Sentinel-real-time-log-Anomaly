import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "live_web.log"
ALERTS_FILE = DATA_DIR / "alerts.jsonl"
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"

if not VENV_PYTHON.exists():
    # Fallback for linux/mac if needed, though this is a windows env
    VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"

# Global state
processes = {}

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)
    if not ALERTS_FILE.exists():
        ALERTS_FILE.touch()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    generator_running = "generator" in processes and processes["generator"].poll() is None
    sentinel_running = "sentinel" in processes and processes["sentinel"].poll() is None
    return jsonify({
        "generator_running": generator_running,
        "sentinel_running": sentinel_running
    })

@app.route("/api/start", methods=["POST"])
def start_server():
    ensure_data_dir()
    
    # Clear old alerts so we don't spam the UI with historical data on restart
    open(ALERTS_FILE, 'w').close()

    # Start generator
    if "generator" not in processes or processes["generator"].poll() is not None:
        cmd_gen = [
            str(VENV_PYTHON),
            "-u",
            "scripts/generate_logs.py",
            "--mode", "mixed",
            "--out", str(LOG_FILE),
            "--live",
            "--rate", "5"
        ]
        processes["generator"] = subprocess.Popen(cmd_gen, cwd=str(BASE_DIR))
        logger.info("Started log generator.")

    # Start sentinel
    if "sentinel" not in processes or processes["sentinel"].poll() is not None:
        # Give generator a moment to create the log file
        time.sleep(1)
        cmd_sentinel = [
            str(VENV_PYTHON),
            "-u", "-m", "sentinel",
            "--model", "models/sentinel_model.joblib",
            "--log", str(LOG_FILE),
            "--dry-run",
            "--cooldown", "0",
            "--out-alerts", str(ALERTS_FILE)
        ]
        processes["sentinel"] = subprocess.Popen(cmd_sentinel, cwd=str(BASE_DIR))
        logger.info("Started sentinel anomaly detector.")

    return jsonify({"status": "started"})

@app.route("/api/stop", methods=["POST"])
def stop_server():
    for name in ["generator", "sentinel"]:
        if name in processes and processes[name].poll() is None:
            processes[name].terminate()
            try:
                processes[name].wait(timeout=3)
            except subprocess.TimeoutExpired:
                processes[name].kill()
            logger.info(f"Stopped {name}.")
    return jsonify({"status": "stopped"})

@app.route("/api/stream")
def stream():
    def event_stream():
        ensure_data_dir()
        with open(ALERTS_FILE, "r") as f:
            # Go to end of file
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                if not line.endswith('\n'):
                    # Partial line read, rewind and wait
                    f.seek(f.tell() - len(line))
                    time.sleep(0.1)
                    continue
                # We have a new complete alert line
                try:
                    payload = json.loads(line)
                    # Yield as SSE format
                    yield f"data: {json.dumps(payload)}\n\n"
                except Exception as e:
                    logger.error(f"Error parsing alert line: {e}")

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)
