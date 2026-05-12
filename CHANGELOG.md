# Changelog

All notable changes to ezpaw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2025-05-12

### Added
- Initial release
- `ezpaw run` — execute GPAW scripts and record results to database
- `ezpaw web` — Flask web UI at http://127.0.0.1:5056
- `/runs.json` — JSON API endpoint for run data
- PostgreSQL and SQLite database backends
- `ezpaw-flask.service` — systemd service for production deployment
- `gpaw_runner.py` — GPAW subprocess runner with correct `LD_LIBRARY_PATH`
- `AGENTS.md` — developer setup and deployment guide
- `test_si_bandgap.py` — integration test (Si bandgap DFT calculation)
