from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

@dataclass
class GraphNode:
    node_id: str
    node_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    revealed: bool = False
    
    def reveal(self) -> None:
        self.revealed = True

@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    attributes: dict[str, Any] = field(default_factory=dict)
    
@dataclass
class UnlockRule:
    trigger_action: str
    required_nodes: list[str]
    unlocked_nodes: list[str]

class EvidenceGraph:
    """Latent Evidence Graph representing the ground truth causal scenario."""
    
    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.unlock_rules: list[UnlockRule] = []
        
        # Track the latent hypothesis (e.g., safe, account_takeover)
        self.latent_hypothesis: str = "safe"

    def add_node(self, node_id: str, node_type: str, **attributes: Any) -> GraphNode:
        node = GraphNode(node_id=node_id, node_type=node_type, attributes=attributes)
        self.nodes[node_id] = node
        return node
        
    def add_edge(self, source: str, target: str, relation: str, **attributes: Any) -> None:
        self.edges.append(GraphEdge(source, target, relation, attributes))

    def add_unlock_rule(self, trigger_action: str, required_nodes: list[str], unlocked_nodes: list[str]) -> None:
        self.unlock_rules.append(UnlockRule(trigger_action, required_nodes, unlocked_nodes))

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)
        
    def reveal_by_action(self, action: str) -> list[str]:
        """Reveal nodes unlocked by an action, assuming prerequisite nodes are revealed."""
        newly_revealed = []
        for rule in self.unlock_rules:
            if rule.trigger_action == action:
                if all(self.nodes[req].revealed for req in rule.required_nodes if req in self.nodes):
                    for unl in rule.unlocked_nodes:
                        if unl in self.nodes and not self.nodes[unl].revealed:
                            self.nodes[unl].reveal()
                            newly_revealed.append(unl)
        return newly_revealed

    def serialize(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "latent_hypothesis": self.latent_hypothesis,
            "nodes": {nid: {"type": n.node_type, "attributes": n.attributes, "revealed": n.revealed} 
                      for nid, n in self.nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "relation": e.relation, "attributes": e.attributes} 
                      for e in self.edges],
            "unlock_rules": [{"trigger_action": r.trigger_action, "required_nodes": r.required_nodes, "unlocked_nodes": r.unlocked_nodes} 
                             for r in self.unlock_rules]
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> EvidenceGraph:
        graph = cls(seed=data.get("seed", 0))
        graph.latent_hypothesis = data.get("latent_hypothesis", "safe")
        for nid, ndata in data.get("nodes", {}).items():
            n = graph.add_node(nid, ndata.get("type", "unknown"), **ndata.get("attributes", {}))
            n.revealed = ndata.get("revealed", False)
        for edata in data.get("edges", []):
            graph.add_edge(edata["source"], edata["target"], edata["relation"], **edata.get("attributes", {}))
        for rdata in data.get("unlock_rules", []):
            graph.add_unlock_rule(rdata["trigger_action"], rdata["required_nodes"], rdata["unlocked_nodes"])
        return graph


def generate_scenario_graph(scenario_type: str, seed: int) -> EvidenceGraph:
    """
    Generate a full latent graph for a scenario.
    Parameters vary by seed to satisfy P1 constraints.
    """
    graph = EvidenceGraph(seed)
    rng = graph.rng
    
    # Base nodes common to all scenarios
    vendor = graph.add_node("vendor_entity", "vendor", approved_bank="US_BANK_123")
    invoice = graph.add_node("invoice_doc", "document", request_amount=rng.uniform(100.0, 5000.0))
    graph.add_edge("invoice_doc", "vendor_entity", "claims_identity")
    
    if scenario_type == "safe":
        graph.latent_hypothesis = "safe"
        bank = graph.add_node("payment_bank", "bank_account", account="US_BANK_123")
        graph.add_edge("invoice_doc", "payment_bank", "requests_payment_to")
        # Direct verification available
        graph.add_unlock_rule("lookup_vendor_history", ["vendor_entity"], ["payment_bank"])
        
    elif scenario_type == "bank_change_fraud":
        graph.latent_hypothesis = "fraud_account_takeover"
        bank = graph.add_node("payment_bank", "bank_account", account="FOREIGN_BANK_999")
        email = graph.add_node("phishing_email", "email_thread", sender_domain="vend0r.com")
        graph.add_edge("invoice_doc", "payment_bank", "requests_payment_to")
        graph.add_edge("phishing_email", "invoice_doc", "delivers_document")
        graph.add_edge("payment_bank", "vendor_entity", "contradicts_approved_bank")
        
        # Interventions needed to reveal full truth
        graph.add_node("callback_verification", "intervention_result", outcome="failed", risk_signal="account_takeover")
        graph.add_unlock_rule("request_callback_verification", ["invoice_doc", "vendor_entity"], ["callback_verification"])
        
    elif scenario_type == "duplicate_invoice":
        graph.latent_hypothesis = "duplicate_billing"
        bank = graph.add_node("payment_bank", "bank_account", account="US_BANK_123")
        past_invoice = graph.add_node("past_invoice", "historic_document", previous_amount=invoice.attributes["request_amount"])
        graph.add_edge("invoice_doc", "payment_bank", "requests_payment_to")
        graph.add_edge("invoice_doc", "past_invoice", "duplicates_characteristics")
        
        graph.add_node("duplicate_report", "intervention_result", outcome="cluster_detected")
        graph.add_unlock_rule("flag_duplicate_cluster_review", ["invoice_doc", "past_invoice"], ["duplicate_report"])
        
    else:
        # fallback default
        graph.latent_hypothesis = "safe"

    return graph
