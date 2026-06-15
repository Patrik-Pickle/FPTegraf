import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network
import tempfile

# def create_pyvis_network(G, community_map, centralities_df, category_map) -> str:
#     """Membuat visualisasi graf interaktif HTML dengan skema warna modularitas dinamis."""
#     net = Network(height='600px', width='100%', bgcolor='#f8f9fa', font_color='#212529', notebook=False)
    
#     degree_dict = centralities_df.set_index('Product')['Degree Centrality'].to_dict()
    
#     # Palet warna hex yang diperluas untuk menghindari tabrakan visual klastering
#     colors = [
#         '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
#         '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
#         '#4abc96', '#a55eea', '#ffb142', '#ff5252', '#341f97'
#     ]
    
#     for node in G.nodes():
#         # Skala ukuran logaritmik agar simpul dominan tidak menutupi simpul kecil
#         base_size = degree_dict.get(node, 0) * 400
#         size = max(12, min(base_size, 50))
        
#         comm_id = community_map.get(node, 0)
#         color = colors[comm_id % len(colors)]
        
#         kategori_fisik = category_map.get(node, "Tidak Terdefinisi")
        
#         title_hover = (
#             f"📦 Produk: {node}\n"
#             f"📁 Taksonomi Kategori: {kategori_fisik}\n"
#             f"🏘️ Zona Rak Belanja: {comm_id + 1}\n"
#             f"📈 Degree Centrality: {degree_dict.get(node, 0):.4f}"
#         )
        
#         net.add_node(node, label=node, size=size, color=color, title=title_hover, borderWidth=1.5)
        
#     for edge in G.edges(data=True):
#         weight = edge[2].get('weight', 1.0)
#         # Normalisasi ketebalan garis tepi berdasarkan kekuatan nilai Lift
#         edge_width = max(1.0, min(weight * 0.5, 8.0))
#         net.add_edge(edge[0], edge[1], value=edge_width, color='#ced4da', title=f"Asosiasi (Lift): {weight:.2f}")
        
#     net.set_options("""
#     var options = {
#       "physics": {
#         "forceAtlas2Based": {
#           "gravitationalConstant": -60,
#           "centralGravity": 0.015,
#           "springLength": 120,
#           "springConstant": 0.06
#         },
#         "minVelocity": 0.75,
#         "solver": "forceAtlas2Based"
#       },
#       "interaction": {
#         "hover": true,
#         "tooltipDelay": 100
#       }
#     }
#     """)
# import pandas as pd
# import networkx as nx
# from pyvis.network import Network
# import tempfile
import os

def create_pyvis_network(G, community_map, centralities_df, category_map) -> str:
    """Membuat visualisasi graf interaktif HTML yang sangat berwarna dengan skema warna komunitas yang cerah dan tepi berwarna dinamis."""
    # Ubah latar belakang menjadi putih bersih (#ffffff) untuk menonjolkan warna,
    # dan gunakan warna font yang sedikit lebih cerah untuk label.
    net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='#2c3e50', notebook=False)
    
    degree_dict = centralities_df.set_index('Product')['Degree Centrality'].to_dict()
    
    # Palet warna node yang sangat cerah, ceria, dan kontras (total 15 warna).
    colors = [
        '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
        '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
        '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000'
    ]
    
    for node in G.nodes():
        # Skala ukuran logaritmik agar simpul dominan tidak menutupi simpul kecil
        base_size = degree_dict.get(node, 0) * 400
        size = max(12, min(base_size, 50))
        
        comm_id = community_map.get(node, 0)
        comm_color = colors[comm_id % len(colors)]
        
        # Tambahkan border/pinggiran berwarna sama dengan node agar lebih pop-out
        node_style = {
            'background': comm_color,
            'border': comm_color,
            'hover': {'background': comm_color, 'border': comm_color},
            'selected': {'background': comm_color, 'border': comm_color}
        }
        
        kategori_fisik = category_map.get(node, "Tidak Terdefinisi")
        
        title_hover = (
            f"📦 Produk: {node}\n"
            f"📁 Taksonomi Kategori: {kategori_fisik}\n"
            f"🏘️ Zona Rak Belanja: {comm_id + 1}\n"
            f"📈 Degree Centrality: {degree_dict.get(node, 0):.4f}"
        )
        
        net.add_node(node, label=node, size=size, color=node_style, title=title_hover, borderWidth=1.5, borderWidthSelected=3)
        
    for edge in G.edges(data=True):
        u, v, data = edge
        weight = data.get('weight', 1.0)
        
        source_comm_id = community_map.get(u, 0)
        target_comm_id = community_map.get(v, 0)
        
        # Normalisasi ketebalan garis tepi berdasarkan kekuatan nilai Lift
        edge_width = max(1.0, min(weight * 0.5, 8.0))
        
        # Logika Pewarnaan Garis Tepi:
        # Jika kedua node yang terhubung berada dalam komunitas yang sama,
        # gunakan warna komunitas tersebut dengan sedikit transparansi untuk estetika.
        if source_comm_id == target_comm_id:
            comm_color = colors[source_comm_id % len(colors)]
            # Tambahkan transparansi (hex alpha, contoh: 50% = 80 di suffix)
            edge_color = comm_color + '80' 
        else:
            # Jika berbeda komunitas, gunakan abu-abu netral semi-transparan.
            # Ini membuat kelompok intra-komunitas yang berwarna lebih menonjol.
            edge_color = '#ced4da80'
            
        net.add_edge(u, v, value=edge_width, color=edge_color, title=f"Asosiasi (Lift): {weight:.2f}")
        
    # Opsi Fisika & Interaksi (Gravitasi jaringan yang sedikit disesuaikan agar menyebar)
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.012,
          "springLength": 150,
          "springConstant": 0.05
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100
      },
      "nodes": {
        "borderWidth": 1.5,
        "borderWidthSelected": 3
      },
      "edges": {
        "color": {
          "inherit": false
        }
      }
    }
    """)
    
    # Menyimpan ke file sementara untuk di-render di Streamlit
    path = tempfile.NamedTemporaryFile(delete=False, suffix='.html').name
    net.save_graph(path)
    return path
    
    path = tempfile.NamedTemporaryFile(delete=False, suffix='.html').name
    net.save_graph(path)
    return path



# def create_pyvis_network(G, community_map, centralities_df, category_map=None) -> str:
#     """
#     Membuat visualisasi graf interaktif HTML dengan skema warna komunitas yang cerah,
#     tepi berwarna dinamis transparan, dan optimasi performa drag-drop.
#     """
#     from pyvis.network import Network
#     import tempfile

#     # Inisialisasi Network dengan warna teks kontras netral
#     net = Network(
#         height="650px",
#         width="100%",
#         bgcolor="#ffffff",
#         font_color="#2c3e50",
#         notebook=False
#     )

#     # Ambil metrik sentralitas derajat untuk ukuran node
#     degree_dict = centralities_df.set_index("Product")["Degree Centrality"].to_dict()

#     # Palet 15 warna kontras tinggi untuk membedakan Zona Rak / Komunitas Produk
#     colors = [
#         '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
#         '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
#         '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000'
#     ]

#     # ==========================================
#     # 1. PROSES SIMPUL (NODES)
#     # ==========================================
#     for node in G.nodes():
#         degree_val = degree_dict.get(node, 0)
        
#         # Batasi ukuran minimum dan maksimum agar layout seimbang
#         size = max(12, min(degree_val * 400, 60))

#         comm_id = community_map.get(node, 0)
#         comm_color = colors[comm_id % len(colors)]

#         # Desain gaya datar (Flat UI Design) modern dengan warna batas senada
#         node_style = {
#             'background': comm_color,
#             'border': comm_color,
#             'highlight': {'background': comm_color, 'border': '#2c3e50'},
#             'hover': {'background': comm_color, 'border': '#2c3e50'}
#         }

#         # Handling pemetaan kategori taksonomi barang
#         kategori_fisik = (
#             category_map.get(node, "Lainnya")
#             if category_map is not None
#             else "Lainnya"
#         )

#         # Tooltip interaktif kaya informasi berbasis HTML
#         title_hover = (
#             f"<b>📦 Produk:</b> {node}<br>"
#             f"<b>📁 Taksonomi Kategori:</b> {kategori_fisik}<br>"
#             f"<b>🏘️ Zona Rak Belanja:</b> Klaster {comm_id + 1}<br>"
#             f"<b>📈 Degree Centrality:</b> {degree_val:.4f}"
#         )

#         net.add_node(
#             node,
#             label=node,
#             size=size,
#             color=node_style,
#             title=title_hover,
#             borderWidth=1.5,
#             borderWidthSelected=3
#         )

#     # ==========================================
#     # 2. PROSES HUBUNGAN (EDGES)
#     # ==========================================
#     for u, v, data in G.edges(data=True):
#         weight = data.get("weight", 1.0)

#         source_comm = community_map.get(u, 0)
#         target_comm = community_map.get(v, 0)

#         # Logika Pewarnaan & Transparansi Sisi:
#         # Menambahkan '66' (Alpha kanal Hex) untuk efek transparansi ~40% 
#         # guna mengurangi noise visual pada struktur jaringan yang padat.
#         if source_comm == target_comm:
#             edge_color = colors[source_comm % len(colors)] + '66'
#         else:
#             # Hubungan lintas komunitas diwarnai dengan abu-abu netral tipis
#             edge_color = "#ced4da66"

#         # Penskalaan ketebalan garis berdasarkan nilai Lift hasil Apriori
#         edge_width = max(1.0, min(weight * 1.5, 8.0))

#         net.add_edge(
#             u,
#             v,
#             width=edge_width,
#             color=edge_color,
#             title=f"Kekuatan Asosiasi (Lift): {weight:.2f}"
#         )

#     # ==========================================
#     # 3. ATURAN FISIKA & INTERAKSI (JSON OPTIONS)
#     # ==========================================
#     net.set_options("""
#     {
#       "physics": {
#         "enabled": true,
#         "forceAtlas2Based": {
#           "gravitationalConstant": -100,
#           "centralGravity": 0.02,
#           "springLength": 140,
#           "springConstant": 0.04,
#           "avoidOverlap": 0.7
#         },
#         "solver": "forceAtlas2Based",
#         "minVelocity": 0.75
#       },
#       "interaction": {
#         "hover": true,
#         "tooltipDelay": 100,
#         "hideEdgesOnDrag": true,
#         "navigationButtons": true
#       },
#       "nodes": {
#         "font": {
#           "size": 11,
#           "face": "Helvetica",
#           "strokeWidth": 2.5,
#           "strokeColor": "#ffffff"
#         }
#       },
#       "edges": {
#         "smooth": {
#           "enabled": true,
#           "type": "dynamic"
#         }
#       }
#     }
#     """)

#     # Penyimpanan berkas sementara untuk di-render oleh komponen Streamlit
#     path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name
#     net.save_graph(path)
    
#     return path


# def create_pyvis_network(G, community_map, centralities_df, category_map=None) -> str:
#     """
#     Membuat jaringan interaktif PyVis dengan warna berdasarkan KOMUNITAS dan ukuran linear (Gaya Asli Anda).
#     Kompatibel dengan panggilan 4 argumen di app.py dan dioptimalkan agar tidak menggumpal di tengah.
#     """
#     # Menggunakan font hitam dan background putih bersih sesuai gaya lama Anda
#     net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='black', notebook=False)
    
#     # Mapping sentralitas untuk ukuran node
#     degree_dict = centralities_df.set_index('Product')['Degree Centrality'].to_dict()
    
#     # Palet warna komunitas klasik pilihan Anda (Tableau 10)
#     colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
#     for node in G.nodes():
#         # 1. Ukuran node berbasis nilai linear asli Anda
#         size = max(10, degree_dict.get(node, 0) * 300)
        
#         # 2. Pewarnaan murni berbasis ID Komunitas asli Anda
#         comm_id = community_map.get(node, 0)
#         color = colors[comm_id % len(colors)]
        
#         # Memanfaatkan category_map dari app.py hanya untuk memperkaya info di dalam Hover Tooltip (title)
#         kategori_fisik = category_map.get(node, "Lainnya") if category_map else "Lainnya"
        
#         title = (
#             f"📦 Produk: {node}\n"
#             f"📁 Kategori Tipe: {kategori_fisik}\n"
#             f"🏘️ Komunitas Rak: {comm_id + 1}\n"
#             f"📈 Degree: {degree_dict.get(node, 0):.4f}"
#         )
        
#         # 3. Menampilkan seluruh nama produk secara langsung tanpa ada yang disembunyikan
#         net.add_node(node, label=node, size=size, color=color, title=title)
        
#     for edge in G.edges(data=True):
#         weight = edge[2].get('weight', 1)
        
#         # SOLUSI VISUAL: Berikan warna abu-abu transparan (#ced4da40 -> opacity ~25%)
#         # Cara ini efektif mengurai kabut garis tebal di tengah tanpa mengubah nilai 'value=weight' asli Anda
#         net.add_edge(edge[0], edge[1], value=weight, color='#ced4da40', title=f"Korelasi (Lift): {weight:.2f}")
        
#     # Opsi Fisika Baru: Melonggarkan gaya pegas dan memperkuat daya tolak magnet antarproduk
#     # agar label teks yang panjang tidak saling bertabrakan di layar
#     net.set_options("""
#     var options = {
#       "physics": {
#         "forceAtlas2Based": {
#           "gravitationalConstant": -180, // Diperkuat dari -50 agar node saling mendorong menjauh ke luar
#           "centralGravity": 0.003,       // Diturunkan dari 0.01 agar klaster tidak menumpuk ketat di pusat
#           "springLength": 220,           // Diperpanjang dari 100 untuk memberi ruang bernapas bagi label teks
#           "springConstant": 0.03,        // Pegas dibuat lebih lentur agar cluster memisahkan diri secara spasial
#           "avoidOverlap": 1              // Mencegah lingkaran/node bertumpang tindih secara keras
#         },
#         "minVelocity": 0.75,
#         "solver": "forceAtlas2Based"
#       },
#       "interaction": {
#         "hover": true,
#         "tooltipDelay": 80,
#         "hideEdgesOnDrag": true          // Menghemat RAM/performa Streamlit saat graf digeser atau di-zoom
#       },
#       "nodes": {
#         "font": {
#           "size": 11,
#           "face": "Helvetica",
#           "strokeWidth": 2,
#           "strokeColor": "#ffffff"
#         }
#       }
#     }
#     """)
    
#     path = tempfile.NamedTemporaryFile(delete=False, suffix='.html').name
#     net.save_graph(path)
#     return path


def plot_top_centralities(df, centrality_type, title, color):
    """Membuat plot batang horizontal interaktif dengan transisi animasi."""
    top_df = df.sort_values(by=centrality_type, ascending=False).head(10)
    
    fig = px.bar(
        top_df, x=centrality_type, y='Product', orientation='h', 
        title=title, text_auto='.4f', color_discrete_sequence=[color]
    )
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'}, 
        margin=dict(l=10, r=10, t=50, b=10),
        height=380,
        template="plotly_white",
        hovermode="y unified"
    )
    return fig

def plot_robustness(df):
    """Membuat diagram garis visualisasi keruntuhan jaringan akibat stok kosong."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Nodes Removed'], y=df['LCC Size (Fraction)'],
        mode='lines+markers', name='Ukuran Komponen Utama (LCC)',
        line=dict(color='#e74c3c', width=3),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title="Kurva Degradasi Ketahanan Jaringan (Albert et al., 2000)",
        xaxis_title="Jumlah Produk Utama yang Mengalami Out-Of-Stock",
        yaxis_title="Fraksi Konektivitas Jaringan Toko ($LCC$)",
        template="plotly_white",
        hovermode="x unified"
    )
    return fig