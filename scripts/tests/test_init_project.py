#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "init-project.py"
sys.path.insert(0, str(MODULE_PATH.parent))
_spec = importlib.util.spec_from_file_location("init_project", MODULE_PATH)
init_project = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(init_project)

import skeleton_manifest

TEMPLATE_ONLY_FIXTURE = init_project.TEMPLATE_ONLY


def make_tree(files: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp())
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


class PlanChangesTest(unittest.TestCase):
    def setUp(self):
        self._orig = init_project.MARKED_FILES
        init_project.MARKED_FILES = ["Makefile"]

    def tearDown(self):
        init_project.MARKED_FILES = self._orig

    def test_prunes_marked_files_and_does_not_touch_presets(self):
        root = make_tree({
            "Makefile": "# >>> preset:template\nskeleton.init:\n# <<< preset\nhelp:\n",
            ".presets/laravel/composer.json": "{}",
            ".presets/next/package.json": "{}",
        })
        planned = init_project.plan_changes(root, "laravel")
        self.assertNotIn("preset:template", planned["pruned"]["Makefile"])
        self.assertIn("help:", planned["pruned"]["Makefile"])
        self.assertEqual(planned["removals"], TEMPLATE_ONLY_FIXTURE)

    def test_missing_marked_file_is_error(self):
        root = make_tree({})
        with self.assertRaises(init_project.InitError):
            init_project.plan_changes(root, "next")


class RebrandTest(unittest.TestCase):
    def test_devctl_profile(self):
        root = make_tree({".devctl.json": json.dumps({
            "name": "skeleton", "compose_project_name": "devctl_skeleton",
            "env": {"PROJECT_NAME": "devctl_skeleton"}})})
        init_project.rebrand_devctl_profile(root, "billing-api")
        data = json.loads((root / ".devctl.json").read_text())
        self.assertEqual(data["name"], "billing-api")
        self.assertEqual(data["compose_project_name"], "devctl_billing_api")
        self.assertEqual(data["env"]["PROJECT_NAME"], "devctl_billing_api")

    def test_env_example(self):
        root = make_tree({".env.example": "PROJECT_NAME=devctl_skeleton\nAPP_PRESET=laravel\nX=1\n"})
        init_project.rebrand_env_example(root, "billing-api", "next")
        text = (root / ".env.example").read_text()
        self.assertIn("PROJECT_NAME=devctl_billing_api\n", text)
        self.assertIn("APP_PRESET=next\n", text)
        self.assertIn("X=1\n", text)

    def test_text_references(self):
        root = make_tree({"docs/x.md": "see http://skeleton.localhost and devctl_skeleton, project_skeleton, project-skeleton\n"})
        init_project.rebrand_text_references(root, "shop")
        text = (root / "docs/x.md").read_text()
        self.assertEqual(text, "see http://shop.localhost and devctl_shop, devctl_shop, shop\n")

    def test_skeleton_slug_rejected(self):
        with self.assertRaises(SystemExit):
            init_project.main(["my-skeleton", "--preset", "next", "--dry-run", "--force"])

    def test_package_names_next(self):
        root = make_tree({
            "apps/package.json": json.dumps({"name": "project-skeleton-next"}),
            "apps/package-lock.json": json.dumps(
                {"name": "project-skeleton-next",
                 "packages": {"": {"name": "project-skeleton-next"}}}),
        })
        init_project.rebrand_packages(root, "shop", "next")
        self.assertEqual(json.loads((root / "apps/package.json").read_text())["name"], "shop")
        lock = json.loads((root / "apps/package-lock.json").read_text())
        self.assertEqual(lock["name"], "shop")
        self.assertEqual(lock["packages"][""]["name"], "shop")


class DockerScriptsSurviveInitTest(unittest.TestCase):
    def setUp(self):
        self._orig = init_project.MARKED_FILES
        init_project.MARKED_FILES = ["Makefile"]

    def tearDown(self):
        init_project.MARKED_FILES = self._orig

    def test_all_preset_arms_remain_after_init_with_any_single_preset(self):
        root = make_tree({
            "Makefile": "help:\n",
            ".docker/nginx/entrypoint.sh": (
                "case \"$preset\" in\n"
                "# >>> preset:laravel\n  laravel) ;;\n# <<< preset\n"
                "# >>> preset:next\n  next) ;;\n# <<< preset\n"
                "# >>> preset:legacy\n  legacy) ;;\n# <<< preset\nesac\n"
            ),
        })
        planned = init_project.plan_changes(root, "laravel")
        self.assertNotIn(".docker/nginx/entrypoint.sh", planned["pruned"])


class VersionFileTest(unittest.TestCase):
    def test_write_version_file(self):
        root = make_tree({})
        init_project.write_version_file(root, "v1.2.3", "laravel")
        data = json.loads((root / ".versions/current.json").read_text())
        self.assertEqual(data, {"ref": "v1.2.3", "preset": "laravel"})

    def test_ref_comes_from_the_manifest_stamp_not_project_git(self):
        root = make_tree({"skeleton.manifest.json": json.dumps({"version": "v1.1.1"})})
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "project commit"],
            cwd=root, check=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()

        ref = init_project.current_skeleton_ref(root)

        self.assertEqual("v1.1.1", ref)
        self.assertNotEqual(head, ref)

    def test_ref_refuses_to_guess_when_stamp_is_absent(self):
        root = make_tree({"skeleton.manifest.json": json.dumps({"presets": ["laravel"]})})
        with self.assertRaises(skeleton_manifest.MissingVersionError):
            init_project.current_skeleton_ref(root)


class SelfCheckTest(unittest.TestCase):
    def test_flags_leftover_marker_and_forbidden_reference(self):
        root = make_tree({
            "a.txt": "x  # preset:next\n",
            "b.txt": "visit skeleton.localhost\n",
            "c.md": "<!-- >>> preset:legacy -->\n",
        })
        problems = init_project.self_check(root, "laravel")
        joined = "\n".join(problems)
        self.assertIn("a.txt", joined)
        self.assertIn("b.txt", joined)
        self.assertIn("c.md", joined)

    def test_clean_tree_passes(self):
        root = make_tree({"a.txt": "hello\n"})
        self.assertEqual(init_project.self_check(root, "laravel"), [])

    def test_does_not_flag_infra_template_markers_as_leftover(self):
        root = make_tree({
            ".presets/_infra/Makefile.tmpl": "# >>> preset:laravel\nlaravel-only:\n# <<< preset\n",
        })
        self.assertEqual(init_project.self_check(root, "laravel"), [])

    def test_does_not_flag_docker_preset_dispatch_scripts_as_leftover(self):
        root = make_tree({
            ".docker/nginx/entrypoint.sh": (
                "#!/bin/sh\ncase \"$preset\" in\n"
                "# >>> preset:laravel\n  laravel) ;;\n# <<< preset\n"
                "# >>> preset:next\n  next) ;;\n# <<< preset\nesac\n"
            ),
        })
        self.assertEqual(init_project.self_check(root, "laravel"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
