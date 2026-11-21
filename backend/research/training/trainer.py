"""Training, Validation, Checkpointing, and Threshold Calibration Pipeline."""
import io
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import torch
from torch import nn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    precision_recall_curve
)
from ..device import get_device, get_process_memory_mb, ResourceProfile
from .models import AMLGCN, AMLGraphSAGE, AMLGAT
from .losses import FocalLoss
from .batching import PurePyTorchGraphBatcher

logger = logging.getLogger("amlnet.trainer")

def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> Dict[str, Any]:
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    roc_auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0
    pr_auc = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0

    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "confusion_matrix": cm.tolist(),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "classification_report": classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    }

def find_optimal_threshold(y_val: np.ndarray, p_val: np.ndarray) -> float:
    """Tune decision threshold strictly on validation predictions to maximize F1."""
    if len(np.unique(y_val)) <= 1 or np.all(p_val == p_val[0]):
        return 0.5
    precisions, recalls, thresholds = precision_recall_curve(y_val, p_val)
    if len(thresholds) == 0:
        return 0.5
    f1_scores = 2 * precisions[:-1] * recalls[:-1] / (precisions[:-1] + recalls[:-1] + 1e-9)
    best_idx = int(np.nanargmax(f1_scores))
    best_t = float(thresholds[best_idx])
    return max(0.05, min(0.95, best_t))

def train_tabular_baselines(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    seed: int = 42
) -> Dict[str, Dict[str, Any]]:
    """Train and fairly evaluate competitive non-graph tabular baselines."""
    results = {}

    # 1. Logistic Regression
    lr = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=seed)
    lr.fit(x_train, y_train)
    p_val_lr = lr.predict_proba(x_val)[:, 1]
    p_test_lr = lr.predict_proba(x_test)[:, 1]
    t_lr = find_optimal_threshold(y_val, p_val_lr)
    results["logistic_regression"] = {
        **compute_metrics(y_test, p_test_lr, t_lr),
        "model_type": "LogisticRegression (Class-Weighted)",
    }

    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=150, class_weight='balanced_subsample', random_state=seed, n_jobs=1)
    rf.fit(x_train, y_train)
    p_val_rf = rf.predict_proba(x_val)[:, 1]
    p_test_rf = rf.predict_proba(x_test)[:, 1]
    t_rf = find_optimal_threshold(y_val, p_val_rf)
    results["random_forest"] = {
        **compute_metrics(y_test, p_test_rf, t_rf),
        "model_type": "RandomForest (150 trees, balanced subsample)",
    }

    # 3. Histogram-based Gradient Boosting (LightGBM style from sklearn)
    hgb = HistGradientBoostingClassifier(class_weight='balanced', random_state=seed, max_iter=100)
    hgb.fit(x_train, y_train)
    p_val_hgb = hgb.predict_proba(x_val)[:, 1]
    p_test_hgb = hgb.predict_proba(x_test)[:, 1]
    t_hgb = find_optimal_threshold(y_val, p_val_hgb)
    results["gradient_boosting"] = {
        **compute_metrics(y_test, p_test_hgb, t_hgb),
        "model_type": "HistGradientBoosting (Gradient Boosted Trees)",
    }

    return results

def train_gnn_model(
    model_name: str,
    pyg_data: Any,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    epochs: int = 80,
    lr: float = 0.01,
    seed: int = 42,
    use_focal_loss: bool = True,
    checkpoint_dir: Optional[Path] = None,
    resume_checkpoint: Optional[Path] = None
) -> Tuple[Dict[str, Any], Any, List[Dict[str, Any]]]:
    """
    Train a GNN architecture (GCN, GraphSAGE, GAT) with:
    - Early stopping
    - Validation threshold tuning
    - State checkpointing
    - Leakage prevention (test labels are never used during training/tuning)
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    device = get_device(prefer_mps=True)
    logger.info(f"Training {model_name} on device: {device}")

    num_features = pyg_data.x.shape[1]
    if model_name.lower() == "gcn":
        model = AMLGCN(num_features, hidden_dim=48, dropout=0.25).to(device)
    elif model_name.lower() == "graphsage":
        model = AMLGraphSAGE(num_features, hidden_dim=48, dropout=0.20).to(device)
    elif model_name.lower() == "gat":
        model = AMLGAT(num_features, hidden_dim=32, heads=2, dropout=0.20).to(device)
    else:
        raise ValueError(f"Unknown GNN model: {model_name}")

    y_train = pyg_data.y[train_idx].numpy()
    pos_count = max(1, int((y_train == 1).sum()))
    neg_count = max(1, int((y_train == 0).sum()))
    imbalance_ratio = neg_count / pos_count

    if use_focal_loss:
        loss_fn = FocalLoss(alpha=0.75, gamma=2.0)
    else:
        weights = torch.tensor([1.0, min(imbalance_ratio, 20.0)], dtype=torch.float32, device=device)
        loss_fn = nn.CrossEntropyLoss(weight=weights)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=8)

    x = pyg_data.x.to(device)
    edge_index = pyg_data.edge_index.to(device)
    labels = pyg_data.y.to(device)

    tr_tensor = torch.tensor(train_idx, dtype=torch.long, device=device)
    va_tensor = torch.tensor(val_idx, dtype=torch.long, device=device)
    te_tensor = torch.tensor(test_idx, dtype=torch.long, device=device)

    start_epoch = 0
    best_val_f1 = -1.0
    best_state = None
    best_threshold = 0.5
    history = []
    patience = 20
    patience_counter = 0

    if resume_checkpoint and resume_checkpoint.exists():
        logger.info(f"Resuming training from checkpoint: {resume_checkpoint}")
        ckpt = torch.load(resume_checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(ckpt['model_state'])
        optimizer.load_state_dict(ckpt['optimizer_state'])
        start_epoch = ckpt.get('epoch', 0) + 1
        best_val_f1 = ckpt.get('best_val_f1', -1.0)
        best_threshold = ckpt.get('best_threshold', 0.5)

    for epoch in range(start_epoch, epochs):
        model.train()
        optimizer.zero_grad()
        out = model(x, edge_index)
        loss = loss_fn(out[tr_tensor], labels[tr_tensor])
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_out = model(x, edge_index)
            val_loss = loss_fn(val_out[va_tensor], labels[va_tensor]).item()
            val_probs = torch.softmax(val_out[va_tensor], dim=1)[:, 1].cpu().numpy()
            y_val_np = labels[va_tensor].cpu().numpy()

            t_cand = find_optimal_threshold(y_val_np, val_probs)
            val_f1 = f1_score(y_val_np, (val_probs >= t_cand).astype(int), zero_division=0)

        scheduler.step(val_f1)

        history.append({
            "epoch": epoch + 1,
            "train_loss": round(float(loss.item()), 4),
            "val_loss": round(float(val_loss), 4),
            "val_f1": round(float(val_f1), 4),
            "threshold": round(float(t_cand), 4)
        })

        if val_f1 > best_val_f1 + 1e-4:
            best_val_f1 = val_f1
            best_threshold = t_cand
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0

            # Save checkpoint if dir provided
            if checkpoint_dir:
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                ckpt_path = checkpoint_dir / f"{model_name.lower()}_best_checkpoint.pt"
                torch.save({
                    "epoch": epoch,
                    "model_state": best_state,
                    "optimizer_state": optimizer.state_dict(),
                    "best_val_f1": best_val_f1,
                    "best_threshold": best_threshold,
                    "model_name": model_name
                }, ckpt_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch+1} (best val F1: {best_val_f1:.4f})")
                break

    # Load best checkpoint state for test evaluation
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    with torch.no_grad():
        test_out = model(x, edge_index)
        test_probs = torch.softmax(test_out[te_tensor], dim=1)[:, 1].cpu().numpy()
        y_test_np = labels[te_tensor].cpu().numpy()

    test_metrics = compute_metrics(y_test_np, test_probs, best_threshold)
    test_metrics["model_type"] = f"GNN ({model_name})"
    test_metrics["best_val_f1"] = round(float(best_val_f1), 4)
    test_metrics["epochs_completed"] = len(history)

    return test_metrics, model, history
