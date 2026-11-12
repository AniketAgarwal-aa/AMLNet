from datetime import datetime
from sqlalchemy import select
from ..database import Base, engine, SessionLocal
from ..models import Account, Transaction, Alert, Prediction, TrainingRun, ModelArtifact
from .data import generate_dataset
from ..detection.engine import detect_patterns, rule_scores
from ..ml.train import train_models
from ..services.graph import FEATURE_NAMES

def risk_level(v): return 'Critical' if v>=80 else 'High' if v>=60 else 'Medium' if v>=30 else 'Low'
def initialize(train=True, force=False):
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        if db.scalar(select(Account).limit(1)) and not force: return
        if force:
            db.query(Prediction).delete(); db.query(Alert).delete(); db.query(Transaction).delete(); db.query(Account).delete(); db.commit()
        accounts,tx=generate_dataset(force=force)
        if train:
            probs, raw, metrics, model_blob, scaler_blob=train_models(accounts,tx)
            db.add(ModelArtifact(version=f'initial-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}', status='active', model_blob=model_blob, scaler_blob=scaler_blob, metrics=metrics, configuration={'risk_weights': {'gnn_probability': .7, 'rule_score': .3}, 'storage': 'database'}))
        else:
            probs, raw, metrics=([0.0]*len(accounts),None,None)
        alerts=detect_patterns(tx); rules=rule_scores(alerts)
        for i,row in accounts.iterrows():
            rule=rules.get(row.id,0.0); final=100*(.7*float(probs[i])+.3*rule/100)
            features={} if raw is None else {name:float(raw[i,j]) for j,name in enumerate(FEATURE_NAMES)}
            db.add(Account(id=row.id,account_type=row.account_type,label=int(row.label),gnn_probability=float(probs[i]),rule_score=rule,final_risk=final,risk_level=risk_level(final),features=features))
            db.add(Prediction(account_id=row.id,probability=float(probs[i]),final_risk=final))
        for row in tx.itertuples(): db.add(Transaction(id=row.id,source_id=row.source_id,target_id=row.target_id,amount=float(row.amount),timestamp=row.timestamp.to_pydatetime(),transaction_type=row.transaction_type,scenario=row.scenario))
        for a in alerts: db.add(Alert(**a))
        db.add(TrainingRun(status='completed',completed_at=datetime.utcnow(),metrics=metrics or {})); db.commit()
    finally: db.close()
