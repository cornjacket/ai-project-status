"""Unit tests for tools/_lib.py — primarily gather_report() classification
and advance_state()."""
import json

import yaml

import _lib
from conftest import init_git_repo, commit_log


def titles(entry):
    return [c["title"] for c in (entry["commit_telemetry"] or [])]


def write_repos(project, entries):
    (project / "repos.yml").write_text(yaml.safe_dump({"repos": entries}))


def write_state(project, state):
    (project / "state.json").write_text(json.dumps(state))


def read_state(project):
    return json.loads((project / "state.json").read_text())


def test_not_synced_when_repo_dir_missing(project):
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    report = _lib.gather_report(today="2026-04-30")
    assert len(report) == 1
    assert report[0]["status"] == "NOT_SYNCED"
    assert report[0]["head"] is None


def test_active_on_first_run_uses_empty_tree_baseline(project):
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    head = commit_log(repo, "first entry")
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])

    report = _lib.gather_report(today="2026-04-30")

    assert report[0]["status"] == "ACTIVE"
    assert report[0]["head"] == head
    assert report[0]["last_commit"] == _lib.EMPTY_TREE
    assert "first entry" in titles(report[0])
    assert "work.txt" in report[0]["file_stat"]
    assert head[:7] in report[0]["commit_list"]


def test_inactive_when_head_matches_last_commit(project):
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    head = commit_log(repo, "old work")
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    write_state(project, {"ai-foo": {
        "last_commit": head,
        "last_synced": "2026-04-22",
        "last_activity_date": "2026-04-22",
    }})

    report = _lib.gather_report(today="2026-04-30")

    assert report[0]["status"] == "INACTIVE"
    assert report[0]["days_inactive"] == 8
    assert report[0]["last_activity_date"] == "2026-04-22"
    assert report[0]["commit_telemetry"] is None


def test_inactive_suppressed_when_flag_false(project):
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    head = commit_log(repo, "old work")
    write_repos(project, [{
        "name": "ai-foo", "remote": "git@example.com:foo.git",
        "report_inactivity": False,
    }])
    write_state(project, {"ai-foo": {
        "last_commit": head,
        "last_synced": "2026-04-22",
        "last_activity_date": "2026-04-22",
    }})

    report = _lib.gather_report(today="2026-04-30")
    assert report[0]["status"] == "INACTIVE_SUPPRESSED"


def test_active_with_new_commits_since_last(project):
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    first = commit_log(repo, "old work")
    second = commit_log(repo, "new work")
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    write_state(project, {"ai-foo": {
        "last_commit": first,
        "last_synced": "2026-04-29",
        "last_activity_date": "2026-04-29",
    }})

    e = _lib.gather_report(today="2026-04-30")[0]

    assert e["status"] == "ACTIVE"
    assert e["head"] == second
    assert e["last_commit"] == first
    assert "new work" in titles(e)
    assert "old work" not in titles(e)  # not in this slice
    assert "work.txt" in e["file_stat"]
    assert second[:7] in e["commit_list"]
    assert first[:7] not in e["commit_list"]


def test_disabled_repo_is_omitted(project):
    write_repos(project, [
        {"name": "ai-foo", "remote": "git@example.com:foo.git", "enabled": False},
        {"name": "ai-bar", "remote": "git@example.com:bar.git"},
    ])
    report = _lib.gather_report(today="2026-04-30")
    assert [e["name"] for e in report] == ["ai-bar"]


def test_repo_order_follows_repos_yml(project):
    write_repos(project, [
        {"name": "ai-zeta", "remote": "git@example.com:zeta.git"},
        {"name": "ai-alpha", "remote": "git@example.com:alpha.git"},
    ])
    report = _lib.gather_report(today="2026-04-30")
    assert [e["name"] for e in report] == ["ai-zeta", "ai-alpha"]


def test_days_inactive_is_none_when_no_activity_recorded(project):
    """A first-time NOT_SYNCED repo has no last_activity_date; days_inactive stays None."""
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    report = _lib.gather_report(today="2026-04-30")
    assert report[0]["days_inactive"] is None
    assert report[0]["last_activity_date"] is None


def test_advance_state_bumps_activity_date_when_head_moved(project):
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    first = commit_log(repo, "old work")
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    write_state(project, {"ai-foo": {
        "last_commit": first,
        "last_synced": "2026-04-29",
        "last_activity_date": "2026-04-29",
    }})
    second = commit_log(repo, "new work")

    _lib.advance_state(today="2026-04-30")

    s = read_state(project)["ai-foo"]
    assert s["last_commit"] == second
    assert s["last_synced"] == "2026-04-30"
    assert s["last_activity_date"] == "2026-04-30"


def test_git_telemetry_parses_context_impact_schema(project):
    """The structured commit schema is parsed into title/context/impact, and
    multi-line bodies survive — both with and without a blank line after the
    title (git folds the whole first paragraph into %s, so we parse %B)."""
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    # No blank line after the title (matches the CLAUDE.md schema verbatim).
    commit_log(repo, "x", msg=(
        "engine(telemetry): swap log.md for git telemetry\n"
        "- [Context]: log.md duplicated history; this removes the\n"
        "  duplicate-logging overhead.\n"
        "- [Impact]: backward-looking reports read commit messages."
    ))
    # With a blank line (conventional git style).
    commit_log(repo, "y", msg=(
        "feat(api): add retry logic\n\n"
        "- [Context]: upstream flakiness caused 502s.\n"
        "- [Impact]: success rate up, no API change."
    ))

    commits = _lib.git_telemetry(repo, "HEAD")
    by_title = {c["title"]: c for c in commits}

    eng = by_title["engine(telemetry): swap log.md for git telemetry"]
    assert "duplicate-logging overhead" in eng["context"]  # continuation folded in
    assert eng["impact"] == "backward-looking reports read commit messages."

    api = by_title["feat(api): add retry logic"]
    assert api["context"] == "upstream flakiness caused 502s."
    assert api["impact"] == "success rate up, no API change."


def test_since_override_activates_repo_independent_of_state(project):
    """`since` is an ad-hoc override: a repo INACTIVE by state.json becomes
    ACTIVE when the time window contains commits (Locked decision #1)."""
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    head = commit_log(repo, "old work")
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    # state says we're caught up to head → default run would be INACTIVE.
    write_state(project, {"ai-foo": {
        "last_commit": head,
        "last_synced": "2026-04-29",
        "last_activity_date": "2026-04-29",
    }})

    default = _lib.gather_report(today="2026-04-30")[0]
    assert default["status"] == "INACTIVE"

    windowed = _lib.gather_report(today="2026-04-30", since="1 year ago")[0]
    assert windowed["status"] == "ACTIVE"
    assert "old work" in titles(windowed)


def test_advance_state_preserves_activity_date_when_idle(project):
    repo = project / "tracked" / "ai-foo"
    init_git_repo(repo)
    head = commit_log(repo, "old work")
    write_repos(project, [{"name": "ai-foo", "remote": "git@example.com:foo.git"}])
    write_state(project, {"ai-foo": {
        "last_commit": head,
        "last_synced": "2026-04-29",
        "last_activity_date": "2026-04-22",
    }})

    _lib.advance_state(today="2026-04-30")

    s = read_state(project)["ai-foo"]
    assert s["last_commit"] == head
    assert s["last_synced"] == "2026-04-30"
    assert s["last_activity_date"] == "2026-04-22"


def test_load_repos_defaults_priority_to_last_band(project):
    (project / "repos.yml").write_text(
        "repos:\n  - name: ai-foo\n    remote: git@example.com:x/ai-foo.git\n"
    )
    assert _lib.load_repos()[0]["priority"] == _lib.DEFAULT_PRIORITY


def test_load_repos_reads_explicit_priority(project):
    (project / "repos.yml").write_text(
        "repos:\n  - name: ai-foo\n    remote: git@example.com:x/ai-foo.git\n"
        "    priority: 1\n"
    )
    assert _lib.load_repos()[0]["priority"] == 1
