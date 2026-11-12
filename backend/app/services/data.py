"""Deterministic synthetic AML data. Labels are derived from planted behavioural scenarios."""
import json, random
from datetime import datetime, timedelta
import pandas as pd
from ..config import DATA_DIR, SEED

def generate_dataset(force=False):
    paths=[DATA_DIR/'accounts.csv',DATA_DIR/'transactions.csv',DATA_DIR/'dataset_metadata.json']
    if not force and all(p.exists() for p in paths):
        return pd.read_csv(paths[0]), pd.read_csv(paths[1], parse_dates=['timestamp'])
    rng=random.Random(SEED); start=datetime(2025,1,1,9)
    normal=[f'A{i:03d}' for i in range(1,81)]; suspicious=[f'S{i:03d}' for i in range(1,21)]
    accounts=pd.DataFrame([{'id':x,'account_type':'personal' if i%3 else 'business','label':0,'scenario':'normal'} for i,x in enumerate(normal,1)]+[
        {'id':x,'account_type':'business' if i%2 else 'personal','label':1,'scenario':('circular' if i<=5 else 'rapid' if i<=10 else 'fan_in' if i<=15 else 'fan_out')} for i,x in enumerate(suspicious,1)])
    rows=[]
    def add(src,dst,amt,when,typ,scenario):
        rows.append({'id':f'T{len(rows)+1:04d}','source_id':src,'target_id':dst,'amount':round(amt,2),'timestamp':when,'transaction_type':typ,'scenario':scenario})
    # 420 regular salary/business/personal payments
    for i in range(420):
        src,dst=rng.sample(normal,2); kind=['salary','business_transfer','personal_transfer'][i%3]
        amount=rng.uniform(1600,6500) if kind=='salary' else rng.uniform(100,9000)
        add(src,dst,amount,start+timedelta(minutes=rng.randrange(60*24*30)),kind,'normal')
    # cycles: two rotations per account produces visible directed cycles, 30 tx
    cycle=suspicious[:5]
    for round_ in range(2):
        for j,src in enumerate(cycle): add(src,cycle[(j+1)%5],12000+round_*1200,start+timedelta(days=3+round_,minutes=j*6),'transfer','circular')
    # rapid chains, 4 per chain => 20 tx
    for j in range(5):
        hub=suspicious[5+j]; peers=normal[j*4:j*4+4]
        for k,dst in enumerate(peers): add(hub,dst,7000+k*250,start+timedelta(days=8,minutes=j*40+k*5),'transfer','rapid')
    # fan-in, 25 tx from normal sources to S011-S015
    for j,hub in enumerate(suspicious[10:15]):
        for k,src in enumerate(normal[20+j*5:25+j*5]): add(src,hub,9500+k*500,start+timedelta(days=12,minutes=j*20+k*4),'transfer','fan_in')
    # fan-out, 25 tx from S016-S020
    for j,hub in enumerate(suspicious[15:]):
        for k,dst in enumerate(normal[45+j*5:50+j*5]): add(hub,dst,10500+k*350,start+timedelta(days=16,minutes=j*20+k*4),'transfer','fan_out')
    assert len(rows)==500
    tx=pd.DataFrame(rows); accounts.to_csv(paths[0],index=False); tx.to_csv(paths[1],index=False)
    paths[2].write_text(json.dumps({'seed':SEED,'accounts':100,'transactions':500,'normal_accounts':80,'suspicious_accounts':20,'scenarios':['circular','rapid','fan_in','fan_out']},indent=2))
    return accounts,tx
