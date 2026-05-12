"""CLI entry point for ezpaw."""
import os
import re
import subprocess
import sys
import time

from ezpaw import database
from ezpaw.config import BASE_DIR, get_ezpaw_config, get_gpaw_config


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: ezpaw <command> [args]")
        print("Commands: run, web, init-db, runs")
        sys.exit(1)

    command = sys.argv[1]

    if command == "run":
        run_script()
    elif command == "web":
        run_web()
    elif command == "init-db":
        init_db()
    elif command == "runs":
        list_runs()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: run, web, init-db, runs")
        sys.exit(1)


def run_script():
    """Run a Python script with GPAW logging."""
    if len(sys.argv) < 3:
        print("Usage: ezpaw run <script.py>")
        sys.exit(1)

    script_path = sys.argv[2]
    if not os.path.isabs(script_path):
        script_path = os.path.abspath(script_path)

    if not os.path.exists(script_path):
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)

    ezpaw_cfg = get_ezpaw_config()
    gpaw_cfg = get_gpaw_config()
    python_bin = BASE_DIR / ".venv/bin/python3"

    db = database.get_connection()
    run = database.create_run(db, script_name=script_path)

    log_dir = BASE_DIR / ezpaw_cfg.get("log_dir", "logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"gpaw_{os.path.basename(script_path)}.out"

    env = os.environ.copy()
    ld_library_path = gpaw_cfg.get("ld_library_path", "")
    if ld_library_path:
        env["LD_LIBRARY_PATH"] = ld_library_path

    print(f"Starting run {run['id']} — log: {log_file}")

    start = time.time()
    try:
        with open(log_file, "w") as log:
            result = subprocess.run(
                [str(python_bin), "-m", "ezpaw.gpaw_runner", script_path],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
            )

        duration = time.time() - start
        status = "success" if result.returncode == 0 else "failed"
        results = parse_log_for_results(log_file) if result.returncode == 0 else None
        database.update_run(db, run["id"], status=status, duration_seconds=duration, results=results)

        print(f"Run {run['id']} {status} ({duration:.2f}s, exit {result.returncode})")
    except Exception as e:
        print(f"Error running script: {e}")
        database.update_run(db, run["id"], status="failed")
        sys.exit(1)


    finally:
        database.close_connection(db)

def parse_log_for_results(log_file):
    """Parse key=value lines from a GPAW log file.

    Looks for lines matching 'Label:  value  unit' and returns a dict.
    """
    results = {}
    try:
        with open(log_file) as f:
            for line in f:
                line = line.rstrip()
                # Match "Label:  value  unit" patterns
                m = re.match(r"^([A-Za-z][A-Za-z\s\-]*?):\s*([\d.]+)\s*(\S+)?$", line)
                if m:
                    key = m.group(1).strip().replace(" ", "_")
                    value = float(m.group(2))
                    unit = m.group(3) if m.group(3) else None
                    if unit:
                        results[key] = {"value": value, "unit": unit}
                    else:
                        results[key] = value
    except Exception:
        pass
    return results if results else None


def run_web():
    """Run the web interface."""
    print("Web interface not yet implemented")
    sys.exit(1)


def init_db():
    """Initialize the database."""
    try:
        database.init_db()
        print("Database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)


def list_runs():
    """List all runs."""
    try:
        runs = database.get_all_runs()
        print(f"{'ID':<6} {'Script':<30} {'Status':<10} {'Duration':<12} {'Started'}")
        print("-" * 80)
        for run in runs:
            duration = f"{run['duration_seconds']:.2f}s" if run.get("duration_seconds") else "N/A"
            started = run["started_at"].isoformat() if run.get("started_at") else "N/A"
            status = run.get("status", "unknown")
            print(f"{run['id']:<6} {run['script_name']:<30} {status:<10} {duration:<12} {started}")
    except Exception as e:
        print(f"Error listing runs: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
