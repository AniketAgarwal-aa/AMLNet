"""Memory-efficient Subgraph and Mini-batch Sampling without C++ dependencies."""
import math
from typing import Generator, List, Tuple
import torch
import numpy as np
from torch_geometric.utils import subgraph

class PurePyTorchGraphBatcher:
    """
    Partitions or samples subgraphs using pure PyTorch operations, guaranteeing compatibility
    on macOS Apple Silicon without requiring torch-sparse or pyg-lib C++ extensions.
    """
    def __init__(self, edge_index: torch.Tensor, num_nodes: int, batch_size: int = 512, seed: int = 42):
        self.edge_index = edge_index
        self.num_nodes = num_nodes
        self.batch_size = batch_size
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def iterate_node_batches(self, node_indices: np.ndarray, shuffle: bool = True) -> Generator[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], None, None]:
        """
        Yields (batch_nodes, batch_edge_index, batch_labels_mask).
        Extracts the induced subgraph for the batch.
        """
        indices = node_indices.copy()
        if shuffle:
            self.rng.shuffle(indices)

        n_batches = math.ceil(len(indices) / self.batch_size)
        for i in range(n_batches):
            batch_nodes_np = indices[i * self.batch_size : (i + 1) * self.batch_size]
            batch_nodes = torch.tensor(batch_nodes_np, dtype=torch.long)

            # Extract induced subgraph on these nodes (with relabeling)
            sub_edges, _ = subgraph(batch_nodes, self.edge_index, relabel_nodes=True, num_nodes=self.num_nodes)
            yield batch_nodes, sub_edges
