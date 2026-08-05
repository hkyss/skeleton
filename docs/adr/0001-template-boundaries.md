# 0001. Template Boundaries

## Status

Accepted. Amended by [0002. Switchable Presets](0002-switchable-presets.md) — presets are no longer deleted; see 0002 for the current model.

## Context

Legacy project copies mix source, generated assets, runtime data, local scripts, and deployment assumptions.

Supported shapes:

- Laravel or Laravel-style PHP.
- Next/React/Node.
- Legacy PHP or CMS applications with Vite-managed frontend assets.

A single-framework starter does not cover the supported project shapes. A skeleton without a bootable local contract does not satisfy onboarding requirements.

## Decision

Use one runnable multi-preset skeleton with a shared local development contract.

Required repository contract:

- `.docker/compose.yml`
- `.devctl.json`
- `.env.example`
- app presets under `apps/`
- documentation that requires choosing one preset and deleting unused presets

## Consequences

Positive:

- Local infrastructure remains consistent across stack types.
- Stack choice is visible in repository structure.
- Legacy migrations get a controlled target shape.

Negative:

- The template is heavier than a single-stack starter.
- Keeping unused presets creates maintenance cost and ambiguity.
- The template must clearly separate local development from production deployment.

## Enforcement

- Keep exactly one primary application preset unless multiple apps are a deliberate architecture decision.
- Do not put product logic in `.docker/`.
- Do not put single-consumer helpers in `packages/`.
- Do not treat local Compose or `devctl` config as production deployment config.
