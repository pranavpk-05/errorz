# Getting started

## Prerequisites

- Python 3.11 or newer
- Windows CMD (for the `.cmd` helpers), or Linux/macOS with a shell
- Internet access only when installing packages not already cached

## Windows: from ZIP to first diagnosis

1. Extract the ZIP. Open the **inner** `errorpilot-v0.3` folder in VS Code.
2. Open **Terminal → New Terminal → Command Prompt**.
3. Confirm the files are in the current folder: `dir setup.cmd ep.cmd pyproject.toml`.
4. Run:

```cmd
.\setup.cmd
.\ep.cmd doctor
.\ep.cmd auto examples
```

The example intentionally imports a dependency that may not be installed. To offer a repair:

```cmd
.\ep.cmd auto examples --apply
```

Approve the prompt only if you trust the dependency. ErrorPilot will create `examples\.venv` if necessary, install the declared package, and rerun `examples\main.py`.

## Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m errorpilot doctor
.venv/bin/python -m errorpilot auto examples
```

## First real project

Start with a **non-executing scan**:

```cmd
.\ep.cmd diagnose "C:\path\to\my-project"
```

Then, only for trusted projects:

```cmd
.\ep.cmd auto "C:\path\to\my-project" --entry main.py
```

Finally, to approve supported dependency installation:

```cmd
.\ep.cmd auto "C:\path\to\my-project" --entry main.py --apply
```

`--entry` is relative to the project directory. Projects that require environment variables, services, interactive input, or complex startup commands may need manual setup; ErrorPilot does not provision those automatically.

## Next steps

See [Usage](USAGE.md), [Diagnostics](DIAGNOSTICS.md), and [Troubleshooting](TROUBLESHOOTING.md).
