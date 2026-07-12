# Daily plan summary — 2026-07-11

<!-- Auto-aggregated by tools/aggregate-plans.py from each tracked repo's daily-plan.md. Overwritten on every run. -->

## second-brain-test — STALE (last plan: 2026-07-09)

**Focus:** The #10 → #8 thread was prototyped here and handed off (splice helper + full
auto-linking: canonical-body embedding, nomic prefixes, KNN calibration, `related_auto:`
write path, `content_hash` gate — all proven against real Ollama, then vendored → template →
devkit CI 7/7). Next in the thread is **#9 (README markers)**; after that, seed the
**diverse corpus (#15)** here so real semantic structure exists to tune against.

- **Prototype task #9 — the README managed block** in the golden `README.md`: HTML-comment
  markers (`<!-- BEGIN/END generated -->`) wrapping the devkit-owned region, spliced via the
  shared helper so a user's own preamble/appendix is preserved. This is the emitted half the
  devkit vendors + templatizes.
- **Then seed the task #15 diverse corpus here** — many topically-distinct notes embedded
  with real Ollama, so the auto-link `t_max`/topic-count analysis has genuine cluster
  structure (today's ~7 notes are one blob). This repo is where the deferred auto-link
  `--apply` eventually runs once the corpus lands.
- **Stay a clean diff oracle** — `self_test.py` green; resolve any golden/template mismatch
  here first. CI gates (compile, `check_autolink_format`, …) live in the devkit, not here.

```
 role: hand-prototype → prove (real Ollama) → hand off to the devkit
                              │
 wed 07-08 ✅ prototyped #10 helper + #8 auto-linking end-to-end → handed off (devkit CI 7/7)
                              │
 thu 07-09 ▸ prototype #9 README markers (splice via #10 helper)
            → seed #15 diverse corpus (real Ollama) for t_max / topic-count tuning
```

## second-brain-devkit — plan for 2026-07-13

**Focus:** Fri 07-10 landed **#15** — the 200-note topically-diverse benchmark corpus + a
30-query labeled eval set + corpus-driven tooling, with acceptance **passed on real Ollama**
(purity@1 98%, separation +0.136, a confident `t_max ≈ 0.30`, retrieval top-5 30/30). With the
dataset **and** the method now in hand, Monday opens the benchmarking thread and the top
IT-separation lever.

- **▶▶ Start #13 — catalog the quality-enhancement features** (docs-only; the input to #12 and
  the tutorial outline): each retrieval/graph feature with its mechanism, index- vs query-time,
  config toggle, and status.
- **Then #12 — the ablation harness** scaffold: run `queries.jsonl` against the #15 corpus under
  each toggle, reporting recall@k / MRR / separation. Also the vehicle to **compare embedders**.
- **Parallel lever — #3 hybrid FTS5/BM25:** highest-ROI for the IT-heavy real brain (exact tokens
  dense vectors blur). See `docs/embedding-separation.md §1`.
- **Optional:** run the now-unblocked auto-link `--apply` calibration on the real brain (derive
  its own `t_max` — IT-heavy, so expect a looser cut than the diverse corpus).
- Guards stay green via `tools/ci.py` (8 gates).

```
 fri 07-10 ✅ #15 corpus + eval set + tooling · acceptance PASS (98% purity, t_max≈0.30)
                              │
                              ▼
 mon 07-13  ▶▶ #13 feature catalog ──► #12 ablation harness  (consumes #15 corpus + queries)
            ‖ parallel: #3 hybrid FTS5/BM25 (IT-separation lever)
            → optional: real-brain auto-link --apply calibration
 guards: tools/ci.py (8) green
```

## customer-req-responder — STALE (last plan: 2026-05-29)

Decide the workflow methodology for this project going forward. Researched the field
(GSD, Superpowers, Claude Skills, chub, Everything Claude Code, paperclip, RooFlow, Open Design)
via parallel subagents. Decision: **switch to Superpowers** for this project (single framework,
not stacked with GSD). Rationale: small greenfield TS/Node pipeline is an ideal TDD fit, fresh
learning ground that feeds the homegrown ai-builder framework, and low-risk to trial at this size.
Two known gaps to own deliberately: (a) no LLM/eval phase like GSD's AI-SPEC / eval-review — will
hand-spec the eval or author an own eval skill; (b) draft-quality is non-deterministic, so TDD
covers the plumbing while a separate Gemini-as-judge eval loop covers generation. The log.md /
daily-plan.md / project-status discipline is framework-agnostic and stays. Next: set up
Superpowers and start brainstorm on the 6 blocking open questions toward SPEC.md.

```
  workflow decision                    spec work (via Superpowers)
  ┌──────────────────────────┐        ┌─────────────────────────────┐
  │ research candidates   ok │        │ /superpowers:brainstorm  --> │
  │ score vs project      ok │   -->  │ answer blocking Qs           │ --> plan
  │ DECISION: Superpowers ok │        │ (2,4,5,7,9,11)               │
  └──────────────────────────┘        └─────────────────────────────┘
   replace GSD, keep ai-builder log     own the eval loop separately
```
