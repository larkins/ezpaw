"""GPAW wrapper that logs every run to the ezpaw PostgreSQL database.

Usage in user scripts
---------------------
    from gpaw import GPAW   # ← gets our wrapper class

    calc = GPAW(xc='GLLB-SC', kpts=(6, 6, 6), txt='gs.out')
    atoms.calc = calc
    e = atoms.get_potential_energy()   # ← DB row created on init, updated here

The wrapper
-----------
1. ``__init__`` creates a gpaw_runs row (status='running').
2. ``get_potential_energy()`` calls the real GPAW, then extracts results.
3. ``get_potential_energy()`` also parses the GPAW text-output file for gap values.
4. Updates the DB row with finished_at, duration_seconds, results, status.
5. Re-raises so the caller's environment is unchanged.
"""

from __future__ import annotations

import gc
import os
import re
import sys
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from ezpaw import database as _db_module


# ---------------------------------------------------------------------------
# Result extraction helpers
# ---------------------------------------------------------------------------

def _extract_results(calc) -> dict[str, Any]:
    """Pull scalars from a completed GPAW calculator."""
    results = {}
    try:
        results["energy_eV"] = float(calc.get_potential_energy())
    except Exception:
        pass
    try:
        dft = calc.dft
        results["homo_lumo_gap_eV"] = float(dft.get_homo_lumo_gap())
    except Exception:
        pass
    try:
        results["total_energy_eV"] = float(dft.get_total_energy())
    except Exception:
        pass
    try:
        forces = dft.get_forces()
        if forces is not None:
            results["max_force_eV_ang"] = float(np.abs(forces).max())
    except Exception:
        pass
    try:
        bs = dft.band_structure()
        if bs is not None:
            results["band_structure_available"] = True
    except Exception:
        pass
    try:
        nelect = calc.get_number_of_electrons()
        results["n_electrons"] = int(nelect)
    except Exception:
        pass
    try:
        results["kpts"] = list(calc.get_k_point_distribution())
    except Exception:
        pass
    try:
        results["ecut_eV"] = float(calc.get_ecut())
    except Exception:
        pass
    return results


def _parse_txt_file(path: str | Path | None) -> dict[str, Any]:
    """Extract gap / discontinuity / energy values from a GPAW .txt file."""
    parsed = {}
    if not path or not os.path.exists(path):
        return parsed
    try:
        txt = Path(path).read_text()
    except Exception:
        return parsed

    # Kohn-Sham gap (e.g. "Kohn-Sham band gap: 0.71 eV")
    m = re.search(r"Kohn-Sham band gap:\s+([\d.]+)\s+eV", txt)
    if m:
        parsed["ks_gap_eV"] = float(m.group(1))

    # Fundamental / QP gap
    m = re.search(r"Fundamental band gap:\s+([\d.]+)\s+eV", txt)
    if m:
        parsed["qp_gap_eV"] = float(m.group(1))

    # GLLB-SC discontinuity
    m = re.search(r"Discontinuity from GLLB-SC:\s+([\d.]+)\s+eV", txt)
    if m:
        parsed["dxc_eV"] = float(m.group(1))

    # Total energy
    m = re.search(r"Total energy\s+=\s+([\d.\-eE+]+)", txt)
    if m:
        parsed["total_energy_txt_eV"] = float(m.group(1))

    return parsed


def _get_caller_script_name() -> str:
    """
    Walk up the call stack to find the outermost Python script that called
    run() or GPAW().  That script's resolved Path is returned.
    """
    import inspect
    for frame_info in reversed(inspect.stack()):
        path = frame_info.filename
        if path.startswith("<") or path == __file__:
            continue
        return Path(path).resolve().name
    return "unknown"


# ---------------------------------------------------------------------------
# GPAW wrapper class
# ---------------------------------------------------------------------------

class GPAW:
    """
    Thin wrapper around ``gpaw.GPAW`` that logs every run to PostgreSQL.

    Works with both ``calc.calculate(atoms)`` and
    ``atoms.get_potential_energy()`` entry points.
    """

    _real: type | None = None  # cached reference to the real gpaw.GPAW class

    def __init__(self, *args, script_name: str | None = None, **kwargs):
        """
        Parameters
        ----------
        script_name : str, optional
            Human-readable name for this calculation run.
            If omitted, the wrapper walks the call stack to find the caller's
            ``.py`` script filename and uses that.
        All remaining ``*args`` and ``**kwargs`` are passed 1:1 to the real
        ``gpaw.GPAW`` constructor.
        """
        # Lazily import the real GPAW class (only once per process).
        if GPAW._real is None:
            import gpaw as _real_mod
            GPAW._real = _real_mod.GPAW

        # Build the real calculator instance.
        self._wrapped = GPAW._real(*args, **kwargs)

        # Create a DB row immediately so the run is tracked even if the
        # script never calls calculate().
        self._run_id: int | None = None
        self._start_time: float = _time.time()
        self._txt_file: str | None = kwargs.get("txt", None)
        self._conn = None

        try:
            self._conn = _db_module.get_connection()
            name = script_name or _get_caller_script_name()
            result = _db_module.create_run(
                self._conn,
                script_name=name,
                arguments={"args": args, "kwargs": kwargs},
            )
            self._run_id = result["id"]
        except Exception as exc:
            print(f"[ezpaw warning] create_run failed: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    # get_potential_energy — the entry point ASE actually uses
    # ------------------------------------------------------------------

    def get_potential_energy(
        self, atoms=None, force_consistent=False
    ) -> float:
        """
        Call the wrapped calculator and log results to the DB.

        ASE's ``Atoms.get_potential_energy()`` calls this method directly,
        so this is the primary interception point.
        """
        txt_file = None
        try:
            # Let GPAW do its thing.
            energy = self._wrapped.get_potential_energy(
                atoms, force_consistent=force_consistent
            )
            duration = _time.time() - self._start_time
            results = _extract_results(self._wrapped)

            # Grab txt path from the kwargs or the txt attribute
            if self._txt_file:
                txt_file = os.path.abspath(
                    os.path.join(os.getcwd(), self._txt_file)
                )
            elif hasattr(self._wrapped, "txt") and self._wrapped.txt:
                txt_file = os.path.abspath(self._wrapped.txt)

            # Parse the text output for gap / discontinuity values
            if txt_file:
                results["_txt_file"] = txt_file
                txt_parsed = _parse_txt_file(txt_file)
                results.update(txt_parsed)

            # Write success to DB
            if self._run_id is not None:
                try:
                    _db_module.update_run(
                        self._conn,
                        self._run_id,
                        duration_seconds=duration,
                        status="success",
                        results=results,
                        stdout_path=txt_file,
                    )
                except Exception as exc:
                    print(f"[ezpaw warning] update_run failed: {exc}", file=sys.stderr)

            return energy

        except Exception as exc:
            # Log failure, then re-raise so caller sees the error.
            if self._run_id is not None:
                try:
                    _db_module.update_run(
                        self._conn,
                        self._run_id,
                        duration_seconds=_time.time() - self._start_time,
                        status="failed",
                        error_message=f"{type(exc).__name__}: {exc}",
                    )
                except Exception:
                    pass
            raise

    # ------------------------------------------------------------------
    # calculate — for direct calls (e.g. calc.calculate(atoms))
    # ------------------------------------------------------------------

    def calculate(self, atoms=None, *pargs, **pkwargs) -> None:
        """Run the calculation and write results to the DB."""
        txt_file = None
        try:
            self._wrapped.calculate(atoms, *pargs, **pkwargs)
            duration = _time.time() - self._start_time
            results = _extract_results(self._wrapped)

            if self._txt_file:
                txt_file = os.path.abspath(
                    os.path.join(os.getcwd(), self._txt_file)
                )
            elif hasattr(self._wrapped, "txt") and self._wrapped.txt:
                txt_file = os.path.abspath(self._wrapped.txt)

            if txt_file:
                results["_txt_file"] = txt_file
                txt_parsed = _parse_txt_file(txt_file)
                results.update(txt_parsed)

            if self._run_id is not None:
                try:
                    _db_module.update_run(
                        self._conn,
                        self._run_id,
                        duration_seconds=duration,
                        status="success",
                        results=results,
                        stdout_path=txt_file,
                    )
                except Exception as exc:
                    print(f"[ezpaw warning] update_run failed: {exc}", file=sys.stderr)

        except Exception as exc:
            if self._run_id is not None:
                try:
                    _db_module.update_run(
                        self._conn,
                        self._run_id,
                        duration_seconds=_time.time() - self._start_time,
                        status="failed",
                        error_message=f"{type(exc).__name__}: {exc}",
                    )
                except Exception:
                    pass
            raise

    # ------------------------------------------------------------------
    # Delegate everything else to the wrapped calculator
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Forward any attribute lookup to the wrapped calculator."""
        return getattr(self._wrapped, name)


# ---------------------------------------------------------------------------
# Convenience: run a script file
# ---------------------------------------------------------------------------

def run(script_path: str | Path, **kwargs) -> dict[str, Any]:
    """
    Run a Python script that uses GPAW, logging the whole execution to the DB.

    Parameters
    ----------
    script_path : str or Path
        Path to the ``.py`` script to execute.
    **kwargs
        Additional arguments forwarded to ``GPAW`` if a global ``calc`` variable
        is found in the script namespace (not yet implemented — reserved).

    Returns
    -------
    dict
        The merged results dict from the DB row.
    """
    import importlib.util

    script_path = Path(script_path).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    start_time = _time.time()
    orig_out = sys.stdout
    orig_err = sys.stderr
    out_path = script_path.with_suffix(".stdout")
    err_path = script_path.with_suffix(".stderr")

    _real_gpaw_mod = sys.modules.get("gpaw")
    run_id = None
    last_calc: GPAW | None = None
    conn = None

    try:
        # Capture stdout / stderr
        sys.stdout = open(out_path, "w", buffering=1)
        sys.stderr = open(err_path, "w", buffering=1)

        # Open a database connection and create the run row
        conn = _db_module.get_connection()
        result = _db_module.create_run(
            conn,
            script_name=script_path.name,
            arguments={"script": str(script_path)},
        )
        run_id = result["id"]

        # Execute the script in an isolated namespace
        ns: dict[str, Any] = {"__name__": "__ezpaw_script__"}
        spec = importlib.util.spec_from_file_location("__ezpaw_script__", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load spec for {script_path}")
        loader = importlib.util.Loader()
        exec(open(script_path).read(), ns)

        # Find the last GPAW calculator in the namespace
        for var in list(ns.keys()):
            val = ns.get(var)
            if isinstance(val, GPAW):
                last_calc = val

        duration = _time.time() - start_time

        results: dict[str, Any] = {}
        if last_calc is not None:
            results = _extract_results(last_calc._wrapped)
            txt = getattr(last_calc, "txt", None) or last_calc._wrapped.txt
            if txt:
                txt = os.path.abspath(os.path.join(os.getcwd(), str(txt)))
                results["_txt_file"] = txt
                results.update(_parse_txt_file(txt))

        _db_module.update_run(
            conn,
            run_id,
            duration_seconds=duration,
            status="success",
            results=results,
            stdout_path=str(out_path),
            stderr_path=str(err_path),
        )

        return results

    except Exception as exc:
        if run_id is not None:
            try:
                _db_module.update_run(
                    conn,
                    run_id,
                    duration_seconds=_time.time() - start_time,
                    status="failed",
                    error_message=f"{type(exc).__name__}: {exc}",
                    stdout_path=str(out_path),
                    stderr_path=str(err_path),
                )
            except Exception:
                pass
        raise

    finally:
        # Restore stdout / stderr and close capture files
        if sys.stdout is not orig_out:
            try:
                sys.stdout.flush()
                sys.stdout.close()
            except Exception:
                pass
            sys.stdout = orig_out
        if sys.stderr is not orig_err:
            try:
                sys.stderr.flush()
                sys.stderr.close()
            except Exception:
                pass
            sys.stderr = orig_err
        # Close the database connection
        if conn is not None:
            try:
                _db_module.close_connection(conn)
            except Exception:
                pass
