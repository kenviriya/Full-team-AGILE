from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
WORKFLOW = (ROOT / "skills/sprint/SKILL.md").read_text()
README = (ROOT / "README.md").read_text()


CONFLICT_KINDS = frozenset(
    {
        "path",
        "contract",
        "schema",
        "migration",
        "generated-artifact",
        "lockfile",
        "configuration",
        "fixture",
        "external-test-resource",
    }
)


def validate_dependencies(items: dict[str, dict[str, object]]) -> None:
    for item_id, item in items.items():
        dependencies = item["dependsOn"]
        if item_id in dependencies or any(dependency not in items for dependency in dependencies):
            raise ValueError("invalid dependency")

    visiting, visited = set(), set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise ValueError("dependency cycle")
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in items[item_id]["dependsOn"]:
            visit(dependency)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in items:
        visit(item_id)


def ready_items(items: dict[str, dict[str, object]]) -> set[str]:
    return {
        item_id
        for item_id, item in items.items()
        if item["status"] == "planned"
        and all(items[dependency]["status"] == "done" for dependency in item["dependsOn"])
    }


def block_dependents(items: dict[str, dict[str, object]], failed_item: str) -> set[str]:
    blocked = set()
    changed = True
    while changed:
        changed = False
        for item_id, item in items.items():
            if item_id != failed_item and item["status"] == "planned" and any(
                dependency == failed_item or dependency in blocked
                for dependency in item["dependsOn"]
            ):
                item["status"] = "blocked"
                blocked.add(item_id)
                changed = True
    return blocked


def conflicts(left: dict[str, object], right: dict[str, object]) -> bool:
    if left["repository"] == right["repository"]:
        return True
    left_resources = left["resources"]
    right_resources = right["resources"]
    if left_resources is None or right_resources is None:
        return True
    return bool(
        {
            (kind, name)
            for kind, name in left_resources
            if kind in CONFLICT_KINDS
        }
        & {
            (kind, name)
            for kind, name in right_resources
            if kind in CONFLICT_KINDS
        }
    )


def select_dispatch_batch(items: dict[str, dict[str, object]]) -> set[str]:
    batch = set()
    for item_id in sorted(ready_items(items)):
        if not any(conflicts(items[item_id], items[selected]) for selected in batch):
            batch.add(item_id)
    return batch


def launch_results(items: dict[str, dict[str, object]], started: set[str]) -> None:
    for item_id in items:
        if item_id in started:
            items[item_id]["status"] = "running"
        else:
            items[item_id]["status"] = "ready"
            items[item_id]["launchFailure"] = "delegate did not start"


class SprintWorkflowTests(unittest.TestCase):
    def test_dependency_validation_rejects_self_references_and_cycles(self):
        with self.assertRaisesRegex(ValueError, "invalid dependency"):
            validate_dependencies({"api": {"dependsOn": ["api"]}})
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            validate_dependencies(
                {
                    "api": {"dependsOn": ["web"]},
                    "web": {"dependsOn": ["api"]},
                }
            )

    def test_only_completed_dependencies_make_an_item_ready(self):
        items = {
            "api": {"dependsOn": [], "status": "done"},
            "web": {"dependsOn": ["api"], "status": "planned"},
            "docs": {"dependsOn": ["web"], "status": "planned"},
        }

        self.assertEqual(ready_items(items), {"web"})

    def test_failure_blocks_transitive_dependents_but_not_independent_work(self):
        items = {
            "api": {"dependsOn": [], "status": "failed"},
            "web": {"dependsOn": ["api"], "status": "planned"},
            "e2e": {"dependsOn": ["web"], "status": "planned"},
            "docs": {"dependsOn": [], "status": "planned"},
        }

        self.assertEqual(block_dependents(items, "api"), {"web", "e2e"})
        self.assertEqual(items["docs"]["status"], "planned")

    def test_different_repositories_with_disjoint_resources_can_run_in_parallel(self):
        api = {"repository": "api", "resources": {("contract", "saved-searches")}}
        docs = {"repository": "docs", "resources": {("path", "docs/searches.md")}}
        web = {"repository": "web", "resources": {("contract", "saved-searches")}}
        api_docs = {"repository": "api", "resources": {("path", "docs/searches.md")}}
        unknown = {"repository": "docs", "resources": None}

        self.assertFalse(conflicts(api, docs))
        self.assertTrue(conflicts(api, web))
        self.assertTrue(conflicts(api, api_docs))
        self.assertTrue(conflicts(api, unknown))

    def test_dispatch_batch_includes_only_ready_nonconflicting_items(self):
        items = {
            "api": {
                "dependsOn": [],
                "status": "planned",
                "repository": "api",
                "resources": {("contract", "saved-searches")},
            },
            "docs": {
                "dependsOn": [],
                "status": "planned",
                "repository": "docs",
                "resources": {("path", "docs/searches.md")},
            },
            "web": {
                "dependsOn": [],
                "status": "planned",
                "repository": "web",
                "resources": {("contract", "saved-searches")},
            },
            "follow-up": {
                "dependsOn": ["api"],
                "status": "planned",
                "repository": "e2e",
                "resources": {("path", "tests/e2e")},
            },
        }

        self.assertEqual(select_dispatch_batch(items), {"api", "docs"})

    def test_failed_batch_launch_preserves_feature_id_and_returns_item_to_ready(self):
        items = {
            "api": {"status": "ready", "featureId": "api--20260727t000000z--a1b2c3d4"},
            "docs": {"status": "ready", "featureId": "docs--20260727t000000z--d4c3b2a1"},
        }

        launch_results(items, {"api"})

        self.assertEqual(items["api"]["status"], "running")
        self.assertEqual(items["docs"]["status"], "ready")
        self.assertEqual(items["docs"]["featureId"], "docs--20260727t000000z--d4c3b2a1")
        self.assertEqual(items["docs"]["launchFailure"], "delegate did not start")

    def test_workflow_delegates_parallel_feature_batches_without_reimplementing_feature_lifecycle(self):
        self.assertTrue((ROOT / "skills/sprint/SKILL.md").is_file())
        self.assertIn("name: sprint", WORKFLOW)
        self.assertIn("full-team-agile:feature", WORKFLOW)
        self.assertIn("non-Git invocation parent is a multi-repository workspace container", WORKFLOW)
        self.assertIn("preserve its exact root and basename", WORKFLOW)
        self.assertIn("Sprint must not independently scan or infer child repositories", WORKFLOW)
        self.assertIn("selected repository's existing primary checkout", WORKFLOW)
        self.assertIn("existing primary checkout", WORKFLOW)
        self.assertIn("primary-checkout validation", WORKFLOW)
        self.assertIn("create a fallback checkout", WORKFLOW)
        self.assertIn("Pass that preserved workspace context and each item's explicit workspace-relative repository scope", WORKFLOW)
        self.assertIn("sprint must not imply all child repositories", WORKFLOW)
        self.assertIn("single parallel dispatch", WORKFLOW)
        self.assertIn("one separate feature delegate per selected ready item", WORKFLOW)
        self.assertIn("assign and persist each selected item's feature ID and record its launch as pending", WORKFLOW)
        self.assertIn("Mark an item `running` only after its delegate starts", WORKFLOW)
        self.assertIn("retry only that same feature assignment on a later dispatch", WORKFLOW)
        self.assertIn("feature-id=<assigned-feature-id>", WORKFLOW)
        self.assertIn("Feature State.md is authoritative", WORKFLOW)
        self.assertIn("linked-worktree or actual-cwd mismatch", WORKFLOW)
        self.assertIn("must not create, select, repair, or retry another checkout automatically", WORKFLOW)
        self.assertIn("product-manager, conditional UX, backend/frontend implementation, QA, and code-review agents", WORKFLOW)
        self.assertIn("Sprint must not directly delegate those lifecycle agents", WORKFLOW)
        self.assertIn("must not create, reset, switch, merge, delete, or clean up feature branches", WORKFLOW)
        self.assertIn("done` sprint may be released only through the explicit `full-team-agile:release` workflow", WORKFLOW)
        self.assertNotIn("- **questions:**", WORKFLOW)
        self.assertNotIn("- **implementation:**", WORKFLOW)
        self.assertNotIn("- **cleanup:**", WORKFLOW)

    def test_workflow_keeps_sprint_and_feature_records_separate_and_requires_integration(self):
        self.assertIn(
            "Set `<sprint-directory>` to `<artifact-root>/Sprints/<workspace-name>/<sprint-id>/`",
            WORKFLOW,
        )
        self.assertIn("<sprint-directory>/State.md", WORKFLOW)
        self.assertIn("<sprint-directory>/01-sprint-plan.md", WORKFLOW)
        self.assertIn("<sprint-directory>/02-integration-report.md", WORKFLOW)
        self.assertIn("<sprint-directory>/03-sprint-recap.md", WORKFLOW)
        self.assertIn("Obsidian MCP vault tools only", WORKFLOW)
        self.assertIn("artifactRoot", WORKFLOW)
        self.assertIn("exact feature State.md reference", WORKFLOW)
        self.assertIn("stop if both exist", WORKFLOW)
        self.assertIn("Never relocate artifacts", WORKFLOW)
        self.assertIn("02-integration-report.md", WORKFLOW)
        self.assertIn("03-sprint-recap.md", WORKFLOW)
        self.assertIn("For every terminal sprint status (`done`, `failed`, or `blocked`)", WORKFLOW)
        self.assertIn("only when every item is `done`", WORKFLOW)
        self.assertIn("passing QA and approved review evidence", WORKFLOW)
        self.assertIn("never claim a passing integration gate for a non-`done` sprint", WORKFLOW)
        self.assertIn("do not automatically roll back, reopen, merge, reset, delete, or clean up", WORKFLOW)

    def test_readme_advertises_the_sprint_workflow(self):
        self.assertIn("`sprint` skill", README)
        self.assertIn("/full-team-agile:sprint", README)
        self.assertIn("Sprints/<workspace-name>/<sprint-id>/", README)
        self.assertIn("non-Git parent folder", README)
        self.assertIn("multi-repository workspace container", README)
        self.assertIn("explicit workspace-relative repository scope", README)
        self.assertIn("parallel `feature` workflows", README)
        self.assertIn("03-sprint-recap.md", README)
        self.assertIn("integration gate", README)


if __name__ == "__main__":
    unittest.main()
