"""Prepare $OUT_DIR/deliver/ for publication: the weights of one trained model and its model card.

    just run 003-affine-augmentation --run <run> -- python export.py [--model affine-seed0]

Launched under the run name of a finished sweep, so $OUT_DIR already holds its models.
"""

import argparse
import os
import shutil
from pathlib import Path

HERE = Path(__file__).parent

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="affine-seed0", help="<arm>-seed<seed> directory of the sweep")
args = parser.parse_args()

out_dir = Path(os.environ.get("OUT_DIR", HERE / ".local/out"))
deliver = out_dir / "deliver"
deliver.mkdir(exist_ok=True)
shutil.copy(out_dir / args.model / "model.safetensors", deliver / "model.safetensors")
shutil.copy(HERE / "model_card.md", deliver / "README.md")
print(f"deliver/ holds {sorted(path.name for path in deliver.iterdir())}")
