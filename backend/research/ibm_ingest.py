"""Chunked IBM AMLSim inspection and reproducible subset creation.

The raw AMLSim folders are intentionally not imported into production SQLite/Neon.
This utility reads only selected columns, retains every fraud transaction, and
then samples normal transactions with a fixed seed. It is safe for an 8 GB laptop.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
import numpy as np

ACCOUNT_COLUMNS=['ACCOUNT_ID','CUSTOMER_ID','INIT_BALANCE','COUNTRY','ACCOUNT_TYPE','IS_FRAUD','TX_BEHAVIOR_ID']
TX_COLUMNS=['TX_ID','SENDER_ACCOUNT_ID','RECEIVER_ACCOUNT_ID','TX_TYPE','TX_AMOUNT','TIMESTAMP','IS_FRAUD','ALERT_ID']
ALERT_COLUMNS=['ALERT_ID','ALERT_TYPE','IS_FRAUD','TX_ID','SENDER_ACCOUNT_ID','RECEIVER_ACCOUNT_ID','TX_TYPE','TX_AMOUNT','TIMESTAMP']

def _bool_count(series): return int(series.astype(str).str.strip().str.lower().isin(['true','1','yes']).sum())

def inspect_dataset(source: Path, chunk_size=100_000) -> dict:
    accounts=pd.read_csv(source/'accounts.csv', usecols=ACCOUNT_COLUMNS)
    alerts=pd.read_csv(source/'alerts.csv', usecols=ALERT_COLUMNS)
    tx_rows=fraud_rows=0; amount=0.0; types={}; tx_ids=set(); duplicate_ids=0
    for chunk in pd.read_csv(source/'transactions.csv', usecols=TX_COLUMNS, chunksize=chunk_size):
        tx_rows+=len(chunk); fraud_rows+=_bool_count(chunk['IS_FRAUD']); amount+=float(chunk['TX_AMOUNT'].sum())
        for k,v in chunk['TX_TYPE'].value_counts().items(): types[str(k)]=types.get(str(k),0)+int(v)
        duplicate_ids += int(chunk['TX_ID'].duplicated().sum()); tx_ids.update(chunk['TX_ID'].astype(str))
    return {'source':str(source.resolve()),'accounts':len(accounts),'account_fraud':_bool_count(accounts['IS_FRAUD']),'transactions':tx_rows,'transaction_fraud':fraud_rows,'alerts':len(alerts),'alert_fraud':_bool_count(alerts['IS_FRAUD']),'alert_types':{str(k):int(v) for k,v in alerts['ALERT_TYPE'].value_counts().items()},'transaction_types':types,'transaction_amount_total':amount,'unique_transaction_ids':len(tx_ids),'duplicate_transaction_ids_seen_within_chunks':duplicate_ids,'schema':{'accounts':ACCOUNT_COLUMNS,'transactions':TX_COLUMNS,'alerts':ALERT_COLUMNS},'label_notes':'IS_FRAUD is preserved as source ground truth; model predictions are separate.'}

def make_subset(source: Path, output: Path, max_transactions=25_000, seed=42, chunk_size=100_000):
    output.mkdir(parents=True, exist_ok=True)
    accounts=pd.read_csv(source/'accounts.csv', usecols=ACCOUNT_COLUMNS); accounts.to_csv(output/'accounts.csv',index=False)
    alerts=pd.read_csv(source/'alerts.csv', usecols=ALERT_COLUMNS); alerts.to_csv(output/'alerts.csv',index=False)
    fraud=[]; normal_candidates=[]; rng=np.random.default_rng(seed)
    # Keep every source-labelled suspicious transaction, then reservoir-sample normal rows.
    for chunk in pd.read_csv(source/'transactions.csv', usecols=TX_COLUMNS, chunksize=chunk_size):
        mask=chunk['IS_FRAUD'].astype(str).str.strip().str.lower().isin(['true','1','yes'])
        fraud.append(chunk[mask])
        normal_chunk=chunk[~mask].copy()
        if len(normal_chunk):
            normal_chunk['_sample_key']=rng.random(len(normal_chunk))
            normal_candidates.append(normal_chunk)
            # Keep the candidate pool bounded even for the 1.3M-edge source.
            if len(normal_candidates) > 4:
                bounded=pd.concat(normal_candidates,ignore_index=True).nsmallest(max_transactions*2,'_sample_key')
                normal_candidates=[bounded]
    fraud_df=pd.concat(fraud,ignore_index=True) if fraud else pd.DataFrame(columns=TX_COLUMNS)
    normal_df=pd.concat(normal_candidates,ignore_index=True) if normal_candidates else pd.DataFrame(columns=TX_COLUMNS)
    if '_sample_key' in normal_df: normal_df=normal_df.drop(columns=['_sample_key'])
    remaining=max(0,max_transactions-len(fraud_df)); take=min(remaining,len(normal_df))
    normal_sample=normal_df.sample(n=take,random_state=seed) if take else normal_df.head(0)
    subset=pd.concat([fraud_df,normal_sample],ignore_index=True).sort_values('TX_ID')
    subset.to_csv(output/'transactions.csv',index=False)
    report={'seed':seed,'max_transactions':max_transactions,'selected_transactions':len(subset),'selected_fraud_transactions':_bool_count(subset['IS_FRAUD']),'accounts':len(accounts),'sampling':'all IS_FRAUD=true rows plus fixed-seed random sample of normal rows','source':str(source.resolve())}
    (output/'subset_metadata.json').write_text(json.dumps(report,indent=2)); return report

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--max-transactions',type=int,default=25_000); p.add_argument('--seed',type=int,default=42); args=p.parse_args()
    report=inspect_dataset(args.source); args.output.mkdir(parents=True,exist_ok=True); (args.output/'dataset_report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2)); print(json.dumps(make_subset(args.source,args.output,args.max_transactions,args.seed),indent=2))
if __name__=='__main__': main()
