# AI Project Status Summary

Auto-maintained by ai-project-status. Newest activity at the top.

<!-- new sections inserted below -->

## 2026-07-09

### second-brain-test

- Auto-linking (task #8) landed: `d086620` writes a `related_auto:` block into frontmatter with suggested neighbor links, gated to never overwrite a hand-written `related:` field or an in-body link — built on the read-only calibration tool from `6ad86cc` that reports neighbor distances for tuning the similarity cutoff.
- Two embedding fixes underpin it: `9e827a5` embeds only body text (stripping frontmatter) so auto-links don't feed back into and skew a note's own vector; `44ea6f6` adds task-specific prefixes so a search query and a stored note no longer embed identically.
- `2bc1f27` adds a content fingerprint so notes re-embed only when their text changes, not on metadata-only edits.
- `578f20a`/`babeb00` are supporting refactors: decoupling auto-link logic from the vector database for standalone testing, and extracting a shared marked-region helper reused by the upcoming README feature.
- Range `e4e78be0..b25ac58e`, ~2,000 lines across 12 files (incl. regenerated fixtures). Next up: prototype README status markers (#9), then seed a larger topic-diverse test vault (#15) to stress-test linking thresholds.

### second-brain-devkit

- Built a reusable 100-note, 10-topic test corpus with install/remove tooling (`119f7d6`, `9de9a8c`), then rewrote all notes longer and more topic-focused (`a64496d`), lifting nearest-neighbor clustering accuracy from 69%→79% (top match) and 55%→75% (top 5).
- Advanced auto-linking (similarity-based `related_auto:` frontmatter links) end-to-end: substance-only embedding (`caba3a3`), direction-aware search/clustering prefixes (`a336184`, `638b5d3`), a calibration tool for the similarity cutoff (`8042520`), the write path itself (`e0e218f`), and a CI check confirming Obsidian-graphable formatting (`e82f692`).
- Shipped a perf fix skipping re-embedding of unchanged notes (`aa4e692`) and extracted a shared "marked block" helper reused by both auto-linking and the README-update feature (`ac0b305`).
- Queued: closing out README auto-update (#9), renaming to `create-second-brain` (#11), a retrieval-enhancement ablation/benchmarking effort (#12/#13), a public getting-started writeup (#14), and the diverse test corpus (#15) needed before final threshold tuning (`0ed572a`, `d12d36f`, `d4b8a0f`, `8b3d1ab`).
- Tightened process: commit messages must now read clearly to outside reviewers, and the agent commits autonomously without pushing unless asked (`faff004`, `3af3f76`, `ca8aac2`).

### No updates
- customer-req-responder (for 27 days)

### Cross-repo

- Both repos advanced the same auto-linking feature in lockstep today — substance-only embedding, direction-aware prefixes, similarity calibration tooling, skip-unchanged-notes optimization, and a shared marked-block helper. `second-brain-test` landed it as a consumer (`d086620`), while `second-brain-devkit` built the generalized version plus the corpus to validate it (`e0e218f`, `a64496d`), with both queuing the README-status-marker feature and a larger diverse test vault (#15) next.


## 2026-07-08

### second-brain-test
- Daily plan updated for 2026-07-08 (`e4e78be`), resuming this repo as the prototyping ground for the devkit after a period of inactivity; sync-hook/FTS5 work is deprioritized in favor of this.
- Plan: prototype a splice helper for task #10 (programmatically insert/update managed text blocks) and refactor `install_skill.py`'s `--nudge` flag to use it, verified via a round-trip test against a local Ollama model.
- Also kicks off task #8: auto-link related notes by embedding canonical body text into `related_auto` frontmatter, tracking a `content_hash` to detect when re-embedding is needed.
- Only `daily-plan.md` changed (19 insertions/20 deletions) — planning ahead of implementation, no code yet.

### second-brain-devkit
- Shipped task #6: brain creation can now connect to a git remote on the spot via `--remote`, with safety checks (git identity configured, remote reachable, remote empty) run upfront so a failed setup never leaves a half-built brain; a new hermetic test verifies the full connect→push→clone-as-a-second-machine flow (`3d6cf08`).
- Renamed `new_brain.py` to the clearer `create_second_brain.py` throughout code and docs, and added an installation checklist so a freshly created brain is verified runnable, not just generated (`b41dbd6`).
- Queued three backlog design docs: task #8, vector-similarity auto-linking between notes without creating a feedback loop where auto-links get folded back into re-indexing (`d196a4d`); task #9, letting the toolkit own a marked region of a brain's README so it can push updates without overwriting user edits (`a4e36d7`); and task #10, a shared text-splicing helper to unify #8, #9, and an existing similar feature (`5ac2f03`).
- Tomorrow's plan: build the task #10 helper first, then start task #8 auto-linking (`1157288`).
- Touched 16 files (~1,023 insertions), including two new design docs and a ~210-line test script for the remote-connection feature (`6b321537..11572886`).

### Cross-repo
- second-brain-devkit spent today designing tasks #8 (embedding-based auto-linking) and #10 (shared splice helper) and queued both for tomorrow, while second-brain-test picked up the same two tasks as its prototyping plan the same day — the two repos are converging on identical feature work in lockstep.

### No updates
- customer-req-responder (for 26 days)


## 2026-07-07

### second-brain-test

- No functional changes — still a deliberately idle "diff oracle" baseline, untouched since July 4th since companion devkit work hasn't yet produced anything to prototype here (`8f5b23e`).
- Daily plan refreshed to flag two prototype candidates: a post-merge sync hook (big-brain Approach A, pending task #6) and hybrid FTS5 search (task #3).
- Still slated for eventual retirement once those prototypes are validated elsewhere.

### second-brain-devkit

- Added two CI safety nets (`9e09371`, `cfd4d5b`): syntax-checking every generated script, and spinning up the generated MCP server to verify real runtime behavior — closing the gap that let a prior Claude Desktop bug ship untested.
- Shipped `tools/update_brain.py` (`b7e08c2`), a non-destructive upgrade path that refreshes a brain's tooling scaffold in place while preserving notes and git history, replacing the old delete-and-regenerate workaround. Dry-run by default; `--apply` commits a revertable snapshot.
- Designed a git-remote-based sync approach for sharing a brain across machines (`ea3f54e`, `8d6c996`, `f49ef8b`): pull/push over git rather than a hosted database, explicitly excluding embeddings from commits since they aren't byte-reproducible across machines.
- Planned the next build task — `new_brain` creating a brain wired to a remote repo from the start, auto-sync on by default, with a preflight check and CI-testability without real credentials (`ab1953b`, `1381e8c`, `7f39f95`).
- Added a source map and Claude Desktop setup walkthrough (`e8fecab`) as a single onboarding reference from fresh brain to working Desktop integration.
- Queued a PDF-ingestion backlog item, flagging that PDFs need chunked, multi-embedding handling — breaking the current one-note-per-embedding model (`6b32153`). Range `b2a029e2..6b321537`, docs-heavy, 12 files (~984 lines added).

### No updates
- customer-req-responder (for 25 days)


## 2026-07-06

### No updates
- second-brain-test (for 1 days)
- second-brain-devkit (for 1 days)
- customer-req-responder (for 24 days)


## 2026-07-05

### second-brain-test

- Made cache rebuilds concurrency-safe: `hydrate_cache.py` now rebuilds the search cache in-place inside a single transaction instead of delete-and-recreate, so readers never see a missing/empty cache mid-rebuild and failed rebuilds roll back cleanly (5604fb4).
- Added a read-only MCP server (`scripts/mcp_server.py`, 103 lines) exposing search and note-retrieval over the vault, reusing the existing CLI/skill's search logic rather than duplicating it (4867eec).
- Found and fixed a Claude Desktop compatibility bug: an auto-generated schema field its older MCP client didn't support was hiding the tools; disabling that field fixed it, verified end-to-end after restart (d9d4260).
- Documented MCP setup in depth — full Desktop install/config walkthrough with troubleshooting, plus a standalone verification recipe that confirms the server works without opening Desktop (ff7fd84, e70fbd4; README +~125 lines).
- Scoped (not yet built) a hybrid search upgrade: fusing today's vector-only search with keyword search (FTS5) to catch exact-term matches pure semantic search misses (e70fbd4).
- Plan going forward: hold steady as the reference implementation while devkit builds CI coverage and an upgrade tool; prototype hybrid search here next, on demand (2c64264, range 276f3dd6..2c642643).

### second-brain-devkit

- Shipped MCP server v1 across every generated brain (4e5bdc0..420a6cb): first landed the same concurrency prerequisite as second-brain-test (in-place cache rebuild, avoiding a race with the server's open connection), then generated the read-only MCP server into each brain, closing the last open design question.
- Fixed the same Claude Desktop compatibility bug (66a6664) — a structured-output schema field broke Desktop integration — and in the process found that CI only byte-diffs the generated server script without ever running it, so a broken server could still pass.
- Scoped the CI fix in two planning commits (4055af5, 6abca08): add a hermetic syntax-check gate plus an opt-in test that spawns and exercises the server, and a new task for a non-destructive "upgrade an existing brain" tool.
- Chased a reported search-quality bug to a false alarm (Desktop hallucinated a bad result; the tool was fine), but used the investigation to scope hybrid keyword+vector search via Reciprocal Rank Fusion, designed in depth in a new architecture doc (6792458, b3c16c5; +171 lines).
- Rewrote tomorrow's plan (b2a029e) to prioritize CI hardening for the MCP server before starting the brain-upgrade tool, since both the server and the search-quality design landed ahead of schedule over the weekend.

### Cross-repo

- second-brain-test and second-brain-devkit converged on the same day: both shipped MCP server v1 behind the identical concurrency fix (in-place cache rebuild — 5604fb4 / 4e5bdc0..420a6cb), both hit and fixed the same Claude Desktop schema-compatibility bug (d9d4260 / 66a6664), and both are now scoping the same hybrid keyword+vector (RRF) search upgrade as their next feature (e70fbd4 / 6792458, b3c16c5) — devkit is templating what test is prototyping.

### No updates
- customer-req-responder (for 23 days)


## 2026-07-04

### second-brain-test

- Added `scripts/doctor.py`, a health-check command verifying the chain from notes on disk to the search database, catching drift (missing/stale/wrong-format cache entries) with a `--repair` flag to auto-fix (c3f15da).
- Hardened SQLite for concurrent access: switched to WAL mode with a 5-second retry window so readers (search) and writers (cache updates) no longer collide (0520c0f).
- `install_skill.py` gained an opt-in "nudge" install mode that adds a reflexive reminder to consult this brain into global Claude/Gemini config, plus a matching `--uninstall`, round-trip tested against a scratch home directory (b73aaca).
- README now documents enabling semantic search via Ollama and using `doctor.py` as a health check, verified end-to-end against a live Ollama server (c08be09).
- Plan: continue as the hand-built prototyping/correctness reference for `second-brain-devkit`, which will vendor back the next hydrate/cache layer and a first MCP server (276f3dd).
- Range `0520c0f..276f3dd6`: 5 files, ~580 lines added, concentrated in `doctor.py` (new) and `install_skill.py`.

### second-brain-devkit

- Shipped `doctor.py` into every generated brain as a live-tested (not just prototyped) setup/consistency check (`e180069..9793ed5`).
- Enabled SQLite WAL mode plus a busy-timeout in generated brains so readers and background cache writes no longer collide (`ba4f3ba`).
- Added the reflexive "consult before designing" install trigger with `--uninstall`, and Ollama setup/readiness docs to the generated README — 14 files, ~1,480 lines added, mostly regenerated template/golden fixtures (`7178c57..9793ed5`).
- Scoped (not yet built) an MCP server for AI clients like Claude Desktop that can't run local Python scripts; decided it must run over stdio, not the web, and needs a safe "rebuild without deleting the live database" approach first since the server holds a long-running connection (`4eb17e8`, `c0888eb`).
- Decided the devkit will never auto-install dependencies (detect-and-instruct instead), and flagged a gap: no supported way to upgrade an existing populated brain in place, only regenerate from scratch — fix now planned (`46424ac`).
- Plan: build the safer in-place rebuild first, then a first MCP server version (`62c8bb4`).

### No updates
- customer-req-responder (for 22 days)

### Cross-repo

Both `second-brain-test` and `second-brain-devkit` landed the same trio of features today — a `doctor.py` health check, SQLite WAL mode for concurrent reader/writer access, and a reflexive install-nudge with `--uninstall` — with `second-brain-test` prototyping and `second-brain-devkit` vendoring the hardened versions into its templates. Both also converged on scoping an MCP server as the next major piece of work.


## 2026-07-03

### second-brain-test

- Replaced full-rebuild search indexing with incremental updates — `--upsert`/`--delete` for single notes and `--from-commit` for commit-driven updates, wired into a new post-commit hook so notes become searchable immediately after `git commit` (`20eb3ef`, `ccce176`).
- Moved the embedding backend to a per-project setting in `config/embedder.toml`: this golden reference copy pins the deterministic test backend, while generated brains default to Ollama, with an env var override still available (`04a9d31`, `84cbffb`).
- Added a "second-brain" skill (lightweight shell interface, not a persistent server) letting other AI coding agents query this knowledge base for existing conventions, with install docs (`c9b8838`, `40fc98f`).
- Added `scripts/embed_vault.py` for one-shot bulk re-embedding (first-time setup or backend switches), an annotated note template, and a README tip on phrasing notes for better retrieval (`135bcfb`, `38cc6e8`, `71e2536`).
- Daily plan (2026-07-02) freezes this repo as a stable reference copy — only reactive fixes expected — while active development moves to `second-brain-devkit` (`3df0261`).

### second-brain-devkit

- Closed the "G1" milestone: `generate()` now produces a personal knowledge-base repo from a template, validated with a byte-exact structural diff against the reference copy (33/33 files matching) (`f748894..04a0177`).
- Shipped production-mode generation — `new_brain.py` now creates a real, user-owned git repo rather than a throwaway test copy (`91cddb4`).
- Made tests self-sufficient by vendoring the ~42-file golden brain directly into the repo and adding a GitHub Actions CI workflow, removing the dependency on an external repo (`f23c9ab..5018f9f`).
- Verified real-world search quality with Ollama and fixed a bug where newly generated brains returned garbage results unless a user manually set an env var — search now works out of the box (`1e388f0`, `b036221`).
- Rolled the AI skill, incremental index updates, auto-sync-on-commit, and a guided note-taking template into every newly generated brain (`06903b7`, `0503449`, `14c6cd1`, `c0f8856`, `87261ab`, `bec1a0c`).
- Found a real data-consistency bug (note on disk but missing from the index), setting tomorrow's plan: build a "doctor" tool to check/repair vault-database consistency (`1f9c8c6`).

### No updates
- customer-req-responder (for 21 days)

### Cross-repo

`second-brain-test` and `second-brain-devkit` converged on the same feature set today — incremental search-index updates, auto-sync-on-commit, and the AI query skill — landing in the golden reference copy and then getting baked into every brain the generator produces.


## 2026-07-02

### second-brain-test

- Core build is now feature-complete through Milestone 2 (M2) and Task 0004; this repo's role shifts from active development to serving as the stable "golden" reference/oracle that a new `second-brain-devkit` repo generates from and diffs against (`97a94bf`).
- Added `scripts/register.py`, an idempotent block-injector for other projects' `CLAUDE.md` that points their AI at this brain for saving/searching durable lessons — verified byte-identical on repeat runs and end-to-end (a note gets embedded, hydrated, and surfaces as the top search result) (`6a8b2ec`).
- Reworked embedding-vector handling: real-vault vectors dropped from git (regenerable, model-specific), a fixed set of test vectors moved to `tests/fixtures/vault/` for byte-reproducible regression testing, plus a new `self_test.py` structural check and a two-tier testing writeup (`1926342`).
- `SPEC.md` churned between repos — removed here in favor of a devkit copy (`f675fe3`), then restored since this repo remains the active build/reference target until full retirement later (`e934dcb`).
- Rewrote `README.md` as a task-oriented operating guide rather than a design document (`9ed9356`).
- Net: 25 files touched, ~3,185 lines of committed vector data removed, ~2,058 added — mostly documentation and test-fixture rework (`0da0d766..97a94bf8`).

### second-brain-devkit

- Completed the templatizing step of milestone G1: built a `template/` tree (28 files) by copying the golden reference repo byte-for-byte, auto-scrubbing 4 files of internal tracking references, and verifying clean via an automated guard (`2f6e7f6`, `ec40130`).
- Added `emit-manifest.toml` as the single source of truth classifying all 42 golden-repo files (copy as-is / clean before copying / generate at build time / don't ship), now driving the generator, diff-checker, and reference guard (`4ce520c`, `cd212e3`).
- Locked in an automated scanner enforcing that no file shipped to end users can mention this internal tracking system (`3012492`).
- Same `SPEC.md` location churn as upstream: briefly duplicated here, then reverted — spec now lives only in the golden reference repo and is never shipped to generated brains (`dab1163`, `cd212e3`, `d3b3a41`).
- Documented two generation modes sharing the same build logic: throwaway validation (build → compare to golden → discard) and production (build → user's own repo, kept permanently) (`4232858`).
- Next up: implement `generate()`, a sandbox runner to exercise it, and a structural diff check against the golden repo (`95204d0`).

### Cross-repo

- `second-brain-test` and `second-brain-devkit` are converging into one system: the former is settling into a frozen "golden" reference while the latter builds the generator and diff-checker that treats it as ground truth. Both repos independently churned on where `SPEC.md` should live today and landed on the same resolution — spec stays only in `second-brain-test`, never shipped to generated brains (`f675fe3`/`e934dcb` vs `dab1163`/`cd212e3`/`d3b3a41`).

### No updates
- customer-req-responder (for 20 days)


## 2026-07-01

### second-brain-devkit
- Planning-only update: `daily-plan.md` rewritten for 2026-07-01 now that second-brain-test's embed→hydrate→search pipeline is complete, unblocking work that had been on hold (b063c6c).
- Focus shifts from documentation to designing "G1" (template-generation strategy) against the now-stable brain reference output, plus an early validation approach ("G2") — a diff-against-golden-output check using a deterministic test embedder — while deferring anything dependent on the brain's still-unfinished semantic-search features.

### second-brain-test
- Finished layout restructuring (Task 0001, `59c9d67`): notes now live under a single Obsidian-openable `vault/` folder, with generated search-index files kept in `data/`; this activates an automatic commit-time embedding hook.
- Verified the full note-search pipeline end-to-end for the first time (`267084f`) — four sample notes embedded, loaded, and returning ranked results, proving the plumbing works, though the placeholder embedding model means result quality isn't real yet (needs a follow-up Ollama integration).
- Added a repeatable test harness (Task 0003, `1a3cddd`): a `seeds/` baseline plus `scripts/seed_vault.py` enables wipe→reseed→search cycles, guardrailed to only ever touch note files.
- Added a non-blocking safety net (Task 0002, `31056e0`) warning on commits when a note exceeds 300 lines, verified across editors including Obsidian.
- ~32 files changed, ~3,800 lines added (`dd9be808..0da0d766`), mostly generated embedding sidecars and task/plan docs; tomorrow's plan (`0da0d76`) pivots to Milestone 2 — registering this pipeline into other repos and adding an ingestion smoke test.

### No updates
- ai-builder (for 19 days)
- gsd-walkthru (for 19 days)
- customer-req-responder (for 19 days)

### Cross-repo
- second-brain-test's completed embed→hydrate→search pipeline (`267084f`, `59c9d67`) directly unblocked second-brain-devkit's planning (`b063c6c`), which now designs its template-generation strategy against that stable output.


## 2026-06-30

### second-brain-devkit

- Fresh repo bootstrapped from scratch: 11 files, 653 lines added across specs, docs, tooling config, and hooks (`5578387..cc0c174`).
- `README.md` (`c8d6cdc`) documents the core "write for humans, index for machines" philosophy — the embed→hydrate→search pipeline, sidecar schema, and dual human/AI value proposition.
- Spec and planning docs reorganized to eliminate drift (`cc0c174`): `SPEC.md` owns system-level design (three-repo workflow: golden→devkit→mothball, validation loop, non-goals); `PLAN.md` tracks generator milestones (G1–G3) gated on brain validation; `open-questions.md` records interim decisions.
- Dev scaffolding wired up: Gemini CLI support, open-questions tracking, and ai-project-status integration (daily-plan + SessionStart hook) in `aba47ab`/`dd96ede`.

### second-brain-test

- New repo bootstrapped from scratch (`8f111c0..dd9be80`): 21 files, ~920 lines — a full semantic-search pipeline including an embedder, SQLite-backed vector store, git pre-commit hook that embeds staged files, cache hydration script, and vault search interface.
- Initial content follows the PARA method (Projects, Areas, Resources, Archive) with seed markdown notes; `SPEC.md` and `PLAN.md` lay out the longer-term agent-memory vision.
- Tracking infrastructure wired in (`d24e611`): daily-plan, git-automation commit-message discipline, and the SessionStart hook.
- Today's focus (`dd9be80`): M1 milestone — activating the embed hook and symlink, then verifying the full embed→hydrate→search flow end-to-end. Registering/ingesting external content (M2) is a stretch goal.

### Cross-repo

Both `second-brain-devkit` and `second-brain-test` were bootstrapped today as complementary halves of the same system: `devkit` supplies the generator tooling and spec (three-repo workflow, sidecar schema), while `second-brain-test` is the first live brain being built against it — already running the embed→hydrate→search pipeline the devkit is designed to produce.

### No updates
- ai-builder (for 18 days)
- gsd-walkthru (for 18 days)
- customer-req-responder (for 18 days)


## 2026-06-29

### No updates
- ai-builder (for 17 days)
- gsd-walkthru (for 17 days)
- customer-req-responder (for 17 days)


## 2026-06-28

### No updates
- ai-builder (for 16 days)
- gsd-walkthru (for 16 days)
- customer-req-responder (for 16 days)


## 2026-06-27

### No updates
- ai-builder (for 15 days)
- gsd-walkthru (for 15 days)
- customer-req-responder (for 15 days)


## 2026-06-26

### No updates
- ai-builder (for 14 days)
- gsd-walkthru (for 14 days)
- customer-req-responder (for 14 days)


## 2026-06-25

### No updates
- ai-builder (for 13 days)
- gsd-walkthru (for 13 days)
- customer-req-responder (for 13 days)


## 2026-06-24

### No updates
- ai-builder (for 12 days)
- gsd-walkthru (for 12 days)
- customer-req-responder (for 12 days)


## 2026-06-23

### No updates
- ai-builder (for 11 days)
- gsd-walkthru (for 11 days)
- customer-req-responder (for 11 days)


## 2026-06-22

### No updates
- ai-builder (for 10 days)
- gsd-walkthru (for 10 days)
- customer-req-responder (for 10 days)


## 2026-06-21

### No updates
- ai-builder (for 9 days)
- gsd-walkthru (for 9 days)
- customer-req-responder (for 9 days)


## 2026-06-20

### No updates
- ai-builder (for 8 days)
- gsd-walkthru (for 8 days)
- customer-req-responder (for 8 days)


## 2026-06-19

### No updates
- ai-builder (for 7 days)
- gsd-walkthru (for 7 days)
- customer-req-responder (for 7 days)


## 2026-06-18

### No updates
- ai-builder (for 6 days)
- gsd-walkthru (for 6 days)
- customer-req-responder (for 6 days)


## 2026-06-17

### No updates
- ai-builder (for 5 days)
- gsd-walkthru (for 5 days)
- customer-req-responder (for 5 days)


## 2026-06-16

### No updates
- ai-builder (for 4 days)
- gsd-walkthru (for 4 days)
- customer-req-responder (for 4 days)


## 2026-06-15

### No updates
- ai-builder (for 3 days)
- gsd-walkthru (for 3 days)
- customer-req-responder (for 3 days)


## 2026-06-14

### No updates
- ai-builder (for 2 days)
- gsd-walkthru (for 2 days)
- customer-req-responder (for 2 days)


## 2026-06-13

### No updates
- ai-builder (for 1 days)
- gsd-walkthru (for 1 days)
- customer-req-responder (for 1 days)


## 2026-06-12

### ai-builder

- Bootstrapped into the cross-repo status tracking system (`3f34758`): added `daily-plan.md`, commit-message discipline rule in `CLAUDE.md`, and the `SessionStart` hook that enforces daily planning on session open.

### gsd-walkthru

- Bootstrapped into the cross-repo status tracking system (`f1efd3c`): added `daily-plan.md`, commit-message discipline rule in `CLAUDE.md`, and the `SessionStart` hook.

### customer-req-responder

- Onboarded into the cross-repo status tracking system (`c73a7fd`): added `daily-plan.md`, commit-message discipline rule in `CLAUDE.md`, and the `SessionStart` hook.

### Cross-repo

- All three repos received identical tracking scaffolding today: `daily-plan.md`, git-automation commit-message discipline in `CLAUDE.md`, and the `SessionStart` hook — the triad required for each repo's activity to flow into this rollup.


## 2026-06-11

### No updates
- ai-builder (for 7 days)
- gsd-walkthru (for 7 days)
- customer-req-responder (for 7 days)


## 2026-06-10

### No updates
- ai-builder (for 6 days)
- gsd-walkthru (for 6 days)
- customer-req-responder (for 6 days)


## 2026-06-09

### No updates
- ai-builder (for 5 days)
- gsd-walkthru (for 5 days)
- customer-req-responder (for 5 days)


## 2026-06-08

### No updates
- ai-builder (for 4 days)
- gsd-walkthru (for 4 days)
- customer-req-responder (for 4 days)


## 2026-06-07

### No updates
- ai-builder (for 3 days)
- gsd-walkthru (for 3 days)
- customer-req-responder (for 3 days)


## 2026-06-06

### No updates
- ai-builder (for 2 days)
- gsd-walkthru (for 2 days)
- customer-req-responder (for 2 days)


## 2026-06-05

### No updates
- ai-builder (for 1 days)
- gsd-walkthru (for 1 days)
- customer-req-responder (for 1 days)


## 2026-06-04

### ai-builder

- Retired the hand-maintained `log.md` work-log subsystem in favor of structured git commit messages as the single source of truth (`6101dd4..a53a002`). The old tooling — shell scripts, markdown templates, and associated `CLAUDE.md` instructions — was removed (8 files, net −354 lines), with per-task context now carried directly in commit bodies via `[Context]`/`[Impact]` annotations.

### gsd-walkthru

- **v1.0 milestone complete** (`1e40ea91..c0f543d1`): all 7 phases done, 139/139 tests passing across 16 files.
- The README was rebuilt from scratch (`0facf4f`): installation instructions, three self-contained per-provider quickstarts (Stripe, GitHub, Shopify), a config reference table, and a security notes section with a replay-protection comparison. Version bumped to 1.0.0 in `package.json` and the exported `VERSION` constant (`9806796`).
- A standalone example app landed under `examples/example-app/` (`654bcad`, `3f10758`): three independent mock webhook senders using `crypto.createHmac` directly — intentionally bypassing the library's own signing helper so HMAC bugs can't be masked. `npm start` fires all three in parallel.
- Closing docs: `ARCHITECTURE.md` for contributors (`639c472`), a v1.0 milestone summary at `.planning/reports/MILESTONE_SUMMARY-v1.0.md` (`1e56789`), and a post-mortem queued in `daily-plan.md` (`c0f543d`). Repo signals it should be archived as complete.

### customer-req-responder

- Migrated commit telemetry from `log.md` to structured git-native commit messages (`66f65fc`): `CLAUDE.md` now enforces the `domain(scope) title` + `[Context]/[Impact]` schema so the upstream tracker can reconstruct activity directly from git history. Net −16 lines across the two affected files.

### Cross-repo

Both **ai-builder** and **customer-req-responder** completed the same migration today: retiring hand-maintained `log.md` work logs in favor of structured git commit messages. This brings both repos onto the telemetry discipline this tracker consumes.


## 2026-06-03

### gsd-walkthru

- Phase 6 (webhook-signature verification library) was formally closed out with a security audit (`2f56a28`): a 17-threat STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) register was built from prior threat models, an automated auditor verified 16/17 mitigations against code, and the one remaining open item was a stale documentation row — resolved with a doc-only edit. `SECURITY.md` written with zero open threats.
- Phase 7 (Documentation & Example App, the final v1.0 phase) was scoped via a design discussion (`d95ec21`, `7971bf6`): the existing README will be rebuilt into canonical OSS shape (install → quickstart → config → security), and the currently-empty `examples/` directory will become a self-contained demo that boots a server, fires three cryptographically-signed mock webhook requests, and exits cleanly. A `package.json` version mismatch (0.0.1 vs v1.0) was flagged for the planning step.
- 8 files, ~400 lines added across the planning tree, capturing the STRIDE register, Phase 7 design decisions, and an updated daily plan targeting Phase 7 execution.

### No updates
- ai-builder (for 27 days)
- customer-req-responder (for 4 days)


## 2026-06-02

### No updates
- ai-builder (for 26 days)
- gsd-walkthru (for 3 days)
- customer-req-responder (for 3 days)


## 2026-06-01

### No updates
- ai-builder (for 25 days)
- gsd-walkthru (for 2 days)
- customer-req-responder (for 2 days)


## 2026-05-31

### No updates
- ai-builder (for 24 days)
- gsd-walkthru (for 1 days)
- customer-req-responder (for 1 days)


Looking at the two drafts: gsd-walkthru is closing out a webhook validation library's test suite; customer-req-responder is resuming a planning phase with a framework switch. No genuine cross-repo theme — the TDD mentions are incidental and unrelated in substance. Omitting the `### Cross-repo` subsection.

## 2026-05-30

### gsd-walkthru

- Phase 6 (integration tests, coverage gate, negative-case audit) closed across 33 files, 4800+ insertions (`4b6e7a99..21d10022`). The project is now 6 of 7 phases complete for v1.0.
- Added a per-file >90% V8 branch/line/function/statement coverage gate via `@vitest/coverage-v8`, scoped to Node 22 × Express 5.x in CI — then fixed a silent misconfiguration where vitest 4.x ignored thresholds placed at the config root instead of inside the `test:` block (`a7acdc1`).
- Built three Supertest integration test files (Stripe, GitHub, Shopify) covering both body-parser wiring modes; suite grew from 110 → 139 tests across 16 files.
- Resolved all 8 advisory carry-overs from phases 4–5: tightened the Stripe `v1=` header parser to reject array-shaped headers and non-numeric timestamp fields, added loud-fail guards for invalid tolerance values at factory call time, and made body-leakage assertions non-vacuous (`a94558d`).
- A post-merge `tsc` type error (not caught by vitest) required making `toleranceSeconds` optional on the Stripe validator to preserve the `Provider` interface contract — a concrete reminder that test-pass ≠ type-soundness (`41c8fa8`).
- Seeded `07-SECURITY-NOTES-SEED.md` flagging a test-oracle gap: hand-rolled `makeSignature` helpers share authorship with the validator, so they prove wiring correctness but not spec conformance. Prescribed fix: capture ground-truth fixtures from Stripe CLI, GitHub redeliver, and Shopify sandbox (`1dfff46`).

### customer-req-responder

- After a long gap since initial brainstorming, the project resumed with a framework decision: eight frameworks (GSD, Superpowers, RooFlow, Claude Skills, and others) were evaluated via parallel research agents, and the project switched to Superpowers — chosen for TDD alignment and its value as a single, non-stacked framework (`d4c3406`).
- Sketched a blueprint for a deferred LLM evaluation skill in `eval-skill-sketch.md` (132 lines): directory shape, judge prompt design, fixture format, and the split between reusable and project-specific logic — permanent home designated as a new `ai-skills` repo, symlinked into `~/.claude/skills/` (`e98779e`).
- Open questions around eval-gap coverage and TDD non-determinism captured in `open-questions.md` to seed the upcoming design/spec session; 5 files touched total (`bce68578..04d4285e`).

### No updates
- ai-builder (for 23 days)


## 2026-05-29

### No updates
- ai-builder (for 22 days)
- gsd-walkthru (for 20 days)
- customer-req-responder (for 20 days)


## 2026-05-28

### No updates
- ai-builder (for 21 days)
- gsd-walkthru (for 19 days)
- customer-req-responder (for 19 days)


## 2026-05-27

### No updates
- ai-builder (for 20 days)
- gsd-walkthru (for 18 days)
- customer-req-responder (for 18 days)


## 2026-05-25

### No updates
- ai-builder (for 18 days)
- gsd-walkthru (for 16 days)
- customer-req-responder (for 16 days)


## 2026-05-24

### No updates
- ai-builder (for 17 days)
- gsd-walkthru (for 15 days)
- customer-req-responder (for 15 days)


## 2026-05-23

### No updates
- ai-builder (for 16 days)
- gsd-walkthru (for 14 days)
- customer-req-responder (for 14 days)


## 2026-05-22

### No updates
- ai-builder (for 15 days)
- gsd-walkthru (for 13 days)
- customer-req-responder (for 13 days)


## 2026-05-21

### No updates
- ai-builder (for 14 days)
- gsd-walkthru (for 12 days)
- customer-req-responder (for 12 days)


## 2026-05-20

### No updates
- ai-builder (for 13 days)
- gsd-walkthru (for 11 days)
- customer-req-responder (for 11 days)


## 2026-05-19

### No updates
- ai-builder (for 12 days)
- gsd-walkthru (for 10 days)
- customer-req-responder (for 10 days)


## 2026-05-18

### No updates
- ai-builder (for 11 days)
- gsd-walkthru (for 9 days)
- customer-req-responder (for 9 days)


## 2026-05-17

### No updates
- ai-builder (for 10 days)
- gsd-walkthru (for 8 days)
- customer-req-responder (for 8 days)


## 2026-05-16

### No updates
- ai-builder (for 9 days)
- gsd-walkthru (for 7 days)
- customer-req-responder (for 7 days)


## 2026-05-15

### No updates
- ai-builder (for 8 days)
- gsd-walkthru (for 6 days)
- customer-req-responder (for 6 days)


## 2026-05-14

### No updates
- ai-builder (for 7 days)
- gsd-walkthru (for 5 days)
- customer-req-responder (for 5 days)


## 2026-05-13

### No updates
- ai-builder (for 6 days)
- gsd-walkthru (for 4 days)
- customer-req-responder (for 4 days)


## 2026-05-12

### No updates
- ai-builder (for 5 days)
- gsd-walkthru (for 3 days)
- customer-req-responder (for 3 days)


## 2026-05-11

### No updates
- ai-builder (for 4 days)
- gsd-walkthru (for 2 days)
- customer-req-responder (for 2 days)


## 2026-05-10

### No updates
- ai-builder (for 3 days)
- gsd-walkthru (for 1 days)
- customer-req-responder (for 1 days)


## 2026-05-09

### gsd-walkthru

- Phase 5 (GitHub & Shopify webhook signature providers) shipped end-to-end across `6c7241c..5977253` via discuss → plan → parallel worktree execution, replacing Phase 3 stubs in `src/providers/github.ts` and `src/providers/shopify.ts` with real HMAC-SHA256 validators. Test suite grew from 86 to 110 tests across 13 files.
- Both providers share an 8-step validation order (raw body guard → header parse → HMAC → timing-safe compare → metadata extraction → JSON parse → result build). Notable divergence from the Stripe provider: Buffer-direct HMAC avoids a UTF-8 round-trip. Two day-one correctness fixes applied: WR-02 (outer `expect(...).toThrow` guards on error-case tests) and WR-03 (three-way auth-header split distinguishing missing / malformed / deprecated headers).
- GitHub provider (`a96ae16`) silently ignores the deprecated SHA-1 `x-hub-signature` header — SHA-1-only requests fall through to `'missing_header'`. Shopify provider (`7fb70b4`) resolves hex-vs-base64 ambiguity via length-mismatch in the timing-safe compare path, surfacing as `'signature_mismatch'` without widening the error union.
- Code review (`5977253`) passed with 0 blockers; 5/5 must-haves confirmed. Phase 5 closed; 3 advisory warnings carried into `05-REVIEW.md` for Phase 6.
- Phase 6 scoped (`bb1667d`): `@vitest/coverage-v8` with `perFile` thresholds, integration suites at `tests/integration/{stripe,github,shopify}.test.ts`, 90% coverage gate, and a manual guard-removal verification protocol covering 8 carry-over advisories from Phases 4–5.

### customer-req-responder

- Project bootstrapped (`c974694..bce68578`): 7 files added, including a rough-draft spec (`spec-rough-draft.md`) and `open-questions.md` to seed the design space before formal specification begins.

### No updates
- ai-builder (for 2 days)


## 2026-05-08

### gsd-walkthru

- Completed Phase 4 (Stripe webhook provider) across commits `a99bbe7..cb09563`: implemented a 9-step HMAC-SHA256 (Hash-based Message Authentication Code) validator in `src/providers/stripe.ts` covering header parsing, constant-time multi-segment comparison, and a configurable replay-protection window (default 300 s); 15 unit tests added covering all security-critical paths — suite now 86/86 green across 11 files.
- Two preparatory type-level changes landed before the Stripe implementation: `WebhookValidationReason` union widened with `'invalid_signature_format'` (needed for malformed Stripe headers), and a `tolerance?: number` option added to the middleware factory so providers can receive a timestamp window without touching the `Provider` interface.
- Phase 3 close-out fixes were folded in (`a99bbe7`): `raw-body` promoted from a transitive express dependency to an explicit runtime dep (ship-blocker under pnpm/Yarn PnP), unknown-provider error message made dynamic via a new `listProviders()` registry export, and whitespace-only secrets now rejected — bringing the suite to 68 tests before Phase 4 work began.
- Wrote the initial `README.md` (`628867d`): project description, per-provider gotchas (Stripe timestamp window, GitHub SHA-256 + dedup header, Shopify base64-not-hex), and ASCII data-flow diagrams for both the system boundary and the internal middleware chain.
- Fixed a UTC-vs-Pacific timezone bug (`0ac66f1`) where the Claude Code sandbox's lack of a `TZ` env var caused `daily-plan.md` dates to land two calendar days ahead of the user's local date; corrected by setting `TZ=America/Los_Angeles` in the user-global Claude settings.
- Plan for 2026-05-08 targets Phase 5 (GitHub and Shopify providers) in a single session arc, with explicit pre-plan discussion flagged for two known failure modes: GitHub's deprecated SHA-1 header and Shopify's base64-vs-hex signature encoding.

### No updates
- ai-builder (for 1 days)


## 2026-05-07

### document-analyzer

- Bootstrapped for cross-repo activity tracking (`744e671..1543258b`): added `log.md`, `daily-plan.md`, a SessionStart hook (`check-daily-plan.py`) enforcing daily planning hygiene, and the corresponding `CLAUDE.md` rule block and `settings.json` registration — 170 lines across 4 files. No development work logged yet.

### ai-builder

- Bootstrapped for cross-repo status tracking (`f689f55..953afae`): added `log.md`, `daily-plan.md`, a `CLAUDE.md` rule block enforcing work-log discipline, and a SessionStart hook (`check-daily-plan.py`) that runs automatically on session open — 170 lines across 4 new files.

### gsd-walkthru

- Phase 3 (Body Handling & Public API Surface) fully delivered across 7 implementation tasks (`61e69b6..f6c9fa4`): raw-body capture middleware, a webhook provider registry with self-registering Stripe/GitHub/Shopify stubs, a `WebhookMetadata` discriminated union with compile-time narrowing proof, a `webhookErrorHandler()` Express error-middleware factory, the core `createWebhookMiddleware` factory, and the finalized public barrel — 67 tests green across 10 source files.
- The 96-file, 22k-line commit range covers the repo's entire history bootstrapped from scratch, including a full planning corpus under `.planning/` and the production `src/` tree.
- Post-phase rebase (`fd4631e`) integrated upstream bootstrap commits from `ai-project-status`, resolved `log.md` union conflicts, and separated `settings.local.json` from `.claude/settings.json` so per-user GSD hooks coexist with the project's SessionStart hook.
- Next session planned around pushing to origin, fixing blocker `BL-01`, a code-review fix pass, and scoping Phase 4.

### Cross-repo

- Today's activity was largely a tracking-infrastructure rollout: **document-analyzer** and **ai-builder** both received identical bootstrap treatment (same 170-line, 4-file footprint: `log.md`, `daily-plan.md`, `check-daily-plan.py` SessionStart hook, `CLAUDE.md` rule block, `settings.json`), and **gsd-walkthru**'s post-phase rebase also pulled in bootstrap commits from `ai-project-status` to integrate the same hook infrastructure alongside its existing project hooks.


## 2026-05-06

### document-analyzer
No activity for 2 days (last activity 2026-05-04)

### ai-builder
No activity for 3 days (last activity 2026-05-03)


## 2026-05-05

### document-analyzer
No activity for 1 days (last activity 2026-05-04)

### ai-builder
No activity for 2 days (last activity 2026-05-03)


## 2026-05-04

### document-analyzer

- Phase 11 wrapped up with the cross-strategy non-identity check (`31c3965`): after a question swap (the original canonical answer caused genuine naive/chunking convergence, a false positive the test's own comment had flagged), all 21 integration tests passed 21/21 under Tier 1.
- Gemini Tier 1 upgrade removed the recurring 20 RPD daily-cap blocker that stalled multiple phases; `GeminiClient` now logs `x-gemini-service-tier` on first call to confirm propagation without waiting for a quota error.
- Phase 12 built a full LLM-as-judge evaluation pipeline across 28 files / 2 889 insertions (`0d66a2a`..`5c72af5`): curated dataset (3 triples spanning short/medium/long docs), typed interfaces, triple loader, `LLMJudgeScorer` with retry-once-then-`score=null` sentinel, evaluator runner with parallel strategy fan-out, atomic JSON+MD co-located persistence, and `npm run eval` CLI with `--purpose`/`--no-save`/`--triple` flags.
- A scorer `maxTokens` ceiling (200 → 500, `5c72af5`) fixed a 67% unscoreable rate surfaced by a smoke run — verbose naive/chunking answers were truncating mid-JSON before the sentinel path could fire; the fix unblocks the `--purpose baseline` sweep.
- README gained an `## About this project` retrospective (`dbaece1`) and a promoted `## Testing` section covering all four layers (unit, integration, evaluations) with trigger lists, expected costs, and runnable examples.

### ai-builder
No activity for 1 days (last activity 2026-05-03)


## 2026-05-03

### document-analyzer
No activity for 0 days (last activity 2026-05-03)

### ai-builder

- **Repo initialized as first commit** (`4b825dc6..f689f55a`): this is the initial population of the entire codebase — 897 files, 64 k lines added, covering the orchestrator, task management scripts, regression test suite, lessons, and project infrastructure.
- Task tooling matured rapidly in the Apr 30–May 2 window: `new-user-task.sh` gained a required `--category` flag (`d442bd0`), `list-tasks.sh` got `--category` and `--group-by-category` filters with 9 new bats tests (`485a167`..`b615538`), enabling the canonical "what's next per worktree class" query.
- Parallel worktree workflow formalized: partition classes shipped to `project/tasks/classes.md`, four class worktrees created (acceptance-spec, docs, regression-infra, task-tooling), and a end-to-end "Standard task workflow" recipe added to CLAUDE.md (`f49cf50`..`dc2f590`).
- `log.md` work-log mechanism introduced (`69acb01`) with helper script at `project/scripts/log-add.sh`; overlap with `project/status/` resolved by reframing status as a delta document rather than a daily sign-off (`58f932e`).
- As of today, four tasks moved to in-progress across the new worktrees for parallel implementation (`f689f55`): pipeline-acceptance-spec-writer, gemini-frontend brainstorm, regression-test README review, and session-context document.


## 2026-05-03

### document-analyzer

- This appears to be an **initial import** of the full repo — 52 files, 9 110 lines added in a single range from an empty tree (`4b825dc6..2115578c`), covering everything from Phase 0 bootstrap through Phase 11.
- Core work across the range: built three LLM document-querying strategies (naive, chunking, divide-and-conquer) against the Gemini API, with a shared `RateLimitedLLMClient`, 429/5xx retry logic with `RetryInfo` parsing, and timing decomposed into `apiLatencyMs / backoffMs / localCpuMs` (`72e0d44`).
- Operational hardening added a pre-flight call-count budget gate (`--unsafe-skip-budget-check` / `GEMINI_RPM`), fault-tolerant `Promise.allSettled` fan-out, `--paced` sequential mode, and run-state persistence with `--resume <runId>` for quota-interrupted runs (`e0fdfb9`, `9e6b61a`).
- Test coverage is substantial: 155 unit tests + a live integration suite (Gemini client field-population, per-strategy invariants, tiktoken drift guard) with a shared rate-limited client across strategy `beforeAll`s to stay within the 5 RPM free-tier ceiling (`0bb7381`, `2d35e37`).
- As of the last commit (`2115578`), Phase 11 task 29 (cross-strategy non-identity check) is drafted and staged but unverified — daily quota exhausted before D&C's `beforeAll` could complete; pickup deferred to quota reset.

