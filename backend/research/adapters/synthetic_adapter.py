"""Synthetic Demo Dataset Adapter."""
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from .base import BaseDatasetAdapter
from app.services.graph import build_graph_features, edge_index

class SyntheticDemoAdapter(BaseDatasetAdapter):
    def __init__(self, source_path: Path, name: str = "AMLNet Synthetic Demo"):
        super().__init__(source_path, name)
        self.accounts_file = self.source_path / "accounts.csv"
        self.transactions_file = self.source_path / "transactions.csv"

    def inspect_metadata(self) -> Dict[str, Any]:
        acc_df = pd.read_csv(self.accounts_file)
        tx_df = pd.read_csv(self.transactions_file)
        return {
            "name": self.name,
            "source_path": str(self.source_path.resolve()),
            "accounts_count": len(acc_df),
            "suspicious_accounts": int(acc_df['label'].sum()),
            "transactions_count": len(tx_df),
            "account_columns": list(acc_df.columns),
            "transaction_columns": list(tx_df.columns),
        }

    def load_and_preprocess(
        self,
        max_transactions: Optional[int] = None,
        max_accounts: Optional[int] = None,
        chunk_size: int = 100_000
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        acc_df = pd.read_csv(self.accounts_file)
        tx_df = pd.read_csv(self.transactions_file)
        stats = {
            "total_transactions_in_file": len(tx_df),
            "total_fraud_transactions_in_file": int((tx_df['scenario'] != 'normal').sum()) if 'scenario' in tx_df.columns else 0,
            "loaded_transactions": len(tx_df),
            "loaded_fraud_transactions": int((tx_df['scenario'] != 'normal').sum()) if 'scenario' in tx_df.columns else 0,
            "loaded_accounts": len(acc_df),
            "loaded_fraud_accounts": int(acc_df['label'].sum()),
            "is_full_dataset": True,
            "ingestion_coverage_pct": 100.0,
        }
        return acc_df, tx_df, stats

    def build_graph(
        self,
        accounts_df: pd.DataFrame,
        transactions_df: pd.DataFrame
    ) -> Tuple[Data, np.ndarray, np.ndarray, Any]:
        _, raw, scaled, scaler = build_graph_features(accounts_df, transactions_df)
        edges = edge_index(accounts_df, transactions_df)
        labels = accounts_df['label'].to_numpy(dtype=int)

        pyg_data = Data(
            x=torch.tensor(scaled, dtype=torch.float32),
            edge_index=torch.tensor(edges, dtype=torch.long),
            y=torch.tensor(labels, dtype=torch.long)
        )
        return pyg_data, raw, scaled, scaler

    def create_splits(
        self,
        num_nodes: int,
        labels: np.ndarray,
        test_ratio: float = 0.2,
        val_ratio: float = 0.2,
        seed: int = 42,
        temporal: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        idx = np.arange(num_nodes)
        train_idx, temp_idx = train_test_split(
            idx,
            test_size=(test_ratio + val_ratio),
            stratify=labels,
            random_state=seed
        )
        val_idx, test_idx = train_test_split(
            temp_idx,
            test_size=test_ratio / (test_ratio + val_ratio),
            stratify=labels[temp_idx],
            random_state=seed
        )
        return train_idx, val_idx, test_idx
