"""Run one experiment command on a fresh Colab VM and release the VM afterwards.

    just run <exp-id> [--run NAME] [--keep] -- <command...>

The VM gets the committed state of packages/ and experiments/<exp-id>/ (HEAD, never the
working tree), the secrets it needs, and scripts/vm_bootstrap.py, which does the work
on the VM. Outputs land in the bucket under <exp-id>/<run>/; reusing a run name resumes
it. Reads BUCKET, DRIVE_ROOT and HF_TOKEN from the environment (the justfile and .env
set them).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GPUS = {"T4", "L4", "G4", "H100", "A100"}
TPUS = {"v5e1", "v6e1"}
EXIT_MARKER = "[vm] exit code: "


def fail(message):
    sys.exit(f"launch: {message}")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def required_env(name, hint):
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set; {hint}")
    return value


def accelerator_flags(accelerator):
    # `colab new` silently gives an A100 for a GPU name it does not know, so reject typos here.
    if accelerator == "cpu":
        return []
    if accelerator in GPUS:
        return ["--gpu", accelerator]
    if accelerator in TPUS:
        return ["--tpu", accelerator]
    fail(f"colab.toml: accelerator {accelerator!r} is not one of cpu, {sorted(GPUS)}, {sorted(TPUS)}")


def drive_secrets(drive_root):
    """The rclone remote of DRIVE_ROOT as RCLONE_CONFIG_* variables, so the VM needs no config file."""
    remote = drive_root.split(":", 1)[0]
    dump = json.loads(subprocess.run(["rclone", "config", "dump"], check=True, capture_output=True, text=True).stdout)
    if remote not in dump:
        fail(f"rclone has no remote named {remote!r}; create it as README.md, Setup, describes")
    return {f"RCLONE_CONFIG_{remote.upper()}_{key.upper()}": value for key, value in dump[remote].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("experiment", help="directory name under experiments/")
    parser.add_argument("--run", help="run name; reuse one to resume it (default: <UTC time>-<commit>)")
    parser.add_argument(
        "--keep", action="store_true", help="leave the VM running afterwards (stop it with `colab stop`)"
    )
    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="command run with `uv run` in the experiment directory"
    )
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        fail("no command given; usage: just run <exp-id> -- <command...>")

    exp_dir = ROOT / "experiments" / args.experiment
    if not (exp_dir / "colab.toml").is_file():
        fail(f"{exp_dir.relative_to(ROOT)}/colab.toml not found")
    config = tomllib.loads((exp_dir / "colab.toml").read_text())
    new_flags = accelerator_flags(config.get("accelerator", "cpu"))
    drive_inputs = config.get("drive_inputs", {})

    sources = [path for path in ("packages", f"experiments/{args.experiment}") if (ROOT / path).is_dir()]
    dirty = git("status", "--porcelain", "--", *sources)
    if dirty:
        fail(f"the VM runs HEAD, and these changes are not committed:\n{dirty}")
    commit = git("rev-parse", "HEAD")
    run = args.run or f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{commit[:7]}"

    secrets = {"HF_TOKEN": required_env("HF_TOKEN", "copy .env.example to .env and fill it in")}
    drive_root = ""
    if drive_inputs:
        drive_root = required_env("DRIVE_ROOT", "set it at the top of the justfile")
        secrets.update(drive_secrets(drive_root))
    spec = {
        "experiment": args.experiment,
        "run": run,
        "commit": commit,
        "command": command,
        "bucket": required_env("BUCKET", "set it at the top of the justfile"),
        "drive_root": drive_root,
        "drive_inputs": drive_inputs,
        "secrets": secrets,
    }

    def colab(*colab_args):
        subprocess.run(["colab", *colab_args], check=True)

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "source.tar.gz"
        git("archive", "--format=tar.gz", "-o", str(archive), commit, "--", *sources)
        spec_file = Path(tmp) / "run-spec.json"
        spec_file.touch(mode=0o600)
        spec_file.write_text(json.dumps(spec))

        print(f"launch: run {run} of {args.experiment} at {commit[:7]}", flush=True)
        colab("new", "-s", run, *new_flags)
        try:
            # Secrets travel in an uploaded file: `colab exec --env` would write them into
            # the CLI's local history log.
            colab("upload", "-s", run, str(archive), "/content/source.tar.gz")
            colab("upload", "-s", run, str(spec_file), "/content/run-spec.json")
            process = subprocess.Popen(
                ["colab", "exec", "-s", run, "--timeout", "86400", "-f", str(ROOT / "scripts/vm_bootstrap.py")],
                stdout=subprocess.PIPE,
                text=True,
            )
            exit_code = None
            for line in process.stdout:
                print(line, end="", flush=True)
                if line.startswith(EXIT_MARKER):
                    exit_code = int(line[len(EXIT_MARKER) :])
            process.wait()
        finally:
            if args.keep:
                print(f"launch: session {run} kept; stop it with `colab stop -s {run}`", flush=True)
            else:
                colab("stop", "-s", run)

    if exit_code is None:
        fail("the VM never reported an exit code; the session was lost or the bootstrap was cut off")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
