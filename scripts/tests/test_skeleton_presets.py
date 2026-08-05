#!/usr/bin/env python3
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

MODULE_PATH = SCRIPTS_DIR / "skeleton_presets.py"
_spec = importlib.util.spec_from_file_location("skeleton_presets", MODULE_PATH)
skeleton_presets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skeleton_presets)


def make_presets_dir(root: Path, names: list[str]) -> None:
    presets_dir = root / ".presets"
    (presets_dir / "_infra").mkdir(parents=True)
    for name in names:
        (presets_dir / name).mkdir(parents=True)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class ListPresetsTest(unittest.TestCase):
    def test_lists_preset_dirs_excluding_infra(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_presets_dir(root, ["laravel", "next", "legacy"])
            info = skeleton_presets.collect_presets(root)
            self.assertEqual(info, {"active": None, "presets": ["laravel", "legacy", "next"]})

    def test_reports_active_preset_when_initialized(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_presets_dir(root, ["laravel", "next", "legacy"])
            write_json(root / ".versions/current.json", {"ref": "v1.2.3", "preset": "laravel"})
            info = skeleton_presets.collect_presets(root)
            self.assertEqual(info, {"active": "laravel", "presets": ["laravel", "legacy", "next"]})


class FormatPresetsTest(unittest.TestCase):
    def test_formats_without_active_preset(self):
        text = skeleton_presets.format_presets({"active": None, "presets": ["laravel", "legacy", "next"]})
        self.assertIn("laravel", text)
        self.assertIn("next", text)
        self.assertIn("legacy", text)
        self.assertIn("skeleton.init", text)

    def test_formats_with_active_preset_marked(self):
        text = skeleton_presets.format_presets({"active": "laravel", "presets": ["laravel", "legacy", "next"]})
        self.assertIn("laravel (active)", text)
        self.assertIn("skeleton.preset use=", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
