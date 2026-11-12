from collections import defaultdict
import networkx as nx
import pandas as pd

def detect_patterns(transactions, rapid_minutes=30, fan_threshold=4):
    tx=transactions.copy(); tx['timestamp']=pd.to_datetime(tx['timestamp']); alerts=[]; graph=nx.DiGraph()
    # Focus bounded cycle search on material transfers. This avoids enumerating the
    # combinatorial number of incidental cycles in a dense retail-payment graph.
    cycle_tx=tx[tx.amount>=10000]
    for r in cycle_tx.itertuples(): graph.add_edge(r.source_id,r.target_id,transaction_id=r.id,amount=float(r.amount),timestamp=r.timestamp)
    # simple cycles only 3..5, dedupe canonical account sets
    seen=set()
    for cycle in nx.simple_cycles(graph, length_bound=5):
        if 3<=len(cycle)<=5:
            key=tuple(sorted(cycle))
            if key in seen: continue
            seen.add(key); related=[]
            for i,a in enumerate(cycle): related.append(graph[a][cycle[(i+1)%len(cycle)]]['transaction_id'])
            subset=tx[tx.id.isin(related)]; alerts.append(_alert('circular',cycle,related,subset.amount.sum(),subset.timestamp.max(),'High',f'Directed cycle of {len(cycle)} accounts; investigate potential circular movement.'))
    # rapid outgoing sequences, grouped source and sorted
    for account, group in tx.sort_values('timestamp').groupby('source_id'):
        window=group[group.timestamp.diff().dt.total_seconds().fillna(999999)<=rapid_minutes*60]
        if len(window)>=2:
            alerts.append(_alert('rapid',[account]+window.target_id.tolist(),window.id.tolist(),window.amount.sum(),window.timestamp.max(),'High',f'{len(window)} outbound transfers occurred within {rapid_minutes} minutes.'))
    for target, group in tx.groupby('target_id'):
        if group.source_id.nunique()>=fan_threshold:
            alerts.append(_alert('fan_in',[target]+group.source_id.unique().tolist(),group.id.tolist(),group.amount.sum(),group.timestamp.max(),'High',f'{group.source_id.nunique()} counterparties concentrated funds into this account.'))
    for source, group in tx.groupby('source_id'):
        if group.target_id.nunique()>=fan_threshold:
            alerts.append(_alert('fan_out',[source]+group.target_id.unique().tolist(),group.id.tolist(),group.amount.sum(),group.timestamp.max(),'High',f'{group.target_id.nunique()} counterparties received funds from this account.'))
    return alerts

def _alert(kind, accounts, txids, amount, timestamp, level, explanation):
    import hashlib
    digest=hashlib.sha1((kind+'|'+','.join(sorted(set(accounts)))+'|'+','.join(sorted(txids))).encode()).hexdigest()[:10]
    return {'id':f'AL-{digest}','account_ids':list(dict.fromkeys(accounts)),'transaction_ids':list(dict.fromkeys(txids)),'pattern_type':kind,'amount':float(amount),'timestamp':timestamp.to_pydatetime() if hasattr(timestamp,'to_pydatetime') else timestamp,'risk_level':level,'explanation':explanation}

def rule_scores(alerts):
    scores=defaultdict(float)
    weights={'circular':70,'rapid':45,'fan_in':35,'fan_out':35}
    for a in alerts:
        for account in a['account_ids']: scores[account]=min(100,scores[account]+weights[a['pattern_type']])
    return scores
