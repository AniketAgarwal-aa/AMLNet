import io, json, random, pickle
from datetime import datetime
import numpy as np, torch
from torch import nn
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
from ..config import ARTIFACT_DIR, SEED
from ..services.graph import build_graph_features, edge_index, FEATURE_NAMES

class AMLGCN(nn.Module):
    def __init__(self, n_features):
        super().__init__(); self.gcn1=GCNConv(n_features,32); self.gcn2=GCNConv(32,16); self.out=nn.Linear(16,2); self.dropout=nn.Dropout(.25)
    def forward(self,x,edges):
        hidden=self.dropout(torch.relu(self.gcn1(x,edges)))
        return self.out(self.gcn2(hidden,edges))

def _metrics(y,p):
    acc=accuracy_score(y,p); pr,re,f1,_=precision_recall_fscore_support(y,p,average='binary',zero_division=0)
    return {'accuracy':float(acc),'precision':float(pr),'recall':float(re),'f1':float(f1),'confusion_matrix':confusion_matrix(y,p).tolist(),'classification_report':classification_report(y,p,output_dict=True,zero_division=0)}

def train_models(accounts, transactions, epochs=160):
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    _, raw, scaled, scaler=build_graph_features(accounts,transactions); labels=accounts.label.to_numpy(); idx=np.arange(len(labels))
    train_i,tmp_i=train_test_split(idx,test_size=.4,stratify=labels,random_state=SEED)
    val_i,test_i=train_test_split(tmp_i,test_size=.5,stratify=labels[tmp_i],random_state=SEED)
    edges=torch.tensor(edge_index(accounts,transactions),dtype=torch.long); x=torch.tensor(scaled,dtype=torch.float32); y=torch.tensor(labels,dtype=torch.long)
    data=Data(x=x,edge_index=edges,y=y); model=AMLGCN(x.shape[1]); weights=torch.tensor([1., (labels==0).sum()/(labels==1).sum()],dtype=torch.float32)
    opt=torch.optim.Adam(model.parameters(),lr=.01,weight_decay=5e-4); loss_fn=nn.CrossEntropyLoss(weight=weights)
    best=(float('inf'),None); wait=0; history=[]
    tr=torch.tensor(train_i); va=torch.tensor(val_i)
    for epoch in range(epochs):
        model.train(); opt.zero_grad(); logits=model(data.x,data.edge_index); loss=loss_fn(logits[tr],y[tr]); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            val_loss=loss_fn(model(data.x,data.edge_index)[va],y[va]).item()
        history.append({'epoch':epoch+1,'train_loss':float(loss.item()),'val_loss':float(val_loss)})
        if val_loss < best[0]-1e-4: best=(val_loss,{k:v.detach().clone() for k,v in model.state_dict().items()}); wait=0
        else: wait+=1
        if wait>=25: break
    model.load_state_dict(best[1]); model.eval()
    with torch.no_grad(): probs=torch.softmax(model(data.x,data.edge_index),1)[:,1].numpy()
    gnn_metrics=_metrics(labels[test_i],(probs[test_i]>=.5).astype(int))
    baseline=LogisticRegression(class_weight='balanced',max_iter=1000,random_state=SEED).fit(scaled[train_i],labels[train_i])
    base_metrics=_metrics(labels[test_i],baseline.predict(scaled[test_i]))
    metrics={'generated_at':datetime.utcnow().isoformat()+'Z','split':{'train':len(train_i),'validation':len(val_i),'test':len(test_i)},'gcn':gnn_metrics,'logistic_regression':base_metrics,'training_history':history,'note':'Metrics are held-out account-level results on a small synthetic dataset; they are demonstration-only.'}
    model_buffer=io.BytesIO(); torch.save({'state_dict':model.state_dict(),'input_dim':x.shape[1]},model_buffer)
    scaler_buffer=io.BytesIO(); pickle.dump(scaler,scaler_buffer)
    model_blob=model_buffer.getvalue(); scaler_blob=scaler_buffer.getvalue()
    # Development convenience copies only. Production source-of-truth is ModelArtifact.
    (ARTIFACT_DIR/'gnn_model.pt').write_bytes(model_blob)
    (ARTIFACT_DIR/'scaler.pkl').write_bytes(scaler_blob)
    (ARTIFACT_DIR/'metrics.json').write_text(json.dumps(metrics,indent=2)); (ARTIFACT_DIR/'model_config.json').write_text(json.dumps({'architecture':'GCNConv(10,32) -> ReLU/Dropout -> GCNConv(32,16) -> Linear(16,2)','epochs_completed':len(history),'seed':SEED,'risk_weights':{'gnn_probability':.7,'rule_score':.3},'directed_graph_note':'Transaction graph stays directed for pattern detection; the GCN receives a symmetrized edge index.'},indent=2))
    return probs, raw, metrics, model_blob, scaler_blob

def load_metrics():
    path=ARTIFACT_DIR/'metrics.json'; return json.loads(path.read_text()) if path.exists() else None
