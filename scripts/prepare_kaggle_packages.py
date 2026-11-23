"""Prepare clean, secret-free Kaggle Model packages for PyTorch and Scikit-Learn."""
import os
import shutil
import json
import hashlib
from pathlib import Path

def prepare_kaggle_packages():
    project_root = Path(__file__).resolve().parent.parent
    dist_hf = project_root / 'dist_hf'
    dist_kaggle = project_root / 'dist_kaggle'

    if dist_kaggle.exists():
        shutil.rmtree(dist_kaggle)

    pt_dir = dist_kaggle / 'pytorch'
    sk_dir = dist_kaggle / 'scikit_learn'
    pt_dir.mkdir(parents=True, exist_ok=True)
    sk_dir.mkdir(parents=True, exist_ok=True)

    tiers = ['100', '1K', '10K', '100K', '1M']
    gnn_models = ['gat', 'gcn', 'graphsage']
    sk_models = ['gradient_boosting', 'random_forest', 'logistic_regression']

    # 1. Package PyTorch variation
    pt_records = []
    for t in tiers:
        for m in gnn_models:
            src = dist_hf / 'models' / t / m
            dst = pt_dir / 'models' / t / m
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / 'model.pt', dst / 'model.pt')
            shutil.copy2(src / 'config.json', dst / 'config.json')
            with open(src / 'model.pt', 'rb') as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            with open(src / 'config.json') as f:
                cfg = json.load(f)
            pt_records.append({
                'tier': t,
                'model_name': m,
                'framework': 'PyTorch Geometric',
                'artifact': f'models/{t}/{m}/model.pt',
                'sha256': sha,
                'metrics': cfg.get('metrics', {})
            })

    shutil.copy2(dist_hf / 'inference.py', pt_dir / 'inference.py')
    shutil.copy2(dist_hf / 'LICENSE', pt_dir / 'LICENSE')
    with open(pt_dir / 'model_manifest.json', 'w') as f:
        json.dump({'framework': 'pyTorch', 'models': pt_records}, f, indent=2)

    pt_meta = {
        'ownerSlug': 'aniketagarwal10aa',
        'modelSlug': 'amlnet',
        'instanceSlug': 'gnn-architectures',
        'framework': 'pyTorch',
        'overview': 'Graph Neural Network architectures (GAT, GCN, GraphSAGE) evaluated across all five financial simulation graph tiers (100 to 1,000,000 accounts).',
        'usage': '# AMLNet PyTorch Geometric GNN Models\n\n```python\nimport torch\nckpt = torch.load("models/100K/gat/model.pt", map_location="cpu", weights_only=True)\nprint("Model state:", ckpt.keys())\n```\n',
        'licenseName': 'Apache 2.0',
        'fineTunable': False
    }
    with open(pt_dir / 'model-instance-metadata.json', 'w') as f:
        json.dump(pt_meta, f, indent=2)

    # 2. Package Scikit-Learn variation
    sk_records = []
    for t in tiers:
        for m in sk_models:
            src = dist_hf / 'models' / t / m
            dst = sk_dir / 'models' / t / m
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / 'model.joblib', dst / 'model.joblib')
            shutil.copy2(src / 'standard_scaler.joblib', dst / 'standard_scaler.joblib')
            shutil.copy2(src / 'config.json', dst / 'config.json')
            with open(src / 'model.joblib', 'rb') as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            with open(src / 'config.json') as f:
                cfg = json.load(f)
            sk_records.append({
                'tier': t,
                'model_name': m,
                'framework': 'Scikit-Learn',
                'artifact': f'models/{t}/{m}/model.joblib',
                'sha256': sha,
                'metrics': cfg.get('metrics', {})
            })

    shutil.copy2(dist_hf / 'LICENSE', sk_dir / 'LICENSE')
    with open(sk_dir / 'model_manifest.json', 'w') as f:
        json.dump({'framework': 'scikitLearn', 'models': sk_records}, f, indent=2)

    sk_meta = {
        'ownerSlug': 'aniketagarwal10aa',
        'modelSlug': 'amlnet',
        'instanceSlug': 'tabular-baselines',
        'framework': 'scikitLearn',
        'overview': 'Gradient Boosting, Random Forest, and Regularized Logistic Regression baselines evaluated across all five financial simulation graph tiers (100 to 1,000,000 accounts).',
        'usage': '# AMLNet Scikit-Learn Models\n\n```python\nimport joblib\npkg = joblib.load("models/100K/gradient_boosting/model.joblib")\nmodel = pkg["model"]\nscaler = joblib.load("models/100K/gradient_boosting/standard_scaler.joblib")\n```\n',
        'licenseName': 'Apache 2.0',
        'fineTunable': False
    }
    with open(sk_dir / 'model-instance-metadata.json', 'w') as f:
        json.dump(sk_meta, f, indent=2)

    print(f'Successfully prepared dist_kaggle with {len(pt_records)} PyTorch models and {len(sk_records)} Scikit-Learn models.')

if __name__ == '__main__':
    prepare_kaggle_packages()
