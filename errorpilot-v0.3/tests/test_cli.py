import json
import sys
from pathlib import Path
from typer.testing import CliRunner
from errorpilot.cli import app
from errorpilot.engine import (resolve_target, diagnose, syntax_check, analyze_log, repair_plan,
                               run_script, declared_requirements, select_python)

runner = CliRunner()


def test_missing_package(tmp_path):
    (tmp_path / 'requirements.txt').write_text('package-that-does-not-exist-errorpilot-123==1.0\n')
    assert any(f['code'] == 'MISSING_DEPENDENCY' for f in diagnose(resolve_target(tmp_path)))


def test_python_version(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="demo"\nversion="0.1"\nrequires-python=">=99"\n')
    assert any(f['code'] == 'PYTHON_VERSION' for f in diagnose(resolve_target(tmp_path)))


def test_syntax_check(tmp_path):
    (tmp_path / 'wrong.py').write_text('def bad(:\n')
    result = syntax_check(tmp_path)
    assert result[0]['code'] == 'SYNTAX_ERROR'
    assert result[0]['line'] == 1


def test_skip_virtualenv(tmp_path):
    p = tmp_path / '.venv' / 'Scripts'
    p.mkdir(parents=True)
    (p / 'broken.py').write_text('def bad(:\n')
    assert syntax_check(tmp_path) == []


def test_resolve_main(tmp_path):
    (tmp_path / 'main.py').write_text('print("works")\n')
    assert resolve_target(tmp_path).script.name == 'main.py'


def test_ambiguous_entries(tmp_path):
    for name in ('main.py', 'app.py'):
        (tmp_path / name).write_text('pass')
    try:
        resolve_target(tmp_path)
    except ValueError as e:
        assert 'entry' in str(e)
    else:
        assert False, 'should refuse to guess entrypoint'


def test_runtime_type_error(tmp_path):
    script = tmp_path / 'main.py'
    script.write_text('raise TypeError("bad operands")')
    result = run_script(script, Path(sys.executable))
    assert result['returncode'] != 0
    assert result['findings'][0]['code'] == 'TYPE_ERROR'


def test_friendly_cli_doctor():
    result = runner.invoke(app, ['doctor'])
    assert result.exit_code == 0
    assert 'ErrorPilot' in result.output


def test_friendly_cli_diagnose_json(tmp_path):
    (tmp_path / 'requirements.txt').write_text('fake-errorpilot-no-library==4.0')
    result = runner.invoke(app, ['diagnose', str(tmp_path), '--json'])
    assert result.exit_code == 1
    decoded = json.loads(result.stdout)
    assert decoded['findings'][0]['code'] in ('NO_PROJECT_VENV', 'MISSING_DEPENDENCY')
    assert any(f['code'] == 'MISSING_DEPENDENCY' for f in decoded['findings'])


def test_auto_success(tmp_path):
    (tmp_path / 'main.py').write_text('print("hello from ErrorPilot")\n')
    result = runner.invoke(app, ['auto', str(tmp_path), '--json'])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data['execution']['returncode'] == 0
    assert 'hello from ErrorPilot' in data['execution']['stdout']


def test_auto_no_entry(tmp_path):
    result = runner.invoke(app, ['auto', str(tmp_path), '--json'])
    assert result.exit_code == 0
    assert json.loads(result.stdout)['execution'] is None


def test_auto_syntax_not_executed(tmp_path):
    (tmp_path / 'main.py').write_text('def broken(:\n')
    result = runner.invoke(app, ['auto', str(tmp_path), '--json'])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data['execution'] is None
    assert any(f['code'] == 'SYNTAX_ERROR' for f in data['diagnostics'])


def test_reject_yes_without_apply(tmp_path):
    result = runner.invoke(app, ['auto', str(tmp_path), '--yes'])
    assert result.exit_code == 2


def test_safe_repair_not_undeclared(tmp_path):
    (tmp_path / 'requirements.txt').write_text('flask==3.0.0\n')
    assert repair_plan(tmp_path, analyze_log("ModuleNotFoundError: No module named 'flask'")) == ['flask==3.0.0']
    assert repair_plan(tmp_path, analyze_log("ModuleNotFoundError: No module named 'unknown'")) == []


def test_local_venv_preferred(tmp_path):
    folder = tmp_path / '.venv' / ('Scripts' if sys.platform == 'win32' else 'bin')
    folder.mkdir(parents=True)
    name = 'python.exe' if sys.platform == 'win32' else 'python'
    (folder / name).write_text('fake')
    py, is_local = select_python(tmp_path)
    assert is_local
    assert py.name == name


def test_invalid_pyproject(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[[invalid')
    result = diagnose(resolve_target(tmp_path))
    assert any(f['code'] == 'INVALID_PYPROJECT' for f in result)


def test_auto_repair_requires_approval(tmp_path, monkeypatch):
    """Without --apply even a repairable crash must never install packages."""
    (tmp_path / 'requirements.txt').write_text('flask==3.0.0\n')
    (tmp_path / 'main.py').write_text('import flask\n')
    calls = []
    import errorpilot.cli as cli
    monkeypatch.setattr(cli, 'install_packages', lambda *a, **k: calls.append(1))
    monkeypatch.setattr(cli, 'run_script', lambda *a, **k: {
        'returncode': 1, 'stdout': '', 'stderr': "ModuleNotFoundError: No module named 'flask'",
        'findings': analyze_log("ModuleNotFoundError: No module named 'flask'")})
    result = runner.invoke(app, ['auto', str(tmp_path)])
    assert result.exit_code == 1
    assert calls == []


def test_auto_approved_repair_verifies(tmp_path, monkeypatch):
    (tmp_path / 'requirements.txt').write_text('flask==3.0.0\n')
    (tmp_path / 'main.py').write_text('import flask\n')
    import errorpilot.cli as cli
    execution_count = {'n': 0}
    created = tmp_path / 'mock_venv_python'
    def fake_run(*args, **kwargs):
        execution_count['n'] += 1
        if execution_count['n'] == 1:
            return {'returncode': 1, 'stdout': '', 'stderr': 'error',
                    'findings': analyze_log("ModuleNotFoundError: No module named 'flask'")}
        return {'returncode': 0, 'stdout': 'fixed', 'stderr': '', 'findings': []}
    monkeypatch.setattr(cli, 'run_script', fake_run)
    monkeypatch.setattr(cli, 'create_venv', lambda *a, **k: created)
    monkeypatch.setattr(cli, 'install_packages', lambda *a, **k: {'returncode': 0, 'output': 'installed'})
    result = runner.invoke(app, ['auto', str(tmp_path), '--apply', '--yes'])
    assert result.exit_code == 0, result.output
    assert 'Verification passed' in result.output
    assert execution_count['n'] == 2


def test_run_alias(tmp_path):
    script = tmp_path / 'runme.py'
    script.write_text('print("okay")\n')
    result = runner.invoke(app, ['run', str(script)])
    assert result.exit_code == 0, result.output
    assert 'okay' in result.output


def test_missing_module_location():
    log = 'Traceback (most recent call last):\n  File "app.py", line 42, in <module>\n    import nonsense\nModuleNotFoundError: No module named \'nonsense\''
    f = analyze_log(log)[0]
    assert f['code'] == 'MISSING_MODULE'
    assert f['line'] == 42
    assert f['file'] == 'app.py'


def test_nested_unsupported_requirement(tmp_path):
    (tmp_path / 'requirements.txt').write_text('-r more.txt\n')
    result = diagnose(resolve_target(tmp_path))
    assert any(f['code'] == 'UNSUPPORTED_REQUIREMENT' for f in result)


def test_no_automatic_fix_for_syntax(tmp_path):
    (tmp_path / 'main.py').write_text('if True print(1)\n')
    result = runner.invoke(app, ['auto', str(tmp_path), '--apply', '--yes'])
    assert result.exit_code == 1
    assert 'syntax error' in result.output.lower()
