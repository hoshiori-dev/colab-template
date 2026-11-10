"""Lock and run single-file scripts on Colab. Called by `just lock` and `just run`.

    colab.py lock <script.py>
    colab.py run <script.py> [--run NAME] [--keep] [KEY=VALUE ...]

A script declares its dependencies in PEP 723 inline metadata. A script meant for Colab
adds a `[tool.colab]` table there:

    # [tool.colab]
    # accelerator = "T4"            # "cpu" (default), a GPU or a TPU that `colab new` accepts
    # drive-inputs = { "datasets/name/v1" = "data/name" }   # DRIVE_ROOT path = path on the VM

`lock` writes <script>.lock and, for a Colab script, <stem>.requirements.txt: the locked
versions resolved for Colab's Python and for the script's accelerator, which is what
`colab install -r` installs on the VM.

`run` creates a VM, installs that file, mounts the bucket prefix <directory>/<run>/ as
$OUT_DIR, copies the Drive inputs, executes the script in the VM's kernel and stops the
VM. Reusing a run name resumes it: $OUT_DIR still holds its files. KEY=VALUE pairs become
environment variables of the script. Reads BUCKET, DRIVE_ROOT, COLAB_PYTHON and HF_TOKEN
from the environment (the justfile and .env set them).

Standard library only.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
GPUS = {"T4", "L4", "G4", "H100", "A100"}
TPUS = {"v5e1", "v6e1"}
# The block format PEP 723 specifies.
METADATA = re.compile(r"(?m)^# /// script$\s(?P<content>(^#(| .*)$\s)+)^# ///$")
STATUS = "[vm] status: "


def fail(message):
    sys.exit(f"colab.py: {message}")


def required_env(name, hint):
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set; {hint}")
    return value


def output_of(*command, cwd=None):
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def colab_table(script):
    """The script's [tool.colab] table, or None when the script is not meant for Colab."""
    match = METADATA.search(script.read_text())
    if not match:
        fail(f"{script} has no PEP 723 metadata block (# /// script ... # ///)")
    lines = match.group("content").splitlines()
    metadata = tomllib.loads("\n".join(line[2:] if line.startswith("# ") else line[1:] for line in lines))
    return metadata.get("tool", {}).get("colab")


def accelerator_flags(accelerator):
    # `colab new` silently gives an A100 for a GPU name it does not know, so reject typos here.
    if accelerator == "cpu":
        return []
    if accelerator in GPUS:
        return ["--gpu", accelerator]
    if accelerator in TPUS:
        return ["--tpu", accelerator]
    fail(f"accelerator {accelerator!r} is not one of cpu, {sorted(GPUS)}, {sorted(TPUS)}")


def requirements_file(script):
    return script.with_name(f"{script.stem}.requirements.txt")


def colab_requirements(script, accelerator):
    """The script's locked dependencies as Colab installs them: its Python, Linux, the accelerator's PyTorch build."""
    python = required_env("COLAB_PYTHON", "set it at the top of the justfile")
    accelerator_flags(accelerator)
    with tempfile.TemporaryDirectory() as tmp:
        pins = Path(tmp) / "pins.txt"
        output_of(
            "uv",
            "export",
            "--quiet",
            "--script",
            str(script),
            "--format",
            "requirements.txt",
            "--no-hashes",
            "-o",
            str(pins),
        )
        command = ["uv", "pip", "compile", "--quiet", str(script), "--constraints", str(pins)]
        command += ["--python-version", python, "--python-platform", "x86_64-manylinux_2_28"]
        command += ["--no-header", "--no-annotate", "--emit-index-url"]
        if accelerator not in GPUS:
            # PyPI's Linux build of PyTorch carries CUDA; a VM without a GPU gets the CPU build.
            command += ["--torch-backend", "cpu"]
        body = output_of(*command)
    header = (
        f"# Written by `just lock {script.name}` for Colab: Python {python}, accelerator {accelerator}. Do not edit.\n"
    )
    return header + body + "\n"


def lock(script):
    subprocess.run(["uv", "lock", "--script", str(script)], check=True)
    colab = colab_table(script)
    if colab is None:
        return
    target = requirements_file(script)
    target.write_text(colab_requirements(script, colab.get("accelerator", "cpu")))
    print(f"wrote {target.name}")


def drive_secrets(drive_root):
    """The rclone remote of DRIVE_ROOT as RCLONE_CONFIG_* variables, so the VM needs no config file."""
    remote = drive_root.split(":", 1)[0]
    dump = json.loads(output_of("rclone", "config", "dump"))
    if remote not in dump:
        fail(f"rclone has no remote named {remote!r}; run `just auth`")
    return {f"RCLONE_CONFIG_{remote.upper()}_{key.upper()}": value for key, value in dump[remote].items()}


def run(script, run_name, keep, variables):
    colab = colab_table(script)
    if colab is None:
        fail(f"{script.name} has no [tool.colab] table in its inline metadata")
    accelerator = colab.get("accelerator", "cpu")
    new_flags = accelerator_flags(accelerator)
    drive_inputs = colab.get("drive-inputs", {})
    for variable in variables:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", variable):
            fail(f"{variable!r} is not KEY=VALUE")

    directory = script.parent
    root = Path(output_of("git", "rev-parse", "--show-toplevel", cwd=directory))
    dirty = output_of("git", "status", "--porcelain", "--", ".", cwd=directory)
    if dirty:
        fail(f"commit first, so the run can be traced to a commit:\n{dirty}")
    subprocess.run(["uv", "lock", "--script", str(script), "--check"], check=True)
    requirements = requirements_file(script)
    if not requirements.is_file() or requirements.read_text() != colab_requirements(script, accelerator):
        fail(f"{requirements.name} does not match the lock; run `just lock {script.name}` and commit")
    commit = output_of("git", "rev-parse", "HEAD", cwd=directory)
    run_name = run_name or f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{commit[:7]}"

    secrets = {"HF_TOKEN": required_env("HF_TOKEN", "copy .env.example to .env and fill it in")}
    drive_root = ""
    if drive_inputs:
        drive_root = required_env("DRIVE_ROOT", "set it at the top of the justfile")
        secrets.update(drive_secrets(drive_root))
    spec = {
        "bucket_path": f"{required_env('BUCKET', 'set it at the top of the justfile')}/{directory.name}/{run_name}",
        "python": required_env("COLAB_PYTHON", "set it at the top of the justfile"),
        "drive_root": drive_root,
        "drive_inputs": drive_inputs,
        "secrets": secrets,
        "environment": {"RUN_NAME": run_name, "GIT_COMMIT": commit},
    }

    def colab_cli(*args, **kwargs):
        if subprocess.run(["colab", *args], **kwargs).returncode:
            fail(f"`colab {args[0]}` failed; `colab sessions` shows what is still allocated")

    def step(code_file):
        """Execute a helper in the kernel and return the status it reports on its last line.

        `colab exec` and `colab install` exit 0 whatever happened in the kernel, so the
        helpers print the outcome and this reads it back.
        """
        process = subprocess.Popen(
            ["colab", "exec", "-s", run_name, "--timeout", "3600", "-f", str(code_file)],
            stdout=subprocess.PIPE,
            text=True,
        )
        status = None
        for line in process.stdout:
            print(line, end="", flush=True)
            if line.startswith(STATUS):
                status = line[len(STATUS) :].strip()
        process.wait()
        if status is None:
            fail(f"{code_file.name} did not report a status; the session was lost or the step was cut off")
        return status

    print(f"colab.py: run {run_name} of {script.relative_to(root)} at {commit[:7]} on {accelerator}", flush=True)
    colab_cli("new", "-s", run_name, *new_flags)
    try:
        if any(line.strip() and not line.startswith(("#", "-")) for line in requirements.read_text().splitlines()):
            # `colab install` waits REQUEST_TIMEOUT seconds (default 10) for the kernel and prints
            # nothing while uv works; a PyTorch download needs minutes.
            print(f"colab.py: installing {requirements.name} (silent until done)", flush=True)
            colab_cli("install", "-s", run_name, "-r", str(requirements), env={**os.environ, "REQUEST_TIMEOUT": "3600"})
            if step(HERE / "vm_status.py") != "0":
                fail(f"`colab install -r {requirements.name}` failed on the VM")
            # Packages the kernel had already imported may just have been replaced.
            colab_cli("restart-kernel", "-s", run_name)
        with tempfile.TemporaryDirectory() as tmp:
            spec_file = Path(tmp) / "run-spec.json"
            spec_file.touch(mode=0o600)
            spec_file.write_text(json.dumps(spec))
            # Secrets travel in an uploaded file: `colab exec --env` writes its values into
            # the CLI's local history log.
            colab_cli("upload", "-s", run_name, str(spec_file), "/content/run-spec.json")
        if step(HERE / "vm_setup.py") != "0":
            fail("setting up the VM failed; see the output above")
        environment = [flag for variable in variables for flag in ("--env", variable)]
        colab_cli("exec", "-s", run_name, "--timeout", "86400", *environment, "-f", str(script))
        status = step(HERE / "vm_finish.py")
    finally:
        if keep:
            print(f"colab.py: session {run_name} kept; stop it with `colab stop -s {run_name}`", flush=True)
        else:
            colab_cli("stop", "-s", run_name)
    print(f"colab.py: outputs in hf://buckets/{spec['bucket_path']}", flush=True)
    sys.exit(int(status))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["lock", "run"])
    parser.add_argument("script", type=Path)
    parser.add_argument("--run", help="run: the run name; reuse one to resume it (default: <UTC time>-<commit>)")
    parser.add_argument("--keep", action="store_true", help="run: leave the VM running afterwards")
    parser.add_argument("variables", nargs="*", metavar="KEY=VALUE", help="run: environment variables for the script")
    # Intermixed, so that KEY=VALUE pairs may follow the options.
    args = parser.parse_intermixed_args()
    script = args.script.resolve()
    if not script.is_file():
        fail(f"{args.script} not found")
    if args.command == "lock":
        lock(script)
    else:
        run(script, args.run, args.keep, args.variables)


if __name__ == "__main__":
    main()
