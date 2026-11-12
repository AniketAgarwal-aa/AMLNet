import numpy as np, pandas as pd, networkx as nx
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES=['incoming_count','outgoing_count','total_incoming','total_outgoing','average_amount','unique_counterparties','in_out_ratio','avg_interval_minutes','circular_participation','rapid_transfer_count']
def build_graph_features(accounts, transactions):
    tx=transactions.copy(); tx['timestamp']=pd.to_datetime(tx['timestamp']); G=nx.DiGraph()
    G.add_nodes_from(accounts.id)
    for r in tx.itertuples(): G.add_edge(r.source_id,r.target_id,amount=r.amount,transaction_id=r.id,timestamp=r.timestamp)
    cycles=set(n for c in nx.simple_cycles(G,length_bound=5) if 3<=len(c)<=5 for n in c)
    rows=[]
    for aid in accounts.id:
        inc=tx[tx.target_id==aid]; out=tx[tx.source_id==aid]; involved=pd.concat([inc,out]).sort_values('timestamp')
        intervals=involved.timestamp.diff().dt.total_seconds().dropna()/60
        rapid=int((intervals<=30).sum())
        counterparties=set(inc.source_id).union(out.target_id)
        total_in=inc.amount.sum(); total_out=out.amount.sum(); count=len(involved)
        rows.append([len(inc),len(out),total_in,total_out,involved.amount.mean() if count else 0,len(counterparties),total_in/(total_out or 1),intervals.mean() if len(intervals) else 0,int(aid in cycles),rapid])
    raw=np.nan_to_num(np.array(rows,dtype=float)); scaler=StandardScaler(); scaled=scaler.fit_transform(raw)
    return G, raw, scaled, scaler

def edge_index(accounts, transactions):
    ix={a:i for i,a in enumerate(accounts.id)}; edges=[]
    for r in transactions.itertuples():
        # symmetrized adjacency for standard GCN; directed records remain in NetworkX/DB
        edges.extend([(ix[r.source_id],ix[r.target_id]),(ix[r.target_id],ix[r.source_id])])
    return np.asarray(edges,dtype=np.int64).T
