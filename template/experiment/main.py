# /// script
# requires-python = ">=3.12"
# dependencies = []
#
# [tool.colab]
# accelerator = "cpu"
# ///
"""One execution of the experiment, in one file.

    uv run main.py            # here, for debugging
    just run main.py          # on a fresh Colab VM

Everything the script needs is in this file: dependencies above, parameters below. On
Colab it runs inside the VM's kernel with /content as the working directory, so it reads
its parameters from the environment (there is no command line) and has no __file__.
"""

import json
import os
from pathlib import Path

# Parameters: `STEPS=10 uv run main.py`, or `just run main.py STEPS=10`.
STEPS = int(os.environ.get("STEPS", "3"))

# Files written here outlive the VM: on Colab this directory is the run's bucket prefix.
OUT_DIR = Path(os.environ.get("OUT_DIR", ".local/out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Resume: a run launched again under the same name finds its earlier files in OUT_DIR.
state_file = OUT_DIR / "state.json"
done = json.loads(state_file.read_text())["done"] if state_file.exists() else 0
for step in range(done + 1, STEPS + 1):
    print(f"step {step} of {STEPS}", flush=True)
    state_file.write_text(json.dumps({"done": step}))
print(f"finished at commit {os.environ.get('GIT_COMMIT', 'unknown')}")
