import pandas as pd
import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities, modularity
from mlxtend.frequent_patterns import apriori, association_rules

# def bangun_graph_dari_transaksi(df, min_support=0.001, min_lift=1.0):

#     df = df.copy()

#     df['Transaction_ID'] = (
#         df['Member_number'].astype(str)
#         + "_"
#         + df['Date'].astype(str)
#     )

#     basket = pd.crosstab(
#         df['Transaction_ID'],
#         df['itemDescription']
#     )

#     basket_sets = basket > 0

#     frequent_itemsets = apriori(
#         basket_sets,
#         min_support=min_support,
#         use_colnames=True
#     )

#     if frequent_itemsets.empty:
#         return nx.Graph()

#     rules = association_rules(
#         frequent_itemsets,
#         metric='lift',
#         min_threshold=min_lift
#     )

#     G = nx.Graph()

#     for _, row in rules.iterrows():

#         antecedents = list(row['antecedents'])
#         consequents = list(row['consequents'])

#         for ant in antecedents:
#             for con in consequents:

#                 if ant == con:
#                     continue

#                 weight = row['lift']

#                 if G.has_edge(ant, con):
#                     G[ant][con]['weight'] = max(
#                         G[ant][con]['weight'],
#                         weight
#                     )
#                 else:
#                     G.add_edge(
#                         ant,
#                         con,
#                         weight=weight,
#                         support=row['support'],
#                         confidence=row['confidence']
#                     )

#     return G



# from networkx.algorithms.community import (
#     greedy_modularity_communities,
#     modularity
# )

# def deteksi_komunitas(G):

#     if G.number_of_nodes() == 0:
#         return {}, 0, []

#     communities = list(
#         greedy_modularity_communities(
#             G,
#             weight='weight'
#         )
#     )

#     community_map = {}

#     for i, comm in enumerate(communities):
#         for node in comm:
#             community_map[node] = i

#     modularity_score = modularity(
#         G,
#         communities,
#         weight='weight'
#     )

#     return community_map, modularity_score, communities



def build_graph_from_transactions(df, min_support=0.001, min_lift=1.0):
    #Membangun Graf Produk (undirected) dari data transaksi menggunakan apriori
    df['Transaction_ID']= df['Member_number'].astype(str) + "_" + df['Date'].astype(str)

    # basket = pd.crosstab(
    # df['Transaction_ID'],
    # df['itemDescription'])
    basket = (df.groupby(['Transaction_ID', 'itemDescription'])['itemDescription']
              .count().unstack().reset_index().fillna(0)
              .set_index('Transaction_ID'))
    
    # basket_sets= basket >0
    basket_sets = basket.astype(bool)
    frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)

    if frequent_itemsets.empty:
        return nx.Graph()
    
    rules= association_rules(frequent_itemsets, metric='lift', min_threshold=min_lift)

    # Menggunakan Undirected Graph untuk Analisis Komunitas dan Ketahanan Rak
    G= nx.Graph()
    for _, row in rules.iterrows():
        ant= list(row['antecedents'])[0]
        con= list(row['consequents'])[0]
        weight= row['lift']

        #mencegah Self-loop
        if ant!=con:
            if G.has_edge(ant, con):
                G[ant][con]['weight']= max(G[ant][con]['weight'], weight)
            else:
                G.add_edge(ant,con, weight=weight)
                # G.add_edge(ant,
                #            con,
                #            weight=row['lift'],
                #            support=row['support'],
                #            confidence=row['confidence']
                #             )

    return G

# def calculate_network_metrics(G):
#     #Menghitung metrik dasar Jaringan (Newmann, 2010)
#     if G.number_of_nodes()==0:
#         return {}
    
#     metrics= {
#         'Nodes': G.number_of_nodes(),
#         'Edges': G.number_of_edges(),
#         'Density': nx.density(G),
#         # 'Average Degree': sum(dict(G.degree()).values()) / G.number_of_nodes(),
#         # 'Average Degree': sum(d for _, d in G.degree()) / G.number_of_nodes(), 
#         'Average Degree': 2 * G.number_of_edges() / G.number_of_nodes(), #K= 2E/N 
#         'Clustering Coefficient': nx.average_clustering(G),
#         'Connected Components': nx.number_connected_components(G)
#     }

#     #Diameter hanya bisa dihitung pada kompnen yang terhubung penuh
#     if nx.is_connected(G):
#         metrics['Diameter']= nx.diameter(G)
#     else:
#         # Hitung diameter dari largest Connected Component (LCC)
#         largest_cc= max(nx.connected_components, key=len)
#         subgraph= G.subgraph(largest_cc)
#         metrics['Diameter (LCC)']= nx.diameter(subgraph)

#     return metrics

def calculate_network_metrics(G):
    # Menghitung metrik dasar Jaringan (Newmann, 2010)
    if G.number_of_nodes() == 0:
        return {}
    
    metrics = {
        'Nodes': G.number_of_nodes(),
        'Edges': G.number_of_edges(),
        'Density': nx.density(G),
        'Average Degree': 2 * G.number_of_edges() / G.number_of_nodes(), # K= 2E/N 
        'Clustering Coefficient': nx.average_clustering(G),
        'Connected Components': nx.number_connected_components(G)
    }

    # Diameter hanya bisa dihitung pada komponen yang terhubung penuh
    if nx.is_connected(G):
        metrics['Diameter'] = nx.diameter(G)
    else:
        # FIX: Tambahkan (G) pada nx.connected_components
        largest_cc = max(nx.connected_components(G), key=len)
        subgraph = G.subgraph(largest_cc)
        metrics['Diameter (LCC)'] = nx.diameter(subgraph)

    return metrics

def calculate_centralities(G):
    #Menghitung Degree, Betweeness, Closeness, dan Eigenvector centrality - Freeman, 1970
    if G.number_of_nodes()==0:
        return pd.DataFrame()
    
    deg_cent= nx.degree_centrality(G)
    bet_cent= nx.betweenness_centrality(G, weight='weight')
    clo_cent= nx.closeness_centrality(G)

    try:
        eig_cent= nx.eigenvector_centrality(G,max_iter=1000, weight='weight')
    except:
        #fallback jika konvergensi gagal
        eig_cent= {node:0 for node in G.nodes()}

    df= pd.DataFrame({
        'Product': list(G.nodes()),
        'Degree Centrality': [deg_cent[node] for node in G.nodes()],
        'Betweenness Centrality': [bet_cent[node] for node in G.nodes()],
        'Closeness Centrality': [clo_cent[node] for node in G.nodes()],
        'Eigenvector Centrality': [eig_cent[node] for node in G.nodes()]
    })

    return df

def detect_communities(G):
    # FIX: Tambahkan pengecekan jumlah edges untuk mencegah ZeroDivisionError
    if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
        return {}, 0, []
    
    # Menggunakan Clauset-Newman-Moore Greedy Modularity Maximization
    communities = list(greedy_modularity_communities(G))

    community_map = {}
    for i, comm in enumerate(communities):
        for node in comm:
            community_map[node] = i

    modularity_score = modularity(G, communities)

    return community_map, modularity_score, communities

def analyze_robustness(G):
    """Simulasi serangan bertarget (Targeted Attack) pada node paling sentral (Albert, Jeong, Barabási, 2000)."""
    if G.number_of_nodes() == 0:
        return pd.DataFrame()
        
    G_sim = G.copy()
    nodes_removed = 0
    
    results = [{
        'Nodes Removed': 0,
        'LCC Size (Fraction)': 1.0,
        'Number of Components': nx.number_connected_components(G_sim)
    }]
    
    initial_nodes = G_sim.number_of_nodes()
    
    # Hapus 20% node paling penting (Degree tertinggi) secara berurutan
    target_removals = max(1, int(initial_nodes * 0.2))
    
    for _ in range(target_removals):
        if G_sim.number_of_nodes() == 0:
            break
            
        # Cari node dengan degree tertinggi saat ini
        degrees = dict(G_sim.degree())
        highest_degree_node = max(degrees, key=degrees.get)
        
        G_sim.remove_node(highest_degree_node)
        nodes_removed += 1
        
        if G_sim.number_of_nodes() > 0:
            largest_cc = max(nx.connected_components(G_sim), key=len)
            lcc_fraction = len(largest_cc) / initial_nodes
            n_components = nx.number_connected_components(G_sim)
        else:
            lcc_fraction = 0
            n_components = 0
            
        results.append({
            'Nodes Removed': nodes_removed,
            'LCC Size (Fraction)': lcc_fraction,
            'Number of Components': n_components
        })
        
    return pd.DataFrame(results)

def get_structural_vulnerabilities(G):
    """Mendeteksi Articulation Points (Cut Vertices) dan Bridges."""
    if G.number_of_nodes() == 0:
        return [], []
    
    articulation_points = list(nx.articulation_points(G))
    bridges = list(nx.bridges(G))
    
    return articulation_points, bridges


    