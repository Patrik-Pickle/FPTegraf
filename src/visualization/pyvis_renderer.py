"""
Visualization Engine — Version C (Merged)
==========================================
SOURCE DECISION:
  PYVIS RENDERER   : ZIP A  (HSV dynamic palette, K-Core filtering, thread-safe UUID temp file,
                              DIRECTED graph arrows, PageRank node sizing, HTML tooltip)
  EDGE COLORING    : ZIP B  (intra-community colored edges + inter-community grey — visual superior)
  PHYSICS TUNING   : MERGE  (spring parameters dari ZIP B, arrows+smooth dari ZIP A)
  PLOTLY CHARTS    : ZIP B  (plot_top_centralities + plot_robustness — fitur baru tidak ada di ZIP A)
  NODE TOOLTIP     : ZIP A  (HTML tooltip lebih kaya: bold + emoji + HTML tags)
"""

import networkx as nx
from pyvis.network import Network
import colorsys
import uuid
import os
import tempfile
import plotly.express as px
import plotly.graph_objects as go
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: HSV Dynamic Color Palette (ZIP A — kontras maksimal, skalabel)
# ─────────────────────────────────────────────────────────────────────────────

# def generate_hsv_colors(n: int) -> list:
#     """
#     Menghasilkan palet warna dinamis menggunakan ruang warna HSV untuk kontras maksimal.
#     Keunggulan vs. hardcoded list ZIP B: skala otomatis sesuai jumlah komunitas (berapapun).
#     """
#     colors = []
#     for i in range(max(n, 1)):
#         hue = i / max(n, 1)
#         lightness = 0.58
#         saturation = 0.85
#         rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
#         hex_color = '#%02x%02x%02x' % (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
#         colors.append(hex_color)
#     return colors
def generate_hsv_colors(n):
    colors = []

    for i in range(max(n,1)):
        h = i / n
        r,g,b = colorsys.hsv_to_rgb(h,0.7,0.95)

        colors.append(
            '#{:02x}{:02x}{:02x}'.format(
                int(r*255),
                int(g*255),
                int(b*255)
            )
        )

    return colors

# ─────────────────────────────────────────────────────────────────────────────
# PYVIS NETWORK RENDERER (Main Visual — best of both)
# ─────────────────────────────────────────────────────────────────────────────

# # def render_interactive_graph(
# #     G_raw: nx.DiGraph,
# #     community_map: dict,
# #     centralities_df,
# #     category_map: dict = None
# # ) -> str:
# #     """
# #     Membangun string HTML interaktif PyVis.

# #     Keunggulan gabungan:
# #       - ZIP A: K-Core filtering (pencegahan browser crash), HSV dynamic palette,
# #                directed arrows, PageRank node sizing, HTML tooltip, UUID thread-safe,
# #                ForceAtlas2 physics, return HTML string langsung.
# #       - ZIP B: Intra-community colored edges (70% alpha), inter-community grey edges,
# #                hover interaction options, borderWidthSelected.
# #     """
# #     # ── 1. K-CORE FILTERING (ZIP A) ───────────────────────────────────────────
# #     max_visual_nodes = 800
# #     G = G_raw.copy()

# #     if G.number_of_nodes() > max_visual_nodes:
# #         logger.warning(f"Graf besar ({G.number_of_nodes()} nodes). Menerapkan K-Core Filtering...")
# #         G_undirected = G.to_undirected()
# #         k = 2
# #         while G_undirected.number_of_nodes() > max_visual_nodes and k < 10:
# #             G_undirected = nx.k_core(G_undirected, k=k)
# #             k += 1
# #         valid_nodes = set(G_undirected.nodes())
# #         G = G.subgraph(valid_nodes).copy()
# #         logger.info(f"K-Core filtering selesai (k={k - 1}). Nodes tersisa: {G.number_of_nodes()}")

#     # ── 2. INISIALISASI NETWORK ────────────────────────────────────────────────
#     net = Network(
#         height='700px', width='100%',
#         bgcolor='#ffffff', font_color='#2c3e50',
#         directed=True,          # ZIP A: DiGraph arrows
#         notebook=False
#     )

#     # ── 3. WARNA KOMUNITAS — HSV dynamic (ZIP A) ──────────────────────────────
#     num_communities = len(set(community_map.values())) if community_map else 1
#     dynamic_colors = generate_hsv_colors(num_communities)

#     # ── 4. NODE SIZING via PageRank (ZIP A — lebih saintifik dari degree) ──────
#     try:
#         pr_dict = centralities_df.set_index('Product')['PageRank Centrality'].to_dict()
#     except KeyError:
#         pr_dict = {node: 1.0 for node in G.nodes()}

#     # ── 5. TAMBAH NODES ────────────────────────────────────────────────────────
#     for node in G.nodes():
#         pr_val = pr_dict.get(node, 0.01)
#         size = max(10, min(pr_val * 2000, 70))  # Skalasi logaritmis aman

#         comm_id = community_map.get(node, 0)
#         comm_color = dynamic_colors[comm_id % len(dynamic_colors)]

#         # Gaya node dengan border senada komunitas (ZIP B flat-design)
#         node_style = {
#             'background': comm_color,
#             'border': comm_color,
#             'highlight': {'background': comm_color, 'border': '#2c3e50'},
#             'hover': {'background': comm_color, 'border': '#2c3e50'},
#         }

#         cat = category_map.get(node, "Unknown") if category_map else "Unknown"

#         # HTML tooltip kaya informasi (ZIP A format — lebih bisa dibaca)
#         title_html = (
#             f"<b>📦 Product:</b> {node}<br>"
#             f"<b>📂 Category:</b> {cat}<br>"
#             f"<b>🏘️ Community:</b> Klaster {comm_id + 1}<br>"
#             f"<b>⭐ PageRank:</b> {pr_val:.4f}"
#         )

#         net.add_node(
#             node, label=node, size=size,
#             color=node_style, title=title_html,
#             borderWidth=2, borderWidthSelected=4
#         )

#     # ── 6. TAMBAH EDGES — intra/inter community coloring (ZIP B) ──────────────
#     for u, v, data in G.edges(data=True):
#         conf = data.get('confidence', 0.1)
#         lift = data.get('lift', 1.0)

#         edge_width = max(1.0, min(conf * 10, 8.0))

#         source_comm = community_map.get(u, 0)
#         target_comm = community_map.get(v, 0)

#         if source_comm == target_comm:
#             # Intra-community: warna senada komunitas + 80 (alpha ~50%)
#             edge_color = dynamic_colors[source_comm % len(dynamic_colors)] + '80'
#         else:
#             # Inter-community: abu-abu netral semi-transparan
#             edge_color = '#bdc3c780'

#         title_hover = (
#             f"<b>Confidence</b> P({v}|{u}): {conf:.3f}<br>"
#             f"<b>Lift:</b> {lift:.2f}"
#         )
#         net.add_edge(u, v, value=edge_width, title=title_hover, color=edge_color, arrows='to')

#     # ── 7. PHYSICS & INTERACTION OPTIONS (ZIP A + ZIP B merge) ────────────────
#     net.set_options("""
#     var options = {
#       "physics": {
#         "forceAtlas2Based": {
#           "gravitationalConstant": -100,
#           "centralGravity": 0.012,
#           "springLength": 140,
#           "springConstant": 0.06,
#           "avoidOverlap": 0.5
#         },
#         "minVelocity": 0.75,
#         "solver": "forceAtlas2Based"
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
#           "strokeWidth": 2,
#           "strokeColor": "#ffffff"
#         }
#       },
#       "edges": {
#         "smooth": {"type": "continuous", "roundness": 0.4},
#         "color": {"inherit": false}
#       }
#     }
#     """)

#     # ── 8. THREAD-SAFE HTML RENDERING (ZIP A — UUID temp file) ────────────────
#     temp_id = uuid.uuid4().hex
#     temp_path = f"/tmp/graph_render_{temp_id}.html"

#     try:
#         net.save_graph(temp_path)
#         with open(temp_path, 'r', encoding='utf-8') as f:
#             html_data = f.read()
#     finally:
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

#     return html_data

# def render_interactive_graph(G, community_map, centralities, category_map):

#     net = Network(
#         height="700px",
#         width="100%",
#         directed=True,
#         bgcolor="#ffffff",
#         font_color="black"
#     )

#     # Tambahkan node dan edge
#     for node in G.nodes():
#         net.add_node(node)

#     for u, v in G.edges():
#         net.add_edge(u, v)

#     # return html string
#     return net.generate_html()

def render_interactive_graph(
        G,
        community_map,
        centralities,
        category_map=None
):

    net = Network(
        height="700px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#2c3e50"
    )

    # jumlah komunitas
    n_comm = len(set(community_map.values()))

    colors = generate_hsv_colors(n_comm)

    # pagerank
    pr = centralities.set_index(
        "Product"
    )["PageRank Centrality"].to_dict()


    # NODE
    for node in G.nodes():

        comm = community_map.get(node,0)

        color = colors[comm]

        size = max(
            12,
            min(
                pr.get(node,0.01)*2000,
                60
            )
        )

        category = (
            category_map.get(node,"Unknown")
            if category_map
            else "Unknown"
        )

        tooltip = f"""
        <b>Product:</b> {node}<br>
        <b>Category:</b> {category}<br>
        <b>Community:</b> {comm}<br>
        <b>PageRank:</b> {pr.get(node,0):.4f}
        """

        net.add_node(
            node,
            label=node,
            size=size,
            color=color,
            title=tooltip
        )


    # EDGE
    for u,v,data in G.edges(data=True):

        c1 = community_map.get(u,0)
        c2 = community_map.get(v,0)

        if c1==c2:

            edge_color = colors[c1] + "80"

        else:

            edge_color = "#cccccc70"

        net.add_edge(
            u,
            v,
            color=edge_color,
            arrows="to"
        )



    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 120,
          "springConstant": 0.06,
          "avoidOverlap": 0.7
        },
        "solver": "forceAtlas2Based"
      },

      "interaction": {
        "hover": true,
        "navigationButtons": true
      },

      "nodes": {
        "font": {
          "size": 10,
          "strokeWidth": 2
        }
      },

      "edges": {
        "smooth": {
          "type":"continuous"
        }
      }

    }
    """)

    return net.generate_html()

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY CHARTS (ZIP B — fitur baru, tidak ada di ZIP A)
# ─────────────────────────────────────────────────────────────────────────────

def plot_top_centralities(df, centrality_type: str, title: str, color: str):
    """Membuat bar chart horizontal interaktif Top-10 produk berdasarkan metrik sentralitas."""
    top_df = df.sort_values(by=centrality_type, ascending=False).head(10).copy()
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
    """Membuat diagram garis visualisasi keruntuhan jaringan (Albert et al., 2000)."""
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
        yaxis_title="Fraksi Konektivitas Jaringan Toko (LCC)",
        template="plotly_white",
        hovermode="x unified"
    )
    return fig
