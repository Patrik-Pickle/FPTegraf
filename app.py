import streamlit as st
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
import networkx as nx
import matplotlib.pyplot as plt

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Market Basket Graph", layout="wide")
st.title("🛒 Dashboard Market Basket Analysis")
st.write("Unggah dataset transaksi untuk menganalisis keterhubungan produk menggunakan Algoritma Apriori dan Teori Graf.")

# --- FUNGSI PIPELINE ---
@st.cache_data # Menambahkan cache agar tidak perlu proses ulang saat geser slider
def run_market_basket_graph(df, min_support, min_lift):
    # 1. Preprocessing: Menggabungkan Member dan Date menjadi ID Transaksi unik
    df['Transaction_ID'] = df['Member_number'].astype(str) + "_" + df['Date'].astype(str)
    
    # Membuat format basket (pivot table)
    basket = (df.groupby(['Transaction_ID', 'itemDescription'])['itemDescription']
              .count().unstack().reset_index().fillna(0)
              .set_index('Transaction_ID'))
    
    # Konversi ke boolean (True jika dibeli, False jika tidak)
    basket_sets = basket.map(lambda x: 1 if x > 0 else 0).astype(bool)
    
    # 2. Apriori & Rules
    frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)
    
# Cek apakah ada frequent itemsets yang ditemukan
    if frequent_itemsets.empty:
        return pd.DataFrame(), nx.DiGraph() # Kembalikan objek kosong, bukan None
        
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # 3. Membangun Graf
    G = nx.DiGraph()
    for idx, row in rules.iterrows():
        # Karena item bisa berupa frozenset, kita ambil item pertamanya
        antecedent = list(row['antecedents'])[0]
        consequent = list(row['consequents'])[0]
        weight = row['lift']
        G.add_edge(antecedent, consequent, weight=weight)
        
    return rules, G

# --- SIDEBAR UNTUK UPLOAD & PENGATURAN PARAMETER ---
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV Dataset", type=['csv'])

st.sidebar.header("2. Tuning Parameter")
# Catatan: Nilai support default dikecilkan (0.001) karena pada dataset asli retail, kemunculan kombinasi item biasanya sangat kecil persentasenya
support_val = st.sidebar.slider("Minimum Support", 0.0001, 0.1, 0.001, format="%.4f")
lift_val = st.sidebar.slider("Minimum Lift", 0.1, 5.0, 1.0)

# --- EKSEKUSI & TAMPILAN ---
if uploaded_file is not None:
    # Membaca dataset
    df_raw = pd.read_csv(uploaded_file)
    
    # Tampilkan preview raw data
    with st.expander("Lihat Preview Dataset"):
        st.dataframe(df_raw.head())
        st.write(f"Total baris data: {df_raw.shape[0]}")
    
    if st.button("Jalankan Analisis", type="primary"):
        with st.spinner("Memproses algoritma..."):
            # Pastikan kolom yang dibutuhkan ada di dataset
            required_cols = {'Member_number', 'Date', 'itemDescription'}
            if not required_cols.issubset(df_raw.columns):
                st.error(f"Error: Dataset harus memiliki kolom: {required_cols}. Kolom terdeteksi: {set(df_raw.columns)}")
            else:
                rules_df, product_graph = run_market_basket_graph(df_raw, support_val, lift_val)
                
                if rules_df.empty:
                    st.warning("Tidak ditemukan pola hubungan (rules). Coba turunkan nilai **Minimum Support** atau **Minimum Lift** di sidebar.")
                else:
                    st.success(f"Analisis Selesai! Ditemukan {len(rules_df)} kombinasi hubungan.")
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.subheader("Tabel Hubungan Produk")
                        # Format ulang tabel agar lebih rapi
                        display_df = rules_df[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
                        display_df['antecedents'] = display_df['antecedents'].apply(lambda x: ', '.join(list(x)))
                        display_df['consequents'] = display_df['consequents'].apply(lambda x: ', '.join(list(x)))
                        st.dataframe(display_df, hide_index=True)
                        
                    with col2:
                        st.subheader("Network Graph Visualisasi")
                        
                        # Plotting dengan Matplotlib
                        fig, ax = plt.subplots(figsize=(10, 8))
                        
                        # Atur layout algoritma
                        pos = nx.spring_layout(product_graph, k=2, seed=42)
                        
                        # Ukuran node berdasarkan derajat (seberapa banyak dia terhubung)
                        node_sizes = [dict(product_graph.degree)[node] * 300 for node in product_graph.nodes()]
                        # Batasi ukuran minimal agar tidak hilang jika degree-nya kecil
                        node_sizes = [max(size, 800) for size in node_sizes]
                        
                        nx.draw_networkx_nodes(product_graph, pos, node_color='#00f2ff', node_size=node_sizes, edgecolors='black', ax=ax)
                        nx.draw_networkx_edges(product_graph, pos, edge_color='#cccccc', arrows=True, ax=ax)
                        
                        # Pengaturan font agar tidak tumpang tindih
                        nx.draw_networkx_labels(product_graph, pos, font_size=9, font_weight='bold', font_family='sans-serif', ax=ax)
                        
                        plt.axis('off')
                        
                        # Tampilkan grafik matplotlib di dalam Streamlit
                        st.pyplot(fig)
else:
    st.info("👈 Silakan upload file CSV dataset kamu di menu Sidebar sebelah kiri terlebih dahulu.")
