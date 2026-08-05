# Contributing

This repo is a template. Most changes land in one of two places, and it matters
which:

- **Skeleton-owned** — `.docker/`, `Makefile`, `.presets/_infra/`, the tooling
  in `scripts/`, CI, ops docs. These are synced into downstream projects by
  `devctl make skeleton.update`, so a change here reaches every project that
  was ever generated from the skeleton.
- **Project-owned** — `apps/`, `.presets/{laravel,next,legacy}/`, `packages/`,
  project docs. Downstream projects customize these freely and never receive
  updates to them.

`skeleton.manifest.json` is the authority on which is which. Read it before
moving a file between the two.

Default branch is `dev`. Branch from it, open the PR against it.

## Setup

```bash
git clone https://github.com/hkyss/skeleton
cd skeleton
cp .env.example .env
devctl make setup
devctl up
```

You need [`devctl`](https://github.com/hkyss/devctl) and Docker. Everything else
runs in containers — there is no host toolchain to install, and you should not
install one.

## Before you push

```bash
devctl make verify   # smoke + lint + format check + typecheck + test
devctl make fix      # apply formatting
```

`verify` only exercises the *active* preset. CI runs every preset that exists
under `.presets/`, so if you touched shared infrastructure, check the other
presets too:

```bash
devctl make skeleton.preset use=next
devctl make verify
```

Switching is non-destructive — nothing is deleted, and you can switch back.

## Preset markers

Shared files carry `# >>> preset:<tags>` / `# <<< preset` blocks and trailing
`# preset:<tags>` markers. They are load-bearing: `scripts/preset_markers.py`
prunes on them when a preset is installed or a project is initialized. Deleting
or reformatting one silently changes what generated projects get.

The grammar is documented in
[`docs/architecture/overview.md`](docs/architecture/overview.md#preset-markers).
If you add a marker, add a case to `scripts/tests/test_preset_markers.py`.

## Code style

- No comments and no docstrings anywhere, with two exceptions: shebangs, and the
  preset markers above. If something needs explaining, explain it in `docs/`.
- Tooling scripts are stdlib-only Python — they run in the `tools` container,
  which deliberately has no third-party packages.
- Every `scripts/*.py` change needs a test in `scripts/tests/`.

## Adding a preset

1. Create `.presets/<name>/` with the app source and its own lock file.
2. Add the scopes it needs to `.presets/_infra/Makefile.tmpl`, wrapped in
   preset markers.
3. Add its routing to `.docker/nginx/entrypoint.sh`.
4. Register it in `PRESETS` in `scripts/preset_markers.py`.
5. Run `devctl make skeleton.preset use=<name> && devctl make verify`.

CI picks the new preset up automatically — the matrices are computed from which
`.presets/` directories exist.

## Docs

Architecture decisions go in `docs/adr/` as a new numbered file. Amend an
existing ADR rather than rewriting it; superseded decisions stay readable.
