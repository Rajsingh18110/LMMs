import launcher


def test_help_launch_does_not_start_engine(monkeypatch):
    captured = {}

    def fake_run(command, env):
        captured["command"] = command

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    monkeypatch.setattr(launcher, "ensure_engine_running", lambda: (_ for _ in ()).throw(AssertionError()))

    launcher.launch("cli", ["--help"], ensure_engine=False)

    assert captured["command"][-2:] == ["lmms.backend.main", "--help"]
