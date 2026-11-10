"""Runs in the Colab kernel after the script. Flushes $OUT_DIR to the bucket and reports the script's outcome."""

import os
import subprocess
import sys


def _finish():
    error = getattr(sys, "last_value", None)
    if error is None:
        status = 0
    elif isinstance(error, SystemExit):
        status = error.code if isinstance(error.code, int) else int(error.code is not None)
    else:
        status = 1
    # Unmounting waits for the writes still queued for the bucket.
    stop = subprocess.run(["hf-mount", "stop", os.environ["OUT_DIR"]], capture_output=True, text=True)
    print(stop.stdout + stop.stderr, end="", flush=True)
    return status or stop.returncode


print(f"[vm] status: {_finish()}", flush=True)
del _finish
