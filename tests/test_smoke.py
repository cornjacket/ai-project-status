"""End-to-end smoke test: run the orchestrator in --dry-run mode against
two tmp git repos and verify the pipeline wiring."""
import yaml

import _lib
import run
from conftest import init_git_repo, commit_log


def test_dry_run_orchestrator_pipeline(project, monkeypatch):
    foo = project / "tracked" / "ai-foo"
    bar = project / "tracked" / "ai-bar"
    init_git_repo(foo)
    init_git_repo(bar)
    foo_head = commit_log(foo, "implemented vector store")
    bar_head = commit_log(bar, "added prompt cache")

    (project / "repos.yml").write_text(yaml.safe_dump({"repos": [
        {"name": "ai-foo", "remote": "git@example.com:foo.git"},
        {"name": "ai-bar", "remote": "git@example.com:bar.git"},
    ]}))

    # run.py imported SUMMARY_MD at its own import time, so the conftest
    # patch on _lib.SUMMARY_MD does not reach it. Patch the rebound name too.
    monkeypatch.setattr(run, "SUMMARY_MD", project / "summary.md")
    monkeypatch.setattr("sys.argv", ["run.py", "--dry-run", "--skip-sync", "--skip-commit"])

    run.main()

    text = (project / "summary.md").read_text()
    assert "### ai-foo" in text
    assert "### ai-bar" in text
    # Both repos active → polish path runs (still dry-run, so deterministic wrap)
    assert "## " in text  # day section header
    # Marker preserved above the new section
    assert text.index("<!-- new sections inserted below -->") < text.index("### ai-foo")

    # --skip-commit means state.json was not advanced. Exercise advance_state
    # directly to cover the other half of the pipeline.
    _lib.advance_state(today="2026-04-30")
    import json
    state = json.loads((project / "state.json").read_text())
    assert state["ai-foo"]["last_commit"] == foo_head
    assert state["ai-bar"]["last_commit"] == bar_head
    assert state["ai-foo"]["last_activity_date"] == "2026-04-30"
    assert state["ai-bar"]["last_activity_date"] == "2026-04-30"


def test_dry_run_with_single_active_skips_polish(project, monkeypatch):
    """active_count < 2 → no polish call, drafts wrapped directly."""
    foo = project / "tracked" / "ai-foo"
    init_git_repo(foo)
    commit_log(foo, "did the thing")

    (project / "repos.yml").write_text(yaml.safe_dump({"repos": [
        {"name": "ai-foo", "remote": "git@example.com:foo.git"},
    ]}))

    monkeypatch.setattr(run, "SUMMARY_MD", project / "summary.md")
    monkeypatch.setattr("sys.argv", ["run.py", "--dry-run", "--skip-sync", "--skip-commit"])

    run.main()

    text = (project / "summary.md").read_text()
    assert "### ai-foo" in text
    assert "(dry-run placeholder" in text


def test_dry_run_mixed_active_and_inactive(project, monkeypatch):
    """One active repo and one inactive repo: both appear, with the right shape."""
    foo = project / "tracked" / "ai-foo"
    bar = project / "tracked" / "ai-bar"
    init_git_repo(foo)
    init_git_repo(bar)
    commit_log(foo, "new work")
    bar_head = commit_log(bar, "stable")

    (project / "repos.yml").write_text(yaml.safe_dump({"repos": [
        {"name": "ai-foo", "remote": "git@example.com:foo.git"},
        {"name": "ai-bar", "remote": "git@example.com:bar.git"},
    ]}))
    (project / "state.json").write_text(
        '{"ai-bar": {"last_commit": "' + bar_head + '", '
        '"last_synced": "2026-04-22", "last_activity_date": "2026-04-22"}}'
    )

    monkeypatch.setattr(run, "SUMMARY_MD", project / "summary.md")
    monkeypatch.setattr("sys.argv", ["run.py", "--dry-run", "--skip-sync", "--skip-commit"])

    run.main()

    text = (project / "summary.md").read_text()
    assert "### ai-foo" in text
    assert "### ai-bar" in text
    assert "No activity for 8 days (last activity 2026-04-22)" in text
