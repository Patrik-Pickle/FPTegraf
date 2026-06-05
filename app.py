import streamlit as st
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
import networkx as nx
import matplotlib.pyplot as plt
from networkx.algorithms.community import greedy_modularity_communities

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Market Basket Graph", layout="wide")
st.title("🛒 Dashboard Market Basket Analysis")
st.write("Unggah dataset transaksi untuk menganalisis keterhubungan produk menggunakan Algoritma Apriori dan Teori Graf.")

# --- PANDUAN FORMAT DATA ---
with st.expander("📌 Lihat Panduan Format Dataset (CSV)", expanded=False):
    st.write("Dataset harus dalam format `.csv` dan wajib memiliki 4 kolom persis seperti ini: `Member_number`, `Date`, `itemDescription`, dan `itemCategory`.")
    st.code("""Member_number,Date,itemDescription,itemCategory
1808,21-07-2015,tropical fruit,Makanan Segar
2552,05-01-2015,whole milk,Makanan Segar
2300,19-09-2015,pip fruit,Makanan Segar
1187,12-12-2015,other vegetables,Makanan Segar
...""", language="text")

# --- FUNGSI PIPELINE ---
@st.cache_data
def run_market_basket_graph(df, min_support, min_lift):
    # 1. Preprocessing
    df['Transaction_ID'] = df['Member_number'].astype(str) + "_" + df['Date'].astype(str)
    
    basket = (df.groupby(['Transaction_ID', 'itemDescription'])['itemDescription']
              .count().unstack().reset_index().fillna(0)
              .set_index('Transaction_ID'))
    
    basket_sets = basket > 0
    
    # 2. Apriori & Rules
    frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)
    
    if frequent_itemsets.empty:
        return pd.DataFrame(), nx.DiGraph()
        
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # 3. Membangun Graf
    G = nx.DiGraph()
    for idx, row in rules.iterrows():
        antecedent = list(row['antecedents'])[0]
        consequent = list(row['consequents'])[0]
        weight = row['lift']
        G.add_edge(antecedent, consequent, weight=weight)
        
    return rules, G

# --- SIDEBAR PENGATURAN ---
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV Dataset", type=['csv'])

st.sidebar.header("2. Tuning Parameter")
support_val = st.sidebar.slider("Minimum Support", min_value=0.0001, max_value=0.1000, value=0.0010, step=0.0001, format="%.4f")
lift_val = st.sidebar.slider("Minimum Lift", 0.1, 5.0, 1.0)

# --- EKSEKUSI & TAMPILAN ---
if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    
    if st.button("Jalankan Analisis", type="primary"):
        with st.spinner("Memproses algoritma..."):
            # Update validasi kolom untuk menyertakan itemCategory
            required_cols = {'Member_number', 'Date', 'itemDescription', 'itemCategory'}
            if not required_cols.issubset(df_raw.columns):
                st.error(f"Error: Dataset harus memiliki kolom: {required_cols}. Kolom terdeteksi: {set(df_raw.columns)}")
            else:
                rules_df, product_graph = run_market_basket_graph(df_raw, support_val, lift_val)
                
                if rules_df.empty:
                    st.warning("Tidak ditemukan pola hubungan (rules). Coba turunkan nilai Minimum Support atau Minimum Lift.")
                else:
                    st.success(f"Analisis Selesai! Ditemukan {len(rules_df)} kombinasi hubungan.")
                    
                    # Membuat kamus mapping (Barang -> Kategori)
                    item_to_cat = dict(zip(df_raw['itemDescription'], df_raw['itemCategory']))

                    # ==========================================
                    # DETEKSI KOMUNITAS
                    # ==========================================
                    undirected_G = product_graph.to_undirected()
                    try:
                        components = list(greedy_modularity_communities(undirected_G))
                        meaningful_groups = [list(comp) for comp in components if len(comp) > 1]
                        meaningful_groups.sort(key=len, reverse=True)
                    except:
                        components = [list(product_graph.nodes())]
                        meaningful_groups = []

                    # ==========================================
                    # SECTION: INSIGHT LANGSUNG
                    # ==========================================
                    st.markdown("---")
                    st.subheader("💡 Insight Langsung & Analisis Bisnis")
                    
                    insight_col1, insight_col2 = st.columns(2)
                    
                    with insight_col1:
                        st.markdown("**🏆 Top 5 Kombinasi Paling Kuat:**")
                        
                        insight_rules = rules_df.copy()
                        insight_rules['combined_items'] = insight_rules.apply(
                            lambda row: frozenset(row['antecedents'] | row['consequents']), axis=1
                        )
                        unique_top_rules = insight_rules.sort_values(
                            by=['lift', 'confidence'], ascending=[False, False]
                        ).drop_duplicates(subset=['combined_items']).head(5)
                        
                        for _, row in unique_top_rules.iterrows():
                            ant_list = list(row['antecedents'])
                            con_list = list(row['consequents'])
                            ant = ', '.join(ant_list)
                            con = ', '.join(con_list)
                            
                            # Mengambil label kategori untuk setiap barang utama
                            cat_ant = item_to_cat.get(ant_list[0], "Lainnya")
                            cat_con = item_to_cat.get(con_list[0], "Lainnya")
                            
                            st.write(f"- **{ant}** *({cat_ant})* ➔ **{con}** *({cat_con})* (Lift: {row['lift']:.2f})")
                            
                    with insight_col2:
                        st.markdown("**🔗 Analisis Komunitas Berdasarkan Kategori:**")
                        st.caption("Membedah isi komunitas graf untuk merekomendasikan strategi toko.")
                        
                        if meaningful_groups:
                            for i, group in enumerate(meaningful_groups[:5], 1):
                                # Hitung persentase dominasi kategori di komunitas ini
                                cat_counts = {}
                                for item in group:
                                    cat = item_to_cat.get(item, "Lain-lain")
                                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                                
                                sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
                                dominant_cat = sorted_cats[0][0]
                                dominant_pct = (sorted_cats[0][1] / len(group)) * 100
                                
                                # Menggunakan expander agar UI tidak terlalu penuh
                                with st.expander(f"**Komunitas {i}** - Didominasi: {dominant_cat} ({dominant_pct:.0f}%)", expanded=(i==1)):
                                    st.write(f"**Anggota:** {', '.join(group)}")
                                    
                                    # Output Analisis Bisnis Otomatis
                                    st.markdown("**Analisis Bisnis:**")
                                    if dominant_pct > 60:
                                        st.success(f"📌 Komunitas ini sangat homogen (didominasi **{dominant_cat}**). Pelanggan menunjukkan pola *restocking* kategori spesifik.\n\n**Rekomendasi:** Kelompokkan barang-barang ini di lorong (aisle) yang sama agar pembeli lebih mudah menemukan barang terkait.")
                                    else:
                                        second_cat = sorted_cats[1][0] if len(sorted_cats) > 1 else "kategori lain"
                                        st.info(f"⚡ Komunitas ini bersifat *lintas kategori*, utamanya menggabungkan **{dominant_cat}** dan **{second_cat}**. Ini adalah pola *Cross-Selling* natural.\n\n**Rekomendasi:** Buat promo 'Paket Bundling' atau pajang barang dari kategori {second_cat} di rak ujung (end-cap) dekat lorong {dominant_cat}.")
                        else:
                            st.write("Belum ada komunitas padat yang terbentuk.")
                            
                    st.markdown("---")
                    
                    # ==========================================
                    # SECTION: TABEL & GRAF
                    # ==========================================
                    col1, col2 = st.columns([1, 1.5])
                    
                    with col1:
                        st.subheader("Tabel Hubungan Produk")
                        display_df = rules_df[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
                        display_df['antecedents'] = display_df['antecedents'].apply(lambda x: ', '.join(list(x)))
                        display_df['consequents'] = display_df['consequents'].apply(lambda x: ', '.join(list(x)))
                        st.dataframe(display_df, hide_index=True)
                        
                    with col2:
                        st.subheader("Network Graph Visualisasi")
                        fig, ax = plt.subplots(figsize=(10, 8))
                        pos = nx.spring_layout(product_graph, k=1.5, seed=42)
                        
                        node_sizes = [max(dict(product_graph.degree)[node] * 300, 800) for node in product_graph.nodes()]
                        
                        community_map = {}
                        for i, comp in enumerate(components):
                            for node in comp:
                                community_map[node] = i
                                
                        cmap = plt.get_cmap('tab20')
                        color_palette = [cmap(i) for i in range(20)]
                        
                        node_colors = []
                        for node in product_graph.nodes():
                            idx = community_map.get(node, 0)
                            node_colors.append(color_palette[idx % len(color_palette)])
                        
                        nx.draw_networkx_nodes(product_graph, pos, node_color=node_colors, node_size=node_sizes, edgecolors='black', ax=ax)
                        nx.draw_networkx_edges(product_graph, pos, edge_color='#cccccc', arrows=True, ax=ax)
                        nx.draw_networkx_labels(product_graph, pos, font_size=9, font_weight='bold', font_family='sans-serif', ax=ax)
                        
                        plt.axis('off')
                        st.pyplot(fig)
else:
    st.info("👈 Silakan upload file CSV dataset kamu di menu Sidebar sebelah kiri terlebih dahulu.")
