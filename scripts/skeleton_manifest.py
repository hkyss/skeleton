#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

MANIFEST_FILENAME = "skeleton.manifest.json"


class MissingVersionError(RuntimeError):
    pass


def load_manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST_FILENAME).read_text(encoding="utf-8"))


def manifest_version(root: Path) -> str:
    version = load_manifest(root).get("version")
    if not version:
        raise MissingVersionError(
            f"{MANIFEST_FILENAME} has no 'version'. It is stamped when a release "
            "is cut; a working tree built from an unreleased checkout has to set "
            "it before a project can be initialized from this skeleton."
        )
    return version
