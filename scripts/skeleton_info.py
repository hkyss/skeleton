#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_info(root: Path) -> dict:
    devctl = _read_json(root / ".devctl.json")
    name = devctl.get("name", "")

    version_path = root / ".versions" / "current.json"
    if version_path.is_file():
        version = _read_json(version_path)
        return {
            "initialized": True,
            "name": name,
            "preset": version["preset"],
            "ref": version["ref"],
        }

    return {"initialized": False, "name": name}


def format_info(info: dict) -> str:
    if info["initialized"]:
        return (
            f"Project:  {info['name']}\n"
            f"Preset:   {info['preset']}\n"
            f"Skeleton: {info['ref']}\n"
        )
    return (
        f"Project:  {info['name']} (not yet initialized)\n"
        "This is still the raw skeleton template.\n"
        "Run: devctl make skeleton.init name=<name> preset=<preset>\n"
    )


def main() -> None:
    print(format_info(collect_info(ROOT)), end="")


if __name__ == "__main__":
    main()
