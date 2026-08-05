#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from preset_markers import prune_text

ROOT = Path(__file__).resolve().parents[1]


class InstallPresetError(RuntimeError):
    pass


def available_presets(presets_dir: Path) -> list[str]:
    return sorted(
        p.name for p in presets_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


_DEPENDENCY_DIRS = (
    "vendor",
    "node_modules",
    "frontend/node_modules",
    ".next",
    "dist",
    "build",
)


def apps_is_clean(root: Path) -> bool:
    pathspecs = ["apps", *(f":(exclude)apps/{d}" for d in _DEPENDENCY_DIRS)]
    result = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "--", *pathspecs],
        cwd=root, capture_output=True, text=True,
    )
    return result.returncode == 0 and not result.stdout.strip()


def wipe_apps(apps_dir: Path) -> None:
    if apps_dir.exists():
        shutil.rmtree(apps_dir)
    apps_dir.mkdir(parents=True)


def copy_preset(preset: str, presets_dir: Path, apps_dir: Path) -> None:
    source = presets_dir / preset
    for item in source.iterdir():
        dest = apps_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def render_active_makefile(preset: str, tmpl_path: Path) -> str:
    text = tmpl_path.read_text(encoding="utf-8")
    return prune_text(text, preset, str(tmpl_path))


def write_active_makefile(preset: str, tmpl_path: Path, active_mk: Path) -> None:
    active_mk.parent.mkdir(parents=True, exist_ok=True)
    active_mk.write_text(render_active_makefile(preset, tmpl_path), encoding="utf-8")


def _apply_env_updates(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    found = set()
    out = []
    for line in lines:
        key = next((k for k in updates if line.startswith(f"{k}=")), None)
        if key:
            out.append(f"{key}={updates[key]}\n")
            found.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in found:
            out.append(f"{key}={value}\n")
    path.write_text("".join(out), encoding="utf-8")


def set_env_app_preset(preset: str, env_path: Path, example_path: Path) -> None:
    if not env_path.is_file():
        shutil.copy2(example_path, env_path)
    updates = {"APP_PRESET": preset, "COMPOSE_PROFILES": preset}
    _apply_env_updates(env_path, updates)
    _apply_env_updates(example_path, updates)


def write_version_preset(preset: str, version_path: Path) -> None:
    if not version_path.is_file():
        return
    data = json.loads(version_path.read_text(encoding="utf-8"))
    data["preset"] = preset
    version_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def validate_compose(root: Path) -> None:
    result = subprocess.run(
        ["docker", "compose", "--env-file", ".env", "-f", ".docker/compose.yml", "config"],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise InstallPresetError(f"docker compose config failed:\n{result.stderr}")


def install(
    preset: str,
    *,
    force: bool = False,
    root: Path = ROOT,
    skip_docker_validate: bool = False,
) -> None:
    presets_dir = root / ".presets"
    if preset not in available_presets(presets_dir):
        available = ", ".join(available_presets(presets_dir))
        raise InstallPresetError(f"unknown preset {preset!r}; available: {available}")
    if not force and not apps_is_clean(root):
        raise InstallPresetError(
            "apps/ has uncommitted changes; commit or stash first (or pass --force)"
        )
    wipe_apps(root / "apps")
    copy_preset(preset, presets_dir, root / "apps")
    write_active_makefile(
        preset, presets_dir / "_infra" / "Makefile.tmpl", root / ".make" / "active.mk"
    )
    set_env_app_preset(preset, root / ".env", root / ".env.example")
    write_version_preset(preset, root / ".versions" / "current.json")
    if not skip_docker_validate and shutil.which("docker"):
        validate_compose(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize a preset into apps/.")
    parser.add_argument("--use", required=True, dest="preset")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        install(args.preset, force=args.force)
    except InstallPresetError as error:
        print(f"install-preset: {error}", file=sys.stderr)
        return 1
    print(f"install-preset: apps/ now running preset {args.preset!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
