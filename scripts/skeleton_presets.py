#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _available_presets(presets_dir: Path) -> list[str]:
    return sorted(
        p.name for p in presets_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def collect_presets(root: Path) -> dict:
    presets = _available_presets(root / ".presets")

    version_path = root / ".versions" / "current.json"
    active = None
    if version_path.is_file():
        version = json.loads(version_path.read_text(encoding="utf-8"))
        active = version["preset"]

    return {"active": active, "presets": presets}


def format_presets(info: dict) -> str:
    lines = [
        f"{name} (active)" if name == info["active"] else name
        for name in info["presets"]
    ]
    text = "Available presets:\n" + "".join(f"  {line}\n" for line in lines)
    if info["active"] is None:
        text += "Use one with: devctl make skeleton.init name=<name> preset=<preset>\n"
    else:
        text += "Switch with: devctl make skeleton.preset use=<preset>\n"
    return text


def main() -> None:
    print(format_presets(collect_presets(ROOT)), end="")


if __name__ == "__main__":
    main()
