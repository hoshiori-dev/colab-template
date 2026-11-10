# Colab and storage

Read this before writing or running a script for Colab, reading or writing the bucket, Google Drive or the Hugging
Face Hub, or delivering weights.

## Where things live

| What                                      | Where                                                  | Reached with                                  |
| ----------------------------------------- | ------------------------------------------------------ | --------------------------------------------- |
| Public datasets                           | Hugging Face Hub dataset repos                         | `datasets` / `huggingface_hub` in the script  |
| Private datasets                          | Google Drive, `$DRIVE_ROOT/datasets/<name>/<version>/` | `drive-inputs` in the script, `just drive-*`  |
| Session files: checkpoints, logs, metrics | Hugging Face bucket, `$BUCKET/<exp-id>/<run>/`         | `$OUT_DIR` on the VM, `just bucket-*`         |
| Results the answer rests on               | Git, `experiments/<id>/results/`                       | copied from the bucket by a recipe or by hand |
| Weights for others                        | Hugging Face Hub model repos, private until released   | `just deliver-hub` (a person, after merge)    |
| Private weights                           | Google Drive, `$DRIVE_ROOT/models/...`                 | `just deliver-drive` (a person, after merge)  |

`BUCKET`, `DRIVE_ROOT` and `COLAB_PYTHON` are set at the top of the root `justfile`. The bucket is scratch space:
anything worth keeping leaves it for Git, the Hub or Drive, and the rest may be deleted once the pull request is
merged.

Pin what you read. Load a Hub dataset with an explicit `revision=<commit sha>`. A Drive dataset folder is immutable
once an experiment has read it: a change is a new `<version>` folder. The experiment README's Reproduce section
names both.

## A script for Colab

One execution is one Python file. `template/experiment/main.py` is the smallest working example. Its inline metadata
carries everything the launcher needs:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["torch>=2.6", "datasets>=4"]
#
# [tool.colab]
# accelerator = "T4"                                        # "cpu" (default), T4, L4, G4, H100, A100, v5e1, v6e1
# drive-inputs = { "datasets/name/v1" = "data/name" }       # path under DRIVE_ROOT = path in the working directory
# ///
```

Write the script so the same file runs with `uv run <script.py>` on a laptop and inside the Colab kernel:

- **Parameters come from environment variables** with defaults in the file (`int(os.environ.get("EPOCHS", "5"))`).
  On Colab the script is executed in the kernel, which has no command line of its own; `argparse` would read the
  kernel's arguments.
- **Paths are relative to the working directory**, which is `/content` on the VM and wherever `uv run` was started
  locally. There is no `__file__` in the kernel. Drive inputs appear at the path the metadata names (`data/name`).
- **Everything that should outlive the VM is written under `OUT_DIR`** (`Path(os.environ.get("OUT_DIR",
  ".local/out"))`). On the VM it is the run's bucket prefix, mounted. Files to publish after the merge go in
  `$OUT_DIR/deliver/`.
- **The file imports nothing from the repository.** Only that one file reaches the VM. Code shared with another
  script is copied in.
- **Resume from `OUT_DIR`.** A run launched again under the same name finds its earlier files there. Skip units
  whose result file exists, and continue a unit from its checkpoint. Sessions end without warning.
- `RUN_NAME`, `GIT_COMMIT` and `HF_TOKEN` are set on the VM.

After changing the dependencies or `[tool.colab]`, run `just lock <script.py>` and commit what it writes:
`<script.py>.lock`, and `<stem>.requirements.txt`, the locked versions resolved for Colab's Python and for the
accelerator. A GPU gets PyPI's CUDA build of PyTorch, anything else the CPU build, so changing the accelerator
changes this file.

## Running it

`just run <script.py> [--run NAME] [--keep] [KEY=VALUE ...]`, from the script's directory, does the following
(`scripts/colab.py` locally; `scripts/vm_*.py` in the kernel):

1. Refuses to start when the script's directory has uncommitted changes, or when the requirements file does not
   match the lock.
2. `colab new` with the script's accelerator.
3. `colab install -r <stem>.requirements.txt`, which prints nothing until it is done, then restarts the kernel so
   no replaced package stays imported.
4. Puts the secrets and run variables into the kernel's environment, mounts `$BUCKET/<directory>/<run>/` at
   `/content/out` with `hf-mount`, and copies each Drive input with rclone.
5. `colab exec -f <script.py>`, with every `KEY=VALUE` passed as an environment variable.
6. Unmounts the bucket, which flushes pending writes, and `colab stop` (unless `--keep`).

The exit status of `just run` is 0 when the script finished, 1 when it raised, or the script's own `sys.exit` code.
The run name defaults to `<UTC time>-<commit>`. A launch without dependencies to install takes about 20 seconds
from start to finish; one that installs PyTorch on a T4 took about four minutes, of which the six trainings of
experiment 003 were under one.

`KEY=VALUE` pairs end up in the Colab CLI's local history file; use them for parameters, never for secrets.

## Drive

`rclone` is authorized with the scope `drive.file`: it sees only files that rclone itself uploaded. A dataset
dragged into Drive through the browser is invisible to it, so upload with `just drive-push <local-dir>
datasets/<name>/<version>`. The launcher passes the rclone remote's configuration to the VM; nothing on the VM
mounts Drive. rclone's built-in Google client ID is being retired during 2026 (rclone prints a notice on every
call); the remote should use a client ID of the project's own, see README.md, Setup.

## Delivery

Delivery is done by a person after the pull request is merged: `just deliver-hub <exp-id> <run>
<namespace/repo>` uploads the run's `deliver/` directory as a private model repo, which its owner makes public on the
Hub when it should be (code that loads it needs a token until then), `just deliver-drive <exp-id> <run>
<path>` copies it to Drive. Have the script write `deliver/` itself at the end of the run, and name the run to
deliver in the pull request body. Clean up afterwards with `just bucket-rm <exp-id>`.

## Pitfalls, each one observed

- `colab install` waits only ten seconds for the kernel and has no timeout option, so a PyTorch download ends in
  `TimeoutError: Timeout waiting for reply`. The wait is the environment variable `REQUEST_TIMEOUT` of the CLI's
  kernel client; `colab.py` sets it to an hour for that one command.
- `colab exec` and `colab install` exit 0 even when the code raised in the kernel. The kernel keeps the last
  uncaught exception in `sys.last_value`; `scripts/vm_status.py` and `vm_finish.py` read it, and `just run` turns it
  into an exit status.
- Environment variables set in one `colab exec` are still set in the next one of the same session: the kernel is
  one long-lived process. That is how the secrets reach the script. A kernel restart clears them.
- `colab exec --env KEY=VALUE` and `colab run --env` write the value into `~/.config/colab-cli/history/*.jsonl`.
  Secrets go to the VM in an uploaded file that the setup step deletes.
- A child process started by code under `colab exec` writes to the kernel's own stdout, which the CLI never shows.
  Relay a child's output through `print`, as `vm_setup.py` does, or a failing tool looks like silence.
- `hf-mount` on the VM works only with `--fuse` (there is no `mount.nfs`). In its default mode a mounted bucket
  accepts only whole new files: appending to a file fails with `PermissionError` and seeking back fails with
  `EINVAL`. `--advanced-writes` lifts both, and `torch.save` works with it. Files reach the bucket two to three
  seconds after they are closed.
- `colab drivemount` needs a person to approve in a browser on every new VM. That is why Drive goes through rclone.
- `colab new --gpu <name>` with a name it does not know silently allocates an A100. `colab.py` validates the name
  against the list in `colab new --help`; update `GPUS` and `TPUS` there when that list changes.
- GPU allocation fails intermittently, and an idle session can disappear within minutes. Retry the launch; do not
  build a workflow on a session that waits.
- After a failed launch, run `colab sessions`. Once, `colab new` reported "Allocation refused" while a T4 stayed
  allocated on the server, listed as `[?]` and billed. `colab stop` cannot stop a session it has no local record
  of; `just colab-release <name shown after [?]>` does.
- Requirements are installed over Colab's preinstalled packages, not into an empty environment. Everything the
  script declares is pinned, but a preinstalled package outside its dependency tree keeps Colab's version (pandas
  warned about an older `bottleneck` in experiment 003). Declare what the script imports.
- The kernel's environment has `UV_SYSTEM_PYTHON=true`: `uv pip install` on the VM targets the system Python, the
  one the kernel runs. `colab install` relies on this.
- `downloads.rclone.org` answers Python's `urllib` with 403; `curl` works.
- The kernel runs Python 3.13 (`COLAB_PYTHON`), whatever the script's `requires-python` allows. The setup step stops
  with a message when Colab has moved to another version.

## When a run fails

Read the output from the top: the setup prints each step as `[vm] $ <command>` and every step ends with
`[vm] status: <code>`. A failure before the script is a setup problem (token scope, missing Drive folder, stale
requirements): run `just auth-check` first, and ask the user to run `just auth` when it reports something missing,
since logging in needs a person and a browser. After fixing a pitfall that is not listed above, add it to the list
in the same pull request.
