"""Runs inside the Colab kernel; scripts/launch.py sends it with `colab exec`.

Unpacks the uploaded source, restores the run's bucket prefix, copies the declared Drive
inputs, installs the experiment's locked environment and runs its command. Everything
under OUT_DIR is synced to the bucket every minute and once more at the end, so a VM
that disappears loses at most a minute of files.

Standard library only: it runs before any project dependency is installed.
"""

import io
import json
import os
import shutil
import subprocess
import tarfile
import threading
import traceback
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SPEC_FILE = Path("/content/run-spec.json")
SOURCE_ARCHIVE = Path("/content/source.tar.gz")
REPO = Path("/content/repo")
RCLONE_VERSION = "v1.76.0"
SYNC_SECONDS = 60


def sh(cmd, env, cwd=None):
    print(f"[vm] $ {' '.join(str(part) for part in cmd)}", flush=True)
    subprocess.run(cmd, env=env, cwd=cwd, check=True)


def install_rclone(env):
    name = f"rclone-{RCLONE_VERSION}-linux-amd64"
    url = f"https://downloads.rclone.org/{RCLONE_VERSION}/{name}.zip"
    print(f"[vm] installing rclone {RCLONE_VERSION}", flush=True)
    with urllib.request.urlopen(url) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    target = Path("/usr/local/bin/rclone")
    target.write_bytes(archive.read(f"{name}/rclone"))
    target.chmod(0o755)
    sh(["rclone", "version"], env)


def main():
    spec = json.loads(SPEC_FILE.read_text())
    SPEC_FILE.unlink()  # it holds the tokens; nothing else needs the file

    # Colab exports UV_SYSTEM_PYTHON and PYTHONPATH for its own kernel. Inherited by the
    # run they would point uv and the project's Python at Colab's packages.
    env = {k: v for k, v in os.environ.items() if k not in ("UV_SYSTEM_PYTHON", "PYTHONPATH")}
    env.update(spec["secrets"])

    exp_dir = REPO / "experiments" / spec["experiment"]
    out_dir = Path("/content/out") / spec["experiment"] / spec["run"]
    bucket_url = f"hf://buckets/{spec['bucket']}/{spec['experiment']}/{spec['run']}"
    env.update(OUT_DIR=str(out_dir), RUN_NAME=spec["run"], GIT_COMMIT=spec["commit"], PYTHONUNBUFFERED="1")

    shutil.rmtree(REPO, ignore_errors=True)
    with tarfile.open(SOURCE_ARCHIVE) as archive:
        archive.extractall(REPO, filter="data")

    # Restore what an earlier session of the same run left in the bucket, so the command
    # can resume from its own checkpoint. A new run has nothing there and gets an empty
    # directory.
    out_dir.mkdir(parents=True, exist_ok=True)
    sh(["hf", "sync", bucket_url, str(out_dir), "--quiet"], env)

    if spec["drive_inputs"]:
        install_rclone(env)
        for source, target in spec["drive_inputs"].items():
            sh(["rclone", "copy", f"{spec['drive_root']}/{source}", str(exp_dir / target)], env)
            if not any((exp_dir / target).iterdir()):
                raise RuntimeError(
                    f"Drive input {source} is empty; rclone with scope drive.file sees only files it uploaded"
                )

    sh(["uv", "sync", "--locked"], env, cwd=exp_dir)

    def sync_up(check):
        subprocess.run(["hf", "sync", str(out_dir), bucket_url, "--quiet"], env=env, check=check)

    finished = threading.Event()

    def sync_periodically():
        # A failed periodic sync is tolerated: the next one, or the final one below, retries.
        while not finished.wait(SYNC_SECONDS):
            sync_up(check=False)

    syncer = threading.Thread(target=sync_periodically, daemon=True)
    syncer.start()

    gpu = (
        subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True
        ).stdout.strip()
        if shutil.which("nvidia-smi")
        else "none"
    )
    command = ["uv", "run", "--locked", *spec["command"]]
    with open(out_dir / "run.log", "a") as log:

        def emit(line):
            print(line, end="", flush=True)
            log.write(line)
            log.flush()

        emit(f"[vm] {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} commit {spec['commit']} gpu {gpu}\n")
        emit(f"[vm] $ {' '.join(command)}\n")
        process = subprocess.Popen(
            command, cwd=exp_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in process.stdout:
            emit(line)
        code = process.wait()
        emit(f"[vm] command exited with {code}\n")

    finished.set()
    syncer.join()
    sync_up(check=True)
    print(f"[vm] outputs: {bucket_url}", flush=True)
    return code


# launch.py reads this last line to learn the outcome; `colab exec` has no exit code of
# its own for the code it runs.
try:
    exit_code = main()
except Exception:
    traceback.print_exc()
    exit_code = 1
print(f"[vm] exit code: {exit_code}", flush=True)
