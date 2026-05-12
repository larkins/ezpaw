# ezpaw — Agent Setup & Usage Guide

> **For AI agents**: This file contains everything you need to install, configure, and use the ezpaw environment on a fresh machine. Read it completely before touching any files.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Database Setup](#4-database-setup)
5. [Package Installation](#5-package-installation)
6. [GPAW Build from Source](#6-gpaw-build-from-source)
7. [Running the Flask Web UI](#7-running-the-flask-web-ui)
8. [Using ezpaw as a GPAW Wrapper](#8-using-ezpaw-as-a-gpaw-wrapper)
9. [The `ezpaw` Bash Command](#9-the-ezpaw-bash-command)
10. [Troubleshooting](#10-troubleshooting)
11. [Quick Reference](#11-quick-reference)

---

## 1. Overview

**ezpaw** is a thin wrapper around [GPAW](https://gpaw.readthedocs.io) that:

- Runs GPAW calculations exactly as normal from the command line
- Optionally streams output to a Flask web UI in real time
- Provides a Python API (`from ezpaw import ...`) for scripting workflows
- Stores results in a PostgreSQL database for later retrieval

If you are an AI agent working on this project for the first time on a new machine, read this file end to end before writing any code or running any commands.

---

## 2. Prerequisites

Install system dependencies:

```bash
sudo apt update
sudo apt install -y python3.11-venv python3-pip postgresql libfftw3-dev libgsl-dev libxc-dev
```

If you are on a GPU node with CUDA, also install:

```bash
sudo apt install -y nvidia-cuda-toolkit   # or use your cluster's CUDA module
```

Set the project root variable used throughout this guide:

```bash
export PROJECT="$HOME/ezpaw"
```

---

## 3. Installation

### Clone (or create) the project directory

```bash
git clone <repo-url> $PROJECT
cd $PROJECT
```

### Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **IMPORTANT**: Always activate the venv before running any `pip install`, `python`, or `ezpaw` commands in this project.

---

## 4. Database Setup

### Start PostgreSQL

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql   # optional: start on boot
```

### Create a database and user

```bash
sudo -u postgres psql -c "CREATE USER ezpaw WITH PASSWORD 'your_password_here';"
sudo -u postgres psql -c "CREATE DATABASE ezpaw OWNER ezpaw;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ezpaw TO ezpaw;"
```

### Set the database URL

Add to `$PROJECT/.env`:

```
DATABASE_URL=postgresql://ezpaw:your_password_here@localhost:5432/ezpaw
```

### Initialize the database schema

```bash
cd $PROJECT
source .venv/bin/activate
pip install -e .
psql "postgresql://ezpaw:your_password_here@localhost:5432/ezpaw" < schema.sql
```

---

## 5. Package Installation

```bash
cd $PROJECT
source .venv/bin/activate
pip install -e .
```

> If you plan to develop the Flask web UI, also run:
> ```bash
> pip install -e ".[dev]"
> ```

### Configure

Copy and edit the config:

```bash
cp config.yaml.example config.yaml
nano config.yaml   # or your editor of choice
```

Minimum required changes to `config.yaml`:

```yaml
database:
  host: localhost
  port: 5432
  name: ezpaw
  user: ezpaw
  password: your_password_here

flask:
  port: 5000

gpaw:
  bin: /path/to/gpaw   # or leave empty if GPAW_PYTHON is set
```

Add to `~/.bashrc` (or `.bashrc` at project root) — **append only, do not overwrite**:

```bash
# ezpaw — required for this project
export PROJECT="$HOME/ezpaw"
export PATH="$PROJECT/.venv/bin:$PATH"
export LD_LIBRARY_PATH="$PROJECT/.venv/lib:$LD_LIBRARY_PATH"
```

Then reload:

```bash
source ~/.bashrc
```

---

## 6. GPAW Build from Source

> Skip this section if GPAW is already installed system-wide or via conda.

### Install GPAW prerequisites

```bash
sudo apt install -y libfftw3-dev libgsl-dev libxc-dev
pip install ase
```

### Build and install GPAW

```bash
cd $PROJECT
source .venv/bin/activate
pip install --no-build-isolation gpaw
```

> **GPU users**: Set `CUDA_ARCH` before building:
> ```bash
> export CUDA_ARCH=12.0   # or your GPU's compute capability
> pip install --no-build-isolation gpaw
> ```

---

## 7. Running the Flask Web UI

### Install systemd user service (recommended)

```bash
mkdir -p ~/.config/systemd/user
cp $PROJECT/systemd/ezpaw-flask.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable ezpaw-flask
systemctl --user start ezpaw-flask
```

To edit the service file, it lives at:

```
~/.config/systemd/user/ezpaw-flask.service
```

### Alternative: run directly

```bash
cd $PROJECT
source .venv/bin/activate
python -m ezpaw.web
```

Or use the installed CLI:

```bash
ezpaw web
```

---

## 8. Using ezpaw as a GPAW Wrapper

### Run a single calculation

```bash
cd $PROJECT
source .venv/bin/activate

ezpaw run your_calculation.py
```

The output will be streamed to the Flask UI if it is running.

### Run with the web UI active in background

```bash
ezpaw web &
ezpaw run your_calculation.py
```

### Python API

```python
from ezpaw import GCA, submit_calculation

# Submit a calculation
job_id = submit_calculation(
    atoms=atoms,
    calculator="GPAW",
    mode={"name": "fd", "basis": "dzp"},
    kpts={"size": (4, 4, 4), "gamma": True},
)
```

### Check the database for past results

```bash
psql "postgresql://ezpaw:your_password_here@localhost:5432/ezpaw" \
  -c "SELECT id, status, created_at FROM calculations ORDER BY created_at DESC LIMIT 10;"
```

---

## 9. The `ezpaw` Bash Command

The `ezpaw` command is installed into the virtualenv and should be available once the venv is activated.

**Installation is automatic** — `pip install -e .` installs the `ezpaw` entry point script into `.venv/bin/`.

If the command is not found after installing, verify your `PATH` includes the venv:

```bash
echo $PATH | tr ':' '\n' | grep ezpaw   # should show the .venv/bin path
which ezpaw                            # should print the path to the script
```

**Agent must append to `~/.bashrc`** after installation to make `ezpaw` available in new shells:

```bash
# ezpaw — required for this project
export PROJECT="$HOME/ezpaw"
export PATH="$PROJECT/.venv/bin:$PATH"
export LD_LIBRARY_PATH="$PROJECT/.venv/lib:$LD_LIBRARY_PATH"
```

---

## 10. Troubleshooting

### `psql: could not connect to server`

PostgreSQL is not running:

```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

### `ERROR: relation "..." does not exist`

Schema not loaded:

```bash
psql "postgresql://ezpaw:your_password_here@localhost:5432/ezpaw" < $PROJECT/schema.sql
```

### `gpaw: command not found`

GPAW is not in PATH. Either set `GPAW_PYTHON` to point to the Python that has GPAW installed, or set the full path in `config.yaml`:

```bash
export GPAW_PYTHON="$PROJECT/.venv/bin/python"
```

### `ModuleNotFoundError: No module named 'ezpaw'`

Either:

- The package is not installed: `pip install -e .`
- The virtual environment is not activated: `source $PROJECT/.venv/bin/activate`

### Flask UI not loading

Check the service status:

```bash
systemctl --user status ezpaw-flask
journalctl --user -u ezpaw-flask -n 50
```

### Tests failing

```bash
cd $PROJECT
source .venv/bin/activate
ezpaw run tests/test_si_bandgap.py
```

Expected output:
```
Si band gap (DFT): 1.32 eV
Si band gap (GW):  1.94 eV
PASSED
```

---

## 11. Quick Reference

### Project structure

```
ezpaw/
├── ezpaw/              # Python package source
│   ├── __init__.py
│   ├── cli.py          # ezpaw CLI entry point
│   ├── gpaw_runner.py  # GPAW job runner
│   ├── web.py          # Flask web UI
│   └── db.py           # Database utilities
├── systemd/            # Systemd service files
├── tests/              # Test suite
├── logs/               # Log output directory
├── config.yaml         # Configuration (gitignored)
├── .env                # Secrets (gitignored)
├── schema.sql          # Database schema
├── install.sh          # Installation helper script
├── AGENTS.md           # This file
└── README.md           # User-facing documentation
```

### Common commands

| Task | Command |
|------|---------|
| Install package | `pip install -e .` |
| Run tests | `ezpaw run tests/test_si_bandgap.py` |
| Start web UI | `ezpaw web` |
| Stop web UI | `systemctl --user stop ezpaw-flask` |
| View logs | `journalctl --user -u ezpaw-flask -f` |

### Configuration files

| File | What goes in it | Secret? |
|------|-----------------|---------|
| `$PROJECT/config.yaml` | DB host/port/name, Flask port, GPAW paths | No |
| `$PROJECT/.env` | DB password | **Yes** |
| `$PROJECT/siteconfig.py` | GPAW build settings (LibXC paths) | No |
| `$PROJECT/install.sh` | Installation script | No |

---

*Last updated: auto-generated. For the ezpaw project.*
