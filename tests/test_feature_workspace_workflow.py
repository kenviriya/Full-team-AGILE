from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = (ROOT / "skills/feature/SKILL.md").read_text()
README = (ROOT / "README.md").read_text()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=check
    )


def discover_repositories(workspace: Path) -> list[str]:
    workspace = workspace.resolve()
    repositories = []
    for child in sorted(path for path in workspace.iterdir() if path.is_dir() and not path.is_symlink()):
        result = git(child, "rev-parse", "--show-toplevel", check=False)
        if result.returncode:
            continue
        root = Path(result.stdout.strip()).resolve()
        if root == child.resolve() and root.parent == workspace:
            repositories.append(child.name)
    return repositories


def select_repositories(
    workspace: Path,
    detected: list[str],
    *,
    explicit: list[str] | None = None,
    cwd: Path | None = None,
    active_file: Path | None = None,
    root_confirmed: bool = False,
) -> list[str]:
    eligible = set(detected)
    if root_confirmed:
        eligible.add(".")

    def target(path: Path | None) -> str | None:
        if path is None:
            return None
        location = path if path.is_dir() else path.parent
        try:
            location.resolve().relative_to(workspace.resolve())
        except ValueError:
            return None
        while not location.exists() and location != workspace:
            location = location.parent
        result = git(location, "rev-parse", "--show-toplevel", check=False)
        if result.returncode:
            return None
        root = Path(result.stdout.strip()).resolve()
        relative = root.relative_to(workspace.resolve())
        candidate = "." if not relative.parts else relative.as_posix()
        return candidate if candidate in eligible else None

    if explicit:
        selected = [path for path in explicit if path in eligible]
        if len(selected) != len(explicit):
            raise ValueError("invalid or unconfirmed repository target")
        return list(dict.fromkeys(selected))
    inferred = target(cwd) or target(active_file)
    if inferred:
        return [inferred]
    return detected if len(detected) == 1 else []


def migrate_v2_state(state: dict[str, object], workspace: Path, root_confirmed: bool) -> dict[str, object]:
    repository = state.get("repository")
    if not isinstance(repository, dict) or Path(str(repository.get("root", ""))).resolve() != workspace.resolve():
        raise ValueError("legacy repository root does not match workspace")
    if not root_confirmed:
        raise ValueError("root repository confirmation required")
    return {
        "version": 3,
        "featureId": state["featureId"],
        "repositories": {".": {"path": ".", "rootConfirmed": True}},
    }


def registered_worktrees(repo: Path) -> str:
    return git(repo, "worktree", "list", "--porcelain").stdout


def registered_worktree_paths(repo: Path) -> set[Path]:
    return {
        Path(line.removeprefix("worktree ")).resolve()
        for line in registered_worktrees(repo).splitlines()
        if line.startswith("worktree ")
    }


def branch_is_occupied(repo: Path, branch: str) -> bool:
    current_worktree = None
    for line in registered_worktrees(repo).splitlines():
        if line.startswith("worktree "):
            current_worktree = Path(line.removeprefix("worktree ")).resolve()
        elif line == f"branch refs/heads/{branch}" and current_worktree != repo.resolve():
            return True
    return False


def create_or_reset_target(
    repo: Path,
    target: str,
    *,
    create_from_remote_confirmed: bool = False,
    destructive_reset_confirmed: bool = False,
) -> str:
    """Execute the documented checkout contract against an isolated repository."""
    remote_main = "origin/main"
    dirty = bool(git(repo, "status", "--porcelain").stdout)
    exists = git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{target}", check=False).returncode == 0

    if not exists:
        if dirty and not create_from_remote_confirmed:
            return "declined-create"
        base = remote_main if dirty else "HEAD"
        result = git(repo, "checkout", "-b", target, base, check=False)
        return "created" if result.returncode == 0 else "blocked-checkout"

    if branch_is_occupied(repo, target):
        return "blocked-occupied"

    if dirty:
        return "blocked-dirty-existing-target"

    if not destructive_reset_confirmed:
        return "declined-reset"

    if git(repo, "rev-parse", "--verify", "--quiet", f"{remote_main}^{{commit}}", check=False).returncode:
        return "blocked-remote-main"
    git(repo, "checkout", target)
    git(repo, "reset", "--hard", remote_main)
    return "reset"


def artifact(path: str, kind: str = "test") -> dict[str, str]:
    return {
        "path": path,
        "kind": kind,
        "createdBy": "qa-engineer",
        "recordedAt": "2026-07-22T03:00:00Z",
        "status": "active",
    }


def protected_branches_from_state(state: dict[str, object]) -> frozenset[str] | None:
    policy = state.get("repositoryPolicy", {})
    if not isinstance(policy, dict) or policy.get("valid", True) is not True:
        return None
    protected_branches = policy.get("protectedBranches", [])
    if not isinstance(protected_branches, list) or not all(
        isinstance(branch, str) and branch for branch in protected_branches
    ):
        return None
    return frozenset(protected_branches)


def repository_policy_from_file(repo: Path) -> dict[str, object]:
    source = repo / ".claude/full-team-agile.json"
    try:
        if not source.exists():
            return {"source": str(source), "protectedBranches": [], "valid": True}
        config = json.loads(source.read_text())
        protected_branches = config.get("protectedBranches", [])
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return {"source": str(source), "protectedBranches": [], "valid": False}
    if not isinstance(protected_branches, list) or not all(
        isinstance(branch, str) and branch for branch in protected_branches
    ):
        return {"source": str(source), "protectedBranches": [], "valid": False}
    return {"source": str(source), "protectedBranches": protected_branches, "valid": True}


def cleanup_temporary_artifacts(repo: Path, artifacts: list[dict[str, str]]) -> list[str]:
    """Remove only explicitly registered files inside an isolated repository."""
    outcomes = []
    paths = set()
    for artifact in artifacts:
        required = {"path", "kind", "createdBy", "recordedAt", "status"}
        if set(artifact) != required or artifact["kind"] not in {"test", "execution"} or artifact["status"] != "active":
            raise ValueError("invalid artifact registry entry")
        path = Path(artifact["path"])
        if path.as_posix() in paths:
            raise ValueError("duplicate artifact path")
        paths.add(path.as_posix())
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("invalid artifact path")
        parent = repo
        for part in path.parts[:-1]:
            parent /= part
            if parent.is_symlink():
                raise ValueError("temporary artifact path contains symlink")
        target = repo / path
        if target.is_symlink():
            target.unlink()
            outcomes.append("removed")
        elif target.is_file():
            target.unlink()
            outcomes.append("removed")
        elif target.exists():
            raise ValueError("temporary artifact is not a file")
        else:
            outcomes.append("alreadyAbsent")
    return outcomes


def delete_remote_feature_branch(
    repo: Path,
    feature_branch: str,
    remote: str,
    *,
    branch_created_by_plugin: bool,
    confirmed: bool,
    feature_id: str = "demo",
    repository_policy: dict[str, object] | None = None,
) -> str:
    protected_branches = protected_branches_from_state(
        repository_policy or {"repositoryPolicy": repository_policy_from_file(repo)}
    )
    if protected_branches is None:
        return "blocked-policy"
    if not confirmed or not branch_created_by_plugin:
        return "declined"
    if not feature_branch.startswith("feature/"):
        return "blocked-non-feature"
    if feature_branch != f"feature/{feature_id}":
        return "blocked-unrelated"
    if feature_branch in protected_branches:
        return "blocked-protected"
    if git(repo, "remote", "get-url", remote, check=False).returncode:
        return "blocked-remote"
    if git(repo, "ls-remote", "--exit-code", "--heads", remote, feature_branch, check=False).returncode:
        return "alreadyAbsent"
    result = git(repo, "push", remote, "--delete", feature_branch, check=False)
    return "deleted" if result.returncode == 0 else "blocked-delete"


def delete_feature_branch(
    repo: Path,
    feature_branch: str,
    return_branch: str,
    *,
    branch_created_by_plugin: bool,
    confirmed: bool,
    feature_id: str = "demo",
    repository_policy: dict[str, object] | None = None,
) -> str:
    protected_branches = protected_branches_from_state(
        repository_policy or {"repositoryPolicy": repository_policy_from_file(repo)}
    )
    if protected_branches is None:
        return "blocked-policy"
    if not confirmed or not branch_created_by_plugin:
        return "declined"
    if not feature_branch.startswith("feature/"):
        return "blocked-non-feature"
    if feature_branch != f"feature/{feature_id}":
        return "blocked-unrelated"
    if feature_branch in protected_branches:
        return "blocked-protected"
    if feature_branch == return_branch:
        return "blocked-return-branch"
    if git(repo, "status", "--porcelain").stdout:
        return "blocked-dirty"
    if branch_is_occupied(repo, feature_branch):
        return "blocked-occupied"
    if git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{return_branch}", check=False).returncode:
        return "blocked-return-branch"
    if git(repo, "merge-base", "--is-ancestor", feature_branch, return_branch, check=False).returncode:
        return "blocked-unmerged"
    git(repo, "switch", return_branch)
    result = git(repo, "branch", "-d", feature_branch, check=False)
    return "deleted" if result.returncode == 0 else "blocked-delete"


class FeatureWorkspaceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.remote = Path(self.tempdir.name) / "origin.git"
        self.repo.mkdir()
        self.remote.mkdir()
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test User")
        (self.repo / "tracked.txt").write_text("main\n")
        git(self.repo, "add", "tracked.txt")
        git(self.repo, "commit", "-m", "initial")
        git(self.repo, "branch", "-M", "main")
        git(self.remote, "init", "--bare")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    def tearDown(self):
        self.tempdir.cleanup()

    def commit_target_change(self, target: str = "feature/demo") -> str:
        git(self.repo, "checkout", "-b", target)
        (self.repo / "tracked.txt").write_text("target commit\n")
        git(self.repo, "commit", "-am", "target change")
        target_head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "checkout", "main")
        return target_head

    def test_immediate_child_detection_excludes_nested_and_accepts_linked_worktree(self):
        workspace = Path(self.tempdir.name) / "workspace"
        workspace.mkdir()
        api = workspace / "api"
        web_source = Path(self.tempdir.name) / "web-source"
        web = workspace / "web"
        nested = workspace / "group/nested"
        for repo in (api, web_source, nested):
            repo.mkdir(parents=True)
            git(repo, "init")
        git(web_source, "config", "user.email", "test@example.com")
        git(web_source, "config", "user.name", "Test User")
        (web_source / "tracked.txt").write_text("web\n")
        git(web_source, "add", "tracked.txt")
        git(web_source, "commit", "-m", "initial")
        git(web_source, "worktree", "add", str(web))
        (workspace / "notes").mkdir()
        external = Path(self.tempdir.name) / "external"
        external.mkdir()
        git(external, "init")
        (workspace / "external-link").symlink_to(external, target_is_directory=True)

        self.assertEqual(discover_repositories(workspace), ["api", "web"])

    def test_selection_precedence_boundaries_and_ambiguous_root(self):
        workspace = Path(self.tempdir.name) / "workspace"
        api = workspace / "api"
        web = workspace / "web"
        nested = api / "nested"
        for repo in (api, web, nested):
            repo.mkdir(parents=True)
            git(repo, "init")
        detected = discover_repositories(workspace)
        active_file = web / "src/app.py"

        self.assertEqual(
            select_repositories(workspace, detected, explicit=["api"], cwd=web, active_file=active_file),
            ["api"],
        )
        self.assertEqual(select_repositories(workspace, detected, cwd=web), ["web"])
        self.assertEqual(select_repositories(workspace, detected, active_file=active_file), ["web"])
        self.assertEqual(select_repositories(workspace, detected, cwd=workspace), [])
        self.assertEqual(select_repositories(workspace, detected, cwd=nested), [])
        self.assertEqual(select_repositories(workspace, detected, active_file=nested / "file.py"), [])
        self.assertEqual(select_repositories(workspace, detected, explicit=["api", "web"]), ["api", "web"])
        with self.assertRaisesRegex(ValueError, "invalid or unconfirmed"):
            select_repositories(workspace, detected, explicit=["group/nested"])
        with self.assertRaisesRegex(ValueError, "invalid or unconfirmed"):
            select_repositories(workspace, detected, explicit=["."])
        self.assertEqual(
            select_repositories(workspace, detected, explicit=["."], root_confirmed=True),
            ["."],
        )
        self.assertEqual(
            select_repositories(workspace, detected, active_file=Path(self.tempdir.name) / "outside.py"),
            [],
        )

    def test_sole_child_auto_selection_and_stale_state_rejection(self):
        workspace = Path(self.tempdir.name) / "workspace"
        api = workspace / "api"
        api.mkdir(parents=True)
        git(api, "init")
        detected = discover_repositories(workspace)

        self.assertEqual(select_repositories(workspace, detected, cwd=workspace), ["api"])
        api.rename(workspace / "removed")
        self.assertEqual(discover_repositories(workspace), ["removed"])
        with self.assertRaisesRegex(ValueError, "invalid or unconfirmed"):
            select_repositories(workspace, discover_repositories(workspace), explicit=["api"])

    def test_version_two_migration_requires_matching_confirmed_root(self):
        workspace = Path(self.tempdir.name) / "workspace"
        workspace.mkdir()
        git(workspace, "init")
        state = {
            "version": 2,
            "featureId": "demo",
            "repository": {"name": "workspace", "root": str(workspace)},
        }

        with self.assertRaisesRegex(ValueError, "confirmation required"):
            migrate_v2_state(state, workspace, False)
        self.assertEqual(
            migrate_v2_state(state, workspace, True),
            {
                "version": 3,
                "featureId": "demo",
                "repositories": {".": {"path": ".", "rootConfirmed": True}},
            },
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            migrate_v2_state(state, workspace / "other", True)

    def test_cross_repository_lifecycles_remain_isolated(self):
        workspace = Path(self.tempdir.name) / "workspace"
        api = workspace / "api"
        web = workspace / "web"
        for repo in (api, web):
            repo.mkdir(parents=True)
            git(repo, "init")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "config", "user.name", "Test User")
            (repo / "tracked.txt").write_text(f"{repo.name}\n")
            git(repo, "add", "tracked.txt")
            git(repo, "commit", "-m", "initial")
            git(repo, "branch", "-M", "main")
            git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        results = {
            "api": create_or_reset_target(api, "feature/demo"),
            "web": create_or_reset_target(web, "feature/demo"),
        }
        (api / "tmp.txt").write_text("remove\n")
        (web / "tmp.txt").write_text("keep\n")
        self.assertEqual(results, {"api": "created", "web": "created"})
        self.assertEqual(cleanup_temporary_artifacts(api, [artifact("tmp.txt")]), ["removed"])
        self.assertTrue((web / "tmp.txt").exists())
        self.assertEqual(git(api, "branch", "--show-current").stdout.strip(), "feature/demo")
        self.assertEqual(git(web, "branch", "--show-current").stdout.strip(), "feature/demo")

    def test_documentation_defines_workspace_scoped_contract(self):
        for phrase in (
            "immediate child directories",
            "explicit repository path or name",
            "current directory",
            "active file",
            "sole eligible child",
            "session-scoped confirmation",
            "workspace-relative",
            "separate delegation",
            "selected repository as `cwd`",
            "success`, `failed`, `skipped`, `rejected`, or `unavailable",
        ):
            self.assertIn(phrase, WORKFLOW)
        self.assertIn("immediate-child Git repositories", README)
        self.assertIn("agentModels: {}", README)

    def test_clean_creation_uses_current_checkout_without_worktree_registration(self):
        before = registered_worktree_paths(self.repo)

        self.assertEqual(create_or_reset_target(self.repo, "feature/demo"), "created")
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "feature/demo")
        self.assertEqual(registered_worktree_paths(self.repo), before)

    def test_existing_branch_requires_separate_confirmation_before_discarding_commits(self):
        target_head = self.commit_target_change()
        before = registered_worktree_paths(self.repo)

        self.assertEqual(create_or_reset_target(self.repo, "feature/demo"), "declined-reset")
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(git(self.repo, "rev-parse", "feature/demo").stdout.strip(), target_head)
        self.assertEqual(
            create_or_reset_target(
                self.repo, "feature/demo", destructive_reset_confirmed=True
            ),
            "reset",
        )
        self.assertEqual(
            git(self.repo, "rev-parse", "feature/demo").stdout.strip(),
            git(self.repo, "rev-parse", "origin/main").stdout.strip(),
        )
        self.assertEqual(registered_worktree_paths(self.repo), before)

    def test_existing_branch_blocks_when_remote_main_is_missing_before_checkout(self):
        target_head = self.commit_target_change()
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")

        self.assertEqual(
            create_or_reset_target(
                self.repo, "feature/demo", destructive_reset_confirmed=True
            ),
            "blocked-remote-main",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(git(self.repo, "rev-parse", "feature/demo").stdout.strip(), target_head)

    def test_existing_branch_checked_out_elsewhere_blocks_without_changes(self):
        self.commit_target_change()
        occupied = Path(self.tempdir.name) / "occupied"
        git(self.repo, "worktree", "add", str(occupied), "feature/demo")
        before = registered_worktree_paths(self.repo)

        self.assertEqual(
            create_or_reset_target(
                self.repo, "feature/demo", destructive_reset_confirmed=True
            ),
            "blocked-occupied",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(registered_worktree_paths(self.repo), before)

    def test_dirty_existing_target_blocks_before_non_conflicting_checkout(self):
        self.commit_target_change()
        (self.repo / "local-only.txt").write_text("local change\n")
        before = registered_worktree_paths(self.repo)

        self.assertEqual(
            create_or_reset_target(self.repo, "feature/demo"),
            "blocked-dirty-existing-target",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual((self.repo / "local-only.txt").read_text(), "local change\n")
        self.assertTrue(git(self.repo, "status", "--porcelain").stdout)
        self.assertEqual(registered_worktree_paths(self.repo), before)

    def test_declined_dirty_creation_preserves_current_branch_and_work(self):
        (self.repo / "tracked.txt").write_text("local change\n")
        before = registered_worktree_paths(self.repo)

        self.assertEqual(create_or_reset_target(self.repo, "feature/demo"), "declined-create")
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual((self.repo / "tracked.txt").read_text(), "local change\n")
        self.assertEqual(registered_worktree_paths(self.repo), before)

        self.assertEqual(
            repository_policy_from_file(self.repo),
            {
                "source": str(self.repo / ".claude/full-team-agile.json"),
                "protectedBranches": [],
                "valid": True,
            },
        )

    def test_repository_policy_is_loaded_and_malformed_policy_blocks_deletion(self):
        config = self.repo / ".claude/full-team-agile.json"
        config.parent.mkdir()
        config.write_text('{"protectedBranches": ["feature/demo"]}\n')
        policy = repository_policy_from_file(self.repo)
        self.assertEqual(
            policy,
            {
                "source": str(config),
                "protectedBranches": ["feature/demo"],
                "valid": True,
            },
        )
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/demo",
                "main",
                branch_created_by_plugin=True,
                confirmed=True,
            ),
            "blocked-protected",
        )
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo,
                "feature/demo",
                "origin",
                branch_created_by_plugin=True,
                confirmed=True,
            ),
            "blocked-protected",
        )
        config.write_text("not json\n")
        self.assertEqual(
            repository_policy_from_file(self.repo),
            {"source": str(config), "protectedBranches": [], "valid": False},
        )
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/demo",
                "main",
                branch_created_by_plugin=True,
                confirmed=True,
                repository_policy={"repositoryPolicy": repository_policy_from_file(self.repo)},
            ),
            "blocked-policy",
        )
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo,
                "feature/demo",
                "origin",
                branch_created_by_plugin=True,
                confirmed=True,
                repository_policy={"repositoryPolicy": repository_policy_from_file(self.repo)},
            ),
            "blocked-policy",
        )

    def test_cleanup_removes_only_registered_temporary_files(self):
        registered = self.repo / "tmp/test-output.txt"
        registered.parent.mkdir()
        registered.write_text("temporary\n")
        user_file = self.repo / "tmp/user-output.txt"
        user_file.write_text("keep\n")

        self.assertEqual(
            cleanup_temporary_artifacts(
                self.repo, [artifact("tmp/test-output.txt")]
            ),
            ["removed"],
        )
        self.assertFalse(registered.exists())
        self.assertEqual(user_file.read_text(), "keep\n")

    def test_cleanup_records_already_absent_registered_file(self):
        self.assertEqual(
            cleanup_temporary_artifacts(
                self.repo, [artifact("tmp/already-gone.txt", "execution")]
            ),
            ["alreadyAbsent"],
        )

    def test_cleanup_failure_leaves_registered_file_present(self):
        registered = self.repo / "tmp/test-output.txt"
        registered.parent.mkdir()
        registered.write_text("temporary\n")
        original_unlink = Path.unlink

        def fail_unlink(path: Path, *args, **kwargs):
            if path == registered:
                raise OSError("simulated cleanup failure")
            return original_unlink(path, *args, **kwargs)

        Path.unlink = fail_unlink
        try:
            with self.assertRaisesRegex(OSError, "simulated cleanup failure"):
                cleanup_temporary_artifacts(self.repo, [artifact("tmp/test-output.txt")])
        finally:
            Path.unlink = original_unlink
        self.assertTrue(registered.exists())

    def test_cleanup_rejects_duplicate_paths(self):
        with self.assertRaisesRegex(ValueError, "duplicate artifact path"):
            cleanup_temporary_artifacts(
                self.repo, [artifact("tmp/output.txt"), artifact("tmp/output.txt", "execution")]
            )

    def test_cleanup_rejects_invalid_registry_entry(self):
        with self.assertRaisesRegex(ValueError, "invalid artifact registry entry"):
            cleanup_temporary_artifacts(self.repo, [{"path": "tmp/output.txt", "kind": "test"}])

    def test_cleanup_rejects_symlinked_parent_without_touching_external_file(self):
        external = Path(self.tempdir.name) / "external"
        external.mkdir()
        external_file = external / "user-output.txt"
        external_file.write_text("keep\n")
        (self.repo / "tmp").symlink_to(external, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "contains symlink"):
            cleanup_temporary_artifacts(self.repo, [artifact("tmp/user-output.txt")])
        self.assertEqual(external_file.read_text(), "keep\n")

    def test_cleanup_rejects_outside_or_directory_paths(self):
        directory = self.repo / "tmp"
        directory.mkdir()

        with self.assertRaisesRegex(ValueError, "invalid artifact path"):
            cleanup_temporary_artifacts(self.repo, [artifact("../outside.txt")])
        with self.assertRaisesRegex(ValueError, "invalid artifact path"):
            cleanup_temporary_artifacts(self.repo, [artifact("/tmp/outside.txt")])
        with self.assertRaisesRegex(ValueError, "not a file"):
            cleanup_temporary_artifacts(self.repo, [artifact("tmp")])
        self.assertTrue(directory.is_dir())

    def test_remote_branch_deletion_needs_separate_confirmation(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        git(self.repo, "push", "origin", "feature/demo")
        git(self.repo, "checkout", "main")

        self.assertEqual(
            delete_remote_feature_branch(
                self.repo, "feature/demo", "origin", branch_created_by_plugin=True, confirmed=False
            ),
            "declined",
        )
        self.assertEqual(
            git(self.repo, "ls-remote", "--exit-code", "--heads", "origin", "feature/demo", check=False).returncode,
            0,
        )
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo, "feature/demo", "origin", branch_created_by_plugin=True, confirmed=True
            ),
            "deleted",
        )
        self.assertNotEqual(
            git(self.repo, "ls-remote", "--exit-code", "--heads", "origin", "feature/demo", check=False).returncode,
            0,
        )
        self.assertEqual(git(self.repo, "show-ref", "--verify", "--quiet", "refs/heads/feature/demo", check=False).returncode, 0)

    def test_remote_branch_deletion_blocks_unconfigured_or_non_feature_branch(self):
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo, "main", "origin", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-non-feature",
        )
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo, "feature/demo", "missing", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-remote",
        )

    def test_remote_branch_deletion_blocks_unrelated_or_protected_feature_branch(self):
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo, "feature/other", "origin", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-unrelated",
        )
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo,
                "feature/demo",
                "origin",
                branch_created_by_plugin=True,
                confirmed=True,
                repository_policy={"repositoryPolicy": {"protectedBranches": ["feature/demo"]}},
            ),
            "blocked-protected",
        )
        self.assertEqual(
            delete_remote_feature_branch(
                self.repo,
                "feature/demo",
                "origin",
                branch_created_by_plugin=True,
                confirmed=True,
                repository_policy={"repositoryPolicy": {"protectedBranches": "feature/demo"}},
            ),
            "blocked-policy",
        )

    def test_unrequested_branch_deletion_retains_branch(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        git(self.repo, "checkout", "main")
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/demo",
                "main",
                branch_created_by_plugin=True,
                confirmed=False,
            ),
            "declined",
        )
        self.assertEqual(git(self.repo, "show-ref", "--verify", "--quiet", "refs/heads/feature/demo", check=False).returncode, 0)

    def test_non_plugin_branch_deletion_is_declined(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        git(self.repo, "checkout", "main")
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/demo",
                "main",
                branch_created_by_plugin=False,
                confirmed=True,
            ),
            "declined",
        )
        self.assertEqual(git(self.repo, "show-ref", "--verify", "--quiet", "refs/heads/feature/demo", check=False).returncode, 0)

    def test_branch_deletion_blocks_missing_or_same_return_branch(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        git(self.repo, "checkout", "main")
        self.assertEqual(
            delete_feature_branch(
                self.repo, "feature/demo", "feature/demo", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-return-branch",
        )
        self.assertEqual(
            delete_feature_branch(
                self.repo, "feature/demo", "missing", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-return-branch",
        )

    def test_branch_deletion_blocks_occupied_feature_branch(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        git(self.repo, "checkout", "main")
        occupied = Path(self.tempdir.name) / "occupied"
        git(self.repo, "worktree", "add", str(occupied), "feature/demo")
        self.assertEqual(
            delete_feature_branch(
                self.repo, "feature/demo", "main", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-occupied",
        )

    def test_confirmed_plugin_branch_deletion_switches_to_return_branch(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        git(self.repo, "checkout", "main")
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/demo",
                "main",
                branch_created_by_plugin=True,
                confirmed=True,
            ),
            "deleted",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertNotEqual(
            git(self.repo, "show-ref", "--verify", "--quiet", "refs/heads/feature/demo", check=False).returncode,
            0,
        )

    def test_branch_deletion_blocks_non_feature_branch(self):
        self.assertEqual(
            delete_feature_branch(
                self.repo, "main", "feature/return", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-non-feature",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")

    def test_branch_deletion_blocks_unrelated_or_protected_feature_branch(self):
        git(self.repo, "checkout", "-b", "feature/other")
        git(self.repo, "checkout", "main")

        self.assertEqual(
            delete_feature_branch(
                self.repo, "feature/other", "main", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-unrelated",
        )
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/other",
                "main",
                feature_id="other",
                branch_created_by_plugin=True,
                confirmed=True,
                repository_policy={"repositoryPolicy": {"protectedBranches": ["feature/other"]}},
            ),
            "blocked-protected",
        )
        self.assertEqual(
            delete_feature_branch(
                self.repo,
                "feature/other",
                "main",
                feature_id="other",
                branch_created_by_plugin=True,
                confirmed=True,
                repository_policy={"repositoryPolicy": {"protectedBranches": [""]}},
            ),
            "blocked-policy",
        )

    def test_branch_deletion_blocks_dirty_or_unmerged_branch(self):
        git(self.repo, "checkout", "-b", "feature/demo")
        (self.repo / "feature.txt").write_text("feature\n")
        git(self.repo, "add", "feature.txt")
        git(self.repo, "commit", "-m", "feature change")
        git(self.repo, "checkout", "main")
        (self.repo / "local-only.txt").write_text("local\n")
        self.assertEqual(
            delete_feature_branch(
                self.repo, "feature/demo", "main", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-dirty",
        )
        (self.repo / "local-only.txt").unlink()
        self.assertEqual(
            delete_feature_branch(
                self.repo, "feature/demo", "main", branch_created_by_plugin=True, confirmed=True
            ),
            "blocked-unmerged",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")

    def test_documentation_blocks_dirty_existing_targets_before_checkout(self):
        self.assertIn("git worktree list --porcelain", WORKFLOW)
        self.assertIn("if the tree is dirty, block before checkout", WORKFLOW)
        self.assertIn("clean or stash manually, then rerun", WORKFLOW)
        self.assertIn("separate explicit destructive-reset confirmation", WORKFLOW)
        self.assertIn("will discard commits on that branch", WORKFLOW)
        self.assertIn("Never stash, discard, reset, or force checkout automatically", WORKFLOW)
        self.assertIn("target already exists and the tree is dirty, it blocks before checkout", README)
        self.assertNotIn("non-forced `git checkout feature/<feature-id>`", WORKFLOW)
        self.assertIn("temporaryArtifacts", WORKFLOW)
        self.assertIn("Run immediately before the final completion response", WORKFLOW)
        self.assertIn("git branch -d <feature-branch>", WORKFLOW)
        self.assertIn("Remote deletion is separately optional", WORKFLOW)
        self.assertIn("local-deletion confirmation never authorizes it", WORKFLOW)
        self.assertIn("only explicitly tracked temporary artifacts are removed", README)
        self.assertNotIn("worktree cleanup", WORKFLOW)
        self.assertNotIn("worktree cleanup", README)


if __name__ == "__main__":
    unittest.main()
