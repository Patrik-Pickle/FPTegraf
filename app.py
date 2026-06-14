import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import networkx as nx

from graph_processor import (build_graph_from_transactions, calculate_network_metrics, 
                             calculate_centralities, detect_communities, 
                             analyze_robustness, get_structural_vulnerabilities)
from visualizer import (create_pyvis_network, plot_top_centralities, plot_robustness)

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="ShelfGraph Analytics", layout="wide", page_icon="🛒")

st.title("🛒 ShelfGraph Analytics: Optimasi Tata Letak Rak Retail")
st.markdown("""
Sistem Analisis Struktur Jaringan Produk menggunakan **Teori Graf** berdasarkan literatur Freeman (1978), 
Newman (2006, 2010), dan Albert et al. (2000). Dashboard ini dirancang untuk akademisi, mahasiswa, dan manajer ritel.
""")

# --- SIDEBAR PENGATURAN ---
st.sidebar.header("📁 1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload CSV Dataset (Format Market Basket)", type=['csv'])

st.sidebar.header("⚙️ 2. Parameter Jaringan")
support_val = st.sidebar.slider("Minimum Support", min_value=0.0001, max_value=0.0500, value=0.0010, step=0.0001)
lift_val = st.sidebar.slider("Minimum Lift", 0.1, 5.0, 1.0)

# --- FUNGSI UTAMA ---
if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    
    required_cols = {'Member_number', 'Date', 'itemDescription', 'itemCategory'}
    if not required_cols.issubset(df_raw.columns):
        st.error(f"Dataset harus memiliki kolom: {required_cols}. Mohon periksa kembali file Anda.")
        st.stop()
        
    if st.sidebar.button("🚀 Jalankan Analisis Ekstensif", type="primary"):
        with st.spinner("Memproses Model Teori Graf..."):
            
            # 1. Ekstraksi Jaringan
            G = build_graph_from_transactions(df_raw, support_val, lift_val)
            
            if G.number_of_nodes() == 0:
                st.warning("⚠️ Graf kosong. Coba turunkan Minimum Support atau Lift.")
                st.stop()
                
            # 2. Kalkulasi Metrik & Teori
            metrics = calculate_network_metrics(G)
            centralities_df = calculate_centralities(G)
            community_map, modularity_score, communities = detect_communities(G)
            robustness_df = analyze_robustness(G)
            articulations, bridges = get_structural_vulnerabilities(G)
            
            # --- TAB NAVIGASI ---
            tab1, tab2, tab3, tab4 = st.tabs([
                "🌐 A. Network Overview", 
                "👑 B. Top Influential Products (Centrality)", 
                "🏘️ C. Community & Shelf Layout", 
                "🛡️ D. Network Robustness"
            ])
            
            # ====================================================
            # TAB 1: NETWORK OVERVIEW
            # ====================================================
            with tab1:
                st.header("Visualisasi Struktur Makro Jaringan")
                st.markdown("Menganalisis topologi keseluruhan jaringan berdasarkan metrik Newman (2010).")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.subheader("📊 Metrik Jaringan")
                    for k, v in metrics.items():
                        if isinstance(v, float):
                            st.metric(label=k, value=f"{v:.4f}")
                        else:
                            st.metric(label=k, value=str(v))
                            
                    st.markdown("---")
                    st.subheader("💡 Interpretasi Metrik")
                    st.info(f"Jaringan ini memiliki kepadatan (Density) sebesar **{metrics['Density']:.4f}**. "
                            f"Rata-rata setiap produk terhubung dengan **{metrics['Average Degree']:.1f}** produk lainnya. "
                            f"Koefisien Clustering **{metrics.get('Clustering Coefficient', 0):.4f}** mengindikasikan seberapa kuat kecenderungan produk membentuk kelompok padat (triangle).")
                            
                with col2:
                    st.subheader("Graf Interaktif PyVis")
                    html_path = create_pyvis_network(G, community_map, centralities_df)
                    with open(html_path, 'r', encoding='utf-8') as f:
                        components.html(f.read(), height=650)
                    os.remove(html_path)  # Cleanup
                    
            # ====================================================
            # TAB 2: CENTRALITY & INFLUENCERS
            # ====================================================
            with tab2:
                st.header("Analisis Aktor Kunci (Centrality Measures)")
                st.markdown("Berdasarkan konsep Sentralitas oleh **Freeman (1978)**. Metrik ini krusial untuk menemukan produk *Hub* dan *Bridge*.")
                
                c1, c2 = st.columns(2)
                
                top_degree = centralities_df.sort_values(by='Degree Centrality', ascending=False).iloc[0]['Product']
                top_between = centralities_df.sort_values(by='Betweenness Centrality', ascending=False).iloc[0]['Product']
                
                with c1:
                    st.plotly_chart(plot_top_centralities(centralities_df, 'Degree Centrality', 'Top 10 Degree Centrality (Produk Terpopuler)', '#1f77b4'), use_container_width=True)
                    st.plotly_chart(plot_top_centralities(centralities_df, 'Closeness Centrality', 'Top 10 Closeness Centrality (Aksesibilitas Cepat)', '#2ca02c'), use_container_width=True)
                    
                with c2:
                    st.plotly_chart(plot_top_centralities(centralities_df, 'Betweenness Centrality', 'Top 10 Betweenness Centrality (Produk Jembatan)', '#ff7f0e'), use_container_width=True)
                    st.plotly_chart(plot_top_centralities(centralities_df, 'Eigenvector Centrality', 'Top 10 Eigenvector Centrality (Pengaruh Kualitas)', '#d62728'), use_container_width=True)

                st.subheader("💡 Interpretasi Otomatis (Insight Bisnis)")
                st.success(f"**Insight 1:** Produk **'{top_degree}'** memiliki Degree Centrality tertinggi. Ini adalah produk utama yang paling sering dibeli bersama produk lain. Posisikan di **tengah area belanja** sebagai jangkar (Anchor Product) penarik trafik pengunjung.")
                st.warning(f"**Insight 2:** Produk **'{top_between}'** memiliki Betweenness tertinggi. Produk ini bertindak sebagai 'jembatan' antar kategori berbeda. Menempatkannya di **persimpangan lorong utama** (main aisles intersection) akan mendorong pembeli menjelajahi bagian rak yang berbeda.")

            # ====================================================
            # TAB 3: COMMUNITY & SHELF LAYOUT
            # ====================================================
            with tab3:
                st.header("Struktur Komunitas & Rekomendasi Tata Letak Rak")
                st.markdown(f"Menggunakan algoritma Greedy Modularity Maximization (**Newman, 2006**). Skor Modularity saat ini: **{modularity_score:.4f}**.")
                
                if modularity_score > 0.3:
                    st.success("Skor modularitas > 0.3 menunjukkan struktur komunitas yang kuat dan terdefinisi dengan jelas.")
                else:
                    st.info("Skor modularitas rendah (<0.3). Hubungan antar produk cenderung acak atau tersebar secara merata.")

                st.subheader("Rekomendasi Pemetaan Rak (Aisle Optimization)")
                
                cols = st.columns(3)
                for i, comm in enumerate(communities):
                    if len(comm) < 2:
                        continue # Skip isolated nodes for shelf layout
                    col_idx = i % 3
                    with cols[col_idx]:
                        with st.container(border=True):
                            st.markdown(f"### 🛒 Rak / Zona {i+1}")
                            st.write(f"**Jumlah Barang:** {len(comm)}")
                            st.markdown("**Barang yang harus berdekatan:**")
                            
                            # Tampilkan top 5 barang dari komunitas berdasarkan degree dalam subgraf
                            sub_g = G.subgraph(comm)
                            sub_deg = nx.degree_centrality(sub_g)
                            top_items = sorted(sub_deg, key=sub_deg.get, reverse=True)[:5]
                            
                            for item in top_items:
                                st.write(f"- {item}")
                            if len(comm) > 5:
                                st.caption(f"... dan {len(comm)-5} barang lainnya.")
                                
                st.markdown("---")
                st.subheader("💡 Interpretasi Strategis Rak")
                st.info("Berdasarkan deteksi komunitas, produk-produk dalam satu **Zona Rak** di atas sering kali masuk ke keranjang belanja secara bersamaan (Co-purchasing). Tata letak rak direkomendasikan dengan menempatkan produk yang berada dalam komunitas yang sama pada area lorong (aisle) yang berdekatan untuk meminimalkan *search cost* pembeli dan meningkatkan kenyamanan berbelanja (Impulse Buying).")

            # ====================================================
            # TAB 4: NETWORK ROBUSTNESS & VULNERABILITY
            # ====================================================
            with tab4:
                st.header("Ketahanan Jaringan (Network Robustness)")
                st.markdown("Simulasi serangan terarah (Targeted Attack) pada node *hub* (**Albert, Jeong, Barabási, 2000**).")
                
                r_col1, r_col2 = st.columns([2, 1])
                
                with r_col1:
                    st.plotly_chart(plot_robustness(robustness_df), use_container_width=True)
                    
                with r_col2:
                    st.subheader("Titik Kritis Jaringan")
                    st.write(f"**Jumlah Articulation Points:** {len(articulations)}")
                    st.write(f"**Jumlah Bridges:** {len(bridges)}")
                    
                    with st.expander("Lihat Articulation Points (Cut Vertices)"):
                        st.write(articulations if articulations else "Tidak ditemukan titik rentan.")
                        
                st.subheader("💡 Interpretasi Ketahanan Jaringan")
                if len(robustness_df) > 1:
                    drop_percent = (1.0 - robustness_df.iloc[-1]['LCC Size (Fraction)']) * 100
                    st.error(f"Penghapusan {robustness_df['Nodes Removed'].max()} produk paling sentral menyebabkan ukuran komponen utama jaringan menurun drastis sebesar **{drop_percent:.1f}%** dan terpecah menjadi **{robustness_df['Number of Components'].max()}** klaster terpisah.")
                    st.warning("Dalam konteks bisnis (Supply Chain/Stockout): Jika produk-produk utama (Hubs) ini mengalami **kekosongan stok (Out of Stock)**, efek dominonya akan memutus rantai penjualan barang pelengkap lainnya secara signifikan. Manajemen inventaris harus memprioritaskan ketersediaan (Safety Stock) untuk produk-produk ini di atas yang lainnya.")

else:
    st.info("👈 Silakan mulai dengan mengunggah dataset berformat CSV di menu samping. (Pastikan format kolom: Member_number, Date, itemDescription, itemCategory)")
