#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

MODULE_PATH = SCRIPTS_DIR / "update-skeleton.py"
_spec = importlib.util.spec_from_file_location("update_skeleton", MODULE_PATH)
update_skeleton = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_skeleton)


class SemverKeyTest(unittest.TestCase):
    def test_valid_tag(self):
        self.assertEqual(update_skeleton._semver_key("v1.2.3"), (1, 2, 3))

    def test_rejects_non_v_prefix(self):
        self.assertIsNone(update_skeleton._semver_key("1.2.3"))

    def test_rejects_non_numeric_parts(self):
        self.assertIsNone(update_skeleton._semver_key("v1.2.x"))

    def test_sorts_numerically_not_lexically(self):
        tags = ["v1.9.0", "v1.10.0", "v1.2.0"]
        self.assertEqual(max(tags, key=update_skeleton._semver_key), "v1.10.0")


class OwnedMatchesTest(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(update_skeleton._owned_matches("Makefile", ["Makefile"]))
        self.assertFalse(update_skeleton._owned_matches("Makefile2", ["Makefile"]))

    def test_glob_prefix_match(self):
        patterns = [".docker/**"]
        self.assertTrue(update_skeleton._owned_matches(".docker/compose.yml", patterns))
        self.assertTrue(update_skeleton._owned_matches(".docker", patterns))
        self.assertFalse(update_skeleton._owned_matches("docs/.docker/x", patterns))
        self.assertFalse(update_skeleton._owned_matches("dockerfile", patterns))


import tempfile as _tempfile
from pathlib import Path as _Path


class MergeFileTest(unittest.TestCase):
    def test_clean_merge_when_base_matches_mine(self):
        with _tempfile.TemporaryDirectory() as tmp:
            mine_path = _Path(tmp) / "f.txt"
            mine_path.write_text("hello\n", encoding="utf-8")
            merged, has_conflict = update_skeleton.merge_file(mine_path, "hello\n", "hello world\n")
            self.assertEqual(merged, "hello world\n")
            self.assertFalse(has_conflict)

    def test_conflict_when_both_sides_changed_the_same_line(self):
        with _tempfile.TemporaryDirectory() as tmp:
            mine_path = _Path(tmp) / "f.txt"
            mine_path.write_text("mine\n", encoding="utf-8")
            merged, has_conflict = update_skeleton.merge_file(mine_path, "base\n", "theirs\n")
            self.assertTrue(has_conflict)
            self.assertIn("<<<<<<<", merged)

    def test_clean_merge_is_not_flagged_as_conflict_even_when_content_contains_marker_text(self):
        with _tempfile.TemporaryDirectory() as tmp:
            mine_path = _Path(tmp) / "f.txt"
            content = "print('<<<<<<< literal marker text, not a real conflict')\n"
            mine_path.write_text(content, encoding="utf-8")
            merged, has_conflict = update_skeleton.merge_file(mine_path, content, content)
            self.assertFalse(has_conflict)
            self.assertEqual(merged, content)


class PlanUpdateTest(unittest.TestCase):
    def test_added_removed_common_split(self):
        base_files = {"a.txt", "b.txt"}
        target_files = {"a.txt", "c.txt"}
        added = sorted(target_files - base_files)
        removed = sorted(base_files - target_files)
        common = sorted(base_files & target_files)
        self.assertEqual(added, ["c.txt"])
        self.assertEqual(removed, ["b.txt"])
        self.assertEqual(common, ["a.txt"])


import json
import subprocess as _subprocess
import unittest.mock as _mock


class MergeFileErrorHandlingTest(unittest.TestCase):
    def test_hard_error_raises_instead_of_writing_empty_content(self):
        with _tempfile.TemporaryDirectory() as tmp:
            mine_path = _Path(tmp) / "f.txt"
            mine_path.write_text("mine\n", encoding="utf-8")
            fake_result = _subprocess.CompletedProcess(
                args=[], returncode=-1, stdout="", stderr="fatal: cannot merge binary files"
            )
            with _mock.patch.object(update_skeleton.subprocess, "run", return_value=fake_result):
                with self.assertRaises(update_skeleton.UpdateError):
                    update_skeleton.merge_file(mine_path, "base\n", "theirs\n")


def _git(cwd: Path, *args: str) -> None:
    _subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_skeleton_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "skeleton-upstream"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")

    manifest_v1 = {
        "presets": ["laravel", "next", "legacy"],
        "marked_files": [],
        "skeleton_owned": [".docker/compose.yml"],
        "project_owned": ["apps/**"],
        "template_only": ["skeleton.manifest.json"],
    }
    _write(repo, "skeleton.manifest.json", json.dumps(manifest_v1))
    _write(repo, ".docker/compose.yml", "line-1\nline-2\nline-3\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "v1")
    _git(repo, "tag", "v1.0.0")

    manifest_v2 = dict(manifest_v1)
    manifest_v2["skeleton_owned"] = [".docker/compose.yml", ".docker/new-file.yml"]
    _write(repo, "skeleton.manifest.json", json.dumps(manifest_v2))
    _write(repo, ".docker/compose.yml", "line-1\nline-2-upstream-change\nline-3\n")
    _write(repo, ".docker/new-file.yml", "brand new\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "v2")
    _git(repo, "tag", "v2.0.0")

    return repo


def make_project_repo(tmp_path: Path, skeleton_repo: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "test@example.com")
    _git(project, "config", "user.name", "test")

    _write(project, ".docker/compose.yml", "line-1\nline-2-local-change\nline-3\n")
    _write(project, "apps/laravel/index.php", "<?php // untouched\n")
    _write(project, ".versions/current.json", json.dumps({"ref": "v1.0.0", "preset": "laravel"}))
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "init from v1.0.0")

    _git(project, "remote", "add", update_skeleton.SKELETON_REMOTE_NAME, str(skeleton_repo))
    return project


class UpdateIntegrationTest(unittest.TestCase):
    def test_full_flow_against_project_root(self):
        with _tempfile.TemporaryDirectory() as tmp:
            tmp_path = _Path(tmp)
            skeleton_repo = make_skeleton_repo(tmp_path)
            project = make_project_repo(tmp_path, skeleton_repo)

            original_root = update_skeleton.ROOT
            update_skeleton.ROOT = project
            try:
                rc = update_skeleton.main(["--to", "v2.0.0"])
            finally:
                update_skeleton.ROOT = original_root

            self.assertEqual(rc, 1)

            apps_content = (project / "apps/laravel/index.php").read_text(encoding="utf-8")
            self.assertEqual(apps_content, "<?php // untouched\n")

            merged = (project / ".docker/compose.yml").read_text(encoding="utf-8")
            self.assertIn("<<<<<<<", merged)

            new_file = (project / ".docker/new-file.yml").read_text(encoding="utf-8")
            self.assertEqual(new_file, "brand new\n")

            version = json.loads((project / ".versions/current.json").read_text())
            self.assertEqual(version["ref"], "v1.0.0")

    def test_clean_merge_advances_version_and_rerun_is_noop(self):
        with _tempfile.TemporaryDirectory() as tmp:
            tmp_path = _Path(tmp)
            skeleton_repo = make_skeleton_repo(tmp_path)
            project = tmp_path / "project"
            project.mkdir()
            _git(project, "init", "-q")
            _git(project, "config", "user.email", "test@example.com")
            _git(project, "config", "user.name", "test")
            _write(project, ".docker/compose.yml", "line-1\nline-2\nline-3\n")
            _write(project, "apps/laravel/index.php", "<?php // untouched\n")
            _write(project, ".versions/current.json", json.dumps({"ref": "v1.0.0", "preset": "laravel"}))
            _git(project, "add", "-A")
            _git(project, "commit", "-q", "-m", "init from v1.0.0")
            _git(project, "remote", "add", update_skeleton.SKELETON_REMOTE_NAME, str(skeleton_repo))

            original_root = update_skeleton.ROOT
            update_skeleton.ROOT = project
            try:
                rc = update_skeleton.main(["--to", "v2.0.0"])
                self.assertEqual(rc, 0)
                version = json.loads((project / ".versions/current.json").read_text())
                self.assertEqual(version["ref"], "v2.0.0")

                rc2 = update_skeleton.main([])
                self.assertEqual(rc2, 0)
            finally:
                update_skeleton.ROOT = original_root


def make_skeleton_repo_with_template_file(tmp_path: Path) -> Path:
    repo = tmp_path / "skeleton-upstream-tmpl"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")

    manifest = {
        "presets": ["laravel", "next", "legacy"],
        "marked_files": [],
        "skeleton_owned": [".presets/_infra/Makefile.tmpl"],
        "project_owned": ["apps/**"],
        "template_only": ["skeleton.manifest.json"],
    }
    _write(repo, "skeleton.manifest.json", json.dumps(manifest))
    _write(
        repo, ".presets/_infra/Makefile.tmpl",
        "# >>> preset:laravel\nlaravel-only:\n# <<< preset\n"
        "# >>> preset:next\nnext-only:\n# <<< preset\n",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "v1")
    _git(repo, "tag", "v1.0.0")

    _write(
        repo, ".presets/_infra/Makefile.tmpl",
        "# >>> preset:laravel\nlaravel-only:\n\techo added\n# <<< preset\n"
        "# >>> preset:next\nnext-only:\n# <<< preset\n",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "v2")
    _git(repo, "tag", "v2.0.0")
    return repo


class SkeletonOwnedButUnmarkedTest(unittest.TestCase):
    def test_template_file_syncs_with_markers_intact(self):
        with _tempfile.TemporaryDirectory() as tmp:
            tmp_path = _Path(tmp)
            skeleton_repo = make_skeleton_repo_with_template_file(tmp_path)
            project = tmp_path / "project"
            project.mkdir()
            _git(project, "init", "-q")
            _git(project, "config", "user.email", "test@example.com")
            _git(project, "config", "user.name", "test")
            _write(
                project, ".presets/_infra/Makefile.tmpl",
                "# >>> preset:laravel\nlaravel-only:\n# <<< preset\n"
                "# >>> preset:next\nnext-only:\n# <<< preset\n",
            )
            _write(project, ".versions/current.json", json.dumps({"ref": "v1.0.0", "preset": "laravel"}))
            _git(project, "add", "-A")
            _git(project, "commit", "-q", "-m", "init from v1.0.0")
            _git(project, "remote", "add", update_skeleton.SKELETON_REMOTE_NAME, str(skeleton_repo))

            original_root = update_skeleton.ROOT
            update_skeleton.ROOT = project
            try:
                rc = update_skeleton.main(["--to", "v2.0.0"])
                self.assertEqual(rc, 0)
            finally:
                update_skeleton.ROOT = original_root

            text = (project / ".presets/_infra/Makefile.tmpl").read_text(encoding="utf-8")
            self.assertIn("# >>> preset:laravel", text)
            self.assertIn("# >>> preset:next", text)
            self.assertIn("next-only:", text)


class TagPollutionTest(unittest.TestCase):
    def test_latest_tag_ignores_projects_own_tags_and_fetch_does_not_touch_local_tags(self):
        with _tempfile.TemporaryDirectory() as tmp:
            tmp_path = _Path(tmp)
            skeleton_repo = make_skeleton_repo(tmp_path)
            project = tmp_path / "project"
            project.mkdir()
            _git(project, "init", "-q")
            _git(project, "config", "user.email", "test@example.com")
            _git(project, "config", "user.name", "test")
            _write(project, ".docker/compose.yml", "line-1\nline-2\nline-3\n")
            _write(project, "apps/laravel/index.php", "<?php // untouched\n")
            _write(project, ".versions/current.json", json.dumps({"ref": "v1.0.0", "preset": "laravel"}))
            _git(project, "add", "-A")
            _git(project, "commit", "-q", "-m", "init from v1.0.0")
            _git(project, "tag", "v9.9.9")
            _git(project, "remote", "add", update_skeleton.SKELETON_REMOTE_NAME, str(skeleton_repo))

            original_root = update_skeleton.ROOT
            update_skeleton.ROOT = project
            try:
                update_skeleton.ensure_remote(project)
                update_skeleton.fetch_tags(project)
                self.assertEqual(update_skeleton.latest_tag(project), "v2.0.0")
                project_tags = _subprocess.run(
                    ["git", "tag", "-l"], cwd=project, capture_output=True, text=True
                ).stdout.split()
                self.assertEqual(project_tags, ["v9.9.9"])
            finally:
                update_skeleton.ROOT = original_root


if __name__ == "__main__":
    unittest.main(verbosity=2)
