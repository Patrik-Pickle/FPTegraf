"""
Graph Builder — Version C (Merged)
====================================
SOURCE DECISION:
  STRUCTURE  : ZIP A  (DiGraph — asimetri P(B|A) ≠ P(A|B) valid secara ilmiah)
  METRICS    : ZIP B  (calculate_network_metrics, analyze_robustness, get_structural_vulnerabilities)
               — fitur baru yang tidak ada di ZIP A, diadopsi penuh
"""

import networkx as nx
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_network_metrics(G: nx.DiGraph) -> dict:
    """
    Menghitung metrik makro topologi jaringan berdasarkan standar Newman (2010).
    Kompatibel dengan DiGraph — memperhitungkan arah aliran asosiatif.
    """
    if G.number_of_nodes() == 0:
        return {}

    # Konversi ke undirected untuk metrik topologi simetris
    G_und = G.to_undirected()

    metrics = {
        'Nodes': G.number_of_nodes(),
        'Edges': G.number_of_edges(),
        'Density': nx.density(G),
        'Average Degree': 2 * G_und.number_of_edges() / G.number_of_nodes(),
        'Clustering Coefficient': nx.average_clustering(G_und),
        'Connected Components': nx.number_weakly_connected_components(G)
    }

    # Diameter dihitung pada undirected projection (Largest Connected Component)
    if nx.is_connected(G_und):
        metrics['Diameter'] = nx.diameter(G_und)
    else:
        largest_cc = max(nx.connected_components(G_und), key=len)
        subgraph = G_und.subgraph(largest_cc)
        metrics['Diameter (LCC)'] = nx.diameter(subgraph)

    return metrics


def analyze_robustness(G: nx.DiGraph) -> pd.DataFrame:
    """
    Simulasi dekonstruksi jaringan retail akibat efek domino stok kosong (Albert et al., 2000).
    Menggunakan undirected projection agar metrik LCC konsisten.
    """
    if G.number_of_nodes() == 0:
        return pd.DataFrame()

    G_sim = G.to_undirected()
    initial_nodes = G_sim.number_of_nodes()
    nodes_removed = 0

    results = [{
        'Nodes Removed': 0,
        'LCC Size (Fraction)': 1.0,
        'Number of Components': nx.number_connected_components(G_sim)
    }]

    target_removals = max(1, int(initial_nodes * 0.25))

    for _ in range(target_removals):
        if G_sim.number_of_nodes() == 0:
            break

        degrees = dict(G_sim.degree())
        highest_degree_node = max(degrees, key=degrees.get)
        G_sim.remove_node(highest_degree_node)
        nodes_removed += 1

        if G_sim.number_of_nodes() > 0:
            largest_cc = max(nx.connected_components(G_sim), key=len)
            lcc_fraction = len(largest_cc) / initial_nodes
            n_components = nx.number_connected_components(G_sim)
        else:
            lcc_fraction = 0.0
            n_components = 0

        results.append({
            'Nodes Removed': nodes_removed,
            'LCC Size (Fraction)': lcc_fraction,
            'Number of Components': n_components
        })

    return pd.DataFrame(results)


def get_structural_vulnerabilities(G: nx.DiGraph) -> tuple:
    """
    Mendeteksi Articulation Points dan Bridges pada undirected projection.
    Fitur baru dari ZIP B — tidak ada di ZIP A.
    """
    if G.number_of_nodes() == 0:
        return [], []
    G_und = G.to_undirected()
    return list(nx.articulation_points(G_und)), list(nx.bridges(G_und))
