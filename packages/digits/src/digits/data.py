"""Digit images as uint8 arrays of shape (N, 28, 28) with int64 labels of shape (N,)."""

from pathlib import Path

import numpy as np
import torch
from datasets import Dataset, load_dataset

MNIST_REPO = "ylecun/mnist"
# Commit of the dataset repository on the Hub. Every experiment reads this revision
# unless its README says otherwise.
MNIST_REVISION = "77f3279092a1c1579b2250db8eafed0ad422088c"

# Mean and standard deviation of the MNIST training pixels scaled to [0, 1].
MEAN, STD = 0.1307, 0.3081


def dataset_to_arrays(dataset: Dataset) -> tuple[np.ndarray, np.ndarray]:
    images = np.stack([np.asarray(image, dtype=np.uint8) for image in dataset["image"]])
    labels = np.asarray(dataset["label"], dtype=np.int64)
    return images, labels


def load_mnist(split: str, revision: str = MNIST_REVISION) -> tuple[np.ndarray, np.ndarray]:
    """The "train" (60,000 digits) or "test" (10,000 digits) split of MNIST from the Hub."""
    return dataset_to_arrays(load_dataset(MNIST_REPO, split=split, revision=revision))


def save_arrays(path: str | Path, images: np.ndarray, labels: np.ndarray) -> None:
    np.savez_compressed(path, images=images, labels=labels)


def load_arrays(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """A digit set written by `save_arrays`."""
    with np.load(path) as data:
        return data["images"], data["labels"]


def to_input(images: np.ndarray | torch.Tensor) -> torch.Tensor:
    """uint8 images (N, 28, 28) as the normalized float tensor (N, 1, 28, 28) the model takes."""
    tensor = torch.as_tensor(images).float().div(255.0)
    return tensor.sub(MEAN).div(STD).unsqueeze(1)
