# Changelog

All notable changes to LedgerShield will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive industry-standard documentation
- New docs/ folder with detailed guides
- API reference documentation
- Architecture documentation with data flow diagrams
- Task reference with scoring breakdowns
- Development guide for contributors
- Deployment guide for production use

### Changed
- `compare_models_live.py` now records per-model capability profiles, runtime context, configurable case lists, and monotonic strength-order checks in `live_model_comparison.json`

### Fixed
- `server/grading.py` now correctly applies `DEGENERATE_EVIDENCE_CAP` to empty evidence submissions instead of collapsing that path to `0.0`

### Notes
- Local verification for this patch covered targeted `pytest` suites and bytecode compilation in the current shell. A fresh live `compare_models_live.py` API run and Docker-backed end-to-end reproduction were not executed as part of this patch.

## [0.1.0] - 2026-04-07

### Added
- Initial release of LedgerShield
- 5 task families (A-E) with 12 curated benchmark cases
- 14 deterministic challenge variants
- FastAPI-based OpenEnv-compatible server
- POMDP-based environment model
- Partial observability with hidden state
- Investigation tools (11 actions)
- Intervention system (9 actions)
- Trajectory-based grading system
- Potential-based reward shaping (PBRS)
- Adversarial case generation via attack library
- Vendor callback simulation (Dec-POMDP extension)
- Mid-episode pressure events
- Contrastive calibration grading
- Downstream outcome simulation
- Baseline inference agent
- Benchmark reporting tools
- Docker containerization
- Hugging Face Space deployment support
- Comprehensive test suite
- JSON fixtures for test data

### Task Families

#### Task A: Proof-Carrying Field Extraction
- Invoice field extraction with evidence mapping
- Line item extraction
- 2 benchmark cases

#### Task B: Three-Way Match Decisioning
- PO/receipt reconciliation
- Discrepancy detection
- Policy compliance checking
- 3 benchmark cases

#### Task C: Duplicate and Fraud Triage
- Ledger search for duplicates
- Bank account validation
- Fraud escalation
- 2 benchmark cases

#### Task D: AP Inbox Incident Triage
- Email analysis for spoofing
- Multi-hop reasoning
- Counterfactual reasoning
- Pressure event resistance
- 4 benchmark cases

#### Task E: Campaign-Level Detection
- Multi-invoice analysis
- Threshold evasion detection
- Cross-invoice linking
- 1 expert-level benchmark case

### Environment Features
- Budget constraints per episode
- Step limits per case
- Delayed artifact reveal
- Tool cost structure
- Risk signal tracking
- Decision readiness scoring

### Grading Components
- Task-specific scoring
- Trajectory quality metrics
- Investigation coverage
- Intervention quality
- Calibration scoring
- Efficiency metrics
- Downstream outcomes

### Tools Available
- `zoom` - Document region inspection
- `get_doc_crop` - Cropped region extraction
- `ocr` - Text extraction (fast/accurate modes)
- `lookup_vendor` - Vendor master lookup
- `lookup_vendor_history` - Historical changes
- `lookup_policy` - Policy rule lookup
- `lookup_po` - Purchase order lookup
- `lookup_receipt` - Goods receipt lookup
- `search_ledger` - Duplicate payment search
- `inspect_email_thread` - Email analysis
- `compare_bank_account` - Bank validation

### Interventions Available
- `request_callback_verification` - Vendor callback
- `freeze_vendor_profile` - Account freeze
- `request_bank_change_approval_chain` - Bank change approval
- `request_po_reconciliation` - PO reconciliation
- `request_additional_receipt_evidence` - Additional receipts
- `route_to_procurement` - Route to procurement
- `route_to_security` - Security escalation
- `flag_duplicate_cluster_review` - Duplicate review
- `create_human_handoff` - Manual review handoff

### Attack Patterns
- Bank override attacks
- Near-duplicate invoice attacks
- Vendor takeover attacks
- Urgency spoof attacks
- Approval threshold evasion
- Workflow override attacks
- Fake receipt attacks

### API Endpoints
- `POST /reset` - Initialize episode
- `POST /step` - Execute action
- `GET /state` - Get current state
- `GET /health` - Health check
- `GET /leaderboard` - Benchmark results
- `GET /benchmark-report` - Detailed report

### Documentation
- README with quick start
- Inline code documentation
- Docstrings for public APIs
- Example usage in tests

### Testing
- Unit tests for core functions
- Integration tests for environment
- API smoke tests
- Benchmark validation tests
- Grader validation

### Deployment
- Dockerfile for containerization
- Docker Compose configuration
- Systemd service example
- Kubernetes deployment manifest
- Nginx reverse proxy config
- Hugging Face Spaces support

### Development Tools
- pytest test runner
- Black code formatter (recommended)
- Type hints throughout
- Development documentation

## Future Roadmap

### Planned Features
- [ ] Additional task families (F, G)
- [ ] More benchmark cases
- [ ] WebSocket support for real-time updates
- [ ] REST API rate limiting
- [ ] Prometheus metrics export
- [ ] Distributed episode execution
- [ ] Multi-agent support
- [ ] Custom attack pattern builder
- [ ] Case difficulty auto-calibration
- [ ] Performance profiling tools

### Under Consideration
- [ ] GPU-accelerated OCR
- [ ] Vector database integration for ledger search
- [ ] LLM-based case generation
- [ ] Interactive case builder UI
- [ ] Real-time leaderboard
- [ ] Mobile app for monitoring
- [ ] Integration with external payment systems (simulated)
- [ ] Custom tool builder API

## Version History

### Versioning Scheme

LedgerShield follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Tags

- `v0.1.0` - Initial release (current)

### Deprecation Policy

- Deprecated features will be marked in documentation
- Deprecation warnings added one minor version before removal
- Breaking changes only in major versions
- Migration guides provided for major updates

## Notes

### Breaking Changes

No breaking changes in v0.1.0 (initial release).

### Security Advisories

None at this time.

### Known Issues

See [GitHub Issues](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues) for current known issues.

### Acknowledgments

- Meta OpenEnv Hackathon for the opportunity

---

For the complete list of changes, see the [commit history](https://github.com/BiradarScripts/Meta-s-LedgerShield/commits/main).
