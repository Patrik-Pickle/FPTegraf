import streamlit as st
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
import networkx as nx
import matplotlib.pyplot as plt

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Market Basket Graph", layout="wide")
st.title("🛒 Dashboard Market Basket Analysis")
st.write("Analisis keterhubungan produk menggunakan Algoritma Apriori dan Teori Graf.")

# --- FUNGSI PIPELINE ---
def run_market_basket_graph(df, min_support, min_lift):
    # Preprocessing
    basket = (df.groupby(['MemberID', 'Item'])['Item']
              .count().unstack().reset_index().fillna(0)
              .set_index('MemberID'))
    basket_sets = basket.map(lambda x: 1 if x > 0 else 0).astype(bool)
    
    # Apriori & Rules
    frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # Membangun Graf
    G = nx.DiGraph()
    for idx, row in rules.iterrows():
        antecedent = list(row['antecedents'])[0]
        consequent = list(row['consequents'])[0]
        weight = row['lift']
        G.add_edge(antecedent, consequent, weight=weight)
        
    return rules, G

# --- SIMULASI DATA (Bisa diganti dengan st.file_uploader nantinya) ---
data = {
    'MemberID': ['M01', 'M01', 'M01', 'M02', 'M02', 'M03', 'M03', 'M03', 'M04', 'M04'],
    'Item': ['Susu', 'Roti', 'Mentega', 'Susu', 'Roti', 'Susu', 'Sereal', 'Mentega', 'Roti', 'Selai']
}
df_raw = pd.DataFrame(data)

# --- SIDEBAR UNTUK PENGATURAN PARAMETER ---
st.sidebar.header("Tuning Parameter")
support_val = st.sidebar.slider("Minimum Support", 0.01, 1.0, 0.2)
lift_val = st.sidebar.slider("Minimum Lift", 0.1, 5.0, 1.0)

# --- EKSEKUSI & TAMPILAN ---
if st.button("Jalankan Analisis"):
    rules_df, product_graph = run_market_basket_graph(df_raw, support_val, lift_val)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Data Association Rules")
        st.dataframe(rules_df[['antecedents', 'consequents', 'support', 'confidence', 'lift']])
        
    with col2:
        st.subheader("Network Graph Keterhubungan")
        
        # Plotting dengan Matplotlib
        fig, ax = plt.subplots(figsize=(8, 6))
        pos = nx.spring_layout(product_graph, seed=42)
        
        # Node & Edges
        nx.draw_networkx_nodes(product_graph, pos, node_color='#00f2ff', node_size=2000, ax=ax)
        nx.draw_networkx_edges(product_graph, pos, edge_color='gray', ax=ax)
        nx.draw_networkx_labels(product_graph, pos, font_size=10, font_weight='bold', ax=ax)
        
        plt.axis('off')
        
        # Tampilkan grafik matplotlib di dalam Streamlit
        st.pyplot(fig)