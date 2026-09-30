import os

from lmms.backend.tools.boundaries import is_within_workspace, require_workspace_path


def test_workspace_boundary_allows_nested_paths(tmp_path):
    nested = tmp_path / "src" / "main.py"
    assert is_within_workspace(str(nested), str(tmp_path))
    assert require_workspace_path(str(nested), str(tmp_path)).endswith("src/main.py")


def test_workspace_boundary_rejects_prefix_lookalike(tmp_path):
    workspace = tmp_path / "app"
    lookalike = tmp_path / "app-copy" / "secret.txt"
    assert not is_within_workspace(str(lookalike), str(workspace))


def test_workspace_boundary_resolves_symlinks(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace / "escape"
    os.symlink(outside, link)

    assert not is_within_workspace(str(link / "secret.txt"), str(workspace))
