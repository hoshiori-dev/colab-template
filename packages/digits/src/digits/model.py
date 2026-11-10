from pathlib import Path

import torch
from safetensors.torch import load_file, save_file
from torch import nn


class SmallCNN(nn.Module):
    """Two convolution blocks and a hidden layer; about 105,000 parameters."""

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 7 * 7, 64),
            nn.ReLU(),
            nn.Linear(64, 10),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def save_weights(model: SmallCNN, path: str | Path) -> None:
    save_file(model.state_dict(), str(path))


def load_weights(path: str | Path) -> SmallCNN:
    """A model in eval mode with the weights `save_weights` wrote."""
    model = SmallCNN()
    model.load_state_dict(load_file(str(path)))
    return model.eval()
