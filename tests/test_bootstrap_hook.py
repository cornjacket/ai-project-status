"""Tests for hooks/check-repo-bootstrap.py, the user-level SessionStart hook.

Run as a subprocess with cwd set, because that is exactly how Claude Code
invokes it — the hook derives everything from the working directory.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import init_git_repo

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "check-repo-bootstrap.py"
MARKER = "<!-- ai-project-status:begin -->"


def run_hook(cwd: Path, workspace: Path):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={"PROJECT_STATUS_WORKSPACE": str(workspace), "PATH": "/usr/bin:/bin"},
    )


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_silent_outside_a_git_repo(tmp_path, workspace):
    loose = workspace / "not-a-repo"
    loose.mkdir()
    assert run_hook(loose, workspace).stdout == ""


def test_silent_outside_the_workspace(tmp_path, workspace):
    elsewhere = tmp_path / "elsewhere"
    init_git_repo(elsewhere)
    assert run_hook(elsewhere, workspace).stdout == ""


def test_nudges_an_unbootstrapped_repo_in_the_workspace(workspace):
    repo = workspace / "ai-new"
    init_git_repo(repo)
    out = run_hook(repo, workspace).stdout
    assert "not bootstrapped for project-status" in out
    assert "setup-new-repo.sh" in out


def test_nudge_offers_the_opt_out_not_just_the_fix(workspace):
    """Without the opt-out the user gets nagged every session in a repo they
    have already decided about, which is how a hook earns being ignored."""
    repo = workspace / "ai-new"
    init_git_repo(repo)
    out = run_hook(repo, workspace).stdout
    assert ".project-status-ignore" in out
    assert "Doing nothing is also fine" in out


def test_silent_when_the_marker_is_present(workspace):
    repo = workspace / "ai-tracked"
    init_git_repo(repo)
    (repo / "CLAUDE.md").write_text(f"# CLAUDE.md\n\n{MARKER}\nrules\n")
    assert run_hook(repo, workspace).stdout == ""


def test_nudges_when_claude_md_exists_without_the_marker(workspace):
    repo = workspace / "ai-partial"
    init_git_repo(repo)
    (repo / "CLAUDE.md").write_text("# CLAUDE.md\n\nhand-written only\n")
    assert "not bootstrapped" in run_hook(repo, workspace).stdout


def test_opt_out_file_silences_it(workspace):
    repo = workspace / "scratch"
    init_git_repo(repo)
    (repo / ".project-status-ignore").touch()
    assert run_hook(repo, workspace).stdout == ""


def test_silent_in_the_tracker_itself(workspace):
    repo = workspace / "project-status"
    init_git_repo(repo)
    (repo / "repos.yml").write_text("repos: []\n")
    assert run_hook(repo, workspace).stdout == ""


def test_silent_in_a_repo_named_differently_but_holding_repos_yml(workspace):
    """A renamed or worktree copy of the tracker is still the tracker."""
    repo = workspace / "status-fork"
    init_git_repo(repo)
    (repo / "repos.yml").write_text("repos: []\n")
    assert run_hook(repo, workspace).stdout == ""


def test_always_exits_zero_so_it_never_blocks_a_session(workspace):
    repo = workspace / "ai-new"
    init_git_repo(repo)
    assert run_hook(repo, workspace).returncode == 0
