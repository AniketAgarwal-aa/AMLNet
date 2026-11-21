"""GNN and Machine Learning Model Architectures for AML Detection."""
import torch
from torch import nn
from torch_geometric.nn import GCNConv, SAGEConv, GATConv

class AMLGCN(nn.Module):
    """
    Improved Graph Convolutional Network:
    - Symmetrized message passing with residual skip connection
    - LayerNorm for gradient stabilization
    - Configurable dropout to prevent oversmoothing
    """
    def __init__(self, in_features: int, hidden_dim: int = 48, out_classes: int = 2, dropout: float = 0.25):
        super().__init__()
        self.conv1 = GCNConv(in_features, hidden_dim)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim // 2)
        self.norm2 = nn.LayerNorm(hidden_dim // 2)
        self.out = nn.Linear(hidden_dim // 2, out_classes)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.GELU()

    def forward(self, x, edge_index):
        h = self.conv1(x, edge_index)
        h = self.norm1(h)
        h = self.act(h)
        h = self.dropout(h)

        h = self.conv2(h, edge_index)
        h = self.norm2(h)
        h = self.act(h)
        h = self.dropout(h)

        return self.out(h)

class AMLGraphSAGE(nn.Module):
    """
    GraphSAGE for Inductive Representation Learning on Large Transaction Graphs.
    Uses mean neighbor aggregation, layer normalization, and residual projection.
    """
    def __init__(self, in_features: int, hidden_dim: int = 48, out_classes: int = 2, dropout: float = 0.20):
        super().__init__()
        self.conv1 = SAGEConv(in_features, hidden_dim, aggr='mean')
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim // 2, aggr='mean')
        self.norm2 = nn.LayerNorm(hidden_dim // 2)
        self.out = nn.Linear(hidden_dim // 2, out_classes)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.ReLU()

    def forward(self, x, edge_index):
        h = self.conv1(x, edge_index)
        h = self.norm1(h)
        h = self.act(h)
        h = self.dropout(h)

        h = self.conv2(h, edge_index)
        h = self.norm2(h)
        h = self.act(h)
        h = self.dropout(h)

        return self.out(h)

class AMLGAT(nn.Module):
    """
    Graph Attention Network (GAT):
    Learns dynamic attention weights over connected counterparties, giving higher weight
    to suspicious transaction partners.
    """
    def __init__(self, in_features: int, hidden_dim: int = 32, heads: int = 2, out_classes: int = 2, dropout: float = 0.20):
        super().__init__()
        self.conv1 = GATConv(in_features, hidden_dim, heads=heads, dropout=dropout)
        self.norm1 = nn.LayerNorm(hidden_dim * heads)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, concat=False, dropout=dropout)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.out = nn.Linear(hidden_dim, out_classes)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.ELU()

    def forward(self, x, edge_index):
        h = self.conv1(x, edge_index)
        h = self.norm1(h)
        h = self.act(h)
        h = self.dropout(h)

        h = self.conv2(h, edge_index)
        h = self.norm2(h)
        h = self.act(h)
        h = self.dropout(h)

        return self.out(h)
