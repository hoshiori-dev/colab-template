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
nothing more. A Task is ordinary engineering work: a demo, a report, the project setup.

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
| Dependencies                 | uv, declared inside each script as PEP 723 inline metadata and locked per script      |
| Reports                      | Quarto (HTML, and PDF through Typst)                                                  |
| Commands                     | just                                                                                  |

A project built from the template will often use less than this. Delete what you do not need.

**Every experiment and every demo stands alone.** Nothing in `experiments/` or `demos/` imports from another
directory, and there is no shared package. When two scripts need the same function, it is copied. The duplication is
the price of being able to read, run, move or delete one experiment without touching another.

**One execution is one file.** A script carries its dependencies in its own header, so `uv run train.py` works on any
machine with uv. A script meant for Colab adds two lines there for the accelerator and the private data it needs:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["torch>=2.6", "datasets>=4"]
#
# [tool.colab]
# accelerator = "T4"
# drive-inputs = { "datasets/my-set/v1" = "data/my-set" }
# ///
```

`just lock train.py` locks those dependencies and exports them as a requirements file for Colab's Python and for that
accelerator, with the CUDA build of PyTorch for a GPU and the CPU build otherwise. `just run train.py` then creates a
VM, installs that file with `colab install`, mounts the run's bucket prefix as the output directory, copies the
private data from Drive, executes the script with `colab exec`, and stops the VM. Starting it again with the same run
name resumes from the bucket, which matters because Colab sessions end without warning.

Commands for the whole project live in the root `justfile`. Each experiment and demo has its own `justfile` for its
own steps and falls back to the root one, so `just run`, `just lock` and the rest work from inside its directory.

## Setup

1. Create a repository from this template and open it in the dev container. The container has every tool installed.
2. Set `BUCKET` and `DRIVE_ROOT` at the top of the `justfile`.
3. Run `just auth`. It walks through whatever is missing: the Colab login, the GitHub login and rclone's access to
   Google Drive. Each prints a link to approve in a browser.
   - Drive access is requested with the scope `drive.file`: rclone sees only the files it uploaded itself, so private
     datasets go to Drive through `just drive-push`, not through the browser.
   - rclone's built-in Google client ID is being retired during 2026. To use your own, create the remote yourself
     before `just auth`: `rclone config create gdrive drive scope=drive.file client_id=... client_secret=...`
     ([how to get one](https://rclone.org/drive/#making-your-own-client-id)).
4. Create a fine-grained Hugging Face token that can write to the bucket's namespace and to the repositories the
   project uses, and put it in `.env` after `HF_TOKEN=`. This is the token the Colab VM receives, so keep it narrow.
5. Run `just auth-check` until every line says `ok`, then `just init-storage` and `just init-labels`.
6. In the repository settings, allow merge commits. Experiment pull requests are merged with a merge commit so that
   the commits an experiment README cites remain on `main`.

Then open your agent and tell it what you want to find out, or open the first Question yourself.

## Everyday commands

| You want to                                   | Run                                                        |
| --------------------------------------------- | ---------------------------------------------------------- |
| Start an experiment for issue 12              | `just new 12 label-smoothing`                              |
| Lock a script after changing its dependencies | `just lock train.py`                                       |
| Run a script on Colab                         | `just run train.py`                                        |
| Run it with different parameters              | `just run train.py EPOCHS=1 LIMIT=2000`                    |
| Resume or repeat a run under the same name    | `just run train.py --run NAME`                             |
| See what a run left in the bucket             | `just bucket-ls 012-label-smoothing`                       |
| Fetch a run's files to `.local/out/`          | `just bucket-pull 012-label-smoothing NAME`                |
| Upload a private dataset                      | `just drive-push ./data datasets/my-set/v1`                |
| Check formatting, lint and lock files         | `just check`                                               |
| See which credentials are in place            | `just auth-check`                                          |
| Render a report to HTML and PDF               | `just render`, in the report's directory                   |
| Start a demo                                  | `just serve`, in the demo's directory                      |
| Publish a merged experiment's weights         | `just deliver-hub ...` or `just deliver-drive ...`         |

The script commands are run from the experiment's directory. `just` alone lists everything.

## Layout

```text
AGENTS.md  CLAUDE.md          what an agent reads first
.agents/knowledge/            how to work here: the workflow, Colab and storage
.agents/skills/               step-by-step procedures, added when one is worth keeping
justfile  scripts/            project-wide commands and the Colab launcher
experiments/<NNN-slug>/       one experiment: README, justfile, single-file scripts and their locks, results/
template/experiment/          the starter that `just new` copies
demos/<name>/                 one demo: justfile and a single-file app
reports/<name>/               Quarto reports, drawn from experiments/*/results/
docs/                         findings that hold beyond one experiment
```

A directory appears when it has something to hold.

## The worked example

The repository carries one small research project, built through its own issues and pull requests so that the
workflow can be read from a real case and not only from its description.

- The direction is an Epic: [#2](https://github.com/hoshiori-dev/colab-template/issues/2), how a small digit classifier copes with rotated, shifted and rescaled digits.
- The first Question under it is [#3](https://github.com/hoshiori-dev/colab-template/issues/3): does affine augmentation close the accuracy gap on perturbed digits? The
  plan was posted there before anything ran, and the answer when it was known.
- The experiment that answers it is recorded in [#8](https://github.com/hoshiori-dev/colab-template/pull/8). Its milestone comments show what a record looks like: the
  first launch that worked and the bugs found on the way, the result, and a second run after the project's design
  changed, which corrected a finding of the first.
  [`experiments/003-affine-augmentation/`](experiments/003-affine-augmentation/README.md) holds the scripts, the
  results and the answer: augmentation lifts accuracy on perturbed digits from 84.0% to 97.5% and leaves a gap of
  1.1 points.
- What the experiment taught went to three places: its README, [`docs/geometric-shift.md`](docs/geometric-shift.md)
  for what holds beyond it, and [`.agents/knowledge/colab.md`](.agents/knowledge/colab.md) for what it taught about
  running on Colab.
- Two things it noticed without being asked became [#9](https://github.com/hoshiori-dev/colab-template/issues/9) and [#10](https://github.com/hoshiori-dev/colab-template/issues/10). They are open on purpose: either is a good
  first experiment for trying the template.
- The engineering around it was done as Tasks: the demo [`demos/digit-sketch/`](demos/digit-sketch) ([#5](https://github.com/hoshiori-dev/colab-template/issues/5)) and
  the report [`reports/affine-augmentation/`](reports/affine-augmentation) ([#6](https://github.com/hoshiori-dev/colab-template/issues/6)). A third Task, a shared library
  ([#4](https://github.com/hoshiori-dev/colab-template/issues/4)), was built and then dropped when the project decided that experiments and demos should not depend on
  shared code; the demo carries its own copy of the model.

The private dataset in the example is a stand-in: a perturbed copy of the public MNIST test set, generated by a script
and kept on Drive only to exercise that path.

## Starting your own project

Issues and pull requests are not copied when you create a repository from a template, so the example's history stays
here. Remove its files: `experiments/003-affine-augmentation/`, `demos/digit-sketch/`,
`reports/affine-augmentation/` and `docs/`. Nothing else refers to them. Point `BUCKET` and `DRIVE_ROOT` in the
`justfile` at your own storage, and replace this section and the one above with a description of your project.

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
