import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network
import tempfile

def create_pyvis_network(G, community_map, centralities_df):
    """Membuat jaringan interaktif PyVis dengan warna berdasarkan komunitas dan ukuran berdasarkan Centrality."""
    net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='black', notebook=False)
    
    # Mapping sentralitas untuk ukuran node
    degree_dict = centralities_df.set_index('Product')['Degree Centrality'].to_dict()
    
    # Palet warna komunitas
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for node in G.nodes():
        # Ukuran berdasarkan degree centrality
        size = max(10, degree_dict.get(node, 0) * 300)
        
        # Warna berdasarkan komunitas
        comm_id = community_map.get(node, 0)
        color = colors[comm_id % len(colors)]
        
        title = f"Produk: {node}\nKomunitas: {comm_id}\nDegree: {degree_dict.get(node, 0):.4f}"
        
        net.add_node(node, label=node, size=size, color=color, title=title)
        
    for edge in G.edges(data=True):
        weight = edge[2].get('weight', 1)
        # Menambahkan edge dengan ketebalan yang sesuai bobot
        net.add_edge(edge[0], edge[1], value=weight, title=f"Korelasi (Lift): {weight:.2f}")
        
    # Opsi Fisika (Gravitasi jaringan)
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      }
    }
    """)
    
    # Menyimpan ke file sementara untuk di-render di Streamlit
    path = tempfile.NamedTemporaryFile(delete=False, suffix='.html').name
    net.save_graph(path)
    return path

def plot_top_centralities(df, centrality_type, title, color):
    """Membuat Bar Chart Plotly untuk Top Node berdasarkan Centrality tertentu."""
    top_df = df.sort_values(by=centrality_type, ascending=False).head(10)
    fig = px.bar(top_df, x=centrality_type, y='Product', orientation='h', 
                 title=title, text_auto='.4f', color_discrete_sequence=[color])
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, 
                      margin=dict(l=0, r=0, t=40, b=0),
                      height=400)
    return fig

def plot_robustness(df):
    """Membuat plot yang menunjukkan dekonstruksi jaringan akibat penghapusan node."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Nodes Removed'], y=df['LCC Size (Fraction)'],
                             mode='lines+markers', name='Ukuran Komponen Utama (LCC)',
                             line=dict(color='red', width=3)))
    
    fig.update_layout(title="Analisis Ketahanan Jaringan (Albert et al., 2000)",
                      xaxis_title="Jumlah Produk Kunci Dihapus",
                      yaxis_title="Fraksi Jaringan Tetap Terhubung",
                      template="plotly_white",
                      hovermode="x unified")
    return fig