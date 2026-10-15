# accounts-code-review

This skill reviews an ERPNext pull request that changes the Accounts module. It
compares the pull request with its GitHub issue or support ticket, runs a code
review, and posts the same documents on a bench site under the base code and the
pull request code. It then compares the two ledgers and writes `report.md`.

This file lists what you need before you run it. `SKILL.md` has the procedure
that the agent follows.

## What you give the agent

- The pull request, as a number or a URL.
- The requirement source: a GitHub issue URL, or the text of a support ticket.
- The name of the site to use.

## Versions

The skill reviews pull requests for any ERPNext version: `develop`,
`version-15-hotfix`, `version-16-hotfix` and the other release branches. The
review uses the base branch of the pull request.

The bench and the site must run the same major version as that base branch. For
example, a pull request to `version-15-hotfix` needs a bench on Frappe v15 and a
site with ERPNext v15. `init` compares the three versions and stops if they do
not match. A site cannot migrate down to an older major version.

The skill is in the ERPNext `develop` branch. To review a pull request for an
older version, run the skill from a `develop` checkout or from an installed copy.
Then give the bench of that version with `--bench`.

| Version | Status |
| --- | --- |
| develop (v17) | Tested |
| v15 | Tested |
| v16 | Not tested yet |
| v14 and older | Not tested |

## Requirements

### Bench and site

- A Frappe bench with ERPNext in `apps/erpnext`, as a git checkout. The bench must run the same major version as the base branch of the pull request.
- No uncommitted changes to tracked files in `apps/erpnext`.
- A site with ERPNext installed and the setup wizard complete, on the same major version.
- The database and Redis must run. `bench start` starts them.
- Use a development site, not a production site. The run changes the site while it runs.

### Tools

| Tool | Version | Check |
| --- | --- | --- |
| `git` | any | `git --version` |
| GitHub CLI `gh`, signed in | any | `gh auth status` |
| Python | 3.10 or later | `python3 --version` |
| `bench` | any | `bench --site <site> list-apps` |
| Node.js and npm (UI changes only) | Node.js 18 or later | `node --version` |

The scripts use only the Python standard library. If `bench` is not on the
`PATH`, give its path with `--bench-cmd`.

### Network

- Access to `github.com`, to get the pull request, its base branch and the issue.
- For UI changes only: access to the npm registry and the Playwright download
  server. The first run installs Playwright 1.49.1 and Chromium in the work
  directory.

### Agent

- An agent that reads skills from `.agents/skills/`. To install the skill
  somewhere else, use `npx skills add frappe/erpnext --skill accounts-code-review`.
- The `frappe-code-review` skill. Install it with
  `npx skills add frappe/skills --skill frappe-code-review`.

## What the run does to the site

The run changes the site and the bench, and undoes the changes when it stops:

- It switches `apps/erpnext` to a review branch. This changes the code for every site on the bench.
- It runs `bench migrate` on the base code. It runs it again on the pull request code if the pull request changes DocType JSON, `patches.txt` or `hooks.py`.
- It pauses the scheduler.
- It changes settings (for example, Accounts Settings) to each value it tests.
- It creates companies, masters and documents. At the end, it deletes them.
- For UI changes: it builds the ERPNext assets and starts a web server on a free local port. It also creates the user `review-ui@example.com`.

At the end, the run restores the settings, the scheduler, the branch and the
assets. It also deletes the data that it created. To keep the data, give
`--keep-data` to `run`.

The migrations are not undone. If the pull request adds a column, the column
stays on the site.

## Time

A run takes about one minute for each settings combination on each code. A pull
request that reads three yes/no settings runs four combinations: the site
defaults, and each setting switched. That run takes about eight minutes. Each
setting that changes after posting adds a short pass. UI checks add an asset
build and a browser pass on each code.

## Commands

The agent runs these commands. You can also run them yourself, from any
directory:

```
python3 <skill dir>/scripts/review.py init --workdir /tmp/review-<N> --pr <N> --requirement <issue URL or ticket ref> --site <site> --bench <bench path>
python3 <skill dir>/scripts/review.py analyze --workdir /tmp/review-<N>
python3 <skill dir>/scripts/review.py lock --workdir /tmp/review-<N>
python3 <skill dir>/scripts/review.py run --workdir /tmp/review-<N>
python3 <skill dir>/scripts/review.py report --workdir /tmp/review-<N>
```

Before `lock`, write `requirement.md`, `code-review.md`, `s0.py` and
`expect.json` in the work directory. If the pull request changes UI files, also
write `ui.spec.mjs`. `SKILL.md` explains each file.

If a run stops before it ends, run `review.py restore --workdir /tmp/review-<N>`.
To delete the data of a run that kept it, run
`review.py cleanup --workdir /tmp/review-<N> --run <run>`.
