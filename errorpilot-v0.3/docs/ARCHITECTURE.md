# Architecture and execution pipeline

ErrorPilot v0.3 is a small deterministic Python CLI. It has no LLM dependency and no hosted backend.

## Repository structure

```text
errorpilot-v0.3/
├── src/errorpilot/
│   ├── __init__.py       # version
│   ├── __main__.py       # python -m errorpilot entry
│   ├── cli.py            # Typer commands, console/JSON output, repair approval
│   └── engine.py         # target resolution, checks, run, traceback analysis, installs
├── tests/test_cli.py     # pytest coverage
├── examples/             # intentionally broken demonstration
├── docs/                 # user and developer documentation
├── .github/              # CI and contribution templates
├── setup.cmd / ep.cmd    # Windows setup and launcher
└── pyproject.toml        # packaging and dependencies
```

## Execution stages

1. **Resolve target**: accept a Python file or directory, select a likely entry script (or `--entry`), select a Python interpreter.
2. **Static/environment checks**: parse straightforward dependency declarations, inspect installed distributions, validate interpreter constraints, compile-check local Python source.
3. **Execution (`auto` only)**: run the selected script with a timeout; capture stdout, stderr, and exit code. This runs user code, **not** in a sandbox.
4. **Traceback classification**: match recognized Python error patterns, report diagnostic codes and suggested actions.
5. **Repair planning**: only if a missing module can be tied to an explicitly declared direct dependency. Do not guess install names from arbitrary imports.
6. **Approval**: `--apply` enables the proposal; the user confirms unless `--yes` is also present.
7. **Repair**: use a project-local virtual environment and pip; avoid modifying arbitrary interpreters.
8. **Verification**: rerun the same entry script and check the exit status. A successful exit does not imply test-suite or business-logic correctness.

## Design decisions

- **Deterministic over speculative**: transparent diagnostic rules and explicit limitations.
- **Local-first**: no code upload, account, model, or remote inference service is required. Pip may access package indexes when installing.
- **Read-only default**: `diagnose` doesn't run the application. `auto` does run the application, and the application's own side effects are outside ErrorPilot's control.
- **Narrow repair surface**: opt-in dependency installation, not arbitrary source edits.
- **Structured output**: `--json` supports future CI and editor integrations without promising those integrations exist today.

## Threat model

ErrorPilot is **not** a secure execution boundary. Scripts and package installation may run arbitrary code. The timeout is not a guarantee that spawned child processes will be terminated. Treat unknown repositories and unreviewed packages as untrusted. See [Security](../SECURITY.md).
