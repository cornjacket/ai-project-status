You are polishing today's day section for a multi-repo status rollup. Each repo's subsection has already been drafted independently by separate per-repo summary calls; you are the only step that sees them all together.

Your job:
- Surface cross-repo themes ONLY when a real one exists (e.g., "both ai-foo and ai-bar shipped vector-store backends today"). When one exists, add a single `### Cross-repo` subsection at the END of the day section. Don't force a theme — if the repos are doing unrelated work, omit the cross-repo subsection entirely.
- Tighten prose. Cut filler. Combine redundant bullets within a single repo's section if any.
- Preserve the order of repos exactly as given in the drafts.
- Preserve inactivity one-liners exactly as given. Do not rewrite them, do not move them.
- Preserve all commit hashes exactly. Never invent or remove a hash.

Output the full day section, starting with `## {{TODAY}}` on its own line. Output ONLY the day section — no preamble, no closing remarks, no surrounding code fences.

DRAFTS:
---
{{DRAFTS}}
---
