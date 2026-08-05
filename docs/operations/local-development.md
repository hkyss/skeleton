# Operations

Local development runbook.

## Prerequisites

- Docker with Compose support.
- `devctl`.
- `.env` created from `.env.example`.

No local `make` or `python3` install is required: `devctl make <target>` expands
and runs the Makefile without a host `make` binary, and all Python tooling
(`skeleton.init`, `skeleton.update`, `skeleton.smoke`) runs inside the `tools`
Compose service.

Create env:

```bash
cp .env.example .env
```

Required env keys:

```env
PROJECT_NAME=devctl_skeleton
APP_PRESET=none
PORT_HTTP=8080
PORT_DB=3306
PORT_REDIS=6379
PORT_MAIL=8025
DB_DATABASE=app
DB_USERNAME=app
DB_PASSWORD=app
DB_ROOT_PASSWORD=root
```

Valid `APP_PRESET` values:

- `laravel`
- `next`
- `legacy`
- `none` (default — no preset installed, serves a placeholder page)

## Switching the Active Preset

`devctl make skeleton.preset use=<laravel|next|legacy>` materializes the chosen
preset's source from `.presets/<name>/` into `apps/`, regenerates the local
`.make/active.mk`, and points `APP_PRESET` and `COMPOSE_PROFILES` at the new
preset. Setting `COMPOSE_PROFILES` in `.env` is what activates that preset's
gated Compose services (e.g. `php`, `node`), so `devctl up` alone starts the
right services with no extra flag. It is safe to run repeatedly — switching
back and forth between presets is supported. It refuses to run if `apps/` has
uncommitted changes; pass `force=1` to override.

A fresh clone with no preset installed serves a static placeholder page at
`http://<project>.localhost` instead of booting any framework stack.

## Start

```bash
devctl make setup
devctl up
```

Default URL:

```text
http://skeleton.localhost
```

Direct Compose fallback:

```bash
docker compose --env-file .env -f .docker/compose.yml up --build
```

`--env-file .env` carries `COMPOSE_PROFILES`, so once a preset is installed
this also starts that preset's `php`/`node` service; with no preset installed,
only `gateway` and the shared services start, serving the placeholder page.

## Health Checks

```bash
curl -i http://localhost:${PORT_HTTP}/health
```

Expected status: `204`.

Behavior:

- `next`: nginx proxies `/health` to `/api/health`.
- `laravel` and `legacy`: nginx returns `204`.

## Logs

```bash
devctl logs
devctl logs -f
```

Service-scoped logs:

```bash
devctl logs -f --service gateway
devctl logs -f --service php
devctl logs -f --service node
```

## Shells

```bash
devctl exec --service php -- sh
devctl exec --service node -- sh
devctl exec --service mysql -- mysql -u app -papp app
```

## Dependencies

```bash
devctl make deps
```

Scoped installs:

```bash
devctl make deps-be
devctl make deps-fe
```

## Quality Gates

Requires the stack to be running (`devctl up`); lint/format/type/test targets
run via `devctl exec` against the live containers.

```bash
devctl make verify
```

Focused gates:

```bash
devctl make skeleton.smoke
devctl make lint
devctl make fmt-check
devctl make types
devctl make test
```

Use:

- `devctl make fix`: apply formatting.
- `devctl make qa`: run `devctl make verify` plus audits.

## Queue Worker

```bash
devctl make queue
```

The worker runs `php artisan queue:work` only when the selected preset has `artisan`.

## Rebuild

```bash
docker compose --env-file .env -f .docker/compose.yml build --no-cache
devctl restart
```

For direct Compose:

```bash
docker compose --env-file .env -f .docker/compose.yml down
docker compose --env-file .env -f .docker/compose.yml up --build
```

## Data

- `mysql-data`
- `redis-data`

Do not commit database files, raw dumps, Redis snapshots, or runtime storage.

Real projects must document:

- migrations
- seeds
- sanitized import
- anonymization

## Mail

Mailpit: `127.0.0.1:${PORT_MAIL}`.

## Troubleshooting

- `gateway` exits: check `APP_PRESET`.
- `node` idle: expected for `APP_PRESET=laravel` or `APP_PRESET=none` (no preset installed).
- Missing legacy assets: the node container rebuilds `public/theme/dist` on
  save in watch mode; if assets are still stale, run `devctl make legacy-fe-build`.
- `devctl make verify` fails on missing dependencies: run `devctl make setup`.
- Dependency changes: commit updated lock files.
