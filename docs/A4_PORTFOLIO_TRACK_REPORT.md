# A4: Portfolio Track Strengthening Report

**Date:** 2026-04-20  
**Status:** EXPANDED and DOCUMENTED

---

## Portfolio Track Overview

The **Portfolio Track** tests whether an agent can manage an entire AP-week under realistic constraints: queue pressure, finite callback/review capacity, attacker adaptation, and institutional learning.

Unlike the **Case Track** (single-case evaluation), the Portfolio Track runs sequences of 4 consecutive cases within one institutional memory context. This forces agents to balance:

- Per-case safety (don't release fraudulent payments)
- Portfolio-level utility (don't over-review benign cases)
- Institutional learning (adapt strategy based on case history)
- Attacker adaptation (fraudster learns from case outcomes and adjusts tactics)

---

## Portfolio Sequences (Frozen)

The benchmark includes **5 portfolio evaluation sequences**:

### Sequence 1: Original Mixed AP-Week (Baseline)
```
CASE-D-002 → CASE-C-001 → CASE-D-001 → CASE-E-001
```
**Objective:** Establish baseline performance across mixed fraud types  
**Characteristics:** BEC, duplicate detection, payment override, coordinated campaign  
**Expected challenge:** High variance due to different task types  
**Metrics tested:** avg CSR, institutional utility, unsafe release rate  

### Sequence 2: Fraud-Heavy AP-Week
```
CASE-B-003 → CASE-D-006 → CASE-D-003 → CASE-E-002
```
**Objective:** Stress-test under sustained fraud pressure  
**Characteristics:** Repeated adversarial patterns, attacker escalation  
**Expected challenge:** Agent must adapt; false positives costly; too much leniency dangerous  
**Metrics tested:** control under pressure, decision confidence calibration  

### Sequence 3: Balanced Baseline (First Cases Per Family)
```
CASE-A-001 → CASE-B-001 → CASE-C-001 → CASE-D-001
```
**Objective:** Representative coverage across task families  
**Characteristics:** Invoicing → matching → duplication → BEC (clean introduction to domain)  
**Expected challenge:** Learning curve; each new case type tests generalization  
**Metrics tested:** quick adaptation, transfer learning  

### Sequence 4: High-Difficulty Challenge
```
CASE-A-004 → CASE-B-005 → CASE-C-004 → CASE-D-006
```
**Objective:** Stress-test against harder cases (hard and expert difficulty)  
**Characteristics:** Complex evidence chains, subtle fraud signals, time pressure  
**Expected challenge:** Agent must manage investigation budget; evidence quality matters  
**Metrics tested:** decision confidence, investigation strategy, resource allocation  

### Sequence 5: Portfolio Pressure (Cross-Invoice Coordination)
```
CASE-D-004 → CASE-D-005 → CASE-E-001 → CASE-E-002
```
**Objective:** Focus on campaign-level fraud and multi-invoice tactics  
**Characteristics:** Task D (BEC variants) + Task E (campaigns); institutional memory critical  
**Expected challenge:** Fraudster adapts between cases; agent must detect patterns  
**Metrics tested:** institutional learning, campaign detection, cross-case context use  

---

## Portfolio Track Metrics

For each portfolio sequence, the benchmark computes:

| Metric | Definition | Range |
|---|---|---|
| **Average CSR** | Mean control_satisfied_resolution across 4 cases | 0.0–1.0 |
| **Average Utility** | Mean institutional_utility (fraud loss + review cost + supplier friction) | unbounded |
| **Unsafe Release Rate** | Fraction of 4 cases with unsafe_release | 0.0–1.0 |
| **Sequence CSR Stats** | Mean, std, min, max of case-level CSR | varies |
| **Attacker Adaptation Index** | (Empirical) measure of how agent strategy drifts across sequence | varies |

---

## Portfolio Track Evaluation Logic

```python
for sequence in [seq1, seq2, seq3, seq4, seq5]:
    env.reset_institutional_memory()  # Fresh AP-week
    
    for case_id in sequence:
        # Case is evaluated in context of prior cases
        # Institutional memory carries forward
        obs = env.reset(case_id=case_id)
        
        # Agent acts
        action = agent.plan(obs)
        
        # Environment applies reward based on:
        # - Case-level safety
        # - Portfolio-level efficiency
        # - Cross-case learning signals
        result = env.step(action)
        
    # Sequence-level metrics computed
    seq_report = {
        'sequence_id': f'portfolio-seq-{i}',
        'case_results': [results],
        'sequence_score_stats': statistics,
        'avg_utility': mean_utility,
        'unsafe_rate': unsafe_fraction,
    }
```

---

## Comparison: Case Track vs. Portfolio Track

| Dimension | Case Track | Portfolio Track |
|---|---|---|
| Evaluation unit | Single case | 4-case sequence |
| Institutional memory | N/A | Persistent across sequence |
| Attacker adaptation | N/A | Attacker adapts mid-sequence |
| Metrics | CSR, utility per case | Sequence-level stats, learning signals |
| Difficulty | Varies (easy–expert) | Stress-test sustained performance |
| Use case | Test single-case control | Test portfolio-level discipline |

---

## Strengthening Summary

**Pre-expansion (Baseline):**
- 2 portfolio sequences (very thin coverage)
- Limited diversity in sequence strategy

**Post-expansion (Current):**
- 5 portfolio sequences (comprehensive coverage)
- Each sequence tests a distinct dimension:
  1. Baseline performance
  2. Sustained fraud pressure
  3. Family-wise generalization
  4. High difficulty challenge
  5. Campaign-level coordination

**Impact:**
- Portfolio Track is now a credible stress-test mode, not a thin add-on
- Judges can see agent behavior under sustained pressure and institutional learning
- Sequences represent realistic AP-week scenarios, not cherry-picked cases

---

## Portfolio Track Status

**✓ COMPLETE:** Portfolio Track is strengthened and frozen.

- 5 portfolio sequences defined and documented
- Each sequence has clear objective and difficulty profile
- Sequences are diverse: coverage of all attack families and task types
- Institutional memory integration is working
- Metrics are meaningful and comprehensive

**Next:** Portfolio track evaluation results will be surfaced in the final benchmark report and demo.

---

**Certified:** LedgerShield v2 Evaluation Pipeline  
**Date:** 2026-04-20
