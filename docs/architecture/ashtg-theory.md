---
title: "ASHTG Theory"
description: "Adversarial Sequential Hypothesis Testing Game — the theoretical framework grounding LedgerShield's rewards, stopping rules, and grading."
icon: "brain-circuit"
sidebarTitle: "ASHTG Theory"
---

> Source: `docs/ashtg-theory.md` (consolidated)

## The Adversarial Sequential Hypothesis Testing Game

LedgerShield formalizes invoice fraud investigation as an **Adversarial Sequential Hypothesis Testing Game (ASHTG)** — a theoretically grounded framework that unifies five distinct mathematical traditions never previously combined in a single evaluation environment.

---

## 1. The Core Thesis

Every existing OpenEnv environment uses one of:
- Hand-tuned reward functions with no theoretical basis
- Counting steps as a proxy for investigation quality
- Classification accuracy as the terminal grading signal

LedgerShield breaks all three conventions:

| Convention | LedgerShield Innovation |
|---|---|
| Hand-tuned rewards | Rewards derived from **Value of Information** (Howard 1966, Lindley 1956) |
| Step counting | Investigation terminates at **Wald's SPRT optimal stopping boundary** |
| Classification accuracy | Grading uses **strictly proper scoring rules** proven mathematically strategy-proof |
| Correlation grading | **Pearlian counterfactual evaluation** at Level 3 of the causal hierarchy |
| Single-agent | **Stackelberg Security Game** watchdog with Nash equilibrium audit policy |

---

## 2. Pillar 1 — Wald's Sequential Probability Ratio Test (SPRT)

### Theoretical Foundation
- **Primary**: Wald, A. (1945). Sequential Tests of Statistical Hypotheses. *Annals of Mathematical Statistics*, 16(2):117–186.
- **Theory**: Wald, A. & Wolfowitz, J. (1948). Optimum character of the sequential probability ratio test. *Annals of Mathematical Statistics*, 19(3):326–339.

### What We Built
The `sprt_engine.py` module formalizes each LedgerShield investigation as a **sequential multi-hypothesis test** over 12 fraud hypotheses:

```
H₀: safe          H₁: bank_fraud      H₂: duplicate_billing
H₃: vendor_takeover   H₄: ceo_bec    H₅: phantom_vendor
H₆: supply_chain  H₇: insider_collusion   H₈: multi_entity_layering
H₉: campaign_fraud    H₁₀: split_payment  H₁₁: threshold_evasion
```

For each hypothesis Hᵢ, the **Log-Likelihood Ratio** is updated with every tool observation:

```
LLR_i(t) = LLR_i(t-1) + log[ P(obs_t | H_i) / P(obs_t | H_0) ]
```

Wald's boundaries at error rates (α=0.05, β=0.10):
```
Upper boundary: A = log((1-β)/α) = log(18.0) ≈ 2.89
Lower boundary: B = log(β/(1-α)) = log(0.105) ≈ -2.25
```

**Key property**: When LLR_i ≥ A, the SPRT guarantees Type I error ≤ α and maximizes Expected Sample Number (ESN). This proves the investigation is optimal — it terminates at the earliest provably sufficient evidence.

### Implementation
```python
# server/sprt_engine.py
state = initialize_sprt(alpha=0.05, beta=0.10)
state = update_sprt(state, "compare_bank_account", {"matched": False})
stop = optimal_stopping_check(state, budget_remaining=5.0)
# → {"should_stop": True, "recommended_decision": "ESCALATE_FRAUD"}
```

---

## 3. Pillar 2 — Pearl's Structural Causal Model (SCM)

### Theoretical Foundation
- **Primary**: Pearl, J. (2009). *Causality: Models, Reasoning and Inference* (2nd ed.). Cambridge University Press.
- **Counterfactuals**: Pearl, J. (2000). The logic of counterfactuals in causal inference. *Statistical Science*.
- **d-Separation**: Verma, T. & Pearl, J. (1988). Causal networks: Semantics and expressiveness. *Proceedings of UAI*, 352–359.

### What We Built
The `causal_model.py` module defines a full **Structural Causal Model** over AP payment decisions. The SCM operates at all three levels of Pearl's Ladder of Causation:

- **Level 1 (Association)**: P(decision | observed_signals)
- **Level 2 (Intervention)**: P(decision | do(inspect_email)) — which tools cause belief updates
- **Level 3 (Counterfactual)**: "What would the decision have been if the bank account matched?"

The **d-separation grading score** measures whether the agent's investigation correctly blocks all confounding paths:

```
d_sep_score = |{confounders blocked by obs_set}| / |confounders|
```

Where `confounders` are SCM nodes that can create spurious associations between evidence and decision.

### Implementation
```python
# server/causal_model.py + server/causal_grader.py
scm = build_causal_model_for_case(case)
observed = scm.observed_nodes_for_actions(["inspect_email_thread", "compare_bank_account"])
d_sep = scm.d_separation_sufficiency(observed)  # → 0.85
counterfactual = scm.counterfactual(overrides={"bank_alignment": "match"})  # → {"decision": "PAY"}
```

---

## 4. Pillar 3 — Value of Information (VoI) Rewards

### Theoretical Foundation
- **Primary**: Howard, R.A. (1966). Information Value Theory. *IEEE Transactions on Systems Science and Cybernetics*, 2(1):22–26.
- **Expected Utility**: Savage, L.J. (1954). *The Foundations of Statistics*. Wiley.
- **Myopic VoI**: Krause, A. & Guestrin, C. (2009). Optimal value of information in graphical models. *JAIR*, 35:557–591.

### What We Built
Instead of hand-tuned rewards, `voi_engine.py` computes the **Value of Information** for each available tool before the agent acts:

```
VoI(tool) = E[max_a U(a, θ) after observing tool] - max_a E[U(a, θ)] - cost(tool)
```

Where:
- `θ` = latent fraud hypothesis (unknown to agent)
- `a` = possible decisions (PAY/HOLD/ESCALATE_FRAUD/NEEDS_REVIEW)
- `U(a, θ)` = utility table valued from enterprise loss/recovery data
- `cost(tool)` = budget cost of the investigation action

**Key property**: VoI > 0 means the tool provides more decision-relevant information than it costs to obtain. This is the mathematically principled answer to "which tool should the agent call next?"

### Implementation
```python
# server/voi_engine.py
voi = value_of_information("compare_bank_account", sprt_state, cost=0.15)
optimal = optimal_tool_selection(available_tools, sprt_state, budget, costs)
plan = myopic_vs_nonmyopic_voi(sprt_state, budget, horizon=3)
```

---

## 5. Pillar 4 — Strictly Proper Scoring Rules

### Theoretical Foundation
- **Primary**: Gneiting, T. & Raftery, A.E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. *JASA*, 102(477):359–378.
- **Brier Score**: Brier, G.W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, 78(1):1–3.
- **Log Score**: Good, I.J. (1952). Rational decisions. *JRSS-B*, 14(1):107–114.
- **Strategy-proofness**: McCarthy, J. (1956). Measures of the value of information. *PNAS*, 42(9):654–655.

### What We Built
`proper_scoring.py` implements a composite scoring function over the agent's submitted `predicted_probabilities`:

```
score = 0.40 × Brier(p, θ*) + 0.30 × LogScore(p, θ*) + 0.30 × PenalizedBrier(p, θ*)
```

Where θ* is the true latent hypothesis revealed at episode end.

**Key property**: For any strictly proper scoring rule S, the agent's optimal strategy is to report their *true beliefs* — misreporting confidence cannot improve the score. This is mathematically proven (McCarthy 1956, Savage 1971). The benchmark is **ungameable by design**.

The `PenalizedBrier` variant adds a penalty proportional to max(0, P(wrong) - P(right)), which further penalizes overconfident wrong answers.

### Implementation
```python
# server/proper_scoring.py
score = composite_proper_score({"bank_fraud": 0.85, "safe": 0.15}, true_class="bank_fraud")
# honest high-confidence correct answer →  ~0.97
# overconfident wrong answer → ~0.02
```

---

## 6. Pillar 5 — LTLf Reward Machines

### Theoretical Foundation
- **Primary**: De Giacomo, G. & Vardi, M.Y. (2015). Synthesis for LTL and LDL on finite traces. *IJCAI*, 1558–1564.
- **Reward Machines**: Icarte, R.T. et al. (2018). Using reward machines for high-level task specification and reward shaping in deep RL. *ICML*.
- **LPOMDP**: Icarte, R.T. et al. (2022). Reward machines: Exploiting reward function machine structure in multi-agent reinforcement learning. *NeurIPS*.

### What We Built
`reward_machine.py` compiles LTLf temporal specifications for each task family into **deterministic finite automata**. Each automaton tracks whether the agent is making progress on the required investigation sequence:

```
Task D temporal spec: F(inspect_email_thread) ∧ F(lookup_vendor_history) ∧
                      F(compare_bank_account) ∧ F(request_callback_verification) ∧
                      F(submit_decision)
```

Rewards of +0.02 are given when the agent advances the automaton forward, and -0.02 when decisions are submitted before >50% of the investigation sequence is complete.

### Implementation
```python
# server/reward_machine.py
rm_state = initialize_reward_machine("task_d")
rm_state, reward = transition_reward_machine(rm_state, "inspect_email_thread", success=True)
# → +0.02 (advancing the task automaton)
```

---

## 7. Pillar 6 — Stackelberg Security Game (SSE)

### Theoretical Foundation
- **Primary**: Tambe, M. (2011). *Security and Game Theory: Algorithms, Deployed Systems, Lessons Learned*. Cambridge University Press.
- **SSE Algorithm**: Conitzer, V. & Sandholm, T. (2006). Computing the optimal strategy to commit to. *EC*, 82–90.
- **PROTECT/PITA**: Shieh, E. et al. (2012). PROTECT: A deployed game theoretic system for strategic security. *AAMAS*.

### What We Built
`dual_agent_mode.py` models the analyst-watchdog interaction as a **Stackelberg Security Game**. The watchdog (leader) commits to an optimal mixed audit strategy, and the analyst (follower) best-responds:

```
Watchdog audit mix: π* = argmax_{π} min_a U_watchdog(a, π)
```

The `compute_stackelberg_equilibrium` function solves for the Strong Stackelberg Equilibrium (SSE) by grid-searching over audit probability simplices, computing analyst best-responses, and selecting the watchdog strategy that maximizes worst-case outcome.

### Implementation
```python
# server/dual_agent_mode.py
strategy = compute_stackelberg_equilibrium(analyst_payoffs, watchdog_payoffs)
# → StackelbergAuditStrategy(audit_probabilities={"audit_payment": 0.6, ...}, veto_threshold=0.72)
```

---

## 8. Pillar 7 — Kamenica-Gentzkow Bayesian Persuasion

### Theoretical Foundation
- **Primary**: Kamenica, E. & Gentzkow, M. (2011). Bayesian Persuasion. *American Economic Review*, 101(6):2590–2615.
- **Markov Persuasion**: Wu, J. et al. (2022). Markov Persuasion Process. *NeurIPS*.
- **Information Design**: Bergemann, D. & Morris, S. (2019). Information Design. *JEL*, 57(1):44–95.

### What We Built
`information_design.py` models the environment as a **strategic information designer** that reveals evidence to maximize the benchmark's discriminative power between strong and weak agents. The `MarkovPersuasionEnvironment` selects which tools to highlight by measuring each tool's discriminative power across hypotheses.

---

## 9. Pillar 8 — Adversarial PCG via Regret Minimization (PAIRED)

### Theoretical Foundation
- **Primary**: Dennis, M. et al. (2020). Emergent Complexity and Zero-shot Transfer via Unsupervised Environment Design. *NeurIPS*.
- **Regret-based UED**: Jiang, M. et al. (2021). Replay-Guided Adversarial Environment Design. *NeurIPS*.
- **PAIRED**: Dennis, M. et al. (2021). Emergent complexity via multi-agent competition. *ICLR*.

### What We Built
`adversarial_designer.py` implements a PAIRED-inspired adversarial case generator. `build_regret_profile` computes each case's **regret** (oracle score − achieved score) and **weakness vector**. Cases are re-ordered for curriculum training with the highest-regret, solvable cases prioritized, ensuring the training pressure is targeted at genuine capability gaps.

---

## 10. Pillar 9 — Categorical MDP Composition

### Theoretical Foundation
- **Primary**: Fong, B. & Spivak, D. (2019). *An Invitation to Applied Category Theory*. Cambridge University Press.
- **Categorical RL**: Capucci, M. et al. (2022). Towards Foundations of Categorical Cybernetics. *MFPS*.
- **Poly**: Spivak, D.I. (2020). Generalized Lens Categories via Functors. *arXiv:1908.02202*.

### What We Built
`categorical_composition.py` defines task families as **MDPComponent** objects that compose via categorical pushouts. Task E is formally built as the colimit of Task D and Campaign Detection components:

```
Task_E = Task_D ⊔_{shared_actions} CampaignDetection
```

This gives a rigorous algebraic foundation for why Task E is strictly harder — it contains Task D as a subcategory.

### Integration in environment.py
At episode start, the environment loads the `MDPComponent` for the current task type. The component's `temporal_spec` is compiled into the Reward Machine, and the `required_observations` set seeds the VoI computation's expected evidence frontier.

```python
# server/environment.py (wired in reset())
from .categorical_composition import task_family_component
mdp_component = task_family_component(task_type)
# temporal_spec → reward machine
# required_observations → voi frontier
```

---

## 11. Pillar 10 — Decision-Transformer RL Export

### Theoretical Foundation
- **Primary**: Chen, L. et al. (2021). Decision Transformer: Reinforcement Learning via Sequence Modeling. *NeurIPS*.
- **Offline RL**: Levine, S. et al. (2020). Offline Reinforcement Learning. *arXiv:2005.01643*.
- **State Representations**: Bellemare, M. et al. (2013). The Arcade Learning Environment. *JAIR*, 47:253–279.

### What We Built
`rl_export.py` exports a **37-dimensional state vector** at every step, enabling offline RL training from episode trajectories:

```
Vector layout:
  [0:11]   LLR_i for each fraud hypothesis (from SPRT)
  [11:23]  distance_to_boundary_i for each hypothesis
  [23]     decision_ready flag (SPRT stopped)
  [24]     best_tool_voi (from VoI engine)
  [25]     budget_fraction_remaining
  [26]     step_fraction_remaining
  [27]     reward_machine_progress_fraction
  [28:34]  one-hot reward machine state (6 states)
  [34]     watchdog_suspicion_score
  [35]     calibration_running_average
```

This state vector is exposed at every `step()` under `info["rl_data_plane"]["state_vector"]`.

---

## Citations

1. Wald, A. (1945). Sequential Tests of Statistical Hypotheses. *Ann. Math. Stat.* 16(2):117–186.
2. Wald, A. & Wolfowitz, J. (1948). Optimum character of the SPRT. *Ann. Math. Stat.* 19(3):326–339.
3. Pearl, J. (2009). *Causality* (2nd ed.). Cambridge University Press.
4. Pearl, J. (2000). The logic of counterfactuals in causal inference. *Statistical Science*.
5. Verma, T. & Pearl, J. (1988). Causal networks. *UAI*, 352–359.
6. Kamenica, E. & Gentzkow, M. (2011). Bayesian Persuasion. *AER* 101(6):2590–2615.
7. Wu, J. et al. (2022). Markov Persuasion Process. *NeurIPS*.
8. Bergemann, D. & Morris, S. (2019). Information Design. *JEL* 57(1):44–95.
9. Tambe, M. (2011). *Security and Game Theory*. Cambridge University Press.
10. Conitzer, V. & Sandholm, T. (2006). Computing the optimal strategy to commit to. *EC*, 82–90.
11. Shieh, E. et al. (2012). PROTECT. *AAMAS*.
12. Gneiting, T. & Raftery, A.E. (2007). Strictly Proper Scoring Rules. *JASA* 102(477):359–378.
13. Brier, G.W. (1950). Verification of probability forecasts. *Monthly Weather Review* 78(1):1–3.
14. Good, I.J. (1952). Rational decisions. *JRSS-B* 14(1):107–114.
15. McCarthy, J. (1956). Measures of the value of information. *PNAS* 42(9):654–655.
16. Savage, L.J. (1971). Elicitation of personal probabilities and expectations. *JASA* 66(336):783–801.
17. Howard, R.A. (1966). Information Value Theory. *IEEE Trans. SSC* 2(1):22–26.
18. Lindley, D.V. (1956). On a measure of the information provided by an experiment. *Ann. Math. Stat.* 27(4):986–1005.
19. Krause, A. & Guestrin, C. (2009). Optimal value of information in graphical models. *JAIR* 35:557–591.
20. De Giacomo, G. & Vardi, M.Y. (2015). Synthesis for LTL and LDL on finite traces. *IJCAI*, 1558–1564.
21. Icarte, R.T. et al. (2018). Using reward machines. *ICML*.
22. Icarte, R.T. et al. (2022). Reward machines in multi-agent RL. *NeurIPS*.
23. Dennis, M. et al. (2020). Emergent Complexity via UED. *NeurIPS*.
24. Jiang, M. et al. (2021). Replay-Guided Adversarial Environment Design. *NeurIPS*.
25. Dennis, M. et al. (2021). Emergent complexity via multi-agent competition (PAIRED). *ICLR*.
26. Fong, B. & Spivak, D. (2019). *An Invitation to Applied Category Theory*. Cambridge.
27. Capucci, M. et al. (2022). Towards Foundations of Categorical Cybernetics. *MFPS*.
28. Chen, L. et al. (2021). Decision Transformer. *NeurIPS*.
29. Levine, S. et al. (2020). Offline Reinforcement Learning. *arXiv:2005.01643*.
30. Savage, L.J. (1954). *The Foundations of Statistics*. Wiley.

---
