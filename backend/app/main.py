import hmac, json, threading
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from .database import get_db, SessionLocal
from .models import Account, Transaction, Alert, Prediction, TrainingRun, ModelArtifact
from .services.initialize import initialize, risk_level
from .services.graph import build_graph_features
from .ml.train import train_models, predict_with_artifact
from .config import CORS_ORIGINS, ADMIN_API_KEY, APP_ENV
from .detection.engine import detect_patterns, rule_scores

app=FastAPI(title='AMLNet API',version='1.0.0',description='Synthetic-data graph-based AML research/demo API')
app.add_middleware(CORSMiddleware,allow_origins=CORS_ORIGINS,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Admin-Key'])
training_lock=threading.Lock()
@app.on_event('startup')
def startup(): initialize()
def require_admin(x_admin_key: str | None = Header(default=None)):
    if not ADMIN_API_KEY or not x_admin_key or not hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(401, 'Administrative authentication required')
def account_out(a): return {'id':a.id,'account_type':a.account_type,'label':a.label,'gnn_probability':a.gnn_probability,'rule_score':a.rule_score,'final_risk':a.final_risk,'risk_level':a.risk_level,'features':a.features}
def tx_out(t): return {'id':t.id,'source_id':t.source_id,'target_id':t.target_id,'amount':t.amount,'timestamp':t.timestamp,'transaction_type':t.transaction_type,'scenario':t.scenario}

@app.get('/api/health')
def health(db:Session=Depends(get_db)):
    db.execute(__import__('sqlalchemy').text('SELECT 1'))
    return {'status':'healthy','service':'AMLNet','environment':APP_ENV,'synthetic_data_only':True}
@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db)):
    ac=db.query(Account).all(); tx=db.query(Transaction).all(); alerts=db.query(Alert).order_by(desc(Alert.timestamp)).limit(8).all()
    levels={x:sum(a.risk_level==x for a in ac) for x in ['Low','Medium','High','Critical']}
    return {'total_accounts':len(ac),'total_transactions':len(tx),'suspicious_accounts':sum(a.label for a in ac),'high_risk_accounts':sum(a.final_risk>=60 for a in ac),'total_volume':sum(t.amount for t in tx),'average_risk':sum(a.final_risk for a in ac)/len(ac),'risk_distribution':levels,'label_distribution':{'normal':sum(not a.label for a in ac),'suspicious':sum(a.label for a in ac)},'recent_alerts':[alert_out(a) for a in alerts]}
@app.get('/api/accounts')
def accounts(search:str='',risk_level:str|None=None,page:int=1,page_size:int=25,db:Session=Depends(get_db)):
    q=db.query(Account)
    if search:q=q.filter(Account.id.ilike(f'%{search}%'))
    if risk_level:q=q.filter(Account.risk_level==risk_level)
    total=q.count(); items=q.order_by(desc(Account.final_risk)).offset((page-1)*page_size).limit(min(page_size,100)).all()
    return {'items':[account_out(x) for x in items],'total':total,'page':page,'page_size':page_size}
@app.get('/api/accounts/{account_id}')
def account(account_id:str,db:Session=Depends(get_db)):
    a=db.get(Account,account_id)
    if not a: raise HTTPException(404,'Account not found')
    return account_out(a)
@app.get('/api/accounts/{account_id}/transactions')
def account_transactions(account_id:str,db:Session=Depends(get_db)):
    if not db.get(Account,account_id): raise HTTPException(404,'Account not found')
    tx=db.query(Transaction).filter(or_(Transaction.source_id==account_id,Transaction.target_id==account_id)).order_by(desc(Transaction.timestamp)).all()
    return {'items':[tx_out(t) for t in tx]}
@app.get('/api/transactions')
def transactions(account:str='',min_amount:float|None=None,max_amount:float|None=None,start:str|None=None,end:str|None=None,page:int=1,page_size:int=50,db:Session=Depends(get_db)):
    q=db.query(Transaction)
    if account:q=q.filter(or_(Transaction.source_id.ilike(f'%{account}%'),Transaction.target_id.ilike(f'%{account}%')))
    if min_amount is not None:q=q.filter(Transaction.amount>=min_amount)
    if max_amount is not None:q=q.filter(Transaction.amount<=max_amount)
    if start:q=q.filter(Transaction.timestamp>=datetime.fromisoformat(start))
    if end:q=q.filter(Transaction.timestamp<=datetime.fromisoformat(end))
    total=q.count(); rows=q.order_by(desc(Transaction.timestamp)).offset((page-1)*page_size).limit(min(page_size,200)).all()
    return {'items':[tx_out(x) for x in rows],'total':total,'page':page}
@app.get('/api/graph')
def graph(risk_level:str|None=None,limit:int=500,db:Session=Depends(get_db)):
    q=db.query(Account)
    if risk_level:q=q.filter(Account.risk_level==risk_level)
    nodes=q.all(); ids={a.id for a in nodes}; tx=[t for t in db.query(Transaction).limit(limit).all() if t.source_id in ids and t.target_id in ids]
    return {'nodes':[{'data':{'id':a.id,'label':a.id,'risk':a.final_risk,'risk_level':a.risk_level}} for a in nodes],'edges':[{'data':{'id':t.id,'source':t.source_id,'target':t.target_id,'amount':t.amount}} for t in tx]}
def alert_out(a): return {'id':a.id,'account_ids':a.account_ids,'transaction_ids':a.transaction_ids,'pattern_type':a.pattern_type,'amount':a.amount,'timestamp':a.timestamp,'risk_level':a.risk_level,'explanation':a.explanation}
@app.get('/api/alerts')
def alerts(pattern_type:str|None=None,db:Session=Depends(get_db)):
    q=db.query(Alert)
    if pattern_type:q=q.filter(Alert.pattern_type==pattern_type)
    return {'items':[alert_out(a) for a in q.order_by(desc(Alert.timestamp)).all()]}
@app.get('/api/model/metrics')
def metrics(db:Session=Depends(get_db)):
    artifact=db.query(ModelArtifact).filter(ModelArtifact.status=='active').order_by(desc(ModelArtifact.id)).first()
    m=artifact.metrics if artifact else None
    if not m: raise HTTPException(404,'No model metrics available')
    return m
@app.get('/api/model/status')
def status(db:Session=Depends(get_db)):
    run=db.query(TrainingRun).order_by(desc(TrainingRun.id)).first()
    artifact=db.query(ModelArtifact).filter(ModelArtifact.status=='active').order_by(desc(ModelArtifact.id)).first()
    return {'status':run.status if run else 'uninitialized','last_run':run.completed_at if run else None,'error':run.error if run else None,'running':training_lock.locked(),'model_version':artifact.version if artifact else None}
def retrain(run_id):
    db=SessionLocal()
    try:
        ac=db.query(Account).order_by(Account.id).all(); tx=db.query(Transaction).all(); accounts=pd.DataFrame([{'id':a.id,'label':a.label} for a in ac]); transactions=pd.DataFrame([tx_out(t) for t in tx]); probs,raw,metrics,model_blob,scaler_blob=train_models(accounts,transactions); alerts=detect_patterns(transactions); rules=rule_scores(alerts)
        for i,a in enumerate(ac):
            a.gnn_probability=float(probs[i]); a.rule_score=rules.get(a.id,0); a.final_risk=100*(.7*a.gnn_probability+.3*a.rule_score/100); a.risk_level=risk_level(a.final_risk)
        db.query(ModelArtifact).filter(ModelArtifact.status=='active').update({'status':'superseded'})
        db.add(ModelArtifact(version=f'retrain-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',status='active',model_blob=model_blob,scaler_blob=scaler_blob,metrics=metrics,configuration={'risk_weights':{'gnn_probability':.7,'rule_score':.3},'storage':'database'}))
        run=db.get(TrainingRun,run_id); run.status='completed';run.completed_at=datetime.utcnow();run.metrics=metrics;db.commit()
    except Exception as e:
        db.rollback(); run=db.get(TrainingRun,run_id);run.status='failed';run.error=str(e);run.completed_at=datetime.utcnow();db.commit()
    finally: db.close();training_lock.release()
@app.post('/api/model/train')
def train(db:Session=Depends(get_db), _: None=Depends(require_admin)):
    if not training_lock.acquire(blocking=False): raise HTTPException(409,'Model training is already running')
    run=TrainingRun(status='running');db.add(run);db.commit();db.refresh(run);threading.Thread(target=retrain,args=(run.id,),daemon=True).start();return {'status':'running','run_id':run.id}
@app.post('/api/model/predict')
def predict(db:Session=Depends(get_db), _: None=Depends(require_admin)):
    artifact=db.query(ModelArtifact).filter(ModelArtifact.status=='active').order_by(desc(ModelArtifact.id)).first()
    if not artifact: raise HTTPException(503,'No persisted model artifact is available')
    accounts=db.query(Account).order_by(Account.id).all(); tx=db.query(Transaction).all()
    account_frame=pd.DataFrame([{'id':a.id,'label':a.label} for a in accounts]); tx_frame=pd.DataFrame([tx_out(t) for t in tx])
    probabilities,_=predict_with_artifact(account_frame,tx_frame,artifact.model_blob,artifact.scaler_blob)
    alerts=detect_patterns(tx_frame); rules=rule_scores(alerts)
    for i, account in enumerate(accounts):
        account.gnn_probability=float(probabilities[i]); account.rule_score=rules.get(account.id,0); account.final_risk=100*(.7*account.gnn_probability+.3*account.rule_score/100); account.risk_level=risk_level(account.final_risk)
        db.add(Prediction(account_id=account.id,probability=account.gnn_probability,final_risk=account.final_risk))
    db.commit()
    return {'updated_accounts':len(accounts),'model_version':artifact.version,'message':'Predictions were regenerated from the persisted GNN and scaler.'}
