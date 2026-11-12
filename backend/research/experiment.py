"""Reproducible IBM AMLSim model comparison (research-only)."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import numpy as np, pandas as pd, torch
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, classification_report, confusion_matrix, f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch_geometric.nn import GCNConv, SAGEConv

class ResearchGCN(nn.Module):
    def __init__(self, n, improved=False):
        super().__init__(); hidden = 48 if improved else 32; self.a=GCNConv(n,hidden); self.b=GCNConv(hidden,16); self.o=nn.Linear(16,2); self.drop=nn.Dropout(.30 if improved else .20)
    def forward(self,x,e): return self.o(self.b(self.drop(torch.relu(self.a(x,e))),e))

class ResearchSAGE(nn.Module):
    def __init__(self,n):
        super().__init__(); self.a=SAGEConv(n,32); self.b=SAGEConv(32,16); self.o=nn.Linear(16,2); self.drop=nn.Dropout(.20)
    def forward(self,x,e): return self.o(self.b(self.drop(torch.relu(self.a(x,e))),e))

def features(accounts, tx):
    ids=accounts.ACCOUNT_ID.astype(str).tolist(); ix={v:i for i,v in enumerate(ids)}; n=len(ids); f=np.zeros((n,10),dtype=np.float32); edges=[]; ins={i:set() for i in range(n)}; outs={i:set() for i in range(n)}
    for c in tx.itertuples(index=False):
        s,r=str(c.SENDER_ACCOUNT_ID),str(c.RECEIVER_ACCOUNT_ID)
        if s not in ix or r not in ix: continue
        si,ri=ix[s],ix[r]; amount=float(c.TX_AMOUNT); edges += [(si,ri),(ri,si)]; f[si,1]+=1; f[ri,0]+=1; f[si,3]+=amount; f[ri,2]+=amount; outs[si].add(r); ins[ri].add(s)
    for i in range(n): f[i,6]=len(ins[i])+len(outs[i]); f[i,7]=f[i,2]/(f[i,3] or 1); f[i,8]=np.log1p(f[i,2]); f[i,9]=np.log1p(f[i,3])
    return f,np.asarray(edges,dtype=np.int64).T if edges else np.empty((2,0),dtype=np.int64)

def metrics(y,pred,prob,threshold):
    cm=confusion_matrix(y,pred,labels=[0,1]); tn,fp,fn,tp=cm.ravel(); return {'threshold':float(threshold),'accuracy':float(accuracy_score(y,pred)),'precision':float(precision_score(y,pred,zero_division=0)),'recall':float(recall_score(y,pred,zero_division=0)),'f1':float(f1_score(y,pred,zero_division=0)),'pr_auc':float(average_precision_score(y,prob)),'roc_auc':float(roc_auc_score(y,prob)) if len(np.unique(y))>1 else 0.0,'false_positive_rate':float(fp/(fp+tn) if fp+tn else 0),'false_negative_rate':float(fn/(fn+tp) if fn+tp else 0),'confusion_matrix':cm.tolist(),'classification_report':classification_report(y,pred,output_dict=True,zero_division=0)}

def best_threshold(y,p):
    precision,recall,thresholds=precision_recall_curve(y,p)
    if not len(thresholds): return .5
    f=2*precision[:-1]*recall[:-1]/(precision[:-1]+recall[:-1]+1e-9); return float(thresholds[int(np.nanargmax(f))])

def fit_gnn(model,x,e,labels,tr,va,seed,epochs,class_weight):
    torch.manual_seed(seed); opt=torch.optim.Adam(model.parameters(),lr=.01,weight_decay=5e-4); loss_fn=nn.CrossEntropyLoss(weight=torch.tensor(class_weight,dtype=torch.float32)); best_state=None; best_f1=-1; wait=0
    for _ in range(epochs):
        model.train(); opt.zero_grad(); loss_fn(model(x,e)[tr],labels[tr]).backward(); opt.step(); model.eval()
        with torch.no_grad(): p=torch.softmax(model(x,e),1)[:,1].numpy()
        threshold=best_threshold(labels[va].numpy(),p[va]); score=f1_score(labels[va].numpy(),p[va]>=threshold,zero_division=0)
        if score>best_f1: best_f1=score; best_state={k:v.detach().clone() for k,v in model.state_dict().items()}; wait=0
        else:
            wait+=1
            if wait>=15: break
    if best_state: model.load_state_dict(best_state)
    model.eval();
    with torch.no_grad(): return torch.softmax(model(x,e),1)[:,1].numpy()

def run(subset:Path,output:Path,seed=42,epochs=120):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); output.mkdir(parents=True,exist_ok=True)
    accounts=pd.read_csv(subset/'accounts.csv',dtype={'ACCOUNT_ID':str}); tx=pd.read_csv(subset/'transactions.csv',dtype={'SENDER_ACCOUNT_ID':str,'RECEIVER_ACCOUNT_ID':str}); y=accounts.IS_FRAUD.astype(str).str.lower().isin(['true','1','yes']).astype(int).to_numpy(); raw,edge_np=features(accounts,tx); scaler=StandardScaler(); x_np=scaler.fit_transform(raw); idx=np.arange(len(y)); tr,tmp=train_test_split(idx,test_size=.4,stratify=y,random_state=seed); va,te=train_test_split(tmp,test_size=.5,stratify=y[tmp],random_state=seed); class_weight=[1.,max(1.,(y==0).sum()/max(1,(y==1).sum()))]; results={}
    for name,clf in [('logistic_regression',LogisticRegression(max_iter=1000,class_weight='balanced',random_state=seed)),('random_forest',RandomForestClassifier(n_estimators=250,class_weight='balanced_subsample',random_state=seed,n_jobs=1))]:
        clf.fit(x_np[tr],y[tr]); pval=clf.predict_proba(x_np[va])[:,1]; ptest=clf.predict_proba(x_np[te])[:,1]; threshold=best_threshold(y[va],pval); results[name]=metrics(y[te],ptest>=threshold,ptest,threshold)
    x=torch.tensor(x_np,dtype=torch.float32); edge=torch.tensor(edge_np,dtype=torch.long); labels=torch.tensor(y,dtype=torch.long)
    for name,model in [('gcn_existing',ResearchGCN(x.shape[1],False)),('gcn_improved',ResearchGCN(x.shape[1],True)),('graphsage',ResearchSAGE(x.shape[1]))]:
        p=fit_gnn(model,x,edge,labels,tr,va,seed,epochs,class_weight); threshold=best_threshold(y[va],p[va]); results[name]=metrics(y[te],p[te]>=threshold,p[te],threshold)
    result={'dataset':'IBM AMLSim subset','source_subset':str(subset.resolve()),'seed':seed,'split':{'train':len(tr),'validation':len(va),'test':len(te)},'positive_accounts':int(y.sum()),'models':results,'features':['incoming_count','outgoing_count','total_incoming','total_outgoing','outgoing_event_count','incoming_event_count','unique_counterparties','in_out_amount_ratio','log_total_incoming','log_total_outgoing'],'selection':'Identical stratified account split; threshold selected by validation F1; test labels untouched.','note':'Research-only comparison. No model is promoted to AMLNet production.'}
    (output/'comparison.json').write_text(json.dumps(result,indent=2)); print(json.dumps({k:{m:round(v[m],4) for m in ['accuracy','precision','recall','f1','pr_auc','roc_auc']} for k,v in results.items()},indent=2)); return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--subset',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--epochs',type=int,default=120); args=p.parse_args(); run(args.subset,args.output,epochs=args.epochs)
