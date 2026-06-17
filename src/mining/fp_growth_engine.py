"""
FP-Growth Mining Engine — Version C (Merged)
=============================================
SOURCE DECISION:
  ALGORITHM  : ZIP A  (FP-Growth + Sparse Matrix — O(N) vs Apriori O(2^N) di ZIP B)
  ROBUSTNESS : ZIP B  (validation, empty-result guard, multi-item edge handling)
  GRAPH TYPE : ZIP A  (DiGraph — lebih akurat secara ilmiah daripada UndirectedGraph ZIP B)
"""

import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
import networkx as nx
import logging

logger = logging.getLogger(__name__)


def mine_association_rules(df: pd.DataFrame, min_support: float = 0.001, min_lift: float = 1.0) -> pd.DataFrame:
    """
    Mengekstrak aturan asosiasi menggunakan FP-Growth dan Sparse Matrix.
    Kompleksitas asimtotik O(N) — jauh lebih efisien dari Apriori O(2^N) milik ZIP B.
    Memory-safe untuk dataset enterprise berskala besar.
    """
    try:
        logger.info("Memulai agregasi transaksi data ritel...")
        df = df.copy()
        df['Transaction_ID'] = df['Member_number'].astype(str) + "_" + df['Date'].astype(str)

        # Agregasi data menjadi list of lists transaksi per ID
        transactions = df.groupby('Transaction_ID')['itemDescription'].apply(list).tolist()

        logger.info(f"Total transaksi: {len(transactions)}. Melakukan Sparse Encoding...")
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions, sparse=True)

        # Sparse DataFrame Pandas — hemat memori untuk katalog produk besar
        sparse_df = pd.DataFrame.sparse.from_spmatrix(te_ary, columns=te.columns_)

        logger.info(f"Mengeksekusi FP-Growth dengan min_support={min_support}...")
        frequent_itemsets = fpgrowth(sparse_df, min_support=min_support, use_colnames=True)

        if frequent_itemsets.empty:
            logger.warning("FP-Growth: tidak ada frequent itemsets yang memenuhi threshold.")
            return pd.DataFrame()

        logger.info("Menghasilkan Association Rules...")
        rules = association_rules(frequent_itemsets, metric='lift', min_threshold=min_lift)

        if rules.empty:
            logger.warning("Tidak ada aturan asosiasi yang memenuhi min_lift.")
            return pd.DataFrame()

        logger.info(f"Berhasil menghasilkan {len(rules)} aturan asosiasi.")
        return rules

    except Exception as e:
        logger.error(f"Kegagalan FP-Growth engine: {str(e)}")
        raise


def build_directed_graph(rules: pd.DataFrame) -> nx.DiGraph:
    """
    Membangun Directed Graph (DiGraph) dari aturan asosiasi.
    DiGraph lebih akurat ilmiah: P(B|A) ≠ P(A|B) (Confidence tidak simetris).
    Edge merepresentasikan aliran probabilitas bersyarat (Confidence).
    Menggunakan logika multi-item antecedents/consequents dari ZIP B.
    """
    G = nx.DiGraph()

    if rules is None or rules.empty:
        logger.warning("Rules DataFrame kosong. Mengembalikan graf kosong.")
        return G

    logger.info(f"Membangun DiGraph dari {len(rules)} aturan asosiasi...")

    for _, row in rules.iterrows():
        antecedents = list(row['antecedents'])
        consequents = list(row['consequents'])

        confidence = float(row['confidence'])
        lift = float(row['lift'])
        support = float(row['support'])

        # Mapping hyperedge → kombinasi dyadic directed edges
        for ant in antecedents:
            for con in consequents:
                if ant != con:
                    if G.has_edge(ant, con):
                        # Pertahankan rule terkuat (max confidence = asosiasi paling deterministik)
                        if confidence > G[ant][con]['confidence']:
                            G[ant][con]['confidence'] = confidence
                            G[ant][con]['lift'] = lift
                            G[ant][con]['support'] = support
                    else:
                        G.add_edge(ant, con, confidence=confidence, lift=lift, support=support)

    logger.info(f"DiGraph selesai: {G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges.")
    return G
