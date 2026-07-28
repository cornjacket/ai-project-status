"""Unit tests for tools/check-pending.py.

All deterministic: real git repos in tmp dirs, no network and no LLM. The cases
that matter are the ones where a repo *looks* clean but isn't — an unpushed
branch, a branch with no upstream, and work parked in a second worktree.
"""
import importlib.util
import subprocess
from pathlib import Path

import pytest

from conftest import init_git_repo


def _load():
    path = Path(__file__).resolve().parent.parent / "tools" / "check-pending.py"
    spec = importlib.util.spec_from_file_location("check_pending", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cp = _load()


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True,
                          capture_output=True, text=True)


def _repo(root: Path, name: str, *, commit=True) -> Path:
    d = root / name
    init_git_repo(d)
    if commit:
        (d / "README.md").write_text("hi\n")
        _git(d, "add", "README.md")
        _git(d, "commit", "-m", "init")
    return d


def _with_origin(root: Path, name: str) -> Path:
    """A repo whose branch tracks a bare 'remote', already in sync."""
    bare = root / f"{name}.git"
    bare.mkdir(parents=True)
    _git(bare, "init", "--bare", "-b", "main")
    d = _repo(root, name)
    _git(d, "remote", "add", "origin", str(bare))
    _git(d, "push", "-u", "origin", "main")
    return d


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "workspace"
    w.mkdir()
    return w


# --- working-tree state ---------------------------------------------------

def test_clean_synced_repo_is_not_pending(ws):
    r = cp.inspect("foo", _with_origin(ws, "foo"))
    assert cp.summarize(r) == "clean"
    assert not cp.is_pending(r)


def test_modified_file_is_pending(ws):
    d = _with_origin(ws, "foo")
    (d / "README.md").write_text("edited\n")
    r = cp.inspect("foo", d)
    assert cp.is_pending(r)
    assert r["changes"] == [(" M", "README.md")]
    assert cp.summarize(r) == "1 changed"


def test_staged_and_untracked_are_counted_separately(ws):
    d = _with_origin(ws, "foo")
    (d / "README.md").write_text("edited\n")
    _git(d, "add", "README.md")
    (d / "scratch.txt").write_text("new\n")
    r = cp.inspect("foo", d)
    assert r["staged"] == 1 and r["untracked"] == 1
    assert cp.summarize(r) == "2 changed (1 staged, 1 untracked)"


# --- the states that look clean but aren't --------------------------------

def test_committed_but_unpushed_is_pending(ws):
    """The failure this tool exists for: `git status` calls this repo clean."""
    d = _with_origin(ws, "foo")
    (d / "README.md").write_text("more\n")
    _git(d, "add", "README.md")
    _git(d, "commit", "-m", "work")

    r = cp.inspect("foo", d)
    assert r["changes"] == []          # working tree really is clean...
    assert r["ahead"] == 1             # ...but the commit never left
    assert cp.is_pending(r)
    assert cp.summarize(r) == "1 unpushed commit"


def test_branch_with_no_upstream_is_reported_not_assumed_clean(ws):
    d = _repo(ws, "foo")  # no remote at all
    r = cp.inspect("foo", d)
    assert r["upstream_problem"] == "no upstream"
    assert cp.is_pending(r)
    assert "no upstream" in cp.summarize(r)


def test_unpushed_commits_and_edits_are_both_reported(ws):
    d = _with_origin(ws, "foo")
    (d / "README.md").write_text("more\n")
    _git(d, "add", "README.md")
    _git(d, "commit", "-m", "work")
    (d / "scratch.txt").write_text("new\n")

    assert cp.summarize(cp.inspect("foo", d)) == "1 changed (1 untracked), 1 unpushed commit"


# --- worktrees ------------------------------------------------------------

def test_expand_finds_a_worktree_parked_outside_the_workspace(ws, tmp_path):
    """`git worktree list` is the authority: a worktree can live anywhere, and
    directory-shape guessing would miss it entirely."""
    d = _with_origin(ws, "foo")
    outside = tmp_path / "elsewhere" / "hotfix"
    _git(d, "worktree", "add", "-b", "hotfix", str(outside))

    entries = cp.expand([("foo", d)], ws)
    paths = {Path(p).resolve() for _, p in entries}

    assert d.resolve() in paths
    assert outside.resolve() in paths
    # Outside the workspace, so it is named by its full path rather than faked
    # into a relative one.
    label = next(lbl for lbl, p in entries if Path(p).resolve() == outside.resolve())
    assert label == str(outside)


def test_work_in_a_second_worktree_is_reported(ws):
    d = _with_origin(ws, "foo")
    wt = ws / "foo-wt"
    _git(d, "worktree", "add", "-b", "feature", str(wt))
    (wt / "scratch.txt").write_text("uncommitted work\n")

    results = [cp.inspect(lbl, p) for lbl, p in cp.expand([("foo", d)], ws)]
    by_label = {r["label"]: r for r in results}

    assert not by_label["foo"]["changes"]           # primary is clean...
    assert by_label["foo-wt"]["untracked"] == 1     # ...the worktree is not
    assert cp.is_pending(by_label["foo-wt"])


def test_expand_dedupes_repeated_checkouts(ws):
    d = _with_origin(ws, "foo")
    entries = cp.expand([("foo", d), ("foo-again", d)], ws)
    assert len(entries) == 1


def test_expand_keeps_repos_that_are_not_checked_out(ws):
    assert cp.expand([("absent", None)], ws) == [("absent", None)]


def test_bare_repos_contribute_no_working_tree(ws):
    """A bare repo has nothing to be uncommitted in; listing it would be noise."""
    d = _with_origin(ws, "foo")
    trees = cp.worktrees_of(d)
    assert all((Path(t) / ".git").exists() for t in trees)
    assert not any(str(t).endswith(".git") for t in trees)


# --- discovery ------------------------------------------------------------

def test_discover_finds_top_level_and_nested_checkouts(ws):
    _repo(ws, "flat")
    container = ws / "container"
    _repo(container, "main")           # <container>/main, the worktree layout
    (ws / "not-a-repo").mkdir()

    found = dict(cp.discover_repos(ws))
    assert "flat" in found
    assert "container/main" in found
    assert "not-a-repo" not in found


def test_discover_honors_the_project_status_ignore_optout(ws):
    d = _repo(ws, "scratch")
    (d / cp.IGNORE_FILE).touch()
    assert "scratch" not in dict(cp.discover_repos(ws))


# --- reporting and exit code ----------------------------------------------

def test_dirty_only_hides_clean_repos(ws):
    _with_origin(ws, "clean")
    dirty = _with_origin(ws, "dirty")
    (dirty / "README.md").write_text("edited\n")

    results, source = cp.collect(ws, scan_all=True)
    text = cp.render(results, ws, source, dirty_only=True)

    assert "dirty" in text
    assert "\n! clean" not in text


def test_main_exits_nonzero_only_when_something_is_pending(ws, capsys):
    _with_origin(ws, "clean")
    assert cp.main(["--all", "--path", str(ws)]) == 0
    assert "everything committed and pushed" in capsys.readouterr().out

    (ws / "clean" / "README.md").write_text("edited\n")
    assert cp.main(["--all", "--path", str(ws)]) == 1


def test_main_rejects_a_missing_workspace(tmp_path, capsys):
    assert cp.main(["--path", str(tmp_path / "nope")]) == 2
