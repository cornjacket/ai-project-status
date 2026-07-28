"""Unit tests for tools/gen-umbrella-claude.py."""
import importlib.util
from pathlib import Path


def _load():
    """The module name has a hyphen, so import via spec."""
    here = Path(__file__).resolve().parent.parent
    path = here / "tools" / "gen-umbrella-claude.py"
    spec = importlib.util.spec_from_file_location("gen_umbrella_claude", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gu = _load()

PLAN = (
    "# Daily plan — 2026-07-27\n\n"
    "**What this repo is (for a newcomer):** `ai-foo` builds widgets for the downstream factory pipeline every day.\n"
    "It also does other things.\n\n"
    "**Last implemented:** the widget.\n"
)


def _repo(umbrella: Path, name: str, plan: str | None = PLAN) -> None:
    d = umbrella / name
    d.mkdir(parents=True)
    if plan is not None:
        (d / "daily-plan.md").write_text(plan)


# --- purpose extraction ---------------------------------------------------

def test_extract_purpose_takes_first_sentence():
    assert gu.extract_purpose(PLAN) == "`ai-foo` builds widgets for the downstream factory pipeline every day."


def test_extract_purpose_pulls_second_sentence_when_first_is_terse():
    text = (
        "**What this repo is (for a newcomer):** `ai-foo` is a generator. "
        "It builds a widget factory from a template.\n"
    )
    assert gu.extract_purpose(text) == (
        "`ai-foo` is a generator. It builds a widget factory from a template."
    )


def test_extract_purpose_stops_before_overflowing_on_second_sentence():
    text = (
        "**What this repo is (for a newcomer):** "
        + "A sentence that is comfortably past the minimum length on its own. "
        + "x" * 200
        + "\n"
    )
    assert gu.extract_purpose(text) == (
        "A sentence that is comfortably past the minimum length on its own."
    )


def test_extract_purpose_folds_wrapped_line():
    text = (
        "**What this repo is (for a newcomer):** A generator that\n"
        "builds a personal vault\n"
    )
    assert gu.extract_purpose(text) == "A generator that builds a personal vault"


def test_extract_purpose_stops_at_next_field():
    text = (
        "**What this repo is (for a newcomer):** Widgets\n"
        "**Last implemented:** the widget.\n"
    )
    assert gu.extract_purpose(text) == "Widgets"


def test_extract_purpose_missing_field():
    assert gu.extract_purpose("# Daily plan — 2026-07-27\n\nStuff.\n") is None


def test_extract_purpose_ignores_template_placeholder():
    text = (
        "**What this repo is (for a newcomer):** "
        "(one or two sentences — replace this)\n"
    )
    assert gu.extract_purpose(text) is None


def test_extract_purpose_truncates_long_text():
    long = "word " * 200
    text = f"**What this repo is (for a newcomer):** {long}\n"
    out = gu.extract_purpose(text)
    assert len(out) <= gu.MAX_PURPOSE_CHARS + 1  # +1 for the ellipsis
    assert out.endswith("…")


# --- source precedence ----------------------------------------------------

def test_purpose_prefers_local_checkout_over_tracked(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    tracked = tmp_path / "tracked"
    monkeypatch.setattr(gu, "TRACKED_DIR", tracked)
    _repo(umbrella, "ai-foo")
    (tracked / "ai-foo").mkdir(parents=True)
    (tracked / "ai-foo" / "daily-plan.md").write_text(
        "**What this repo is (for a newcomer):** stale cached copy.\n"
    )
    assert gu.repo_purpose("ai-foo", umbrella) == "`ai-foo` builds widgets for the downstream factory pipeline every day."


def test_purpose_falls_back_to_tracked_cache(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    umbrella.mkdir()
    tracked = tmp_path / "tracked"
    monkeypatch.setattr(gu, "TRACKED_DIR", tracked)
    (tracked / "ai-foo").mkdir(parents=True)
    (tracked / "ai-foo" / "daily-plan.md").write_text(
        "**What this repo is (for a newcomer):** cached copy.\n"
    )
    assert gu.repo_purpose("ai-foo", umbrella) == "cached copy."


def test_purpose_none_when_no_plan_anywhere(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo", plan=None)
    assert gu.repo_purpose("ai-foo", umbrella) is None


# --- roster block ---------------------------------------------------------

def test_render_block_lists_repos_with_path_and_purpose(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo")
    block = gu.render_block([{"name": "ai-foo"}], umbrella)
    assert block.startswith(gu.BEGIN_MARKER)
    assert block.rstrip().endswith(gu.END_MARKER)
    assert "- **ai-foo** (`./ai-foo`) — `ai-foo` builds widgets for the downstream factory pipeline every day." in block


def test_render_block_flags_repo_not_checked_out(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    umbrella.mkdir()
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    block = gu.render_block([{"name": "ai-foo"}], umbrella)
    assert "not checked out locally" in block
    assert "_(no daily-plan.md yet)_" in block


def test_render_block_preserves_repos_yml_order(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    for name in ("ai-b", "ai-a"):
        _repo(umbrella, name)
    block = gu.render_block([{"name": "ai-b"}, {"name": "ai-a"}], umbrella)
    assert block.index("**ai-b**") < block.index("**ai-a**")


def test_render_block_ignores_untracked_siblings(tmp_path, monkeypatch):
    """Only repos.yml defines the roster — a sibling directory that isn't
    tracked is invisible to project-status and stays out of the block."""
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo")
    (umbrella / "scratch-repo").mkdir()
    block = gu.render_block([{"name": "ai-foo"}], umbrella)
    assert "scratch-repo" not in block


def test_render_block_handles_empty_roster(tmp_path):
    umbrella = tmp_path / "workspace"
    umbrella.mkdir()
    block = gu.render_block([], umbrella)
    assert "no enabled repos" in block


# --- splice / build -------------------------------------------------------

def test_splice_replaces_only_the_block():
    existing = (
        "# CLAUDE.md\n\nHand-written intro.\n\n"
        f"{gu.BEGIN_MARKER}\nold roster\n{gu.END_MARKER}\n\n"
        "Hand-written outro.\n"
    )
    out = gu.splice(existing, f"{gu.BEGIN_MARKER}\nnew roster\n{gu.END_MARKER}")
    assert "Hand-written intro." in out
    assert "Hand-written outro." in out
    assert "new roster" in out
    assert "old roster" not in out


def test_splice_is_idempotent():
    block = f"{gu.BEGIN_MARKER}\nroster\n{gu.END_MARKER}"
    once = gu.splice(f"# CLAUDE.md\n\nintro\n\n{block}\n", block)
    assert gu.splice(once, block) == once


def test_splice_appends_when_markers_absent():
    out = gu.splice(
        "# CLAUDE.md\n\nHand-written only.\n",
        f"{gu.BEGIN_MARKER}\nroster\n{gu.END_MARKER}",
    )
    assert "Hand-written only." in out
    assert gu.BEGIN_MARKER in out


def test_build_creates_file_from_template_when_missing(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo")
    out = gu.build(umbrella, repos=[{"name": "ai-foo"}])
    assert "read-only cross-repo dashboard" in out
    assert "**ai-foo**" in out
    assert "daily-plan-summary.md" in out


def test_build_preserves_human_content_on_regeneration(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo")
    (umbrella / "CLAUDE.md").write_text(gu.build(umbrella, repos=[{"name": "ai-foo"}]))
    (umbrella / "CLAUDE.md").write_text(
        (umbrella / "CLAUDE.md").read_text() + "\n## My own section\n\nKeep me.\n"
    )
    _repo(umbrella, "ai-bar")
    out = gu.build(umbrella, repos=[{"name": "ai-foo"}, {"name": "ai-bar"}])
    assert "Keep me." in out
    assert "**ai-bar**" in out


def test_main_refuses_to_write_project_status_itself(capsys):
    assert gu.main(["--path", str(gu.REPO_ROOT)]) == 1
    assert "refusing" in capsys.readouterr().err


def test_main_errors_on_missing_directory(tmp_path, capsys):
    assert gu.main(["--path", str(tmp_path / "nope")]) == 1
    assert "no such directory" in capsys.readouterr().err


def test_main_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo")
    monkeypatch.setattr(gu, "enabled_repos", lambda: [{"name": "ai-foo"}])
    assert gu.main(["--path", str(umbrella), "--dry-run"]) == 0
    assert not (umbrella / "CLAUDE.md").exists()
    assert "**ai-foo**" in capsys.readouterr().out


def test_main_writes_file(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _repo(umbrella, "ai-foo")
    monkeypatch.setattr(gu, "enabled_repos", lambda: [{"name": "ai-foo"}])
    assert gu.main(["--path", str(umbrella)]) == 0
    assert "**ai-foo**" in (umbrella / "CLAUDE.md").read_text()


# --- bare + worktree layouts ----------------------------------------------

def _worktree_repo(umbrella: Path, name: str, branch: str = "main",
                   plan: str | None = PLAN) -> None:
    """A container whose .git is a FILE and whose checkout is a subdirectory —
    the `git clone --bare` + `git worktree add` layout."""
    base = umbrella / name
    (base / ".bare").mkdir(parents=True)
    (base / ".git").write_text("gitdir: ./.bare\n")
    wt = base / branch
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: ../.bare/worktrees/{branch}\n")
    if plan is not None:
        (wt / "daily-plan.md").write_text(plan)


def test_local_checkout_normal_clone(tmp_path):
    umbrella = tmp_path / "workspace"
    _repo(umbrella, "ai-foo")
    (umbrella / "ai-foo" / ".git").mkdir()
    assert gu.local_checkout(umbrella, "ai-foo") == umbrella / "ai-foo"


def test_local_checkout_finds_the_worktree(tmp_path):
    umbrella = tmp_path / "workspace"
    _worktree_repo(umbrella, "ai-foo")
    assert gu.local_checkout(umbrella, "ai-foo") == umbrella / "ai-foo" / "main"


def test_local_checkout_prefers_the_tracked_branch(tmp_path):
    umbrella = tmp_path / "workspace"
    _worktree_repo(umbrella, "ai-foo", branch="develop")
    _worktree_repo_extra = umbrella / "ai-foo" / "feature-x"
    _worktree_repo_extra.mkdir()
    (_worktree_repo_extra / ".git").write_text("gitdir: ../.bare/worktrees/x\n")
    assert gu.local_checkout(umbrella, "ai-foo", "develop") == \
        umbrella / "ai-foo" / "develop"


def test_local_checkout_absent(tmp_path):
    umbrella = tmp_path / "workspace"
    umbrella.mkdir()
    assert gu.local_checkout(umbrella, "ai-foo") is None


def test_purpose_read_from_worktree_checkout(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _worktree_repo(umbrella, "ai-foo")
    assert gu.repo_purpose("ai-foo", umbrella) == \
        "`ai-foo` builds widgets for the downstream factory pipeline every day."


def test_roster_points_at_the_worktree_not_the_container(tmp_path, monkeypatch):
    umbrella = tmp_path / "workspace"
    monkeypatch.setattr(gu, "TRACKED_DIR", tmp_path / "tracked")
    _worktree_repo(umbrella, "ai-foo")
    block = gu.render_block([{"name": "ai-foo"}], umbrella)
    assert "`./ai-foo/main`" in block
    assert "not checked out locally" not in block
