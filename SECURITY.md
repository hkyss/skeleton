# Security Policy

## Supported Versions

This repository is a development template, not a versioned production
service. There are no maintained release branches — only the latest commit
on `dev` (the default branch) receives security fixes.

## Reporting a Vulnerability

Please report security vulnerabilities privately using GitHub's
[private vulnerability reporting](https://github.com/hkyss/skeleton/security/advisories/new)
(Security tab → Report a vulnerability).

Do not open a public issue for security reports.

If you cannot use GitHub's reporting flow, contact hkyss.services@protonmail.com.

We aim to acknowledge reports within 5 business days.

## Scope

Since this is a local development template (Docker Compose + `devctl`), reports
that are especially useful include:

- Insecure defaults in `.docker/compose.yml` or `.devctl.json` (e.g. ports bound
  beyond loopback, weak default credentials).
- Vulnerable dependencies in any of the presets (`.presets/laravel`,
  `.presets/next`, `.presets/legacy`).
- Issues in `scripts/` or CI workflows that could lead to secret exposure or
  code execution in CI.
