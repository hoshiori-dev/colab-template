# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "datasets>=4",
#     "numpy>=2",
#     "pillow>=10",
#     "torch>=2.6",
# ]
# ///
"""Build the perturbed test set: every MNIST test digit under one random affine draw.

    uv run make_shifted.py        # writes data/mnist-shifted/shifted.npz

`just shifted` runs this and uploads the file to Drive, where it plays the part of a
private dataset.
"""

import math
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset

MNIST_REVISION = "77f3279092a1c1579b2250db8eafed0ad422088c"
SEED = 20261110

# The perturbation family of this experiment. train.py holds an identical copy of these
# three ranges and of random_affine; the two must stay the same, or the augmentation no
# longer matches the test set.
MAX_DEGREES = 20.0
MAX_SHIFT_PIXELS = 3.0
SCALE_RANGE = (0.85, 1.15)


def random_affine(images: torch.Tensor, generator: torch.Generator) -> torch.Tensor:
    """Perturb float images (N, 1, 28, 28) with background value 0; `generator` lives on the CPU."""
    count = images.shape[0]

    def uniform(low: float, high: float) -> torch.Tensor:
        return torch.empty(count).uniform_(low, high, generator=generator)

    angle = uniform(-MAX_DEGREES, MAX_DEGREES) * math.pi / 180
    scale = uniform(*SCALE_RANGE)
    # affine_grid works in normalized coordinates, where the image spans [-1, 1].
    shift_x = uniform(-MAX_SHIFT_PIXELS, MAX_SHIFT_PIXELS) * 2 / images.shape[-1]
    shift_y = uniform(-MAX_SHIFT_PIXELS, MAX_SHIFT_PIXELS) * 2 / images.shape[-2]
    cos, sin = torch.cos(angle) / scale, torch.sin(angle) / scale
    matrices = torch.stack(
        [torch.stack([cos, -sin, shift_x], dim=1), torch.stack([sin, cos, shift_y], dim=1)], dim=1
    ).to(images.device)
    grid = F.affine_grid(matrices, list(images.shape), align_corners=False)
    return F.grid_sample(images, grid, mode="bilinear", padding_mode="zeros", align_corners=False)


test = load_dataset("ylecun/mnist", split="test", revision=MNIST_REVISION)
images = np.stack([np.asarray(image, dtype=np.uint8) for image in test["image"]])
labels = np.asarray(test["label"], dtype=np.int64)

generator = torch.Generator().manual_seed(SEED)
perturbed = random_affine(torch.from_numpy(images).float().unsqueeze(1), generator)
perturbed = perturbed.squeeze(1).round().clamp(0, 255).to(torch.uint8).numpy()

target = Path("data/mnist-shifted/shifted.npz")
target.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(target, images=perturbed, labels=labels)
print(f"wrote {len(perturbed)} digits to {target}")
