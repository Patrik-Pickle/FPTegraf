"""
Centrality Metrics — Version C (Merged)
=========================================
SOURCE DECISION:
  PageRank + In/Out Strength : ZIP A  (lebih akurat untuk DiGraph; tidak ada di ZIP B)
  Lift→Distance transform    : ZIP B  (matematika betweenness & closeness lebih tepat)
  Approx Betweenness (k)     : ZIP A  (pencegahan TLE untuk dataset besar)
  Eigenvector Centrality     : ZIP B  (ada konvergensi guard)
  Output columns             : MERGE  (gabungan kolom terbaik keduanya)
"""

import networkx as nx
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_graph_centralities(G: nx.DiGraph) -> pd.DataFrame:
    """
    Menghitung metrik sentralitas multidimensi berbasis sains jaringan.

    Metrik yang dihitung:
      - PageRank Centrality     : Pengganti superior Eigenvector untuk DiGraph (ZIP A)
      - In-Strength (Target)    : Seberapa sering produk menjadi tujuan pembelian (ZIP A)
      - Out-Strength (Source)   : Seberapa sering produk memicu pembelian lain (ZIP A)
      - Degree Centrality       : Jumlah tetangga langsung (diperlukan Tab 2 chart ZIP B)
      - Betweenness Centrality  : Produk jembatan trans-sektoral, dengan Lift→Distance (ZIP B)
      - Closeness Centrality    : Kecepatan aksesibilitas ke seluruh katalog (ZIP B)
      - Eigenvector Centrality  : Pengaruh sistemik berbasis kualitas tetangga (ZIP B)
    """
    if G.number_of_nodes() == 0:
        return pd.DataFrame()

    logger.info("Kalkulasi metrik sentralitas multidimensi dimulai...")
    nodes = list(G.nodes())

    # ── 1. PAGERANK (ZIP A) ──────────────────────────────────────────────────
    try:
        pagerank_cent = nx.pagerank(G, weight='confidence', alpha=0.85)
    except Exception as e:
        logger.warning(f"PageRank gagal konvergen: {e}. Default ke 0.")
        pagerank_cent = {n: 0.0 for n in nodes}

    # ── 2. WEIGHTED NODE STRENGTH (ZIP A) ────────────────────────────────────
    in_strength = dict(G.in_degree(weight='confidence'))
    out_strength = dict(G.out_degree(weight='confidence'))

    # ── 3. DEGREE CENTRALITY — pada undirected projection (untuk chart ZIP B) ─
    G_und = G.to_undirected()
    deg_cent = nx.degree_centrality(G_und)

    # ── 4. LIFT → DISTANCE TRANSFORM (ZIP B) ─────────────────────────────────
    # Semakin tinggi Lift, semakin DEKAT produk secara psikologis (jarak mendekati 0)
    # Diperlukan agar Betweenness & Closeness menghitung path optimal secara benar
    G_dist = G_und.copy()
    for u, v, d in G_dist.edges(data=True):
        raw_lift = d.get('lift', d.get('weight', 1.0))
        d['distance'] = 1.0 / max(raw_lift, 1e-9)  # guard division-by-zero

    # ── 5. BETWEENNESS — Approx k-sampling untuk skala enterprise (ZIP A) ────
    num_nodes = G.number_of_nodes()
    k_samples = None
    if num_nodes > 500:
        k_samples = max(100, int(num_nodes * 0.1))
        logger.info(f"Grafik besar ({num_nodes} nodes). Approx Betweenness (k={k_samples}).")
    bet_cent = nx.betweenness_centrality(G_dist, k=k_samples, weight='distance')

    # ── 6. CLOSENESS (ZIP B) ─────────────────────────────────────────────────
    clo_cent = nx.closeness_centrality(G_dist, distance='distance')

    # ── 7. EIGENVECTOR CENTRALITY — dengan konvergensi guard (ZIP B) ─────────
    try:
        eig_cent = nx.eigenvector_centrality(G_und, max_iter=2000, weight='weight')
    except nx.PowerIterationFailedConvergence:
        logger.warning("Eigenvector Centrality tidak konvergen. Default ke 0.")
        eig_cent = {node: 0.0 for node in nodes}

    df = pd.DataFrame({
        'Product': nodes,
        'PageRank Centrality': [pagerank_cent.get(n, 0.0) for n in nodes],
        'In-Strength (Target)': [in_strength.get(n, 0) for n in nodes],
        'Out-Strength (Source)': [out_strength.get(n, 0) for n in nodes],
        'Degree Centrality': [deg_cent.get(n, 0.0) for n in nodes],
        'Betweenness Centrality': [bet_cent.get(n, 0.0) for n in nodes],
        'Closeness Centrality': [clo_cent.get(n, 0.0) for n in nodes],
        'Eigenvector Centrality': [eig_cent.get(n, 0.0) for n in nodes],
    })

    return df
