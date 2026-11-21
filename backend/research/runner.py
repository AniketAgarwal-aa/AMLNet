"""Unified Research Experiment Execution Engine for AMLNet 2.0."""
import os
import sys
import time
import uuid
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler

# Adjust path for stand-alone execution
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from research.device import get_device, get_process_memory_mb, ResourceProfile
from research.adapters.amlsim_adapter import IBMAMLSimAdapter
from research.adapters.synthetic_adapter import SyntheticDemoAdapter
from research.training.trainer import train_tabular_baselines, train_gnn_model
from research.experiment_store import save_experiment

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("amlnet.runner")

def resolve_dataset_adapter(dataset_key: str) -> Any:
    workspace = backend_dir.parent
    mapping = {
        "synthetic_demo": (workspace / "backend" / "data", SyntheticDemoAdapter, "AMLNet Synthetic Demo"),
        "amlsim_100v_10ke": (workspace / "100vertices-10Kedges", IBMAMLSimAdapter, "IBM AMLSim (100v-10Ke)"),
        "amlsim_1kv_100ke": (workspace / "1Kvertices-100Kedges", IBMAMLSimAdapter, "IBM AMLSim (1Kv-100Ke)"),
        "amlsim_10kv_1me": (workspace / "10Kvertices-1Medges", IBMAMLSimAdapter, "IBM AMLSim (10Kv-1Me)"),
        "amlsim_100kv_10me": (workspace / "100Kvertices-10Medges", IBMAMLSimAdapter, "IBM AMLSim (100Kv-10Me)"),
        "amlsim_1mv_100me": (workspace / "1Mvertices-100Medges", IBMAMLSimAdapter, "IBM AMLSim (1Mv-100Me)"),
    }
    if dataset_key not in mapping:
        raise ValueError(f"Unknown dataset key: {dataset_key}. Available: {list(mapping.keys())}")

    path, adapter_cls, name = mapping[dataset_key]
    if not path.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {path}")
    return adapter_cls(path, name)

def run_experiment(
    dataset_key: str,
    profile_name: str = "balanced",
    models: Optional[List[str]] = None,
    epochs: Optional[int] = None,
    seed: int = 42,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Run an end-to-end reproducible experiment comparing multiple architectures.
    """
    start_time = time.time()
    start_rss = get_process_memory_mb()

    profile = ResourceProfile.get(profile_name)
    max_tx = profile["max_transactions"]
    max_acc = profile["max_accounts"]
    max_scan = profile.get("max_scan_rows")
    if epochs is None:
        epochs = profile["epochs"]

    if models is None or "all" in models:
        models_to_run = ["logistic_regression", "random_forest", "gradient_boosting", "gcn", "graphsage", "gat"]
    else:
        models_to_run = [m.lower() for m in models]

    logger.info(f"=== Starting AMLNet 2.0 Experiment ===")
    logger.info(f"Dataset: {dataset_key} | Profile: {profile_name} (Max Tx: {max_tx}) | Epochs: {epochs} | Seed: {seed}")

    adapter = resolve_dataset_adapter(dataset_key)

    # 1. Ingestion
    logger.info("Ingesting dataset in bounded chunks...")
    accounts_df, transactions_df, ingest_stats = adapter.load_and_preprocess(
        max_transactions=max_tx,
        max_accounts=max_acc,
        max_scan_rows=max_scan
    )
    logger.info(f"Ingested {len(transactions_df):,} transactions across {len(accounts_df):,} accounts (Coverage: {ingest_stats['ingestion_coverage_pct']}%)")

    # 2. Graph Construction
    logger.info("Building graph features and PyG tensors...")
    pyg_data, raw_feats, scaled_feats, scaler = adapter.build_graph(accounts_df, transactions_df)
    labels = pyg_data.y.numpy()

    # 3. Splits
    train_idx, val_idx, test_idx = adapter.create_splits(
        num_nodes=len(labels),
        labels=labels,
        test_ratio=0.2,
        val_ratio=0.2,
        seed=seed
    )
    logger.info(f"Splits: Train={len(train_idx)}, Val={len(val_idx)}, Test={len(test_idx)} (Minority SAR accounts={int(labels.sum())})")

    # 3b. Leak-free feature scaling (Fit strictly on train_idx, transform val & test)
    tab_scaler = StandardScaler()
    x_train_scaled = tab_scaler.fit_transform(raw_feats[train_idx])
    x_val_scaled = tab_scaler.transform(raw_feats[val_idx])
    x_test_scaled = tab_scaler.transform(raw_feats[test_idx])

    # Update PyG node attributes with leak-free train-fitted scaler
    pyg_data.x = torch.tensor(tab_scaler.transform(raw_feats), dtype=torch.float32)

    # Checkpoint directory
    exp_run_id = f"exp_{dataset_key}_{profile_name}_{int(time.time())}"
    if output_dir is None:
        output_dir = backend_dir / "research" / "checkpoints" / exp_run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    experiment_results = {}

    # 4. Tabular Baselines
    tabular_models = [m for m in models_to_run if m in ["logistic_regression", "random_forest", "gradient_boosting"]]
    if tabular_models:
        logger.info(f"Training non-graph tabular baselines: {tabular_models}...")
        tab_start = time.time()
        tab_results = train_tabular_baselines(
            x_train=x_train_scaled,
            y_train=labels[train_idx],
            x_val=x_val_scaled,
            y_val=labels[val_idx],
            x_test=x_test_scaled,
            y_test=labels[test_idx],
            seed=seed
        )
        for m_name, res in tab_results.items():
            if m_name in tabular_models:
                res_duration = round(time.time() - tab_start, 2)
                res_rss = round(get_process_memory_mb(), 2)
                experiment_results[m_name] = res
                save_experiment(
                    exp_id=f"{exp_run_id}_{m_name}",
                    dataset_name=adapter.name,
                    profile=profile_name,
                    model_name=m_name,
                    metrics=res,
                    hyperparameters={"seed": seed, "max_tx": max_tx, "split": "60/20/20"},
                    training_duration=res_duration,
                    peak_rss_mb=res_rss,
                    epochs=0,
                    is_full_dataset=ingest_stats["is_full_dataset"],
                    ingestion_coverage_pct=ingest_stats["ingestion_coverage_pct"],
                    artifact_rel_path=None
                )
                logger.info(f"Baseline {m_name} -> F1: {res['f1']} | PR-AUC: {res['pr_auc']} | ROC-AUC: {res['roc_auc']} | Recall: {res['recall']}")

    # 5. GNN Models
    gnn_models = [m for m in models_to_run if m in ["gcn", "graphsage", "gat"]]
    for gnn_name in gnn_models:
        logger.info(f"Training GNN: {gnn_name}...")
        g_start = time.time()
        ckpt_dir = output_dir / gnn_name
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        test_metrics, trained_model, history = train_gnn_model(
            model_name=gnn_name,
            pyg_data=pyg_data,
            train_idx=train_idx,
            val_idx=val_idx,
            test_idx=test_idx,
            epochs=epochs,
            lr=0.01,
            seed=seed,
            use_focal_loss=True,
            checkpoint_dir=ckpt_dir
        )
        g_dur = round(time.time() - g_start, 2)
        g_rss = round(get_process_memory_mb(), 2)

        # Save artifact metadata
        ckpt_file = ckpt_dir / f"{gnn_name}_best_checkpoint.pt"
        rel_path = str(ckpt_file.relative_to(backend_dir)) if ckpt_file.exists() else None

        test_metrics["training_history"] = history
        experiment_results[gnn_name] = test_metrics

        save_experiment(
            exp_id=f"{exp_run_id}_{gnn_name}",
            dataset_name=adapter.name,
            profile=profile_name,
            model_name=gnn_name,
            metrics=test_metrics,
            hyperparameters={"seed": seed, "epochs": epochs, "lr": 0.01, "loss": "FocalLoss", "max_tx": max_tx},
            training_duration=g_dur,
            peak_rss_mb=g_rss,
            epochs=test_metrics["epochs_completed"],
            is_full_dataset=ingest_stats["is_full_dataset"],
            ingestion_coverage_pct=ingest_stats["ingestion_coverage_pct"],
            artifact_rel_path=rel_path
        )
        logger.info(f"GNN {gnn_name} -> F1: {test_metrics['f1']} | PR-AUC: {test_metrics['pr_auc']} | ROC-AUC: {test_metrics['roc_auc']} | Recall: {test_metrics['recall']}")

    total_duration = round(time.time() - start_time, 2)
    final_peak_rss = round(get_process_memory_mb(), 2)

    summary = {
        "run_id": exp_run_id,
        "dataset_key": dataset_key,
        "dataset_name": adapter.name,
        "profile": profile_name,
        "total_duration_seconds": total_duration,
        "peak_rss_mb": final_peak_rss,
        "ingestion_stats": ingest_stats,
        "models": {k: {m: v[m] for m in ["accuracy", "precision", "recall", "f1", "pr_auc", "roc_auc", "threshold"]} for k, v in experiment_results.items()},
        "full_results": experiment_results
    }

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"=== Experiment Completed in {total_duration}s (Peak RSS: {final_peak_rss} MB). Summary: {summary_path} ===")
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AMLNet 2.0 Research Experiment Runner")
    parser.add_argument("--dataset", type=str, default="amlsim_1kv_100ke", help="Dataset key (e.g. amlsim_1kv_100ke, amlsim_10kv_1me)")
    parser.add_argument("--profile", type=str, default="balanced", choices=["light", "balanced", "full"], help="Resource profile")
    parser.add_argument("--models", nargs="+", default=["all"], help="Models to train: all, gcn, graphsage, gat, random_forest, logistic_regression, gradient_boosting")
    parser.add_argument("--epochs", type=int, default=None, help="Epoch count")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    res = run_experiment(
        dataset_key=args.dataset,
        profile_name=args.profile,
        models=args.models,
        epochs=args.epochs,
        seed=args.seed
    )
    print(json.dumps(res["models"], indent=2))
