"""
Analytics Service — Version C (Merged)
========================================
SOURCE DECISION:
  ARCHITECTURE    : ZIP A  (Facade Pattern + Dataclass AnalyticsResult — lebih clean)
  PIPELINE        : ZIP A  (FP-Growth → DiGraph → Centralities → Communities)
  NEW FEATURES    : ZIP B  (network_metrics, robustness, vulnerabilities — ditambahkan ke pipeline)
  ERROR HANDLING  : BOTH   (gabungan error handling keduanya)
"""

import pandas as pd
import networkx as nx
from dataclasses import dataclass, field
from typing import Dict, List

from src.mining.fp_growth_engine import mine_association_rules, build_directed_graph
from src.graph.centrality import calculate_graph_centralities
from src.graph.communities import detect_graph_communities
from src.graph.graph_builder import calculate_network_metrics, analyze_robustness, get_structural_vulnerabilities


@dataclass
class AnalyticsResult:
    """Dataclass tunggal berisi seluruh hasil komputasi pipeline."""
    graph: nx.DiGraph
    rules: pd.DataFrame
    centralities: pd.DataFrame
    community_map: Dict[str, int]
    modularity: float
    communities: List[set]
    network_metrics: dict = field(default_factory=dict)
    robustness_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    articulations: list = field(default_factory=list)
    bridges: list = field(default_factory=list)
    is_success: bool = True
    error_msg: str = ""


def run_full_pipeline(df: pd.DataFrame, min_support: float, min_lift: float) -> AnalyticsResult:
    """
    Orkestrator pipeline analitik lengkap (Facade Pattern).

    Tahapan:
      1. Data Mining   : FP-Growth + Sparse Matrix (O(N))
      2. Graph Build   : DiGraph dengan edge confidence-weighted
      3. Centralities  : PageRank, In/Out-Strength, Degree, Betweenness, Closeness, Eigenvector
      4. Communities   : Louvain (fallback: Greedy Modularity)
      5. Network Metrics : Density, Clustering, Diameter (NEW dari ZIP B)
      6. Robustness    : Albert-Barabási simulation (NEW dari ZIP B)
      7. Vulnerabilities: Articulation Points & Bridges (NEW dari ZIP B)
    """
    try:
        # TAHAP 1: FP-Growth + Sparse Matrix
        rules = mine_association_rules(df, min_support, min_lift)
        if rules.empty:
            return AnalyticsResult(
                graph=None, rules=None, centralities=None,
                community_map=None, modularity=0.0, communities=[],
                is_success=False,
                error_msg="Tidak ada pola asosiasi yang memenuhi threshold Support/Lift."
            )

        # TAHAP 2: DiGraph
        G = build_directed_graph(rules)
        if G.number_of_nodes() == 0:
            return AnalyticsResult(
                graph=None, rules=rules, centralities=None,
                community_map=None, modularity=0.0, communities=[],
                is_success=False,
                error_msg="Topologi graf kosong setelah penyaringan edge."
            )

        # TAHAP 3: Centralities (gabungan ZIP A + ZIP B)
        centralities_df = calculate_graph_centralities(G)

        # TAHAP 4: Community Detection (Louvain)
        community_map, mod_score, communities = detect_graph_communities(G)

        # TAHAP 5: Network Metrics (ZIP B — baru)
        net_metrics = calculate_network_metrics(G)

        # TAHAP 6: Robustness Simulation (ZIP B — baru)
        robustness_df = analyze_robustness(G)

        # TAHAP 7: Structural Vulnerabilities (ZIP B — baru)
        articulations, bridges = get_structural_vulnerabilities(G)

        return AnalyticsResult(
            graph=G,
            rules=rules,
            centralities=centralities_df,
            community_map=community_map,
            modularity=mod_score,
            communities=communities,
            network_metrics=net_metrics,
            robustness_df=robustness_df,
            articulations=articulations,
            bridges=bridges,
        )

    except Exception as e:
        return AnalyticsResult(
            graph=None, rules=None, centralities=None,
            community_map=None, modularity=0.0, communities=[],
            is_success=False,
            error_msg=str(e)
        )
