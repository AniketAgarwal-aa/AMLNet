"""Tests for machine learning pipeline, checkpointing, and leak-free split integrity."""
import sys
import tempfile
from pathlib import Path
import pytest
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parents[1]))
from research.training.models import AMLGCN, AMLGraphSAGE, AMLGAT
from research.training.losses import FocalLoss
from research.training.batching import PurePyTorchGraphBatcher
from research.training.trainer import compute_metrics, find_optimal_threshold, train_gnn_model
from research.adapters.amlsim_adapter import IBMAMLSimAdapter
from torch_geometric.data import Data

def test_leak_free_split_integrity():
    workspace = Path(__file__).resolve().parents[2]
    path = workspace / "100vertices-10Kedges"
    adapter = IBMAMLSimAdapter(path)

    dummy_labels = np.array([0]*80 + [1]*20)
    tr, va, te = adapter.create_splits(len(dummy_labels), dummy_labels, test_ratio=0.2, val_ratio=0.2, seed=42)

    # 1. Zero overlap between sets
    assert len(set(tr).intersection(set(va))) == 0
    assert len(set(tr).intersection(set(te))) == 0
    assert len(set(va).intersection(set(te))) == 0

    # 2. Complete union
    assert len(set(tr).union(set(va)).union(set(te))) == 100

    # 3. Stratification preserved in minority class
    assert dummy_labels[tr].sum() > 0
    assert dummy_labels[va].sum() > 0
    assert dummy_labels[te].sum() > 0

def test_pure_pytorch_batcher():
    edges = torch.tensor([[0, 1, 2, 3, 0], [1, 2, 3, 0, 2]], dtype=torch.long)
    batcher = PurePyTorchGraphBatcher(edge_index=edges, num_nodes=4, batch_size=2, seed=42)
    batches = list(batcher.iterate_node_batches(np.array([0, 1, 2, 3]), shuffle=False))
    assert len(batches) == 2
    for nodes, sub_edges in batches:
        assert len(nodes) == 2
        assert sub_edges.dim() == 2

def test_checkpoint_saving_and_resumption():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_dir = Path(tmp_dir)

        # Create synthetic graph
        x = torch.randn(20, 10)
        edges = torch.tensor([[0, 1, 2, 3, 4], [1, 2, 3, 4, 0]], dtype=torch.long)
        y = torch.tensor([0]*16 + [1]*4, dtype=torch.long)
        pyg_data = Data(x=x, edge_index=edges, y=y)

        tr = np.arange(12)
        va = np.arange(12, 16)
        te = np.arange(16, 20)

        # Train for 5 epochs and save
        m1, model1, hist1 = train_gnn_model(
            model_name="gcn",
            pyg_data=pyg_data,
            train_idx=tr,
            val_idx=va,
            test_idx=te,
            epochs=5,
            checkpoint_dir=ckpt_dir
        )

        saved_file = ckpt_dir / "gcn_best_checkpoint.pt"
        assert saved_file.exists()

        # Resume training for 5 more epochs
        m2, model2, hist2 = train_gnn_model(
            model_name="gcn",
            pyg_data=pyg_data,
            train_idx=tr,
            val_idx=va,
            test_idx=te,
            epochs=10,
            checkpoint_dir=ckpt_dir,
            resume_checkpoint=saved_file
        )
        assert m2 is not None
        assert 'f1' in m2

def test_focal_loss_extreme_imbalance():
    loss_fn = FocalLoss(alpha=0.75, gamma=2.0)
    logits = torch.tensor([[2.0, -2.0], [-2.0, 2.0]])
    targets = torch.tensor([0, 1], dtype=torch.long)
    loss = loss_fn(logits, targets)
    assert loss.item() >= 0.0
