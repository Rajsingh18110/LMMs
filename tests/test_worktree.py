"""
Unit tests for lmms_worktree: Git worktree isolation, diff inspection,
safe merge apply, dirty tree handling, detached HEAD, and merge conflict rollback.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from lmms_worktree.manager import WorktreeManager


def run_git(args, cwd):
    res = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Git failed: {res.stderr}")
    return res.stdout.strip()


@pytest.fixture
def git_repo(tmp_path):
    """Sets up a temporary git repository with an initial commit."""
    repo_dir = str(tmp_path / "test_repo")
    os.makedirs(repo_dir, exist_ok=True)
    
    run_git(["init"], cwd=repo_dir)
    run_git(["config", "user.name", "Test User"], cwd=repo_dir)
    run_git(["config", "user.email", "test@lmms.ai"], cwd=repo_dir)
    
    # Create initial file & commit
    initial_file = os.path.join(repo_dir, "app.py")
    with open(initial_file, "w") as f:
        f.write("print('hello world')\n")
        
    run_git(["add", "app.py"], cwd=repo_dir)
    run_git(["commit", "-m", "initial commit"], cwd=repo_dir)
    
    return repo_dir


def test_worktree_enable_and_isolation(git_repo):
    """Verify that agent edits in worktree do not touch user working tree."""
    mgr = WorktreeManager()
    session = mgr.enable(git_repo)

    assert session is not None
    assert os.path.exists(session.worktree_dir)
    assert mgr.get_active_workspace(git_repo) == session.worktree_dir

    # Create a new file inside the worktree
    wt_file = os.path.join(session.worktree_dir, "feature.py")
    with open(wt_file, "w") as f:
        f.write("def feature(): pass\n")

    # Assert file exists in worktree, but NOT in user's working tree
    assert os.path.exists(wt_file)
    user_file = os.path.join(git_repo, "feature.py")
    assert not os.path.exists(user_file)

    # Clean up
    mgr.discard(git_repo)
    assert not os.path.exists(session.worktree_dir)


def test_worktree_diff(git_repo):
    """Verify diff accurately reports modified and untracked files."""
    mgr = WorktreeManager()
    session = mgr.enable(git_repo)

    # Modify an existing file in worktree
    with open(os.path.join(session.worktree_dir, "app.py"), "a") as f:
        f.write("# comment added in worktree\n")

    # Add a new untracked file
    with open(os.path.join(session.worktree_dir, "new_module.py"), "w") as f:
        f.write("x = 1\n")

    diff_output = mgr.diff(git_repo)
    assert "# comment added in worktree" in diff_output
    assert "new_module.py" in diff_output

    mgr.discard(git_repo)


def test_worktree_apply(git_repo):
    """Verify apply commits, merges to user branch, and cleans up worktree."""
    mgr = WorktreeManager()
    session = mgr.enable(git_repo)

    # Edit file in worktree
    with open(os.path.join(session.worktree_dir, "app.py"), "w") as f:
        f.write("print('updated in worktree')\n")

    # Add new file
    with open(os.path.join(session.worktree_dir, "helper.py"), "w") as f:
        f.write("def help(): pass\n")

    # Apply changes
    success, msg = mgr.apply(git_repo)
    assert success is True
    assert "successfully merged" in msg

    # Verify changes are now in the user's working tree
    with open(os.path.join(git_repo, "app.py")) as f:
        assert f.read() == "print('updated in worktree')\n"
        
    assert os.path.exists(os.path.join(git_repo, "helper.py"))
    assert mgr.get_session(git_repo) is None


def test_worktree_discard(git_repo):
    """Verify discard removes worktree without touching user workspace."""
    mgr = WorktreeManager()
    session = mgr.enable(git_repo)

    with open(os.path.join(session.worktree_dir, "scratch.py"), "w") as f:
        f.write("temporary file\n")

    assert os.path.exists(os.path.join(session.worktree_dir, "scratch.py"))

    res = mgr.discard(git_repo)
    assert res is True
    assert not os.path.exists(os.path.join(git_repo, "scratch.py"))
    assert mgr.get_session(git_repo) is None


def test_worktree_dirty_working_tree(git_repo):
    """Verify worktree handles uncommitted changes in user working tree safely."""
    # Create uncommitted dirty file in user workspace
    dirty_file = os.path.join(git_repo, "dirty_work.txt")
    with open(dirty_file, "w") as f:
        f.write("unsaved user notes\n")

    mgr = WorktreeManager()
    assert mgr.is_dirty(git_repo) is True

    # Should enable worktree safely without losing user dirty changes
    session = mgr.enable(git_repo)
    assert session is not None
    assert os.path.exists(dirty_file)

    mgr.discard(git_repo)
    assert os.path.exists(dirty_file)


def test_worktree_not_a_git_repo(tmp_path):
    """Verify graceful handling when directory is not a git repo."""
    non_git_dir = str(tmp_path / "not_git")
    os.makedirs(non_git_dir, exist_ok=True)

    mgr = WorktreeManager()
    assert mgr.is_git_repo(non_git_dir) is False

    with pytest.raises(ValueError, match="not a Git repository"):
        mgr.enable(non_git_dir)


def test_worktree_detached_head(git_repo):
    """Verify worktree creates ephemeral branch cleanly when HEAD is detached."""
    # Detach HEAD
    run_git(["checkout", "--detach", "HEAD"], cwd=git_repo)
    
    mgr = WorktreeManager()
    _, _, is_detached = mgr.get_head_info(git_repo)
    assert is_detached is True

    session = mgr.enable(git_repo)
    assert session.is_detached is True
    assert os.path.exists(session.worktree_dir)

    mgr.discard(git_repo)


def test_worktree_merge_conflict(git_repo):
    """Verify merge conflicts abort cleanly and do not corrupt user working tree."""
    mgr = WorktreeManager()
    session = mgr.enable(git_repo)

    # 1. Edit app.py in worktree
    with open(os.path.join(session.worktree_dir, "app.py"), "w") as f:
        f.write("print('worktree conflict')\n")

    # 2. Make conflicting commit on user's branch
    with open(os.path.join(git_repo, "app.py"), "w") as f:
        f.write("print('user concurrent edit')\n")
    run_git(["commit", "-am", "user concurrent commit"], cwd=git_repo)

    # 3. Attempt apply -> conflict must be detected, aborted, and return False
    success, msg = mgr.apply(git_repo)
    assert success is False
    assert "Merge conflict detected" in msg

    # Verify user working tree was NOT left with conflict markers
    with open(os.path.join(git_repo, "app.py")) as f:
        assert f.read() == "print('user concurrent edit')\n"

    # Cleanup
    mgr.discard(git_repo)


@pytest.mark.skipif(not shutil.which("bwrap"), reason="bwrap binary not available on host")
def test_worktree_inside_sandbox_live(git_repo):
    """
    Live test verifying git operations inside a sandboxed worktree:
    1. Bubblewrap mounts worktree as writable workspace.
    2. Git metadata (.git/worktrees/<name>, objects, refs) are mounted writable.
    3. Edits and git commit succeed inside sandbox.
    4. Main user working tree remains completely untouched.
    """
    from lmms_sandbox.runner import SandboxRunner

    mgr = WorktreeManager()
    session = mgr.enable(git_repo)
    wt_dir = session.worktree_dir

    runner = SandboxRunner()
    commit_cmd = 'echo "def sandboxed(): return True" > sandboxed_mod.py && git add -A && git commit -m "sandboxed agent commit"'
    res = runner.run(
        command=commit_cmd,
        workspace_dir=wt_dir,
        enforce_sandbox=True,
        confirm_callback=lambda cmd, reason: True,
    )

    assert res.success is True, f"Sandboxed git commit failed: {res.stderr}\nOutput: {res.output}"

    # Verify commit exists on worktree branch
    wt_log = run_git(["log", "-1", "--oneline"], cwd=wt_dir)
    assert "sandboxed agent commit" in wt_log

    # Verify user main working tree is completely untouched
    assert not os.path.exists(os.path.join(git_repo, "sandboxed_mod.py"))

    mgr.discard(git_repo)


def test_worktree_apply_auto_commit_all_types(git_repo):
    """
    Verify /worktree apply auto-commits all types of uncommitted changes:
    - New untracked file (respecting .gitignore)
    - Modified existing file
    - Deleted file
    All three must land cleanly in the user's branch after apply.
    """
    # Create a file to be deleted
    del_file = os.path.join(git_repo, "delete_target.txt")
    with open(del_file, "w") as f:
        f.write("to be deleted\n")
    run_git(["add", "delete_target.txt"], cwd=git_repo)
    run_git(["commit", "-m", "add delete_target"], cwd=git_repo)

    mgr = WorktreeManager()
    session = mgr.enable(git_repo)
    wt = session.worktree_dir

    # 1. New untracked file
    with open(os.path.join(wt, "brand_new.txt"), "w") as f:
        f.write("hello from brand new file\n")

    # 2. Modified file
    with open(os.path.join(wt, "app.py"), "w") as f:
        f.write("print('brand new app content')\n")

    # 3. Deleted file
    os.remove(os.path.join(wt, "delete_target.txt"))

    # Apply without any manual git add or commit
    success, msg = mgr.apply(git_repo)
    assert success is True
    assert "successfully merged" in msg

    # Verify all 3 changes landed in the user's working tree
    assert os.path.exists(os.path.join(git_repo, "brand_new.txt"))
    with open(os.path.join(git_repo, "brand_new.txt")) as f:
        assert f.read() == "hello from brand new file\n"

    with open(os.path.join(git_repo, "app.py")) as f:
        assert f.read() == "print('brand new app content')\n"

    assert not os.path.exists(os.path.join(git_repo, "delete_target.txt"))


def test_worktree_stale_cleanup_after_crash(git_repo, tmp_path):
    """
    Verify clean_stale_worktrees cleans up abandoned worktrees and orphaned branches
    left behind after an ungraceful crash (no atexit execution).
    """
    custom_temp = str(tmp_path / "crash_temp")
    os.makedirs(custom_temp, exist_ok=True)
    mgr = WorktreeManager(base_temp_dir=custom_temp)

    # 1. Enable worktree to get valid branch & directory
    session = mgr.enable(git_repo)
    stale_branch = session.ephemeral_branch
    stale_dir = session.worktree_dir
    session_id = session.session_id

    # 2. Simulate process crash: simulate dead PID 9999999 in metadata file
    # and remove from active_sessions without calling discard or atexit
    mgr.active_sessions.clear()

    import json
    meta_path = mgr._meta_path(session_id)
    crash_meta = {
        "session_id": session_id,
        "pid": 9999999,  # Non-existent PID
        "workspace": git_repo,
        "worktree_dir": stale_dir,
        "ephemeral_branch": stale_branch,
    }
    with open(meta_path, "w") as f:
        json.dump(crash_meta, f)

    assert os.path.exists(stale_dir)

    # 3. Run stale cleanup
    cleaned = mgr.clean_stale_worktrees(git_repo)
    assert any("stale_worktree" in c for c in cleaned)

    # 4. Verify directory, branch, and metadata are cleaned up
    assert not os.path.exists(stale_dir)
    assert not os.path.exists(meta_path)
    branches = run_git(["branch", "--list", stale_branch], cwd=git_repo)
    assert stale_branch not in branches


def test_dirty_tree_checkpoint_preserves_working_tree_and_index(git_repo):
    """
    Verify create_checkpoint does not modify the user's working tree or index
    (no git stash or git reset used, relies on custom GIT_INDEX_FILE).
    """
    from lmms.backend.cli.checkpoints import create_checkpoint, load_checkpoints

    # Ignore .lmms metadata directory as in standard repos
    with open(os.path.join(git_repo, ".gitignore"), "w") as f:
        f.write(".lmms/\n")
    run_git(["add", ".gitignore"], cwd=git_repo)
    run_git(["commit", "-m", "ignore .lmms"], cwd=git_repo)

    # 1. Create staged change in index
    staged_file = os.path.join(git_repo, "staged.txt")
    with open(staged_file, "w") as f:
        f.write("staged content in index\n")
    run_git(["add", "staged.txt"], cwd=git_repo)


    # 2. Create unstaged modification
    app_file = os.path.join(git_repo, "app.py")
    with open(app_file, "a") as f:
        f.write("# unstaged line\n")

    # 3. Create untracked file
    untracked_file = os.path.join(git_repo, "untracked.txt")
    with open(untracked_file, "w") as f:
        f.write("untracked notes\n")

    # Record porcelain status before checkpoint
    status_before = run_git(["status", "--porcelain"], cwd=git_repo)

    # 4. Execute checkpoint
    cid = create_checkpoint(git_repo, "Dirty Working Tree Test")
    assert cid is not None

    # Record porcelain status after checkpoint
    status_after = run_git(["status", "--porcelain"], cwd=git_repo)

    # 5. Assert status is 100% identical: index and working tree untouched
    assert status_before == status_after
    assert "staged.txt" in status_after
    assert "app.py" in status_after
    assert "untracked.txt" in status_after


    # Verify checkpoint metadata was recorded
    data = load_checkpoints(git_repo)
    assert cid in data
    assert data[cid]["type"] == "git"
    assert "git_hash" in data[cid]

