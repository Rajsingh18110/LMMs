from types import SimpleNamespace

from lmms.backend.cli.diagnostics import collect_doctor_report, collect_status


def test_collect_status_reports_online_engine(tmp_path):
    (tmp_path / ".git").mkdir()

    status = collect_status(
        str(tmp_path),
        "http://engine",
        request_get=lambda *args, **kwargs: SimpleNamespace(status_code=200),
    )

    assert status["engine"] == "online"
    assert status["workspace_exists"] is True
    assert status["git_repository"] is True


def test_collect_doctor_report_handles_offline_engine(tmp_path):
    def offline_request(*args, **kwargs):
        raise OSError("connection refused")

    report = collect_doctor_report(str(tmp_path), "http://engine", request_get=offline_request)

    assert report["engine"] == "offline"
    assert report["healthy"] is False
