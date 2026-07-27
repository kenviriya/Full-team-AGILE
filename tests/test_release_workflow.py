from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).parents[1]
WORKFLOW = (ROOT / "skills/release/SKILL.md").read_text()
README = (ROOT / "README.md").read_text()
CLAUDE_PLUGIN = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
CODEX_PLUGIN = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())


SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
RELEASE_ID = re.compile(r"^[a-z0-9]+(?:-+[a-z0-9]+)*$")


def release_inputs(mode: str, version: str, target: str, repositories: str | None) -> bool:
    if mode not in {"sprint", "feature"} or not SEMVER.fullmatch(version) or not target:
        return False
    return mode != "feature" or repositories in {"all", "api", "api,web"}


def resumable_steps(record: dict[str, bool]) -> list[str]:
    return [step for step in ("merge", "tag", "target", "push", "publish") if not record[step]]


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_requires_valid_explicit_scope(self):
        self.assertTrue(release_inputs("sprint", "1.2.3", "main", None))
        self.assertTrue(release_inputs("feature", "1.2.3-rc.1", "main", "api"))
        self.assertFalse(release_inputs("sprint", "v1.2.3", "main", None))
        self.assertFalse(release_inputs("sprint", "1.2.3", "", None))
        self.assertFalse(release_inputs("feature", "1.2.3", "main", None))

    def test_continuation_skips_completed_steps(self):
        record = {"merge": True, "tag": True, "target": True, "push": False, "publish": False}
        self.assertEqual(resumable_steps(record), ["push", "publish"])

    def test_workflow_defaults_to_sprint_and_keeps_feature_explicit(self):
        self.assertTrue((ROOT / "skills/release/SKILL.md").is_file())
        self.assertIn("name: release", WORKFLOW)
        self.assertIn("/release <sprint-id>", WORKFLOW)
        self.assertIn("/release feature <feature-id>", WORKFLOW)
        self.assertIn("A bare release target is a sprint ID", WORKFLOW)
        self.assertIn("Feature release is explicit", WORKFLOW)

    def test_workflow_requires_eligibility_explicit_inputs_and_durable_records(self):
        for phrase in (
            "Require `version=<major.minor.patch>`",
            "Require a non-empty `target=<branch>` every time",
            "Require a non-empty `remote=<remote>` every time",
            "require explicit workspace-relative `repositories=<path,...>` or `repositories=all`",
            "passing evidence in `02-integration-report.md`",
            "passing QA and approved review evidence",
            "Releases/<workspace-name>/<release-id>/State.md",
            "01-release-plan.md",
            "02-release-validation.md",
            "03-release-recap.md",
        ):
            self.assertIn(phrase, WORKFLOW)

    def test_workflow_requires_preflight_fresh_confirmation_and_safe_git_actions(self):
        for phrase in (
            "Persist a frozen preflight plan",
            "Request one fresh confirmation",
            "release/<release-id>",
            "with `--no-ff`",
            "create an annotated `v<version>` tag",
            "target branch, reverify that it still equals its captured preflight SHA",
            "push each updated target branch and its exact annotated `v<version>` tag",
        ):
            self.assertIn(phrase, WORKFLOW)
        for phrase in (
            "Never infer `main`",
            "Never infer all repositories",
            "must not stage arbitrary work, stash, reset, force-push, delete branches or tags, automatically roll back",
            "External publication is disabled by default",
            "Never store credentials, authorization headers, registry tokens",
        ):
            self.assertIn(phrase, WORKFLOW)

    def test_workflow_continues_only_incomplete_steps_and_recaps_terminal_state(self):
        self.assertIn("resuming only the incomplete step", WORKFLOW)
        self.assertIn("Do not recreate a completed merge, tag, target update, push, or external publication", WORKFLOW)
        self.assertIn("For every terminal release status (`done`, `failed`, or `blocked`)", WORKFLOW)
        self.assertIn("external publishing occurred only when separately confirmed", WORKFLOW)

    def test_documentation_and_manifest_versions_advertise_release(self):
        self.assertIn("`release` skill", README)
        self.assertIn("/full-team-agile:release", README)
        self.assertEqual(CLAUDE_PLUGIN["version"], "0.4.0")
        self.assertEqual(CLAUDE_PLUGIN["version"], CODEX_PLUGIN["version"])


if __name__ == "__main__":
    unittest.main()
