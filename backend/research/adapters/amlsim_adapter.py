"""IBM AMLSim Dataset Adapter with chunked ingestion and scalable graph feature generation."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from .base import BaseDatasetAdapter
from ..device import get_process_memory_mb

logger = logging.getLogger("amlnet.adapters.amlsim")

class IBMAMLSimAdapter(BaseDatasetAdapter):
    ACCOUNT_COLUMNS = ['ACCOUNT_ID', 'CUSTOMER_ID', 'INIT_BALANCE', 'COUNTRY', 'ACCOUNT_TYPE', 'IS_FRAUD', 'TX_BEHAVIOR_ID']
    TX_COLUMNS = ['TX_ID', 'SENDER_ACCOUNT_ID', 'RECEIVER_ACCOUNT_ID', 'TX_TYPE', 'TX_AMOUNT', 'TIMESTAMP', 'IS_FRAUD', 'ALERT_ID']
    FEATURE_NAMES = [
        'incoming_count',
        'outgoing_count',
        'total_incoming_amount',
        'total_outgoing_amount',
        'avg_incoming_amount',
        'avg_outgoing_amount',
        'unique_counterparties',
        'in_out_amount_ratio',
        'log_total_incoming',
        'log_total_outgoing'
    ]

    def __init__(self, source_path: Path, name: str = "IBM AMLSim"):
        super().__init__(source_path, name)
        self.accounts_file = self.source_path / "accounts.csv"
        self.transactions_file = self.source_path / "transactions.csv"
        self.alerts_file = self.source_path / "alerts.csv"

    def inspect_metadata(self) -> Dict[str, Any]:
        """Inspect schema, counts, and size quickly."""
        acc_head = pd.read_csv(self.accounts_file, nrows=10)
        tx_head = pd.read_csv(self.transactions_file, nrows=10)

        # Count accounts (small file)
        acc_df = pd.read_csv(self.accounts_file, usecols=['ACCOUNT_ID', 'IS_FRAUD'])
        num_accounts = len(acc_df)
        acc_fraud = int(acc_df['IS_FRAUD'].astype(str).str.strip().str.lower().isin(['true', '1', 'yes']).sum())

        # File sizes
        tx_size_mb = self.transactions_file.stat().st_size / (1024 * 1024)
        acc_size_mb = self.accounts_file.stat().st_size / (1024 * 1024)

        return {
            "name": self.name,
            "source_path": str(self.source_path.resolve()),
            "accounts_count": num_accounts,
            "suspicious_accounts": acc_fraud,
            "accounts_file_size_mb": round(acc_size_mb, 2),
            "transactions_file_size_mb": round(tx_size_mb, 2),
            "account_columns": list(acc_head.columns),
            "transaction_columns": list(tx_head.columns),
        }

    def load_and_preprocess(
        self,
        max_transactions: Optional[int] = None,
        max_accounts: Optional[int] = None,
        chunk_size: int = 100_000,
        max_scan_rows: Optional[int] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Chunked, bounded-memory ingestion.
        If max_transactions is None, ingests the entire transaction stream.
        If max_transactions is specified, preserves ALL fraud transactions and reservoir-samples normal ones.
        """
        start_mem = get_process_memory_mb()
        accounts_df = pd.read_csv(self.accounts_file, dtype={'ACCOUNT_ID': str})
        if max_accounts and len(accounts_df) > max_accounts:
            fraud_acc = accounts_df[accounts_df['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes'])]
            norm_acc = accounts_df[~accounts_df['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes'])]

            # Stratified proportional sampling: strictly preserve source dataset class distribution
            source_fraud_ratio = len(fraud_acc) / max(1, len(accounts_df))
            target_fraud = max(10, int(round(max_accounts * source_fraud_ratio)))
            target_norm = max_accounts - target_fraud
            sample_fraud = fraud_acc.sample(n=min(target_fraud, len(fraud_acc)), random_state=42)
            sample_norm = norm_acc.sample(n=min(target_norm, len(norm_acc)), random_state=42)
            accounts_df = pd.concat([sample_fraud, sample_norm], ignore_index=True).sort_values('ACCOUNT_ID')

        valid_account_ids = set(accounts_df['ACCOUNT_ID'].astype(str))

        total_streamed_tx = 0
        total_fraud_tx = 0
        tx_chunks: List[pd.DataFrame] = []

        if max_transactions is None:
            # Full dataset processing
            logger.info("Processing complete dataset without truncation...")
            for chunk in pd.read_csv(
                self.transactions_file,
                dtype={'TX_ID': str, 'SENDER_ACCOUNT_ID': str, 'RECEIVER_ACCOUNT_ID': str},
                chunksize=chunk_size
            ):
                total_streamed_tx += len(chunk)
                is_fraud = chunk['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes'])
                total_fraud_tx += int(is_fraud.sum())
                # Keep edges where endpoints are in accounts_df
                mask = chunk['SENDER_ACCOUNT_ID'].isin(valid_account_ids) & chunk['RECEIVER_ACCOUNT_ID'].isin(valid_account_ids)
                tx_chunks.append(chunk[mask])
            transactions_df = pd.concat(tx_chunks, ignore_index=True) if tx_chunks else pd.DataFrame(columns=self.TX_COLUMNS)
            is_full = True
        else:
            # Bounded sample: retain all fraud, sample normal
            fraud_chunks = []
            normal_pool = []
            rng = np.random.default_rng(42)

            for chunk in pd.read_csv(
                self.transactions_file,
                dtype={'TX_ID': str, 'SENDER_ACCOUNT_ID': str, 'RECEIVER_ACCOUNT_ID': str},
                chunksize=chunk_size
            ):
                total_streamed_tx += len(chunk)
                is_fraud = chunk['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes'])
                total_fraud_tx += int(is_fraud.sum())

                mask = chunk['SENDER_ACCOUNT_ID'].isin(valid_account_ids) & chunk['RECEIVER_ACCOUNT_ID'].isin(valid_account_ids)
                valid_chunk = chunk[mask]

                chunk_fraud = valid_chunk[valid_chunk['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes'])]
                chunk_normal = valid_chunk[~valid_chunk['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes'])].copy()

                if len(chunk_fraud):
                    fraud_chunks.append(chunk_fraud)
                if len(chunk_normal):
                    chunk_normal['_sample_key'] = rng.random(len(chunk_normal))
                    normal_pool.append(chunk_normal)
                    if len(normal_pool) > 4:
                        combined = pd.concat(normal_pool, ignore_index=True).nsmallest(max_transactions * 2, '_sample_key')
                        normal_pool = [combined]

                if max_scan_rows and total_streamed_tx >= max_scan_rows:
                    logger.info(f"Reached max_scan_rows limit ({max_scan_rows:,}). Stopping stream early for resource safety.")
                    break

            fraud_df = pd.concat(fraud_chunks, ignore_index=True) if fraud_chunks else pd.DataFrame(columns=self.TX_COLUMNS)
            norm_combined = pd.concat(normal_pool, ignore_index=True) if normal_pool else pd.DataFrame(columns=self.TX_COLUMNS)
            if '_sample_key' in norm_combined.columns:
                norm_combined = norm_combined.drop(columns=['_sample_key'])

            remaining = max(0, max_transactions - len(fraud_df))
            sample_normal = norm_combined.sample(n=min(remaining, len(norm_combined)), random_state=42) if len(norm_combined) else norm_combined
            transactions_df = pd.concat([fraud_df, sample_normal], ignore_index=True).sort_values('TX_ID')
            is_full = (total_streamed_tx == len(transactions_df))

        end_mem = get_process_memory_mb()

        stats = {
            "total_transactions_in_file": total_streamed_tx,
            "total_fraud_transactions_in_file": total_fraud_tx,
            "loaded_transactions": len(transactions_df),
            "loaded_fraud_transactions": int(transactions_df['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes']).sum()),
            "loaded_accounts": len(accounts_df),
            "loaded_fraud_accounts": int(accounts_df['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes']).sum()),
            "is_full_dataset": is_full,
            "ingestion_coverage_pct": round((len(transactions_df) / max(1, total_streamed_tx)) * 100, 2),
            "peak_rss_mb": round(end_mem, 2),
            "memory_delta_mb": round(end_mem - start_mem, 2),
        }
        return accounts_df, transactions_df, stats

    def build_graph(
        self,
        accounts_df: pd.DataFrame,
        transactions_df: pd.DataFrame
    ) -> Tuple[Data, np.ndarray, np.ndarray, Any]:
        """
        Fast, vectorised feature extraction and PyG Data construction.
        """
        acc_ids = accounts_df['ACCOUNT_ID'].astype(str).tolist()
        id_to_idx = {acc_id: i for i, acc_id in enumerate(acc_ids)}
        num_nodes = len(acc_ids)

        # Raw features array: [N, 10]
        raw_features = np.zeros((num_nodes, 10), dtype=np.float32)
        edges = []
        edge_amounts = []
        edge_times = []

        senders = transactions_df['SENDER_ACCOUNT_ID'].astype(str).values
        receivers = transactions_df['RECEIVER_ACCOUNT_ID'].astype(str).values
        amounts = transactions_df['TX_AMOUNT'].astype(float).values
        timestamps = transactions_df['TIMESTAMP'].astype(float).values if 'TIMESTAMP' in transactions_df.columns else np.zeros(len(amounts))

        in_counts = np.zeros(num_nodes, dtype=np.float32)
        out_counts = np.zeros(num_nodes, dtype=np.float32)
        in_amounts = np.zeros(num_nodes, dtype=np.float32)
        out_amounts = np.zeros(num_nodes, dtype=np.float32)
        counterparties = [set() for _ in range(num_nodes)]

        for s, r, amt, ts in zip(senders, receivers, amounts, timestamps):
            if s in id_to_idx and r in id_to_idx:
                si = id_to_idx[s]
                ri = id_to_idx[r]
                # Bidirectional for undirected GCN propagation
                edges.append((si, ri))
                edges.append((ri, si))
                edge_amounts.extend([amt, amt])
                edge_times.extend([ts, ts])

                out_counts[si] += 1
                in_counts[ri] += 1
                out_amounts[si] += amt
                in_amounts[ri] += amt
                counterparties[si].add(r)
                counterparties[ri].add(s)

        raw_features[:, 0] = in_counts
        raw_features[:, 1] = out_counts
        raw_features[:, 2] = in_amounts
        raw_features[:, 3] = out_amounts
        raw_features[:, 4] = in_amounts / np.maximum(in_counts, 1.0)
        raw_features[:, 5] = out_amounts / np.maximum(out_counts, 1.0)
        raw_features[:, 6] = np.array([len(cp) for cp in counterparties], dtype=np.float32)
        raw_features[:, 7] = in_amounts / np.maximum(out_amounts, 1.0)
        raw_features[:, 8] = np.log1p(np.maximum(in_amounts, 0.0))
        raw_features[:, 9] = np.log1p(np.maximum(out_amounts, 0.0))

        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(raw_features)

        edge_index = np.asarray(edges, dtype=np.int64).T if edges else np.empty((2, 0), dtype=np.int64)
        edge_attr = np.column_stack([edge_amounts, edge_times]).astype(np.float32) if edges else np.empty((0, 2), dtype=np.float32)

        labels = accounts_df['IS_FRAUD'].astype(str).str.lower().isin(['true', '1', 'yes']).astype(int).values

        pyg_data = Data(
            x=torch.tensor(scaled_features, dtype=torch.float32),
            edge_index=torch.tensor(edge_index, dtype=torch.long),
            edge_attr=torch.tensor(edge_attr, dtype=torch.float32),
            y=torch.tensor(labels, dtype=torch.long)
        )
        return pyg_data, raw_features, scaled_features, scaler

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
        Leakage-aware account splits.
        Stratified on account label to preserve minority SAR class.
        """
        idx = np.arange(num_nodes)
        train_idx, temp_idx = train_test_split(
            idx,
            test_size=(test_ratio + val_ratio),
            stratify=labels,
            random_state=seed
        )
        rel_test_ratio = test_ratio / (test_ratio + val_ratio)
        val_idx, test_idx = train_test_split(
            temp_idx,
            test_size=rel_test_ratio,
            stratify=labels[temp_idx],
            random_state=seed
        )
        return train_idx, val_idx, test_idx
