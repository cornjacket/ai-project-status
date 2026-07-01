"""Unit tests for tools/aggregate-plans.py."""
from datetime import date
from pathlib import Path

import importlib.util


def _load_aggregate_plans():
    """The module name has a hyphen, so import via spec."""
    here = Path(__file__).resolve().parent.parent
    path = here / "tools" / "aggregate-plans.py"
    spec = importlib.util.spec_from_file_location("aggregate_plans", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ap = _load_aggregate_plans()


def test_most_recent_weekday_monday_is_today():
    assert ap.most_recent_weekday(date(2026, 5, 4)) == date(2026, 5, 4)  # Mon


def test_most_recent_weekday_friday_is_today():
    assert ap.most_recent_weekday(date(2026, 5, 8)) == date(2026, 5, 8)  # Fri


def test_most_recent_weekday_saturday_returns_friday():
    assert ap.most_recent_weekday(date(2026, 5, 9)) == date(2026, 5, 8)


def test_most_recent_weekday_sunday_returns_friday():
    assert ap.most_recent_weekday(date(2026, 5, 10)) == date(2026, 5, 8)


def test_parse_plan_em_dash():
    plan_date, body = ap.parse_plan(
        "# Daily plan — 2026-05-06\n\nWork on foo.\n"
    )
    assert plan_date == date(2026, 5, 6)
    assert body == "Work on foo."


def test_parse_plan_hyphen():
    plan_date, body = ap.parse_plan(
        "# Daily plan - 2026-05-06\n\nWork on foo.\n"
    )
    assert plan_date == date(2026, 5, 6)


def test_parse_plan_missing_header():
    plan_date, body = ap.parse_plan("Hello world.\n")
    assert plan_date is None
    assert body == "Hello world."


def test_parse_plan_invalid_date():
    plan_date, body = ap.parse_plan("# Daily plan — 2026-13-99\n\nx\n")
    assert plan_date is None


def test_render_repo_section_missing_file(tmp_path):
    out = ap.render_repo_section("ai-foo", tmp_path / "missing.md", date(2026, 5, 6))
    assert "ai-foo — no plan committed" in out


def test_render_repo_section_fresh(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-06\n\nDo the thing.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 6))
    assert "## ai-foo — plan for 2026-05-06" in out
    assert "Do the thing." in out
    assert "STALE" not in out


def test_render_repo_section_stale(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-04-30\n\nOld plan.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 6))
    assert "STALE" in out
    assert "last plan: 2026-04-30" in out
    assert "Old plan." in out


def test_render_repo_section_friday_plan_on_saturday_is_fresh(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-08\n\nFriday's plan.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 9))  # Saturday
    assert "STALE" not in out
    assert "plan for 2026-05-08" in out


def test_render_repo_section_friday_plan_on_monday_is_stale(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-08\n\nFriday's plan.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 11))  # Monday
    assert "STALE" in out


def test_render_repo_section_malformed(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("just some text without a header\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 6))
    assert "unparseable" in out


def test_build_summary_skips_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "TRACKED_DIR", tmp_path)
    repos = [
        {"name": "ai-foo", "enabled": True},
        {"name": "ai-bar", "enabled": False},
    ]
    out = ap.build_summary(today=date(2026, 5, 6), repos=repos)
    assert "ai-foo" in out
    assert "ai-bar" not in out


def test_build_summary_header_includes_today():
    out = ap.build_summary(today=date(2026, 5, 6), repos=[])
    assert "# Daily plan summary — 2026-05-06" in out


def test_archive_summary_writes_dated_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "DAILY_PLAN_ARCHIVE_DIR", tmp_path / "daily-plan-archive")
    summary = "# Daily plan summary — 2026-05-06\n\nbody\n"
    dest = ap.archive_summary(date(2026, 5, 6), summary)
    assert dest == tmp_path / "daily-plan-archive" / "2026-05-06.md"
    assert dest.read_text() == summary


def test_archive_summary_is_idempotent_per_day(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "DAILY_PLAN_ARCHIVE_DIR", tmp_path / "daily-plan-archive")
    ap.archive_summary(date(2026, 5, 6), "first\n")
    ap.archive_summary(date(2026, 5, 6), "second\n")
    files = list((tmp_path / "daily-plan-archive").iterdir())
    assert [f.name for f in files] == ["2026-05-06.md"]
    assert files[0].read_text() == "second\n"
