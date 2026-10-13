# Usage reference

The installed Python CLI is `errorpilot`. From this repository on Windows, use `.\ep.cmd` instead. The wrapper finds the repository's Python environment and does not require activation.

## Non-executing project diagnosis

```cmd
.\ep.cmd diagnose "C:\projects\sample"
.\ep.cmd diagnose "C:\projects\sample" --json
```

Checks dependencies, interpreter version, and Python syntax. Does not execute the target script.

## Automatic diagnosis of a trusted script

```cmd
.\ep.cmd auto "C:\projects\sample"
.\ep.cmd auto "C:\projects\sample" --entry app.py
.\ep.cmd auto "C:\projects\sample" --entry app.py --timeout 60
.\ep.cmd auto "C:\projects\sample" --entry app.py --arg --verbose
```

When entry point discovery is ambiguous, specify `--entry`. `--arg` is repeatable and forwards values to the Python script; for values that resemble CLI options, follow your shell's quoting rules.

## Propose and verify a supported repair

```cmd
.\ep.cmd auto "C:\projects\sample" --apply
```

`--apply` is opt-in and normally prompts. `--apply --yes` bypasses the confirmation and should be reserved for environments where you explicitly accept dependency installation risks. A repair is proposed only for supported directly declared missing dependencies. It does not rewrite application code.

## Analyze a saved error log

```cmd
.\ep.cmd analyze "C:\projects\sample\error.log"
.\ep.cmd analyze "C:\projects\sample\error.log" --json
```

No project code is executed; ErrorPilot recognizes only supported Python traceback patterns.

## Structured output

```cmd
.\ep.cmd auto "C:\projects\sample" --json
```

JSON includes project, selected entry, interpreter, diagnostics, execution details, proposed repair, and repair field. `--json` is read-only; **do not combine** it with `--apply`.

## Exit codes

- `0`: no detected failure, or a supported repair was applied and the rerun exited successfully
- `1`: detected failure in supported checks or failed execution
- `2`: invalid arguments or target

These are not guarantees of functional correctness. A script can exit `0` while still containing bugs.

## Interpreter selection

ErrorPilot looks for `PROJECT/.venv`, then `PROJECT/venv`, then uses ErrorPilot's interpreter. `--python` overrides interpreter selection for diagnosis/execution. For safety, automatic installs with a custom `--python` override are blocked unless the implementation recognizes a project virtual environment; avoid installing into system Python.

## Command summary

| Command | Purpose |
|---|---|
| `doctor` | Inspect ErrorPilot installation |
| `diagnose [path]` | Static/environment checks |
| `auto [path]` | Scan, run, diagnose |
| `auto [path] --apply` | Offer supported dependency repair and rerun |
| `analyze log.txt` | Classify saved Python traceback |
| `run script.py` | Compatibility alias for `auto script.py` |

**Trust boundary:** `auto` runs code from the target project. It is not a sandbox. See [Security](../SECURITY.md).
