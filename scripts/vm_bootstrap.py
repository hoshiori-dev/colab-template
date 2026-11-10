"""Runs inside the Colab kernel; scripts/launch.py sends it with `colab exec`.

Unpacks the uploaded source, restores the run's bucket prefix, copies the declared Drive
inputs, installs the experiment's locked environment and runs its command. Everything
under OUT_DIR is synced to the bucket every minute and once more at the end, so a VM
that disappears loses at most a minute of files.

Standard library only: it runs before any project dependency is installed.
"""

import json
import os
import shutil
import subprocess
import tarfile
import threading
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SPEC_FILE = Path("/content/run-spec.json")
SOURCE_ARCHIVE = Path("/content/source.tar.gz")
REPO = Path("/content/repo")
RCLONE_VERSION = "v1.76.0"
SYNC_SECONDS = 60


def relay(cmd, env, cwd=None, log=None):
    """Run a command and return its exit code, printing its output line by line.

    A child process's own stdout never reaches the notebook's output stream, so without
    this relay its messages, errors included, would be invisible to `colab exec`.
    """
    header = f"[vm] $ {' '.join(str(part) for part in cmd)}\n"
    process = subprocess.Popen(cmd, env=env, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in [header, *process.stdout]:
        print(line, end="", flush=True)
        if log:
            log.write(line)
            log.flush()
    return process.wait()


def sh(cmd, env, cwd=None):
    code = relay(cmd, env, cwd)
    if code:
        raise RuntimeError(f"{cmd[0]} exited with {code}")


def install_rclone(env):
    name = f"rclone-{RCLONE_VERSION}-linux-amd64"
    archive = Path(f"/content/{name}.zip")
    # curl, because downloads.rclone.org answers Python's urllib with 403.
    sh(["curl", "-fsSL", "-o", str(archive), f"https://downloads.rclone.org/{RCLONE_VERSION}/{name}.zip"], env)
    target = Path("/usr/local/bin/rclone")
    with zipfile.ZipFile(archive) as bundle:
        target.write_bytes(bundle.read(f"{name}/rclone"))
    target.chmod(0o755)
    archive.unlink()
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

    upload = ["hf", "sync", str(out_dir), bucket_url, "--quiet"]
    finished = threading.Event()

    def sync_periodically():
        # A failed periodic sync is tolerated: the next one, or the final one below, retries.
        while not finished.wait(SYNC_SECONDS):
            subprocess.run(upload, env=env, capture_output=True)

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
        header = f"[vm] {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} commit {spec['commit']} gpu {gpu}\n"
        print(header, end="", flush=True)
        log.write(header)
        code = relay(command, env, cwd=exp_dir, log=log)
        footer = f"[vm] command exited with {code}\n"
        print(footer, end="", flush=True)
        log.write(footer)

    finished.set()
    syncer.join()
    sh(upload, env)
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
