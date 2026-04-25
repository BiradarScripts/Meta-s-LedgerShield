# LedgerShield Deep Dive — Missing Sections & Expansion Opportunities

**Analysis Date:** 2026-04-25  
**Document Analyzed:** `LEDGERSHIELD_EXHAUSTIVE_TECHNICAL_DEEP_DIVE_UPDATED.md` (597 lines)  
**Repo State:** 4 commits analyzed (`df53a65` → `bf345c6`)  
**Server Modules:** 41 Python files, ~14,403 total lines  
**Test Coverage:** 32 test files  

---

## Executive Summary

The current deep dive document is **well-structured and covers the major conceptual shifts** (ControlBench, FraudGen, Certify, institutional loss surface). However, it **lacks breadth and depth in several critical areas**:

1. **Missing file-by-file module documentation** — only 10 of 41 server modules are explicitly described
2. **Missing ControlBench implementation details** — authority gates, sleeper-vendor state machines, loss-surface computation
3. **Missing FraudGen technical details** — scenario typing, difficulty banding, solvability manifests, validation logic
4. **Missing Certify/Visualization API details** — deployability policies, red-team plans, graph payloads
5. **Missing test coverage narrative** — 32 test files barely mentioned
6. **Missing CI/CD and deployment details** — GitHub Actions workflow, Docker, validation pipeline
7. **Missing training/RL export details** — TRL SFT notebook, RL state vector, decision transformer export
8. **Missing root-level script documentation** — 10+ comparison/reporting scripts not covered
9. **Missing decision-falsifier and trust-graph technical details** — deterministic murder-board logic, TrustGraph projection
10. **Missing institutional-memory computation details** — loss-surface ratios, calibration-gate state machine, sleeper-vendor lifecycle

---

## Section 1: Missing Server Module Documentation

### Current Coverage
The deep dive explicitly documents:
- `server/app.py` (brief)
- `server/environment.py` (brief)
- `server/institutional_game.py` (moderate)
- `server/fraudgen.py` (moderate)
- `server/case_factory.py` (brief)
- `server/certify.py` (moderate)
- `server/visualization.py` (moderate)
- `server/trust_graph.py` (brief mention)
- `server/decision_falsifier.py` (brief mention)
- `server/control_statechart.py` (brief mention)

### Missing Detailed Coverage (31 modules)

#### Core Environment & State
- **`server/world_state.py`** — Hidden world construction, artifact scheduling, evidence graph initialization, campaign context, pressure-event sequencing
- **`server/schema.py`** — Observation/action/state dataclasses, reason codes, decision certificate graph schema, institutional metrics schema
- **`server/data_loader.py`** — Fixture loading, case indexing, vendor/ledger/email/PO/receipt/policy data structures

#### Investigation & Grading
- **`server/tools.py`** — 10+ investigation tools (zoom, ocr, lookup_vendor, inspect_email_thread, compare_bank_account, etc.), tool result normalization, domain-alignment inference, composite risk-flag logic
- **`server/grading.py`** — Task-specific rubrics (A/B/C/D/E), semantic counterfactual scoring, degenerate-evidence penalties, policy-completeness checks
- **`server/trajectory_grading.py`** — Investigation efficiency scoring, intervention-use scoring, calibration scoring, outcome scoring
- **`server/evidence_graph.py`** — Evidence node types, reveal logic, artifact dependencies, counterfactual evidence paths

#### Formal Methods (ASHTG Pillars)
- **`server/sprt_engine.py`** — Wald SPRT implementation, 12 hypothesis classes, 9 likelihood tables, boundary computation, optimal-stopping logic
- **`server/voi_engine.py`** — Value-of-Information calculation, myopic vs non-myopic planning, action-ranking frontier
- **`server/causal_model.py`** — Pearl SCM with 17 scenario templates, d-separation, counterfactual reasoning, do-calculus
- **`server/causal_grader.py`** — 3-level causal grading (association/intervention/counterfactual), causal-path verification
- **`server/proper_scoring.py`** — Brier score, log score, penalized score, calibration ECE, composite proper-scoring rules
- **`server/reward_machine.py`** — LTLf reward machines for all 5 task families, milestone tracking, temporal-progress rewards
- **`server/categorical_composition.py`** — Categorical MDP pushouts, task-family composition algebra, mdp_component field generation
- **`server/rl_export.py`** — 37-dimensional state vector, RL data plane, decision-transformer export format

#### Risk & Control
- **`server/risk_rules.py`** — Risk signal definitions, composite risk flags, bank-override-attempt logic, domain-alignment scoring
- **`server/attack_library.py`** — 16 adversarial attack templates, attack-profile matching, attack-difficulty scoring
- **`server/compliance_engine.py`** — SOX-style AP control evaluation, policy-rule matching, control-violation detection
- **`server/currency_engine.py`** — FX conversion, IBAN/SWIFT validation, currency-mismatch detection, aging-report support
- **`server/pressure_events.py`** — Pressure-event scheduling, urgency signals, deadline-driven behavior, attacker-belief updates

#### Institutional & Watchdog
- **`server/dual_agent_mode.py`** — Dec-POMDP watchdog/auditor mode, Stackelberg SSE, mixed-strategy audit policy, separation-of-duties enforcement
- **`server/information_design.py`** — Kamenica-Gentzkow Bayesian persuasion, information-structure design, belief-update incentives
- **`server/adversarial_designer.py`** — PAIRED regret-guided adversarial PCG, curriculum adaptation, procedural case generation
- **`server/curriculum.py`** — Dynamic difficulty adaptation, case-selection strategy, agent-strength profiling
- **`server/outcome_simulator.py`** — Downstream consequence simulation, fraud-loss computation, false-positive cost, operational burn
- **`server/vendor_simulator.py`** — Vendor behavior simulation, sleeper-vendor activation, bank-change patterns, BEC-attack sequences
- **`server/transition_engine.py`** — State-transition logic, artifact-reveal scheduling, evidence-accumulation mechanics
- **`server/human_baseline.py`** — Human-baseline profile loading, AP-analyst reference data, operational-realism anchoring
- **`server/benchmark_contract.py`** — Official tracks, latent-mechanism signatures, track labels, mechanism-family grouping

#### Decision & Audit
- **`server/decision_certificate.py`** — Decision Certificate Graph schema, artifact/observation/hypothesis/policy/intervention/decision/counterfactual nodes, verifier logic, support-path checking
- **`server/trust_graph.py`** — Compact TrustGraph projection, evidence/policy/authority/loss nodes, persistent projection, health summaries
- **`server/decision_falsifier.py`** — Deterministic murder-board diagnostics, unsafe-PAY detection, unsupported-claim detection, pending-artifact detection, certificate-failure detection
- **`server/control_statechart.py`** — Statechart-style control boundaries, prompt-injection-style premature-PAY prevention, authority-gate enforcement

---

## Section 2: Missing ControlBench Implementation Details

### What's Documented
- High-level framing: institutional loss surface, calibration-gated authority, sleeper-vendor vigilance
- Loss-surface dimensions (10 listed)
- Authority levels (4 listed)
- Sleeper-vendor states (warmup, trust-building, activation, detection)

### What's Missing

#### Loss-Surface Computation
- **Exact formula for normalized institutional loss score** — how are the 10 dimensions weighted?
- **Fraud-loss calculation** — how is fraud loss released vs prevented computed from case outcomes?
- **False-positive cost model** — what is the cost per false positive, and how does it scale?
- **Operational-delay penalty** — how is delay measured and penalized?
- **Manual-review burn** — how many review hours per case, and what is the hourly cost?
- **Supplier-friction model** — how does over-blocking vendors affect future vendor relationships?
- **Calibration-debt accumulation** — how does miscalibration compound over sequences?
- **Vigilance-loss penalty** — what is the cost of missing sleeper-vendor activations?
- **Authority-restriction rate** — how does poor performance trigger authority downgrades?
- **Catastrophic-event rate** — what constitutes a catastrophic event, and what is its cost?

#### Authority-Gate State Machine
- **Transition logic** — under what conditions does authority move from `full_authority` → `restricted_authority` → `review_only` → `locked`?
- **Recovery paths** — can authority be restored, and under what conditions?
- **Per-action authority checks** — which actions require which authority levels?
- **Threshold values** — what loss-surface thresholds trigger each downgrade?
- **Sequence-level vs case-level gates** — are gates applied per case or per AP-quarter sequence?

#### Sleeper-Vendor State Machine
- **Warmup phase** — how many cases before a sleeper vendor is considered "trusted"?
- **Trust-building phase** — what signals indicate successful trust-building?
- **Activation trigger** — what event (bank change, BEC, duplicate) triggers activation?
- **Detection logic** — what agent actions or observations can detect activation?
- **Penalty for missed detection** — how much loss is incurred if activation is not detected before unsafe PAY?
- **Sleeper-vendor lifecycle** — can a sleeper vendor return to warmup after detection?

#### ControlBench Sequence Generation
- **AP-quarter structure** — how are 100 cases distributed across 4 weeks?
- **Vendor-relationship continuity** — how are vendors reused across cases to build sleeper-vendor sequences?
- **Attacker-belief evolution** — how does the attacker model agent behavior and adapt?
- **Pressure-event scheduling** — when are deadline/urgency events injected?
- **Holdout vs public split** — what percentage of ControlBench cases are held out vs public?

#### Institutional-Memory Persistence
- **Memory scope** — is institutional memory per-sequence, per-agent, or per-benchmark-run?
- **Vendor-history tracking** — what vendor attributes are tracked across cases?
- **Authority-timeline recording** — how is the authority-level timeline persisted?
- **Loss-surface aggregation** — how are per-case losses aggregated into sequence-level metrics?

---

## Section 3: Missing FraudGen Technical Details

### What's Documented
- Scenario typing (sleeper_activation, campaign_fraud, duplicate_invoice, three_way_match_conflict, prompt_injection_fraud)
- Difficulty banding (easy, medium, hard, expert)
- Solvability manifests
- Independent ecosystem generation

### What's Missing

#### Scenario-Type Classification Logic
- **Exact decision tree** — how does `fraudgen_scenario_type()` classify cases?
- **Sleeper-phase detection** — how are warmup/trust-building/activation phases inferred?
- **Campaign-fraud detection** — what signals indicate coordinated fraud?
- **Prompt-injection detection** — what language patterns trigger prompt-injection classification?
- **Duplicate-family detection** — how are duplicate clusters identified?
- **Three-way-match conflict detection** — what PO/receipt/policy mismatches are detected?

#### Difficulty-Band Assignment
- **Scoring function** — how is difficulty_band_for_case() computed?
- **Signal weighting** — which signals (attack complexity, evidence obscurity, policy ambiguity) are weighted most?
- **Difficulty thresholds** — what score ranges map to easy/medium/hard/expert?
- **Task-family modulation** — do Task A cases have different difficulty ranges than Task E?

#### Solvability-Manifest Structure
- **Required tools** — which investigation tools must be called to solve the case?
- **Recommended interventions** — which interventions are most effective?
- **Revealable artifacts** — which hidden artifacts can be revealed, and in what order?
- **Minimum evidence hops** — what is the minimum number of tool calls to reach optimal evidence?
- **Proof-carrying requirements** — what decision-certificate nodes are required?

#### Validation Logic
- **Non-triviality checks** — how is it verified that a generated case is not trivially solvable?
- **Solvability verification** — does the validator actually run a solver to confirm solvability?
- **Artifact-dependency checks** — are artifact-reveal sequences validated?
- **Policy-completeness checks** — are all policy rules reachable?

#### FraudGen Ecosystem Independence
- **Vendor generation** — how are synthetic vendors created without curated-case sampling?
- **Invoice generation** — how are synthetic invoices generated with realistic fraud patterns?
- **Email-thread generation** — how are synthetic email threads created with BEC/spoofing patterns?
- **PO/receipt generation** — how are synthetic PO and receipt records created?
- **Ledger generation** — how is the synthetic ledger populated?

#### FraudGen Summary Statistics
- **Scenario-type distribution** — what percentage of generated cases fall into each scenario type?
- **Difficulty distribution** — what percentage are easy/medium/hard/expert?
- **Solvability statistics** — what is the mean/median minimum-evidence-hops across generated cases?
- **Attack-profile distribution** — which attack types are most common in generated cases?

---

## Section 4: Missing Certify & Visualization API Details

### What's Documented
- Deployability outcomes (6 levels: unsafe → high_trust)
- Certification status (fail, conditional_fail, conditional, conditional_pass, pass)
- Authority recommendations
- Red-team plan, monitoring requirements, limitations

### What's Missing

#### Deployability-Policy Mapping
- **Exact policy per rating** — what are the full policy dictionaries for each deployability level?
- **Authority-action mapping** — which actions are allowed at each authority level?
- **Threshold values** — what loss-surface thresholds trigger each deployability rating?
- **Transition logic** — how does an agent move from one deployability level to another?
- **Recovery conditions** — what must an agent do to improve its deployability rating?

#### Red-Team Plan Generation
- **Attack vectors** — what specific attacks are recommended for each deployability level?
- **Test-case generation** — how are red-team test cases generated?
- **Failure-mode detection** — what failure modes should be tested?
- **Monitoring requirements** — what metrics should be monitored post-deployment?

#### Certification-Report Structure
- **Control-profile metrics** — what metrics are included in the control profile?
- **Loss-surface breakdown** — how is the loss surface visualized in the report?
- **Authority timeline** — how is the authority-level timeline presented?
- **Certificate-gate comparison** — how are agent-authored vs synthesized certificates compared?
- **TrustGraph health** — what health metrics are computed for the TrustGraph?

#### Visualization-Payload Generation
- **Accuracy vs loss profile** — how are accuracy and institutional loss plotted?
- **Authority-timeline rows** — what data is included in each timeline row?
- **Loss-surface chart rows** — how is the 10-dimensional loss surface reduced to 2D?
- **Certificate-gate comparison payloads** — what data is included in the comparison?
- **TrustGraph-health summaries** — what health metrics are computed?
- **Demo-script generation** — what demo scripts are generated for presentations?

#### Graph-Layer Descriptions
- **Node types** — what node types are included in the visualization graph?
- **Edge types** — what edge types represent relationships?
- **Styling rules** — how are nodes/edges styled based on metrics?
- **Interactivity** — what interactions are supported (hover, click, zoom)?

---

## Section 5: Missing Test Coverage Narrative

### Current Mention
- Brief list of test files (7 mentioned)
- Newer test themes (6 bullet points)

### Missing Details

#### Test File Breakdown (32 files)
**Core Environment Tests:**
- `test_ashtg_environment.py` — ASHTG environment loop, SPRT/VoI/reward-machine integration
- `test_ledgershield_env.py` — OpenEnv compatibility, reset/step/state contracts
- `test_api_smoke.py` — API endpoint smoke tests, response envelope validation

**Formal Methods Tests:**
- `test_sprt_engine.py` — SPRT boundary computation, optimal-stopping logic, hypothesis-class coverage
- `test_voi_engine.py` — VoI calculation, action-ranking frontier, myopic vs non-myopic planning
- `test_causal_model.py` — SCM construction, d-separation, counterfactual reasoning
- `test_causal_grader.py` — 3-level causal grading, causal-path verification
- `test_proper_scoring.py` — Brier/log/penalized scoring, calibration ECE, composite rules
- `test_reward_machine.py` — LTLf reward machines, milestone tracking, temporal-progress rewards
- `test_categorical.py` — Categorical MDP composition, pushout algebra, mdp_component generation
- `test_rl_export.py` — 37-dimensional state vector, RL data plane, decision-transformer export
- `test_stackelberg.py` — Stackelberg SSE, mixed-strategy audit policy, watchdog mode

**Risk & Control Tests:**
- `test_grading.py` — Task-specific rubrics, semantic counterfactual scoring, degenerate-evidence penalties
- `test_compliance_engine.py` — SOX-style AP control evaluation, policy-rule matching
- `test_currency_engine.py` — FX conversion, IBAN/SWIFT validation, currency-mismatch detection
- `test_adversarial_designer.py` — PAIRED PCG, curriculum adaptation, procedural case generation
- `test_curriculum.py` — Dynamic difficulty adaptation, case-selection strategy
- `test_information_design.py` — Bayesian persuasion, information-structure design

**Institutional & Watchdog Tests:**
- `test_institutional_game.py` — Institutional memory, loss-surface computation, authority gates, sleeper-vendor states
- `test_controlbench.py` — ControlBench sequence generation, authority-gate enforcement, sleeper-vendor logic, FraudGen validation

**Decision & Audit Tests:**
- `test_decision_certificate.py` — Decision Certificate Graph schema, verifier logic, support-path checking
- `test_submission_hardening.py` — Submission validation, decision-falsifier diagnostics, control-boundary enforcement

**Inference Tests:**
- `test_inference_contract.py` — Inference API contract, submission format, output validation
- `test_inference_runtime.py` — Inference runtime behavior, tool-call sequencing, decision-making logic
- `test_inference_llm_powered.py` — LLM-powered agent behavior, planning traces, repair logic

**Guardrail Tests:**
- `test_task_c_guardrails.py` — Task C output validation, duplicate detection, bank-account verification
- `test_task_d_guardrails.py` — Task D output validation, email-thread parsing, vendor verification

**Reporting & Comparison Tests:**
- `test_benchmark_report.py` — Benchmark report generation, ControlBench report, holdout/contrastive reporting
- `test_compare_models_live.py` — Live model comparison, capability profiles, monotonic-strength ordering
- `test_compare_all_models.py` — Broader model comparison harness, batch evaluation

**Schema Tests:**
- `test_schema_reason_codes.py` — Reason-code validation, schema compliance

#### Test Coverage Gaps
- **Missing: FraudGen validation tests** — no explicit test for fraudgen_scenario_type(), difficulty_band_for_case(), solvability_manifest validation
- **Missing: Certify API tests** — no explicit test for build_certify_report(), deployability-policy mapping
- **Missing: Visualization API tests** — no explicit test for build_controlbench_visualization(), graph-payload generation
- **Missing: Trust-graph tests** — no explicit test for TrustGraph projection, health-metric computation
- **Missing: Decision-falsifier tests** — no explicit test for falsify_decision(), murder-board diagnostics
- **Missing: Control-statechart tests** — no explicit test for control-boundary enforcement, prompt-injection prevention

#### Test Execution & CI
- **Test runner configuration** — pytest config in pyproject.toml (asyncio mode, markers, deprecation filters)
- **CI workflow** — GitHub Actions workflow in `.github/workflows/ci.yml` (pytest, Docker build, metadata validation)
- **Test markers** — what markers are used (unit, integration, slow, etc.)?
- **Coverage targets** — what is the target code coverage percentage?

---

## Section 6: Missing CI/CD & Deployment Details

### What's Documented
- Brief mention of GitHub Actions workflow
- Docker image mentioned
- Validation script mentioned

### What's Missing

#### GitHub Actions Workflow (`.github/workflows/ci.yml`)
- **Trigger conditions** — on push, PR, schedule, manual?
- **Job matrix** — what Python versions, OS versions are tested?
- **Test job steps** — exact pytest invocation, coverage reporting, artifact upload
- **Docker build job** — Dockerfile build, image tagging, registry push
- **Validation job** — validate-submission.sh invocation, metadata sync, artifact generation
- **Failure handling** — what happens on test failure, build failure, validation failure?
- **Artifact retention** — what artifacts are retained (test reports, coverage, Docker images)?

#### Dockerfile
- **Base image** — what Python version, OS?
- **Dependencies** — how are requirements.txt, pyproject.toml dependencies installed?
- **Entry point** — what is the default command?
- **Port exposure** — what port is exposed for the FastAPI server?
- **Health check** — is there a health-check endpoint?
- **Volume mounts** — what volumes are mounted for fixtures, artifacts?

#### Validation Pipeline (`validate-submission.sh`)
- **Smoke tests** — what smoke tests are run?
- **Contract validation** — what contracts are validated (OpenEnv, API, schema)?
- **Artifact generation** — what artifacts are generated (benchmark report, live comparison)?
- **Metadata sync** — what metadata is synced (README, docs, openenv.yaml)?
- **Exit codes** — what exit codes indicate success/failure?

#### Deployment Targets
- **Local deployment** — how to run locally with `python -m server.app`?
- **Docker deployment** — how to build and run the Docker image?
- **HuggingFace Spaces deployment** — how to deploy to HF Spaces?
- **Environment configuration** — what environment variables are required (API_BASE_URL, MODEL_NAME, HF_TOKEN, ENV_URL)?

---

## Section 7: Missing Training & RL Export Details

### What's Documented
- Brief mention of RL state export (37-dimensional vector)
- Brief mention of decision-transformer export format

### What's Missing

#### TRL SFT Training Notebook
- **Notebook path** — `training/LedgerShield_v2_TRL_SFT_Training.ipynb`
- **Training data** — how are episode traces collected and formatted?
- **Model architecture** — what base model is used (GPT-2, Llama, etc.)?
- **Training hyperparameters** — learning rate, batch size, epochs, warmup steps?
- **Loss function** — what loss function is used (cross-entropy, DPO, etc.)?
- **Evaluation metrics** — how is the trained model evaluated?
- **Colab compatibility** — what Colab-specific setup is required?

#### RL State Vector (37-dimensional)
- **Vector components** — what are the 37 dimensions?
  - SPRT belief state (how many dimensions?)
  - VoI frontier (how many dimensions?)
  - Reward-machine progress (how many dimensions?)
  - Watchdog suspicion (how many dimensions?)
  - Calibration history (how many dimensions?)
  - Other institutional metrics (how many dimensions?)
- **Normalization** — how are values normalized (0-1, z-score, etc.)?
- **Temporal encoding** — how is temporal information encoded?
- **Categorical encoding** — how are categorical variables encoded?

#### Decision-Transformer Export
- **Format** — what is the exact format of the exported data?
- **Trajectory structure** — how are trajectories structured (state, action, reward, next_state)?
- **Sequence length** — what is the typical sequence length?
- **Padding strategy** — how are variable-length sequences padded?
- **Batch format** — how are batches formatted for training?

#### Minimal TRL SFT Script
- **Script path** — `training/minimal_trl_sft.py`
- **Purpose** — what is the minimal viable training script?
- **Dependencies** — what TRL/transformers versions are required?
- **Usage** — how is the script invoked?

#### Plot Before/After Script
- **Script path** — `training/plot_before_after.py`
- **Purpose** — what metrics are plotted?
- **Input data** — what data format is expected?
- **Output format** — what plot format is generated?

---

## Section 8: Missing Root-Level Script Documentation

### What's Documented
- `benchmark_report.py` (brief)
- `compare_models_live.py` (brief)
- `sync_benchmark_metadata.py` (brief)
- `inference.py` (brief)

### What's Missing

#### Comparison & Reporting Scripts
- **`compare_all_models.py`** — broader model comparison harness, batch evaluation, result aggregation
- **`generate_artifacts.py`** — artifact generation pipeline, fixture creation, case generation
- **`generate_branch_comparison_report.py`** — branch-level comparison, commit-level metrics
- **`generate_comparison_report.py`** — comparison report generation, model-vs-model analysis
- **`generate_final_report.py`** — final report generation, summary statistics
- **`generate_sota_report.py`** — state-of-the-art report, benchmark leaderboard

#### Validation & Debugging Scripts
- **`find_codec.py`** — codec discovery/validation script
- **`find_crash.py`** — crash-log analysis script
- **`test_score.py`** — score validation script
- **`test_scoring.py`** — scoring logic validation script
- **`validate_agent_grading.py`** — agent grading validation
- **`validate_grader.py`** — grader validation

#### Inference Variants
- **`inference_improved.py`** — experimental improved agent entrypoint
- **`inference_llm_powered.py`** — richer LLM-powered agent (already mentioned but not detailed)

#### LLM Utilities
- **`llm_utils.py`** — JSON parsing, chat wrapper utilities (mentioned but not detailed)
- **`llm_judge_grader.py`** — optional LLM-as-judge grading experiments

#### Environment Compatibility
- **`ledgershield_env.py`** — compatibility re-export shim
- **`openenv_compat.py`** — OpenEnv compatibility + lazy FastAPI fallback

#### Models & Client
- **`models.py`** — shared dataclasses, Pydantic reward model (mentioned but not detailed)
- **`client.py`** — HTTP client wrapper (mentioned but not detailed)

---

## Section 9: Missing Decision-Falsifier & Trust-Graph Technical Details

### What's Documented
- Brief mention of deterministic murder-board diagnostics
- Brief mention of TrustGraph projection
- Brief mention of control-boundary enforcement

### What's Missing

#### Decision-Falsifier Logic
- **Unsafe-PAY detection** — what conditions trigger unsafe-PAY detection?
- **Unsupported-claim detection** — what claims are considered unsupported?
- **Pending-artifact detection** — what pending artifacts block PAY decisions?
- **Certificate-failure detection** — what certificate failures are detected?
- **Falsification verdict** — what is the exact verdict structure?
- **Diagnostic output** — what diagnostic information is returned?

#### TrustGraph Projection
- **Node types** — case, invoice, vendor, evidence, policy, certificate, authority, loss-surface
- **Edge types** — what relationships are represented?
- **Projection logic** — how is the full case state projected into the TrustGraph?
- **Health metrics** — what health metrics are computed?
- **Persistence** — how is the TrustGraph persisted across sequences?
- **Visualization** — how is the TrustGraph visualized?

#### Control-Statechart Enforcement
- **State machine** — what are the states and transitions?
- **Prompt-injection prevention** — how are prompt-injection-style premature-PAY attempts blocked?
- **Authority-gate enforcement** — how are authority levels enforced?
- **Boundary violations** — what happens when a boundary is violated?
- **Recovery paths** — can the agent recover from a boundary violation?

---

## Section 10: Missing Institutional-Memory Computation Details

### What's Documented
- 10 loss-surface dimensions listed
- Authority levels listed
- Sleeper-vendor states listed
- Brief mention of loss-surface ratios

### What's Missing

#### Loss-Surface Computation
- **Fraud-loss-released formula** — how is fraud loss released computed?
- **Fraud-loss-prevented formula** — how is fraud loss prevented computed?
- **False-positive-cost formula** — how is false-positive cost computed?
- **Operational-delay formula** — how is operational delay computed?
- **Manual-review-burn formula** — how is manual-review burn computed?
- **Supplier-friction formula** — how is supplier friction computed?
- **Calibration-debt formula** — how is calibration debt computed?
- **Vigilance-loss formula** — how is vigilance loss computed?
- **Authority-restriction-rate formula** — how is authority-restriction rate computed?
- **Catastrophic-event-rate formula** — how is catastrophic-event rate computed?
- **Normalization** — how are the 10 dimensions normalized into a single score?

#### Calibration-Gate State Machine
- **State variables** — what state variables track calibration?
- **Update logic** — how is calibration state updated after each case?
- **Threshold values** — what thresholds trigger authority downgrades?
- **Recovery logic** — how can calibration state improve?
- **Sequence-level aggregation** — how is calibration aggregated over sequences?

#### Sleeper-Vendor State Machine
- **State variables** — what state variables track sleeper-vendor status?
- **Warmup phase** — how many cases before trust-building?
- **Trust-building phase** — what signals indicate successful trust-building?
- **Activation trigger** — what event triggers activation?
- **Detection logic** — what agent actions can detect activation?
- **Penalty computation** — how is penalty for missed detection computed?
- **Lifecycle** — can sleeper vendors return to warmup after detection?

#### Vendor-Institutional-Memory
- **Tracked attributes** — what vendor attributes are tracked?
- **History depth** — how many historical cases are tracked per vendor?
- **Update logic** — how is vendor memory updated after each case?
- **Persistence** — how is vendor memory persisted across sequences?

#### Institutional-Loss-Ledger
- **Ledger structure** — how is the ledger organized?
- **Entry types** — what types of entries are recorded?
- **Aggregation** — how are entries aggregated into loss-surface dimensions?
- **Reporting** — how is the ledger reported in benchmark reports?

---

## Section 11: Missing End-to-End Flow Details

### What's Documented
- 4 phases (Boot, Reset, Investigation Loop, Submission)
- Brief description of each phase

### What's Missing

#### Phase 0: Boot (Detailed)
- **Fixture loading** — how are fixtures loaded and indexed?
- **Curriculum initialization** — how is the curriculum initialized?
- **Institutional-memory initialization** — how is institutional memory initialized?
- **Benchmark-artifact loading** — how are benchmark artifacts loaded lazily?
- **Server startup** — what happens during server startup?

#### Phase 1: Reset (Detailed)
- **Case selection** — how is a case selected (curated vs generated)?
- **Benchmark-contract attachment** — how is benchmark metadata attached?
- **Hidden-world construction** — how is the hidden world constructed?
- **Evidence-graph initialization** — how is the evidence graph initialized?
- **SPRT initialization** — how is SPRT state initialized?
- **Reward-machine initialization** — how is reward-machine state initialized?
- **Watchdog initialization** — how is watchdog state initialized?
- **Institutional-context attachment** — how is institutional context attached?
- **Public-observation generation** — how is the public observation generated?

#### Phase 2: Investigation Loop (Detailed)
- **Tool-call handling** — how are tool calls validated and executed?
- **Result normalization** — how are tool results normalized?
- **SPRT update** — how is SPRT state updated?
- **Risk-signal update** — how are risk signals updated?
- **Budget update** — how is the investigation budget updated?
- **Trajectory update** — how is the trajectory updated?
- **Artifact-reveal scheduling** — how are pending artifacts revealed?
- **Pressure-event advancement** — how are pressure events advanced?
- **Reward-shaping computation** — how is reward shaping computed?
- **Next-observation generation** — how is the next observation generated?

#### Phase 3: Submission (Detailed)
- **Decision validation** — how is the final decision validated?
- **Predicted-probability normalization** — how are predicted probabilities normalized?
- **Decision-certificate verification** — how is the decision certificate verified?
- **Outcome simulation** — how are downstream consequences simulated?
- **Compliance evaluation** — how is compliance evaluated?
- **Task grading** — how is task-specific grading performed?
- **Institutional-memory update** — how is institutional memory updated?
- **Authority-gate evaluation** — how is authority-gate evaluation performed?
- **Falsifier diagnostics** — how are falsifier diagnostics computed?
- **TrustGraph projection** — how is the TrustGraph projected?
- **Control-boundary enforcement** — how is control-boundary enforcement performed?
- **Terminal-score computation** — how is the terminal score computed?
- **Info-payload generation** — how is the info payload generated?

#### Phase 4: Reporting (Detailed)
- **Benchmark-report generation** — how is the benchmark report generated?
- **ControlBench-report generation** — how is the ControlBench report generated?
- **Holdout-report generation** — how is the holdout report generated?
- **Certify-report generation** — how is the certify report generated?
- **Visualization-payload generation** — how is the visualization payload generated?
- **Artifact persistence** — how are artifacts persisted?

---

## Section 12: Missing Formal Methods Details

### What's Documented
- Brief mention of ASHTG framework
- 5 mathematical pillars listed
- 5 additional innovations listed

### What's Missing

#### SPRT Implementation Details
- **Hypothesis classes** — what are the 12 hypothesis classes?
- **Likelihood tables** — what are the 9 likelihood tables?
- **Boundary computation** — how are the upper and lower boundaries computed?
- **Optimal-stopping logic** — how is optimal stopping determined?
- **Posterior-probability computation** — how are posterior probabilities computed?
- **Belief-entropy computation** — how is belief entropy computed?
- **Distance-to-boundary computation** — how is distance to boundary computed?

#### VoI Implementation Details
- **VoI formula** — what is the exact VoI formula?
- **Myopic planning** — how is myopic planning performed?
- **Non-myopic planning** — how is non-myopic planning performed?
- **Action-ranking frontier** — how is the action-ranking frontier computed?
- **Budget constraints** — how are budget constraints incorporated?

#### Causal-Model Implementation Details
- **SCM structure** — what is the structure of the SCM?
- **17 scenario templates** — what are the 17 scenario templates?
- **D-separation** — how is d-separation computed?
- **Counterfactual reasoning** — how are counterfactuals computed?
- **Do-calculus** — how is do-calculus applied?

#### Proper-Scoring Implementation Details
- **Brier score** — how is Brier score computed?
- **Log score** — how is log score computed?
- **Penalized score** — how is penalized score computed?
- **Calibration ECE** — how is calibration ECE computed?
- **Composite scoring** — how are multiple scores combined?

#### Reward-Machine Implementation Details
- **LTLf formulas** — what are the LTLf formulas for each task family?
- **Milestone tracking** — how are milestones tracked?
- **Temporal-progress rewards** — how are temporal-progress rewards computed?
- **Reward aggregation** — how are rewards aggregated?

#### Categorical-Composition Implementation Details
- **Pushout algebra** — how is the pushout computed?
- **Task-family composition** — how are task families composed?
- **MDP-component generation** — how is the mdp_component field generated?

#### RL-Export Implementation Details
- **State-vector construction** — how is the 37-dimensional state vector constructed?
- **RL data plane** — what is the structure of the RL data plane?
- **Decision-transformer export** — how is the decision-transformer export formatted?

---

## Section 13: Missing Benchmark-Quality & Evaluation Details

### What's Documented
- Brief mention of 21 curated cases
- Brief mention of 5 task families
- Brief mention of holdout/contrastive generalization

### What's Missing

#### Case Curation & Auditing
- **Case-selection criteria** — how were the 21 cases selected?
- **Case-audit process** — how were cases audited for quality?
- **Latent-mechanism metadata** — what latent-mechanism metadata is attached to each case?
- **Track assignment** — how are cases assigned to official tracks?
- **Difficulty assessment** — how is case difficulty assessed?
- **Solvability verification** — how is case solvability verified?

#### Holdout & Contrastive Reporting
- **Holdout selection** — how are holdout cases selected?
- **Contrastive-pair generation** — how are benign twins generated?
- **Mechanism-aware reporting** — how is reporting mechanism-aware?
- **Generalization metrics** — what generalization metrics are computed?

#### Benchmark-Contract Enforcement
- **Official tracks** — what are the 9 official tracks?
- **Track definitions** — how is each track defined?
- **Track-specific metrics** — what metrics are specific to each track?
- **Track-specific evaluation** — how is evaluation track-specific?

#### Headline Metrics Computation
- **control_satisfied_resolution** — how is this computed?
- **institutional_utility** — how is this computed?
- **institutional_loss_score** — how is this computed?
- **loss_surface** — how is this computed?
- **authority_level** — how is this computed?
- **sleeper_detection_rate** — how is this computed?
- **certificate_required_mean** — how is this computed?
- **adversarial_falsifier_verdict** — how is this computed?
- **human_baseline_track** — how is this computed?
- **unsafe_release_rate** — how is this computed?
- **result_class** — how is this computed?

---

## Section 14: Missing Artifact & Generated-Data Details

### What's Documented
- Fixture directory structure (8 JSON files)
- Brief mention of generated data sources

### What's Missing

#### Fixture Structure Details
- **`cases.json`** — case schema, field descriptions, example case
- **`vendors.json`** — vendor schema, field descriptions, example vendor
- **`vendor_history.json`** — vendor-history schema, field descriptions
- **`ledger_index.json`** — ledger-index schema, field descriptions
- **`email_threads.json`** — email-thread schema, field descriptions
- **`po_records.json`** — PO-record schema, field descriptions
- **`receipts.json`** — receipt schema, field descriptions
- **`policy_rules.json`** — policy-rule schema, field descriptions

#### Generated-Data Pipeline
- **Curated-case variants** — how are variants generated from curated cases?
- **Challenge-case generation** — how are challenge cases generated?
- **Benign-twin generation** — how are benign twins generated?
- **Holdout-case generation** — how are holdout cases generated?
- **ControlBench-sequence generation** — how are ControlBench sequences generated?
- **FraudGen-ecosystem generation** — how are independent FraudGen ecosystems generated?

#### Artifact Persistence
- **Benchmark-report artifacts** — where are benchmark reports stored?
- **ControlBench-report artifacts** — where are ControlBench reports stored?
- **Live-comparison artifacts** — where are live-comparison results stored?
- **Certify-report artifacts** — where are certify reports stored?
- **Visualization-payload artifacts** — where are visualization payloads stored?

---

## Section 15: Missing Configuration & Environment Details

### What's Documented
- Brief mention of environment variables (API_BASE_URL, MODEL_NAME, HF_TOKEN, ENV_URL)
- Brief mention of openenv.yaml

### What's Missing

#### Environment Variables
- **API_BASE_URL** — what is the default value? What endpoints are supported?
- **MODEL_NAME** — what models are supported? What is the default?
- **HF_TOKEN** — what is this used for? Is it required?
- **ENV_URL** — what is the default value? What is this used for?
- **Other variables** — are there other environment variables?

#### Configuration Files
- **`openenv.yaml`** — what is the structure? What fields are required?
- **`pyproject.toml`** — what is the structure? What dependencies are listed?
- **`requirements.txt`** — what are the pinned versions?
- **`.gitignore`** — what files are ignored?
- **`.dockerignore`** — what files are ignored in Docker?

#### Pytest Configuration
- **Asyncio mode** — what asyncio mode is used?
- **Markers** — what markers are defined?
- **Deprecation filters** — what deprecation warnings are filtered?
- **Test discovery** — how are tests discovered?

---

## Summary of Missing Breadth & Depth

| Category | Current Coverage | Missing Coverage | Priority |
|---|---|---|---|
| Server modules | 10 of 41 | 31 modules | **HIGH** |
| ControlBench details | High-level | Loss-surface computation, authority gates, sleeper-vendor SM | **HIGH** |
| FraudGen details | High-level | Scenario typing, difficulty banding, solvability validation | **HIGH** |
| Certify/Visualization | High-level | Deployability policies, red-team plans, graph payloads | **HIGH** |
| Test coverage | 7 files mentioned | 32 files total, detailed coverage gaps | **MEDIUM** |
| CI/CD & deployment | Brief mention | GitHub Actions, Docker, validation pipeline | **MEDIUM** |
| Training & RL export | Brief mention | TRL notebook, 37-dim state vector, decision-transformer | **MEDIUM** |
| Root-level scripts | 4 scripts mentioned | 10+ scripts missing | **MEDIUM** |
| Decision-falsifier & trust-graph | Brief mention | Detailed logic, node/edge types, health metrics | **MEDIUM** |
| Institutional-memory computation | High-level | Loss-surface formulas, calibration SM, sleeper-vendor SM | **HIGH** |
| End-to-end flow | 4 phases | Detailed step-by-step logic for each phase | **MEDIUM** |
| Formal methods | Pillar names | SPRT/VoI/SCM/proper-scoring/reward-machine details | **MEDIUM** |
| Benchmark quality | Brief mention | Case curation, holdout selection, metric computation | **MEDIUM** |
| Artifacts & data | Fixture list | Fixture schemas, generated-data pipeline | **MEDIUM** |
| Configuration | Brief mention | Environment variables, config files, pytest config | **LOW** |

---

## Recommendations for Expansion

### Tier 1: Critical Additions (High Priority)
1. **File-by-file server module documentation** — add 1-2 paragraph descriptions for all 41 modules
2. **ControlBench implementation details** — add loss-surface computation formulas, authority-gate state machine, sleeper-vendor state machine
3. **FraudGen technical details** — add scenario-type classification logic, difficulty-band assignment, solvability-manifest structure, validation logic
4. **Institutional-memory computation** — add loss-surface formulas, calibration-gate state machine, sleeper-vendor state machine
5. **Decision-falsifier & trust-graph details** — add deterministic murder-board logic, TrustGraph projection, control-statechart enforcement

### Tier 2: Important Additions (Medium Priority)
6. **Test coverage narrative** — add detailed breakdown of all 32 test files with coverage gaps
7. **CI/CD & deployment details** — add GitHub Actions workflow, Docker, validation pipeline
8. **Training & RL export details** — add TRL notebook, 37-dim state vector, decision-transformer export
9. **Root-level script documentation** — add 10+ comparison/reporting scripts
10. **End-to-end flow details** — add detailed step-by-step logic for each phase

### Tier 3: Supporting Additions (Lower Priority)
11. **Formal methods details** — add SPRT/VoI/SCM/proper-scoring/reward-machine implementation details
12. **Benchmark-quality details** — add case curation, holdout selection, metric computation
13. **Artifact & data details** — add fixture schemas, generated-data pipeline
14. **Configuration details** — add environment variables, config files, pytest config

---

## Estimated Expansion Size

- **Current document:** 597 lines (~50 minutes reading time)
- **Tier 1 additions:** ~1,500 lines (file-by-file modules, ControlBench, FraudGen, institutional-memory, decision-falsifier)
- **Tier 2 additions:** ~1,000 lines (tests, CI/CD, training, scripts, end-to-end flow)
- **Tier 3 additions:** ~800 lines (formal methods, benchmark quality, artifacts, configuration)
- **Total expanded document:** ~3,900 lines (~3+ hours reading time)

---

## Conclusion

The current deep dive is a **solid high-level overview** of the ControlBench evolution and major architectural shifts. However, it **lacks the breadth and depth** needed for:

1. **Developers** implementing new features or debugging issues
2. **Researchers** understanding the formal methods and evaluation pipeline
3. **Operators** deploying and monitoring the system
4. **Auditors** verifying the benchmark quality and evaluation integrity

An expanded version addressing the Tier 1 and Tier 2 recommendations would provide a **comprehensive technical reference** suitable for all stakeholder groups.
