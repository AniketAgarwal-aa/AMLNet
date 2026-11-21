"""Loss functions for extreme class imbalance in financial crime detection."""
import torch
import torch.nn as nn
import torch.nn.functional as F

class FocalLoss(nn.Module):
    """
    Focal Loss for addressing class imbalance:
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    Down-weights easy well-classified normal accounts and focuses gradients on rare SAR accounts.
    """
    def __init__(self, alpha: float = 0.75, gamma: float = 2.0, reduction: str = 'mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        pt = torch.exp(-ce_loss)

        # alpha weight for class 1 vs class 0
        alpha_t = torch.where(targets == 1, self.alpha, 1.0 - self.alpha)
        focal_loss = alpha_t * ((1.0 - pt) ** self.gamma) * ce_loss

        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        return focal_loss
