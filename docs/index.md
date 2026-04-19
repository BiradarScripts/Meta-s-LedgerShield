# LedgerShield Documentation Hub

Quick navigation to all documentation, organized by category.

---

## Core (Start Here)

| Doc | Purpose |
|-----|---------|
| [`README.md`](../README.md) | Project overview, quick start, benchmark results |
| [`SUBMISSION_CONTRACT.md`](./SUBMISSION_CONTRACT.md) | Locked submission contract for Round 2 |
| [`benchmark-card.md`](./benchmark-card.md) | One-page benchmark summary for judges |
| [`demo-script.md`](./demo-script.md) | Frozen 5-step demo walkthrough (CASE-D-001) |

---

## Environment & API

| Doc | Purpose |
|-----|---------|
| [`tasks.md`](./tasks.md) | Task-by-task contracts and scoring rules |
| [`api-reference.md`](./api-reference.md) | Environment integration details |
| [`architecture.md`](./architecture.md) | Hidden-state, grading, and generation pipeline |
| [`development.md`](./development.md) | Repo map and contributor workflow |
| [`deployment.md`](./deployment.md) | Running LedgerShield outside local dev shell |

---

## Verification Reports

| Phase | Report |
|-------|--------|
| P0-0 | [`P0-0_VERIFICATION_REPORT.md`](./P0-0_VERIFICATION_REPORT.md) — Submission contract locked |
| P0-1 | [`P0-1_VERIFICATION_REPORT.md`](./P0-1_VERIFICATION_REPORT.md) — Runtime validation (9 endpoints verified) |
| P0-2 | [`P0-2_VERIFICATION_REPORT.md`](./P0-2_VERIFICATION_REPORT.md) — Benchmark artifacts frozen |
| P0-3 | [`P0-3_VERIFICATION_REPORT.md`](./P0-3_VERIFICATION_REPORT.md) — Case audit complete |
| P0-4 | [`P0-4_VERIFICATION_REPORT.md`](./P0-4_VERIFICATION_REPORT.md) — Portfolio track strengthened |
| P0-5 | [`P0-5_VERIFICATION_REPORT.md`](./P0-5_VERIFICATION_REPORT.md) — Evaluator hardened |
| P0-6 | [`P0-6_VERIFICATION_REPORT.md`](./P0-6_VERIFICATION_REPORT.md) — README cleanup complete |
| P0-7 | [`P0-7_VERIFICATION_REPORT.md`](./P0-7_VERIFICATION_REPORT.md) — Demo assets frozen |
| P0-8 | [`P0-8_VERIFICATION_REPORT.md`](./P0-8_VERIFICATION_REPORT.md) — Mini-blog package verified |

---

## Plan A Handoff

| Doc | Purpose |
|-----|---------|
| [`PLAN_A_FINAL_DELIVERABLES.md`](./PLAN_A_FINAL_DELIVERABLES.md) | Master handoff checklist (9/10 complete, A8 pending HF publish) |

---

## Publishing (A8)

| Doc | Purpose |
|-----|---------|
| [`HF_MINIBLOG_FINAL.md`](./HF_MINIBLOG_FINAL.md) | Mini-blog source (445 words, ready for HF) |
| [`A8_PUBLISHING_GUIDE.md`](./A8_PUBLISHING_GUIDE.md) | Step-by-step HF publication instructions |

---

## Supporting Docs

| Doc | Purpose |
|-----|---------|
| [`ashtg-theory.md`](./ashtg-theory.md) | ASHTG formal framework |
| [`mini-blog.md`](./mini-blog.md) | Earlier draft (superseded by HF_MINIBLOG_FINAL) |
| [`tasks.md`](./tasks.md) | Detailed task contracts |

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

**Status:** Plan A 9/10 complete. A8 pending manual publication to Hugging Face.