"""Lightweight research experiment tracking store using local SQLite."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "research_experiments.db"

def init_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                dataset_name TEXT NOT NULL,
                profile TEXT NOT NULL,
                model_name TEXT NOT NULL,
                metrics JSON NOT NULL,
                hyperparameters JSON NOT NULL,
                training_duration_seconds REAL,
                peak_rss_mb REAL,
                epochs_completed INTEGER,
                is_full_dataset BOOLEAN,
                ingestion_coverage_pct REAL,
                artifact_relative_path TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_experiment(
    exp_id: str,
    dataset_name: str,
    profile: str,
    model_name: str,
    metrics: Dict[str, Any],
    hyperparameters: Dict[str, Any],
    training_duration: float,
    peak_rss_mb: float,
    epochs: int,
    is_full_dataset: bool,
    ingestion_coverage_pct: float,
    artifact_rel_path: Optional[str] = None,
    status: str = "completed",
    error_message: Optional[str] = None,
    db_path: Path = DB_PATH
) -> str:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO experiments (
                id, dataset_name, profile, model_name, metrics, hyperparameters,
                training_duration_seconds, peak_rss_mb, epochs_completed,
                is_full_dataset, ingestion_coverage_pct, artifact_relative_path,
                status, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id, dataset_name, profile, model_name,
            json.dumps(metrics), json.dumps(hyperparameters),
            training_duration, peak_rss_mb, epochs,
            is_full_dataset, ingestion_coverage_pct, artifact_rel_path,
            status, error_message, datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
    return exp_id

import re

MANIFEST_PATH = Path(__file__).resolve().parent / "published_benchmark_manifest.json"

def _load_manifest_experiments() -> List[Dict[str, Any]]:
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r") as f:
                data = json.load(f)
                return data.get("experiments", [])
        except Exception:
            return []
    return []

def _extract_tier(id_str: str, name_str: str) -> str:
    combined = (id_str + " " + name_str).lower()
    # Explicit vertex/account scale matches
    if re.search(r'1m(v|vertices|-)', combined):
        return '1M'
    if re.search(r'100k(v|vertices|-)', combined):
        return '100K'
    if re.search(r'10k(v|vertices|-)', combined):
        return '10K'
    if re.search(r'1k(v|vertices|-)', combined):
        return '1K'
    if re.search(r'100(v|vertices|-)', combined) or 'synthetic_demo' in combined:
        return '100'
    return '100K'

def list_experiments(
    dataset_name: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 100,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    init_db(db_path)
    result = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Fetch all matching candidate rows ordered by recency
            if dataset_name:
                term = f"%{dataset_name}%"
                cursor.execute("SELECT * FROM experiments WHERE dataset_name LIKE ? OR id LIKE ? ORDER BY created_at DESC", (term, term))
            else:
                cursor.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for r in rows:
                d = dict(r)
                d['metrics'] = json.loads(d['metrics']) if d.get('metrics') else {}
                d['hyperparameters'] = json.loads(d['hyperparameters']) if d.get('hyperparameters') else {}
                d['tier'] = _extract_tier(d.get('id', ''), d.get('dataset_name', ''))
                d['hardware_device'] = "Apple Silicon M2 (CPU/MPS)"
                result.append(d)
    except Exception:
        result = []

    # Fallback to published manifest if SQLite has no records (e.g., fresh deployment on Render)
    if not result:
        result = _load_manifest_experiments()

    # Filter by tier if specified
    if tier:
        target_tier = tier.strip().upper()
        result = [r for r in result if r.get('tier', '').upper() == target_tier]

    return result[:limit]

def get_experiment(exp_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d['metrics'] = json.loads(d['metrics']) if d.get('metrics') else {}
                d['hyperparameters'] = json.loads(d['hyperparameters']) if d.get('hyperparameters') else {}
                d['tier'] = _extract_tier(d.get('id', ''), d.get('dataset_name', ''))
                return d
    except Exception:
        pass

    # Fallback to manifest
    for exp in _load_manifest_experiments():
        if exp.get('id') == exp_id:
            return exp
    return None

def export_experiments_df(db_path: Path = DB_PATH) -> pd.DataFrame:
    exps = list_experiments(limit=1000, db_path=db_path)
    flat = []
    for e in exps:
        m = e.get('metrics', {})
        flat.append({
            "experiment_id": e['id'],
            "dataset": e['dataset_name'],
            "profile": e['profile'],
            "model": e['model_name'],
            "status": e['status'],
            "accuracy": m.get('accuracy'),
            "precision": m.get('precision'),
            "recall": m.get('recall'),
            "f1": m.get('f1'),
            "pr_auc": m.get('pr_auc'),
            "roc_auc": m.get('roc_auc'),
            "threshold": m.get('threshold'),
            "duration_sec": e.get('training_duration_seconds'),
            "peak_rss_mb": e.get('peak_rss_mb'),
            "is_full_dataset": e.get('is_full_dataset'),
            "coverage_pct": e.get('ingestion_coverage_pct'),
            "created_at": e.get('created_at')
        })
    return pd.DataFrame(flat)
