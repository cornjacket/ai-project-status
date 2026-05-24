# AI Project Status Summary

Auto-maintained by ai-project-status. Newest activity at the top.

<!-- new sections inserted below -->

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

