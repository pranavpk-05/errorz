# Supported diagnostics and repair boundaries

## Currently implemented

| Category | Detection | Automatic repair |
|---|---|---|
| Direct missing dependencies | Yes, straightforward requirements/PEP 621 metadata | **Yes**, only declared missing dependencies, with approval |
| Dependency version mismatch | Yes, for supported specifications | No |
| Python interpreter compatibility | Yes, when declared | No |
| Missing project-local virtual environment | Informational finding | May create `.venv` as part of an approved dependency repair |
| Python syntax errors | Yes, local source files | No |
| `ModuleNotFoundError` | Traceback classification | Only when mapped to an eligible direct dependency |
| `NameError`, `TypeError`, `KeyError`, `AttributeError` | Common traceback classification | No |
| `FileNotFoundError`, `ConnectionRefusedError` | Common traceback classification | No |
| Arbitrary logic errors | Not reliably detectable | No |
| Database configuration and network availability | May surface exceptions | No |

## What a successful repair means

The original entry script was rerun and returned exit code `0`. This verifies **observed execution only**. It does not prove that tests pass, endpoints respond, output is correct, or the application is secure.

## Dependency limitations

The project handles straightforward direct dependency declarations. Complex requirements (`-r`, editable installs, URL/VCS requirements, environment-specific constraints), lockfiles, import-name/package-name differences (such as `PIL` versus `Pillow`), and multi-manager dependency graphs are not fully supported.

## Entry point limitations

Auto-detection cannot reliably discover all application startup patterns. Framework-specific entry points, CLI arguments, external services, or environment variables may require `--entry`, `--arg`, and manual setup.

## Not yet implemented

Automatic source-code patching, LLM-based root-cause analysis, regression-test generation, transactional rollback, multi-language analysis, and general infrastructure repair are **roadmap items**, not existing capabilities.
