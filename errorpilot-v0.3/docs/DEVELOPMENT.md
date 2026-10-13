# Development and testing

## Local setup

Windows CMD:

```cmd
.\setup.cmd
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

## Code layout

- `src/errorpilot/cli.py`: Typer command definitions, Rich formatting, JSON reports, approval and repair orchestration.
- `src/errorpilot/engine.py`: environment discovery, dependency inspection, syntax checks, subprocess execution, traceback analysis, and pip repair helpers.
- `tests/test_cli.py`: unit and CLI tests; simulated repair tests do not require real PyPI downloads.
- `examples/`: an intentionally broken dependency fixture.

## Testing changes

1. Add or update tests for the failure mode.
2. Run the complete suite on your local Python version.
3. Check that diagnosis-only paths do not mutate project files.
4. Verify that repairs still require explicit approval and target an isolated environment.
5. Test Windows CMD launcher changes on Windows; CI also tests Windows and Ubuntu.

## CI

The repository's `.github/workflows/tests.yml` runs pytest on Ubuntu and Windows using Python 3.11 and 3.13. The badges in the README do not claim a live workflow status before the repository is published.

## Release discipline

Document user-visible changes in `CHANGELOG.md`. Avoid describing roadmap features as implemented. Include a reproduction case and test when fixing bugs.
