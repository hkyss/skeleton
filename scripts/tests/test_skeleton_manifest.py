#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import preset_markers
import skeleton_manifest


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.data = skeleton_manifest.load_manifest(ROOT)

    def test_valid_json_object(self):
        self.assertIsInstance(self.data, dict)

    def test_required_keys_present(self):
        for key in (
            "version", "presets", "marked_files",
            "skeleton_owned", "project_owned", "template_only",
        ):
            self.assertIn(key, self.data)

    def test_version_looks_like_a_release_tag(self):
        self.assertRegex(self.data["version"], r"^v\d+\.\d+\.\d+$")


    def test_categories_do_not_overlap(self):
        owned = set(self.data["skeleton_owned"])
        project = set(self.data["project_owned"])
        template = set(self.data["template_only"])
        self.assertEqual(owned & project, set())
        self.assertEqual(owned & template, set())
        self.assertEqual(project & template, set())

    def test_presets_match_preset_markers_module(self):
        self.assertEqual(tuple(self.data["presets"]), preset_markers.PRESETS)

    def test_marked_files_actually_contain_marker_syntax(self):
        for rel in self.data["marked_files"]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            has_block = any(p.search(text) or p.match(text) for p in preset_markers.BLOCK_OPEN_PATTERNS)
            has_suffix = any(
                p.search(line)
                for line in text.splitlines()
                for p in preset_markers.LINE_SUFFIX_PATTERNS
            )
            self.assertTrue(
                has_block or has_suffix,
                f"{rel} is listed in marked_files but contains no preset markers",
            )


class ManifestVersionTest(unittest.TestCase):
    def _tree(self, manifest: dict) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / skeleton_manifest.MANIFEST_FILENAME).write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return root

    def test_returns_the_stamped_version(self):
        root = self._tree({"version": "v2.3.4"})
        self.assertEqual("v2.3.4", skeleton_manifest.manifest_version(root))

    def test_raises_when_stamp_is_missing(self):
        root = self._tree({"presets": ["laravel"]})
        with self.assertRaises(skeleton_manifest.MissingVersionError):
            skeleton_manifest.manifest_version(root)

    def test_raises_when_stamp_is_empty(self):
        root = self._tree({"version": ""})
        with self.assertRaises(skeleton_manifest.MissingVersionError):
            skeleton_manifest.manifest_version(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
