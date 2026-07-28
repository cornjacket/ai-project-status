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


def test_remote_to_url_https_strips_git():
    assert ap.remote_to_url("https://github.com/cornjacket/ai-foo.git") == \
        "https://github.com/cornjacket/ai-foo"


def test_remote_to_url_https_without_git():
    assert ap.remote_to_url("https://github.com/cornjacket/ai-foo") == \
        "https://github.com/cornjacket/ai-foo"


def test_remote_to_url_scp_form():
    assert ap.remote_to_url("git@github.com:cornjacket/ai-foo.git") == \
        "https://github.com/cornjacket/ai-foo"


def test_remote_to_url_ssh_form():
    assert ap.remote_to_url("ssh://git@github.com/cornjacket/ai-foo.git") == \
        "https://github.com/cornjacket/ai-foo"


def test_remote_to_url_none_and_unrecognized():
    assert ap.remote_to_url(None) is None
    assert ap.remote_to_url("") is None
    assert ap.remote_to_url("not-a-remote") is None


def test_render_repo_section_links_name_when_remote_given(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-06\n\nDo the thing.\n")
    out = ap.render_repo_section(
        "ai-foo", plan, date(2026, 5, 6),
        "https://github.com/cornjacket/ai-foo.git",
    )
    assert "## [ai-foo](https://github.com/cornjacket/ai-foo) — plan for 2026-05-06" in out


def test_render_repo_section_plain_name_without_remote(tmp_path):
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-06\n\nDo the thing.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 6))
    assert "## ai-foo — plan for 2026-05-06" in out


def test_render_repo_section_missing_file_is_linked(tmp_path):
    out = ap.render_repo_section(
        "ai-foo", tmp_path / "missing.md", date(2026, 5, 6),
        "git@github.com:cornjacket/ai-foo.git",
    )
    assert "## [ai-foo](https://github.com/cornjacket/ai-foo) — no plan committed" in out


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


# --- at-a-glance overview table -------------------------------------------

def test_extract_focus_takes_first_bullet_of_focus_section():
    body = (
        "**What this repo is (for a newcomer):** A thing.\n\n"
        "**Focus / plan:**\n\n"
        "- Ship the widget\n"
        "- Then the other widget\n"
    )
    assert ap.extract_focus(body) == "Ship the widget"


def test_extract_focus_falls_back_to_first_bullet_anywhere():
    """Older plans predate the fixed body structure."""
    assert ap.extract_focus("Some prose.\n\n- Do the thing\n") == "Do the thing"


def test_extract_focus_none_without_bullets():
    assert ap.extract_focus("Just prose, no bullets.\n") is None


def test_plan_state_fresh_stale_missing_unparseable(tmp_path):
    today = date(2026, 5, 6)  # Wednesday
    missing = tmp_path / "nope.md"
    assert ap.plan_state(missing, today)[0] == "missing"

    bad = tmp_path / "bad.md"
    bad.write_text("no header here\n")
    assert ap.plan_state(bad, today)[0] == "unparseable"

    stale = tmp_path / "stale.md"
    stale.write_text("# Daily plan — 2026-04-30\n\nold\n")
    assert ap.plan_state(stale, today)[0] == "stale"

    fresh = tmp_path / "fresh.md"
    fresh.write_text("# Daily plan — 2026-05-06\n\nnew\n")
    state, plan_date, body = ap.plan_state(fresh, today)
    assert (state, plan_date, body) == ("fresh", date(2026, 5, 6), "new")


def _row(name, state, priority):
    return {"name": name, "state": state, "priority": priority}


def test_sort_rows_puts_fresh_before_stale_regardless_of_priority():
    rows = [_row("stale-p1", "stale", 1), _row("fresh-p3", "fresh", 3)]
    assert [r["name"] for _, r in ap.sort_rows(rows)] == ["fresh-p3", "stale-p1"]


def test_sort_rows_orders_by_priority_within_a_group():
    rows = [_row("b", "fresh", 3), _row("a", "fresh", 1), _row("c", "fresh", 2)]
    assert [r["name"] for _, r in ap.sort_rows(rows)] == ["a", "c", "b"]


def test_sort_rows_keeps_repos_yml_order_on_ties():
    rows = [_row("first", "fresh", 2), _row("second", "fresh", 2)]
    assert [r["name"] for _, r in ap.sort_rows(rows)] == ["first", "second"]


def test_sort_rows_treats_missing_plan_as_not_fresh():
    rows = [_row("missing-p1", "missing", 1), _row("fresh-p2", "fresh", 2)]
    assert [r["name"] for _, r in ap.sort_rows(rows)] == ["fresh-p2", "missing-p1"]


def test_cell_escapes_pipes_so_the_table_survives():
    assert ap._cell("a | b") == "a \\| b"


def test_cell_collapses_newlines_and_truncates():
    assert ap._cell("one\ntwo") == "one two"
    out = ap._cell("word " * 40)
    assert len(out) <= ap.MAX_FOCUS_CHARS + 1 and out.endswith("…")


def test_render_overview_renders_a_row_per_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "TRACKED_DIR", tmp_path)
    (tmp_path / "ai-foo").mkdir()
    (tmp_path / "ai-foo" / "daily-plan.md").write_text(
        "# Daily plan — 2026-05-06\n\n**Focus / plan:**\n\n- Ship it\n"
    )
    out = ap.render_overview(
        [{"name": "ai-foo", "remote": "https://github.com/x/ai-foo.git",
          "priority": 2}],
        date(2026, 5, 6),
    )
    assert "## At a glance" in out
    assert "| Repo | Pri | Plan | Focus | Idle |" in out
    assert "[ai-foo](https://github.com/x/ai-foo)" in out
    assert "| P2 |" in out
    assert "2026-05-06" in out
    assert "Ship it" in out


def test_render_overview_flags_stale_and_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "TRACKED_DIR", tmp_path)
    (tmp_path / "ai-stale").mkdir()
    (tmp_path / "ai-stale" / "daily-plan.md").write_text(
        "# Daily plan — 2026-04-30\n\nold\n"
    )
    out = ap.render_overview(
        [{"name": "ai-stale"}, {"name": "ai-gone"}], date(2026, 5, 6)
    )
    assert "**STALE** 2026-04-30" in out
    assert "**none**" in out
    # Neither repo is a git checkout here, so idle is unknown, not zero.
    assert "| — |" in out


def test_render_overview_defaults_unranked_repos_to_last_band(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "TRACKED_DIR", tmp_path)
    out = ap.render_overview([{"name": "ai-foo"}], date(2026, 5, 6))
    assert f"| P{ap.DEFAULT_PRIORITY} |" in out


def test_render_overview_empty_without_repos():
    assert ap.render_overview([], date(2026, 5, 6)) == ""


def test_build_summary_includes_the_overview(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "TRACKED_DIR", tmp_path)
    out = ap.build_summary(
        today=date(2026, 5, 6), repos=[{"name": "ai-foo", "enabled": True}]
    )
    assert "## At a glance" in out
    assert out.index("## At a glance") < out.index("## ai-foo")


# --- drift callout in the per-repo section ---------------------------------

def test_drift_notice_empty_when_in_sync(monkeypatch):
    monkeypatch.setattr(ap, "target_drift", lambda name: [])
    assert ap.drift_notice("ai-foo", "git@example.com:x/ai-foo.git") == ""


def test_drift_notice_names_problems_and_the_fix(monkeypatch):
    monkeypatch.setattr(
        ap, "target_drift", lambda name: ["CLAUDE.md rule block is out of date"]
    )
    out = ap.drift_notice("ai-foo", "git@example.com:x/ai-foo.git")
    assert "project-status drift" in out
    assert "rule block is out of date" in out
    assert "./setup-new-repo.sh --update git@example.com:x/ai-foo.git" in out


def test_drift_shows_up_in_the_repo_section(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "target_drift", lambda name: ["guide is missing"])
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-06\n\nDo the thing.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 6))
    assert "project-status drift" in out
    # the callout sits under the header, above the plan body
    assert out.index("drift") < out.index("Do the thing.")


def test_drift_shows_up_even_without_a_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "target_drift", lambda name: ["guide is missing"])
    out = ap.render_repo_section("ai-foo", tmp_path / "none.md", date(2026, 5, 6))
    assert "no plan committed" in out
    assert "project-status drift" in out


def test_no_drift_callout_when_repo_is_in_sync(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "target_drift", lambda name: [])
    plan = tmp_path / "daily-plan.md"
    plan.write_text("# Daily plan — 2026-05-06\n\nDo the thing.\n")
    out = ap.render_repo_section("ai-foo", plan, date(2026, 5, 6))
    assert "drift" not in out
