---
task: 0005
title: Sync reviewed CONTRACT and ADMIN from the design workspace
status: in-progress
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Take the reviewed `CONTRACT.md` and `ADMIN.md` from the design workspace
`/Users/prabeshshrestha/Work/website-build` (branch `phase-1`, HEAD `d1c7707`) into
`Backend/docs/`, so this branch holds decisions 71–76 and the `/admin/revalidation`
screen row. `DATABASE.md` is deliberately not synced because this branch's copy is ahead
of the design copy on the M2–M4 work.

Documentation only: no application code, no migration, no test change.

## Acceptance criteria

- [x] Source check passed before copying: `CONTRACT.md` has six rows 71–76, two
      occurrences of `no timezone of its own`, and `ADMIN.md` has one
      ``| `/admin/revalidation` `` row. Demonstrated under `## Tests`.
- [x] `Backend/docs/CONTRACT.md` and `Backend/docs/ADMIN.md` are byte-for-byte copies of
      the design workspace files; `cmp` is silent on both. Demonstrated under `## Tests`.
- [x] The copies carry the same six decision rows, the two timezone sentences and the one
      revalidation row. Demonstrated under `## Tests`.
- [x] `Backend/docs/DATABASE.md` is unchanged: same sha256 before and after, and it still
      carries `media_deleted_after_upload` and `their six indexes`. Demonstrated under
      `## Tests`.
- [x] `git diff --check` is silent and `git status --short` lists only paths under
      `Backend/docs/`. Demonstrated under `## Tests`.
- [x] Only `Backend/` changes; `Frontend/`, `Admin/` and `DATABASE.md` untouched.

## Non-goals

- Syncing `Backend/docs/DATABASE.md`. The design copy is 66 lines shorter and differs on
  104 added/removed lines; copying it would revert M2–M4 schema work.
- Merging or cherry-picking anything from `handover/ui-fields`.
- Any implementation of decisions 71–76: no `noindex` control, no route changes, no staff
  delete endpoint, no Next invite route. Those are contract decisions for later slices.
- Any code, migration, test or dependency change. No OpenAPI regeneration is needed because
  no endpoint was added to the running app.
- Pushing.

## Plan

| File | Change |
| --- | --- |
| `Backend/docs/CONTRACT.md` | Replaced with the reviewed copy: decisions 71–76, row 33 and the §Locations prose corrected for `phone_hours` |
| `Backend/docs/ADMIN.md` | Replaced with the reviewed copy: one added screen row, `/admin/revalidation` |
| `Backend/docs/work/0005-source-docs-sync.md` | This log |
| `Backend/docs/work/README.md` | Index row for 0005 |

Order: verify sources, `cp` the two files, re-verify the copies with `cmp` and `grep`,
prove `DATABASE.md` is untouched, write this file, run the git checks, commit.

## Work log

### 2026-11-27

- Verified both workspaces before touching anything: `Backend` branch `prabesh` with a
  clean tree; design workspace branch `phase-1` at `d1c7707`.
- Ran the three source checks against `~/Work/website-build/docs/`: 6, 2, 1 — all as the
  brief expected, so the copy proceeded.
- Read the differences before copying rather than after: `CONTRACT.md` changes are
  decisions 71–76 plus the `phone_hours` correction in row 33 and in the §Locations prose
  (10 insertions, 4 deletions); `ADMIN.md` adds only the `/admin/revalidation` row
  (1 insertion).
- Copied `CONTRACT.md` and `ADMIN.md` with `cp` and confirmed each with `cmp`; both are
  byte-identical to the design workspace.
- Checked that the new decisions do not contradict this branch's `DATABASE.md`:
  `contact_phone_hours` and `phone_hours` are already `text` (`DATABASE.md` lines 1348
  and 1418), so decision 71 corrects the contract to the schema rather than creating a
  conflict; `seo_noindex` (line 533), `long_description` (line 925) and `category`
  (line 1005) all exist, matching decisions 72 and 73, which hide rather than drop them.
  `ADMIN.md` already listed `GET /revalidation` in its API table (line 364), so the new
  screen row is consistent with the rest of the document.
- Left `DATABASE.md` alone. Recorded its baseline sha256 before the copy and re-checked it
  after: unchanged (`1811fd98d46fc7907eb8e21ae3cfcce81b0f7654af4b28188ecb4445f608bf49`).
- Created this work file and the README index row.
- Found the working tree dirty on two files this slice never touched:
  `0004-content-spine.md` and `PLAN.md` were modified by another session during the run
  (round-2 recheck text and an M11 archive note). They were left unstaged and are not in
  this commit; the initial `git status --short` on this branch was empty, so they arrived
  after work began.
- Ran `git diff --check` (silent) and `git status --short` before committing; every path in
  the commit is under `Backend/docs/`.

## Decisions made

- **`DATABASE.md` is not synced, by design.** The design copy is behind this branch on the
  M2–M4 schema work; copying it would revert `media_deleted_after_upload`,
  `their six indexes` and the rest of the newer schema text. The design workspace's
  `DATABASE.md` is the older of the two, so the direction of travel is this branch →
  design workspace for that file, not the reverse. Checked by count and sha256.
- **The two documents were copied byte-for-byte, not merged.** No local edit was made to
  `CONTRACT.md` or `ADMIN.md` while copying, so `cmp` proves the copy and a future diff
  against the design workspace stays meaningful. Rejected alternative: applying the
  changes as a patch on top of our copies — it would produce the same bytes with more ways
  to diverge.
- **Nothing was taken from `handover/ui-fields`.** That branch was not read, merged or
  cherry-picked; only `~/Work/website-build/docs/CONTRACT.md` and `.../ADMIN.md` were
  copied.
- **Docs-only, so the suite was not re-run.** No Python, migration, fixture or config file
  changed, so lint, typecheck, `pytest` and `alembic check` results would be identical to
  task 0004's recorded run. Recorded under `## Not verified` rather than presented as a
  fresh run.

## Files changed

Modified:

- `Backend/docs/CONTRACT.md` — 10 insertions, 4 deletions: decisions 71–76; row 33 and
  the §Locations `phone_hours` prose corrected to "a text string" and "no timezone of its
  own in Phase 1 (decision 71)"
- `Backend/docs/ADMIN.md` — 1 insertion: `/admin/revalidation` in the screen table
- `Backend/docs/work/README.md` — index row for 0005

New:

- `Backend/docs/work/0005-source-docs-sync.md` — this log

Unchanged, deliberately: `Backend/docs/DATABASE.md` (sha256 identical before and after),
`Backend/docs/PRD.md`, `Backend/app/**`, `Backend/migrations/**`, `Backend/tests/**`,
`Frontend/`, `Admin/`, `uv.lock`.

Not in this commit, though modified in the working tree: `Backend/docs/work/0004-content-spine.md`
and `Backend/docs/work/PLAN.md`. Those are another session's concurrent M4 edits; they were
left unstaged so this commit stays one logical change.

## Migrations

None. No table, column, constraint, function, grant or index changes.

## Tests

Documentation-only change; the evidence is byte comparison and the git checks. All output
below is an actual run on 2026-11-27.

Source verification, before copying:

```
$ grep -c '^| 7[1-6] ' ~/Work/website-build/docs/CONTRACT.md
6
$ grep -c 'no timezone of its own' ~/Work/website-build/docs/CONTRACT.md
2
$ grep -c '^| `/admin/revalidation`' ~/Work/website-build/docs/ADMIN.md
1
```

Copy and byte comparison:

```
$ cp ~/Work/website-build/docs/CONTRACT.md Backend/docs/CONTRACT.md
$ cp ~/Work/website-build/docs/ADMIN.md Backend/docs/ADMIN.md
$ cmp ~/Work/website-build/docs/CONTRACT.md Backend/docs/CONTRACT.md && echo identical
identical
$ cmp ~/Work/website-build/docs/ADMIN.md Backend/docs/ADMIN.md && echo identical
identical
```

Verification of the copies:

```
$ grep -c '^| 7[1-6] ' Backend/docs/CONTRACT.md
6
$ grep -c 'no timezone of its own' Backend/docs/CONTRACT.md
2
$ grep -c '^| `/admin/revalidation`' Backend/docs/ADMIN.md
1
$ wc -l Backend/docs/CONTRACT.md Backend/docs/ADMIN.md
    1220 Backend/docs/CONTRACT.md
     976 Backend/docs/ADMIN.md
```

`DATABASE.md` untouched:

```
$ grep -c 'media_deleted_after_upload' Backend/docs/DATABASE.md
1
$ grep -c 'their six indexes' Backend/docs/DATABASE.md
1
$ shasum -a 256 Backend/docs/DATABASE.md
1811fd98d46fc7907eb8e21ae3cfcce81b0f7654af4b28188ecb4445f608bf49  Backend/docs/DATABASE.md
```

The same sha256 was recorded before the copy; the file did not change.

Diff of the two documents:

```
$ git diff --numstat -- Backend/docs/CONTRACT.md Backend/docs/ADMIN.md
1       0       Backend/docs/ADMIN.md
10      4       Backend/docs/CONTRACT.md
```

Working-tree checks:

```
$ git diff --check
(silent)
$ git status --short
 M Backend/docs/ADMIN.md
 M Backend/docs/CONTRACT.md
 M Backend/docs/work/0004-content-spine.md
 M Backend/docs/work/PLAN.md
 M Backend/docs/work/README.md
?? Backend/docs/work/0005-source-docs-sync.md
```

The `0004-content-spine.md` and `PLAN.md` entries are not this slice's work: another
session edited them in the same checkout while this one ran (the M4 round-2 recheck and the
M11 archive note). They were left unstaged. The staged commit contains only the four paths
listed under `## Files changed`.

Superseded: none — this is the only round.

Not run: `uv run ruff check .`, `uv run mypy app`, `uv run pytest`, `uv run alembic check`.
No executable change is in this commit; see `## Not verified`.

## Review

Left for the orchestrator.

## Docs updated

- `Backend/docs/CONTRACT.md` — now the reviewed design copy: decisions 71–76, decision 71
  (`DATABASE.md` wins on a conflict), 72 (no per-page `noindex` control in Phase 1,
  field stays on the wire read-only), 73 (hide the Phase 2 `long_description` and
  `category`), 74 (the "image missing" badge is API state), 75 (staff removal is
  deactivation), 76 (Supabase hosted invite and reset flow, no Next landing route); row 33
  and the §Locations prose now say `phone_hours` is a text string and a location has no
  timezone of its own in Phase 1.
- `Backend/docs/ADMIN.md` — now lists `/admin/revalidation` as an Admin-only screen with
  the loading, empty, filtered and failed states.
- `Backend/docs/DATABASE.md` — unchanged; it is ahead of the design copy and decision 71
  makes it authoritative on conflicts.
- OpenAPI — unchanged. No endpoint was added, removed or altered in the running app; the
  `/admin/revalidation` screen reads the already-documented `GET /revalidation`.
- No ADR: `Backend/docs/` has no ADR directory; the decisions themselves are recorded in
  `CONTRACT.md`.
- No runbook change.

## Remaining

- none.

## Next

Orchestrator: review this slice, then decide whether decisions 72–76 need follow-up
slices. Decision 71 changes the tie-break rule for every later payload; decisions 72, 73
and 75 constrain the admin endpoints that do not exist yet.

## Open questions

- Should `DATABASE.md` be pushed from this branch back into the design workspace so the two
  copies agree? Out of scope here and it is the design workspace's decision, not this
  branch's.
- Decision 72 keeps `noindex` on the wire as a read-only field. When the admin payloads are
  built, the read-only rule has to be enforced server-side (reject a `seo_noindex` value in
  a write body) rather than only in the UI. Not decided or implemented here.

## Not verified

- Lint, typecheck, tests, `alembic check` and the migration round trip were **not run** for
  this commit. Nothing executable changed (`Backend/app/**`, `Backend/migrations/**`,
  `Backend/tests/**` and `uv.lock` are untouched), so the last green run remains task
  0004's.
- The `/admin/revalidation` screen, the `GET /revalidation` endpoint and the worker behind
  them are documentation only at this point; no code implements them.
- `DATABASE.md` was checked by two representative greps and a sha256, not by reviewing all
  5196 lines against the design copy. The full comparison was not made because the file was
  not copied.
- Nothing was compared against `handover/ui-fields`; the branch was deliberately not read.
