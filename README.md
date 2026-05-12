# ezpaw

A lightweight job management interface for [GPAW](https://wiki.fysik.dtu.dk/gpaw/) — the DFT calculator. ezpaw wraps GPAW calculations with a PostgreSQL backend, a Flask web UI, and a CLI for running and tracking DFT jobs.

## Features

- **Flask web interface** — browse completed and in-progress runs, view gaps and convergence
- **CLI runner** — `ezpaw run <script.py>` executes any ASE/GPAW script and records results
- **PostgreSQL backend** — structured storage for run metadata and results
- **GPAW-aware** — ships `gpaw_runner.py` to handle GPAW's `LD_LIBRARY_PATH` and `PYTHONPATH` requirements
- **Systemd service** — `ezpaw-flask.service` for production deployment

## Requirements

- Python ≥ 3.10
- [GPAW](https://wiki.fysik.dtu.dk/gpaw/) (via `gpaw` pip package)
- ASE (`ase`)
- Flask
- PostgreSQL
- psycopg2 (`psycopg2-binary`)
- Python dotenv (`python-dotenv`)
- PyYAML (`pyyaml`)

## Installation

```bash
git clone https://github.com/<your-username>/ezpaw.git
cd ezpaw
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set `$PROJECT` in your environment to the ezpaw root directory (alternatively, edit `config.yaml` directly):

```bash
export PROJECT="$HOME/ezpaw"
```

Or per-session:

```bash
PROJECT="$HOME/ezpaw" ezpaw run my_script.py
```

## Configuration

Copy and edit the example files:

```bash
cp .env.example .env       # then edit: DB_PASSWORD=your_password
cp config.yaml.example config.yaml
```

Create the PostgreSQL database:

```bash
psql -c 'CREATE DATABASE ezpaw;'
```

## Usage

### CLI

```bash
ezpaw run my_gpaw_script.py --arg1 value1
```

### Web UI

```bash
ezpaw web
# or with PROJECT set:
PROJECT="$HOME/ezpaw" ezpaw web
```

Then open `http://127.0.0.1:5056` in your browser.

### Systemd service

```bash
cp systemd/ezpaw-flask.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ezpaw-flask
```

## Project Structure

```
ezpaw/
├── ezpaw/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py            # CLI entry point
│   ├── config.py         # Configuration loader
│   ├── database.py       # Database models and queries
│   ├── gpaw.py           # GPAW wrappers and gap calculations
│   ├── gpaw_runner.py     # GPAW subprocess runner
│   ├── schema.sql        # PostgreSQL schema
│   ├── web.py            # Flask routes and views
│   └── templates/        # HTML templates
├── systemd/
│   └── ezpaw-flask.service  # Systemd service file
├── tests/
│   └── test_si_bandgap.py
├── config.yaml.example
├── .env.example
├── setup.py
└── requirements.txt
```

## License

MIT License — see [LICENSE](LICENSE).
