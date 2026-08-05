SHELL := /bin/sh

COMPOSE_FILE := .docker/compose.yml
COMPOSE := docker compose --env-file .env -f $(COMPOSE_FILE)
COMPOSE_CI := docker compose --env-file .env.example -f $(COMPOSE_FILE)

TOOLS := TOOLS_UID=$$(id -u) TOOLS_GID=$$(id -g) $(COMPOSE_CI) run --rm tools sh -lc

-include .make/active.mk

.DEFAULT_GOAL := help

.PHONY: help setup env deps verify qa fix fmt fmt-check lint types test skeleton.smoke skeleton.init skeleton.info skeleton.presets skeleton.update skeleton.preset audit reset queue

help:
	@printf '%s\n' 'Lifecycle is owned by devctl:'
	@printf '  %-24s %s\n' 'devctl up | down' 'Start / stop the project'
	@printf '  %-24s %s\n' 'devctl restart' 'Restart the project'
	@printf '  %-24s %s\n' 'devctl status' 'Show project status and ports'
	@printf '  %-24s %s\n' 'devctl logs -f' 'Follow project logs'
	@printf '  %-24s %s\n' 'devctl exec --service php -- sh' 'Shell into a service container'
	@printf '  %-24s %s\n' 'devctl open' 'Open the project URL'
	@printf '\n%s\n' 'Project commands:'
	@printf '  %-24s %s\n' 'devctl make skeleton.init name=<n> preset=<p>' 'Turn the skeleton into a project' # preset:template
	@printf '  %-24s %s\n' 'devctl make skeleton.preset use=<p>' 'Install or switch the active app preset'
	@printf '  %-24s %s\n' 'devctl make skeleton.info' 'Show current project name, active preset, and skeleton version'
	@printf '  %-24s %s\n' 'devctl make skeleton.presets' 'List available presets'
	@printf '  %-24s %s\n' 'devctl make setup' 'Create .env and install all dependencies'
	@printf '  %-24s %s\n' 'devctl make verify' 'Run the full local quality gate'
	@printf '  %-24s %s\n' 'devctl make fix' 'Apply automatic formatting'
	@printf '  %-24s %s\n' 'devctl make skeleton.smoke' 'Validate devctl, env, and Compose contracts'
	@printf '  %-24s %s\n' 'devctl make skeleton.update to=<tag>' 'Pull skeleton improvements into this project'
	@printf '  %-24s %s\n' 'devctl make audit' 'Run security audits where configured'
	@printf '  %-24s %s\n' 'make queue' 'Run the opt-in queue worker profile (laravel/legacy presets)'
	@printf '  %-24s %s\n' 'make reset' 'Stop the stack and remove dependency artifacts'
	@printf '\n%s\n' 'Scopes (available once a preset is installed):'
	@printf '  %-24s %s\n' 'make fe' 'Run all frontend checks'
	@printf '  %-24s %s\n' 'make be' 'Run all backend checks'
	@printf '  %-24s %s\n' 'make next' 'Run all Next preset checks'
	@printf '  %-24s %s\n' 'make legacy-fe' 'Run all legacy frontend checks'
	@printf '  %-24s %s\n' 'make laravel' 'Run all Laravel-style PHP checks'
	@printf '  %-24s %s\n' 'make legacy' 'Run all legacy PHP checks'

# >>> preset:template
.PHONY: skeleton.init
skeleton.init:
	$(TOOLS) 'python scripts/init-project.py $(name) $(if $(preset),--preset $(preset),)'
	$(COMPOSE_CI) config >/dev/null
# <<< preset

.PHONY: skeleton.preset
skeleton.preset:
	$(TOOLS) 'python scripts/install-preset.py --use $(use) $(if $(force),--force,)'

env:
	@test -f .env || cp .env.example .env

setup: env deps

deps: $(DEPS_SCOPES)

queue: env
	$(COMPOSE) --profile workers up queue

verify: env skeleton.smoke lint fmt-check types test

qa: verify audit

fix: fmt

fmt: $(FMT_SCOPES)

fmt-check: $(FMT_CHECK_SCOPES)

lint: $(LINT_SCOPES)

types: $(TYPES_SCOPES)

test: $(TEST_SCOPES)

skeleton.smoke: env
	$(TOOLS) 'python scripts/smoke.py'
	$(COMPOSE_CI) config >/dev/null
	devctl validate --strict

skeleton.info:
	$(TOOLS) 'python scripts/skeleton_info.py'

skeleton.presets:
	$(TOOLS) 'python scripts/skeleton_presets.py'

.PHONY: skeleton.update
skeleton.update:
	$(TOOLS) 'python scripts/update-skeleton.py $(if $(to),--to $(to),)$(if $(dry), --dry-run,)'

audit: $(AUDIT_SCOPES)

reset:
	devctl down || true
	@test -f .make/active.mk && $(MAKE) --no-print-directory -f .make/active.mk reset-artifacts || true
