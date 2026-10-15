"""Human-readable report.md for accounts-code-review. Pure function of the run's files.

Plain language first: the verdict in one sentence, a summary a reviewer can act
on, then every change as a sentence. Raw paths, hashes and logs go last, folded.
"""

import difflib
import json
from pathlib import Path

VERDICT_SENTENCE = {
	"PASS": "The PR does what the requirement asks, and nothing else in the ledger or on screen changed unexpectedly.",
	"FAIL": "The PR does not hold up: see the failed checks below.",
	"NOT REPRODUCED": "The reported problem does not happen on the base code with the data in s0.py, so the fix could not be proven.",
	"INVALID": "This run cannot give a verdict: see the reasons below and run again.",
}
WHEN = {
	"build": "when the documents are created with the PR code",
	"rescan": "when the PR code reads documents created with the base code",
	"legacy": "when the PR code later acts on documents created with the base code (cancel, return, pay, reconcile)",
	"flip": "when a setting is changed after posting, and the PR code then acts on the documents",
	"ui": "on screen",
}
ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "NOT REPRODUCED": "❌", "INVALID": "⛔"}


def render(workdir, state, record, result):
	w = Path(workdir)
	rundir = w / "runs" / str(record["run_id"])
	ctx = _Context(w, rundir, record)
	pr, plan, analysis = _read(w / "pr.json"), _read(w / "plan.json"), _read(w / "analysis.json")

	out = [f"# Review of PR #{state['pr']}: {pr['title']}", ""]
	out += [
		f"> {ICON.get(result['verdict'], '')} **{result['verdict']}** — {VERDICT_SENTENCE[result['verdict']]}",
		"",
	]
	out += _summary(ctx, result, plan, record)
	out += _section("What the requirement says", _text(w / "requirement.md"))
	out += _requirement_checks(ctx, result)
	out += _blockers(ctx, result)
	out += _changes(ctx, result, declared=False)
	out += _changes(ctx, result, declared=True)
	out += _ui(ctx, record)
	out += _scenarios(ctx, rundir)
	out += _settings(ctx, plan, analysis, record)
	out += _blast_radius(analysis)
	out += _section("Code review", _text(w / "code-review.md"))
	out += _warnings(result)
	out += _technical(w, state, record, result, plan)
	return "\n".join(out) + "\n"


# ---------------------------------------------------------------- sections


def _summary(ctx, result, plan, record):
	assertions = [c for c in result["checks"] if c["kind"] == "assertion" and "assertion" in c]
	base = [c for c in assertions if c["assertion"]["snapshot"] in ("base", "ui_base")]
	head = [c for c in assertions if c["assertion"]["snapshot"] not in ("base", "ui_base")]
	undeclared = [c for c in result["changes"] if not c["declared"]]
	new_invariants = [c for c in result["checks"] if c["kind"] == "invariant" and c["status"] == "FAIL"]
	ui_fail = [c for c in result["checks"] if c["kind"] == "ui" and c["status"] == "FAIL"]
	ran = [v for v in plan["variants"] if v["id"] not in record.get("skipped_variants", {})]
	lines = ["## Summary", ""]
	if base:
		lines.append(
			_bullet(
				all(c["status"] == "PASS" for c in base),
				"The reported problem happens on the base code.",
				"The reported problem did not happen on the base code.",
			)
		)
	if head:
		ok = sum(c["status"] == "PASS" for c in head)
		lines.append(
			_bullet(
				ok == len(head),
				f"The PR gives the expected result ({ok} of {len(head)} checks).",
				f"The PR gives the expected result in only {ok} of {len(head)} checks.",
			)
		)
	lines.append(
		_bullet(
			not undeclared,
			"Nothing else changed in the ledger, the reports or on screen.",
			f"{len(undeclared)} unexpected change(s) in {len({ctx.subject(c) for c in undeclared})} place(s).",
		)
	)
	lines.append(
		_bullet(
			not new_invariants,
			"The ledger stays consistent (balanced vouchers, matching outstanding amounts).",
			f"{len(new_invariants)} new ledger inconsistency(ies) under the PR code.",
		)
	)
	if record.get("ui"):
		lines.append(
			_bullet(
				not ui_fail,
				"The changed screens work without new errors.",
				f"{len(ui_fail)} UI problem(s) under the PR code.",
			)
		)
	skipped = len(record.get("skipped_variants", {}))
	lines.append(
		f"- {'⚠️' if record.get('data') != 'deleted' else '🧹'} Review data on the site: {_data_state(record)}."
	)
	lines.append(
		f"- ℹ️ Tested with {len(ran)} setting combination(s){f' ({skipped} skipped: same as the site default)' if skipped else ''}, {len(ctx.scenarios)} scenario(s), on site `{record['site']}`."
	)
	return [*lines, ""]


def _requirement_checks(ctx, result):
	rows = {}
	for c in result["checks"]:
		if c["kind"] != "assertion" or "assertion" not in c:
			continue
		a = c["assertion"]
		side = "base" if a["snapshot"] in ("base", "ui_base", "base_legacy") else "head"
		row = rows.setdefault(
			(a["path"], c["variant"]),
			{"path": a["path"], "what": ctx.describe(a["path"]), "variant": ctx.variant(c["variant"])},
		)
		row[side] = (c["actual"], a["equals"], c["status"], a["why"])
	if not rows:
		return []
	lines = [
		"## Checks against the requirement",
		"",
		"| What | Settings | Base code | PR code |",
		"| --- | --- | --- | --- |",
	]
	for _, row in sorted(rows.items()):
		cells = []
		for side in ("base", "head"):
			if side not in row:
				cells.append("—")
				continue
			actual, want, status, why = row[side]
			mark = "✅" if status == "PASS" else "❌"
			show = _outcome if row["path"].startswith("outcomes.") else _fmt
			cells.append(
				f"{mark} {show(actual)}"
				+ ("" if status == "PASS" else f" (expected {show(want)})")
				+ f"<br><sub>{_esc(why)}</sub>"
			)
		lines.append(f"| {row['what']} | {row['variant']} | {cells[0]} | {cells[1]} |")
	return [*lines, ""]


def _blockers(ctx, result):
	items = [
		c
		for c in result["checks"]
		if c["status"] in ("INVALID",)
		or (c["status"] == "FAIL" and c["kind"] in ("invariant", "ui") and "undeclared" not in c["detail"])
	]
	if not items:
		return []
	lines = ["## Problems that block the verdict", ""]
	for c in items:
		lines.append(f"- {ICON[c['status']]} {_esc(c['detail'])} <sub>({c['kind']}: {c['subject']})</sub>")
	return [*lines, ""]


def _changes(ctx, result, declared):
	changes = [c for c in result["changes"] if c["declared"] == declared]
	title = "Expected changes (declared in expect.json)" if declared else "Unexpected changes"
	if not changes:
		return (
			[]
			if declared
			else [f"## {title}", "", "None. Every comparison between base code and PR code matched.", ""]
		)
	lines = [f"## {title}", ""]
	if not declared:
		lines += [
			"Each item below differs between the base code and the PR code, and expect.json does not allow it. Each one fails the review until it is explained.",
			"",
		]
	groups = {}
	for c in changes:
		groups.setdefault(ctx.subject(c), []).append(c)
	for subject, items in sorted(groups.items()):
		lines += [f"**{subject}**", ""]
		for c in items:
			sentence = ctx.sentence(c)
			lines.append(f"- {sentence}" + (f" — _{_esc(c['reason'])}_" if declared else ""))
		lines.append("")
	return lines


def _ui(ctx, record):
	if not record.get("ui"):
		return []
	base, head = _read_or(ctx.rundir / "ui" / "base.json", {}), _read_or(ctx.rundir / "ui" / "head.json", {})
	lines = [
		"## Screens (Playwright)",
		"",
		"Each screen ran once on the base code and once on the PR code. Screenshots are for reading only; the verdict compares the recorded state.",
		"",
	]
	for sid in sorted(set(base) | set(head)):
		b, h = base.get(sid, {}), head.get(sid, {})
		lines += [f"### {b.get('title') or h.get('title') or sid}", ""]
		for side, data in (("Base code", b), ("PR code", h)):
			problems = [*data.get("console_errors", []), *data.get("failed_requests", [])]
			if data.get("error"):
				problems.insert(0, f"step failed: {data['error']}")
			if problems:
				lines.append(f"- {side}: " + "; ".join(_esc(p) for p in problems))
		captures = sorted(set(b.get("captures", {})) | set(h.get("captures", {})))
		if captures:
			lines += ["", "| Step | Base code | PR code |", "| --- | --- | --- |"]
			for cap in captures:
				img = lambda side: f"![{side}](runs/{record['run_id']}/ui/{side}/{sid}--{cap}.png)"  # noqa: E731
				lines.append(f"| {cap} | {img('base')} | {img('head')} |")
		lines.append("")
	return lines


def _scenarios(ctx, rundir):
	preflight = _read_or(rundir / "preflight.json", {})
	lines = [
		"## Scenarios",
		"",
		"Every scenario ran in every setting combination, on both codes.",
		"",
		"| Scenario | Source | On base code |",
		"| --- | --- | --- |",
	]
	for sid, meta in ctx.scenarios.items():
		outcome = preflight.get(f"build-{sid}", "?")
		status = "✅ created" if outcome == "ok" else f"⚠️ {_esc(_short(outcome, 120))}"
		lines.append(
			f"| {_esc(meta['title'])} | {'requirement (s0.py)' if meta['source'] == 's0' else 'fixed library'} | {status} |"
		)
	return [*lines, ""]


def _settings(ctx, plan, analysis, record):
	lines = ["## Settings tested", "", "| Combination | Ran |", "| --- | --- |"]
	for v in plan["variants"]:
		lines.append(
			f"| {_esc(ctx.variant(v['id']))} | {record.get('skipped_variants', {}).get(v['id'], 'yes')} |"
		)
	if plan["flips"]:
		lines += [
			"",
			"Changed after posting (documents created under the first, then acted on under the second):",
			"",
		]
		lines += [f"- {_esc(ctx.variant(a))} → {_esc(ctx.variant(b))}" for a, b in plan["flips"]]
	not_varied = [s for s in analysis["settings"] if s["values"] is None]
	if not_varied:
		lines += [
			"",
			"Read by the changed code but not varied (not a yes/no or choice field): "
			+ ", ".join(f"{s['doctype']} > {s.get('label') or s['field']}" for s in not_varied)
			+ ".",
		]
	return [*lines, ""]


def _blast_radius(analysis):
	lines = ["## What the PR touches", ""]
	for s in analysis["symbols"]:
		path, _, func = s["symbol"].partition(":")
		c = s["callers"]
		if c["kind"] == "lifecycle":
			who = "called by the framework (document event)"
		elif c["kind"] == "module":
			who = "module-level code"
		elif c["kind"] == "widely_used":
			who = f"called from {c['count']} places"
		elif not c["callers"]:
			who = "no callers found"
		else:
			who = f"called from {c['count']} place(s): " + ", ".join(
				f"`{x.split(' ', 1)[-1]}` ({x.split(' ', 1)[0].split('/')[-1]})" for x in c["callers"][:8]
			)
		lines.append(f"- `{func}` in `{path}` — {who}")
	if analysis.get("test_files"):
		lines.append(f"- Tests changed by the PR: {', '.join(f'`{p}`' for p in analysis['test_files'])}")
	if analysis.get("ui_files"):
		lines.append(f"- UI files: {', '.join(f'`{p}`' for p in analysis['ui_files'])}")
	return [*lines, ""]


def _warnings(result):
	warns = [c for c in result["checks"] if c["status"] == "WARN"]
	if not warns:
		return []
	return ["## Warnings", "", *[f"- ⚠️ {_esc(c['detail'])} <sub>({c['subject']})</sub>" for c in warns], ""]


def _technical(w, state, record, result, plan):
	lock = _read(w / "lock.json")
	gen = (w / "plan.generated.json").read_text().splitlines()
	cur = (w / "plan.json").read_text().splitlines()
	edits = list(difflib.unified_diff(gen, cur, "plan.generated.json", "plan.json", lineterm=""))
	lines = [
		"## Technical details",
		"",
		"<details><summary>Inputs, locks, plan edits, every check</summary>",
		"",
	]
	lines += [
		f"- Requirement source: {state['requirement']}",
		f"- Base commit: `{record['base_sha']}`",
		f"- Base + PR: `{record['head_sha']}` (PR head `{state['pr_head_sha']}`)",
		f"- Run {record['run_id']}: {record['status']}, {len(record['sessions'])} sessions, logs in `runs/{record['run_id']}/logs/`",
		f"- Review data on `{record['site']}` (companies starting with `{record['prefix']} `): {_data_state(record)}",
		"",
		"Locks:",
		"",
		*[f"- {h['at']}: {h['reason']}" for h in lock["history"]],
		"",
		"Plan edits by the agent:",
		"",
		*(["```diff", *edits, "```"] if edits else ["None."]),
		"",
		"| Status | Kind | Subject | Detail |",
		"| --- | --- | --- | --- |",
	]
	for c in result["checks"]:
		lines.append(
			f"| {c['status']} | {c['kind']} | `{_esc(c['subject'])}` | {_esc(_short(c['detail'], 200))} |"
		)
	if record.get("cleanup_errors"):
		lines += ["", f"**Cleanup errors — run `review.py restore`:** {_esc(str(record['cleanup_errors']))}"]
	return [*lines, "", "</details>"]


# ---------------------------------------------------------------- language


class _Context:
	def __init__(self, workdir, rundir, record):
		self.rundir = rundir
		self.record = record
		self.scenarios = {s["id"]: s for s in _read_or(rundir / "scenarios.json", [])}  # run order
		self.labels = _read_or(rundir / "labels.json", {})
		self.plan = _read(workdir / "plan.json")
		self.ui = {**_read_or(rundir / "ui" / "base.json", {}), **_read_or(rundir / "ui" / "head.json", {})}

	def variant(self, vid):
		if "-" in vid:
			a, b = vid.split("-", 1)
			return f"{self.variant(a)} → {self.variant(b)}"
		label = next((v["label"] for v in self.plan["variants"] if v["id"] == vid), vid)
		return "site defaults" if label == "default" else label

	def scenario_of(self, label):
		label = label.strip("<>")
		sid = self.labels.get(label) or (label if label in self.scenarios else None)
		return self.scenarios.get(sid, {}).get("title") if sid else None

	def subject(self, change):
		parts = change["path"].split(".")
		if parts[0] == "ui":
			return f"Screen: {self.ui.get(parts[1], {}).get('title', parts[1])}"
		if parts[0] in ("docs", "gl", "ple"):
			return self.scenario_of(parts[1]) or f"Document {parts[1]}"
		if parts[0] == "outcomes":
			sid = parts[1].split("-", 1)[-1]
			return self.scenarios.get(sid, {}).get("title") or self.scenario_of(sid) or "Actions"
		if parts[0] == "reports":
			return f"Report: {parts[1].replace('_', ' ').title()}"
		if parts[0] == "balances":
			return "Account balances"
		return "Ledger checks"

	def describe(self, path):
		parts = path.split(".")
		head = parts[0]
		if head == "docs" and len(parts) == 3:
			return f"{_title(parts[2])} of `{parts[1]}`"
		if head == "balances":
			return f"Balance of account {'.'.join(parts[1:])}"
		if head == "gl":
			return f"General ledger entries of `{parts[1].strip('<>')}`"
		if head == "ple":
			return f"Payment ledger entries of `{parts[1].strip('<>')}`"
		if head == "outcomes":
			return f"Result of `{parts[1]}`"
		if head == "reports":
			return f"Rows of the {_title(parts[1])} report"
		if head == "ui" and len(parts) >= 3:
			return _ui_describe(parts)
		return f"`{path}`"

	def sentence(self, c):
		when = WHEN[c["comparison"]]
		setting = "" if c["variant"] == "v0" else f" with *{_esc(self.variant(c['variant']))}*"
		what, before, after = self.describe(c["path"]), c["before"], c["after"]
		if c["path"].startswith(("gl.", "ple.")):
			return f"{what}{setting}, {when}: {_rows_delta(before, after)}"
		if c["path"].startswith("reports."):
			return f"{what}{setting}, {when}: {_rows_delta(before, after)}"
		if c["path"].startswith("outcomes."):
			return f"{what}{setting}, {when}: {_outcome(before)} → {_outcome(after)}"
		if c["path"] == "invariants":
			return f"Ledger checks{setting}, {when}: {_rows_delta(before, after)}"
		return f"{what}{setting}, {when}: {_fmt(before)} → {_fmt(after)}"


def _data_state(record):
	state = record.get("data")
	if record.get("keep_data") and state != "deleted":
		return f"kept on request; delete it with `review.py cleanup --run {record['run_id']}`"
	if state == "deleted":
		return "deleted after the run"
	return f"**not deleted** ({state or 'cleanup did not run'}); run `review.py cleanup --run {record['run_id']}`"


def _ui_describe(parts):
	# ui.<scenario>.<capture>.form.fields.<field>.<prop> and similar
	cap = parts[2]
	rest = parts[3:]
	if rest[:2] == ["form", "fields"] and len(rest) >= 4:
		prop = {"visible": "shown", "read_only": "read-only", "reqd": "mandatory", "value": "value"}.get(
			rest[3], rest[3]
		)
		return f"At step '{cap}', field {_title(rest[2])} ({prop})"
	return f"At step '{cap}', {' '.join(_title(p) for p in rest)}"


def _rows_delta(before, after):
	if not isinstance(before, list) or not isinstance(after, list):
		return f"{_fmt(before)} → {_fmt(after)}"
	b = [json.dumps(r, sort_keys=True) for r in before]
	a = [json.dumps(r, sort_keys=True) for r in after]
	removed = [json.loads(r) for r in b if r not in a]
	added = [json.loads(r) for r in a if r not in b]
	parts = []
	if removed:
		parts.append(f"{len(removed)} row(s) removed")
	if added:
		parts.append(f"{len(added)} row(s) added")
	detail = [f"<br>&nbsp;&nbsp;− {_row(r)}" for r in removed[:4]] + [
		f"<br>&nbsp;&nbsp;+ {_row(r)}" for r in added[:4]
	]
	return (", ".join(parts) or "same rows, different order") + "".join(detail)


def _row(row):
	if not isinstance(row, dict):
		return _esc(_short(json.dumps(row, default=str), 140))
	if "debit" in row or "credit" in row:
		side = f"Dr {_fmt(row.get('debit'))}" if row.get("debit") else f"Cr {_fmt(row.get('credit'))}"
		party = f", party {row['party']}" if row.get("party") else ""
		cancelled = ", cancelled" if row.get("is_cancelled") else ""
		return _esc(f"{row.get('account')} {side}{party}{cancelled}")
	if "amount" in row:
		return _esc(
			f"{row.get('account')} {_fmt(row.get('amount'))} against {row.get('against_voucher_no')}{', delinked' if row.get('delinked') else ''}"
		)
	keys = [
		k
		for k in (
			"voucher_no",
			"account",
			"party",
			"outstanding",
			"debit",
			"credit",
			"closing_debit",
			"closing_credit",
		)
		if k in row
	]
	return _esc(
		", ".join(f"{_title(k)} {_fmt(row[k])}" for k in keys) or _short(json.dumps(row, default=str), 140)
	)


def _outcome(value):
	if value is None:
		return "not run"
	return "succeeded" if value == "ok" else f"failed ({_esc(_short(value, 140))})"


def _fmt(value):
	if value is None:
		return "empty"
	if isinstance(value, bool):
		return "yes" if value else "no"
	if isinstance(value, int | float):
		return f"{value:,.2f}"
	if isinstance(value, list):
		return f"{len(value)} item(s)"
	if isinstance(value, dict):
		return _esc(_short(json.dumps(value, default=str), 120))
	return _esc(_short(str(value), 120))


def _title(name):
	return name.replace("_", " ").strip().capitalize()


def _bullet(ok, good, bad):
	return f"- {'✅' if ok else '❌'} {good if ok else bad}"


def _section(title, body):
	return [f"## {title}", "", body or "_Not written._", ""]


def _text(path):
	return path.read_text().strip() if path.exists() else None


def _esc(text):
	"""Table-safe text; <label> placeholders stay visible instead of parsing as HTML."""
	return (
		str(text)
		.replace("&", "&amp;")
		.replace("<", "&lt;")
		.replace(">", "&gt;")
		.replace("|", "\\|")
		.replace("\n", " ")
	)


def _short(text, n):
	text = str(text)
	return text if len(text) <= n else text[: n - 1] + "…"


def _read(path):
	return json.loads(Path(path).read_text())


def _read_or(path, default):
	return _read(path) if Path(path).exists() else default
