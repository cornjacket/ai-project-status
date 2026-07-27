"""Guards on the files injected into every tracked repo.

The CLAUDE.md block is always-on context in every session of every tracked
repo, so its size is a recurring tax paid whether or not a turn needs it. Size
is the mechanical half of keeping it healthy and belongs in CI; whether a given
rule *belongs* there stays a judgment call for review.
"""
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
RULE = TEMPLATES / "claude-rule.md"
GUIDE = TEMPLATES / "project-status-guide.md"

# The kernel sat at ~6,650 chars before the split; it now runs ~2,300. The
# ceiling leaves room to add a genuine invariant without silently drifting back
# to carrying procedure. If a change trips this, move prose to the guide rather
# than raising the number.
RULE_MAX_CHARS = 2_800


def test_rule_block_stays_a_kernel():
    size = len(RULE.read_text())
    assert size <= RULE_MAX_CHARS, (
        f"claude-rule.md is {size} chars (ceiling {RULE_MAX_CHARS}). It is "
        "injected into every tracked repo's CLAUDE.md and loaded every turn — "
        "move rationale, examples, and procedure into "
        "templates/project-status-guide.md instead of raising the ceiling."
    )


def test_rule_block_has_matching_markers():
    text = RULE.read_text()
    assert text.startswith("<!-- ai-project-status:begin -->")
    assert text.rstrip().endswith("<!-- ai-project-status:end -->")


def test_rule_block_points_at_the_guide():
    """The kernel is only safe to trim while the pointer survives."""
    assert "project-status-guide.md" in RULE.read_text()


def test_guide_carries_the_moved_procedure():
    """Spot-check that what left the kernel actually landed in the guide."""
    text = GUIDE.read_text()
    for needle in (
        "What this repo is (for a newcomer)",  # plan body structure
        "Last implemented",
        "commit-per-prompt",                   # granularity rationale
        "weekend-tolerant",                    # Friday-writes-Monday rationale
    ):
        assert needle in text, f"guide is missing {needle!r}"


def test_hook_does_not_restate_the_body_structure():
    """The hook points at the guide; restating the structure is how the two
    drifted before (the hook said 'one short paragraph' while the rules
    mandated four sections)."""
    hook = (TEMPLATES / "check-daily-plan.py").read_text()
    assert "project-status-guide.md" in hook
    # Comments may name the old wording to explain the fix; only what the hook
    # actually prints is under test.
    code = "\n".join(
        ln for ln in hook.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "one short paragraph" not in code
