#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "install-preset.py"
sys.path.insert(0, str(MODULE_PATH.parent))
_spec = importlib.util.spec_from_file_location("install_preset", MODULE_PATH)
install_preset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install_preset)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "test")

    (root / "apps").mkdir()
    (root / "apps/index.html").write_text("placeholder\n", encoding="utf-8")

    presets = root / ".presets"
    (presets / "laravel").mkdir(parents=True)
    (presets / "laravel/composer.json").write_text('{"name": "x"}\n', encoding="utf-8")
    (presets / "laravel/public").mkdir()
    (presets / "laravel/public/index.php").write_text("<?php\n", encoding="utf-8")

    (presets / "next").mkdir(parents=True)
    (presets / "next/package.json").write_text('{"name": "y"}\n', encoding="utf-8")

    (presets / "_infra").mkdir(parents=True)
    (presets / "_infra/Makefile.tmpl").write_text(
        "# >>> preset:laravel\nlaravel-only:\n\techo laravel\n# <<< preset\n"
        "# >>> preset:next\nnext-only:\n\techo next\n# <<< preset\n",
        encoding="utf-8",
    )

    (root / ".env.example").write_text("PROJECT_NAME=devctl_x\nAPP_PRESET=none\n", encoding="utf-8")
    (root / ".versions").mkdir()
    (root / ".versions/current.json").write_text(
        json.dumps({"ref": "v1.0.0", "preset": "none"}), encoding="utf-8"
    )

    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


class AvailablePresetsTest(unittest.TestCase):
    def test_lists_preset_dirs_excluding_underscore_prefixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            self.assertEqual(
                install_preset.available_presets(root / ".presets"),
                ["laravel", "next"],
            )


class InstallTest(unittest.TestCase):
    def test_copies_preset_into_apps_and_writes_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            install_preset.install(
                "laravel", root=root, skip_docker_validate=True
            )
            self.assertTrue((root / "apps/composer.json").is_file())
            self.assertTrue((root / "apps/public/index.php").is_file())
            self.assertFalse((root / "apps/index.html").exists())
            env_text = (root / ".env").read_text(encoding="utf-8")
            self.assertIn("APP_PRESET=laravel\n", env_text)
            self.assertIn("COMPOSE_PROFILES=laravel\n", env_text)
            version = json.loads((root / ".versions/current.json").read_text())
            self.assertEqual(version["preset"], "laravel")

    def test_renders_active_makefile_scoped_to_chosen_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            install_preset.install("laravel", root=root, skip_docker_validate=True)
            active = (root / ".make/active.mk").read_text(encoding="utf-8")
            self.assertIn("laravel-only:", active)
            self.assertNotIn("next-only:", active)

    def test_switching_preset_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            install_preset.install("laravel", root=root, skip_docker_validate=True)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "install laravel")

            install_preset.install("next", root=root, skip_docker_validate=True)
            self.assertTrue((root / "apps/package.json").is_file())
            self.assertFalse((root / "apps/composer.json").exists())
            active = (root / ".make/active.mk").read_text(encoding="utf-8")
            self.assertIn("next-only:", active)
            self.assertNotIn("laravel-only:", active)
            env_text = (root / ".env").read_text(encoding="utf-8")
            self.assertIn("APP_PRESET=next\n", env_text)
            self.assertIn("COMPOSE_PROFILES=next\n", env_text)

    def test_unknown_preset_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            with self.assertRaises(install_preset.InstallPresetError):
                install_preset.install("django", root=root, skip_docker_validate=True)

    def test_refuses_dirty_apps_tree_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            install_preset.install("laravel", root=root, skip_docker_validate=True)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "install laravel")
            (root / "apps/local-edit.txt").write_text("uncommitted\n", encoding="utf-8")

            with self.assertRaises(install_preset.InstallPresetError):
                install_preset.install("next", root=root, skip_docker_validate=True)

    def test_force_overrides_dirty_apps_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            install_preset.install("laravel", root=root, skip_docker_validate=True)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "install laravel")
            (root / "apps/local-edit.txt").write_text("uncommitted\n", encoding="utf-8")

            install_preset.install("next", root=root, force=True, skip_docker_validate=True)
            self.assertTrue((root / "apps/package.json").is_file())

    def test_refuses_when_apps_has_gitignored_content_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo2"
            root.mkdir()
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "test@example.com")
            _git(root, "config", "user.name", "test")
            (root / ".gitignore").write_text("apps/storage/*\n", encoding="utf-8")
            presets = root / ".presets"
            (presets / "laravel").mkdir(parents=True)
            (presets / "laravel/composer.json").write_text('{"name": "x"}\n', encoding="utf-8")
            (presets / "_infra").mkdir(parents=True)
            (presets / "_infra/Makefile.tmpl").write_text(
                "# >>> preset:laravel\nlaravel-only:\n\techo laravel\n# <<< preset\n",
                encoding="utf-8",
            )
            (root / "apps").mkdir()
            (root / ".env.example").write_text("PROJECT_NAME=devctl_x\nAPP_PRESET=none\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "init")

            install_preset.install("laravel", root=root, skip_docker_validate=True)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "install laravel")

            (root / "apps/storage").mkdir()
            (root / "apps/storage/dev.log").write_text("local dev data\n", encoding="utf-8")

            with self.assertRaises(install_preset.InstallPresetError):
                install_preset.install("laravel", root=root, skip_docker_validate=True)

    def test_switching_preset_does_not_require_force_when_only_dependency_dirs_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            (root / ".gitignore").write_text("apps/vendor/\napps/node_modules/\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "add gitignore")

            install_preset.install("laravel", root=root, skip_docker_validate=True)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "install laravel")

            (root / "apps/vendor").mkdir()
            (root / "apps/vendor/autoload.php").write_text("<?php\n", encoding="utf-8")

            install_preset.install("next", root=root, skip_docker_validate=True)
            self.assertTrue((root / "apps/package.json").is_file())

    def test_env_example_is_kept_in_sync_with_active_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            install_preset.install("laravel", root=root, skip_docker_validate=True)
            example_text = (root / ".env.example").read_text(encoding="utf-8")
            self.assertIn("APP_PRESET=laravel\n", example_text)
            self.assertIn("COMPOSE_PROFILES=laravel\n", example_text)


class SetEnvAppPresetTest(unittest.TestCase):
    def test_handles_env_file_missing_trailing_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_path = root / ".env"
            example_path = root / ".env.example"
            env_path.write_text("PROJECT_NAME=devctl_x", encoding="utf-8")
            example_path.write_text("PROJECT_NAME=devctl_x\nAPP_PRESET=none\n", encoding="utf-8")

            install_preset.set_env_app_preset("laravel", env_path, example_path)

            text = env_path.read_text(encoding="utf-8")
            self.assertIn("PROJECT_NAME=devctl_x\n", text)
            self.assertIn("APP_PRESET=laravel\n", text)
            self.assertIn("COMPOSE_PROFILES=laravel\n", text)
            self.assertNotIn("devctl_xAPP_PRESET", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
