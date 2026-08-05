#!/usr/bin/env python3
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

MODULE_PATH = SCRIPTS_DIR / "skeleton_info.py"
_spec = importlib.util.spec_from_file_location("skeleton_info", MODULE_PATH)
skeleton_info = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skeleton_info)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class InitializedProjectTest(unittest.TestCase):
    def test_reports_name_preset_and_ref(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / ".devctl.json", {"name": "myproject"})
            write_json(root / ".versions/current.json", {"ref": "v1.2.3", "preset": "laravel"})
            info = skeleton_info.collect_info(root)
            self.assertEqual(info, {
                "initialized": True,
                "name": "myproject",
                "preset": "laravel",
                "ref": "v1.2.3",
            })


class UninitializedTemplateTest(unittest.TestCase):
    def test_reports_not_initialized(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / ".devctl.json", {"name": "skeleton"})
            info = skeleton_info.collect_info(root)
            self.assertEqual(info, {
                "initialized": False,
                "name": "skeleton",
            })


class FormatInfoTest(unittest.TestCase):
    def test_formats_initialized_project(self):
        text = skeleton_info.format_info({
            "initialized": True,
            "name": "myproject",
            "preset": "laravel",
            "ref": "v1.2.3",
        })
        self.assertIn("myproject", text)
        self.assertIn("laravel", text)
        self.assertIn("v1.2.3", text)

    def test_formats_uninitialized_template(self):
        text = skeleton_info.format_info({"initialized": False, "name": "skeleton"})
        self.assertIn("not yet initialized", text)
        self.assertIn("skeleton.init", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
