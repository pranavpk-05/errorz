"""Offline, evidence-based Python diagnostics. Does not modify user projects."""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

SKIP_DIRS = {'.venv', 'venv', '.git', '__pycache__', 'node_modules', '.tox', '.mypy_cache', '.pytest_cache', 'dist', 'build'}
ENTRY_CANDIDATES = ('app.py', 'main.py', '__main__.py', 'run.py')
NORMALIZE = lambda x: re.sub(r'[-_.]+', '-', x).lower()


@dataclass(frozen=True)
class Target:
    root: Path
    script: Path | None
    python: Path
    project_venv: bool


def python_in_venv(folder: Path) -> Path:
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def select_python(root: Path, override: Path | None = None) -> tuple[Path, bool]:
    if override is not None:
        path = override.expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'Python interpreter does not exist: {path}')
        return path, False
    for folder in (root / '.venv', root / 'venv'):
        path = python_in_venv(folder)
        if path.is_file():
            return path.resolve(), True
    # Fallback uses the environment ErrorPilot was installed into.
    return Path(sys.executable).resolve(), False


def resolve_target(path: Path, entry: str | None = None, python: Path | None = None) -> Target:
    path = path.expanduser().resolve()
    if path.is_file():
        if path.suffix.lower() != '.py':
            raise ValueError('The selected file must be a .py script')
        root, script = path.parent, path
    elif path.is_dir():
        root = path
        if entry:
            script = (root / entry).resolve()
            if not script.is_relative_to(root) or not script.is_file() or script.suffix.lower() != '.py':
                raise ValueError('--entry must name an existing .py file inside the project')
        else:
            candidates = [root / name for name in ENTRY_CANDIDATES if (root / name).is_file()]
            if len(candidates) > 1:
                raise ValueError('More than one possible entry point found: ' + ', '.join(p.name for p in candidates) + '. Use --entry.')
            script = candidates[0] if candidates else None
    else:
        raise ValueError(f'Project path does not exist: {path}')
    py, local = select_python(root, python)
    return Target(root=root, script=script, python=py, project_venv=local)


def _requirements(root: Path) -> tuple[list[Requirement], list[dict]]:
    raw: list[str] = []
    findings: list[dict] = []
    req_file = root / 'requirements.txt'
    if req_file.is_file():
        try:
            for line_no, line in enumerate(req_file.read_text(encoding='utf-8-sig').splitlines(), 1):
                value = line.split(' #', 1)[0].strip()
                if not value or value.startswith('#'):
                    continue
                if value.startswith(('-r', '--requirement', '-c', '--constraint', '-e', 'git+', 'http:', 'https:', '.')):
                    findings.append(_finding('warning', 'UNSUPPORTED_REQUIREMENT', f'{req_file.name}:{line_no}: {value}', 'This requirement form is not checked or auto-installed.'))
                    continue
                raw.append(value)
        except OSError as exc:
            findings.append(_finding('error', 'READ_ERROR', str(exc), 'Check file permissions.'))
    pyproject = root / 'pyproject.toml'
    if pyproject.is_file():
        try:
            obj = tomllib.loads(pyproject.read_text(encoding='utf-8-sig'))
            raw.extend(obj.get('project', {}).get('dependencies', []))
        except (OSError, ValueError, TypeError) as exc:
            findings.append(_finding('error', 'INVALID_PYPROJECT', str(exc), 'Check pyproject.toml syntax and project metadata.'))
    parsed: list[Requirement] = []
    for value in raw:
        try:
            req = Requirement(value)
            if req.url:
                findings.append(_finding('warning', 'UNSUPPORTED_REQUIREMENT', value, 'Direct URL dependencies require manual inspection.'))
                continue
            if req.marker and not req.marker.evaluate():
                continue
            parsed.append(req)
        except (ValueError, TypeError) as exc:
            findings.append(_finding('warning', 'UNSUPPORTED_REQUIREMENT', f'{value}: {exc}', 'Review the requirement syntax.'))
    return parsed, findings


def declared_requirements(root: Path) -> dict[str, str]:
    parsed, _ = _requirements(root)
    return {NORMALIZE(req.name): str(req) for req in parsed if not req.extras}


def _finding(severity: str, code: str, message: str, suggestion: str, **extra) -> dict:
    return {'severity': severity, 'code': code, 'message': message, 'suggestion': suggestion, **extra}


def interpreter_info(python: Path, timeout: int = 8) -> dict:
    """Use the chosen interpreter, not ErrorPilot's package environment."""
    code = ('import json, sys, importlib.metadata as m; '
            'print(json.dumps({"version":list(sys.version_info[:3]), '
            '"packages":{d.metadata.get("Name", "").lower().replace("_","-").replace(".","-"):d.version for d in m.distributions() if d.metadata.get("Name")}}))')
    try:
        result = subprocess.run([str(python), '-I', '-c', code], capture_output=True, text=True,
                                errors='replace', timeout=timeout, stdin=subprocess.DEVNULL, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'Unable to inspect interpreter {python}: {exc}') from exc
    if result.returncode != 0:
        raise ValueError(f'Python interpreter failed inspection: {result.stderr.strip()[:300]}')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError('Python interpreter returned invalid package metadata') from exc


def diagnose(target: Target) -> list[dict]:
    findings: list[dict] = []
    dependencies, parse_findings = _requirements(target.root)
    findings.extend(parse_findings)
    if not (target.root / 'requirements.txt').is_file() and not (target.root / 'pyproject.toml').is_file():
        findings.append(_finding('info', 'NO_MANIFEST', 'No requirements.txt or pyproject.toml found.', 'Add a dependency manifest or select the actual project root.'))
    if not target.project_venv:
        findings.append(_finding('info', 'NO_PROJECT_VENV', f'No project-local virtual environment selected; using {target.python}', 'Create a project .venv for isolated package installations.'))
    try:
        data = interpreter_info(target.python)
    except ValueError as exc:
        findings.append(_finding('error', 'PYTHON_INSPECTION_FAILED', str(exc), 'Check interpreter path or use --python.'))
        return findings
    version = '.'.join(map(str, data['version']))
    manifest = target.root / 'pyproject.toml'
    if manifest.is_file():
        try:
            constraint = tomllib.loads(manifest.read_text(encoding='utf-8-sig')).get('project', {}).get('requires-python')
            if constraint and not SpecifierSet(constraint).contains(version):
                findings.append(_finding('error', 'PYTHON_VERSION', f'Python {version} does not satisfy {constraint}.', 'Select a compatible Python version using --python.'))
        except (ValueError, TypeError, OSError):
            pass  # parse error already reported above
    packages = {NORMALIZE(name): ver for name, ver in data['packages'].items()}
    for req in dependencies:
        name = NORMALIZE(req.name)
        installed = packages.get(name)
        if not installed:
            findings.append(_finding('error', 'MISSING_DEPENDENCY', f'{req.name} is not installed in {target.python}', f'Install {req} in the selected project environment.', package=req.name))
        elif req.specifier and not req.specifier.contains(installed, prereleases=True):
            findings.append(_finding('error', 'VERSION_MISMATCH', f'{req.name} {installed} does not satisfy {req.specifier}', f'Resolve the package version in the project environment.', package=req.name))
    return findings


def syntax_check(root: Path, limit: int = 250) -> list[dict]:
    """Parse up to limit local Python files; never execute or alter code."""
    findings: list[dict] = []
    examined = 0
    for folder, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith('.')]
        for filename in files:
            if not filename.endswith('.py'):
                continue
            path = Path(folder) / filename
            examined += 1
            if examined > limit:
                findings.append(_finding('warning', 'SCAN_LIMIT', f'Scanned only the first {limit} Python files.', 'Increase coverage in a future release.'))
                return findings
            try:
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            except (SyntaxError, IndentationError) as exc:
                findings.append(_finding('error', 'SYNTAX_ERROR', f'{path.relative_to(root)}:{exc.lineno}:{exc.offset}: {exc.msg}', 'Correct the indicated Python syntax.', file=str(path.relative_to(root)), line=exc.lineno))
            except (UnicodeError, OSError) as exc:
                findings.append(_finding('warning', 'READ_ERROR', f'{path.relative_to(root)}: {exc}', 'Check the file encoding or permissions.'))
    return findings


def analyze_log(text: str) -> list[dict]:
    """Find the final exception and its likely fix; no LLM guessing."""
    rules = [
        (r'ModuleNotFoundError: No module named [\'\"]([^\'\"]+)', 'MISSING_MODULE', 'The chosen Python interpreter cannot import this module.', 'Verify the project environment and install the declared dependency.'),
        (r'IndentationError: (.+)', 'INDENTATION_ERROR', 'Python could not parse the indentation.', 'Check indentation at the last traceback location.'),
        (r'SyntaxError: (.+)', 'SYNTAX_ERROR', 'Python could not parse this code.', 'Check the highlighted source line.'),
        (r'ImportError: (.+)', 'IMPORT_ERROR', 'An imported name or dependency is unavailable.', 'Verify package versions and the imported name.'),
        (r'FileNotFoundError: (.+)', 'FILE_NOT_FOUND', 'The code attempted to open a file that is not available.', 'Check the path and working directory.'),
        (r'ConnectionRefusedError: (.+)', 'CONNECTION_REFUSED', 'The connection was refused by the destination.', 'Verify the service and configured port.'),
        (r'KeyError: (.+)', 'KEY_ERROR', 'A dictionary key was not present.', 'Inspect the dictionary keys or handle missing values.'),
        (r'NameError: (.+)', 'NAME_ERROR', 'A referenced variable or name does not exist.', 'Check the name, imports, and scope.'),
        (r'TypeError: (.+)', 'TYPE_ERROR', 'An operation used incompatible types or call arguments.', 'Review the call signature and input types.'),
        (r'AttributeError: (.+)', 'ATTRIBUTE_ERROR', 'The object does not provide the requested attribute.', 'Check the object type and attribute name.'),
        (r'ZeroDivisionError: (.+)', 'ZERO_DIVISION', 'The program divided by zero.', 'Validate the divisor before dividing.'),
    ]
    lines = re.findall(r'File [\'\"]([^\'\"]+)[\'\"], line (\d+)(?:, in ([^\n]+))?', text)
    loc = {'file': lines[-1][0], 'line': int(lines[-1][1])} if lines else {}
    matches = []
    for pattern, code, explanation, suggestion in rules:
        for m in re.finditer(pattern, text):
            matches.append((m.start(), _finding('error', code, m.group(1).strip(), suggestion, explanation=explanation, **loc)))
    return [max(matches, key=lambda x: x[0])[1]] if matches else []


def run_script(script: Path, python: Path, timeout: int = 15, args: list[str] | None = None) -> dict:
    """Execute trusted code in the chosen environment. Not sandboxed."""
    cmd = [str(python), str(script), *(args or [])]
    try:
        result = subprocess.run(cmd, cwd=script.parent, text=True, errors='replace', capture_output=True,
                                stdin=subprocess.DEVNULL, timeout=timeout, shell=False)
        return {'returncode': result.returncode, 'stdout': result.stdout[-10000:], 'stderr': result.stderr[-10000:], 'findings': analyze_log(result.stderr), 'command': cmd, 'verified': result.returncode == 0}
    except subprocess.TimeoutExpired:
        return {'returncode': 124, 'stdout': '', 'stderr': f'Execution timed out after {timeout}s',
                'findings': [_finding('error', 'TIMEOUT', f'{timeout} seconds', 'Increase --timeout for long-running programs.')], 'command': cmd, 'verified': False}
    except OSError as exc:
        return {'returncode': 2, 'stdout': '', 'stderr': str(exc),
                'findings': [_finding('error', 'EXECUTION_FAILED', str(exc), 'Check interpreter and file permissions.')], 'command': cmd, 'verified': False}


def repair_plan(root: Path, runtime_findings: list[dict]) -> list[str]:
    """Only simple direct dependencies; no guessing import name to distribution."""
    declared = declared_requirements(root)
    needed = {NORMALIZE(f['message'].split('.')[0]) for f in runtime_findings if f['code'] == 'MISSING_MODULE'}
    return [spec for name, spec in declared.items() if name in needed]


def create_venv(root: Path, python: Path, timeout: int = 120) -> Path:
    folder = root / '.venv'
    if folder.exists():
        raise ValueError('Refusing to overwrite existing .venv')
    proc = subprocess.run([str(python), '-m', 'venv', str(folder)], capture_output=True, text=True,
                          errors='replace', timeout=timeout, shell=False)
    if proc.returncode:
        raise ValueError('Could not create virtual environment: ' + proc.stderr[-500:])
    result = python_in_venv(folder)
    if not result.is_file():
        raise ValueError('Virtual environment creation returned without a Python executable')
    return result


def install_packages(python: Path, specs: list[str], timeout: int = 180) -> dict:
    if not specs:
        return {'returncode': 2, 'output': 'No eligible package repair.'}
    try:
        proc = subprocess.run([str(python), '-m', 'pip', 'install', *specs], capture_output=True, text=True,
                              errors='replace', timeout=timeout, shell=False, stdin=subprocess.DEVNULL)
        return {'returncode': proc.returncode, 'output': (proc.stdout + '\n' + proc.stderr)[-8000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'returncode': 124, 'output': str(exc)}
