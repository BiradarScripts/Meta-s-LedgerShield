---
title: "Documentation Index"
description: "Quick navigation to every documentation page, organized by category."
icon: "list"
sidebarTitle: "Index"
---

> Source: `docs/index.md` (consolidated)

Quick navigation to all documentation, organized by category.

---

## Core (Start Here)

| Doc | Purpose |
|-----|---------|
| [`README.md`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/README.md) | Project overview, quick start, benchmark results |
| [`SUBMISSION_CONTRACT.md`](/contracts/submission-contract) | Locked submission contract for Round 2 |
| [`benchmark-card.md`](/benchmark/benchmark-card) | One-page benchmark summary for judges |
| [`demo-script.md`](/guides/demo-script) | Frozen 5-step demo walkthrough (CASE-D-001) |

Current codebase framing: **LedgerShield ControlBench** extends the original v2 benchmark with ControlBench, generated-holdout, sleeper-vigilance, blind-control, certificate-required, and human-baseline tracks; institutional loss surface; calibration-gated authority; a statechart-style control boundary; and `/controlbench-summary` plus `/human-baseline-summary` API support.

---

## Environment & API

| Doc | Purpose |
|-----|---------|
| [`tasks.md`](/benchmark/tasks) | Task-by-task contracts and scoring rules |
| [`api-reference.md`](/api-reference) | Environment integration details |
| [`architecture.md`](/architecture/overview) | Hidden-state, grading, and generation pipeline |
| [`development.md`](/guides/development) | Repo map and contributor workflow |
| [`deployment.md`](/guides/deployment) | Running LedgerShield outside local dev shell |

---

## Verification Reports

These are historical Round 2 / Plan A artifacts. They describe the pre-ControlBench `LedgerShield v2` freeze and are kept for provenance; the current implementation story is the ControlBench extension described in the root README, architecture docs, API docs, `openenv.yaml`, and `benchmark_report.py`.

| Phase | Report |
|-------|--------|
| P0-0 | [`P0-0_VERIFICATION_REPORT.md`](/verification/p0-0) — Submission contract locked |
| P0-1 | [`P0-1_VERIFICATION_REPORT.md`](/verification/p0-1) — Runtime validation (9 endpoints verified) |
| P0-2 | [`P0-2_VERIFICATION_REPORT.md`](/verification/p0-2) — Benchmark artifacts frozen |
| P0-3 | [`P0-3_VERIFICATION_REPORT.md`](/verification/p0-3) — Case audit complete |
| P0-4 | [`P0-4_VERIFICATION_REPORT.md`](/verification/p0-4) — Portfolio track strengthened |
| P0-5 | [`P0-5_VERIFICATION_REPORT.md`](/verification/p0-5) — Evaluator hardened |
| P0-6 | [`P0-6_VERIFICATION_REPORT.md`](/verification/p0-6) — README cleanup complete |
| P0-7 | [`P0-7_VERIFICATION_REPORT.md`](/verification/p0-7) — Demo assets frozen |
| P0-8 | [`P0-8_VERIFICATION_REPORT.md`](/verification/p0-8) — Mini-blog package verified |

---

## Plan A Handoff

| Doc | Purpose |
|-----|---------|
| [`PLAN_A_FINAL_DELIVERABLES.md`](/reports/plan-a-deliverables) | Master handoff checklist (9/10 complete, A8 pending HF publish) |

---

## Publishing (A8)

| Doc | Purpose |
|-----|---------|
| [`HF_MINIBLOG_FINAL.md`](/blog/hf-mini-blog) | Mini-blog source (445 words, ready for HF) |
| [`A8_PUBLISHING_GUIDE.md`](/reports/a8-publishing-guide) | Step-by-step HF publication instructions |

---

## Supporting Docs

| Doc | Purpose |
|-----|---------|
| [`ashtg-theory.md`](/architecture/ashtg-theory) | ASHTG formal framework |
| [`mini-blog.md`](/blog/mini-blog) | Earlier draft (superseded by HF_MINIBLOG_FINAL) |

---

## Quick Commands

```bash
# Install
pip install -e . && pip install -r requirements.txt

# Run server
python server/app.py

# Run tests
python -m pytest tests/ -q

# Validate submission
bash validate-submission.sh
```

---

**Status:** ControlBench implementation is active in code and docs; Plan A reports remain archived provenance.

---
