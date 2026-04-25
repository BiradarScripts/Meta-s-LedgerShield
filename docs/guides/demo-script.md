---
title: "Demo Script"
description: "Frozen 5-step demo walkthrough for CASE-D-001, optimized for judges and live demos."
icon: "play"
sidebarTitle: "Demo Script"
---

> Source: `docs/demo-script.md` (consolidated)

> Historical archive: this script documents the frozen Round 2 v2 demo. The
> current implementation story is LedgerShield ControlBench, which keeps this
> case-level demo and adds long-horizon loss-surface, calibration-gate, and
> sleeper-vendor sequence evaluation.

## Goal

Show, in under three minutes, that LedgerShield is a benchmark for institutional control intelligence rather than generic fraud detection.

## Demo Flow

### 1. Open the benchmark identity

Say:

> LedgerShield v2 evaluates whether an agent can operate a defensible AP control regime under partial observability, delayed artifacts, and portfolio pressure.

### 2. Run one live case

Recommended case:

- `CASE-D-001`

Show:

1. reset in `blind` mode
2. inspect email thread
3. compare bank account
4. request callback verification
5. submit decision

Point out:

- diagnostics are hidden in public mode
- delayed callback artifact changes what the agent can justify
- success depends on control behavior, not rhetoric

### 3. Show the metric split

Use the benchmark report and highlight:

- `control_satisfied_resolution`
- `institutional_utility`
- `unsafe_release_rate`
- `result_class`

Say:

> Two agents can have similar average scores, but LedgerShield separates the one that released money unsafely from the one that behaved like a control function.

### 4. Show the portfolio advantage

Open the `portfolio_track` section in the report and show:

- AP-week state delta
- callback/review capacity movement
- sequence-level utility

### 5. Close with the novelty statement

Say:

> The benchmark is hard because the agent must generalize across latent fraud mechanisms, manage enterprise controls over time, and satisfy policy gates against hidden backend state in blind mode.

---
