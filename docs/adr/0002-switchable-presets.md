# 0002. Switchable Presets

## Status

Accepted. Amends [0001. Template Boundaries](0001-template-boundaries.md).

## Context

[0001](0001-template-boundaries.md) required keeping exactly one primary
application preset per project, enforced by `scripts/init-project.py`
permanently deleting the other presets' `apps/*` directories and pruning
preset-marker lines out of shared infra files at init time.

That constraint made preset selection a one-way door: switching stacks later
required a fresh clone. It also meant a bare clone of the skeleton itself
booted every supported stack (PHP + Node + MySQL + Redis + Mailpit)
simultaneously before anyone had chosen anything.

## Decision

- Preset application source moves to `.presets/<name>/` and is never deleted.
  It is `project_owned` (see `skeleton.manifest.json`) — customized freely,
  untouched by `skeleton.update`.
- `apps/` holds whichever preset is currently active, materialized by
  `devctl make skeleton.preset use=<name>` (`scripts/install-preset.py`). This
  command is repeatable: switching between presets, including after
  `skeleton.init`, is a supported operation, not a one-time choice.
- A fresh clone or a project with no preset installed serves a minimal
  static placeholder from `apps/` instead of booting a framework stack.
- `.docker/compose.yml` gates preset-specific services (`php`, `node`) with
  native Compose `profiles:`, activated via `COMPOSE_PROFILES` (set alongside
  `APP_PRESET` by `devctl make skeleton.preset use=<name>`), rather than
  deleting service definitions. `Makefile` scope/target definitions live in
  `.presets/_infra/Makefile.tmpl`, rendered per-preset into a gitignored
  `.make/active.mk` — neither file is ever destructively pruned.

## Consequences

Positive:

- No fresh clone required to try a different stack.
- A bare clone boots a lightweight placeholder instead of every stack at once.
- Preset app source and "which preset is active" are cleanly separated.

Negative:

- `.presets/` keeps all supported stacks' source in the repository
  indefinitely — the same "heavier than a single-stack starter" and
  "unused presets create maintenance cost" trade-offs that
  [0001](0001-template-boundaries.md) already accepted, now permanent rather
  than resolved at init time.
- Two more moving parts to reason about locally: `.make/active.mk` and which
  Compose profile is active.

## Enforcement

- `scripts/init-project.py` still performs one-time rebranding (project slug,
  `.devctl.json`, `README.md`, package manifests) — that part remains a
  one-way operation.
- `devctl make skeleton.preset use=<name>` is the only supported way to change
  what's materialized into `apps/`; never hand-edit `apps/` to switch stacks.
- Do not add preset-only content directly to `Makefile` or `.docker/compose.yml`
  again — it belongs in `.presets/_infra/Makefile.tmpl` (Makefile targets) or
  behind a Compose `profiles:` entry (compose services).
