import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from app.services.data import generate_dataset
from app.services.graph import build_graph_features
from app.detection.engine import detect_patterns, rule_scores
def test_dataset_reproducible_shape(tmp_path, monkeypatch):
    a,t=generate_dataset(); assert len(a)==100 and len(t)==500 and a.label.sum()==20
def test_graph_and_patterns():
    a,t=generate_dataset(); g,raw,scaled,scaler=build_graph_features(a,t); alerts=detect_patterns(t); kinds={x['pattern_type'] for x in alerts}
    assert g.number_of_nodes()==100 and raw.shape==(100,10) and scaled.shape==(100,10)
    assert {'circular','rapid','fan_in','fan_out'} <= kinds
    assert rule_scores(alerts)['S001']>0

def test_api_smoke():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        dashboard=client.get('/api/dashboard')
        assert dashboard.status_code == 200
        assert dashboard.json()['total_transactions'] == 500
        assert client.get('/api/accounts/S001/transactions').status_code == 200
        assert client.get('/api/graph').status_code == 200
        assert client.get('/api/model/metrics').status_code == 200
