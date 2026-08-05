# Migration Guide

Use this process when moving an existing project into the skeleton.

Goal: separate source code, generated output, runtime state, secrets, and deployment assumptions.

## Entry Criteria

Document before moving files:

- Application type: Laravel, Next, legacy PHP, CMS, or mixed.
- HTTP entrypoint and public web root.
- PHP version and Composer dependencies.
- Node version, package manager, frontend source path, and build output path.
- Runtime directories: cache, logs, sessions, uploads, compiled views.
- Database, Redis, queues, scheduled jobs, and mail requirements.
- External services and credentials.
- Production-only scripts, SSH sync, cron jobs, and server path assumptions.

Do not copy the full legacy repository first.

## Target Preset

- Use the `laravel` preset only for real Laravel or Laravel-compatible applications.
- Use the `next` preset for applications where Next owns routing and rendering.
- Use the `legacy` preset for public-root PHP or CMS applications with separate frontend assets.

If the project does not fit one preset cleanly, document the mismatch in `docs/architecture/overview.md` before adding compatibility scripts.

## Git Ownership

Commit:

- Application source.
- Framework config templates.
- Migrations, seeds, and sanitized fixtures.
- Frontend source.
- Local development Docker files.
- Documentation and runbooks.
- Lock files for deterministic installs.

Do not commit:

- Real `.env` files.
- `vendor`.
- `node_modules`.
- Runtime storage.
- Generated frontend bundles unless required by a documented legacy deployment constraint.
- Database volumes.
- Raw production dumps.
- Secrets, SSH keys, API tokens, or server-specific config.

## Environment Contract

Create one committed `.env.example` at the repository root.

Rules:

- Include every variable required to boot locally.
- Use safe defaults or explicit placeholders.
- Keep real secrets in local `.env` or a secret manager.
- Collapse duplicate env files during migration.

## Legacy PHP With Vite

```text
apps/
  public/      Stable web root
  src/         PHP application code
  frontend/    Vite/React source
  storage/     Runtime state, not source of truth
```

Rules:

- PHP must not depend on `frontend/src`.
- Browser-served assets must come from `public`.
- Vite build output belongs in `public/theme/dist`.
- If generated assets must be committed, document why and define the build command that refreshes them.

## Migration Order

1. Move source code and config examples only.
2. Add `.env.example` and local boot documentation.
3. Make the app boot with empty runtime state.
4. Add dependency lock files.
5. Add database migrations or sanitized import.
6. Add seed/anonymization commands if real data is needed locally.
7. Add asset build commands.
8. Add queue and scheduled task commands.
9. Nothing to hand-update here: the CI matrix (`.github/workflows/ci.yml`)
   and Makefile scopes (`.make/active.mk`) are both derived automatically
   from which `.presets/` directories exist and which preset is active.
10. Run `make skeleton.preset use=<name>` to materialize the migrated source into `apps/`. Unused presets stay available under `.presets/` for future switching.
11. Remove stale sync scripts and server-specific paths.

## Exit Criteria

- `devctl up` or the documented Compose command boots the chosen preset.
- `/health` returns `204`.
- Dependencies install from lock files.
- `make verify` passes.
- Required local data setup is documented.
- Runtime state is excluded from git.
- Unused presets remain available under `.presets/` for future switching; only the active preset is materialized into `apps/`.
- Production deployment assumptions are documented outside the local Compose contract.
