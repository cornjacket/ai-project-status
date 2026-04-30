"""Unit tests for the pure helpers in tools/run.py."""
import run


def test_render_inactive_with_activity_date():
    e = {"name": "ai-foo", "days_inactive": 8, "last_activity_date": "2026-04-22"}
    assert run.render_inactive(e) == (
        "### ai-foo\nNo activity for 8 days (last activity 2026-04-22)"
    )


def test_render_inactive_without_activity_date():
    e = {"name": "ai-foo", "days_inactive": None, "last_activity_date": None}
    assert run.render_inactive(e) == "### ai-foo\nNo activity recorded yet"


def test_prepend_to_summary_inserts_after_marker(project, monkeypatch):
    summary = project / "summary.md"
    monkeypatch.setattr(run, "SUMMARY_MD", summary)

    run.prepend_to_summary("## 2026-04-30\n\n### ai-foo\n- did stuff")

    text = summary.read_text()
    assert "<!-- new sections inserted below -->" in text
    assert "## 2026-04-30" in text
    assert text.index("<!-- new sections inserted below -->") < text.index("## 2026-04-30")


def test_prepend_to_summary_keeps_newest_on_top(project, monkeypatch):
    summary = project / "summary.md"
    monkeypatch.setattr(run, "SUMMARY_MD", summary)

    run.prepend_to_summary("## 2026-04-29\n\n### ai-foo\n- old")
    run.prepend_to_summary("## 2026-04-30\n\n### ai-foo\n- new")

    text = summary.read_text()
    assert text.index("## 2026-04-30") < text.index("## 2026-04-29")


def test_prepend_to_summary_without_marker(project, monkeypatch):
    summary = project / "summary.md"
    summary.write_text("# Title\n\n## 2026-04-29\n\n### ai-foo\n- old\n")
    monkeypatch.setattr(run, "SUMMARY_MD", summary)

    run.prepend_to_summary("## 2026-04-30\n\n### ai-foo\n- new")

    text = summary.read_text()
    assert text.index("## 2026-04-30") < text.index("## 2026-04-29")


def test_prepend_to_summary_empty_file(project, monkeypatch):
    summary = project / "summary.md"
    summary.write_text("")
    monkeypatch.setattr(run, "SUMMARY_MD", summary)

    run.prepend_to_summary("## 2026-04-30\n\n### ai-foo\n- new")

    assert "## 2026-04-30" in summary.read_text()


def test_format_slice_includes_all_sections():
    e = {
        "name": "ai-foo",
        "last_commit": "abc1234567",
        "head": "def9876543",
        "log_diff": "+ added thing",
        "file_stat": " log.md | 1 +",
        "commit_list": "def9876 added thing",
    }
    out = run.format_slice(e)
    assert "abc12345..def98765" in out
    assert "## log.md additions" in out
    assert "+ added thing" in out
    assert "## file stat" in out
    assert "## commits" in out


def test_format_slice_handles_empty_fields():
    e = {
        "name": "ai-foo",
        "last_commit": "abc1234567",
        "head": "def9876543",
        "log_diff": "",
        "file_stat": "",
        "commit_list": "",
    }
    out = run.format_slice(e)
    assert "(none)" in out
