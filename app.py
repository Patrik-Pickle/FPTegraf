import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import networkx as nx

from graph_processor import (build_graph_from_transactions, calculate_network_metrics, 
                             calculate_centralities, detect_communities, 
                             analyze_robustness, get_structural_vulnerabilities)
from visualizer import (create_pyvis_network, plot_top_centralities, plot_robustness)

# --- KONFIGURASI HALAMAN UTAMA ---
st.set_page_config(page_title="ShelfGraph Analytics", layout="wide", page_icon="🛒")

st.title("🛒 ShelfGraph Analytics: Optimasi Tata Letak Rak Retail")
st.markdown("""
Sistem Analisis Struktur Jaringan Produk menggunakan **Complex Network Science** berbasis literatur 
Freeman (1978), Newman (2006, 2010), dan Albert et al. (2000).
""")
st.markdown("---")

# --- SIDEBAR PENGATURAN PARAMETER ---
st.sidebar.header("📁 1. Manajemen Berkas")
uploaded_file = st.sidebar.file_uploader("Unggah Dataset CSV (Format Transaksi Market Basket)", type=['csv'])

st.sidebar.header("⚙️ 2. Parameter Kunci Kombinatorik")
support_val = st.sidebar.slider("Minimum Support", min_value=0.0001, max_value=0.0500, value=0.0010, step=0.0001, format="%.4f")
lift_val = st.sidebar.slider("Minimum Lift (Ambang Korelasi)", 0.1, 5.0, 1.0, step=0.1)

# --- ENGINE UTAMA BERBASIS SESSION STATE (PERBAIKAN STATE RE-RUN) ---
if 'graph_data' not in st.session_state:
    st.session_state.graph_data = None

if uploaded_file is not None:
    # Menggunakan cache internal agar proses IO file tidak melambat saat re-run UI
    @st.cache_data
    def load_raw_data(file):
        return pd.read_csv(file)
        
    df_raw = load_raw_data(uploaded_file)
    
    required_cols = {'Member_number', 'Date', 'itemDescription', 'itemCategory'}
    if not required_cols.issubset(df_raw.columns):
        st.error(f"⚠️ Dataset cacat format. Kolom wajib ada: {required_cols}")
        st.stop()
        
    if st.sidebar.button("🚀 Jalankan Analisis Ekstensif", type="primary"):
        with st.spinner("Memproses Pemodelan Jaringan Sains Kompleks..."):
            G = build_graph_from_transactions(df_raw, support_val, lift_val)
            
            if G.number_of_nodes() == 0:
                st.error("⚠️ Model gagal terbentuk. Graf kosong! Silakan turunkan ambang batas Support/Lift di sidebar.")
                st.session_state.graph_data = None
            else:
                # Bungkus seluruh hasil kalkulasi berbiaya komputasi tinggi ke session state
                st.session_state.graph_data = {
                    'metrics': calculate_network_metrics(G),
                    'centralities_df': calculate_centralities(G),
                    'community_results': detect_communities(G),
                    'robustness_df': analyze_robustness(G),
                    'vulnerabilities': get_structural_vulnerabilities(G),
                    'raw_nodes': list(G.nodes()),
                    'raw_edges': [list(e) for e in G.edges()]
                }
                # Simpan graf utuh menggunakan penanganan internal networkx reconstruction
                st.session_state.G_object = G
                st.success("✅ Model Teori Graf berhasil disimpan ke dalam Session State!")

    # Fase Rendering UI: Dieksekusi secara independen dari status tombol klik
    if st.session_state.graph_data is not None:
        # Deklarasi ulang objek graf dari session state
        G = st.session_state.G_object
        metrics = st.session_state.graph_data['metrics']
        centralities_df = st.session_state.graph_data['centralities_df']
        community_map, modularity_score, communities = st.session_state.graph_data['community_results']
        robustness_df = st.session_state.graph_data['robustness_df']
        articulations, bridges = st.session_state.graph_data['vulnerabilities']
        
        # UI REFACTOR: Menampilkan Ringkasan Dashboard Menggunakan KPI Cards Horizontal Atas
        st.markdown("### 📊 Ringkasan Eksekutif Struktur Topologi")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric("📦 Total Produk (Nodes)", metrics.get('Nodes', 0))
        m_col2.metric("🔗 Garis Hubung (Edges)", metrics.get('Edges', 0))
        m_col3.metric("🕸️ Kerapatan (Density)", f"{metrics.get('Density', 0):.4f}")
        m_col4.metric("📐 Koefisien Klastering", f"{metrics.get('Clustering Coefficient', 0):.4f}")
        m_col5.metric("🏘️ Modularity Score ($Q$)", f"{modularity_score:.4f}")
        
        st.markdown("---")
        
        # Pembuatan Tab Navigasi Utama
        tab1, tab2, tab3, tab4 = st.tabs([
            "🌐 A. Network Overview", 
            "👑 B. Top Influential Products (Centrality)", 
            "🏘️ C. Community & Shelf Layout", 
            "🛡️ D. Network Robustness"
        ])
        
        # --- TAB 1: OVERVIEW JARINGAN MAKRO ---
        with tab1:
            st.header("Visualisasi Struktur Makro Jaringan")
            st.markdown("Analisis makroskopis pola penyebaran produk berdasarkan pembentukan interaksi spasial.")
            
            # Perbaikan UI/UX: Layout Lebar Penuh (Full-Width) untuk Visualisasi Graf Interaktif
            st.subheader("Graf Interaktif Pemetaan Keterikatan Produk (PyVis)")
            category_map = dict(zip(df_raw['itemDescription'], df_raw['itemCategory']))
            html_path = create_pyvis_network(G, community_map, centralities_df, category_map)
            
            with open(html_path, 'r', encoding='utf-8') as f:
                components.html(f.read(), height=650, scrolling=True)
            try:
                os.remove(html_path)
            except:
                pass
                
            st.info(f"💡 **Interpretasi Topologi:** Jaringan retail saat ini beroperasi dengan kepadatan jaringan sebesar **{metrics['Density']:.4f}**. "
                    f"Rata-rata tiap komoditas produk terikat langsung secara kuat dengan **{metrics['Average Degree']:.1f}** produk pendamping lainnya. "
                    f"Nilai diameter jaringan sebesar **{metrics.get('Diameter', metrics.get('Diameter (LCC)', 0))}** merepresentasikan jarak terjauh batas psikologis antar kategori.")

        # --- TAB 2: CENTRALITY ANALYSIS ---
        with tab2:
            st.header("Analisis Aktor Kunci Makro (Centrality Measures)")
            st.markdown("Mengupas pengaruh strategis sebuah produk di dalam toko ritel menggunakan aksioma **Freeman (1978)**.")
            
            c1, c2 = st.columns(2)
            top_degree = centralities_df.sort_values(by='Degree Centrality', ascending=False).iloc[0]['Product']
            top_between = centralities_df.sort_values(by='Betweenness Centrality', ascending=False).iloc[0]['Product']
            
            with c1:
                st.plotly_chart(plot_top_centralities(centralities_df, 'Degree Centrality', 'Top 10 Degree Centrality (Produk Terpopuler / Volume)', '#1f77b4'), use_container_width=True)
                st.plotly_chart(plot_top_centralities(centralities_df, 'Closeness Centrality', 'Top 10 Closeness Centrality (Aksesibilitas Tercepat)', '#2ca02c'), use_container_width=True)
            with c2:
                st.plotly_chart(plot_top_centralities(centralities_df, 'Betweenness Centrality', 'Top 10 Betweenness Centrality (Produk Jembatan Trans-Sektoral)', '#ff7f0e'), use_container_width=True)
                st.plotly_chart(plot_top_centralities(centralities_df, 'Eigenvector Centrality', 'Top 10 Eigenvector Centrality (Pengaruh Sistemik Kualitas)', '#d62728'), use_container_width=True)

            st.markdown("### 💡 Rekomendasi Penempatan Spasial Berbasis Sains Kompleks")
            st.success(f"📌 **Strategi Akselerasi Volume:** Produk **'{top_degree}'** memuncaki nilai *Degree Centrality*. Produk ini adalah 'Jangkar Utama Toko' (*Anchor Product*). "
                       f"Tempatkan di bagian **titik tengah denah bangunan ritel** untuk menarik arus kunjungan lalu lintas konsumen ke area paling dalam toko.")
            st.warning(f"📌 **Strategi Cross-Selling Inter-Kategori:** Produk **'{top_between}'** mendominasi nilai *Betweenness Centrality*. Komoditas ini bertindak selaku sakelar penghubung antar kelompok kebutuhan yang berbeda. "
                       f"Wajib diposisikan pada **titik persimpangan koridor utama (main aisles intersection)** demi memaksa pembeli mengeksplorasi lorong barang pelengkap lainnya.")

        # --- TAB 3: COMMUNITY DETECTION & LAYOUT CONFIGURATION ---
        with tab3:
            st.header("Struktur Komunitas Modular & Peta Zona Rak Ritel")
            st.markdown(f"Segmentasi otomatis menggunakan optimasi algoritma matematika **Clauset-Newman-Moore** (Skor Moduloritas Jaringan: **{modularity_score:.4f}**).")
            
            if modularity_score > 0.3:
                st.success("🎯 Skor Moduloritas $> 0.3$ memvalidasi bahwa komunitas belanja konsumen terbentuk secara kuat dan terstruktur secara natural.")
            else:
                st.info("⚠️ Skor Moduloritas rendah ($< 0.3$). Pola kombinasi belanja konsumen cenderung acak atau homogen merata tanpa sekat khusus.")

            st.subheader("🛠️ Blueprint Alokasi Penyusunan Komoditas per Lorong Rak")
            cols = st.columns(3)
            for i, comm in enumerate(communities):
                if len(comm) < 2:
                    continue
                col_idx = i % 3
                with cols[col_idx]:
                    with st.container(border=True):
                        st.markdown(f"### 🛒 Zona Klaster Rak {i+1}")
                        st.write(f"**Variasi Produk Komunitas:** {len(comm)} Item")
                        st.markdown("**5 Inti Produk Utama Klaster (Prioritas Pandangan):**")
                        
                        # Pengurutan subgraf internal komunitas untuk menemukan item paling sentral dalam klaster
                        sub_g = G.subgraph(comm)
                        sub_deg = nx.degree_centrality(sub_g)
                        top_items = sorted(sub_deg, key=sub_deg.get, reverse=True)[:5]
                        
                        for item in top_items:
                            st.write(f"🔹 {item}")
                        if len(comm) > 5:
                            st.caption(f"*Dan {len(comm)-5} jenis produk pelengkap lainnya.*")

        # --- TAB 4: ROBUSTNESS SIMULATION & CRITICAL ATTACKS ---
        with tab4:
            st.header("Kekokohan Sistem Jaringan (Network Robustness Analysis)")
            st.markdown("Simulasi ilmiah keruntuhan fungsional toko ritel apabila terjadi kelangkaan barang massal (**Albert-Barabási Model**).")
            
            r_col1, r_col2 = st.columns([2, 1])
            with r_col1:
                st.plotly_chart(plot_robustness(robustness_df), use_container_width=True)
            with r_col2:
                st.subheader("🚨 Titik Kerentanan Struktural Toko")
                st.metric("Cut Vertices (Articulation Points)", len(articulations))
                st.metric("Critical Bridges (Tepi Kritis)", len(bridges))
                
                with st.expander("Daftar Simpul Kritis (Rawan Stockout)"):
                    st.write(articulations if articulations else "Sistem jaringan tidak memiliki titik potong tunggal.")

            st.markdown("### 💡 Analisis Risiko Operasional Supply Chain")
            if len(robustness_df) > 1:
                drop_percent = (1.0 - robustness_df.iloc[-1]['LCC Size (Fraction)']) * 100
                st.error(f"⚠️ **Temuan Simulasi Kritis:** Penghapusan {robustness_df['Nodes Removed'].max()} produk jangkar utama mengakibatkan persentase integritas jaringan anjlok drastis sebesar **{drop_percent:.1f}%** dan memicu fragmentasi toko menjadi **{robustness_df['Number of Components'].max()}** bagian yang terisolasi.")
                st.warning("📊 **Tindakan Korektif Manajemen:** Ketiadaan produk-produk kritis (*Articulation Points*) di atas akibat kelangkaan pasokan (*stockout*) akan memutus rantai transaksi produk turunannya secara berantai. Manajer operasional wajib menetapkan status alokasi batas aman pasokan (*Safety Stock*) tingkat tertinggi untuk komoditas ini demi menghindari penurunan omzet secara domino.")
else:
    st.info("👈 Silakan mulai dengan mengunggah dataset berformat CSV di menu samping untuk membangun model teori graf.")