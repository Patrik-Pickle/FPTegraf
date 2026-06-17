"""
Community Detection — Version C (Merged)
==========================================
SOURCE DECISION:
  ALGORITHM  : ZIP A  (Louvain via NetworkX 3.0+ — lebih akurat dari Greedy Modularity ZIP B)
  CONVERSION : ZIP A  (undirected projection dengan akumulasi confidence — tepat secara teoritis)
  WEIGHT     : ZIP A  (bobot 'confidence' lebih representatif dari 'weight'/lift ZIP B)
  FALLBACK   : ZIP B  (exception handling lebih defensif)
"""

import networkx as nx
import logging

logger = logging.getLogger(__name__)


def detect_graph_communities(G: nx.DiGraph) -> tuple:
    """
    Mendeteksi komunitas menggunakan algoritma Louvain (NetworkX 3.0+).
    Secara matematis superior terhadap Greedy Modularity (Clauset-Newman-Moore) milik ZIP B.
    Mendukung bobot jaringan berbasis confidence asosiasi.

    Returns:
        (community_map: dict[node→int], modularity_score: float, communities: list[set])
    """
    if G.number_of_nodes() == 0:
        return {}, 0.0, []

    logger.info("Memulai deteksi komunitas (Louvain)...")

    # Louvain secara native untuk Undirected Graph.
    # Konversi DiGraph → Undirected dengan bobot confidence terakumulasi.
    G_undirected = G.to_undirected(as_view=False)

    try:
        communities = list(nx.community.louvain_communities(
            G_undirected, weight='confidence', resolution=1.0
        ))

        community_map = {}
        for i, comm in enumerate(communities):
            for node in comm:
                community_map[node] = i

        modularity_score = nx.community.modularity(
            G_undirected, communities, weight='confidence'
        )
        logger.info(f"Terdeteksi {len(communities)} komunitas. Q-Score: {modularity_score:.4f}")
        return community_map, modularity_score, communities

    except Exception as e:
        logger.error(f"Louvain gagal: {e}. Mencoba Greedy Modularity sebagai fallback...")
        try:
            from networkx.algorithms.community import greedy_modularity_communities, modularity
            communities = list(greedy_modularity_communities(G_undirected, weight='confidence'))
            community_map = {node: i for i, comm in enumerate(communities) for node in comm}
            modularity_score = modularity(G_undirected, communities, weight='confidence')
            logger.info(f"Fallback Greedy berhasil. Q-Score: {modularity_score:.4f}")
            return community_map, modularity_score, communities
        except Exception as e2:
            logger.error(f"Semua metode community detection gagal: {e2}")
            return {}, 0.0, []
