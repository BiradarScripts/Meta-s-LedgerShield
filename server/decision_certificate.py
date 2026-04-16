from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .schema import normalize_text


CERTIFICATE_NODE_TYPES = {
    "artifact",
    "observation",
    "hypothesis",
    "policy",
    "intervention",
    "decision",
    "counterfactual",
}

CERTIFICATE_EDGE_TYPES = {
    "supports",
    "contradicts",
    "requires",
    "violates",
    "would_flip",
}

CLAIM_NODE_TYPES = {"hypothesis", "policy", "decision", "counterfactual"}
SUPPORTING_EDGE_TYPES = {"supports", "requires"}
EVIDENCE_NODE_TYPES = {"artifact", "observation", "intervention"}


@dataclass
class CertificateReport:
    """Machine-verifier report for a LedgerShield decision certificate."""

    present: bool
    auto_generated: bool
    valid: bool
    validity_score: float
    support_score: float
    stability_score: float
    minimality_score: float
    unsupported_claim_rate: float
    contradiction_count: int
    node_count: int
    edge_count: int
    overall_score: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _node_id(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _clean_label(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text[:160]


def _append_node(nodes: list[dict[str, Any]], seen: set[str], node: dict[str, Any]) -> str:
    node_id = _node_id(node.get("id"), f"node-{len(nodes) + 1}")
    if node_id in seen:
        suffix = 2
        candidate = f"{node_id}-{suffix}"
        while candidate in seen:
            suffix += 1
            candidate = f"{node_id}-{suffix}"
        node_id = candidate
    node["id"] = node_id
    node["type"] = normalize_text(node.get("type"))
    node["label"] = _clean_label(node.get("label") or node_id)
    nodes.append(node)
    seen.add(node_id)
    return node_id


def _append_edge(edges: list[dict[str, Any]], source: str, target: str, edge_type: str) -> None:
    if not source or not target:
        return
    edges.append({"source": source, "target": target, "type": normalize_text(edge_type)})


def build_decision_certificate(
    submitted: dict[str, Any],
    *,
    trajectory: list[dict[str, Any]] | None = None,
    final_state: dict[str, Any] | None = None,
    case_context: dict[str, Any] | None = None,
    auto_generated: bool = True,
) -> dict[str, Any]:
    """Create a typed certificate graph from a regular LedgerShield submission.

    This is the compatibility bridge from the existing `evidence_map`,
    `policy_checks`, `reason_codes`, `fraud_flags`, `campaign_signals`, and
    `counterfactual` fields into a verifier-readable graph.
    """

    trajectory = trajectory or []
    final_state = final_state or {}
    case_context = case_context or {}

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    decision = str(submitted.get("decision", "") or "NEEDS_REVIEW")
    decision_id = _append_node(
        nodes,
        seen,
        {
            "id": "decision.final",
            "type": "decision",
            "label": decision,
            "value": decision,
        },
    )

    evidence_map = submitted.get("evidence_map", {}) if isinstance(submitted.get("evidence_map"), dict) else {}
    evidence_ids: list[str] = []
    for idx, (claim, ref) in enumerate(sorted(evidence_map.items()), start=1):
        ref_label = _clean_label(ref)
        evidence_id = _append_node(
            nodes,
            seen,
            {
                "id": f"evidence.{normalize_text(claim) or idx}",
                "type": "observation",
                "label": f"{claim}: {ref_label}",
                "claim": str(claim),
                "ref": ref,
            },
        )
        evidence_ids.append(evidence_id)
        _append_edge(edges, evidence_id, decision_id, "supports")

    for idx, code in enumerate(submitted.get("reason_codes", []) or [], start=1):
        claim_id = _append_node(
            nodes,
            seen,
            {
                "id": f"hypothesis.{normalize_text(code) or idx}",
                "type": "hypothesis",
                "label": code,
            },
        )
        if evidence_ids:
            _append_edge(edges, evidence_ids[min(idx - 1, len(evidence_ids) - 1)], claim_id, "supports")
        _append_edge(edges, claim_id, decision_id, "supports")

    for idx, flag in enumerate(submitted.get("fraud_flags", []) or [], start=1):
        claim_id = _append_node(
            nodes,
            seen,
            {
                "id": f"fraud_flag.{normalize_text(flag) or idx}",
                "type": "hypothesis",
                "label": flag,
            },
        )
        if evidence_ids:
            _append_edge(edges, evidence_ids[min(idx - 1, len(evidence_ids) - 1)], claim_id, "supports")
        _append_edge(edges, claim_id, decision_id, "supports")

    for idx, signal in enumerate(submitted.get("campaign_signals", []) or [], start=1):
        claim_id = _append_node(
            nodes,
            seen,
            {
                "id": f"campaign_signal.{normalize_text(signal) or idx}",
                "type": "hypothesis",
                "label": signal,
            },
        )
        if evidence_ids:
            _append_edge(edges, evidence_ids[min(idx - 1, len(evidence_ids) - 1)], claim_id, "supports")
        _append_edge(edges, claim_id, decision_id, "supports")

    policy_checks = submitted.get("policy_checks", {}) if isinstance(submitted.get("policy_checks"), dict) else {}
    for idx, (policy, status) in enumerate(sorted(policy_checks.items()), start=1):
        policy_id = _append_node(
            nodes,
            seen,
            {
                "id": f"policy.{normalize_text(policy) or idx}",
                "type": "policy",
                "label": f"{policy}: {status}",
                "status": status,
            },
        )
        if evidence_ids:
            _append_edge(edges, evidence_ids[min(idx - 1, len(evidence_ids) - 1)], policy_id, "supports")
        edge_type = "violates" if "fail" in normalize_text(status) or "breach" in normalize_text(status) else "supports"
        _append_edge(edges, policy_id, decision_id, edge_type)

    for idx, step in enumerate(trajectory, start=1):
        action_type = normalize_text(step.get("action_type"))
        if not action_type or action_type == "submit_decision":
            continue
        if action_type.startswith("request_") or action_type in {
            "freeze_vendor_profile",
            "route_to_procurement",
            "route_to_security",
            "flag_duplicate_cluster_review",
            "create_human_handoff",
        }:
            intervention_id = _append_node(
                nodes,
                seen,
                {
                    "id": f"intervention.{idx}.{action_type}",
                    "type": "intervention",
                    "label": action_type,
                    "success": bool(step.get("success", True)),
                },
            )
            _append_edge(edges, intervention_id, decision_id, "supports")

    for artifact in (final_state.get("revealed_artifacts", []) or []):
        if not isinstance(artifact, dict):
            continue
        artifact_id = str(artifact.get("artifact_id", "") or "")
        if not artifact_id:
            continue
        node_id = _append_node(
            nodes,
            seen,
            {
                "id": f"artifact.{normalize_text(artifact_id)}",
                "type": "artifact",
                "label": artifact.get("summary", artifact_id),
                "artifact_id": artifact_id,
            },
        )
        _append_edge(edges, node_id, decision_id, "supports")

    counterfactual = str(submitted.get("counterfactual", "") or "").strip()
    if counterfactual:
        counter_id = _append_node(
            nodes,
            seen,
            {
                "id": "counterfactual.primary",
                "type": "counterfactual",
                "label": counterfactual,
                "text": counterfactual,
            },
        )
        if evidence_ids:
            _append_edge(edges, evidence_ids[0], counter_id, "supports")
        _append_edge(edges, counter_id, decision_id, "would_flip")

    return {
        "certificate_version": "ledgershield-dcg-v1",
        "case_id": case_context.get("case_id") or case_context.get("case_snapshot", {}).get("case_id"),
        "decision": decision,
        "auto_generated": bool(auto_generated),
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "source": "legacy_submission_bridge" if auto_generated else "agent_submission",
            "case_id": case_context.get("case_id") or case_context.get("case_snapshot", {}).get("case_id"),
            "task_type": case_context.get("task_type") or case_context.get("case_snapshot", {}).get("task_type"),
            "node_types": sorted(CERTIFICATE_NODE_TYPES),
            "edge_types": sorted(CERTIFICATE_EDGE_TYPES),
            "portfolio_context": dict(final_state.get("portfolio_context", {}) or {}),
            "institutional_memory": dict(final_state.get("institutional_memory", {}) or {}),
        },
    }


def _references_from_value(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, val in value.items():
            norm_key = normalize_text(key)
            if norm_key in {"doc_id", "artifact_id", "token_id", "thread_id", "po_id", "receipt_id"}:
                refs.add(str(val))
            elif norm_key == "token_ids" and isinstance(val, list):
                refs.update(str(item) for item in val)
            else:
                refs.update(_references_from_value(val))
    elif isinstance(value, list):
        for item in value:
            refs.update(_references_from_value(item))
    elif isinstance(value, str):
        text = value.strip()
        if text:
            refs.add(text)
    return {ref for ref in refs if ref}


def _reference_index(final_state: dict[str, Any], case_context: dict[str, Any], submitted: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for doc in case_context.get("documents", []) or []:
        if isinstance(doc, dict) and doc.get("doc_id"):
            refs.add(str(doc["doc_id"]))
        for token_list_name in ("accurate_ocr", "noisy_ocr"):
            for token in doc.get(token_list_name, []) or []:
                if isinstance(token, dict) and token.get("token_id"):
                    refs.add(str(token["token_id"]))
    for artifact_id in final_state.get("revealed_artifact_ids", []) or []:
        refs.add(str(artifact_id))
    for artifact in final_state.get("revealed_artifacts", []) or []:
        if isinstance(artifact, dict) and artifact.get("artifact_id"):
            refs.add(str(artifact["artifact_id"]))
    refs.update(_references_from_value(submitted.get("evidence_map", {})))
    return {ref for ref in refs if ref}


def _path_exists_to_decision(
    source_id: str,
    decision_ids: set[str],
    support_edges: dict[str, set[str]],
    *,
    depth_limit: int = 6,
) -> bool:
    frontier = [(source_id, 0)]
    seen: set[str] = set()
    while frontier:
        node_id, depth = frontier.pop()
        if node_id in decision_ids:
            return True
        if depth >= depth_limit or node_id in seen:
            continue
        seen.add(node_id)
        for next_id in support_edges.get(node_id, set()):
            frontier.append((next_id, depth + 1))
    return False


def verify_decision_certificate(
    certificate: dict[str, Any] | None,
    *,
    submitted: dict[str, Any],
    gold: dict[str, Any] | None = None,
    final_state: dict[str, Any] | None = None,
    case_context: dict[str, Any] | None = None,
    trajectory: list[dict[str, Any]] | None = None,
    synthesize_if_missing: bool = True,
) -> CertificateReport:
    """Verify a decision-certificate graph.

    The verifier checks graph well-formedness, support paths from evidence to
    claims and decisions, contradiction handling, reference grounding, and a
    lightweight replay-stability proxy. It deliberately avoids LLM judging.
    """

    gold = gold or {}
    final_state = final_state or {}
    case_context = case_context or {}
    trajectory = trajectory or []

    auto_generated = False
    if not isinstance(certificate, dict):
        if not synthesize_if_missing:
            return CertificateReport(
                present=False,
                auto_generated=False,
                valid=False,
                validity_score=0.0,
                support_score=0.0,
                stability_score=0.0,
                minimality_score=0.0,
                unsupported_claim_rate=1.0,
                contradiction_count=0,
                node_count=0,
                edge_count=0,
                overall_score=0.0,
                errors=["missing_certificate"],
            )
        certificate = build_decision_certificate(
            submitted,
            trajectory=trajectory,
            final_state=final_state,
            case_context=case_context,
            auto_generated=True,
        )
        auto_generated = True
    else:
        auto_generated = bool(certificate.get("auto_generated", False))

    nodes = certificate.get("nodes", [])
    edges = certificate.get("edges", [])
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(nodes, list) or not nodes:
        errors.append("certificate_nodes_missing")
        nodes = []
    if not isinstance(edges, list):
        errors.append("certificate_edges_malformed")
        edges = []

    node_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids = 0
    invalid_node_types = 0
    for idx, raw_node in enumerate(nodes):
        if not isinstance(raw_node, dict):
            invalid_node_types += 1
            continue
        node_id = _node_id(raw_node.get("id"), f"node-{idx + 1}")
        node_type = normalize_text(raw_node.get("type"))
        if node_id in node_by_id:
            duplicate_ids += 1
        if node_type not in CERTIFICATE_NODE_TYPES:
            invalid_node_types += 1
        node_by_id[node_id] = {**raw_node, "id": node_id, "type": node_type}

    if duplicate_ids:
        errors.append(f"duplicate_node_ids:{duplicate_ids}")
    if invalid_node_types:
        errors.append(f"invalid_node_types:{invalid_node_types}")

    invalid_edges = 0
    contradiction_count = 0
    support_edges: dict[str, set[str]] = {}
    incoming_support: dict[str, int] = {}
    for raw_edge in edges:
        if not isinstance(raw_edge, dict):
            invalid_edges += 1
            continue
        source = str(raw_edge.get("source", "") or "")
        target = str(raw_edge.get("target", "") or "")
        edge_type = normalize_text(raw_edge.get("type"))
        if source not in node_by_id or target not in node_by_id or edge_type not in CERTIFICATE_EDGE_TYPES:
            invalid_edges += 1
            continue
        if edge_type == "contradicts":
            contradiction_count += 1
        if edge_type in SUPPORTING_EDGE_TYPES:
            support_edges.setdefault(source, set()).add(target)
            incoming_support[target] = incoming_support.get(target, 0) + 1

    if invalid_edges:
        errors.append(f"invalid_edges:{invalid_edges}")

    decision_ids = {
        node_id
        for node_id, node in node_by_id.items()
        if node.get("type") == "decision"
    }
    if not decision_ids:
        errors.append("decision_node_missing")

    submitted_decision = normalize_text(submitted.get("decision"))
    mismatched_decision = False
    if submitted_decision and decision_ids:
        decision_values = {
            normalize_text(node_by_id[node_id].get("value") or node_by_id[node_id].get("label"))
            for node_id in decision_ids
        }
        mismatched_decision = submitted_decision not in decision_values
        if mismatched_decision:
            errors.append("decision_mismatch")

    claim_ids = [
        node_id
        for node_id, node in node_by_id.items()
        if node.get("type") in CLAIM_NODE_TYPES
    ]
    unsupported_claims = [
        node_id
        for node_id in claim_ids
        if incoming_support.get(node_id, 0) == 0 and node_by_id[node_id].get("type") != "decision"
    ]
    evidence_ids = [
        node_id
        for node_id, node in node_by_id.items()
        if node.get("type") in EVIDENCE_NODE_TYPES
    ]
    evidence_to_decision = sum(
        1
        for node_id in evidence_ids
        if _path_exists_to_decision(node_id, decision_ids, support_edges)
    )
    support_score = evidence_to_decision / max(len(evidence_ids), 1)
    unsupported_claim_rate = len(unsupported_claims) / max(len(claim_ids), 1)

    reference_index = _reference_index(final_state, case_context, submitted)
    ungrounded_refs = 0
    ref_checked = 0
    for node in node_by_id.values():
        refs = _references_from_value(node.get("ref"))
        if not refs:
            continue
        ref_checked += len(refs)
        ungrounded_refs += len([ref for ref in refs if ref not in reference_index])
    if ungrounded_refs:
        warnings.append(f"ungrounded_references:{ungrounded_refs}")

    has_counterfactual = any(node.get("type") == "counterfactual" for node in node_by_id.values())
    has_policy = any(node.get("type") == "policy" for node in node_by_id.values())
    has_intervention = any(node.get("type") == "intervention" for node in node_by_id.values())
    risky = bool(gold.get("unsafe_if_pay")) or bool(gold.get("fraud_flags")) or bool(gold.get("reason_codes"))
    gold_decision = normalize_text(gold.get("decision"))
    decision_match = 1.0 if not gold_decision or submitted_decision == gold_decision else 0.0
    stability_score = (
        0.45 * decision_match
        + 0.20 * float(has_counterfactual or not risky)
        + 0.20 * float(has_policy or submitted_decision == "pay")
        + 0.15 * float(has_intervention or not risky)
    )
    if contradiction_count and not any(normalize_text(edge.get("type")) == "contradicts" for edge in edges if isinstance(edge, dict)):
        stability_score *= 0.85

    node_count = len(node_by_id)
    edge_count = len(edges)
    minimality_score = 1.0
    if node_count > 34:
        minimality_score -= min(0.35, (node_count - 34) * 0.015)
    if edge_count > 48:
        minimality_score -= min(0.25, (edge_count - 48) * 0.01)
    minimality_score = max(0.0, minimality_score)

    structural_penalty = 0.12 * len(errors) + 0.03 * duplicate_ids + 0.02 * invalid_edges
    reference_penalty = min(0.15, 0.03 * ungrounded_refs)
    validity_score = max(0.0, 1.0 - structural_penalty - reference_penalty)
    if not nodes:
        validity_score = 0.0

    overall = (
        0.32 * validity_score
        + 0.30 * support_score
        + 0.25 * stability_score
        + 0.13 * minimality_score
        - 0.18 * unsupported_claim_rate
    )
    overall = max(0.0, min(1.0, overall))

    return CertificateReport(
        present=True,
        auto_generated=auto_generated,
        valid=validity_score >= 0.70 and unsupported_claim_rate <= 0.40 and not mismatched_decision,
        validity_score=round(validity_score, 4),
        support_score=round(support_score, 4),
        stability_score=round(stability_score, 4),
        minimality_score=round(minimality_score, 4),
        unsupported_claim_rate=round(unsupported_claim_rate, 4),
        contradiction_count=contradiction_count,
        node_count=node_count,
        edge_count=edge_count,
        overall_score=round(overall, 4),
        errors=errors,
        warnings=warnings,
    )


def certificate_score_adjustment(report: CertificateReport, *, explicit_certificate: bool) -> float:
    """Small grading adjustment for executable proof quality.

    Legacy submissions are synthesized for diagnostics and receive no bonus or
    penalty. Agent-supplied certificates can earn a small auditability bonus or
    lose points if they are malformed or unsupported.
    """

    if not explicit_certificate:
        return 0.0
    if report.overall_score >= 0.82 and report.valid:
        return 0.01
    if report.overall_score < 0.45 or not report.valid:
        return -0.03
    return 0.0
