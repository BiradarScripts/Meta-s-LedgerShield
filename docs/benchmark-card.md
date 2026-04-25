# LedgerShield ControlBench Benchmark Card

## Identity

LedgerShield ControlBench is a benchmark for **verified institutional control intelligence** in enterprise accounts-payable workflows.

- Primary theme: **World Modeling — Professional Tasks**
- Secondary theme: **Long-Horizon Planning & Instruction Following**
- Public mode: **blind by default**

## What Makes It Hard

The agent is not graded on a one-shot classification. It must:

1. investigate under budget and step limits
2. trigger enterprise controls and wait for delayed artifacts
3. keep decisions aligned with hidden backend state
4. manage AP-week capacity and portfolio consequences
5. preserve institutional value over long-horizon ControlBench sequences
6. produce an auditable decision certificate

## Official Tracks

### Case Track

Single-case control performance.

- measures: correctness, policy completion, evidence grounding, intervention quality, unsafe release prevention

### Portfolio Track

Persistent AP-week performance.

- measures: institutional utility, queue pressure handling, review/callback burn, attacker adaptation, sequence-level outcomes

### Adversarial Data Track

Hostile or deceptive content inside documents, email threads, or tool outputs.

- measures: resistance to spoofing, urgency pressure, misleading evidence, and workflow override attempts

### Generated Holdout Track

Seeded procedural AP ecosystems generated from benchmark archetypes.

- measures: anti-overfit robustness to unseen mechanism tuples and surface variation

### ControlBench Track

Seeded AP-quarter institutional-control performance.

- measures: institutional loss surface, calibration-gated authority, sleeper-vendor vigilance, catastrophic events, and deployability rating

### Sleeper-Vigilance Track

The subset of ControlBench focused on trust-building vendors that later activate.

- measures: whether institutional memory helps detect, rather than excuse, later fraud

### Blind-Control Track

Benchmark evaluation with SPRT, VoI, and reward-machine scaffolding hidden from the acting agent.

- measures: whether the agent still preserves value without evaluator hints

### Certificate-Required Track

Strict proof-carrying payment decisions.

- measures: whether agent-authored Decision Certificate Graphs survive schema, support-path, contradiction, grounding, and stability checks

### Human-Baseline Track

Optional AP, accounting, audit, and finance-manager participant summaries.

- measures: human accuracy, escalation behavior, evidence citation, speed, and calibration anchors

## Headline Metrics

- `control_satisfied_resolution`
- `institutional_utility`
- `institutional_loss_score`
- `loss_surface`
- `authority_level`
- `sleeper_detection_rate`
- `certificate_required_mean`
- `adversarial_falsifier_verdict`
- `control_boundary`
- `human_baseline_track`
- `unsafe_release_rate`
- `certificate_validity_rate`
- `result_class`

## Result Classes

- `valid_success`
- `correct_but_policy_incomplete`
- `unsafe_release`
- `authority_gate_failed`
- `control_boundary_failed`
- `unsupported_certificate`
- `malformed_submission`
- `false_positive_overcontrol`
- `incorrect_resolution`

## Generalization Policy

LedgerShield ControlBench reports:

- public split performance
- holdout performance over latent mechanism tuples
- blind-control performance with evaluator scaffolding hidden
- contrastive performance on near-identical surface pairs with different hidden mechanisms
- ControlBench sequence performance over seeded AP-quarter cases
- sleeper-vigilance performance over trust-building vendor activations
- certificate-required proof-gated performance
- optional human-baseline summaries
- two-agent control-profile disagreement between accuracy and institutional loss

Each case carries hidden mechanism metadata:

- attack family
- compromise channel
- pressure profile
- control weakness
- vendor history state
- bank adjustment state
- campaign linkage
- portfolio context

## Demo Cases

Recommended showcase set:

- `CASE-D-001`
- `CASE-D-003`
- `CASE-D-004`
- `CASE-D-005`
- `CASE-E-001`
- `CASE-E-002`
- `CASE-C-001`
- `CASE-C-004`

## Evaluation Notes

- `LEDGERSHIELD_TRACK_MODE=blind` is the benchmark default
- `LEDGERSHIELD_TRACK_MODE=instrumented` is diagnostics-only
- `LEDGERSHIELD_INCLUDE_CONTROLBENCH=true` can load generated ControlBench sequence cases into the runtime database
- `benchmark_report.py --controlbench-sequence-length 100` runs the standard AP-quarter ControlBench report
- `artifacts/human_baseline.json` or `LEDGERSHIELD_HUMAN_BASELINE_PATH` can provide a human reference profile
- certificates improve auditability but do not rescue wrong or unsafe control behavior
