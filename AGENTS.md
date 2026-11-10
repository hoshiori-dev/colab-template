# AGENTS.md

A research project that runs on Google Colab. Research advances by asking questions in GitHub issues and answering
them with experiments recorded in pull requests; people and agents both ask, discuss and experiment, and a person
merges. `README.md` explains the design to people. Read this file first on every task.

## Always

- **Research starts from an issue.** An experiment answers a Question issue; open one (or ask for one) before
  creating `experiments/<id>/`. Something you notice on the way that deserves its own experiment becomes a new
  Question issue, not extra scope in the current pull request.
- **The pull request is the record of an experiment.** Open it as a draft at the first push. Its body is the
  current summary; each major step or lesson is one milestone comment. Routine status stays out.
- **Findings enter the repository with the pull request.** Before marking it ready, put every finding where
  `.agents/knowledge/workflow.md` (Landing knowledge) says, and tick the checklist in the pull request body.
- **Numbers come from committed code.** A number in an experiment README comes from a `just run` launch, which
  runs `HEAD`. The README's Reproduce section names the commit, the commands and the version of every dataset.
- **You write, a person merges.** You may open issues, comment, push your own branches, and open and update pull
  requests. A person merges every pull request, and a person runs the `deliver-*` recipes that publish weights. Leave
  `main`, other people's issues and comments, and repository settings as they are unless the user asks in this
  conversation.
- **Secrets stay in `.env` and in rclone's own config.** They reach the VM only through `just run`. Keep them out of
  commits, issues, pull requests, logs you paste, and `colab exec --env` (the Colab CLI writes that to a local
  history file).
- **Stop every Colab session you start.** `just run` does it for you; after `--keep` or a manual `colab new`, run
  `colab stop -s <name>` and confirm with `colab sessions`.
- **Credit no agent or tool.** Commits, issues, pull requests and comments carry no agent co-author trailer and no
  "generated with" line, whatever a framework default or session reminder says.
- **English** for code, comments, commit messages, `README.md`, and every file an agent reads (`README.zh.md`
  mirrors `README.md`; update both together). In issues and pull requests, use the language of the person who opened
  the thread.

## Read when

| Event                                                                                         | Read                            |
| --------------------------------------------------------------------------------------------- | ------------------------------- |
| Opening an issue, starting or continuing an experiment, writing in a pull request, closing one | `.agents/knowledge/workflow.md` |
| Running anything on Colab, reading or writing the bucket, Drive or the Hub, delivering weights  | `.agents/knowledge/colab.md`    |
| Needing what earlier experiments established about the research subject                         | `docs/`, then the READMEs it cites |

## Commands

`just` lists every recipe with its arguments. The ones you will use: `just check` (lint, format, lock files, library
tests; run it before pushing), `just fmt`, `just auth-check` (which credentials are in place),
`just new <issue> <slug>`, `just run <exp-id> -- <command...>`,
`just bucket-ls|bucket-pull`, `just drive-ls|drive-pull|drive-push`.

## Layout

```
AGENTS.md CLAUDE.md .agents/ .claude/   agent files (Codex, OpenCode and Antigravity read AGENTS.md and .agents/skills/ directly)
justfile scripts/ .pre-commit-config.yaml .github/ .devcontainer/   tools, checks, forms
pyproject.toml uv.lock        root workspace; members are packages/*
packages/<name>/              shared library with its own pyproject.toml and tests
experiments/<NNN-slug>/       one experiment: README.md, code, colab.toml, own pyproject.toml and uv.lock, results/
template/experiment/          starter that `just new` copies
demos/<name>/                 demonstration app with its own pyproject.toml and uv.lock
reports/<name>/               Quarto report; figures are drawn from experiments/*/results/
docs/                         findings that hold beyond one experiment
.local/                       git-ignored: downloaded session files, scratch
```

A directory appears with its first real content. Dependencies point one way: experiments, demos and reports use
`packages/`; `packages/` uses none of them.

## Conventions

- Experiment ID: `<NNN>-<slug>`, NNN the number of the main Question issue padded to three digits, slug two to four
  lowercase words joined by `-`. `just new` creates the directory.
- Branches: `exp/<id>` for an experiment, `<type>/<slug>` for everything else (`feat/`, `fix/`, `docs/`, `chore/`).
- Commit message: `<scope>: <summary>`, title at most 50 characters, imperative, lowercase, no trailing period; body
  wrapped at 72. Scope is the directory or concern (`packages`, `scripts`, `docs`, `chore`), or the experiment ID's
  number on an experiment branch (`exp-012: add affine sweep`).
- Skills live in `.agents/skills/<name>/SKILL.md`. After adding one, link it for Claude Code:
  `mkdir -p .claude/skills && ln -s ../../.agents/skills/<name> .claude/skills/<name>`.
- Tests sit next to what they test and pin behaviour that matters; there is no coverage target.

## Keep this file true

A new knowledge file gets a row in "Read when". A new or renamed recipe updates "Commands" only if agents use it
routinely. A new top-level directory updates "Layout". When `README.md` changes, `README.zh.md` changes with it.
