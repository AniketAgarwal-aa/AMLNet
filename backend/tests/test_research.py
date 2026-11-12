import json
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).parents[1]))
from research.ibm_ingest import inspect_dataset, make_subset

def test_ibm_ingestion_preserves_schema_and_fraud(tmp_path):
    source=tmp_path/'source'; source.mkdir()
    accounts=pd.DataFrame([{'ACCOUNT_ID':'1','CUSTOMER_ID':'C1','INIT_BALANCE':10,'COUNTRY':'US','ACCOUNT_TYPE':'I','IS_FRAUD':False,'TX_BEHAVIOR_ID':1},{'ACCOUNT_ID':'2','CUSTOMER_ID':'C2','INIT_BALANCE':10,'COUNTRY':'US','ACCOUNT_TYPE':'I','IS_FRAUD':True,'TX_BEHAVIOR_ID':2}])
    tx=pd.DataFrame([{'TX_ID':str(i),'SENDER_ACCOUNT_ID':'1','RECEIVER_ACCOUNT_ID':'2','TX_TYPE':'TRANSFER','TX_AMOUNT':1,'TIMESTAMP':i,'IS_FRAUD':i==1,'ALERT_ID':-1} for i in range(4)])
    alerts=pd.DataFrame([{'ALERT_ID':'a','ALERT_TYPE':'cycle','IS_FRAUD':True,'TX_ID':'1','SENDER_ACCOUNT_ID':'1','RECEIVER_ACCOUNT_ID':'2','TX_TYPE':'TRANSFER','TX_AMOUNT':1,'TIMESTAMP':1}])
    accounts.to_csv(source/'accounts.csv',index=False); tx.to_csv(source/'transactions.csv',index=False); alerts.to_csv(source/'alerts.csv',index=False)
    report=inspect_dataset(source,chunk_size=2); assert report['accounts']==2 and report['transactions']==4 and report['transaction_fraud']==1
    out=tmp_path/'out'; subset=make_subset(source,out,max_transactions=2,seed=42,chunk_size=2); assert subset['selected_fraud_transactions']==1 and len(pd.read_csv(out/'transactions.csv'))==2
    assert json.loads((out/'subset_metadata.json').read_text())['seed']==42
