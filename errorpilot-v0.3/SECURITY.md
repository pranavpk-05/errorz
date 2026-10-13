# Security policy

## Trust model

ErrorPilot is **not a sandbox**. `auto` and `run` execute a selected Python script, and that script may read/write files, make network calls, or spawn processes. Do not run unknown or untrusted projects. A timeout does not guarantee termination of all child processes.

## Repair risks

`--apply` only proposes supported direct-dependency installation and normally requires interactive approval. `--apply --yes` is an explicit noninteractive authorization. Package installation can execute third-party code. Prefer reviewing dependency names and using an isolated environment before approving.

ErrorPilot v0.3 does not rewrite application source code and does not offer rollback of package installations or application side effects. An exit code of zero is not a security or functional correctness guarantee.

## Sensitive information

Error logs, JSON reports, and console output may include file paths, environment values, tokens, or application data. Review and redact before sharing publicly. Do not include secrets in GitHub issues.

## Reporting vulnerabilities

Please avoid disclosing exploitable details publicly before maintainers can investigate. Once a GitHub repository is published, use its private vulnerability reporting feature if enabled; otherwise contact the repository maintainer through an appropriate private channel. No security-response SLA is promised at this stage.

## Supported versions

This is an experimental project. Security fixes are intended for the latest published version; there is no long-term support commitment for older releases.
