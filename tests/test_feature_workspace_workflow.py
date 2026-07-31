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


def is_primary_checkout(workspace: Path, child: Path) -> bool:
    root_result = git(child, "rev-parse", "--show-toplevel", check=False)
    git_dir_result = git(child, "rev-parse", "--git-dir", check=False)
    if root_result.returncode or git_dir_result.returncode:
        return False
    resolved_child = child.resolve()
    if resolved_child == workspace / ".claude" / "worktrees" or (workspace / ".claude" / "worktrees") in resolved_child.parents:
        return False
    return (
        Path(root_result.stdout.strip()).resolve() == resolved_child
        and resolved_child.parent == workspace
        and (resolved_child / ".git").is_dir()
        and (child / git_dir_result.stdout.strip()).resolve() == (resolved_child / ".git")
    )


def discover_repositories(workspace: Path) -> list[str]:
    workspace = workspace.resolve()
    return [
        child.name
        for child in sorted(path for path in workspace.iterdir() if path.is_dir() and not path.is_symlink())
        if is_primary_checkout(workspace, child)
    ]


def validate_pre_edit_context(
    runtime: Path,
    repository: Path,
    branch: str,
    base_commit: str,
    *,
    inherited_cwd: Path | None = None,
) -> bool:
    runtime = runtime.resolve()
    repository = repository.resolve()
    if not (repository / ".git").is_dir():
        return False
    if runtime != repository:
        plugin_root = repository.parent / ".full-team-agile/worktrees" / repository.name
        if plugin_root.resolve() not in runtime.parents or runtime not in registered_worktree_paths(repository):
            return False
    root = git(runtime, "rev-parse", "--show-toplevel", check=False)
    common_dir = git(runtime, "rev-parse", "--git-common-dir", check=False)
    return (
        root.returncode == 0
        and common_dir.returncode == 0
        and Path(root.stdout.strip()).resolve() == runtime
        and (runtime / common_dir.stdout.strip()).resolve() == repository / ".git"
        and git(runtime, "branch", "--show-current").stdout.strip() == branch
        and git(runtime, "merge-base", "--is-ancestor", base_commit, "HEAD", check=False).returncode == 0
    )


def runtime_target(runtime: Path, target: Path) -> Path | None:
    runtime = runtime.resolve()
    try:
        canonical = target.resolve()
        canonical.relative_to(runtime)
    except (OSError, ValueError):
        return None
    return canonical


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


def resolve_new_execution_mode(explicit: str | None = None, configured: str | None = None) -> str:
    if explicit in {"worktree", "branch"}:
        return explicit
    return configured if configured in {"worktree", "branch"} else "worktree"


def migrate_execution_mode(state: dict[str, object], explicit: str | None = None) -> tuple[dict[str, object], str]:
    """Persist a safe legacy mode before validating the invocation mode."""
    mode = state.get("executionMode")
    if mode is None:
        records_value = state.get("repositories")
        if not isinstance(records_value, dict) or not records_value:
            raise ValueError("ambiguous execution mode")
        records = list(records_value.values())

        def valid_workspace(record: object) -> bool:
            if not isinstance(record, dict):
                return False
            workspace = record.get("workspace")
            return (
                isinstance(workspace, dict)
                and isinstance(workspace.get("root"), str)
                and bool(workspace["root"])
            )

        def valid_worktree(record: object) -> bool:
            if not isinstance(record, dict) or not isinstance(record.get("worktree"), dict):
                return False
            worktree = record["worktree"]
            workspace = record.get("workspace")
            if not isinstance(workspace, dict):
                return False
            raw_path = worktree.get("path")
            branch = worktree.get("branch")
            base = workspace.get("baseCommit")
            root = workspace.get("root")
            if not all(isinstance(value, str) and value for value in (raw_path, branch, base, root)):
                return False
            path = Path(raw_path).resolve()
            repository = Path(root).resolve()
            expected_path = plugin_worktree_path(repository, branch.removeprefix("feature/"))
            return (
                raw_path == str(path)
                and path == expected_path.resolve()
                and (path / ".git").is_file()
                and worktree.get("pluginOwned") is True
                and path in registered_worktree_paths(repository)
                and git(path, "rev-parse", "--show-toplevel").stdout.strip() == str(path)
                and git(path, "rev-parse", "--git-common-dir").stdout.strip() == str(repository / ".git")
                and git(path, "branch", "--show-current").stdout.strip() == branch
                and git(path, "merge-base", "--is-ancestor", base, "HEAD", check=False).returncode == 0
            )

        if any(not valid_workspace(record) for record in records) or any(
            isinstance(record, dict)
            and record.get("worktree") is not None
            and not valid_worktree(record)
            for record in records
        ):
            raise ValueError("ambiguous execution mode")
        mode = "worktree" if records and all(valid_worktree(record) for record in records) else explicit or "worktree"
        state["executionMode"] = mode
    if mode not in {"worktree", "branch"} or (explicit is not None and explicit != mode):
        raise ValueError("execution mode mismatch")
    return state, mode


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


def plugin_worktree_path(repo: Path, feature_id: str) -> Path:
    return repo.parent / ".full-team-agile/worktrees" / repo.name / feature_id


def worktree_for(repo: Path, feature_id: str, metadata: dict[str, object] | None = None) -> tuple[str, dict[str, object] | None]:
    branch = f"feature/{feature_id}"
    path = plugin_worktree_path(repo, feature_id).resolve()
    expected = {"path": str(path), "branch": branch, "pluginOwned": True}
    registered = registered_worktree_paths(repo)
    if metadata is not None:
        if metadata != expected or path not in registered or git(path, "branch", "--show-current").stdout.strip() != branch:
            return "blocked-mismatch", None
        return "continued", metadata
    if git(repo, "status", "--porcelain").stdout:
        return "blocked-dirty", None
    if path.exists() or path in registered:
        return "blocked-path-collision", None
    if git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
        return "blocked-branch-collision", None
    path.parent.mkdir(parents=True, exist_ok=True)
    result = git(repo, "worktree", "add", "-b", branch, str(path), "HEAD", check=False)
    return ("created", expected) if result.returncode == 0 else ("blocked-create", None)


def remove_plugin_worktree(
    repo: Path,
    feature_id: str,
    metadata: dict[str, object],
    *,
    phase: str,
    reviews_complete: bool,
    status: str,
) -> str:
    branch = f"feature/{feature_id}"
    path = plugin_worktree_path(repo, feature_id).resolve()
    expected = {"path": str(path), "branch": branch, "pluginOwned": True}
    if phase != "cleanup":
        return "skipped-pre-cleanup"
    if not reviews_complete:
        return "skipped-incomplete-review"
    if status in {"active", "blocked", "failed", "awaiting-input"}:
        return f"skipped-{status}"
    if metadata.get("pluginOwned") is not True:
        return "skipped-external"
    if metadata != expected or path not in registered_worktree_paths(repo):
        return "skipped-mismatch"
    if git(path, "status", "--porcelain").stdout:
        return "skipped-dirty"
    result = git(repo, "worktree", "remove", str(path), check=False)
    if result.returncode:
        return "blocked-remove"
    prune = git(repo, "worktree", "prune", check=False)
    return "removed-pruned" if prune.returncode == 0 else "blocked-prune"


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


def create_branch_target(
    repo: Path,
    target: str,
    *,
    base_commit: str | None = None,
    persisted_owner: bool = False,
) -> str:
    """Execute branch-mode creation without worktree registration or reset."""
    if git(repo, "status", "--porcelain").stdout:
        return "blocked-dirty"
    base_commit = base_commit or git(repo, "rev-parse", "HEAD").stdout.strip()
    exists = git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{target}", check=False).returncode == 0
    if exists:
        if not persisted_owner:
            return "blocked-unowned"
        if branch_is_occupied(repo, target):
            return "blocked-occupied"
        if git(repo, "rev-parse", target).stdout.strip() != base_commit:
            return "blocked-base-mismatch"
        git(repo, "switch", target)
        return "checked-out"
    result = git(repo, "switch", "-c", target, base_commit, check=False)
    return "created" if result.returncode == 0 else "blocked-create"


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

    def test_immediate_child_detection_excludes_nested_and_linked_worktrees(self):
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

        self.assertEqual(discover_repositories(workspace), ["api"])

    def test_primary_checkout_context_rejects_linked_and_host_worktrees_before_edits(self):
        workspace = Path(self.tempdir.name) / "workspace"
        workspace.mkdir()
        primary = workspace / "api"
        primary.mkdir()
        git(primary, "init")
        git(primary, "config", "user.email", "test@example.com")
        git(primary, "config", "user.name", "Test User")
        (primary / "tracked.txt").write_text("main\n")
        git(primary, "add", "tracked.txt")
        git(primary, "commit", "-m", "initial")
        git(primary, "checkout", "-b", "feature/demo")
        base = git(primary, "rev-parse", "HEAD").stdout.strip()
        linked = workspace / ".claude/worktrees/api"
        linked.parent.mkdir(parents=True)
        git(primary, "worktree", "add", str(linked), "-b", "feature/linked")

        self.assertEqual(discover_repositories(workspace), ["api"])
        self.assertTrue(validate_pre_edit_context(primary, primary, "feature/demo", base))
        self.assertFalse(validate_pre_edit_context(linked, primary, "feature/demo", base))
        self.assertFalse(validate_pre_edit_context(primary, primary, "main", base))
        self.assertFalse(validate_pre_edit_context(primary, primary, "feature/demo", "0" * 40))

    def test_parent_container_cwd_uses_recorded_worktree_and_rejects_sibling_escapes(self):
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
        base = git(api, "rev-parse", "HEAD").stdout.strip()
        status, metadata = worktree_for(api, "parent-cwd")
        runtime = Path(metadata["path"])

        self.assertEqual(status, "created")
        self.assertTrue(
            validate_pre_edit_context(
                runtime,
                api,
                metadata["branch"],
                base,
                inherited_cwd=workspace,
            )
        )
        selected = runtime_target(runtime, runtime / "selected.txt")
        self.assertEqual(selected, runtime / "selected.txt")
        selected.write_text("selected only\n")
        self.assertIsNone(runtime_target(runtime, runtime / ".." / ".." / ".." / "web" / "sibling.txt"))
        self.assertIsNone(runtime_target(runtime, web / "sibling.txt"))
        external = workspace / "external.txt"
        external.write_text("external\n")
        (runtime / "external-link").symlink_to(external)
        self.assertIsNone(runtime_target(runtime, runtime / "external-link"))
        self.assertFalse((web / "sibling.txt").exists())
        self.assertEqual(external.read_text(), "external\n")

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

    def test_legacy_worktree_state_migrates_and_persists_before_mode_validation(self):
        base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        status, metadata = worktree_for(self.repo, "demo")
        self.assertEqual(status, "created")
        state = {
            "repositories": {
                "api": {
                    "workspace": {"root": str(self.repo.resolve()), "baseCommit": base},
                    "worktree": metadata,
                }
            }
        }
        migrated, mode = migrate_execution_mode(state, explicit="worktree")
        self.assertEqual(mode, "worktree")
        self.assertEqual(migrated["executionMode"], "worktree")

        with self.assertRaisesRegex(ValueError, "mismatch"):
            migrate_execution_mode(
                {
                    "repositories": {
                        "api": {
                            "workspace": {"root": str(self.repo.resolve()), "baseCommit": base},
                            "worktree": metadata,
                        }
                    }
                },
                explicit="branch",
            )

        with self.assertRaisesRegex(ValueError, "ambiguous"):
            migrate_execution_mode(
                {"repositories": {"api": {"worktree": {"pluginOwned": True}}}},
                explicit="branch",
            )

        with self.assertRaisesRegex(ValueError, "ambiguous"):
            migrate_execution_mode(
                {
                    "repositories": {
                        "api": {
                            "workspace": {"root": str(self.repo.resolve()), "baseCommit": base},
                            "worktree": {**metadata, "path": "../outside"},
                        }
                    }
                }
            )

    def test_legacy_primary_checkout_uses_explicit_choice_or_safe_default(self):
        legacy = {"repositories": {"api": {"workspace": {"root": "/tmp/api"}}}}
        migrated, mode = migrate_execution_mode(legacy.copy(), explicit="branch")
        self.assertEqual(mode, "branch")
        self.assertEqual(migrated["executionMode"], "branch")

        self.assertEqual(resolve_new_execution_mode(configured="branch"), "branch")
        self.assertEqual(resolve_new_execution_mode(explicit="worktree", configured="branch"), "worktree")
        self.assertEqual(resolve_new_execution_mode(configured="invalid"), "worktree")

        defaulted, mode = migrate_execution_mode(legacy.copy())
        self.assertEqual(mode, "worktree")
        self.assertEqual(defaulted["executionMode"], "worktree")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            migrate_execution_mode(defaulted, explicit="branch")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            migrate_execution_mode({"repositories": {"api": {"workspace": []}}})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            migrate_execution_mode(
                {"repositories": {"api": {"workspace": {"root": 7}, "worktree": None}}}
            )

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
        (web / "tmp.txt").unlink()
        repository_statuses = {
            "api": "done",
            "web": "active",
        }
        api_status, api_metadata = worktree_for(api, "isolated")
        web_status, web_metadata = worktree_for(web, "isolated")
        self.assertEqual((api_status, web_status), ("created", "created"))
        self.assertEqual(
            remove_plugin_worktree(
                api, "isolated", api_metadata, phase="cleanup", reviews_complete=True, status=repository_statuses["api"]
            ),
            "removed-pruned",
        )
        for sibling_status in ("active", "blocked", "failed", "awaiting-input"):
            repository_statuses["web"] = sibling_status
            self.assertEqual(
                remove_plugin_worktree(
                    web, "isolated", web_metadata, phase="cleanup", reviews_complete=True, status=repository_statuses["web"]
                ),
                f"skipped-{sibling_status}",
            )
            self.assertIn(Path(web_metadata["path"]), registered_worktree_paths(web))

    def test_documentation_defines_workspace_scoped_contract(self):
        for phrase in (
            "executionMode=worktree|branch",
            "CLAUDE_PLUGIN_OPTION_DEFAULT_EXECUTION_MODE",
            "absent, empty, or invalid plugin configuration warns and falls back to `worktree`",
            "The plugin default never changes an existing feature",
            "legacy record missing `executionMode`",
            "valid exact plugin-owned worktree metadata",
            "legacy primary-checkout record without a worktree",
            "safe default only when no explicit choice is provided",
            "persist an explicit choice before Git mutation",
            "clean before branch creation or checkout",
            "immediately before each source-editing delegation",
            "must allow expected uncommitted feature changes",
            "without requiring a clean tree",
            "branch deletion retains its separate clean-checkout requirement",
            "preserve its exact path and basename",
            "immediate child directories",
            "explicit repository path or name",
            "current directory",
            "active file",
            "sole eligible child",
            "coordinator-supplied repository scope validated by fresh discovery",
            "untrusted selection request",
            "reject the whole supplied scope without fallback",
            "session-scoped confirmation",
            "workspace-relative",
            "separate delegation",
            "validated recorded runtime",
            "plugin-owned worktree",
            "git -C <primary-checkout> worktree add",
            "inherited Agent cwd",
            "git -C <recorded-runtime>",
            "success`, `failed`, `skipped`, `rejected`, or `unavailable",
        ):
            self.assertIn(phrase, WORKFLOW)
        for phrase in (
            "Obsidian MCP vault tools only",
            "never project-relative filesystem operations",
            "<artifact-root>/Features/<workspace-name>/<feature-id>/",
            "artifactRoot",
            "configured path",
            "stop as ambiguous",
            "Never move or relocate durable artifacts",
            "<feature-directory>",
        ):
            self.assertIn(phrase, WORKFLOW)
        self.assertIn("immediate-child **primary** Git checkouts", README)
        self.assertIn("agentModels: {}", README)
        self.assertIn("Configure artifact storage", README)
        self.assertIn("/Users/kenviriya/Code/Claude-Brain", README)

    def test_version_three_primary_checkout_record_remains_usable_until_worktree_creation(self):
        v3_workspace = {
            "root": str(self.repo),
            "branch": "feature/demo",
            "baseCommit": git(self.repo, "rev-parse", "HEAD").stdout.strip(),
            "returnBranch": "main",
            "branchCreatedByPlugin": True,
        }

        self.assertTrue(
            validate_pre_edit_context(
                self.repo, self.repo, v3_workspace["branch"], v3_workspace["baseCommit"]
            ) is False
        )
        git(self.repo, "checkout", "-b", v3_workspace["branch"])
        self.assertTrue(
            validate_pre_edit_context(
                self.repo, self.repo, v3_workspace["branch"], v3_workspace["baseCommit"]
            )
        )
        self.assertNotIn("worktree", v3_workspace)

        first_status, first = worktree_for(self.repo, "first")
        second_status, second = worktree_for(self.repo, "second")

        self.assertEqual(first_status, "created")
        self.assertEqual(second_status, "created")
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(worktree_for(self.repo, "first", first), ("continued", first))
        self.assertEqual(
            remove_plugin_worktree(
                self.repo,
                "first",
                first,
                phase="review",
                reviews_complete=True,
                status="done",
            ),
            "skipped-pre-cleanup",
        )
        self.assertEqual(
            remove_plugin_worktree(
                self.repo,
                "first",
                first,
                phase="cleanup",
                reviews_complete=False,
                status="done",
            ),
            "skipped-incomplete-review",
        )
        self.assertIn(Path(first["path"]), registered_worktree_paths(self.repo))
        self.assertEqual(remove_plugin_worktree(self.repo, "first", first, phase="cleanup", reviews_complete=True, status="done"), "removed-pruned")
        self.assertEqual(git(self.repo, "rev-parse", "--verify", "feature/first").returncode, 0)
        self.assertEqual(remove_plugin_worktree(self.repo, "second", second, phase="cleanup", reviews_complete=True, status="active"), "skipped-active")
        self.assertEqual(remove_plugin_worktree(self.repo, "second", second, phase="cleanup", reviews_complete=True, status="blocked"), "skipped-blocked")
        self.assertEqual(remove_plugin_worktree(self.repo, "second", second, phase="cleanup", reviews_complete=True, status="failed"), "skipped-failed")
        self.assertEqual(remove_plugin_worktree(self.repo, "second", second, phase="cleanup", reviews_complete=True, status="awaiting-input"), "skipped-awaiting-input")
        self.assertIn(Path(second["path"]), registered_worktree_paths(self.repo))

    def test_plugin_worktree_blocks_collisions_mismatches_and_dirty_cleanup(self):
        status, metadata = worktree_for(self.repo, "demo")

        self.assertEqual(status, "created")
        self.assertEqual(worktree_for(self.repo, "demo"), ("blocked-path-collision", None))
        self.assertEqual(remove_plugin_worktree(self.repo, "demo", {**metadata, "pluginOwned": False}, phase="cleanup", reviews_complete=True, status="done"), "skipped-external")
        self.assertEqual(remove_plugin_worktree(self.repo, "demo", {**metadata, "branch": "feature/other"}, phase="cleanup", reviews_complete=True, status="done"), "skipped-mismatch")
        path = Path(metadata["path"])
        (path / "local.txt").write_text("dirty\n")
        self.assertEqual(remove_plugin_worktree(self.repo, "demo", metadata, phase="cleanup", reviews_complete=True, status="done"), "skipped-dirty")
        self.assertIn(path, registered_worktree_paths(self.repo))

    def test_branch_mode_creates_primary_checkout_branch_without_worktree(self):
        before = registered_worktree_paths(self.repo)
        self.assertEqual(create_branch_target(self.repo, "feature/demo"), "created")
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "feature/demo")
        self.assertEqual(registered_worktree_paths(self.repo), before)

    def test_branch_mode_allows_feature_changes_for_qa_review_but_rejects_wrong_context(self):
        base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(create_branch_target(self.repo, "feature/demo", base_commit=base), "created")
        (self.repo / "tracked.txt").write_text("feature change\n")

        # QA/review validate identity and ancestry, not cleanliness: feature changes are expected here.
        self.assertTrue(validate_pre_edit_context(self.repo, self.repo, "feature/demo", base))
        self.assertFalse(validate_pre_edit_context(self.repo, self.repo, "main", base))

        other = Path(self.tempdir.name) / "other"
        other.mkdir()
        git(other, "init")
        self.assertFalse(validate_pre_edit_context(other, self.repo, "feature/demo", base))

    def test_branch_mode_refuses_unowned_existing_branch(self):
        base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(git(self.repo, "branch", "feature/demo", base).returncode, 0)
        self.assertEqual(
            create_branch_target(self.repo, "feature/demo", base_commit=base),
            "blocked-unowned",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")

    def test_branch_mode_refuses_dirty_or_diverged_existing_branch(self):
        (self.repo / "local-only.txt").write_text("local\n")
        self.assertEqual(create_branch_target(self.repo, "feature/demo"), "blocked-dirty")
        (self.repo / "local-only.txt").unlink()
        target_head = self.commit_target_change()
        self.assertEqual(
            create_branch_target(self.repo, "feature/demo", persisted_owner=True),
            "blocked-base-mismatch",
        )
        self.assertEqual(git(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(git(self.repo, "rev-parse", "feature/demo").stdout.strip(), target_head)

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

    def test_documentation_defines_worktree_creation_and_safe_cleanup(self):
        for phrase in (
            "executionMode=worktree|branch",
            "branch mode",
            "primary checkout",
            "without creating worktrees",
            "feature owns all Git mutation",
            "plugin-owned worktree",
            ".full-team-agile/worktrees/<repository-name>/<feature-id>",
            "git -C <primary-checkout> worktree add -b <feature-branch>",
            "Version-3 primary-checkout workspaces remain valid",
            "recorded runtime path",
            "Distinct feature IDs may make concurrent source edits",
            "git -C <primary-root> worktree remove <worktree-path>",
            "git -C <primary-root> worktree prune",
            "This never deletes the feature branch",
            "separate optional branch-deletion confirmation",
        ):
            self.assertIn(phrase, WORKFLOW)
        self.assertIn("as version 5", WORKFLOW)
        self.assertIn("dispatchMode=serial|parallel", WORKFLOW)
        self.assertIn("always ask the user to choose `dispatchMode=serial|parallel`", WORKFLOW)
        self.assertIn("In `dispatchMode=serial`", WORKFLOW)
        self.assertIn("In `dispatchMode=parallel`", WORKFLOW)
        self.assertIn("executionMode", README)
        self.assertIn("plugin-owned Git worktree", README)
        self.assertIn("same-repository", README)




if __name__ == "__main__":
    unittest.main()
