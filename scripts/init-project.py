#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from preset_markers import (
    BLOCK_CLOSE_PATTERNS,
    BLOCK_OPEN_PATTERNS,
    LINE_SUFFIX_PATTERNS,
    MarkupError,
    PRESETS,
    RESERVED_TAG,
    VALID_TAGS,
    match_any,
    prune_text,
)
from skeleton_manifest import MissingVersionError, load_manifest, manifest_version

ROOT = Path(__file__).resolve().parents[1]
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

_INSTALL_PRESET_PATH = Path(__file__).resolve().parent / "install-preset.py"
_install_preset_spec = importlib.util.spec_from_file_location(
    "install_preset", _INSTALL_PRESET_PATH
)
install_preset = importlib.util.module_from_spec(_install_preset_spec)
_install_preset_spec.loader.exec_module(install_preset)


_MANIFEST = load_manifest(ROOT)
TEMPLATE_ONLY = _MANIFEST["template_only"]
MARKED_FILES = _MANIFEST["marked_files"]
SKIP_DIRS = {".git", "node_modules", "vendor", ".next", ".claude", ".cursor", "_infra"}

MARKER_EXEMPT_FILES = frozenset({
    ".docker/nginx/entrypoint.sh",
    ".docker/node/start-node-preset",
    ".docker/php/start-queue-preset",
})


class InitError(RuntimeError):
    pass


def plan_changes(root: Path, preset: str) -> dict:
    removals = [*TEMPLATE_ONLY]
    pruned: dict[str, str] = {}
    for rel in MARKED_FILES:
        path = root / rel
        if not path.is_file():
            raise InitError(f"manifest error: marked file missing: {rel}")
        pruned[rel] = prune_text(path.read_text(encoding="utf-8"), preset, rel)
    return {"removals": removals, "pruned": pruned}


def apply_removals_and_pruning(root: Path, planned: dict) -> None:
    for rel in planned["removals"]:
        target = root / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for rel, text in planned["pruned"].items():
        (root / rel).write_text(text, encoding="utf-8")


def git_is_clean(root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
    )
    return result.returncode == 0 and not result.stdout.strip()


def devctl_project_name(slug: str) -> str:
    return "devctl_" + slug.replace("-", "_")


def rebrand_devctl_profile(root: Path, slug: str) -> None:
    path = root / ".devctl.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    profile["name"] = slug
    profile["compose_project_name"] = devctl_project_name(slug)
    profile.setdefault("env", {})["PROJECT_NAME"] = devctl_project_name(slug)
    path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")


def rebrand_env_example(root: Path, slug: str, preset: str) -> None:
    path = root / ".env.example"
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("PROJECT_NAME="):
            line = f"PROJECT_NAME={devctl_project_name(slug)}\n"
        elif line.startswith("APP_PRESET="):
            line = f"APP_PRESET={preset}\n"
        lines.append(line)
    path.write_text("".join(lines), encoding="utf-8")


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def rebrand_text_references(root: Path, slug: str) -> None:
    replacements = (
        ("skeleton.localhost", f"{slug}.localhost"),
        ("devctl_skeleton", devctl_project_name(slug)),
        ("project_skeleton", devctl_project_name(slug)),
        ("project-skeleton", slug),
    )
    for path, text in list(iter_text_files(root)):
        updated = text
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def _set_json_name(path: Path, name: str, *, lock_root: bool = False, description: str | None = None) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["name"] = name
    if description is not None and "description" in data:
        data["description"] = description
    if lock_root and isinstance(data.get("packages"), dict) and "" in data["packages"]:
        data["packages"][""]["name"] = name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rebrand_packages(root: Path, slug: str, preset: str) -> None:
    if preset == "next":
        _set_json_name(root / "apps/package.json", slug)
        _set_json_name(root / "apps/package-lock.json", slug, lock_root=True)
    if preset == "legacy":
        fe_name = f"{slug}-frontend"
        _set_json_name(root / "apps/frontend/package.json", fe_name)
        _set_json_name(root / "apps/frontend/package-lock.json", fe_name, lock_root=True)
        _set_json_name(root / "apps/composer.json", f"{slug}/app",
                       description=f"{slug} application")
    if preset == "laravel":
        _set_json_name(root / "apps/composer.json", f"{slug}/app",
                       description=f"{slug} application")


README_TEMPLATE = """# {slug}

Local development runs through [`devctl`](https://github.com/hkyss/devctl) + Docker Compose.

## Quick Start

```bash
cp .env.example .env
devctl make setup   # install dependencies
devctl up           # boot the stack
```

```text
http://{slug}.localhost
```

## Commands

Lifecycle is owned by `devctl`; the Makefile keeps project-specific commands:

```text
devctl up | down | restart | status | logs | exec | open

devctl make help              Full command surface
devctl make setup             Create .env, install dependencies
devctl make verify            smoke + lint + format check + typecheck + test
devctl make skeleton.update   Pull skeleton improvements into this project (to=<tag>)
devctl make qa                verify + audits
devctl make fix               Apply automatic formatting
```

## Docs

- [docs/README.md](docs/README.md)
"""


def write_readme(root: Path, slug: str) -> None:
    (root / "README.md").write_text(README_TEMPLATE.format(slug=slug), encoding="utf-8")


def self_check(root: Path, preset: str) -> list[str]:
    problems: list[str] = []
    forbidden = ["project-skeleton", "project_skeleton", "devctl_skeleton", "skeleton.localhost"]
    for path, text in iter_text_files(root):
        rel = path.relative_to(root)
        if str(rel) not in MARKER_EXEMPT_FILES:
            for line_no, line in enumerate(text.splitlines(), start=1):
                if (match_any(BLOCK_OPEN_PATTERNS, line)
                        or match_any(BLOCK_CLOSE_PATTERNS, line)
                        or match_any(LINE_SUFFIX_PATTERNS, line)):
                    problems.append(f"{rel}:{line_no}: leftover preset marker")
        for needle in forbidden:
            if needle in text:
                problems.append(f"{rel}: contains forbidden reference {needle!r}")
    return problems


def write_version_file(root: Path, ref: str, preset: str) -> None:
    versions_dir = root / ".versions"
    versions_dir.mkdir(exist_ok=True)
    (versions_dir / "current.json").write_text(
        json.dumps({"ref": ref, "preset": preset}, indent=2) + "\n", encoding="utf-8"
    )


def current_skeleton_ref(root: Path) -> str:
    return manifest_version(root)


def run_validations(root: Path) -> None:
    subprocess.run([sys.executable, "scripts/smoke.py"], cwd=root, check=True)
    if shutil.which("docker"):
        subprocess.run(
            ["docker", "compose", "--env-file", ".env.example",
             "-f", ".docker/compose.yml", "config"],
            cwd=root, check=True, stdout=subprocess.DEVNULL,
        )
    else:
        print("init: docker not found, skipped compose config validation")


def print_summary(slug: str, preset: str, planned: dict) -> None:
    print(f"\nInitialized {slug!r} with preset {preset!r}.")
    print(f"Removed {len(planned['removals'])} template paths; "
          f"pruned markers in {len(planned['pruned'])} files.")
    print("\nNext steps:")
    print("  1. Review the diff, then commit.")
    print("  2. devctl make setup && devctl up")
    print("  3. Set unique preferred_ports in .devctl.json "
          "(defaults 8080/3306/6379/8025 collide with other projects).")
    print("  4. Review LICENSE and SECURITY.md for this project.")
    print("  5. package-lock.json was reformatted; the next 'npm install' normalizes it.")


def prompt_slug() -> str:
    while True:
        slug = input("Project slug (e.g. billing-api): ").strip()
        if not SLUG_PATTERN.fullmatch(slug):
            print("  slug must match [a-z][a-z0-9-]* (example: billing-api)")
            continue
        if "skeleton" in slug:
            print("  slug must not contain 'skeleton' (reserved template name)")
            continue
        return slug


def prompt_preset() -> str:
    print("Presets:")
    for i, name in enumerate(PRESETS, start=1):
        print(f"  {i}. {name}")
    while True:
        choice = input(f"Preset [1-{len(PRESETS)} or name]: ").strip()
        if choice in PRESETS:
            return choice
        if choice.isdigit() and 1 <= int(choice) <= len(PRESETS):
            return PRESETS[int(choice) - 1]
        print(f"  enter a number 1-{len(PRESETS)} or one of: {', '.join(PRESETS)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a real project from the skeleton template."
    )
    parser.add_argument("slug", nargs="?", help="project name, [a-z][a-z0-9-]* (example: billing-api)")
    parser.add_argument("--preset", choices=PRESETS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="skip the clean-git-tree check")
    args = parser.parse_args(argv)

    missing = [name for name, value in (("slug", args.slug), ("--preset", args.preset)) if value is None]
    if missing and not sys.stdin.isatty():
        parser.error(f"the following arguments are required: {', '.join(missing)}")
    if args.slug is None:
        args.slug = prompt_slug()
    if args.preset is None:
        args.preset = prompt_preset()

    if not SLUG_PATTERN.fullmatch(args.slug):
        parser.error("slug must match [a-z][a-z0-9-]* (example: billing-api)")
    if "skeleton" in args.slug:
        parser.error("slug must not contain 'skeleton' (reserved template name)")
    if not args.force and not git_is_clean(ROOT):
        parser.error("git tree is not clean; commit or stash first (or use --force)")

    try:
        skeleton_ref = current_skeleton_ref(ROOT)
    except MissingVersionError as exc:
        parser.error(str(exc))

    planned = plan_changes(ROOT, args.preset)
    if args.dry_run:
        print("Would remove:")
        for rel in planned["removals"]:
            print(f"  {rel}")
        print("Would prune preset markers in:")
        for rel in planned["pruned"]:
            print(f"  {rel}")
        print(f"Would rebrand to {args.slug!r} (preset {args.preset!r}) and regenerate README.md")
        return 0

    apply_removals_and_pruning(ROOT, planned)
    install_preset.install(args.preset, root=ROOT, force=True, skip_docker_validate=True)
    rebrand_devctl_profile(ROOT, args.slug)
    rebrand_env_example(ROOT, args.slug, args.preset)
    rebrand_packages(ROOT, args.slug, args.preset)
    rebrand_text_references(ROOT, args.slug)
    write_readme(ROOT, args.slug)
    problems = self_check(ROOT, args.preset)
    if problems:
        print("init: self-check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    run_validations(ROOT)
    write_version_file(ROOT, skeleton_ref, args.preset)
    print_summary(args.slug, args.preset, planned)
    return 0


if __name__ == "__main__":
    sys.exit(main())
