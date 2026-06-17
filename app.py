"""
ShelfGraph Analytics — Version C (Merged)
===========================================
UI/UX      : ZIP A  (clean module import, session state pattern, @st.cache_data hoisting,
                      spinner messaging, metric cards, tab layout, expander communities)
TAB SET    : ZIP B  (4 tabs: Network Overview + Centrality + Community + Robustness)
SIDEBAR    : ZIP A  (header styling, slider format) + ZIP B (required_cols validation)
KPI CARDS  : MERGE  (ZIP A 4 cards + ZIP B density/clustering = 6 cards total)
TAB 1 (Graph) : ZIP A (render_interactive_graph returns HTML string — no file I/O leak)
TAB 2 (Cent)  : ZIP B (4 Plotly bar charts + strategic recommendations)
TAB 3 (Comm)  : ZIP B (3-column grid layout + subgraph ranking) with ZIP A expander style
TAB 4 (Robust): ZIP B (robustness plot + vulnerability metrics)
CENTRALITY TABLE: ZIP A (st.dataframe sorted by PageRank — scientific ranking)
"""

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import networkx as nx

from src.services.analytics_service import run_full_pipeline
from src.visualization.pyvis_renderer import (
    render_interactive_graph,
    plot_top_centralities,
    plot_robustness
)

# ─────────────────────────────────────────────────────────────────────────────
# KONFIGURASI HALAMAN
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ShelfGraph Analytics",
    layout="wide",
    page_icon="🔬"
)

st.title("🔬 ShelfGraph Analytics: Enterprise Graph Platform")
st.markdown("""
Sistem Analisis Struktur Jaringan Produk menggunakan *Frequent Pattern Growth O(N)* dan
*Directed Complex Network Science*. Referensi: Freeman (1978), Newman (2006, 2010), Albert et al. (2000).
""")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.header("📁 1. Manajemen Berkas")
uploaded_file = st.sidebar.file_uploader(
    "Dataset CSV (Member_number, Date, itemDescription, itemCategory)",
    type=['csv']
)

st.sidebar.header("⚙️ 2. Hyperparameter Mining")
support_val = st.sidebar.slider("Minimum Support", 0.0001, 0.0500, 0.0010, step=0.0001, format="%.4f")
lift_val    = st.sidebar.slider("Minimum Lift (Ambang Korelasi)", 0.1, 5.0, 1.0, step=0.1)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING (cache agar tidak re-read di setiap re-run)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(file):
    return pd.read_csv(file)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
if 'pipeline_result' not in st.session_state:
    st.session_state.pipeline_result = None

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    df_raw = load_data(uploaded_file)

    # Validasi kolom (ZIP B)
    required_cols = {'Member_number', 'Date', 'itemDescription', 'itemCategory'}
    if not required_cols.issubset(df_raw.columns):
        st.error(f"⚠️ Dataset cacat format. Kolom wajib ada: {required_cols}")
        st.stop()

    if st.sidebar.button("🚀 Eksekusi Pipeline Big Data", type="primary"):
        with st.spinner("Memproses FP-Growth O(N) & Topologi DiGraph..."):
            result = run_full_pipeline(df_raw, support_val, lift_val)

            if not result.is_success:
                st.error(f"⚠️ Eksekusi Gagal: {result.error_msg}")
                st.session_state.pipeline_result = None
            else:
                st.session_state.pipeline_result = result
                st.success("✅ Komputasi O(N) Berhasil Diselesaikan!")

# ─────────────────────────────────────────────────────────────────────────────
# RENDERING UI (independen dari status tombol klik — ZIP B pattern)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.pipeline_result is not None:
    res = st.session_state.pipeline_result
    metrics = res.network_metrics

    # ── KPI CARDS (ZIP A style, ZIP B extended metrics) ───────────────────────
    st.markdown("### 📊 Enterprise Topology Metrics")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📦 Total SKU (Nodes)", res.graph.number_of_nodes())
    c2.metric("🔗 Directed Edges",    res.graph.number_of_edges())
    c3.metric("📋 Association Rules", len(res.rules))
    c4.metric("🕸️ Kerapatan (Density)", f"{metrics.get('Density', 0):.4f}")
    c5.metric("📐 Koef. Klastering",  f"{metrics.get('Clustering Coefficient', 0):.4f}")
    c6.metric("🏘️ Modularity (Q)",    f"{res.modularity:.4f}")

    st.markdown("---")

    # ── TABS (ZIP A naming style, ZIP B 4-tab set) ────────────────────────────
    t1, t2, t3, t4 = st.tabs([
        "🌐 Directed Graph Explorer",
        "👑 Peringkat Aktor (Centrality)",
        "🏘️ Layout Komunitas Rak",
        "🛡️ Ketahanan Jaringan (Robustness)"
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1: DIRECTED GRAPH EXPLORER (ZIP A UX — inline HTML string)
    # ════════════════════════════════════════════════════════════════════════
    with t1:
        st.subheader("Visualisasi Dinamis K-Core Filtered Network")
        st.markdown(
            "Analisis makroskopis pola penyebaran produk. "
            "Ukuran node = **PageRank** · Warna node = **Komunitas Louvain** · "
            "Warna edge = **Intra/Inter-Community**"
        )
        category_map = (
            dict(zip(df_raw['itemDescription'], df_raw['itemCategory']))
            if 'itemCategory' in df_raw.columns else {}
        )
        with st.spinner("Merender HTML secara asinkron..."):
            html_string = render_interactive_graph(
                res.graph, res.community_map, res.centralities, category_map
            )
            components.html(html_string, height=720, scrolling=True)

        st.info(
            f"💡 **Interpretasi Topologi:** Jaringan beroperasi dengan kepadatan "
            f"**{metrics.get('Density', 0):.4f}**. Rata-rata tiap produk terhubung langsung "
            f"dengan **{metrics.get('Average Degree', 0):.1f}** produk lain. "
            f"Diameter jaringan: "
            f"**{metrics.get('Diameter', metrics.get('Diameter (LCC)', 'N/A'))}** hop."
        )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2: CENTRALITY ANALYSIS (ZIP B Plotly charts + ZIP A full dataframe)
    # ════════════════════════════════════════════════════════════════════════
    with t2:
        st.subheader("Metrik Sentralitas Multidimensi")
        st.markdown("Mengupas pengaruh strategis produk menggunakan aksioma **Freeman (1978)**.")

        c_left, c_right = st.columns(2)
        with c_left:
            st.plotly_chart(
                plot_top_centralities(res.centralities, 'PageRank Centrality',
                                      'Top 10 PageRank (Otoritas Jaringan Produk)', '#1f77b4'),
                use_container_width=True
            )
            st.plotly_chart(
                plot_top_centralities(res.centralities, 'Closeness Centrality',
                                      'Top 10 Closeness (Aksesibilitas Tercepat)', '#2ca02c'),
                use_container_width=True
            )
        with c_right:
            st.plotly_chart(
                plot_top_centralities(res.centralities, 'Betweenness Centrality',
                                      'Top 10 Betweenness (Produk Jembatan Trans-Sektoral)', '#ff7f0e'),
                use_container_width=True
            )
            st.plotly_chart(
                plot_top_centralities(res.centralities, 'Eigenvector Centrality',
                                      'Top 10 Eigenvector (Pengaruh Sistemik Kualitas)', '#d62728'),
                use_container_width=True
            )

        # Rekomendasi Strategis (ZIP B)
        top_pagerank  = res.centralities.sort_values('PageRank Centrality', ascending=False).iloc[0]['Product']
        top_between   = res.centralities.sort_values('Betweenness Centrality', ascending=False).iloc[0]['Product']

        st.markdown("### 💡 Rekomendasi Penempatan Spasial Berbasis Sains Kompleks")
        st.success(
            f"📌 **Strategi Akselerasi Volume:** Produk **'{top_pagerank}'** mendominasi *PageRank Centrality*. "
            f"Produk ini adalah 'Jangkar Utama Toko' (*Anchor Product*). "
            f"Tempatkan di **titik tengah denah bangunan ritel** untuk menarik lalu lintas konsumen ke area terdalam."
        )
        st.warning(
            f"📌 **Strategi Cross-Selling Inter-Kategori:** Produk **'{top_between}'** mendominasi *Betweenness Centrality*. "
            f"Komoditas ini bertindak sebagai penghubung antar kelompok kebutuhan berbeda. "
            f"Posisikan pada **titik persimpangan koridor utama** untuk memaksa eksplorasi lorong pelengkap."
        )

        # Tabel Lengkap (ZIP A — sorted by PageRank)
        st.markdown("### 📋 Tabel Sentralitas Lengkap")
        st.dataframe(
            res.centralities.sort_values('PageRank Centrality', ascending=False),
            use_container_width=True
        )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3: COMMUNITY & SHELF LAYOUT (ZIP B 3-column grid + ZIP A expander)
    # ════════════════════════════════════════════════════════════════════════
    with t3:
        st.subheader("Segmentasi Produk & Peta Zona Rak Ritel")
        st.markdown(
            f"Algoritma **Louvain** (NetworkX 3.0+). "
            f"Skor Modularitas Jaringan: **{res.modularity:.4f}**"
        )

        if res.modularity > 0.3:
            st.success("🎯 Skor Moduloritas > 0.3: komunitas belanja terbentuk kuat dan terstruktur secara natural.")
        else:
            st.info("⚠️ Skor Moduloritas < 0.3: pola kombinasi belanja cenderung acak atau homogen.")

        st.subheader("🛠️ Blueprint Alokasi Komoditas per Lorong Rak")
        cols_grid = st.columns(3)
        valid_comms = [c for c in res.communities if len(c) >= 2]

        for i, comm in enumerate(valid_comms):
            col_idx = i % 3
            with cols_grid[col_idx]:
                with st.container(border=True):
                    st.markdown(f"### 🛒 Zona Klaster Rak {i + 1}")
                    st.write(f"**Variasi Produk:** {len(comm)} Item")
                    st.markdown("**5 Produk Inti Klaster (Prioritas Pandangan):**")

                    sub_g = res.graph.to_undirected().subgraph(comm)
                    sub_deg = nx.degree_centrality(sub_g)
                    top_items = sorted(sub_deg, key=sub_deg.get, reverse=True)[:5]

                    for item in top_items:
                        st.write(f"🔹 {item}")
                    if len(comm) > 5:
                        st.caption(f"*Dan {len(comm) - 5} jenis produk pelengkap lainnya.*")

        # ZIP A expander style untuk daftar lengkap per komunitas
        st.markdown("---")
        st.subheader("📋 Daftar Lengkap Item per Komunitas")
        for idx, comm in enumerate(res.communities):
            if len(comm) > 1:
                with st.expander(f"🛒 Klaster Belanja {idx + 1} ({len(comm)} Item)"):
                    st.write(", ".join(sorted(list(comm))))

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4: ROBUSTNESS (ZIP B — fitur baru, tidak ada di ZIP A)
    # ════════════════════════════════════════════════════════════════════════
    with t4:
        st.subheader("Kekokohan Sistem Jaringan (Network Robustness Analysis)")
        st.markdown(
            "Simulasi ilmiah keruntuhan fungsional toko ritel apabila terjadi "
            "kelangkaan barang massal (**Albert-Barabási Model**)."
        )

        r_col1, r_col2 = st.columns([2, 1])
        with r_col1:
            if not res.robustness_df.empty:
                st.plotly_chart(plot_robustness(res.robustness_df), use_container_width=True)
        with r_col2:
            st.subheader("🚨 Titik Kerentanan Struktural Toko")
            st.metric("Cut Vertices (Articulation Points)", len(res.articulations))
            st.metric("Critical Bridges (Tepi Kritis)",    len(res.bridges))

            with st.expander("Daftar Simpul Kritis (Rawan Stockout)"):
                st.write(
                    res.articulations if res.articulations
                    else "Sistem jaringan tidak memiliki titik potong tunggal."
                )

        st.markdown("### 💡 Analisis Risiko Operasional Supply Chain")
        if not res.robustness_df.empty and len(res.robustness_df) > 1:
            drop_percent = (1.0 - res.robustness_df.iloc[-1]['LCC Size (Fraction)']) * 100
            st.error(
                f"⚠️ **Temuan Kritis:** Penghapusan {res.robustness_df['Nodes Removed'].max()} "
                f"produk jangkar mengakibatkan integritas jaringan anjlok sebesar "
                f"**{drop_percent:.1f}%** dan memicu fragmentasi menjadi "
                f"**{res.robustness_df['Number of Components'].max()}** bagian terisolasi."
            )
            st.warning(
                "📊 **Tindakan Korektif:** Tetapkan *Safety Stock* tertinggi untuk produk-produk "
                "*Articulation Points* di atas guna menghindari penurunan omzet secara domino."
            )

else:
    st.info("👈 Silakan unggah dataset CSV dan konfigurasi parameter untuk memulai simulasi saintifik.")
