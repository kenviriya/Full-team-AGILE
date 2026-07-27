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

    def test_workflow_delegates_to_feature_without_reimplementing_feature_lifecycle(self):
        self.assertTrue((ROOT / "skills/sprint/SKILL.md").is_file())
        self.assertIn("name: sprint", WORKFLOW)
        self.assertIn("full-team-agile:feature", WORKFLOW)
        self.assertIn("one separate agent per ready item", WORKFLOW)
        self.assertIn("feature-id=<assigned-feature-id>", WORKFLOW)
        self.assertIn("Feature State.md is authoritative", WORKFLOW)
        self.assertIn("Sprint must not directly delegate implementation, QA, or review agents", WORKFLOW)
        self.assertIn("must not create, reset, switch, merge, delete, or clean up feature branches", WORKFLOW)
        self.assertNotIn("- **questions:**", WORKFLOW)
        self.assertNotIn("- **implementation:**", WORKFLOW)
        self.assertNotIn("- **cleanup:**", WORKFLOW)

    def test_workflow_keeps_sprint_and_feature_records_separate_and_requires_integration(self):
        self.assertIn("Sprints/<workspace-name>/<sprint-id>/State.md", WORKFLOW)
        self.assertIn("Features/<workspace-name>/<feature-id>/State.md", WORKFLOW)
        self.assertIn("02-integration-report.md", WORKFLOW)
        self.assertIn("only when every item is `done`", WORKFLOW)
        self.assertIn("passing QA and approved review evidence", WORKFLOW)
        self.assertIn("do not automatically roll back, reopen, merge, reset, delete, or clean up", WORKFLOW)

    def test_readme_advertises_the_sprint_workflow(self):
        self.assertIn("`sprint` skill", README)
        self.assertIn("/full-team-agile:sprint", README)
        self.assertIn("Sprints/<workspace-name>/<sprint-id>/", README)
        self.assertIn("integration gate", README)


if __name__ == "__main__":
    unittest.main()
