#!/usr/bin/env python3
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "smoke.py"
sys.path.insert(0, str(MODULE_PATH.parent))
_spec = importlib.util.spec_from_file_location("smoke", MODULE_PATH)
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)


def _with_root(root, fn):
    original_root = smoke.ROOT
    smoke.ROOT = root
    try:
        fn()
    finally:
        smoke.ROOT = original_root


class ActiveMakefileCheckTest(unittest.TestCase):
    def test_noop_when_no_active_makefile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _with_root(root, smoke.assert_active_makefile_is_valid_if_present)

    def test_passes_for_syntactically_valid_makefile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".make").mkdir()
            (root / ".make/active.mk").write_text("help:\n\t@echo ok\n", encoding="utf-8")
            _with_root(root, smoke.assert_active_makefile_is_valid_if_present)

    def test_fails_for_invalid_makefile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".make").mkdir()
            (root / ".make/active.mk").write_text("this is not valid make syntax\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                _with_root(root, smoke.assert_active_makefile_is_valid_if_present)


class ComposeProfilesMatchPresetTest(unittest.TestCase):
    def _run(self, env_text: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text(env_text, encoding="utf-8")
            _with_root(root, smoke.assert_compose_profiles_matches_preset)

    def test_none_preset_skips_check(self):
        self._run("APP_PRESET=none\n")

    def test_matching_profile_passes(self):
        self._run("APP_PRESET=laravel\nCOMPOSE_PROFILES=laravel\n")

    def test_missing_profile_fails(self):
        with self.assertRaises(SystemExit):
            self._run("APP_PRESET=laravel\n")

    def test_mismatched_profile_fails(self):
        with self.assertRaises(SystemExit):
            self._run("APP_PRESET=laravel\nCOMPOSE_PROFILES=next\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
