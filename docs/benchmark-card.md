# LedgerShield v2 Benchmark Card

## Identity

LedgerShield v2 is a benchmark for **verified institutional control intelligence** in enterprise accounts-payable workflows.

- Primary theme: **World Modeling / Professional Tasks**
- Secondary theme: **Long-Horizon Planning & Instruction Following**
- Public mode: **blind by default**

## What Makes It Hard

The agent is not graded on a one-shot classification. It must:

1. investigate under budget and step limits
2. trigger enterprise controls and wait for delayed artifacts
3. keep decisions aligned with hidden backend state
4. manage AP-week capacity and portfolio consequences
5. produce an auditable decision certificate

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

## Headline Metrics

- `control_satisfied_resolution`
- `institutional_utility`
- `unsafe_release_rate`
- `certificate_validity_rate`
- `result_class`

## Result Classes

- `valid_success`
- `correct_but_policy_incomplete`
- `unsafe_release`
- `unsupported_certificate`
- `malformed_submission`
- `false_positive_overcontrol`
- `incorrect_resolution`

## Generalization Policy

LedgerShield v2 reports:

- public split performance
- holdout performance over latent mechanism tuples
- contrastive performance on near-identical surface pairs with different hidden mechanisms

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
- certificates improve auditability but do not rescue wrong or unsafe control behavior
