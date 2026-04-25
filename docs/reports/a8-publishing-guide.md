---
title: "A8 — Publishing Guide"
description: "Publishing checklist for the Hugging Face Space, leaderboard artifacts, and submission package."
icon: "upload"
sidebarTitle: "A8 Publishing Guide"
---

> Source: `docs/A8_PUBLISHING_GUIDE.md` (consolidated)

> Historical archive: this guide references the pre-ControlBench v2 publishing
> package. Current primary docs and artifacts use `ledgershield-controlbench-v1`.

## Final Blog Content

The finalized mini-blog is ready in `docs/HF_MINIBLOG_FINAL.md`.

**Title:** LedgerShield v2: Hardening Enterprise Payment Controls through Agent Benchmarking

**Subtitle:** A benchmark that asks whether agents can operate defensible enterprise control regimes, not just spot suspicious invoices.

**Word Count:** 445 words

**Status:** Ready to publish

---

## How to Publish to Hugging Face Blog

1. **Navigate to Hugging Face Blog Editor:**
   - Go to https://huggingface.co/blog
   - Sign in to your account
   - Click "Write a blog post" or navigate to your profile → "My Blog"

2. **Fill in Blog Details:**
   - **Title:** `LedgerShield v2: Hardening Enterprise Payment Controls through Agent Benchmarking`
   - **Subtitle:** `A benchmark that asks whether agents can operate defensible enterprise control regimes, not just spot suspicious invoices.`
   - **Content:** Copy the full text from `docs/HF_MINIBLOG_FINAL.md` (starting from "## What is LedgerShield v2?" section)

3. **Add Cover Image/Screenshot:**
   - Suggested: Screenshot from `/artifacts/before_after.html` (the improvement visual)
   - Or: Screenshot of the leaderboard at `http://localhost:8000/leaderboard` (once server is running)
   - Dimensions: ~1200×630px recommended

4. **Add Tags/Categories:**
   - `benchmarking`
   - `ai-safety`
   - `fraud-detection`
   - `agents`
   - `enterprise-ai`

5. **Add Links:**
   - Repository: `https://github.com/YOUR-USERNAME/Meta-s-LedgerShield`
   - Submission Contract: Link to the SUBMISSION_CONTRACT.md in your repo

6. **Preview & Publish:**
   - Click "Preview"
   - Verify formatting and links
   - Click "Publish"

7. **After Publishing:**
   - Copy the final published URL (format: `https://huggingface.co/blog/YOUR-USERNAME/SLUG`)
   - Update `docs/PLAN_A_FINAL_DELIVERABLES.md` with this link

---

## Next Step

**Please publish the blog to Hugging Face and provide the final URL.** Once you do, I will:
- Record the link in the PLAN_A_FINAL_DELIVERABLES.md
- Run all verification tests
- Create the final commit

**Or:** If you would prefer, you can provide me with HF credentials and I can attempt to publish programmatically (using HF API).

---
