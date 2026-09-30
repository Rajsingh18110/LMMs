from lmms.backend.context.workspace_rules import MAX_RULES_CHARS, load_workspace_rules


def test_load_workspace_rules_reads_project_file(tmp_path):
    (tmp_path / "LMMS.md").write_text("Run unit tests before editing.", encoding="utf-8")

    assert load_workspace_rules(str(tmp_path)) == "Run unit tests before editing."


def test_load_workspace_rules_ignores_missing_workspace_file(tmp_path):
    assert load_workspace_rules(str(tmp_path)) == ""


def test_load_workspace_rules_bounds_large_file(tmp_path):
    (tmp_path / "LMMS.md").write_text("x" * (MAX_RULES_CHARS + 1), encoding="utf-8")

    rules = load_workspace_rules(str(tmp_path))
    assert "truncated" in rules
    assert len(rules) > MAX_RULES_CHARS
