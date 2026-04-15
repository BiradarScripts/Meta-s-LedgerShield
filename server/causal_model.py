from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .sprt_engine import ATTACK_NAME_TO_HYPOTHESIS, latent_hypothesis_from_case


@dataclass(frozen=True)
class CausalNodeSpec:
    name: str
    parents: tuple[str, ...] = ()
    kind: str = "endogenous"
    domain: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class CausalScenarioTemplate:
    scenario_id: str
    hypothesis: str
    exogenous_priors: dict[str, dict[str, float]]
    nodes: dict[str, CausalNodeSpec]
    edges: tuple[tuple[str, str], ...]
    interventional_nodes: dict[str, tuple[str, ...]]
    confounders: tuple[str, ...]
    evidence_nodes: tuple[str, ...]
    decision_variable: str = "decision"
    outcome_variable: str = "payment_outcome"


def _common_nodes() -> dict[str, CausalNodeSpec]:
    return {
        "latent_hypothesis": CausalNodeSpec("latent_hypothesis", kind="exogenous", domain=("safe", "fraud")),
        "vendor_legitimacy": CausalNodeSpec("vendor_legitimacy", ("latent_hypothesis",), domain=("trusted", "suspect")),
        "sender_authenticity": CausalNodeSpec("sender_authenticity", ("latent_hypothesis", "vendor_legitimacy"), domain=("verified", "spoofed")),
        "bank_alignment": CausalNodeSpec("bank_alignment", ("latent_hypothesis", "vendor_legitimacy"), domain=("match", "mismatch")),
        "document_integrity": CausalNodeSpec("document_integrity", ("latent_hypothesis",), domain=("clean", "tampered")),
        "approval_chain_integrity": CausalNodeSpec("approval_chain_integrity", ("latent_hypothesis",), domain=("approved", "bypassed")),
        "duplicate_pattern": CausalNodeSpec("duplicate_pattern", ("latent_hypothesis", "document_integrity"), domain=("absent", "present")),
        "portfolio_linkage": CausalNodeSpec("portfolio_linkage", ("latent_hypothesis",), domain=("isolated", "linked")),
        "callback_result": CausalNodeSpec("callback_result", ("latent_hypothesis", "vendor_legitimacy"), domain=("clean", "suspicious", "dispute")),
        "decision": CausalNodeSpec("decision", ("sender_authenticity", "bank_alignment", "duplicate_pattern", "approval_chain_integrity", "portfolio_linkage", "callback_result"), kind="decision"),
        "payment_outcome": CausalNodeSpec("payment_outcome", ("decision", "latent_hypothesis"), kind="outcome"),
    }


COMMON_EDGES = (
    ("latent_hypothesis", "vendor_legitimacy"),
    ("latent_hypothesis", "sender_authenticity"),
    ("latent_hypothesis", "bank_alignment"),
    ("latent_hypothesis", "document_integrity"),
    ("latent_hypothesis", "approval_chain_integrity"),
    ("latent_hypothesis", "duplicate_pattern"),
    ("latent_hypothesis", "portfolio_linkage"),
    ("latent_hypothesis", "callback_result"),
    ("vendor_legitimacy", "sender_authenticity"),
    ("vendor_legitimacy", "bank_alignment"),
    ("document_integrity", "duplicate_pattern"),
    ("sender_authenticity", "decision"),
    ("bank_alignment", "decision"),
    ("duplicate_pattern", "decision"),
    ("approval_chain_integrity", "decision"),
    ("portfolio_linkage", "decision"),
    ("callback_result", "decision"),
    ("decision", "payment_outcome"),
    ("latent_hypothesis", "payment_outcome"),
)

COMMON_INTERVENTIONS = {
    "inspect_email_thread": ("sender_authenticity", "approval_chain_integrity"),
    "compare_bank_account": ("bank_alignment",),
    "search_ledger": ("duplicate_pattern", "portfolio_linkage"),
    "lookup_vendor_history": ("vendor_legitimacy",),
    "request_callback_verification": ("callback_result",),
    "flag_duplicate_cluster_review": ("duplicate_pattern", "portfolio_linkage"),
    "request_bank_change_approval_chain": ("approval_chain_integrity", "bank_alignment"),
    "request_po_reconciliation": ("document_integrity",),
    "request_additional_receipt_evidence": ("document_integrity",),
    "route_to_security": ("payment_outcome",),
}


def _template(
    scenario_id: str,
    hypothesis: str,
    *,
    confounders: tuple[str, ...],
    evidence_nodes: tuple[str, ...],
) -> CausalScenarioTemplate:
    return CausalScenarioTemplate(
        scenario_id=scenario_id,
        hypothesis=hypothesis,
        exogenous_priors={
            "latent_hypothesis": {"safe": 0.5, "fraud": 0.5},
            "market_noise": {"low": 0.7, "high": 0.3},
        },
        nodes=_common_nodes(),
        edges=COMMON_EDGES,
        interventional_nodes={key: tuple(value) for key, value in COMMON_INTERVENTIONS.items()},
        confounders=confounders,
        evidence_nodes=evidence_nodes,
    )


SCENARIO_TEMPLATES: dict[str, CausalScenarioTemplate] = {
    "safe_baseline": _template(
        "safe_baseline",
        "safe",
        confounders=("vendor_legitimacy",),
        evidence_nodes=("bank_alignment", "sender_authenticity"),
    ),
    "bank_override_attack": _template(
        "bank_override_attack",
        "bank_fraud",
        confounders=("vendor_legitimacy", "approval_chain_integrity"),
        evidence_nodes=("bank_alignment", "callback_result", "approval_chain_integrity"),
    ),
    "vendor_takeover_attack": _template(
        "vendor_takeover_attack",
        "vendor_takeover",
        confounders=("vendor_legitimacy", "sender_authenticity"),
        evidence_nodes=("sender_authenticity", "callback_result", "bank_alignment"),
    ),
    "ceo_fraud_attack": _template(
        "ceo_fraud_attack",
        "ceo_bec",
        confounders=("sender_authenticity", "approval_chain_integrity"),
        evidence_nodes=("sender_authenticity", "approval_chain_integrity", "callback_result"),
    ),
    "domain_typosquat_attack": _template(
        "domain_typosquat_attack",
        "vendor_takeover",
        confounders=("sender_authenticity",),
        evidence_nodes=("sender_authenticity", "bank_alignment"),
    ),
    "near_duplicate_invoice_attack": _template(
        "near_duplicate_invoice_attack",
        "duplicate_billing",
        confounders=("document_integrity",),
        evidence_nodes=("duplicate_pattern", "document_integrity"),
    ),
    "fake_receipt_attack": _template(
        "fake_receipt_attack",
        "duplicate_billing",
        confounders=("document_integrity", "approval_chain_integrity"),
        evidence_nodes=("document_integrity", "approval_chain_integrity"),
    ),
    "phantom_vendor_attack": _template(
        "phantom_vendor_attack",
        "phantom_vendor",
        confounders=("vendor_legitimacy", "document_integrity"),
        evidence_nodes=("vendor_legitimacy", "document_integrity", "callback_result"),
    ),
    "inflated_line_items_attack": _template(
        "inflated_line_items_attack",
        "duplicate_billing",
        confounders=("document_integrity",),
        evidence_nodes=("document_integrity", "approval_chain_integrity"),
    ),
    "urgency_spoof_attack": _template(
        "urgency_spoof_attack",
        "ceo_bec",
        confounders=("sender_authenticity", "approval_chain_integrity"),
        evidence_nodes=("sender_authenticity", "approval_chain_integrity"),
    ),
    "approval_threshold_evasion_attack": _template(
        "approval_threshold_evasion_attack",
        "threshold_evasion",
        confounders=("approval_chain_integrity",),
        evidence_nodes=("approval_chain_integrity", "duplicate_pattern"),
    ),
    "workflow_override_attack": _template(
        "workflow_override_attack",
        "insider_collusion",
        confounders=("approval_chain_integrity", "sender_authenticity"),
        evidence_nodes=("approval_chain_integrity", "sender_authenticity", "callback_result"),
    ),
    "split_payment_attack": _template(
        "split_payment_attack",
        "split_payment",
        confounders=("duplicate_pattern", "approval_chain_integrity"),
        evidence_nodes=("duplicate_pattern", "portfolio_linkage", "approval_chain_integrity"),
    ),
    "coordinated_campaign_attack": _template(
        "coordinated_campaign_attack",
        "campaign_fraud",
        confounders=("portfolio_linkage", "duplicate_pattern"),
        evidence_nodes=("portfolio_linkage", "duplicate_pattern", "bank_alignment"),
    ),
    "supply_chain_compromise_attack": _template(
        "supply_chain_compromise_attack",
        "supply_chain_compromise",
        confounders=("vendor_legitimacy", "bank_alignment"),
        evidence_nodes=("vendor_legitimacy", "bank_alignment", "callback_result"),
    ),
    "insider_collusion_attack": _template(
        "insider_collusion_attack",
        "insider_collusion",
        confounders=("approval_chain_integrity",),
        evidence_nodes=("approval_chain_integrity", "callback_result"),
    ),
    "multi_entity_layering_attack": _template(
        "multi_entity_layering_attack",
        "multi_entity_layering",
        confounders=("portfolio_linkage", "vendor_legitimacy"),
        evidence_nodes=("portfolio_linkage", "bank_alignment", "callback_result"),
    ),
}

HYPOTHESIS_TO_TEMPLATE = {
    template.hypothesis: template_id
    for template_id, template in SCENARIO_TEMPLATES.items()
}


def scenario_template_from_case(case: dict[str, Any]) -> CausalScenarioTemplate:
    metadata = case.get("generator_metadata", {}) or {}
    attacks = metadata.get("applied_attacks", []) or []
    for attack in attacks:
        if str(attack) in SCENARIO_TEMPLATES:
            return SCENARIO_TEMPLATES[str(attack)]

    hypothesis = latent_hypothesis_from_case(case)
    template_id = HYPOTHESIS_TO_TEMPLATE.get(hypothesis, "safe_baseline")
    return SCENARIO_TEMPLATES[template_id]


@dataclass
class StructuralCausalModel:
    template: CausalScenarioTemplate
    observed_nodes: set[str] = field(default_factory=set)
    interventions: dict[str, Any] = field(default_factory=dict)

    @property
    def parents(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {name: set() for name in self.template.nodes}
        for source, target in self.template.edges:
            graph.setdefault(target, set()).add(source)
        return graph

    @property
    def children(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {name: set() for name in self.template.nodes}
        for source, target in self.template.edges:
            graph.setdefault(source, set()).add(target)
        return graph

    def observed_nodes_for_actions(self, actions: list[str]) -> set[str]:
        observed = set(self.observed_nodes)
        for action in actions:
            observed.update(self.template.interventional_nodes.get(action, ()))
        return observed

    def intervene(self, tool_name: str, value: Any | None = None) -> StructuralCausalModel:
        observed = self.observed_nodes_for_actions([tool_name])
        interventions = dict(self.interventions)
        interventions[tool_name] = value if value is not None else "observed"
        return StructuralCausalModel(self.template, observed_nodes=observed, interventions=interventions)

    def _ancestors(self, targets: set[str]) -> set[str]:
        parents = self.parents
        stack = list(targets)
        visited = set(targets)
        while stack:
            current = stack.pop()
            for parent in parents.get(current, set()):
                if parent not in visited:
                    visited.add(parent)
                    stack.append(parent)
        return visited

    def d_separated(self, x: str, y: str, conditioned: set[str] | None = None) -> bool:
        conditioned = set(conditioned or set())
        relevant = self._ancestors({x, y} | conditioned)
        undirected: dict[str, set[str]] = {node: set() for node in relevant}
        parents = self.parents
        for source, target in self.template.edges:
            if source in relevant and target in relevant:
                undirected[source].add(target)
                undirected[target].add(source)
        for child, node_parents in parents.items():
            if child not in relevant:
                continue
            parent_list = [parent for parent in node_parents if parent in relevant]
            for index, left in enumerate(parent_list):
                for right in parent_list[index + 1 :]:
                    undirected[left].add(right)
                    undirected[right].add(left)
        for blocked in conditioned:
            if blocked in undirected:
                for neighbour in list(undirected[blocked]):
                    undirected[neighbour].discard(blocked)
                undirected.pop(blocked, None)
        if x not in undirected or y not in undirected:
            return True
        stack = [x]
        visited = {x}
        while stack:
            current = stack.pop()
            if current == y:
                return False
            for neighbour in undirected.get(current, set()):
                if neighbour not in visited:
                    visited.add(neighbour)
                    stack.append(neighbour)
        return True

    def d_separation_sufficiency(self, observed_nodes: set[str]) -> float:
        if not self.template.confounders:
            return 1.0
        blocked = 0
        for confounder in self.template.confounders:
            blocked += int(self.d_separated(self.template.decision_variable, confounder, observed_nodes))
        return blocked / len(self.template.confounders)

    def counterfactual(self, *, overrides: dict[str, str] | None = None) -> dict[str, Any]:
        world = {
            "sender_authenticity": "verified",
            "bank_alignment": "match",
            "document_integrity": "clean",
            "approval_chain_integrity": "approved",
            "duplicate_pattern": "absent",
            "portfolio_linkage": "isolated",
            "callback_result": "clean",
        }
        suspicious_defaults = {
            "bank_fraud": {"bank_alignment": "mismatch", "callback_result": "dispute"},
            "duplicate_billing": {"duplicate_pattern": "present", "document_integrity": "tampered"},
            "vendor_takeover": {"sender_authenticity": "spoofed", "bank_alignment": "mismatch"},
            "ceo_bec": {"sender_authenticity": "spoofed", "approval_chain_integrity": "bypassed"},
            "phantom_vendor": {"vendor_legitimacy": "suspect", "document_integrity": "tampered"},
            "supply_chain_compromise": {"bank_alignment": "mismatch", "callback_result": "dispute"},
            "insider_collusion": {"approval_chain_integrity": "bypassed", "callback_result": "suspicious"},
            "multi_entity_layering": {"portfolio_linkage": "linked", "callback_result": "suspicious"},
            "campaign_fraud": {"portfolio_linkage": "linked", "duplicate_pattern": "present"},
            "split_payment": {"duplicate_pattern": "present", "approval_chain_integrity": "bypassed"},
            "threshold_evasion": {"approval_chain_integrity": "bypassed"},
        }
        world.update(suspicious_defaults.get(self.template.hypothesis, {}))
        world.update(overrides or {})

        risk_score = 0
        for key in ("sender_authenticity", "bank_alignment", "approval_chain_integrity", "duplicate_pattern", "portfolio_linkage", "callback_result"):
            if world.get(key) in {"spoofed", "mismatch", "bypassed", "present", "linked", "suspicious", "dispute"}:
                risk_score += 1

        if risk_score == 0:
            decision = "PAY"
        elif risk_score <= 2:
            decision = "HOLD"
        else:
            decision = "ESCALATE_FRAUD"

        return {
            "overrides": dict(overrides or {}),
            "decision": decision,
            "risk_score": risk_score,
            "observed_nodes": sorted(self.observed_nodes),
        }


def build_causal_model_for_case(case: dict[str, Any]) -> StructuralCausalModel:
    return StructuralCausalModel(template=scenario_template_from_case(case))
