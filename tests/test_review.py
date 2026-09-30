import shutil
import subprocess

import pytest

from lmms.backend.cli.review import git_review, is_read_only_command, preview_file_change


def test_preview_file_change_shows_unified_diff(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("answer = 1\n", encoding="utf-8")

    preview = preview_file_change(str(target), "answer = 2\n")

    assert "-answer = 1" in preview
    assert "+answer = 2" in preview


def test_read_only_command_classification():
    assert is_read_only_command("git status --short") is True
    assert is_read_only_command("rg TODO") is True
    assert is_read_only_command("git commit -m message") is False
    assert is_read_only_command("python3 script.py") is False


@pytest.mark.skipif(shutil.which("git") is None, reason="git is required")
def test_git_review_reports_changed_workspace(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    target = tmp_path / "app.py"
    target.write_text("answer = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=LMMS", "-c", "user.email=lmms@example.invalid", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    target.write_text("answer = 2\n", encoding="utf-8")

    review = git_review(str(tmp_path))

    assert review["available"] is True
    assert "app.py" in review["stat"]
    assert review["clean"] is True
