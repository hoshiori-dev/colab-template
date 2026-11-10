"""Runs in the Colab kernel before the script; colab.py sends it with `colab exec`.

Reads the uploaded run spec, puts the secrets and run variables into the kernel's
environment (which the script executed next inherits), mounts the run's bucket prefix as
$OUT_DIR and copies the Drive inputs to the working directory, /content.

Standard library only. Names are kept inside one function so they do not leak into the
namespace the script runs in.
"""

import json
import os
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

HF_MOUNT_VERSION = "v0.13.4"
RCLONE_VERSION = "v1.76.0"


def _setup():
    def sh(*command):
        # A child's own stdout never reaches the notebook stream, so relay it.
        print(f"[vm] $ {' '.join(command)}", flush=True)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="", flush=True)
        if process.wait():
            raise RuntimeError(f"{command[0]} exited with {process.returncode}")

    def download(url, target):
        # curl, because downloads.rclone.org answers Python's urllib with 403.
        sh("curl", "-fsSL", "-o", str(target), url)

    spec_file = Path("/content/run-spec.json")
    spec = json.loads(spec_file.read_text())
    spec_file.unlink()  # it holds the tokens
    os.environ.update(spec["secrets"])
    os.environ.update(spec["environment"])

    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    if running != spec["python"]:
        raise RuntimeError(
            f"Colab runs Python {running}, the requirements were resolved for {spec['python']}: "
            "set COLAB_PYTHON in the justfile and lock the scripts again"
        )

    # --advanced-writes: appends and seeks work, and files reach the bucket a few seconds
    # after they are closed. Without it only whole new files can be written.
    out_dir = Path("/content/out")
    out_dir.mkdir(exist_ok=True)
    for name in ("hf-mount", "hf-mount-fuse"):
        target = Path("/usr/local/bin") / name
        download(
            f"https://github.com/huggingface/hf-mount/releases/download/{HF_MOUNT_VERSION}/{name}-x86_64-linux", target
        )
        target.chmod(0o755)
    sh("hf-mount", "start", "--fuse", "--advanced-writes", "bucket", spec["bucket_path"], str(out_dir))
    os.environ["OUT_DIR"] = str(out_dir)

    if spec["drive_inputs"]:
        name = f"rclone-{RCLONE_VERSION}-linux-amd64"
        archive = Path(f"/content/{name}.zip")
        download(f"https://downloads.rclone.org/{RCLONE_VERSION}/{name}.zip", archive)
        with zipfile.ZipFile(archive) as bundle:
            Path("/usr/local/bin/rclone").write_bytes(bundle.read(f"{name}/rclone"))
        Path("/usr/local/bin/rclone").chmod(0o755)
        archive.unlink()
        for source, target in spec["drive_inputs"].items():
            sh("rclone", "copy", f"{spec['drive_root']}/{source}", f"/content/{target}")
            if not any(Path(f"/content/{target}").iterdir()):
                raise RuntimeError(
                    f"Drive input {source} is empty; rclone with scope drive.file sees only files it uploaded"
                )

    gpu = "none"
    if os.path.exists("/usr/bin/nvidia-smi"):
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True
        ).stdout.strip()
    print(f"[vm] commit {spec['environment']['GIT_COMMIT']} gpu {gpu} out {spec['bucket_path']}", flush=True)


try:
    _setup()
    print("[vm] status: 0", flush=True)
except Exception:
    traceback.print_exc()
    print("[vm] status: 1", flush=True)
del _setup
