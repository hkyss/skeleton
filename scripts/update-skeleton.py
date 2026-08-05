#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from preset_markers import prune_text

ROOT = Path(__file__).resolve().parents[1]
SKELETON_REMOTE_NAME = "_skeleton-upstream"
SKELETON_REMOTE_URL = "https://github.com/hkyss/skeleton"
UPSTREAM_REF_PREFIX = "refs/skeleton-upstream-tags"


class UpdateError(RuntimeError):
    pass


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def version_file(root: Path) -> Path:
    return root / ".versions" / "current.json"


def read_version(root: Path) -> dict:
    path = version_file(root)
    if not path.is_file():
        raise UpdateError(
            f"{path.relative_to(root)} not found. This project predates "
            "skeleton.update; create it manually with the skeleton tag/SHA "
            'this project was initialized from, e.g. '
            '{"ref": "v1.0.0", "preset": "laravel"}'
        )
    return json.loads(path.read_text(encoding="utf-8"))


def write_version(root: Path, ref: str, preset: str) -> None:
    path = version_file(root)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"ref": ref, "preset": preset}, indent=2) + "\n", encoding="utf-8")


def git_is_clean(root: Path) -> bool:
    result = run_git(root, ["status", "--porcelain"])
    return result.returncode == 0 and not result.stdout.strip()


def ensure_remote(root: Path) -> None:
    result = run_git(root, ["remote"])
    if SKELETON_REMOTE_NAME not in result.stdout.split():
        subprocess.run(
            ["git", "remote", "add", SKELETON_REMOTE_NAME, SKELETON_REMOTE_URL],
            cwd=root, check=True,
        )


def fetch_tags(root: Path) -> None:
    subprocess.run(
        ["git", "fetch", "--no-tags", SKELETON_REMOTE_NAME,
         f"+refs/tags/*:{UPSTREAM_REF_PREFIX}/*"],
        cwd=root, check=True,
    )


def _upstream_ref(tag: str) -> str:
    return f"{UPSTREAM_REF_PREFIX}/{tag}"


def _semver_key(tag: str) -> tuple[int, int, int] | None:
    if not tag.startswith("v"):
        return None
    parts = tag[1:].split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def latest_tag(root: Path) -> str:
    result = run_git(root, ["for-each-ref", "--format=%(refname)", f"{UPSTREAM_REF_PREFIX}/"])
    if result.returncode != 0:
        raise UpdateError(f"cannot list fetched tags: {result.stderr.strip()}")
    prefix = f"{UPSTREAM_REF_PREFIX}/"
    tags = [
        ref[len(prefix):] for ref in result.stdout.splitlines()
        if ref.startswith(prefix) and _semver_key(ref[len(prefix):]) is not None
    ]
    if not tags:
        raise UpdateError(f"no semver tags found on remote {SKELETON_REMOTE_NAME!r}")
    return max(tags, key=_semver_key)


def show(root: Path, ref: str, path: str) -> str | None:
    result = run_git(root, ["show", f"{ref}:{path}"])
    return result.stdout if result.returncode == 0 else None


def load_manifest_at(root: Path, ref: str) -> dict:
    text = show(root, ref, "skeleton.manifest.json")
    if text is None:
        raise UpdateError(
            f"skeleton.manifest.json not found at {ref!r} — this skeleton "
            "version predates skeleton.update support."
        )
    return json.loads(text)


def _owned_matches(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
        elif path == pattern:
            return True
    return False


def owned_files_at(root: Path, ref: str, manifest: dict) -> set[str]:
    result = run_git(root, ["ls-tree", "-r", "--name-only", ref])
    if result.returncode != 0:
        raise UpdateError(f"cannot list files at {ref!r}: {result.stderr.strip()}")
    owned = manifest["skeleton_owned"]
    return {path for path in result.stdout.splitlines() if _owned_matches(path, owned)}


def merge_file(mine_path: Path, base_text: str | None, theirs_text: str) -> tuple[str, bool]:
    mine_text = mine_path.read_text(encoding="utf-8") if mine_path.is_file() else ""
    with tempfile.NamedTemporaryFile("w", suffix=".base", delete=False) as base_f:
        base_f.write(base_text or "")
    with tempfile.NamedTemporaryFile("w", suffix=".theirs", delete=False) as theirs_f:
        theirs_f.write(theirs_text)
    with tempfile.NamedTemporaryFile("w", suffix=".mine", delete=False) as mine_f:
        mine_f.write(mine_text)
    try:
        result = subprocess.run(
            ["git", "merge-file", "--stdout", mine_f.name, base_f.name, theirs_f.name],
            capture_output=True, text=True,
        )
        if result.returncode < 0:
            raise UpdateError(
                f"git merge-file failed on {mine_path.name}: {result.stderr.strip()}"
            )
        merged = result.stdout
        has_conflict = result.returncode > 0
    finally:
        for name in (base_f.name, theirs_f.name, mine_f.name):
            Path(name).unlink(missing_ok=True)
    return merged, has_conflict


def plan_update(root: Path, base_ref: str, target_ref: str) -> tuple[dict, dict]:
    base_manifest = load_manifest_at(root, base_ref)
    target_manifest = load_manifest_at(root, target_ref)
    base_files = owned_files_at(root, base_ref, base_manifest)
    target_files = owned_files_at(root, target_ref, target_manifest)
    plan = {
        "added": sorted(target_files - base_files),
        "removed": sorted(base_files - target_files),
        "common": sorted(base_files & target_files),
    }
    return plan, target_manifest


def apply_update(
    root: Path, base_ref: str, target_ref: str, preset: str, plan: dict, marked_files: set[str]
) -> dict:
    changed: list[str] = []
    conflicts: list[str] = []

    def _prune(text: str, path: str) -> str:
        return prune_text(text, preset, path) if path in marked_files else text

    def write_new(path: str) -> None:
        theirs = _prune(show(root, target_ref, path) or "", path)
        mine_path = root / path
        if not mine_path.is_file():
            mine_path.parent.mkdir(parents=True, exist_ok=True)
            mine_path.write_text(theirs, encoding="utf-8")
            changed.append(path)
            return
        merged, has_conflict = merge_file(mine_path, None, theirs)
        mine_path.write_text(merged, encoding="utf-8")
        (conflicts if has_conflict else changed).append(path)

    for path in plan["added"]:
        write_new(path)

    for path in plan["common"]:
        base = _prune(show(root, base_ref, path) or "", path)
        theirs = _prune(show(root, target_ref, path) or "", path)
        if base == theirs:
            continue
        mine_path = root / path
        if not mine_path.is_file():
            mine_path.parent.mkdir(parents=True, exist_ok=True)
            mine_path.write_text(theirs, encoding="utf-8")
            changed.append(path)
            continue
        original = mine_path.read_text(encoding="utf-8")
        merged, has_conflict = merge_file(mine_path, base, theirs)
        if merged == original:
            continue
        mine_path.write_text(merged, encoding="utf-8")
        (conflicts if has_conflict else changed).append(path)

    return {"changed": changed, "conflicts": conflicts, "deprecated": plan["removed"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync skeleton-owned files from upstream.")
    parser.add_argument("--to", help="target skeleton tag (default: latest semver tag)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        version = read_version(ROOT)
    except UpdateError as error:
        print(f"update-skeleton: {error}", file=sys.stderr)
        return 1
    base_tag, preset = version["ref"], version["preset"]

    ensure_remote(ROOT)
    fetch_tags(ROOT)
    try:
        target_tag = args.to or latest_tag(ROOT)
    except UpdateError as error:
        print(f"update-skeleton: {error}", file=sys.stderr)
        return 1

    if target_tag == base_tag:
        print(f"update-skeleton: already on {base_tag}")
        return 0

    if not args.dry_run and not git_is_clean(ROOT):
        print("update-skeleton: git tree is not clean; commit or stash first.", file=sys.stderr)
        return 1

    base_ref, target_ref = _upstream_ref(base_tag), _upstream_ref(target_tag)
    try:
        plan, target_manifest = plan_update(ROOT, base_ref, target_ref)
    except UpdateError as error:
        print(f"update-skeleton: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Would update from {base_tag} to {target_tag}:")
        for path in plan["added"]:
            print(f"  add    {path}")
        for path in plan["common"]:
            print(f"  merge  {path}")
        for path in plan["removed"]:
            print(f"  stale  {path} (no longer managed by skeleton)")
        return 0

    marked_files = set(target_manifest["marked_files"])
    try:
        result = apply_update(ROOT, base_ref, target_ref, preset, plan, marked_files)
    except UpdateError as error:
        print(f"update-skeleton: {error}", file=sys.stderr)
        return 1

    if not result["conflicts"]:
        write_version(ROOT, target_tag, preset)

    print(f"update-skeleton: {base_tag} -> {target_tag}")
    if result["changed"]:
        print("Changed:")
        for path in result["changed"]:
            print(f"  {path}")
    if result["conflicts"]:
        print("Conflicts (resolve manually, look for <<<<<<< markers):")
        for path in result["conflicts"]:
            print(f"  {path}")
    if result["deprecated"]:
        print("No longer managed by skeleton (remove manually if unwanted):")
        for path in result["deprecated"]:
            print(f"  {path}")
    if not result["changed"] and not result["conflicts"]:
        print("Nothing to do.")

    return 1 if result["conflicts"] else 0


if __name__ == "__main__":
    sys.exit(main())
