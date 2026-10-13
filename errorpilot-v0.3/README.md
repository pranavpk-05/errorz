# ErrorPilot

**Diagnose Python project failures in one command. Repair supported missing dependencies with approval, then rerun to verify.**

[![Tests](https://img.shields.io/badge/tests-pytest-informational)](docs/DEVELOPMENT.md) [![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![Status](https://img.shields.io/badge/status-experimental-orange)](CHANGELOG.md)

ErrorPilot is a **free, local-first, deterministic** Python diagnostics CLI. It inspects a project's dependencies and syntax, runs a trusted entry script, explains recognized tracebacks, and can install **directly declared missing dependencies** in an isolated project environment after you approve. No AI model, API key, or paid service is required.

> **Scope:** v0.3 is **not** an autonomous code-fixing AI. It does **not** rewrite Python source code, repair logic bugs, or guarantee that an application works simply because it exits with status 0.

## Demo: detect → repair → verify

The repository includes `examples/main.py`, which imports the dependency `humanize` declared in `examples/requirements.txt`.

```text
$ ep.cmd auto examples
Project checks
  MISSING_DEPENDENCY humanize is not installed ...
Application run: exit 1
  ModuleNotFoundError: No module named 'humanize'
Runtime diagnosis
  MISSING_MODULE humanize

$ ep.cmd auto examples --apply
Proposed dependency repair: humanize==4.12.3
Create an isolated .venv and install the declared dependency? [y/N]: y
...
Verifying by rerunning the original script...
Verification passed: application exited with code 0.
Success: 12,000
```

*Illustrative output from the bundled example. If the package is already installed, the initial failure may not occur.*

## Quick start

### Windows — Command Prompt

Requirements: **Python 3.11+**, accessible via `py -3.11` or `python`.

```cmd
cd /d C:\path\to\errorpilot-v0.3
.\setup.cmd
.\ep.cmd doctor
.\ep.cmd auto examples
.\ep.cmd auto examples --apply
```

**Important:** Run these commands from the folder containing `setup.cmd` and `ep.cmd`, **not** the parent folder containing the extracted directory. `setup.cmd` sets up ErrorPilot's own `.venv`. `ep.cmd` launches ErrorPilot without activating the virtual environment.

### Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m errorpilot doctor
.venv/bin/python -m errorpilot auto examples
```

### Diagnose your own project

```cmd
.\ep.cmd diagnose C:\path\to\your-project
.\ep.cmd auto C:\path\to\your-project
.\ep.cmd auto C:\path\to\your-project --apply
```

`diagnose` does not execute the target application. `auto` **does** execute the target script: use it **only on trusted projects**. `--apply` asks before installing supported missing dependencies; `--apply --yes` explicitly skips confirmation.

## What it can do

| Capability | v0.3 behavior |
|---|---|
| Inspect `requirements.txt` and basic `pyproject.toml` dependencies | Supported for straightforward declarations |
| Detect missing / incompatible installed packages | Supported |
| Check Python version requirements | Supported |
| Detect local Python syntax errors | Supported |
| Find and run a likely entry script | Supported; use `--entry` when ambiguous |
| Recognize common Python traceback patterns | Supported, with limits |
| Install directly declared missing dependency | Supported **with approval** |
| Verify repair | Reruns script and checks exit status |
| Export diagnostics as JSON | Supported (`--json`; cannot combine with `--apply`) |
| Rewrite source code or fix logic bugs | **Not supported** |
| Use an LLM / Ollama | **Not implemented** |

## CLI reference

```text
errorpilot doctor
errorpilot diagnose [PROJECT] [--json] [--python PATH]
errorpilot analyze ERROR_LOG [--json]
errorpilot auto [PROJECT_OR_SCRIPT] [--entry FILE] [--python PATH]
                [--timeout SECONDS] [--arg VALUE ...]
                [--apply [--yes]] [--json]
errorpilot run SCRIPT [--apply]      # compatibility alias
```

On Windows use `.\ep.cmd` in place of `errorpilot` when working from the repository. The default execution timeout is **15 seconds** (configurable up to 300). `--json` cannot be combined with `--apply`. `--yes` requires `--apply`.

## How it works

```text
Project directory
    │
    ├─ Resolve Python interpreter (.venv → venv → ErrorPilot Python)
    ├─ Parse declared dependencies and check installed versions
    ├─ Check Python version constraints and syntax
    │
    └─ auto mode: execute trusted entry script
          │
          ├─ exit 0 → report observed success
          └─ failure → classify traceback
                         │
                         └─ matching declared missing dependency?
                               │
                               └─ --apply + approval
                                     ├─ create/select project virtualenv
                                     ├─ install declared package
                                     └─ rerun and report exit status
```

This tool uses rule-based analysis, **not AI inference**. For architecture and design constraints see [Architecture](docs/ARCHITECTURE.md).

## Documentation

- [Getting started](docs/GETTING_STARTED.md) — installation and first successful run
- [Usage and command examples](docs/USAGE.md) — real projects, logs, JSON, flags
- [Architecture and automation](docs/ARCHITECTURE.md) — internal modules and flow
- [Diagnostics and repair boundaries](docs/DIAGNOSTICS.md) — supported vs unsupported errors
- [Troubleshooting](docs/TROUBLESHOOTING.md) — common Windows and Python problems
- [Development and testing](docs/DEVELOPMENT.md) — tests and CI
- [Roadmap](ROADMAP.md) — future features, not yet implemented
- [Contributing](CONTRIBUTING.md) and [Security](SECURITY.md)

## Development

```cmd
.\setup.cmd
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
```

GitHub Actions runs tests on Windows and Ubuntu with Python 3.11 and 3.13. See [.github/workflows/tests.yml](.github/workflows/tests.yml).

## Safety and limitations

- **Not a sandbox.** `auto` executes target Python code, which may access the network or change files even without `--apply`.
- **No silent source edits.** v0.3 never automatically rewrites source files.
- **Third-party packages can execute code during installation.** Only approve dependencies you trust.
- **No full regression guarantee.** Exit code `0` is a narrow verification, not proof of correct behavior.
- Logs can contain secrets. Review terminal output and JSON before sharing.

See [SECURITY.md](SECURITY.md) for the full trust model.

## License

MIT — see [LICENSE](LICENSE). Contributions welcome: [CONTRIBUTING.md](CONTRIBUTING.md).
