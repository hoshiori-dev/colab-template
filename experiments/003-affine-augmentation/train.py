"""Train the small CNN with and without affine augmentation, several seeds per arm.

    uv run python train.py [--arms none affine] [--seeds 0 1 2] [--epochs 5] [--limit N]

Each (arm, seed) writes to $OUT_DIR/<arm>-seed<seed>/: checkpoint.pt after every epoch,
then metrics.json and model.safetensors. A finished pair is skipped and an unfinished one
continues from its checkpoint, so launching the same run name again resumes the sweep.
"""

import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from digits import SmallCNN, accuracy, load_arrays, load_mnist, save_weights, to_input

from affine import random_affine

HERE = Path(__file__).parent
BATCH_SIZE = 128
LEARNING_RATE = 1e-3


def train_one(arm: str, seed: int, epochs: int, limit: int | None, out_dir: Path, device: str) -> None:
    metrics_file = out_dir / "metrics.json"
    if metrics_file.exists():
        print(f"{out_dir.name}: already finished, skipping", flush=True)
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    train_images, train_labels = load_mnist("train")
    clean_images, clean_labels = load_mnist("test")
    shifted_images, shifted_labels = load_arrays(HERE / "data/mnist-shifted/shifted.npz")
    # Unnormalized float pixels on the device: augmentation runs there, normalization after it.
    pixels = torch.from_numpy(train_images[:limit]).float().unsqueeze(1).to(device)
    targets = torch.from_numpy(train_labels[:limit]).to(device)

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
    for epoch in range(len(history) + 1, epochs + 1):
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
                "clean_accuracy": accuracy(model, clean_images, clean_labels, device),
                "shifted_accuracy": accuracy(model, shifted_images, shifted_labels, device),
            }
        )
        print(f"{out_dir.name}: {history[-1]}", flush=True)
        torch.save(
            {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "history": history}, checkpoint_file
        )

    save_weights(model, out_dir / "model.safetensors")
    metrics_file.write_text(
        json.dumps(
            {
                "arm": arm,
                "seed": seed,
                "epochs": epochs,
                "train_examples": len(pixels),
                "device": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
                "seconds_this_session": round(time.time() - started, 1),
                "commit": os.environ.get("GIT_COMMIT", "unknown"),
                "history": history,
            },
            indent=2,
        )
    )
    checkpoint_file.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", nargs="+", default=["none", "affine"], choices=["none", "affine"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--limit", type=int, help="train on the first N examples only (for debugging)")
    args = parser.parse_args()

    out_dir = Path(os.environ.get("OUT_DIR", HERE / ".local/out"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    for arm in args.arms:
        for seed in args.seeds:
            train_one(arm, seed, args.epochs, args.limit, out_dir / f"{arm}-seed{seed}", device)


if __name__ == "__main__":
    main()
