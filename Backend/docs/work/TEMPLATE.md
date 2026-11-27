# Work file template

Copy to `NNNN-slug.md` and delete the guidance in angle brackets. `AGENTS.md` holds the
ownership and review rules; this file holds the shape and the evidence vocabulary.

Status values: `in-progress`, `in-review`, `done`, `blocked`. Only the orchestrator sets
`status`, and only after the review has no open Critical or High and `Remaining` is empty.

```
---
task: NNNN
title: <short title>
status: in-progress
branch: prabesh
started: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---

## Goal
One paragraph. Cite the requirement IDs it serves (LP-2, EN-9, AD-4) and the section of
the source document.

## Acceptance criteria
- [ ] Testable statement. Each one names how it is demonstrated.

## Non-goals
What this task deliberately does not do, so the reviewer stops asking for it.

## Plan
The slice, the files expected to change, and the interface or contract it exposes.
For an endpoint, name the request and response shape before writing the handler.

## Work log
### <YYYY-MM-DD>
- What was done, in past tense, with file paths.
- What surprised you and how you handled it.
- Corrections: what was wrong, what changed, and whether the earlier result is superseded.

## Decisions made
Each entry: the decision, the alternative rejected, and the reason. A decision the source
documents already make is cited, not re-argued.

## Files changed
New, modified, deleted, grouped by area. Include migrations and generated files such as
`uv.lock`.

## Migrations
Revision id, what it changes, `upgrade` and `downgrade` tested or why not.

## Tests
Every command and its result. Use this vocabulary:
- **actual run** — the command and the output, quoted.
- **superseded** — an earlier result replaced by a later one; say which.
- **not run** — and why. A planned command is never written as a run.

Quote failures that were fixed; a green suite with a deleted test is not evidence.
A round that fails is recorded as an entry of its own. When a later round passes, the
failed entry stays and the new one says what superseded it.

## Review
Round, reviewer session, findings by severity with `file:line`, and how each was resolved
or why it was deferred. Record what the reviewer could not verify.

## Docs updated
`DATABASE.md`, `CONTRACT.md`, `ADMIN.md`, `PLAN.md`, OpenAPI, ADR, runbook — or `none`,
with the reason.

## Remaining
What this task still owes: an unmet acceptance criterion, a deferred Medium finding, a
check that could not run. `none` is a claim, not a default.

## Next
The next action and who owns it: the next task number, a decision the user must make, or
a blocker outside the repository.

## Open questions
Unresolved decisions, blocked dependencies, who answers.

## Not verified
What could not be checked: missing environment, skipped test, manual step not run. This
section is never deleted to make a task look finished.
```
