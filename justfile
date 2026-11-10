# Command entry points. `just` lists them. Scripts live in scripts/.

set dotenv-load
set positional-arguments

# Storage backends of this project. Edit these two lines when you adopt the template;
# secrets go in .env (see .env.example), never here.

# Hugging Face bucket (namespace/name) holding each run's session files.
export BUCKET := "discovery-loop/colab-template"

# rclone remote:path of the project folder on Google Drive.
export DRIVE_ROOT := "gdrive:colab-template"

# Same ruff version as the ruff-pre-commit rev in .pre-commit-config.yaml.

ruff := "uvx ruff@0.11.9"

_default:
    @just --list --unsorted

# Lint, format check, lock files up to date (what CI runs).
check:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ ruff }} check .
    {{ ruff }} format --check .
    for project in . experiments/*/ demos/*/; do
        if [ -f "$project/pyproject.toml" ]; then uv lock --check --project "$project"; fi
    done

# Format and auto-fix in place.
fmt:
    {{ ruff }} format .
    {{ ruff }} check --fix .

# Create experiments/<NNN-slug>/ from the starter, NNN being the issue number.
new issue slug:
    #!/usr/bin/env bash
    set -euo pipefail
    id="$(printf '%03d' "$1")-$2"
    dir="experiments/$id"
    if [ -e "$dir" ]; then echo "$dir already exists" >&2; exit 1; fi
    mkdir -p experiments
    cp -r template/experiment "$dir"
    sed -i "s/EXPERIMENT_ID/$id/g; s/ISSUE_NUMBER/$1/g" "$dir/README.md" "$dir/pyproject.toml"
    uv lock --project "$dir"
    echo "created $dir"

# Run on a fresh Colab VM: just run <exp-id> [--run NAME] [--keep] -- <command...>
run *args:
    uv run python scripts/launch.py "$@"

# One-time storage setup: create the private bucket and the Drive project folder.
init-storage:
    hf buckets create "$BUCKET" --private --exist-ok
    rclone mkdir "$DRIVE_ROOT"

# Create the issue labels the forms in .github/ISSUE_TEMPLATE/ use.
init-labels:
    gh label create epic --force --color 5319e7 --description "A direction of research that groups questions"
    gh label create question --force --color 1d76db --description "A research question, answered by an experiment PR"
    gh label create task --force --color c5def5 --description "Engineering work: shared library, demo, report, harness"

# List session files in the bucket, optionally under <exp-id>[/<run>].
bucket-ls path="":
    hf buckets list "$BUCKET/{{ path }}" --tree -R -h

# Download a run's session files to .local/out/<exp-id>/<run>/.
bucket-pull exp run:
    mkdir -p ".local/out/$1/$2"
    hf sync "hf://buckets/$BUCKET/$1/$2" ".local/out/$1/$2"

# Delete session files under <exp-id>[/<run>] from the bucket (asks first).
bucket-rm path:
    hf buckets remove "$BUCKET/$1" --recursive

# Upload a local directory to a path under DRIVE_ROOT.
drive-push local remote:
    rclone copy --progress "$1" "$DRIVE_ROOT/$2"

# Download a path under DRIVE_ROOT to a local directory.
drive-pull remote local:
    rclone copy --progress "$DRIVE_ROOT/$1" "$2"

# List a path under DRIVE_ROOT.
drive-ls path="":
    rclone lsf "$DRIVE_ROOT/{{ path }}"

# Person only, after merge: publish a run's deliver/ as a public Hub model repo (namespace/name).
[confirm("Publish this run's deliver/ directory to a PUBLIC Hugging Face model repo?")]
deliver-hub exp run repo: (bucket-pull exp run)
    test -d ".local/out/$1/$2/deliver"
    hf upload "$3" ".local/out/$1/$2/deliver" . --repo-type model --no-private --commit-message "deliver $1/$2"

# Person only, after merge: copy a run's deliver/ to a path under DRIVE_ROOT.
deliver-drive exp run remote: (bucket-pull exp run)
    test -d ".local/out/$1/$2/deliver"
    rclone copy --progress ".local/out/$1/$2/deliver" "$DRIVE_ROOT/$3"
