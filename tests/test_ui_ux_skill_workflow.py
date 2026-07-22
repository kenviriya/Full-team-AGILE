from dataclasses import dataclass
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
WORKFLOW = (ROOT / "skills/feature/SKILL.md").read_text()
UX_DESIGNER = (ROOT / "agents/ux-designer.md").read_text()
FRONTEND_ENGINEER = (ROOT / "agents/frontend-engineer.md").read_text()


@dataclass(frozen=True)
class SkillMatch:
    name: str
    purpose_match: int
    ui_need_match: int
    specificity: int


def declared_skills(agent: str) -> set[str]:
    frontmatter = agent.split("---", 2)[1]
    skills = re.search(r"^skills:\n((?:  - .+\n)+)", frontmatter, re.MULTILINE)
    if not skills:
        return set()
    return {line.removeprefix("  - ") for line in skills.group(1).splitlines()}


def evaluate_selection_contract(agent: str, candidates: list[SkillMatch]) -> str | None:
    """Evaluate the documented delegation rule, not a host runtime API."""
    eligible = [candidate for candidate in candidates if candidate.name in declared_skills(agent)]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda candidate: (
            -candidate.purpose_match,
            -candidate.ui_need_match,
            -candidate.specificity,
            candidate.name,
        ),
    ).name


class UiUxSkillWorkflowTests(unittest.TestCase):
    def test_selection_uses_task_purpose_then_ui_need_then_specificity(self):
        candidates = [
            SkillMatch("frontend-design", purpose_match=3, ui_need_match=1, specificity=1),
            SkillMatch("design-taste-frontend", purpose_match=3, ui_need_match=2, specificity=1),
            SkillMatch("user-ui-audit", purpose_match=4, ui_need_match=4, specificity=4),
        ]

        self.assertEqual(
            evaluate_selection_contract(FRONTEND_ENGINEER, candidates),
            "design-taste-frontend",
        )
        self.assertEqual(
            evaluate_selection_contract(
                FRONTEND_ENGINEER,
                [
                    SkillMatch("frontend-design", 3, 2, 1),
                    SkillMatch("design-taste-frontend", 3, 2, 2),
                ],
            ),
            "design-taste-frontend",
        )

    def test_selection_uses_declared_skills_and_deterministic_final_tie_breaker(self):
        candidates = [
            SkillMatch("design-taste-frontend", 3, 2, 2),
            SkillMatch("frontend-design", 3, 2, 2),
            SkillMatch("user-ui-audit", 4, 4, 4),
        ]

        selected_skill = evaluate_selection_contract(FRONTEND_ENGINEER, candidates)

        self.assertEqual(selected_skill, "design-taste-frontend")
        self.assertIn(selected_skill, declared_skills(FRONTEND_ENGINEER))
        self.assertNotIn("user-ui-audit", declared_skills(FRONTEND_ENGINEER))

    def test_selection_returns_one_fallback_when_no_declared_skill_is_applicable(self):
        self.assertIsNone(
            evaluate_selection_contract(
                UX_DESIGNER,
                [SkillMatch("frontend-design", 3, 3, 3)],
            )
        )
        self.assertIn("If no frontmatter-declared skill is applicable, select none", WORKFLOW)
        self.assertIn("record one warning", WORKFLOW)

    def test_workflow_and_agents_restrict_use_to_frontmatter_attached_skills(self):
        precedence = (
            "user request and approved PRD; repository conventions and existing UI patterns; "
            "selected skill; bundled Full-team-AGILE guidance"
        )
        self.assertIn(precedence, WORKFLOW)
        self.assertIn("Match only skills in that list", WORKFLOW)
        self.assertIn("most direct purpose match for the delegated task", WORKFLOW)
        self.assertIn("strongest match for the feature's UI/UX needs", WORKFLOW)
        self.assertIn("most specific documented purpose", WORKFLOW)
        self.assertIn("lexicographically earliest declared skill name", WORKFLOW)
        self.assertIn("Do not perform this matching for product, backend, QA, or review work", WORKFLOW)
        self.assertIn("Use frontmatter-declared UI/UX skills only", UX_DESIGNER)
        self.assertIn("Use frontmatter-declared UI/UX skills only", FRONTEND_ENGINEER)
        self.assertNotIn("design-taste-frontend-v1", UX_DESIGNER)
        self.assertNotIn("design-taste-frontend-v1", FRONTEND_ENGINEER)


if __name__ == "__main__":
    unittest.main()
