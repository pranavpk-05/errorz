# Troubleshooting

## `'setup.cmd' is not recognized`

You are probably in the parent extracted folder. Find the launcher:

```cmd
dir /s /b setup.cmd
```

Then `cd /d` to the directory **containing** the file. For the distributed archive, the folder is typically `errorpilot-v0.3`:

```cmd
cd /d C:\Users\YOUR_USER\Downloads\errorpilot-v0.3-automated\errorpilot-v0.3
.\setup.cmd
```

Use the **actual** path printed by `dir`; don't assume the archive's outer and inner folders have the same name.

## `No suitable Python runtime found`

Install Python 3.11 or later, reopen CMD, and check:

```cmd
py --list
py -3.11 --version
```

If `py -3.11` is unavailable, use an installed compatible version. `setup.cmd` can also use `python` when available.

## `ModuleNotFoundError` when launching ErrorPilot

Run setup again from the repository folder:

```cmd
.\setup.cmd
.\ep.cmd doctor
```

## The example already succeeds

If `humanize` is installed in the interpreter selected for the example, there is nothing to repair. For a clean example, remove only the **example** virtual environment (`examples\.venv`) if you no longer need it, then rerun `auto examples`. Do not remove ErrorPilot's root `.venv` unless you intend to reinstall the tool.

## `NO_PROJECT_VENV` warning

ErrorPilot did not find `.venv` or `venv` inside the target project and fell back to its own interpreter. This is a warning, not necessarily a failure. Approved dependency repair can create a project-local environment.

## `No obvious entry script found`

Specify the startup script:

```cmd
.\ep.cmd auto C:\path\to\project --entry main.py
```

## `--json cannot be combined with --apply`

Run JSON diagnosis separately, then invoke interactive repair without `--json`.

## Repair not offered

ErrorPilot only proposes installing missing packages **directly declared** in supported dependency metadata. Other errors are diagnosed but not automatically patched.

## `Application run: exit 1` after repair

A second error may remain. Read the new traceback; repair verification is based on the rerun's exit status, not merely successful package installation.

## Script hangs or times out

Increase the run timeout for a trusted application, for example `--timeout 60` (maximum 300). ErrorPilot is intended for finite scripts; long-running web servers are not good candidates for exit-code verification.

## `Access is denied` / `.exe` launcher issues on Windows

Use the included `.\ep.cmd` wrapper rather than a generated `errorpilot.exe`. It launches `.venv\Scripts\python.exe -m errorpilot` directly.
