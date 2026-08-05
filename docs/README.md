# Documentation

Documentation is organized by ownership area. Do not add loose Markdown files directly under `docs/`.

## Index

- [Architecture](architecture/overview.md): repo boundaries, presets, switching presets, runtime model, quality gates, updating an initialized project.
- [Local operations](operations/local-development.md): setup, commands, services, checks, troubleshooting.
- [Legacy migration](migration/legacy-projects.md): source migration order, git ownership, exit criteria.
- [ADRs](adr/): accepted architecture decisions.

## Rules

- Root `README.md` is an entry point only.
- Put system shape in `docs/architecture/`.
- Put commands and runbooks in `docs/operations/`.
- Put migration procedures in `docs/migration/`.
- Put accepted decisions in `docs/adr/`.
- Update links in root `README.md` when adding a new primary doc.
