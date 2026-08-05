#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / ".docker" / "compose.yml"
ENV_FILE = ROOT / ".env.example"
POLL_INTERVAL = 3


def fail(message: str) -> None:
    print(f"wait-for-healthy: {message}", file=sys.stderr)
    raise SystemExit(1)


def compose_command(profiles: list[str]) -> list[str]:
    cmd = ["docker", "compose", "--env-file", str(ENV_FILE), "-f", str(COMPOSE_FILE)]
    for profile in profiles:
        cmd += ["--profile", profile]
    return cmd


def container_id(compose_cmd: list[str], service: str) -> str | None:
    result = subprocess.run(
        [*compose_cmd, "ps", "-q", service], cwd=ROOT, capture_output=True, text=True,
    )
    return result.stdout.strip() or None


def readiness(container: str) -> tuple[bool, str]:
    health = subprocess.run(
        ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{end}}", container],
        capture_output=True, text=True,
    ).stdout.strip()
    if health:
        return health == "healthy", f"health={health}"
    status = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}", container],
        capture_output=True, text=True,
    ).stdout.strip()
    return status == "running", f"status={status}"


def dump_diagnostics(compose_cmd: list[str], services: list[str]) -> None:
    for service in services:
        print(f"\n----- {service}: docker compose ps -----", file=sys.stderr)
        subprocess.run([*compose_cmd, "ps", service], cwd=ROOT)
        print(f"----- {service}: docker compose logs (tail 50) -----", file=sys.stderr)
        subprocess.run([*compose_cmd, "logs", "--tail", "50", service], cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start Compose services and wait for real readiness (healthy, or running if no healthcheck)."
    )
    parser.add_argument("services", nargs="+", help="Compose service names to start and wait on")
    parser.add_argument("--profile", action="append", default=[], help="Compose profile to enable (repeatable)")
    parser.add_argument("--timeout", type=int, default=150, help="Seconds to wait before failing (default: 150)")
    args = parser.parse_args()

    compose_cmd = compose_command(args.profile)
    deadline = time.monotonic() + args.timeout

    try:
        up = subprocess.run(
            [*compose_cmd, "up", "-d", *args.services], cwd=ROOT, timeout=max(deadline - time.monotonic(), 0),
        )
    except subprocess.TimeoutExpired:
        dump_diagnostics(compose_cmd, sorted(args.services))
        fail(f"docker compose up -d {' '.join(args.services)} did not finish within {args.timeout}s")
    if up.returncode != 0:
        fail(f"docker compose up -d {' '.join(args.services)} failed (see output above)")

    pending = set(args.services)
    while pending:
        for service in list(pending):
            container = container_id(compose_cmd, service)
            if container is None:
                continue
            ready, detail = readiness(container)
            if ready:
                print(f"wait-for-healthy: {service} ready ({detail})")
                pending.discard(service)
        if not pending:
            break
        if time.monotonic() >= deadline:
            dump_diagnostics(compose_cmd, sorted(pending))
            fail(f"timed out after {args.timeout}s waiting for: {', '.join(sorted(pending))}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
