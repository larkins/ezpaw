"""Database operations for ezpaw."""
import json
import logging
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import Json

from ezpaw.config import get_database_config

logger = logging.getLogger(__name__)


def get_connection():
    """Create and return a database connection."""
    db_config = get_database_config()
    return psycopg2.connect(
        host=db_config.get("host", "localhost"),
        port=db_config.get("port", 5432),
        dbname=db_config.get("database", "ezpaw"),
        user=db_config.get("user", "postgres"),
        password=db_config.get("password", ""),
    )


def close_connection(conn):
    """Close a database connection."""
    conn.close()


def get_all_runs(limit=100):
    """Fetch all gpaw runs ordered by most recent first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, script_name, arguments, started_at, finished_at, "
                "duration_seconds, status, results, ks_gap, qp_gap, dxc, "
                "stdout_path, stderr_path, error_message "
                "FROM gpaw_runs ORDER BY started_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "script_name": r[1],
                    "arguments": r[2],
                    "started_at": r[3],
                    "finished_at": r[4],
                    "duration_seconds": r[5],
                    "status": r[6],
                    "results": r[7],
                    "ks_gap": r[8],
                    "qp_gap": r[9],
                    "dxc": r[10],
                    "stdout_path": r[11],
                    "stderr_path": r[12],
                    "error_message": r[13],
                }
                for r in rows
            ]


def get_run(run_id):
    """Fetch a single gpaw run by ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, script_name, arguments, started_at, finished_at, "
                "duration_seconds, status, results, ks_gap, qp_gap, dxc, "
                "stdout_path, stderr_path, error_message "
                "FROM gpaw_runs WHERE id = %s",
                (run_id,),
            )
            r = cur.fetchone()
            if r is None:
                return None
            return {
                "id": r[0],
                "script_name": r[1],
                "arguments": r[2],
                "started_at": r[3],
                "finished_at": r[4],
                "duration_seconds": r[5],
                "status": r[6],
                "results": r[7],
                "ks_gap": r[8],
                "qp_gap": r[9],
                "dxc": r[10],
                "stdout_path": r[11],
                "stderr_path": r[12],
                "error_message": r[13],
            }


def create_run(conn, script_name, arguments=None):
    """Insert a new run record and return the run dict (id only)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO gpaw_runs (script_name, arguments, started_at) "
            "VALUES (%s, %s, %s) RETURNING id",
            (script_name, Json(arguments), datetime.now(timezone.utc)),
        )
        run_id = cur.fetchone()[0]
        conn.commit()
        return {"id": run_id, "script_name": script_name}


def update_run(conn, run_id, status=None, duration_seconds=None, results=None,
               ks_gap=None, qp_gap=None, dxc=None,
               stdout_path=None, stderr_path=None, error_message=None):
    """Update an existing run record."""
    fields = []
    values = []
    if status is not None:
        fields.append("status = %s")
        values.append(status)
    if duration_seconds is not None:
        fields.append("duration_seconds = %s")
        values.append(duration_seconds)
    if results is not None:
        fields.append("results = %s")
        values.append(Json(results))
    if ks_gap is not None:
        fields.append("ks_gap = %s")
        values.append(ks_gap)
    if qp_gap is not None:
        fields.append("qp_gap = %s")
        values.append(qp_gap)
    if dxc is not None:
        fields.append("dxc = %s")
        values.append(dxc)
    if stdout_path is not None:
        fields.append("stdout_path = %s")
        values.append(stdout_path)
    if stderr_path is not None:
        fields.append("stderr_path = %s")
        values.append(stderr_path)
    if error_message is not None:
        fields.append("error_message = %s")
        values.append(error_message)

    if fields:
        fields.append("finished_at = %s")
        values.append(datetime.now(timezone.utc))
        values.append(run_id)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE gpaw_runs SET {', '.join(fields)} WHERE id = %s",
                values,
            )
            conn.commit()


def save_run(script_name, arguments=None, started_at=None, finished_at=None,
             duration_seconds=None, status=None, results=None,
             ks_gap=None, qp_gap=None, dxc=None,
             stdout_path=None, stderr_path=None, error_message=None):
    """Insert a completed run in one call (for backward compatibility)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO gpaw_runs
                (script_name, arguments, started_at, finished_at, duration_seconds,
                 status, results, ks_gap, qp_gap, dxc,
                 stdout_path, stderr_path, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (script_name, Json(arguments), started_at, finished_at,
                 duration_seconds, status, Json(results),
                 ks_gap, qp_gap, dxc,
                 stdout_path, stderr_path, error_message),
            )
            run_id = cur.fetchone()[0]
            conn.commit()
            return run_id
