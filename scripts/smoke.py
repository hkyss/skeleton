#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV = {
    "APP_PRESET",
    "DB_CONNECTION",
    "DB_DATABASE",
    "DB_HOST",
    "DB_PASSWORD",
    "DB_PORT",
    "DB_ROOT_PASSWORD",
    "DB_USERNAME",
    "MAIL_HOST",
    "MAIL_PORT",
    "NODE_ENV",
    "PORT_DB",
    "PORT_HTTP",
    "PORT_MAIL",
    "PORT_REDIS",
    "PROJECT_NAME",
    "REDIS_HOST",
    "REDIS_PORT",
    "VITE_API_BASE_URL",
}


def fail(message: str) -> None:
    print(f"smoke: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{path.relative_to(ROOT)} contains invalid JSON: {error.msg}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def parse_env_example(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"{path.relative_to(ROOT)} contains an invalid env line: {raw_line}")
        name, value = line.split("=", 1)
        values[name] = value
    return values


def assert_devctl_profile() -> None:
    profile = read_json(ROOT / ".devctl.json")
    expected = {
        "adapter": "docker-compose",
        "compose_file": ".docker/compose.yml",
        "env_file": ".env",
        "http_port_env": "PORT_HTTP",
        "health_check_path": "/health",
        "health_check_statuses": [204],
    }
    for key, value in expected.items():
        if profile.get(key) != value:
            fail(f".devctl.json field {key!r} must be {value!r}")

    extra_ports = profile.get("extra_port_envs")
    if extra_ports != ["PORT_DB", "PORT_REDIS", "PORT_MAIL"]:
        fail(".devctl.json extra_port_envs must be ['PORT_DB', 'PORT_REDIS', 'PORT_MAIL']")

    managed_ports = [profile["http_port_env"], *extra_ports]  # type: ignore[index]
    if len(managed_ports) != len(set(managed_ports)):
        fail(".devctl.json managed port env names must be unique")

    preferred_ports = profile.get("preferred_ports")
    if not isinstance(preferred_ports, list) or len(preferred_ports) != len(managed_ports):
        fail(".devctl.json preferred_ports must match managed port count")


def assert_env_example() -> None:
    names = set(parse_env_example(ROOT / ".env.example"))
    missing = sorted(REQUIRED_ENV - names)
    if missing:
        fail(f".env.example is missing required variables: {', '.join(missing)}")


def assert_compose_profiles_matches_preset() -> None:
    values = parse_env_example(ROOT / ".env.example")
    preset = values.get("APP_PRESET", "none")
    if preset == "none":
        return
    if values.get("COMPOSE_PROFILES") != preset:
        fail(
            ".env.example COMPOSE_PROFILES must match APP_PRESET "
            f"({values.get('COMPOSE_PROFILES')!r} != {preset!r}); "
            "run `devctl make skeleton.preset use=<preset>` to resync"
        )


def assert_project_name_contract() -> None:
    profile = read_json(ROOT / ".devctl.json")
    env = profile.get("env")
    project_name = env.get("PROJECT_NAME") if isinstance(env, dict) else None
    if not isinstance(project_name, str) or not re.fullmatch(r"devctl_[a-z0-9_]+", project_name):
        fail(".devctl.json env.PROJECT_NAME must match devctl_<lowercase_name>")
    if profile.get("compose_project_name") != project_name:
        fail(".devctl.json compose_project_name must match env.PROJECT_NAME")
    example_name = parse_env_example(ROOT / ".env.example").get("PROJECT_NAME")
    if example_name != project_name:
        fail(
            ".env.example PROJECT_NAME must match .devctl.json env.PROJECT_NAME "
            f"({example_name!r} != {project_name!r})"
        )


def assert_no_legacy_old_name() -> None:
    old_name = "legacy" + "-php-vite"
    ignored_dirs = {".git", "node_modules", "vendor"}
    for path in ROOT.rglob("*"):
        if any(part in ignored_dirs for part in path.parts):
            continue
        relative = path.relative_to(ROOT)
        if old_name in str(relative):
            fail(f"old legacy preset path is still present: {relative}")
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if old_name in text:
                fail(f"old legacy preset name is still referenced in {relative}")


def assert_compose_uses_loopback_ports() -> None:
    compose = (ROOT / ".docker/compose.yml").read_text(encoding="utf-8")
    for port_name in ("PORT_HTTP", "PORT_DB", "PORT_REDIS", "PORT_MAIL"):
        pattern = rf"127\.0\.0\.1:\$\{{{re.escape(port_name)}\}}:"
        if not re.search(pattern, compose):
            fail(f".docker/compose.yml must publish {port_name} on 127.0.0.1")


def assert_active_makefile_is_valid_if_present() -> None:
    active_mk = ROOT / ".make" / "active.mk"
    if not active_mk.is_file():
        return
    if not shutil.which("make"):
        print(
            "smoke: 'make' not found, skipping .make/active.mk syntax check",
            file=sys.stderr,
        )
        return
    result = subprocess.run(
        ["make", "-n", "-f", str(active_mk)], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f".make/active.mk is not valid make syntax:\n{result.stderr}")


def assert_compose_config_valid_without_preset() -> None:
    env = dict(**{})
    result = subprocess.run(
        ["docker", "compose", "--env-file", ".env.example", "-f", ".docker/compose.yml", "config"],
        cwd=ROOT, capture_output=True, text=True, env={**_os_environ(), "APP_PRESET": "none"},
    )
    if result.returncode != 0:
        fail(f"docker compose config failed with APP_PRESET=none:\n{result.stderr}")


def _os_environ() -> dict[str, str]:
    import os
    return dict(os.environ)


def main() -> None:
    assert_devctl_profile()
    assert_env_example()
    assert_compose_profiles_matches_preset()
    assert_project_name_contract()
    assert_no_legacy_old_name()
    assert_compose_uses_loopback_ports()
    assert_active_makefile_is_valid_if_present()
    if shutil.which("docker"):
        assert_compose_config_valid_without_preset()
    print("smoke: ok")


if __name__ == "__main__":
    main()
