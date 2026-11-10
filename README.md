# colab-template

> 中文版见 [README.zh.md](README.zh.md)。The two differ only by language; when they disagree, this file is right.

A template for research projects that compute on Google Colab. Researchers and coding agents ask questions in GitHub
issues and answer them with experiments recorded in pull requests. There is no spec process, no approval labels and
no budget ledger: one person merging a pull request is the only gate.

It is a lighter sibling of [experiment-template](https://github.com/hoshiori-dev/experiment-template). Use that one
when you need formal runs, budgets and protected paths; use this one when a small group and its agents want to move
quickly and still be able to say, months later, why they believe what they believe.

## How research moves

**A question is an issue.** Anyone, agent included, opens a Question when something is worth an experiment. The issue
says what is being asked, where the question came from, and what would count as an answer. The discussion happens
in its comments, so the reasoning stays next to the question. An Epic is an issue that groups related questions and
nothing more. A Task is ordinary engineering work: a shared library, a demo, a report.

**An experiment is a pull request.** The experiment lives in `experiments/<issue>-<slug>/`, and its pull request is
opened as a draft at the first push. The body is the experiment's current summary. Each major step, such as the first
run that works, a result that changes the plan, a dead end, or a lesson that cost an afternoon, becomes one comment
that is never edited afterwards. The pull request is not a log. Retries and per-run status stay out of it.

**Findings are merged with the code.** Before the pull request is ready for review, everything learned goes
somewhere a later reader will find it, including what nobody asked about:

| The finding is about                         | It goes to                              |
| -------------------------------------------- | --------------------------------------- |
| this experiment: answer, evidence, how to rerun | `experiments/<id>/README.md`         |
| the research subject, beyond this experiment | `docs/`                                 |
| how to work in this repository               | `.agents/knowledge/`, or a skill        |

**A person merges.** Merging accepts the answer and closes the question. A negative answer closes it just the same.
After the merge, a person decides whether the weights are published.

## What it is built from

| Need                         | Tool                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| Compute                      | Google Colab through the [Colab CLI](https://github.com/googlecolab/google-colab-cli) |
| Public datasets              | Hugging Face Hub datasets, pinned to a revision                                       |
| Private datasets             | Google Drive through rclone                                                           |
| Checkpoints and session files | A private Hugging Face bucket, one prefix per run                                    |
| Public weights               | Hugging Face Hub model repos                                                          |
| Private weights              | Google Drive                                                                          |
| Dependencies                 | uv: a root workspace for shared libraries, one lock file per experiment               |
| Reports                      | Quarto (HTML, and PDF through Typst)                                                  |
| Commands                     | just                                                                                  |

A project built from the template will often use less than this. Delete what you do not need.

`just run <experiment> -- <command>` is the piece that ties compute and storage together. It creates a Colab VM,
uploads the committed code, installs the experiment's locked dependencies, copies the private data it declares from
Drive, runs the command, keeps the output directory synced to the bucket, and stops the VM. Starting it again with
the same run name resumes from the bucket, which matters because Colab sessions end without warning.

## Setup

1. Create a repository from this template and open it in the dev container. The container has every tool installed.
2. Log in, each in the terminal:
   - `colab sessions` prints a link; approve and paste the code back.
   - `gh auth login`
   - `hf auth login`, for your own use of the Hub from this machine.
3. Set `BUCKET` and `DRIVE_ROOT` at the top of the `justfile`.
4. Create a fine-grained Hugging Face token that can write to that bucket and to the repositories the project uses,
   copy `.env.example` to `.env`, and put the token there. This is the token the Colab VM receives, so keep it
   narrow.
5. Authorize rclone for Google Drive with the narrowest scope:
   `rclone config create gdrive drive scope=drive.file`. With this scope rclone sees only the files it uploaded
   itself, so private datasets go to Drive through `just drive-push`, not through the browser. rclone's built-in
   Google client ID is being retired during 2026, so
   [create your own](https://rclone.org/drive/#making-your-own-client-id) and add `client_id=... client_secret=...`
   to the command.
6. Run `just init-storage` and `just init-labels`.
7. In the repository settings, allow merge commits. Experiment pull requests are merged with a merge commit so that
   the commits an experiment README cites remain on `main`.

Then open your agent and tell it what you want to find out, or open the first Question yourself.

## Everyday commands

| You want to                                   | Run                                                        |
| --------------------------------------------- | ---------------------------------------------------------- |
| Start an experiment for issue 12              | `just new 12 label-smoothing`                              |
| Run a command of it on Colab                  | `just run 012-label-smoothing -- python train.py`          |
| Resume or repeat a run under the same name    | `just run 012-label-smoothing --run NAME -- python train.py` |
| See what a run left in the bucket             | `just bucket-ls 012-label-smoothing`                       |
| Fetch a run's files to `.local/out/`          | `just bucket-pull 012-label-smoothing NAME`                |
| Upload a private dataset                      | `just drive-push ./data datasets/my-set/v1`                |
| Check formatting, lint and lock files         | `just check`                                               |
| Publish a merged experiment's weights         | `just deliver-hub ...` or `just deliver-drive ...`         |

`just` alone lists everything.

## Layout

```text
AGENTS.md  CLAUDE.md          what an agent reads first
.agents/knowledge/            how to work here: the workflow, Colab and storage
.agents/skills/               step-by-step procedures, added when one is worth keeping
justfile  scripts/            commands and the Colab launcher
packages/<name>/              shared libraries (root uv workspace)
experiments/<NNN-slug>/       one experiment: README, code, colab.toml, its own lock, results/
template/experiment/          the starter that `just new` copies
demos/<name>/                 demonstration apps
reports/<name>/               Quarto reports, drawn from experiments/*/results/
docs/                         findings that hold beyond one experiment
```

A directory appears when it has something to hold.

## Agents

`AGENTS.md` is the single entry point and is read natively by Codex, OpenCode and Antigravity, which also load
skills from `.agents/skills/`. Claude Code reads `CLAUDE.md`, which only imports `AGENTS.md`, and finds skills
through links in `.claude/skills/`. The repository ships no permission tables. The one framework setting it carries
is `.claude/settings.json`, which turns off Claude Code's commit and pull request attribution; for the other
frameworks the rule in `AGENTS.md` is all there is.

## Limits

- Colab is not a job scheduler. GPU allocation sometimes fails and idle sessions disappear; the launcher makes a run
  resumable, but it does not queue or retry.
- Nothing checks that a number in a README came from the commit it cites. The workflow asks for it and the reviewer
  can verify it.
- `colab drivemount` needs a person in a browser for every new VM, so the template does not use it.

## License

[Apache License 2.0](LICENSE).
