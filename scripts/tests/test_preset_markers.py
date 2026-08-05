#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preset_markers


class PruneTextTest(unittest.TestCase):
    def test_keeps_matching_block_and_strips_markers(self):
        text = "a\n# >>> preset:laravel,legacy\nb\n# <<< preset\nc\n"
        self.assertEqual(preset_markers.prune_text(text, "laravel", "f"), "a\nb\nc\n")

    def test_drops_non_matching_block_with_markers(self):
        text = "a\n# >>> preset:next\nb\n# <<< preset\nc\n"
        self.assertEqual(preset_markers.prune_text(text, "laravel", "f"), "a\nc\n")

    def test_template_tag_is_always_dropped(self):
        text = "# >>> preset:template\nx\n# <<< preset\ny\n"
        for preset in preset_markers.PRESETS:
            self.assertEqual(preset_markers.prune_text(text, preset, "f"), "y\n")

    def test_line_suffix_kept_and_stripped(self):
        text = "keep = 1  # preset:next\ndrop = 2  # preset:laravel\n"
        self.assertEqual(preset_markers.prune_text(text, "next", "f"), "keep = 1\n")

    def test_html_comment_markers(self):
        text = "<!-- >>> preset:legacy -->\n- item\n<!-- <<< preset -->\nline <!-- preset:next -->\n"
        self.assertEqual(preset_markers.prune_text(text, "legacy", "f"), "- item\n")
        self.assertEqual(preset_markers.prune_text(text, "next", "f"), "line\n")

    def test_unknown_tag_raises(self):
        with self.assertRaises(preset_markers.MarkupError):
            preset_markers.prune_text("# >>> preset:bogus\nx\n# <<< preset\n", "next", "f")

    def test_nested_block_raises(self):
        text = "# >>> preset:next\n# >>> preset:legacy\n# <<< preset\n# <<< preset\n"
        with self.assertRaises(preset_markers.MarkupError):
            preset_markers.prune_text(text, "next", "f")

    def test_unclosed_block_raises(self):
        with self.assertRaises(preset_markers.MarkupError):
            preset_markers.prune_text("# >>> preset:next\nx\n", "next", "f")

    def test_stray_close_raises(self):
        with self.assertRaises(preset_markers.MarkupError):
            preset_markers.prune_text("# <<< preset\n", "next", "f")


if __name__ == "__main__":
    unittest.main(verbosity=2)
