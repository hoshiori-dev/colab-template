"""Random rotation, translation and scale of digit images, one draw per image."""

import math

import torch
import torch.nn.functional as F

# The perturbation family of this experiment: the same ranges build the perturbed test
# set (make_shifted.py) and augment training (train.py --augment affine).
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
