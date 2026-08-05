# Project Skeleton

Template repo for projects run through [`devctl`](https://github.com/hkyss/devctl) + Docker Compose. Three interchangeable presets, one `.env`, one `Makefile` surface. Local development only — not a production deployment config.

## Presets

| Preset | Stack |
|---|---|
| `laravel` | PHP 8.5-FPM + nginx |
| `next` | Next.js + nginx |
| `legacy` | PHP public-root + Vite frontend |

The active preset lives in `apps/`, materialized from `.presets/<name>/` via `devctl make skeleton.preset use=<laravel|next|legacy>`. Switching is safe and repeatable — nothing is ever deleted. A fresh clone with no preset installed serves a placeholder page.

## Quick Start

Starting a real project from the skeleton:

```bash
devctl make skeleton.init name=myproject preset=laravel   # rebrand + install the laravel preset
devctl make setup                                          # install deps for the active preset
devctl up                                                   # boot the stack
```

Switch presets later at any time with `devctl make skeleton.preset use=<name>`.

Working on the skeleton itself:

```bash
cp .env.example .env
devctl make setup
devctl up
```

```text
http://skeleton.localhost
```

## Commands

Lifecycle (start, stop, status, logs, shells) is owned by `devctl` — the Makefile keeps only what devctl does not provide:

```text
devctl up | down | restart | status | logs | exec | open

devctl make help              Full command surface
devctl make skeleton.init     Turn the skeleton into a project (name=<n> preset=<p>)
devctl make setup             Create .env, install dependencies
devctl make verify            smoke + lint + format check + typecheck + test
devctl make skeleton.update   Pull skeleton improvements into this project (to=<tag>)
devctl make qa                verify + audits
devctl make fix               Apply automatic formatting
```

## Layout

```text
apps/            active preset's application code (flat; always exactly one preset)
.presets/        source for every preset; the active one is materialized into apps/
packages/shared/ code shared across presets
.docker/         compose.yml, nginx, php, node images
scripts/         repo tooling
docs/            architecture, ADRs, runbooks, migration notes
.devctl.json     devctl profile (ports, health check)
```

## Runtime

`.docker/compose.yml` services:

| Service | Role |
|---|---|
| `gateway` | nginx, routes to the active preset |
| `php` | PHP-FPM runtime (PHP presets) |
| `node` | Next/Vite dev server (Node presets) |
| `mysql` | local MySQL |
| `redis` | local Redis |
| `mailpit` | local mail capture UI |
| `tools` | repo validation utilities |
| `queue` | PHP worker, opt-in via `workers` Compose profile |

Ports are declared in `.devctl.json` (`http_port_env`, `extra_port_envs`) and bind to loopback only; `devctl` owns allocation. `devctl exec` without `--service` targets `gateway` (the only service present in every preset, including the placeholder); use `--service php` / `--service node` for an app shell.

## Docs

- Index: [`docs/README.md`](docs/README.md)
- Architecture: [`docs/architecture/overview.md`](docs/architecture/overview.md)
- Local ops: [`docs/operations/local-development.md`](docs/operations/local-development.md)
- Legacy migration: [`docs/migration/legacy-projects.md`](docs/migration/legacy-projects.md)
- ADRs: [`docs/adr/`](docs/adr/)

## Repository Rules

- Commit: source, docs, tests, lock files, config examples, conventions.
- Never commit: `.env`, secrets, `vendor`, `node_modules`, runtime storage, generated bundles, volumes, raw dumps.
- Keep local dev config separate from production deployment config.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — in particular the skeleton-owned vs
project-owned split, and the preset markers. Security reports:
[SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
