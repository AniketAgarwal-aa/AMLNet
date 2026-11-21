"""Comprehensive tests for AMLNet 2.0 upgrades."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.main import app
from research.adapters.amlsim_adapter import IBMAMLSimAdapter
from research.adapters.synthetic_adapter import SyntheticDemoAdapter
from research.experiment_store import list_experiments, save_experiment, get_experiment
from research.training.trainer import compute_metrics, find_optimal_threshold
import numpy as np

@pytest.fixture
def client():
    return TestClient(app)

def test_explainability_endpoint(client):
    res = client.get('/api/explain/S001')
    assert res.status_code == 200
    data = res.json()
    assert 'account_id' in data
    assert 'rule_evidence' in data
    assert 'correlated_features' in data
    assert 'model_attribution' in data
    assert 'ground_truth_label' in data
    assert data['model_attribution']['gnn_weight_factor'] == 0.70

def test_subgraph_neighborhood_endpoint(client):
    res = client.get('/api/graph/subgraph?account_id=S001&hops=1')
    assert res.status_code == 200
    data = res.json()
    assert data['root_account'] == 'S001'
    assert len(data['nodes']) >= 1
    assert any(n['data']['is_root'] for n in data['nodes'])

def test_research_datasets_catalog(client):
    res = client.get('/api/research/datasets')
    assert res.status_code == 200
    data = res.json()
    assert data['default_tier'] == '100K'
    assert data['default_dataset_key'] == 'amlsim_100kv_10me'
    tiers = data['tiers']
    assert len(tiers) == 5

    tier_100k = next((t for t in tiers if t['tier_id'] == '100K'), None)
    assert tier_100k is not None
    assert tier_100k['is_default'] is True
    assert tier_100k['accounts'] == 100000
    assert tier_100k['transactions'] == 12476012
    assert 'coverage_details' in tier_100k
    assert 'Stratified' in tier_100k['coverage_details']['training_mode'] or 'Partition' in tier_100k['coverage_details']['training_mode']

    # Verify no private local file paths leaked
    catalog = data['datasets']
    for k, v in catalog.items():
        assert 'local_location' not in v

def test_tier_filtered_experiments(client):
    expected_models = {'logistic_regression', 'random_forest', 'gradient_boosting', 'gcn', 'graphsage', 'gat'}
    for tier in ['100', '1K', '10K', '100K', '1M']:
        res = client.get(f'/api/research/experiments?tier={tier}&limit=6')
        assert res.status_code == 200
        exps = res.json()['experiments']
        assert len(exps) == 6, f"Tier {tier} expected 6 experiments, got {len(exps)}"
        models_found = {e['model_name'] for e in exps}
        assert models_found == expected_models
        for e in exps:
            m = e['metrics']
            assert 'f1' in m and m['f1'] is not None
            assert 'recall' in m and m['recall'] is not None
            assert 'precision' in m and m['precision'] is not None
            assert 'pr_auc' in m and m['pr_auc'] is not None
            assert 'roc_auc' in m and m['roc_auc'] is not None
            assert e['training_duration_seconds'] is not None
            assert e['peak_rss_mb'] is not None

def test_research_experiments_api(client):
    res = client.get('/api/research/experiments')
    assert res.status_code == 200
    assert 'experiments' in res.json()
    assert isinstance(res.json()['experiments'], list)
    assert len(res.json()['experiments']) >= 30

def test_webauthn_biometric_flow(client):
    # 1. Status
    st = client.get('/api/auth/webauthn/status')
    assert st.status_code == 200
    assert st.json()['biometrics_supported'] is True

    # 2. Challenge generation
    reg_opt = client.post('/api/auth/webauthn/register-options', json={'username': 'investigator_test'})
    assert reg_opt.status_code == 200
    challenge = reg_opt.json()['challenge']
    assert len(challenge) > 10

    # 3. Register mock assertion
    reg_ver = client.post('/api/auth/webauthn/register-verify', json={
        'id': 'mock-cred-123',
        'type': 'public-key',
        'response': {'clientDataJSON': 'mock'}
    })
    assert reg_ver.status_code == 200
    token = reg_ver.json()['session_token']
    assert token is not None

    # 4. Use token on protected endpoint
    auth_opt = client.post('/api/auth/webauthn/auth-options')
    assert auth_opt.status_code == 200

def test_metric_calculation_and_calibration():
    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 0])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.4, 0.1, 0.2])
    opt_t = find_optimal_threshold(y_true, y_prob)
    assert 0.05 <= opt_t <= 0.95
    m = compute_metrics(y_true, y_prob, opt_t)
    assert 'f1' in m and 'precision' in m and 'recall' in m and 'pr_auc' in m and 'roc_auc' in m
    assert m['confusion_matrix'] is not None

def test_research_model_library_endpoint(client):
    res = client.get('/api/research/model-library?tier=100K')
    assert res.status_code == 200
    data = res.json()
    assert 'models' in data
    assert len(data['models']) == 6
    assert data['repository'] == 'AniketAgarwal-aa/AMLNet-Research'
    # Verify all 6 Tier 4 models are published
    published = [m for m in data['models'] if m['publication_status'].startswith('Published')]
    assert len(published) == 6
