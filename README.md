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

### Quick install (recommended)

```bash
git clone https://github.com/larkins/ezpaw.git ~/ezpaw
cd ~/ezpaw
./install.sh
```

The installer sets up the venv, installs dependencies, creates the PostgreSQL database, loads the schema, configures `.env` and `config.yaml`, and appends shell environment variables to `~/.bashrc`. See `./install.sh --help` for options (e.g. `--skip-gpaw`, `--skip-db`, `--non-interactive`).

### Manual installation

If you prefer to install step by step, or if the installer doesn't cover your platform, follow the instructions in [AGENTS.md](AGENTS.md) (sections 2–6).

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
├── install.sh          # Automated installer
├── setup.py
└── requirements.txt
```

## Band Gap Terminology

ezpaw automatically extracts three band-gap–related values from GLLB-SC calculations and stores them in dedicated database columns:

| Column | Term | Description |
|--------|------|-------------|
| `ks_gap` | **Kohn-Sham band gap** | The eigenvalue gap between the highest occupied (HOMO) and lowest unoccupied (LUMO) Kohn-Sham orbital energies. This is the bare DFT gap **before** any derivative-discontinuity correction. For Si with GLLB-SC at odd k-points (≥7), expect ~0.7 eV. |
| `qp_gap` | **Fundamental (quasiparticle) band gap** | The physically observable band gap, computed as `QP_gap = KS_gap + DxC`. This accounts for the derivative discontinuity missing from plain Kohn-Sham eigenvalues. For Si with GLLB-SC at odd k-points, expect ~1.05 eV (close to the experimental ~1.17 eV). |
| `dxc` | **Exchange-correlation derivative discontinuity** | The GLLB-SC correction term that bridges the Kohn-Sham gap to the quasiparticle gap. It is computed via `response.calculate_discontinuity(dxc_pot)` and represents the derivative discontinuity of the exchange-correlation potential with respect to particle number. For Si with GLLB-SC, expect ~0.34 eV. |

These values are extracted automatically when the wrapped GPAW calculator uses an XC functional that supports the GLLB-SC discontinuity calculation (e.g. `xc='GLLBSC'`). For other functionals, these columns will be `NULL`.

## License

MIT License — see [LICENSE](LICENSE).
