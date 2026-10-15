---
name: accounts-code-review
description: Review an ERPNext Accounts PR against its GitHub issue or support ticket, with code review, a deterministic before/after ledger run on a live bench site, and Playwright checks for UI changes. Use only when the user asks for this review by name and gives a PR and an issue or ticket; the run changes a bench site.
---

# Reviewing an Accounts pull request

Accounting bugs are **silent**: the document saves, the ledger is wrong, and
nobody notices until the books do not close. This review posts real documents on
a **live site** under the base code and under the PR code, and compares the
ledgers.

The review is **deterministic**. Scripts do every mechanical step in a fixed order:
blast-radius analysis, settings variants, a fixed scenario library, the run, and
the verdict. You decide four things, write them to files, and **lock** them before
the run. The same PR, the same locked files and the same site give the same verdict.

| You write | Scripts do |
| --- | --- |
| `requirement.md`: what the requirement source says | `init`: fetch the PR, pin the base and head commits, merge the PR onto base |
| `code-review.md`: the `frappe-code-review` findings | `analyze`: changed functions, callers in every app, settings read, variants |
| `s0.py`: the requirement's repro as a scenario | `run`: build the library and `s0` in every variant, on both codes |
| `expect.json`: the values you predict, and the changes the fix may cause | `report`: diff every comparison, compute the verdict, write a readable report |
| `ui.spec.mjs`: the screens to check, when the PR changes UI files | `run`: the same Playwright steps on base code and PR code |

The skill takes two arguments: the PR, as a URL or a number, and the
**requirement source**, a GitHub issue or a support ticket. If either one is
missing, ask for it. The skill needs the `gh` CLI, signed in, a local bench with
ERPNext, and Node.js when the PR changes UI files.

All commands are `python3 <skill dir>/scripts/review.py <command> --workdir <workdir>`.
Use `/tmp/review-<N>` as the workdir. `init` copies the scripts into
`<workdir>/scripts`, and every later command runs from that copy, because the run
switches the `apps/erpnext` checkout, which may not contain this skill. The lock
covers the copy, so a skill update cannot change a review between lock and run.

## 1. Init

Ask the user which site to use. The run does these things to it, and undoes
them when it ends, also when it fails:

- It commits review companies, masters and documents. It deletes all of them at the end, unless the user explicitly asked to keep them. The report needs only the snapshot files in the workdir.
- It switches settings singles to each variant value.
- It pauses the scheduler.
- It runs `migrate` on the base code, and again on the PR code if the PR changes doctype JSON, `patches.txt` or `hooks.py`.
- It switches the shared `apps/erpnext` checkout, which every site on the bench uses.
- With UI checks, it builds the app's assets for each code, serves the site on a free local port, and creates a new user for the run, `<run>-ui@example.com`. The run refuses to use a user that already exists. Cleanup rebuilds the assets for the original checkout.

```
review.py init --workdir <workdir> --pr <N> --requirement <issue url or ticket ref> --site <site> --bench <bench path>
```

Options for other setups: `--repo <owner/repo>` for a fork (default `frappe/erpnext`),
`--app <app dir>` (default `erpnext`), and `--bench-cmd "<command>"` when `bench`
is not on the PATH.

The skill reviews PRs for any ERPNext version. Give the bench and the site that
run the same major version as the PR's base branch: a bench on Frappe v15 for a
`version-15-hotfix` PR, for example. `init` refuses a version mismatch, a dirty
`apps/erpnext`, and a PR that does not merge cleanly onto its base. Report the
refusal to the user, and stop.

## 2. Requirement

A GitHub issue is in `requirement.json` with its comments. For a support ticket,
fetch it if the URL is public. Otherwise, ask the user to paste it, and put the
text in `requirement.json` under `text`. Never reconstruct a ticket from its title
or from the PR.

Write `requirement.md` with four parts. Quote the source in each part, or write that
the source does not state it:

- **Reported**: what the user saw, with their numbers.
- **Expected**: what should happen instead.
- **Repro**: the steps and the data.
- **Setup**: the version, country, currency, and every setting the reporter names.

Then compare the requirement with `pr.json` and `pr.diff`. Record in
`requirement.md` any reported case that the PR does not address, and any behavior
change that the requirement did not ask for.

## 3. Code review

Run the `frappe-code-review` skill on `pr.diff`. If it is not installed, install it
with `npx skills add frappe/skills --skill frappe-code-review`. Write the findings to
`code-review.md`, each with its `file:line`. A finding that claims wrong ledger
behavior becomes a scenario in `s0.py` and an assertion in `expect.json`.

## 4. Analyze

```
review.py analyze --workdir <workdir>
```

This writes `analysis.json` (changed symbols, callers, settings) and `plan.json`
(variants and flips). The generated plan varies every enumerable setting on a
changed path, one value at a time. Each variant lists the code it exists on. A setting or option that
the PR adds runs on the PR code only, and is compared with the base code at the
site defaults. A value that the PR removes runs on the base code only.

Edit `plan.json` only to add, or to match the requirement's **Setup**:

- Add a variant for each **Setup** setting that the analysis did not find, and values for settings it lists as not varied.
- Set `company_profile` (`country`, `currency`, `chart_of_accounts`) when the requirement is regional. The default is a United States company in USD on the Standard chart.
- Set `item_fields` when the preflight reports that an installed app makes an Item field mandatory.
- Set `"ui": true` when a server change shows on screen, even with no UI file in the diff.

Keep every generated variant. The report prints your edits as a diff against
`plan.generated.json`.

## 5. Write `s0.py` and `expect.json`

Both start from templates in the workdir. Write them before any run. A prediction
written after the run is a rationalization, and the lock makes the order visible.

`s0.py` holds the requirement's **Repro**: one scenario per reported case, with
the reporter's data. It runs after the fixed library in every company. The template
lists what `lab.ctx` provides. Post on `DATE`, and pass every account, currency and
rate explicitly. A scenario must give the same ledger every time it runs.

`expect.json` holds two lists:

- `assertions`: exact values on one snapshot. Each one has a `path` (for example `docs.s0_invoice.outstanding_amount`, `balances.Debtors`, `gl.<s0_invoice>` or `outcomes.cancel-s0`), a `snapshot` (`base`, `head`, `base_legacy` or `head_legacy`), the value it `equals`, and a `why` that quotes the requirement. A bug review needs at least one `base` assertion (**Reported**) and one `head` assertion (**Expected**). Every assertion must run. An assertion that lists `variants` must run on each one, so a listed variant without that snapshot (for example `head_legacy` on a setting that only the PR adds) makes the review `INVALID`. With `"*"`, the assertion runs on every variant that has the snapshot.
- `allowed_changes`: each ledger difference between base code and PR code that the fix may cause. Each one has a `comparison` (`build`, `rescan`, `legacy`, `flip` or `*`), a `path` glob, optional `variants`, and a `reason`. Declare the narrowest path that covers the change.

For a feature rather than a bug, set `"kind": "feature"`. It then needs only `head` assertions.

### UI changes: `ui.spec.mjs`

When `analysis.json` lists `ui_files`, or `plan.json` has `"ui": true`, write
`ui.spec.mjs` from its template. `lock` refuses to continue without it. Each
scenario opens the changed screens on the scenario documents (`ui.openDoc("s0_invoice")`),
does what a user does (`ui.setValue`, `ui.click`, `ui.clickMenu`, `ui.save`), and
calls `ui.capture(name)` after each step that matters.

The run executes the same steps with Playwright on the base code and on the PR
code, against a company built for the browser. A capture records the form's
fields (shown, read-only, mandatory, value), the buttons, dialogs and messages,
and report rows. The verdict compares captures like ledger snapshots: a difference
must be declared with `"comparison": "ui"` and a path such as
`ui.<scenario>.<capture>.form.fields.<fieldname>.read_only`. A new console error,
failed request or failed step under the PR code fails the review. Assertions on
screens use the snapshots `ui_base` and `ui_head`. Screenshots go into the report
for people to read; the verdict never compares pixels.

## 6. Lock and run

```
review.py lock --workdir <workdir>
review.py run --workdir <workdir>
```

Add `--keep-data` only when the user explicitly asked to keep the review data on
the site, for example to open the vouchers in desk. Without it, `run` deletes
every company, transaction, master and user that it created, through ERPNext's
Transaction Deletion Record, and checks that nothing is left.

`run` takes a long time: about one minute for each variant on each code, plus
an asset build and a browser pass on each code when there are UI checks. It
refuses to start if `plan.json`, `s0.py`, `expect.json` or `ui.spec.mjs` changed
since the lock.
Each run gets new companies, named `PR<N>R<run>`.

If `run` is interrupted, run `review.py restore` before anything else. It restores
the settings, the scheduler and the checkout, and deletes the review data unless
the run kept it.

## 7. Report

```
review.py report --workdir <workdir>
```

`report.md` is written for people. It opens with the verdict and a summary in plain
language. It then has the requirement checks with the values on each code, every
change written as a sentence and grouped by scenario, screenshots side by side,
and the technical details folded at the end. The verdict is one of:

| Verdict | Meaning |
| --- | --- |
| `INVALID` | The run is incomplete, a locked file changed after the run, two identical base builds differ, or `expect.json` lacks the required assertions. |
| `NOT REPRODUCED` | A `base` assertion fails: the base code does not show the reported bug. |
| `FAIL` | A `head` assertion fails, an undeclared ledger change appeared, or a new invariant violation appeared under the PR code. |
| `PASS` | Every assertion holds, and every difference is declared. |

The verdict is `verdict.py`'s. Give it to the user unchanged, with the path to
`report.md`, in the same plain language as the report. For
each `FAIL` or `NOT REPRODUCED` check, find the cause in the code and explain it.
To change an expectation after a run, run `lock --reason "<why>"` and then `run`
again. The report lists every lock with its reason.

The report states whether the review data was deleted. If a run kept it, delete it
with `review.py cleanup --workdir <workdir> --run <run>` as soon as the user is
done with it. If cleanup failed, the report says so: run `cleanup` and give the
user its result.

Delete the `review-<N>-base` and `review-<N>-head` branches when the user is done
with them.

## How the run stays deterministic

Read this section when a run is `INVALID`, or when you add to the library.

- **Fixed inputs**: every document posts on `DATE`, with explicit accounts and exchange rates. Reports read as of `REPORT_DATE`.
- **Self-check**: each variant builds two companies on the base code, control (C) and treatment (T). Their snapshots must be identical, or the run is `INVALID`.
- **Comparisons**: `build` compares T with H (built on PR code). `rescan` compares T before and after PR code reads it. `legacy` compares C and T after the same later actions, under base code and PR code. `flip` compares the same for documents posted under one variant and acted on under another.
- **Stable names**: snapshots replace document names with scenario labels, other vouchers with `<Type#k>` in creation order, and the company and its abbreviation with placeholders. Report rows are sorted, and running-balance columns are dropped.
- **No background races**: enqueued jobs run inline during the session, and the scheduler is paused.
- **Browser**: Playwright is pinned. Each UI scenario runs in a fresh browser context with a fixed viewport, locale and timezone, and reduced motion. Every step waits until the network and Frappe's request queue are idle. Times of day are masked, and names are replaced as in the ledger snapshots.
- **Settings caches**: each settings switch has a console session of its own, and every phase checks that the site is on its variant before it starts.
- **Library**: `scripts/library.py` runs in every review. Append new scenarios, and never edit or reorder one in place. A scenario that fails on the base code is a `WARN`, because it gives no coverage.
