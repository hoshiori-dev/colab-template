# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "datasets>=4",
#     "numpy>=2",
#     "pillow>=10",
#     "safetensors>=0.4",
#     "torch>=2.6",
# ]
#
# [tool.colab]
# accelerator = "T4"
# drive-inputs = { "datasets/mnist-shifted/v1" = "data/mnist-shifted" }
# ///
"""Train the small CNN with and without affine augmentation, several seeds per arm.

    just run train.py                                  # the whole sweep on Colab
    ARMS=none SEEDS=0 EPOCHS=1 LIMIT=5000 uv run train.py   # a quick local check

Each (arm, seed) writes to $OUT_DIR/<arm>-seed<seed>/: checkpoint.pt after every epoch,
then metrics.json and model.safetensors. A finished pair is skipped and an unfinished one
continues from its checkpoint, so launching the same run name again resumes the sweep.
At the end the weights of DELIVER are copied to $OUT_DIR/deliver/ for publication.
"""

import json
import math
import os
import shutil
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset
from safetensors.torch import save_file
from torch import nn

# Parameters, from the environment so the same file runs under `uv run` and in the Colab kernel.
ARMS = os.environ.get("ARMS", "none affine").split()
SEEDS = [int(seed) for seed in os.environ.get("SEEDS", "0 1 2").split()]
EPOCHS = int(os.environ.get("EPOCHS", "5"))
LIMIT = int(os.environ["LIMIT"]) if "LIMIT" in os.environ else None  # train on the first N digits only
OUT_DIR = Path(os.environ.get("OUT_DIR", ".local/out"))

BATCH_SIZE = 128
LEARNING_RATE = 1e-3
DELIVER = "affine-seed0"

MNIST_REVISION = "77f3279092a1c1579b2250db8eafed0ad422088c"
SHIFTED_SET = Path("data/mnist-shifted/shifted.npz")
# Mean and standard deviation of the MNIST training pixels scaled to [0, 1].
MEAN, STD = 0.1307, 0.3081

# The perturbation family of this experiment. make_shifted.py holds an identical copy of
# these three ranges and of random_affine; the two must stay the same, or the augmentation
# no longer matches the test set.
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


class SmallCNN(nn.Module):
    """Two convolution blocks and a hidden layer; 105,866 parameters."""

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


def to_input(pixels: torch.Tensor) -> torch.Tensor:
    """Pixels in [0, 255] of shape (N, 28, 28) as the normalized tensor (N, 1, 28, 28) the model takes."""
    return pixels.float().div(255.0).sub(MEAN).div(STD).unsqueeze(1)


def load_mnist(split: str) -> tuple[np.ndarray, np.ndarray]:
    """A split of MNIST from the Hub as uint8 images (N, 28, 28) and int64 labels (N,)."""
    dataset = load_dataset("ylecun/mnist", split=split, revision=MNIST_REVISION)
    images = np.stack([np.asarray(image, dtype=np.uint8) for image in dataset["image"]])
    return images, np.asarray(dataset["label"], dtype=np.int64)


@torch.no_grad()
def accuracy(model: SmallCNN, images: np.ndarray, labels: np.ndarray, device: str) -> float:
    model.eval()
    correct = 0
    for start in range(0, len(images), 1000):
        batch = to_input(torch.from_numpy(images[start : start + 1000])).to(device)
        predicted = model(batch).argmax(dim=1).cpu().numpy()
        correct += int((predicted == labels[start : start + 1000]).sum())
    return correct / len(images)


def train_one(arm: str, seed: int, data: dict, out_dir: Path, device: str) -> None:
    metrics_file = out_dir / "metrics.json"
    if metrics_file.exists():
        print(f"{out_dir.name}: already finished, skipping", flush=True)
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    # Unnormalized float pixels on the device: augmentation runs there, normalization after it.
    pixels = torch.from_numpy(data["train_images"][:LIMIT]).float().unsqueeze(1).to(device)
    targets = torch.from_numpy(data["train_labels"][:LIMIT]).to(device)

    torch.manual_seed(seed)
    model = SmallCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    history = []
    checkpoint_file = out_dir / "checkpoint.pt"
    if checkpoint_file.exists():
        checkpoint = torch.load(checkpoint_file, map_location=device)
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        history = checkpoint["history"]
        print(f"{out_dir.name}: resuming after epoch {len(history)}", flush=True)

    started = time.time()
    for epoch in range(len(history) + 1, EPOCHS + 1):
        # One generator per epoch, so a resumed sweep draws what an uninterrupted one would.
        generator = torch.Generator().manual_seed(seed * 1000 + epoch)
        order = torch.randperm(len(pixels), generator=generator).to(device)
        model.train()
        for start in range(0, len(order), BATCH_SIZE):
            index = order[start : start + BATCH_SIZE]
            batch = pixels[index]
            if arm == "affine":
                batch = random_affine(batch, generator)
            loss = F.cross_entropy(model(to_input(batch.squeeze(1))), targets[index])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        history.append(
            {
                "epoch": epoch,
                "clean_accuracy": accuracy(model, data["clean_images"], data["clean_labels"], device),
                "shifted_accuracy": accuracy(model, data["shifted_images"], data["shifted_labels"], device),
            }
        )
        print(f"{out_dir.name}: {history[-1]}", flush=True)
        torch.save(
            {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "history": history}, checkpoint_file
        )

    save_file(model.state_dict(), str(out_dir / "model.safetensors"))
    metrics_file.write_text(
        json.dumps(
            {
                "arm": arm,
                "seed": seed,
                "epochs": EPOCHS,
                "train_examples": len(pixels),
                "device": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
                "torch": torch.__version__,
                "seconds_this_session": round(time.time() - started, 1),
                "commit": os.environ.get("GIT_COMMIT", "unknown"),
                "history": history,
            },
            indent=2,
        )
    )
    checkpoint_file.unlink()


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    data = {}
    data["train_images"], data["train_labels"] = load_mnist("train")
    data["clean_images"], data["clean_labels"] = load_mnist("test")
    with np.load(SHIFTED_SET) as shifted:
        data["shifted_images"], data["shifted_labels"] = shifted["images"], shifted["labels"]

    for arm in ARMS:
        for seed in SEEDS:
            train_one(arm, seed, data, OUT_DIR / f"{arm}-seed{seed}", device)

    weights = OUT_DIR / DELIVER / "model.safetensors"
    if weights.exists():
        (OUT_DIR / "deliver").mkdir(exist_ok=True)
        shutil.copy(weights, OUT_DIR / "deliver/model.safetensors")
        print(f"deliver/ holds the weights of {DELIVER}", flush=True)


if __name__ == "__main__":
    main()
