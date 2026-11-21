"""Base abstract interface for dataset adapters."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data

class BaseDatasetAdapter(ABC):
    def __init__(self, source_path: Path, name: str):
        self.source_path = Path(source_path)
        self.name = name

    @abstractmethod
    def inspect_metadata(self) -> Dict[str, Any]:
        """Inspect schema, counts, missing values, and metadata without loading entire data."""
        pass

    @abstractmethod
    def load_and_preprocess(
        self,
        max_transactions: Optional[int] = None,
        max_accounts: Optional[int] = None,
        chunk_size: int = 100_000
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Load accounts and transactions with memory-bounded chunking.
        Returns: (accounts_df, transactions_df, ingestion_stats)
        """
        pass

    @abstractmethod
    def build_graph(
        self,
        accounts_df: pd.DataFrame,
        transactions_df: pd.DataFrame
    ) -> Tuple[Data, np.ndarray, np.ndarray, Any]:
        """
        Construct graph features and PyTorch Geometric Data object.
        Returns: (pyg_data, raw_features, scaled_features, fitted_scaler)
        """
        pass

    @abstractmethod
    def create_splits(
        self,
        num_nodes: int,
        labels: np.ndarray,
        test_ratio: float = 0.2,
        val_ratio: float = 0.2,
        seed: int = 42,
        temporal: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create train, validation, and test indices.
        Ensures zero test leakage.
        """
        pass
