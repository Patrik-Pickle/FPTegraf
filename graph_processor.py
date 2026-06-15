import pandas as pd
import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities, modularity
from mlxtend.frequent_patterns import apriori, association_rules

def build_graph_from_transactions(df: pd.DataFrame, min_support: float = 0.001, min_lift: float = 1.0) -> nx.Graph:
    """
    Membangun Undirected Graph dari data transaksi ritel menggunakan algoritma Apriori.
    Mengoptimalkan pemrosesan multi-item dari association rules secara efisien.
    """
    # Membuat ID Transaksi yang unik
    df = df.copy()
    df['Transaction_ID'] = df['Member_number'].astype(str) + "_" + df['Date'].astype(str)

    # Membangun matriks transaksi biner yang ramah memori (menggunakan asType bool secara langsung)
    basket = (df.groupby(['Transaction_ID', 'itemDescription'])['itemDescription']
              .count()
              .unstack(fill_value=0)
              .astype(bool))
    
    # Ekstraksi Frequent Itemsets
    frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)

    if frequent_itemsets.empty:
        return nx.Graph()
    
    # Ekstraksi Aturan Asosiasi
    rules = association_rules(frequent_itemsets, metric='lift', min_threshold=min_lift)

    if rules.empty:
        return nx.Graph()

    G = nx.Graph()
    
    # Perbaikan Utama: Mengatasi multi-item antecedents & consequents dengan nested loop
    for _, row in rules.iterrows():
        antecedents = list(row['antecedents'])
        consequents = list(row['consequents'])
        lift_val = row['lift']
        support_val = row['support']
        confidence_val = row['confidence']

        for ant in antecedents:
            for con in consequents:
                if ant != con:
                    if G.has_edge(ant, con):
                        # Pertahankan nilai Lift tertinggi sebagai bobot kekuatan korelasi
                        G[ant][con]['weight'] = max(G[ant][con]['weight'], lift_val)
                    else:
                        G.add_edge(ant, con, weight=lift_val, support=support_val, confidence=confidence_val)
    return G

def calculate_network_metrics(G: nx.Graph) -> dict:
    """Menghitung metrik makro topologi jaringan berdasarkan standar Newman (2010)."""
    if G.number_of_nodes() == 0:
        return {}
    
    metrics = {
        'Nodes': G.number_of_nodes(),
        'Edges': G.number_of_edges(),
        'Density': nx.density(G),
        'Average Degree': 2 * G.number_of_edges() / G.number_of_nodes(), 
        'Clustering Coefficient': nx.average_clustering(G),
        'Connected Components': nx.number_connected_components(G)
    }

    # Perbaikan Bug: Penanganan eksekusi fungsi connected_components
    if nx.is_connected(G):
        metrics['Diameter'] = nx.diameter(G)
    else:
        largest_cc = max(nx.connected_components(G), key=len)
        subgraph = G.subgraph(largest_cc)
        metrics['Diameter (LCC)'] = nx.diameter(subgraph)

    return metrics

def calculate_centralities(G: nx.Graph) -> pd.DataFrame:
    """
    Menghitung metrik sentralitas aktor kunci (Freeman, 1978).
    Perbaikan: Melakukan transformasi Lift -> Jarak Jauh untuk visualisasi Shortest Path.
    """
    if G.number_of_nodes() == 0:
        return pd.DataFrame()
    
    # Perbaikan Utama: Balikkan makna Lift menjadi Jarak Matematis (Distance Cost)
    G_dist = G.copy()
    for u, v, d in G_dist.edges(data=True):
        # Semakin tinggi Lift, semakin dekat jarak psikologis antar produk (distance mendekati 0)
        d['distance'] = 1.0 / d['weight']
    
    # Derajat keterhubungan langsung (tidak dipengaruhi jarak)
    deg_cent = nx.degree_centrality(G)
    
    # Metrik penengah lintasan informasi (wajib menggunakan metrik jarak hasil transformasi)
    bet_cent = nx.betweenness_centrality(G_dist, weight='distance')
    
    # Metrik kecepatan aksesibilitas ke seluruh simpul
    clo_cent = nx.closeness_centrality(G_dist, distance='distance')

    # Metrik pengaruh kualitas tetangga (menggunakan kedekatan matriks adjacency / Bobot Asli)
    try:
        eig_cent = nx.eigenvector_centrality(G, max_iter=2000, weight='weight')
    except nx.PowerIterationFailedConvergence:
        eig_cent = {node: 0.0 for node in G.nodes()}

    df = pd.DataFrame({
        'Product': list(G.nodes()),
        'Degree Centrality': [deg_cent[node] for node in G.nodes()],
        'Betweenness Centrality': [bet_cent[node] for node in G.nodes()],
        'Closeness Centrality': [clo_cent[node] for node in G.nodes()],
        'Eigenvector Centrality': [eig_cent[node] for node in G.nodes()]
    })

    return df

def detect_communities(G: nx.Graph) -> tuple:
    """Deteksi komunitas belanja modularitas tinggi menggunakan bobot korelasi transaksi."""
    if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
        return {}, 0.0, []
    
    # Perbaikan Utama: Sertakan bobot 'weight' (Lift) agar hasil pengelompokan akurat secara ritel
    communities = list(greedy_modularity_communities(G, weight='weight'))

    community_map = {}
    for i, comm in enumerate(communities):
        for node in comm:
            community_map[node] = i

    modularity_score = modularity(G, communities, weight='weight')

    return community_map, modularity_score, communities

def analyze_robustness(G: nx.Graph) -> pd.DataFrame:
    """Simulasi dekonstruksi jaringan retail akibat efek domino stok kosong (Albert et al., 2000)."""
    if G.number_of_nodes() == 0:
        return pd.DataFrame()
        
    G_sim = G.copy()
    nodes_removed = 0
    initial_nodes = G_sim.number_of_nodes()
    
    results = [{
        'Nodes Removed': 0,
        'LCC Size (Fraction)': 1.0,
        'Number of Components': nx.number_connected_components(G_sim)
    }]
    
    # Hapus 25% simpul vital secara bertahap
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

def get_structural_vulnerabilities(G: nx.Graph) -> tuple:
    """Mendeteksi simpul pemutus alur transaksi (Articulation Points) dan jembatan antar klaster (Bridges)."""
    if G.number_of_nodes() == 0:
        return [], []
    return list(nx.articulation_points(G)), list(nx.bridges(G))

    