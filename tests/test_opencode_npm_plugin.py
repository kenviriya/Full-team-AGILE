import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PACKAGE = json.loads((ROOT / "package.json").read_text())


class OpenCodeNpmPluginTests(unittest.TestCase):
    def test_package_metadata_and_entrypoint_are_native_opencode_compatible(self):
        self.assertEqual(PACKAGE["name"], "opencode-full-team-agile")
        self.assertEqual(PACKAGE["version"], "0.6.1")
        self.assertEqual(PACKAGE["main"], "./opencode/index.js")
        self.assertEqual(PACKAGE["exports"], {".": "./opencode/index.js"})
        self.assertIn("@opencode-ai/plugin", PACKAGE["dependencies"])
        self.assertEqual(PACKAGE["repository"]["type"], "git")
        readme = (ROOT / "README.md").read_text()
        entrypoint = (ROOT / "opencode/index.js").read_text()
        self.assertIn('"plugin": ["opencode-full-team-agile"]', readme)
        self.assertIn("publish-ready but is not published", readme)
        self.assertIn("does not register or transform", readme)
        self.assertIn("full_team_agile_status", entrypoint)
        self.assertIn("does not run the Claude-only", entrypoint)

    @unittest.skipUnless(shutil.which("npm"), "npm is required for package validation")
    def test_packed_package_contains_runtime_and_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            packed = subprocess.run(
                ["npm", "pack", "--json", "--dry-run"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            contents = {item["path"] for item in json.loads(packed.stdout)[0]["files"]}
            self.assertTrue({"opencode/index.js", "skills/feature/SKILL.md", "LICENSE", "README.md"} <= contents)
            self.assertFalse(any(path.startswith(("tests/", "graphify-out/", ".claude-plugin/", ".codex-plugin/")) for path in contents))

            archive = subprocess.run(
                ["npm", "pack", "--json", "--pack-destination", str(staging)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            package = staging / json.loads(archive.stdout)[0]["filename"]
            with tarfile.open(package) as tar:
                tar.extractall(staging, filter="data")
            installed = staging / "package"
            subprocess.run(["npm", "install", "--ignore-scripts", "--no-package-lock"], cwd=installed, check=True, capture_output=True)
            subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "--eval",
                    "import plugin from './opencode/index.js'; if (!(await plugin()).tool.full_team_agile_status) process.exit(1)",
                ],
                cwd=installed,
                check=True,
            )


if __name__ == "__main__":
    unittest.main()
