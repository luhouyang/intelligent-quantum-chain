import networkx as nx
from typing import Dict, Any, List


class ExpandablePolicyOntology:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_base_ontology()

    def _build_base_ontology(self):
        # Base Asset & Execution Classes
        self.graph.add_node("AssetClass:Stablecoin", category="Asset")
        self.graph.add_node("AssetClass:CBDC", category="Asset")
        self.graph.add_node("Execution:Tier1_PQC", crypto="ML-DSA")
        self.graph.add_node("Execution:Tier2_QKD", crypto="BB84_QKD")

        # Dynamic Blacklist Registry Subgraph
        self.graph.add_node("BlacklistRegistry", category="Security")

        # Initial Blacklist Items
        initial_blacklist = ["0xEvil_Contract", "0xEvil_Address", "hacker"]
        for counterparty in initial_blacklist:
            self.add_blacklisted_counterparty(counterparty)

        # Asset Mappings
        self.graph.add_edge("USDC", "AssetClass:Stablecoin", relation="is_a")
        self.graph.add_edge("Digital_Euro", "AssetClass:Stablecoin", relation="is_a")
        self.graph.add_edge("BRICS_Unit", "AssetClass:CBDC", relation="is_a")
        self.graph.add_edge("AssetClass:Stablecoin", "Execution:Tier1_PQC", relation="default_tier")
        self.graph.add_edge("AssetClass:CBDC", "Execution:Tier2_QKD", relation="default_tier")

    def add_blacklisted_counterparty(self, counterparty_id: str):
        """Adds a new blacklisted address or contract ID to the ontology graph."""
        self.graph.add_node(f"Blacklist:{counterparty_id}", counterparty_id=counterparty_id)
        self.graph.add_edge(f"Blacklist:{counterparty_id}", "BlacklistRegistry", relation="blacklisted_under")

    def get_blacklisted_counterparties(self) -> List[str]:
        """Returns the current list of blacklisted entity IDs stored in the ontology."""
        nodes = [d.get("counterparty_id") for n, d in self.graph.nodes(data=True) if n.startswith("Blacklist:")]
        return [n for n in nodes if n is not None]

    def register_new_protocol(self, entity_id: str, parent_class: str):
        self.graph.add_node(entity_id)
        self.graph.add_edge(entity_id, parent_class, relation="is_a")

    def evaluate_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        asset = intent.get("asset", "USDC")
        amount = intent.get("amount", 0.0)
        dest = intent.get("dest", "")

        # Check against the dynamic Blacklist nodes in the Ontology Graph
        blacklisted_ids = self.get_blacklisted_counterparties()
        if any(b_id.lower() in dest.lower() for b_id in blacklisted_ids):
            return {
                "status": "BLOCKED",
                "reason": f"UNTRUSTED_COUNTERPARTY_BLACKLIST: Destination '{dest}' matched Blacklist Registry in Policy Ontology.",
                "matched_blacklist": blacklisted_ids
            }

        asset_parents = list(self.graph.successors(asset)) if self.graph.has_node(asset) else ["AssetClass:Stablecoin"]
        asset_class = asset_parents[0]
        default_tier_nodes = list(self.graph.successors(asset_class))
        required_tier = default_tier_nodes[0] if default_tier_nodes else "Execution:Tier1_PQC"

        if amount >= 1000000.0 and required_tier == "Execution:Tier1_PQC":
            required_tier = "Execution:Tier2_QKD"

        return {
            "status": "APPROVED",
            "asset_class": asset_class,
            "required_tier": required_tier.replace("Execution:", ""),
            "passkey_required": amount > 50000.0
        }