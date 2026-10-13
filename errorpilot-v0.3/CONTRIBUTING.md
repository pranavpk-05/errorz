# Contributing to ErrorPilot

Thanks for considering a contribution. ErrorPilot aims to provide transparent, reliable Python diagnostics with a narrow, reviewable repair surface.

## Before opening a pull request

- Check existing issues and the [roadmap](ROADMAP.md).
- For a new diagnostic rule, provide a minimal failing example and an expected finding.
- For any repair feature, explain the trust boundary, user approval, and verification strategy.
- Keep the default diagnosis non-mutating. Never introduce silent package installation or source rewriting.
- Add tests and run `python -m pytest -q` from the development environment.
- Update documentation when behavior or flags change.

## Pull request checklist

- [ ] Changes have a clear purpose and a reproducible example
- [ ] Tests added or updated where appropriate
- [ ] Full test suite passes locally
- [ ] No secrets, credentials, or sensitive logs committed
- [ ] Documentation and changelog updated if needed
- [ ] Any new execution or installation risk is explained

## Reporting a bug

Include OS, Python version, ErrorPilot version, the exact command, expected versus actual behavior, and a **redacted** traceback. Never publish API keys, passwords, or private project data.

## Code of conduct

Be constructive and respectful. Focus reviews on correctness, reproducibility, safety, and maintainability.
