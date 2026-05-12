"""Flask web UI for ezpaw."""
import json
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from ezpaw import database
from ezpaw.config import get_app_config, get_ezpaw_config

app = Flask(__name__)


def create_app():
    """Create and configure the Flask app."""
    app_config = get_app_config()
    ezpaw_config = get_ezpaw_config()

    app.config["SECRET_KEY"] = app_config.get("secret_key", "dev-secret-key")
    app.config["JSON_SORT_KEYS"] = False

    return app


@app.route("/")
def index():
    """Show table of all gpaw_runs."""
    runs = database.get_all_runs(limit=100)
    for run in runs:
        if run.get("started_at"):
            run["started_at"] = run["started_at"].isoformat() if isinstance(run["started_at"], datetime) else run["started_at"]
        if run.get("results"):
            run["results_json"] = json.dumps(run["results"], indent=2)
    return render_template("index.html", runs=runs)


@app.route("/run/<int:run_id>")
def run_detail(run_id):
    """Show detail page for a single run."""
    run = database.get_run(run_id)
    if run is None:
        return "Run not found", 404

    if run.get("started_at"):
        run["started_at"] = run["started_at"].isoformat() if isinstance(run["started_at"], datetime) else run["started_at"]
    if run.get("ended_at"):
        run["ended_at"] = run["ended_at"].isoformat() if isinstance(run["ended_at"], datetime) else run["ended_at"]
    if run.get("arguments"):
        run["arguments_json"] = json.dumps(run["arguments"], indent=2)
    if run.get("results"):
        run["results_json"] = json.dumps(run["results"], indent=2)

    return render_template("run_detail.html", run=run)


@app.route("/runs.json")
def runs_json():
    """Return all runs as JSON."""
    runs = database.get_all_runs(limit=100)
    for run in runs:
        if run.get("started_at") and isinstance(run["started_at"], datetime):
            run["started_at"] = run["started_at"].isoformat()
    return jsonify(runs)


if __name__ == "__main__":
    app_config = get_app_config()
    create_app()
    app.run(
        host=app_config.get("host", "127.0.0.1"),
        port=app_config.get("port", 5000),
        debug=True,
    )