import numpy as np
import torch

from digits.data import to_input
from digits.model import SmallCNN


@torch.no_grad()
def accuracy(
    model: SmallCNN, images: np.ndarray, labels: np.ndarray, device: str = "cpu", batch_size: int = 1000
) -> float:
    """Fraction of `images` (uint8, N x 28 x 28) the model classifies as `labels`."""
    model = model.to(device).eval()
    correct = 0
    for start in range(0, len(images), batch_size):
        batch = to_input(images[start : start + batch_size]).to(device)
        predicted = model(batch).argmax(dim=1).cpu().numpy()
        correct += int((predicted == labels[start : start + batch_size]).sum())
    return correct / len(images)
