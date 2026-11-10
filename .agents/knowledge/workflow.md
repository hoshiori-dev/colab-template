# Research workflow

Read this before opening an issue, starting or continuing an experiment, writing in a pull request, or closing one.

## Objects

| Object       | Is                                                                        | Lives in                                         |
| ------------ | ------------------------------------------------------------------------- | ------------------------------------------------ |
| Epic         | a direction of research that groups questions; needs no approval          | issue, label `epic`                              |
| Question     | one question an experiment can answer                                     | issue, label `question`, sub-issue of its epic   |
| Task         | engineering work: shared library, demo, report, project setup             | issue, label `task`                              |
| Experiment   | code, results and a README that answer one or more questions              | `experiments/<NNN-slug>/`                        |
| Pull request | for an experiment, its record; for a task, an ordinary software change    | branch `exp/<id>` or `<type>/<slug>`             |

One pull request may carry several experiments and close several issues. Each experiment directory is named after
its main question; its README lists the others.

## Issues are where questions are asked and discussed

- Open a Question whenever something is worth an experiment: a gap in `docs/`, a surprising number, a doubt about an
  earlier answer. Agents open questions on their own initiative; the form asks for the question, the background and
  what would count as an answer. Create it under its epic: `gh issue create --template question.yml --parent <epic>`
  (or `gh issue edit <n> --parent <epic>` afterwards).
- Discussion, proposals, objections and decisions about a question go in its comments, so the reasoning sits next to
  the question. Before starting an experiment, read the whole thread and say in a comment what you plan to run.
- When you need a decision from a person (direction, a trade-off, more compute), ask in the issue and continue with
  whatever does not depend on the answer.
- Engineering needs found during an experiment become Task issues unless the fix belongs to the experiment's own
  directory.

## Experiment loop

1. `git switch -c exp/<id> main`, then `just new <issue-number> <slug>`.
2. Write the README's Question and Setup sections first; they are the plan. Commit, push, open a draft pull request
   from `.github/PULL_REQUEST_TEMPLATE.md` with `Closes #<n>` for every question it will answer.
3. Iterate: change code, commit, `just run`, look at the results. Local CPU runs are fine for debugging; they are not
   evidence.
4. Copy the small result files the answer rests on (metrics, tables; not checkpoints) from the bucket into
   `experiments/<id>/results/` and commit them. Reports and figures are built from these files.
5. Land the findings (next section), bring the pull request body up to date, post the answer on each issue, mark the
   pull request ready. A person reviews and merges; merging closes the issues.

A negative or inconclusive answer is a result: write it up and close the question the same way.

## The pull request as record

The body is the experiment's current summary and is rewritten as understanding changes. A milestone comment is added
when something happens that a later reader needs in order to understand how the answer was reached:

- the first run that works end to end, and what it showed;
- a result that changed the plan, with the old and the new plan;
- a dead end, and why it is one;
- a lesson about tools, data or Colab that cost time to learn.

Write each comment so it stands alone: what was done, what was observed (with the numbers), what it changes. Post it
once and leave it; a correction is a new comment. Per-run status, retries and anything the commit log already says
stay out.

## Landing knowledge

Every finding in the pull request, asked for or not, goes to exactly one place:

| The finding is about                                             | It goes to                                                    |
| ---------------------------------------------------------------- | ------------------------------------------------------------- |
| this experiment: the answer, the evidence, limits, how to rerun  | `experiments/<id>/README.md`                                  |
| the research subject, and it holds beyond this experiment        | `docs/<topic>.md`, citing the experiments it rests on         |
| how to work in this repository: tools, Colab, storage, pitfalls  | `.agents/knowledge/` (the file whose trigger matches)         |
| a procedure worth repeating step by step                         | a skill in `.agents/skills/<name>/`                           |

`docs/` holds one file per topic, written as the current state of knowledge (edit a statement when a later
experiment refines it, and cite both). The first finding creates `docs/README.md` as the index; every later file adds
its line there. When a finding contradicts something already in `docs/` or `.agents/knowledge/`, change that text in
the same pull request.

## Closing

On each issue the pull request closes, post one comment with the answer in two or three sentences, the key number,
and links to the experiment README and the pull request. Then tick the "Knowledge landed" checklist and mark the pull
request ready for review.

After the merge a person may publish what the experiment produced (`just deliver-hub`, `just deliver-drive`); see
`.agents/knowledge/colab.md`, Delivery.

## Engineering pull requests

A Task is done in one ordinary pull request, coarse-grained when that is the natural unit (a whole demo, a whole
report). Its body keeps only Summary and Verification. Shared-library changes that an experiment needs may ride in
the experiment's pull request when they are small; otherwise do the Task first.
