"""Shared pytest setup and fixtures."""
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))


def _git(args, cwd):
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-b", "main"], path)
    _git(["config", "user.email", "test@example.com"], path)
    _git(["config", "user.name", "Test"], path)
    _git(["config", "commit.gpgsign", "false"], path)


def commit_log(path: Path, line: str, msg: str | None = None) -> str:
    """Append a line to log.md and commit. Returns the commit SHA."""
    log = path / "log.md"
    existing = log.read_text() if log.exists() else ""
    log.write_text(existing + line + "\n")
    _git(["add", "log.md"], path)
    _git(["commit", "-m", msg or line], path)
    return _git(["rev-parse", "HEAD"], path).stdout.strip()


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Stand up a tmp project root with the standard layout, and patch the
    module-level paths in `_lib` so every helper reads/writes the tmp dir."""
    import _lib

    (tmp_path / "tracked").mkdir()
    (tmp_path / "summary.md").write_text(
        "# AI Project Status Summary\n\n"
        "Auto-maintained by ai-project-status. Newest activity at the top.\n\n"
        "<!-- new sections inserted below -->\n"
    )
    (tmp_path / "state.json").write_text("{}\n")
    (tmp_path / "repos.yml").write_text("repos: []\n")

    monkeypatch.setattr(_lib, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(_lib, "REPOS_YML", tmp_path / "repos.yml")
    monkeypatch.setattr(_lib, "STATE_JSON", tmp_path / "state.json")
    monkeypatch.setattr(_lib, "TRACKED_DIR", tmp_path / "tracked")
    monkeypatch.setattr(_lib, "SUMMARY_MD", tmp_path / "summary.md")
    return tmp_path
