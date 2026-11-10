"""Build the perturbed test set: every MNIST test digit under one random affine draw.

    uv run python make_shifted.py            # writes data/mnist-shifted/shifted.npz

The file is then uploaded to Drive, where it plays the part of a private dataset:
    just drive-push experiments/003-affine-augmentation/data/mnist-shifted datasets/mnist-shifted/v1
"""

from pathlib import Path

import torch
from digits import load_mnist, save_arrays

from affine import random_affine

SEED = 20261110

images, labels = load_mnist("test")
generator = torch.Generator().manual_seed(SEED)
perturbed = random_affine(torch.from_numpy(images).float().unsqueeze(1), generator)
perturbed = perturbed.squeeze(1).round().clamp(0, 255).to(torch.uint8).numpy()

target = Path(__file__).parent / "data/mnist-shifted/shifted.npz"
target.parent.mkdir(parents=True, exist_ok=True)
save_arrays(target, perturbed, labels)
print(f"wrote {len(perturbed)} digits to {target}")
