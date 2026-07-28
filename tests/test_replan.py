"""Unit tests for tools/replan.py.

The `claude -p` call itself is out of scope (non-deterministic prose), so it is
stubbed; everything around it — target-date math, checkout resolution, response
parsing, the in-place write and its clobber guards, and resumability — is
deterministic and tested.
"""
import importlib.util
import json
import subprocess
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import init_git_repo


def _load(name):
    """Tool module names have hyphens, so import via spec."""
    path = Path(__file__).resolve().parent.parent / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rp = _load("replan")

TARGET = date(2026, 7, 28)

PLAN = (
    "# Daily plan — 2026-07-28\n\n"
    "**What this repo is (for a newcomer):** `ai-foo` builds widgets.\n\n"
    "**Last implemented:** the widget.\n\n"
    "**Focus / plan:**\n\n- ship the other widget\n"
)

REPLY = f"STATUS: advanced\nNOTE: task 3 just landed, task 4 is next\n---PLAN---\n{PLAN}"


def _args(**over):
    base = dict(only=None, force=False, dry_run=False, timeout=60, model=None)
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """Keep the run ledger out of the real repo root."""
    monkeypatch.setattr(rp, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rp, "LAST_RUN_JSON", tmp_path / ".replan-last-run.json")
    return tmp_path


# --- target date ----------------------------------------------------------

@pytest.mark.parametrize("today,expected", [
    (date(2026, 7, 27), date(2026, 7, 28)),  # Mon -> Tue
    (date(2026, 7, 30), date(2026, 7, 31)),  # Thu -> Fri
    (date(2026, 7, 31), date(2026, 8, 3)),   # Fri -> Mon
    (date(2026, 8, 1), date(2026, 8, 3)),    # Sat -> Mon
    (date(2026, 8, 2), date(2026, 8, 3)),    # Sun -> Mon
])
def test_next_business_day_skips_the_weekend(today, expected):
    assert rp.next_business_day(today) == expected


# --- prompt rendering -----------------------------------------------------

def test_render_prompt_fills_both_placeholders():
    out = rp.render_prompt("ai-foo", TARGET, "repo={{REPO_NAME}} date={{TARGET_DATE}}")
    assert out == "repo=ai-foo date=2026-07-28"


def test_shipped_prompt_template_carries_the_invariants():
    text = rp.PROMPT_TEMPLATE.read_text()
    assert "{{REPO_NAME}}" in text and "{{TARGET_DATE}}" in text
    for needle in ("STATUS:", rp.PLAN_MARKER, "Read-only", "blocked"):
        assert needle in text, f"prompt template is missing {needle!r}"


def test_agent_cannot_write_anything():
    """The read-only invariant is enforced by the CLI flags, not the prompt."""
    for tool in ("Write", "Edit", "NotebookEdit"):
        assert tool in rp.DISALLOWED_TOOLS
    assert not any(t.startswith("Bash(git commit") or t.startswith("Bash(git push")
                   for t in rp.ALLOWED_TOOLS)
    cmd = rp.claude_cmd()
    assert "--disallowedTools" in cmd and "Write" in cmd[cmd.index("--disallowedTools") + 1]


# --- response parsing -----------------------------------------------------

def test_parse_response_reads_verdict_note_and_plan():
    verdict, note, plan = rp.parse_response(REPLY)
    assert verdict == "advanced"
    assert note == "task 3 just landed, task 4 is next"
    assert plan.startswith("# Daily plan — 2026-07-28")


def test_parse_response_accepts_a_kept_verdict():
    verdict, _, plan = rp.parse_response(f"STATUS: kept\nNOTE: no clear next step\n"
                                         f"---PLAN---\n{PLAN}")
    assert verdict == "kept"
    assert plan


def test_parse_response_blocked_needs_no_plan():
    verdict, note, plan = rp.parse_response("STATUS: blocked\nNOTE: tasks/ is empty")
    assert (verdict, note, plan) == ("blocked", "tasks/ is empty", "")


def test_parse_response_recovers_without_the_marker():
    verdict, _, plan = rp.parse_response(f"STATUS: kept\nNOTE: n/a\n\n{PLAN}")
    assert verdict == "kept"
    assert plan.startswith("# Daily plan")


def test_parse_response_strips_a_stray_code_fence():
    _, _, plan = rp.parse_response(
        f"STATUS: advanced\nNOTE: x\n{rp.PLAN_MARKER}\n```markdown\n{PLAN.strip()}\n```"
    )
    assert plan.startswith("# Daily plan")
    assert "```markdown" not in plan


def test_parse_response_rejects_a_missing_status():
    with pytest.raises(rp.DraftError):
        rp.parse_response(PLAN)


def test_parse_response_rejects_an_empty_plan_body():
    with pytest.raises(rp.DraftError):
        rp.parse_response(f"STATUS: advanced\nNOTE: x\n{rp.PLAN_MARKER}\n")


# --- header normalization -------------------------------------------------

def test_normalize_header_leaves_a_correct_date_alone():
    plan, rewritten = rp.normalize_header(PLAN, TARGET)
    assert (plan, rewritten) == (PLAN, False)


def test_normalize_header_corrects_a_drifted_date():
    drifted = PLAN.replace("2026-07-28", "2026-07-27", 1)
    plan, rewritten = rp.normalize_header(drifted, TARGET)
    assert rewritten
    assert plan.splitlines()[0] == "# Daily plan — 2026-07-28"
    # Only the header moves; the body is the agent's.
    assert "**Last implemented:** the widget." in plan


def test_normalize_header_rejects_a_headerless_draft():
    with pytest.raises(rp.DraftError):
        rp.normalize_header("just some prose", TARGET)


# --- the agent call -------------------------------------------------------

def test_run_claude_surfaces_a_nonzero_exit(monkeypatch):
    def fake(*a, **k):
        return SimpleNamespace(returncode=1, stdout="", stderr="Invalid API key\n")
    monkeypatch.setattr(rp.subprocess, "run", fake)
    with pytest.raises(rp.DraftError, match="Invalid API key"):
        rp.run_claude("p", Path("."), 60, None)


def test_run_claude_surfaces_an_error_result(monkeypatch):
    payload = json.dumps({"is_error": True, "result": "login expired"})
    monkeypatch.setattr(rp.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=payload, stderr=""))
    with pytest.raises(rp.DraftError, match="login expired"):
        rp.run_claude("p", Path("."), 60, None)


def test_run_claude_unwraps_the_json_result(monkeypatch):
    payload = json.dumps({"is_error": False, "result": REPLY})
    monkeypatch.setattr(rp.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=payload, stderr=""))
    assert rp.run_claude("p", Path("."), 60, None) == REPLY.strip()


def test_run_claude_reports_a_missing_cli(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError()
    monkeypatch.setattr(rp.subprocess, "run", boom)
    with pytest.raises(rp.DraftError, match="not found"):
        rp.run_claude("p", Path("."), 60, None)


# --- batch behaviour ------------------------------------------------------

OLD_PLAN = "# Daily plan — 2026-07-27\n\n**Focus / plan:**\n\n- yesterday's thing\n"


def _commit(checkout: Path, *args) -> None:
    subprocess.run(["git", *args], cwd=str(checkout), check=True, capture_output=True)


def _umbrella(tmp_path, *names, plan: str | None = OLD_PLAN):
    """A workspace of git repos, each with `plan` committed (so the working tree
    starts clean — the state the tool is designed to write into)."""
    u = tmp_path / "workspace"
    for n in names:
        init_git_repo(u / n)
        if plan is not None:
            (u / n / "daily-plan.md").write_text(plan)
            _commit(u / n, "add", "daily-plan.md")
            _commit(u / n, "commit", "-m", "docs(plan): today")
    return u


def _stub_agent(monkeypatch, reply=REPLY):
    monkeypatch.setattr(rp, "run_claude", lambda *a, **k: reply)
    monkeypatch.setattr(rp, "PROMPT_TEMPLATE", SimpleNamespace(read_text=lambda: "x"))


def test_batch_writes_the_plan_in_place(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "foo")
    _stub_agent(monkeypatch)

    results = rp.run_batch(TARGET, _args(), repos=[{"name": "foo"}], umbrella=umbrella)

    assert results[0]["status"] == "advanced"
    assert (umbrella / "foo" / "daily-plan.md").read_text() == PLAN
    assert results[0]["path"] == str(umbrella / "foo" / "daily-plan.md")


def test_batch_leaves_the_plan_uncommitted_and_unstaged(staged, tmp_path, monkeypatch):
    """Git is the review surface: the plan must show up as a modified file, and
    nothing may be staged, committed, or pushed on the human's behalf."""
    umbrella = _umbrella(tmp_path, "foo")
    _stub_agent(monkeypatch)
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(umbrella / "foo"),
                            capture_output=True, text=True).stdout

    rp.run_batch(TARGET, _args(), repos=[{"name": "foo"}], umbrella=umbrella)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(umbrella / "foo"),
                            capture_output=True, text=True).stdout
    after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(umbrella / "foo"),
                           capture_output=True, text=True).stdout
    assert status.strip() == "M daily-plan.md"  # modified, not staged ("M " would be)
    assert after == before                      # no commit was made


def test_batch_skips_repos_that_are_not_checked_out(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "checked-out")
    _stub_agent(monkeypatch)
    repos = [{"name": "checked-out"}, {"name": "absent"}]

    results = rp.run_batch(TARGET, _args(), repos=repos, umbrella=umbrella)

    assert [r["status"] for r in results] == ["advanced", "skipped"]
    assert results[1]["note"] == "not checked out locally"


def test_batch_isolates_one_repos_failure(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "good", "bad")

    def flaky(prompt, cwd, timeout, model):
        if Path(cwd).name == "bad":
            raise rp.DraftError("login expired")
        return REPLY

    monkeypatch.setattr(rp, "run_claude", flaky)
    monkeypatch.setattr(rp, "PROMPT_TEMPLATE", SimpleNamespace(read_text=lambda: "x"))

    results = rp.run_batch(TARGET, _args(), repos=[{"name": "bad"}, {"name": "good"}],
                           umbrella=umbrella)

    assert results[0]["status"] == "failed" and "login expired" in results[0]["note"]
    assert results[1]["status"] == "advanced"
    # The healthy repo is written even though an earlier one died...
    assert (umbrella / "good" / "daily-plan.md").read_text() == PLAN
    # ...and the failed one keeps the plan it had.
    assert (umbrella / "bad" / "daily-plan.md").read_text() == OLD_PLAN


def test_a_malformed_reply_never_overwrites_a_good_plan(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "foo")
    _stub_agent(monkeypatch, reply="STATUS: advanced\nNOTE: x\n---PLAN---\nno header here")

    results = rp.run_batch(TARGET, _args(), repos=[{"name": "foo"}], umbrella=umbrella)

    assert results[0]["status"] == "failed"
    assert (umbrella / "foo" / "daily-plan.md").read_text() == OLD_PLAN


def test_rerun_skips_repos_already_dated_for_the_target(staged, tmp_path, monkeypatch):
    """Resumability after the 2026-07-27 mid-batch auth failure: a re-run must not
    re-spend a call on a repo whose plan is already dated for the target."""
    umbrella = _umbrella(tmp_path, "foo")
    calls = []

    def counted(prompt, cwd, timeout, model):
        calls.append(cwd)
        return REPLY

    monkeypatch.setattr(rp, "run_claude", counted)
    monkeypatch.setattr(rp, "PROMPT_TEMPLATE", SimpleNamespace(read_text=lambda: "x"))
    repos = [{"name": "foo"}]

    rp.run_batch(TARGET, _args(), repos=repos, umbrella=umbrella)
    again = rp.run_batch(TARGET, _args(), repos=repos, umbrella=umbrella)
    assert len(calls) == 1
    assert again[0]["status"] == "skipped"
    assert "already dated" in again[0]["note"]

    rp.run_batch(TARGET, _args(force=True), repos=repos, umbrella=umbrella)
    assert len(calls) == 2


def test_batch_refuses_to_clobber_an_uncommitted_plan(staged, tmp_path, monkeypatch):
    """An uncommitted plan is work git cannot give back — never overwrite it
    without being told to."""
    umbrella = _umbrella(tmp_path, "foo")
    (umbrella / "foo" / "daily-plan.md").write_text(OLD_PLAN + "- hand-written wip\n")
    _stub_agent(monkeypatch)

    results = rp.run_batch(TARGET, _args(), repos=[{"name": "foo"}], umbrella=umbrella)

    assert results[0]["status"] == "skipped"
    assert "uncommitted changes" in results[0]["note"]
    assert "hand-written wip" in (umbrella / "foo" / "daily-plan.md").read_text()

    forced = rp.run_batch(TARGET, _args(force=True), repos=[{"name": "foo"}],
                          umbrella=umbrella)
    assert forced[0]["status"] == "advanced"


def test_batch_writes_a_repo_that_has_no_plan_yet(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "foo", plan=None)
    _stub_agent(monkeypatch)

    results = rp.run_batch(TARGET, _args(), repos=[{"name": "foo"}], umbrella=umbrella)

    assert results[0]["status"] == "advanced"
    assert (umbrella / "foo" / "daily-plan.md").read_text() == PLAN


def test_batch_records_the_run_for_report(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "foo")
    _stub_agent(monkeypatch)

    rp.run_batch(TARGET, _args(), repos=[{"name": "foo"}], umbrella=umbrella)

    stored = json.loads(rp.LAST_RUN_JSON.read_text())
    assert stored["date"] == TARGET.isoformat()
    assert stored["results"][0]["status"] == "advanced"


def test_only_limits_the_batch(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "foo", "bar")
    _stub_agent(monkeypatch)

    results = rp.run_batch(TARGET, _args(only="bar"),
                           repos=[{"name": "foo"}, {"name": "bar"}], umbrella=umbrella)

    assert [r["name"] for r in results] == ["bar"]
    assert (umbrella / "foo" / "daily-plan.md").read_text() == OLD_PLAN


def test_dry_run_calls_nothing_and_writes_nothing(staged, tmp_path, monkeypatch):
    umbrella = _umbrella(tmp_path, "foo")

    def boom(*a, **k):
        raise AssertionError("dry run must not call claude")

    monkeypatch.setattr(rp, "run_claude", boom)
    monkeypatch.setattr(rp, "PROMPT_TEMPLATE", SimpleNamespace(read_text=lambda: "x"))

    results = rp.run_batch(TARGET, _args(dry_run=True), repos=[{"name": "foo"}],
                           umbrella=umbrella)

    assert results[0]["status"] == "dry-run"
    assert (umbrella / "foo" / "daily-plan.md").read_text() == OLD_PLAN
    assert not rp.LAST_RUN_JSON.exists()


# --- plan header probing --------------------------------------------------

def test_plan_header_date_reads_the_current_plan(tmp_path):
    init_git_repo(tmp_path / "foo")
    (tmp_path / "foo" / "daily-plan.md").write_text(PLAN)
    assert rp.plan_header_date(tmp_path / "foo") == TARGET


def test_plan_header_date_is_none_without_a_parseable_header(tmp_path):
    init_git_repo(tmp_path / "foo")
    assert rp.plan_header_date(tmp_path / "foo") is None
    (tmp_path / "foo" / "daily-plan.md").write_text("no header\n")
    assert rp.plan_header_date(tmp_path / "foo") is None


# --- reporting ------------------------------------------------------------

def test_report_labels_every_outcome():
    text = rp.render_report([
        {"name": "a", "status": "advanced", "note": "next task is clear"},
        {"name": "b", "status": "kept", "note": ""},
        {"name": "c", "status": "blocked", "note": "tasks are stale"},
        {"name": "d", "status": "failed", "note": "timed out after 900s"},
        {"name": "e", "status": "skipped", "note": "not checked out locally"},
    ], TARGET)
    assert "drafted — advanced" in text
    assert "drafted — kept, re-dated" in text
    assert "BLOCKED — tasks are stale" in text
    assert "FAILED — timed out after 900s" in text
    assert "skipped — not checked out locally" in text


def test_next_steps_tells_the_user_to_review_commit_and_push():
    text = rp.next_steps([
        {"name": "a", "status": "advanced", "path": "/w/a/daily-plan.md"},
        {"name": "b", "status": "kept", "path": "/w/b/daily-plan.md"},
        {"name": "c", "status": "skipped", "note": "not checked out locally"},
    ])
    assert "Review the daily-plans, commit, and push." in text
    assert "/w/a/daily-plan.md" in text and "/w/b/daily-plan.md" in text
    assert "/w/c" not in text
    assert "Nothing was staged, committed, or pushed" in text


def test_next_steps_is_silent_when_nothing_was_written():
    assert rp.next_steps([{"name": "a", "status": "skipped", "note": "x"}]) == ""
