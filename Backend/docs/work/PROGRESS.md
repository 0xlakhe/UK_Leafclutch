# Backend progress

Chronological evidence log, in the EventBook format: one entry per task, one per review,
and one per round of fixes. Dates are local; any result that names a time also names its
zone.

**Failures are logged.** A round that fails is an entry, not a gap. When a later round
passes, the failed round stays where it is and the new entry says what superseded it.
Deleting a failure once it is fixed turns the log into fiction.

**Precedence.** The canonical record for a task is its `NNNN-slug.md`: full work log,
files, migrations, tests, decisions and review. This file is the reading copy. If the two
disagree, the task file wins and this file is corrected.

## Entry format

```text
Task: TASK-0001
Status: in-progress | in-review | done | blocked
Date: YYYY-MM-DD
Milestone: M1
Changed:
- path (what changed)
Evidence (actual runs, date):
- `command` → actual result; rule or criterion proved
Decisions:
- decision, alternative rejected, reason
Remaining: concrete unmet item, or none
Next: next task, decision or blocker
Canonical: [NNNN-slug.md](NNNN-slug.md)
```

Reviews use their own shape:

```text
Review: TASK-0001, round N
Reviewer: fresh `reviewer` subagent, session <id>
Date: YYYY-MM-DD
Scope: what was reviewed, and what was read-only
Independently verified: what the reviewer ran and saw
Findings: counts by severity, with file:line for anything not closed
Corrections: what changed after the review, and whether a recheck happened
Limits: what the review could not verify
Outcome: accepted / accepted with recorded minors / rejected
```

---

## Setup: repository and process

Status: done
Date: 2026-11-27

Changed:
- Fork cloned to `~/Work/UK_Leafclutch`, `upstream` added, branch `prabesh` created and pushed.
- `Backend/docs/` holds PRD, CONTRACT, DATABASE, ADMIN. `Backend/.gitignore` added.
- `AGENTS.md`, `.opencode/agents/` and the pre-push guard live locally; they are excluded and never pushed.
- `Backend/docs/work/PLAN.md` (22 milestones), `TEMPLATE.md`, `PROGRESS.md`, `README.md` index.

Evidence:
- `git push -u origin prabesh` → new branch; `a5c683c` docs commit.
- `opencode debug agents` → orchestrator, programmer and reviewer load; orchestrator `edit` limited to `Backend/docs/work/**`.

Decisions:
- One branch, `prabesh`; the pre-push hook refuses any diff outside `Backend/`.
- Per-task files stay canonical; this file is the reading copy.

Remaining: none.

---

## Task: TASK-0001 — FastAPI skeleton and local database

Status: blocked
Date: 2026-11-27
Milestone: M1

Changed:
- Skeleton written: `app/`, `migrations/`, `compose.yaml`, tests, `README.md`.

Evidence:
- `docker compose up -d db` → **failed**: `bind: address already in use` on 5432.
- Cause: a native PostgreSQL 18 owns 127.0.0.1:5432; 5433 is another project's container.
- `alembic current` with the documented URL therefore reached the wrong server and failed authentication.

Decisions:
- Do not stop the host PostgreSQL and do not point at it. Make the Compose host port configurable and use 5434 locally.

Remaining: start the Compose database, verify healthy, run `alembic current`.
Next: fix the port mapping, then re-run.

Canonical: [0001-skeleton.md](0001-skeleton.md)

---

## Task: TASK-0001 — port fix

Status: in-progress
Date: 2026-11-27
Milestone: M1

Changed:
- `compose.yaml`: project `leafclutch`, `"${POSTGRES_PORT:-5432}:5432"`.
- `.env.example` and `README.md`: the override documented.
- Local, gitignored `Backend/.env`: `POSTGRES_PORT=5434`.

Evidence:
- `docker compose up -d --wait db` → healthy on 5434; `leafclutch_test` created by the init script.
- `uv run alembic current` → exit 0.
- `uv run pytest` → 12 passed; ruff and mypy green.
- Commit `79d68f3`.

Decisions:
- The default stays 5432 so the repo is portable; 5434 is local only.

Remaining: independent review.
Next: dispatch the reviewer.

---

## Review: TASK-0001, round 1

Reviewer: fresh `reviewer` subagent
Date: 2026-11-27
Scope: the M1 diff, `f5fe65e..79d68f3`; read-only apart from a fresh `git archive` copy.
Outcome: **rejected — fixes required**, no Critical or High.

Independently verified (reviewer ran):
- ruff, mypy and pytest green; a clean-copy run without `.env` and `.venv` also green.
- Compose healthy, `alembic current` and `alembic check` exit 0, both databases present.
- `/health` 200, unknown route 404, app imports without `DATABASE_URL`.
- No `.env` in git history; only the local Compose password is a committed credential.

Findings:
- Medium 1 — `compose.yaml:11` published the database on `0.0.0.0` with a repo-known password.
- Medium 2 — `tests/conftest.py:15-18` hardcoded port 5432 and overrode any external `DATABASE_URL`.
- Medium 3 — `DATABASE.md:4782-4784` still said the data layer was unconfirmed.
- Low: socket-only healthcheck; a framework-only 404 test; unproven engine disposal; conftest import order; unused `log_level`; README missing `--wait`; the work file rewrote earlier evidence.

Corrections:
- All ten fixed in `06b61b6`; recheck requested.

Limits: default 5432 could not be exercised on this machine; no migrations existed yet.

---

## Task: TASK-0001 — review fixes

Status: in-review
Date: 2026-11-27
Milestone: M1

Changed:
- Loopback bind, configurable port, `--wait` in the README.
- `conftest.py` derives the port and uses `setdefault`; new `test_conftest.py`.
- `DATABASE.md` records the confirmed data layer.
- `log_level` removed until logging exists; disposal test added; 404 test deleted.

Evidence:
- `uv run pytest` → 14 passed; ruff and mypy green (orchestrator reproduced).
- `docker compose ps` → `127.0.0.1:5434->5432/tcp`; `alembic current` exit 0.
- Commit `06b61b6`.

Remaining: recheck.
Next: recheck the delta.

---

## Review: TASK-0001, round 2 (recheck)

Reviewer: same `reviewer` subagent
Date: 2026-11-27
Scope: `79d68f3..06b61b6`.
Outcome: **partially accepted — two Medium still open**, no Critical or High.

Independently verified:
- Eight of ten findings closed, with the disposal test proven by deleting `engine.dispose()` in a scratch copy.
- The suite passes with a bogus `.env`, so it does not read the developer's file.
- `localhost` resolves to `::1` before `127.0.0.1`; the IPv4-only bind still connects only through libpq fallback.

Findings:
- Medium 1 — `conftest.py:20` used `setdefault`, so **any** exported `DATABASE_URL` won, including a production URL. Latent now; High once M2 adds a database-backed test.
- Medium 2 — the documented `.env` port override was not honoured; conftest read only the environment.
- Low — `localhost` versus `127.0.0.1`; no test of the import-order claim; the work file claimed full closure.

Corrections:
- Guard added in `af66155`: validate the target, refuse a non-`_test` database or non-loopback host, force `ENVIRONMENT=test`, honour `POSTGRES_PORT` from `.env`, and prove it by failing collection on a production URL.

Limits: no test opens a connection; the guard is proven by construction and refusal, not by a query.

---

## Review: TASK-0001, round 3 (guard recheck)

Reviewer: same `reviewer` subagent
Date: 2026-11-27
Scope: `06b61b6..af66155`.
Outcome: **rejected — one High**, so M1 does not close.

Independently verified:
- Ambient production `DATABASE_URL` now fails collection with exit 4; the trailing `.env` port path resolves to 5434.
- `clear_settings_cache` clears the same function the app uses.

Findings:
- **High 1** — `tests/database_target.py:17-43` ignored `parsed.query`, so `?host=db.production.example&dbname=leafclutch` passed validation while SQLAlchemy's connect arguments pointed at the production host. Reproduced with `TEST_DATABASE_URL` and with `POSTGRES_PORT`.
- Medium 2 — malformed URLs printed their password verbatim (`{url!r}` plus `from exc`); query-string passwords were visible; `.env` interpolation could pull `${DATABASE_URL}` into the port value.
- Low — `--import-mode=importlib` failed; `.env` interpolation not disabled; the "forces test environment" test was not a force test.

Corrections:
- In progress: refuse any query, validate the port as a decimal in range, generic parse errors with `from None`, `dotenv_values(..., interpolate=False)`, `tests` on the pytest path, and a subprocess `ENVIRONMENT=production` test.

Limits: the query override was proven through SQLAlchemy's connect arguments and a loopback target, not a production connection.

---

## Task: TASK-0001 — guard bypass fix

Status: in-review
Date: 2026-11-27
Milestone: M1

Changed:
- `tests/database_target.py`: rejects any non-empty query before the host/database checks; validates `POSTGRES_PORT` as a decimal in 1–65535; generic parse errors raised `from None`; `.env` read with `interpolate=False`.
- `tests/test_conftest.py`: query-override, port-injection/range, malformed-URL redaction, interpolation and subprocess force tests.
- `pyproject.toml`: `pythonpath = [".", "tests"]` so `--import-mode=importlib` works.
- Commit `44c4d5e`.

Evidence (orchestrator reproduced, 2026-11-27):
- `uv run pytest -q` → 29 passed; `uv run pytest -q --import-mode=importlib` → 29 passed.
- `TEST_DATABASE_URL=…?host=db.production.example&dbname=leafclutch uv run pytest` → refused: "query parameters can override the connection target and are not allowed."
- `POSTGRES_PORT='5434?host=db.production.example' uv run pytest` → refused: "it must be a decimal integer between 1 and 65535."
- A malformed URL carrying `supersecret` → "it is not a valid SQLAlchemy URL", with zero occurrences of the password in the output.

Decisions:
- Reject every query rather than blocklist individual keys: a blocklist is a list of the attacks someone thought of.
- A generic parse error is preferred to a helpful one; the URL may contain a credential.

Remaining: none — the round-4 confirmation returned clean.
Next: close and commit.

Canonical: [0001-skeleton.md](0001-skeleton.md)

---

## Review: TASK-0001, round 4 (final)

Reviewer: same `reviewer` subagent
Date: 2026-11-27
Scope: `af66155..44c4d5e`.
Outcome: **accepted — no open Critical or High.**

Independently verified:
- Query override closed through both `TEST_DATABASE_URL` and `POSTGRES_PORT`; `?`, `?x=`, fragments and encoded separators were tried.
- The password is absent from malformed-URL, query-string, host/database, port and interpolation refusals.
- 29 tests pass in default and importlib mode, from `Backend` and from `/tmp`.
- The subprocess force test genuinely sets `ENVIRONMENT=production` before loading conftest.

Findings: four Low, deferred with reasons in the task file — the blanket query refusal
blocks `sslmode` for a future managed CI database; the `_test` suffix is a naming
convention, not a boundary; an empty `?` is accepted while the message says queries are
not allowed; and the interpolation test does not distinguish disabled interpolation from a
later rejection.

Limits: no connection to a real database; no production attempt; the default port 5432
could not be exercised on this host.

---

## Task: TASK-0001 — closed

Status: done
Date: 2026-11-27
Milestone: M1

Changed:
- Final state after `44c4d5e`; the review outcome is recorded in the task file and here.

Evidence:
- `uv run pytest -q` → 29 passed; `--import-mode=importlib` → 29 passed; ruff and mypy green.
- `docker compose ps` → healthy on `127.0.0.1:5434`; `alembic current` exit 0; `/health` 200.
- The orchestrator reproduced the guard refusals after round 4.

Decisions:
- Four Low findings deferred, each with a trigger, rather than extending M1 further: sslmode
  support when CI exists, the suffix policy, the message wording, and the interpolation test.

Remaining: none.
Next: M2.

Canonical: [0001-skeleton.md](0001-skeleton.md)

---

## Process: reviewed documents synced, plan updated

Status: done
Date: 2026-11-27

Changed:
- `Backend/docs/ADMIN.md`, `CONTRACT.md`, `DATABASE.md` replaced with the reviewed versions from the design workspace.
- `Backend/docs/runbooks/database-validation.md` and `.sql` added: the harness that executed the schema on PostgreSQL 18.7.
- `Backend/docs/work/PLAN.md`: validation reference, M11 (draft-on-unpublish, `delete_content`), M15 (Admin-only legal/settings, AAL1 sign-in), M16 (delete endpoint), M17 (evidence isolation), review focus 10–11, owner decisions.

Evidence:
- `cmp` and `sha256sum` identical for all five files against `/Users/prabeshshrestha/Work/website-build/docs`; commit `89ebb56`.
- `delete_content`: 8 occurrences in `DATABASE.md`, 3 in `ADMIN.md`. Decisions 69 and 70 at `CONTRACT.md:1076-1077`.
- Design workspace committed and clean at `baa66d0`; its tasks 0001, 0002 and 0003 are `done` with no open findings.

Decisions:
- **M8 accepted** by the owner on 27 November: no settings/landing two-way gate. The risk stays recorded in `ADMIN.md` §14 and is not mitigated.
- **D-13 deferred to week 4**; it blocks the operational assignment, not M18.
- The local database moves to the validated major, PostgreSQL 18. The production Supabase major is confirmed at deployment (M22); if it differs, the harness is re-run there.

Remaining: the Compose image change and its verification.
Next: M2 — extensions, enums and `staff`.

Canonical: [PLAN.md](PLAN.md)

---

## Task: TASK-0002 — extensions, enums and staff

Status: done
Date: 2026-11-27
Milestone: M2

Changed:
- `migrations/versions/0001_extensions_enums.py`, `0002_staff.py`; `app/models.py`; `migrations/env.py` (`compare_server_default`, `auth` excluded); `scripts/bootstrap_local.sql`; `tests/conftest.py`, `test_migrations.py`, `test_staff_schema.py`; `README.md`; `DATABASE.md` (guard and downgrade).

Evidence (actual runs, PostgreSQL 18.7):
- `uv run pytest -q` → 59 passed; `--import-mode=importlib` → 59 passed.
- `alembic check` → no new operations; `alembic current` → `0002_staff`.
- `downgrade base` → enums gone, `citext`/`pgcrypto` retained; `upgrade head` → clean.
- Trigger `staff_lock_writes BEFORE INSERT OR DELETE OR UPDATE ... FOR EACH STATEMENT`; `enforce_last_admin` counts through `for update`.
- Mutation: with `staff_lock_writes` dropped, the two-delete test fails with `40P01`; with it, one `P0001`/`40001` and one active Admin.

Decisions:
- The last-Admin invariant is enforced at `READ COMMITTED`, `REPEATABLE READ` and `SERIALIZABLE`. The advisory lock sits in a statement trigger so it precedes the statement's own row locks; the count is a locking read so stricter isolation reports `40001` instead of allowing the removal.
- A lock held by the caller before the statement cannot be reordered by a trigger; staff services must take the advisory lock before their first staff row lock or retry `40P01`. Recorded as an M15 obligation.
- The `0001` downgrade drops enums only; extensions are shared objects and stay.
- `DATABASE.md` in this checkout carries the fixed guard; the design workspace still has the unguarded body until it is patched.

Remaining: none. Deferred Lows: `TRUNCATE` bypass, catalog-level CHECK/enum drift, manual round trip.
Next: M3 — media.

Canonical: [0002-extensions-enums-staff.md](0002-extensions-enums-staff.md)

---

## Review: TASK-0002, rounds 1–4

Reviewer: one `reviewer` subagent across all rounds
Date: 2026-11-27
Scope: `3c6f46f..0c24e23`.
Outcome: **accepted — no open Critical or High.**

Round 1: High (guard not concurrency-safe; two deletes leave zero), 2 Medium, 8 Low — fixed in `64cf3b2`.
Round 2: High (advisory lock fails at `REPEATABLE READ`/`SERIALIZABLE`), Medium (new `40P01` deadlock), Medium (stale docs) — fixed in `2be94ce`.
Round 3: no High; Medium (trigger misses `INSERT` and earlier locks), Medium (deadlock test passes without the trigger) — fixed in `0c24e23`.
Round 4: no Critical, High or Medium; mutation proves the new test fails with `40P01` when the trigger is dropped.

Limits: Supabase was not run; the design workspace copy of `DATABASE.md` still differs; no admin service exists to exercise `40001` handling.

---

## Sync: design-workspace divergence closed

Status: done
Date: 2026-11-27

Changed:
- `Backend/docs/CONTRACT.md`, `ADMIN.md` and `DATABASE.md` replaced with the design workspace's `75dcc0c`.

Evidence:
- `sha256sum` identical for all three; `PRD.md` and both runbooks were already identical.
- Present: `hours.summary`; `title` 40, `body` 160; `{kind, path, slug}`; `both (legal_page/settings: Admin)`; `sign-ins tab`; `no two-way gate`; "after this trigger"; `Backend/docs/work/PLAN.md M15`.
- Absent, zero occurrences: `phone_hours.summary`; `path?, slug?`; `/admin/sign-ins`; `a gate needs a decision`.
- Design workspace: `120fbaf` applied the M2 guard; `75dcc0c` clarified the INSERT sentence and the PLAN citation.

Decisions:
- The two repositories are now identical for the four documents and both runbooks. The M2 note that the design workspace still carried the unguarded body is resolved, and the next sync will not revert the guard.

Remaining: none.
Next: M3 — media.




