# Colab and storage

Read this before running anything on Colab, reading or writing the bucket, Google Drive or the Hugging Face Hub, or
delivering weights.

## Where things live

| What                                   | Where                                                       | Reached with                               |
| -------------------------------------- | ----------------------------------------------------------- | ------------------------------------------ |
| Public datasets                        | Hugging Face Hub dataset repos                              | `datasets` / `huggingface_hub` in code     |
| Private datasets                       | Google Drive, `$DRIVE_ROOT/datasets/<name>/<version>/`      | `drive_inputs` in `colab.toml`, `just drive-*` |
| Session files: checkpoints, logs, metrics | Hugging Face bucket, `$BUCKET/<exp-id>/<run>/`           | `$OUT_DIR` on the VM, `just bucket-*`      |
| Results the answer rests on            | Git, `experiments/<id>/results/`                            | copied by hand from the bucket             |
| Public weights                         | Hugging Face Hub model repos                                | `just deliver-hub` (a person, after merge) |
| Private weights                        | Google Drive, `$DRIVE_ROOT/models/...`                      | `just deliver-drive` (a person, after merge) |

`BUCKET` and `DRIVE_ROOT` are set at the top of the `justfile`. The bucket is scratch space: anything worth keeping
leaves it for Git, the Hub or Drive, and the rest may be deleted once the pull request is merged.

Pin what you read. Load a Hub dataset with an explicit `revision=<commit sha>`. A Drive dataset folder is immutable
once an experiment has read it: a change is a new `<version>` folder. The experiment README's Reproduce section
names both.

## Running an experiment

`just run <exp-id> [--run NAME] [--keep] -- <command...>` does the following (`scripts/launch.py` locally,
`scripts/vm_bootstrap.py` on the VM):

1. Refuses to start when `packages/` or `experiments/<exp-id>/` has uncommitted changes: the VM runs `HEAD`.
2. Creates a VM with the accelerator named in `experiments/<exp-id>/colab.toml`.
3. Uploads `git archive HEAD` of `packages/` and `experiments/<exp-id>/`, plus the secrets as a file.
4. Downloads `$BUCKET/<exp-id>/<run>/` into `$OUT_DIR`, copies each `drive_inputs` entry from Drive into the
   experiment directory, and runs `uv sync --locked` there.
5. Runs `uv run --locked <command...>` in the experiment directory, with the output also written to
   `$OUT_DIR/run.log`.
6. Uploads `$OUT_DIR` to the bucket every 60 seconds and once at the end, then stops the VM (unless `--keep`).

The exit status of `just run` is the command's. The run name defaults to `<UTC time>-<commit>`.

What the experiment's code can rely on:

- `OUT_DIR`: write every file that should outlive the VM here, and only here. Files to publish after the merge go
  in `$OUT_DIR/deliver/` (weights, config, model card).
- `RUN_NAME`, `GIT_COMMIT`, `HF_TOKEN` are set; the working directory is the experiment directory.
- Resuming: launch again with the same `--run NAME`. `$OUT_DIR` then starts with the files of the earlier session,
  so a training script that looks for its own checkpoint in `$OUT_DIR` at startup continues from it. Write
  checkpoints for anything longer than a few minutes; sessions end without warning.

Take the output directory from `OUT_DIR` with a local default (for example `.local/out`), so the same command runs
on the VM and on a laptop.

## Drive

`rclone` is authorized with the scope `drive.file`: it sees only files that rclone itself uploaded. A dataset
dragged into Drive through the browser is invisible to it, so upload with `just drive-push <local-dir>
datasets/<name>/<version>`. The launcher passes the rclone remote's configuration to the VM; nothing on the VM
mounts Drive. rclone's built-in Google client ID is being retired during 2026 (rclone prints a notice on every
call); the remote should use a client ID of the project's own, see README.md, Setup.

## Delivery

Delivery publishes and is done by a person after the pull request is merged: `just deliver-hub <exp-id> <run>
<namespace/repo>` uploads the run's `deliver/` directory as a public model repo, `just deliver-drive <exp-id> <run>
<path>` copies it to Drive. During the experiment, prepare `deliver/` (including a `README.md` model card for the
Hub) and name the run to deliver in the pull request body. Clean up afterwards with `just bucket-rm <exp-id>`.

## Pitfalls, each one observed

- `colab drivemount` needs a person to approve in a browser on every new VM, and it cannot be combined with a
  one-shot run. That is why Drive goes through rclone.
- `colab exec` exits 0 even when the code it ran raised. `just run` gets the real status from the last line the
  bootstrap prints.
- `colab exec --env KEY=VALUE` and `colab run --env` write the value into `~/.config/colab-cli/history/*.jsonl`.
  Pass secrets only through `just run`.
- `colab new --gpu <name>` with a name it does not know silently allocates an A100. `launch.py` validates the name
  against the list in `colab new --help`; update `GPUS` and `TPUS` there when that list changes.
- GPU allocation fails intermittently, and an idle session can disappear within minutes. Retry the launch; do not
  build a workflow on a session that waits.
- The kernel's environment has `UV_SYSTEM_PYTHON=true` and a `PYTHONPATH`. With them `uv pip install` targets the
  system Python and the project's Python sees Colab's packages. The bootstrap removes both for the run; when you
  run uv by hand in `colab exec`, use `uv sync` / `uv run` in a project and unset them.
- On the VM `hf-mount` works only with `--fuse` (there is no `mount.nfs`). The launcher does not mount at all: it
  syncs a plain directory, which survives any write pattern.
- A fresh `uv sync` of PyTorch with CUDA wheels takes about 90 seconds and 5.5 GB on the VM. With VM creation and
  the Drive copy, a launch spends about two minutes before the command starts; put several short trainings in one
  launch.
- A child process started by code under `colab exec` writes to the kernel's own stdout, which the CLI never shows.
  The bootstrap relays every child's output through `print` (`relay` in `vm_bootstrap.py`); do the same in any code
  you send with `colab exec`, or a failing tool looks like silence.
- `downloads.rclone.org` answers Python's `urllib` with 403; `curl` works.

## When a run fails

Read the output from the top: the bootstrap prints each step as `[vm] $ <command>`. A failure before the experiment's
command is a setup problem (token scope, missing Drive folder, stale lock); `just bucket-pull <exp-id> <run>` fetches
`run.log` for a failure inside it. After fixing a pitfall that is not listed above, add it to the list in the same
pull request.
