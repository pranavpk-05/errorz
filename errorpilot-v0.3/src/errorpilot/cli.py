"""ErrorPilot command-line interface."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from . import __version__
from .engine import (Target, resolve_target, diagnose as collect_diagnostics, syntax_check,
                     analyze_log, run_script, repair_plan, create_venv, install_packages)

app = typer.Typer(help='ErrorPilot: fast offline Python diagnostics, with optional approved repairs.', no_args_is_help=True,
                  add_completion=False)
console = Console()


def show_findings(findings: list[dict], *, heading: str | None = None) -> None:
    if heading:
        console.print(f'\n[bold]{heading}[/bold]')
    colors = {'error': 'red', 'warning': 'yellow', 'info': 'cyan'}
    for f in findings:
        console.print(Text.assemble(("  " + f["code"], colors.get(f["severity"], "white")), " " + f["message"]))
        console.print(f'      Suggestion: {f["suggestion"]}', style='dim')
    if not findings:
        console.print('  [green]No issues found by the supported checks.[/green]')


def validate_target(path: Path, entry: str | None, python: Path | None) -> Target:
    try:
        return resolve_target(path, entry=entry, python=python)
    except ValueError as exc:
        Console(stderr=True).print(f'[red]{exc}[/red]')
        raise typer.Exit(code=2) from exc


def collect(target: Target, with_syntax: bool = True) -> list[dict]:
    return collect_diagnostics(target) + (syntax_check(target.root) if with_syntax else [])


@app.command('doctor')
def doctor() -> None:
    """Verify that ErrorPilot's installation and Python environment are usable."""
    console.print(Panel.fit(f'[bold cyan]ErrorPilot {__version__}[/bold cyan]\nPython: {sys.executable}\nVersion: {sys.version.split()[0]}\nCLI: ready'))


@app.command('diagnose')
def diagnose(path: Path = typer.Argument(Path('.'), help='Python project directory'),
             json_output: bool = typer.Option(False, '--json', help='Output JSON for automation'),
             python: Path | None = typer.Option(None, '--python', help='Target Python interpreter')) -> None:
    """Inspect dependencies, interpreter versions and Python syntax without running the app."""
    target = validate_target(path, None, python)
    findings = collect(target)
    result = {'root': str(target.root), 'interpreter': str(target.python), 'findings': findings}
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        console.print(f'[bold cyan]ErrorPilot {__version__}[/bold cyan] — {target.root}')
        console.print(f'[dim]Inspecting Python: {target.python}[/dim]')
        show_findings(findings)
    if any(f['severity'] == 'error' for f in findings):
        raise typer.Exit(code=1)


@app.command('analyze')
def analyze(log_file: Path = typer.Argument(..., help='Saved Python error output'),
            json_output: bool = typer.Option(False, '--json')) -> None:
    """Analyze an existing Python traceback without executing anything."""
    if not log_file.is_file():
        Console(stderr=True).print('[red]Log file does not exist[/red]')
        raise typer.Exit(code=2)
    findings = analyze_log(log_file.read_text(encoding='utf-8', errors='replace'))
    if json_output:
        print(json.dumps({'findings': findings}, indent=2))
    else:
        show_findings(findings, heading='Traceback analysis')


@app.command('auto')
def auto(path: Path = typer.Argument(Path('.'), help='Project directory or Python script'),
         entry: str | None = typer.Option(None, '--entry', help='Script to run relative to project root'),
         python: Path | None = typer.Option(None, '--python', help='Run using this interpreter'),
         timeout: int = typer.Option(15, '--timeout', min=1, max=300, help='Run limit in seconds'),
         apply: bool = typer.Option(False, '--apply', help='Offer repairs to declared missing dependencies'),
         yes: bool = typer.Option(False, '--yes', help='Approve --apply without interactive confirmation'),
         json_output: bool = typer.Option(False, '--json', help='Print structured JSON'),
         arg: list[str] | None = typer.Option(None, '--arg', help='Script argument (repeatable)')) -> None:
    """One-stop project scan, optional app execution, failure analysis, and approved repair."""
    if yes and not apply:
        Console(stderr=True).print('[red]--yes requires --apply.[/red]')
        raise typer.Exit(code=2)
    if json_output and apply:
        Console(stderr=True).print('[red]--json cannot be combined with --apply. Run a diagnosis first.[/red]')
        raise typer.Exit(code=2)
    target = validate_target(path, entry, python)
    findings = collect(target)
    # Avoid running a script with invalid syntax in the script itself.
    syntax_errors = [f for f in findings if f['code'] == 'SYNTAX_ERROR' and target.script is not None and Path(f.get('file', '')) == target.script.relative_to(target.root)]
    execution = None
    if target.script and not syntax_errors:
        execution = run_script(target.script, target.python, timeout=timeout, args=arg or [])
    plan = repair_plan(target.root, execution['findings']) if execution else []
    report = {'project': str(target.root), 'entry': str(target.script) if target.script else None,
              'interpreter': str(target.python), 'diagnostics': findings, 'execution': execution,
              'proposed_repair': plan, 'repair': None}
    if json_output:
        print(json.dumps(report, indent=2))
        if any(f['severity'] == 'error' for f in findings) or (execution and execution['returncode'] != 0):
            raise typer.Exit(code=1)
        return

    console.print(f'[bold cyan]ErrorPilot {__version__}[/bold cyan] — {target.root}')
    console.print(f'[dim]Python: {target.python}[/dim]')
    show_findings(findings, heading='Project checks')
    if execution:
        console.print(f'\n[bold]Application run:[/bold] exit {execution["returncode"]}')
        if execution['stdout']:
            console.print(execution['stdout'])
        if execution['stderr']:
            console.print(execution['stderr'], style='dim')
        show_findings(execution['findings'], heading='Runtime diagnosis')
        if execution['returncode'] != 0 and not execution['findings']:
            console.print('[yellow]The program failed, but no supported traceback pattern was detected.[/yellow]')
    elif target.script is None:
        console.print('\n[yellow]No obvious entry script found. Static diagnostics completed.[/yellow]')
        console.print('[dim]Use --entry filename.py to select the script to run.[/dim]')
    else:
        console.print('[yellow]Skipped running the script because it has a syntax error.[/yellow]')

    verified_repair = False
    if apply and execution and execution['returncode'] != 0:
        if not plan:
            console.print('[yellow]No supported automatic repair. No changes made.[/yellow]')
        else:
            console.print(f'\n[bold]Proposed dependency repair:[/bold] {", ".join(plan)}')
            console.print('Only directly declared missing packages are eligible. Installing packages can execute third-party code.')
            if python is not None and not target.project_venv:
                # Explicit interpreter override is considered user controlled, but avoid corrupting arbitrary runtimes.
                console.print('[red]Refusing installs with --python override. Select a project .venv instead.[/red]')
            elif not (target.root / '.venv').is_dir() and not (target.root / 'venv').is_dir():
                approved = yes or typer.confirm('Create an isolated .venv and install the declared dependency?', default=False)
                if approved:
                    try:
                        project_python = create_venv(target.root, target.python)
                    except Exception as exc:
                        console.print(f'[red]Could not create .venv: {exc}[/red]')
                    else:
                        verified_repair = _apply_and_verify(project_python, plan, target, timeout, arg or [])
                else:
                    console.print('Repair declined. No changes made.')
            else:
                approved = yes or typer.confirm(f'Install into {target.python}?', default=False)
                if approved:
                    verified_repair = _apply_and_verify(target.python, plan, target, timeout, arg or [])
                else:
                    console.print('Repair declined. No changes made.')

    # Successful execution takes precedence over static dependency errors only if they concern the same selected interpreter.
    if (execution and execution['returncode'] != 0 and not verified_repair) or (not execution and any(f['severity'] == 'error' for f in findings)):
        raise typer.Exit(code=1)


def _apply_and_verify(python: Path, specs: list[str], target: Target, timeout: int, args: list[str]) -> bool:
    console.print(f'[bold]Installing with {python}[/bold]')
    install = install_packages(python, specs)
    console.print(install['output'])
    if install['returncode'] != 0:
        console.print('[red]Installation failed. No fix was verified.[/red]')
        return False
    console.print('[bold]Verifying by rerunning the original script...[/bold]')
    verification = run_script(target.script, python, timeout=timeout, args=args)
    if verification['returncode'] == 0:
        console.print('[green]Verification passed: application exited with code 0.[/green]')
    else:
        console.print(f'[yellow]Still failing (exit {verification["returncode"]}). Another issue remains.[/yellow]')
        show_findings(verification['findings'], heading='Remaining errors')
    if verification['stdout']:
        console.print(verification['stdout'])
    if verification['stderr']:
        console.print(verification['stderr'], style='dim')
    return verification['returncode'] == 0


@app.command('run')
def run_compat(script: Path = typer.Argument(...),
               timeout: int = typer.Option(15, '--timeout', min=1, max=300),
               apply: bool = typer.Option(False, '--apply'),
               yes: bool = typer.Option(False, '--yes'),
               json_output: bool = typer.Option(False, '--json')) -> None:
    """Compatibility alias for older v0.2 run commands."""
    auto(script, entry=None, python=None, timeout=timeout, apply=apply, yes=yes, json_output=json_output, arg=[])


def main():
    app()
