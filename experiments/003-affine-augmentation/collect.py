"""Gather the metrics.json of every (arm, seed) of a run into the committed result files.

    just bucket-pull 003-affine-augmentation <run>
    uv run python collect.py ../../.local/out/003-affine-augmentation/<run>

Writes results/runs.csv (final accuracies, one row per arm and seed) and
results/history.csv (accuracies after every epoch).
"""

import csv
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
results = Path(__file__).parent / "results"
results.mkdir(exist_ok=True)

metrics = sorted(
    (json.loads(path.read_text()) for path in run_dir.glob("*/metrics.json")), key=lambda m: (m["arm"], m["seed"])
)
if not metrics:
    sys.exit(f"no */metrics.json under {run_dir}")

with open(results / "runs.csv", "w", newline="") as file:
    writer = csv.writer(file, lineterminator="\n")
    writer.writerow(["arm", "seed", "epochs", "clean_accuracy", "shifted_accuracy", "device", "commit"])
    for m in metrics:
        final = m["history"][-1]
        writer.writerow(
            [
                m["arm"],
                m["seed"],
                m["epochs"],
                final["clean_accuracy"],
                final["shifted_accuracy"],
                m["device"],
                m["commit"],
            ]
        )

with open(results / "history.csv", "w", newline="") as file:
    writer = csv.writer(file, lineterminator="\n")
    writer.writerow(["arm", "seed", "epoch", "clean_accuracy", "shifted_accuracy"])
    for m in metrics:
        for row in m["history"]:
            writer.writerow([m["arm"], m["seed"], row["epoch"], row["clean_accuracy"], row["shifted_accuracy"]])

print(f"wrote {len(metrics)} runs to {results}")
