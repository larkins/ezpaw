# Contributing to ezpaw

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/<your-username>/ezpaw.git
cd ezpaw
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # install with dev dependencies if available
pip install gpaw ase flask psycopg2-binary python-dotenv pyyaml pytest
```

## Running Tests

```bash
# Run via the ezpaw CLI
ezpaw run tests/test_si_bandgap.py

# Or directly with pytest
pytest tests/
```

## Code Style

- Python ≥ 3.10
- Follow [PEP 8](https://pep8.org/)
- Use type hints where practical
- Max line length: 88 characters (Black default)

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Run `ezpaw run tests/test_si_bandgap.py` to verify nothing is broken
5. Commit with a clear message: `git commit -m "Add feature X"`
6. Push and open a Pull Request

## Reporting Issues

Please report issues on the [GitHub issue tracker](https://github.com/<your-username>/ezpaw/issues) with:

- Python version
- GPAW version
- Steps to reproduce
- Expected vs actual behavior
