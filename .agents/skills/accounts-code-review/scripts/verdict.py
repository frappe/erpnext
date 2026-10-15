"""Mechanical verdict for accounts-code-review. Pure function of the run's files.

Comparisons (per variant v; per flip a-b):
    selfcheck  C-v-built   == T-v-built      both on base code: must be identical, or the run is INVALID
    build      T-v-built   vs H-v-built      same scenarios, base code vs PR code
    rescan     T-v-built   vs T-v-rescan     same data, read by PR code
    legacy     C-v-legacy  vs T-v-legacy     same old data, acted on by base code vs PR code
    flip       FC-a-b-legacy vs FT-a-b-legacy
    ui         ui/base.json vs ui/head.json  the same Playwright scenarios on base code and PR code

Every difference must match an `allowed_changes` entry in expect.json; any other
difference fails. Assertions pin exact values on one snapshot.
"""

import fnmatch
import json
from pathlib import Path

SIDES = {
	"base": "T-{v}-built",
	"head": "H-{v}-built",
	"base_legacy": "C-{v}-legacy",
	"head_legacy": "T-{v}-legacy",
	"ui_base": "ui:base",
	"ui_head": "ui:head",
}
UI_PROBLEMS = ("console_errors", "failed_requests", "error")
VERDICT_ORDER = ["INVALID", "NOT REPRODUCED", "FAIL", "PASS"]


def flatten(snap):
	"""path -> value. Lists stay whole values; their rows are diffed for display only."""
	out = {}
	for top, section in snap.items():
		if isinstance(section, dict):
			for key, value in section.items():
				if top == "docs" and isinstance(value, dict):
					for field, v in value.items():
						out[f"docs.{key}.{field}"] = v
				else:
					out[f"{top}.{key}"] = value
		else:
			out[top] = section
	return out


def diff(a, b):
	fa, fb = flatten(a), flatten(b)
	return {p: (fa.get(p), fb.get(p)) for p in sorted(set(fa) | set(fb)) if not _equal(fa.get(p), fb.get(p))}


def _equal(x, y):
	if isinstance(x, int | float) and isinstance(y, int | float):
		return abs(x - y) <= 0.005
	return x == y


def evaluate(workdir, run_id):
	workdir = Path(workdir)
	rundir = workdir / "runs" / str(run_id)
	plan = json.loads((workdir / "plan.json").read_text())
	expect = json.loads((workdir / "expect.json").read_text())
	run = json.loads((rundir / "run.json").read_text())
	snaps = rundir / "snapshots"

	def load(name):
		if name.startswith("ui:"):
			path = rundir / "ui" / f"{name[3:]}.json"
			return {"ui": json.loads(path.read_text())} if path.exists() else None
		path = snaps / f"{name}.json"
		return json.loads(path.read_text()) if path.exists() else None

	checks, changes, declared_hits = [], [], set()
	allowed = expect.get("allowed_changes", [])

	def check(status, kind, subject, detail, **extra):
		checks.append({"status": status, "kind": kind, "subject": subject, "detail": detail, **extra})

	if run.get("status") != "complete":
		check("INVALID", "run", "run", f"run status is {run.get('status')!r}: {run.get('error', '')}")
	if run.get("lock") != _current_lock(workdir):
		check("INVALID", "lock", "lock", "a locked file or the scripts snapshot changed after the run's lock")

	active = [v for v in plan["variants"] if v["id"] not in run.get("skipped_variants", {})]
	pairs = []
	for v in active:
		vid = v["id"]
		pairs += [
			("selfcheck", vid, f"C-{vid}-built", f"T-{vid}-built"),
			("build", vid, f"T-{vid}-built", f"H-{vid}-built"),
			("rescan", vid, f"T-{vid}-built", f"T-{vid}-rescan"),
			("legacy", vid, f"C-{vid}-legacy", f"T-{vid}-legacy"),
		]
	for a, b in plan["flips"]:
		if a in {v["id"] for v in active} and b in {v["id"] for v in active}:
			pairs += [
				("selfcheck", f"{a}-{b}", f"FC-{a}-{b}-built", f"FT-{a}-{b}-built"),
				("flip", f"{a}-{b}", f"FC-{a}-{b}-legacy", f"FT-{a}-{b}-legacy"),
			]

	for comparison, key, left, right in pairs:
		sa, sb = load(left), load(right)
		if sa is None or sb is None:
			check("INVALID", comparison, key, f"missing snapshot: {left if sa is None else right}")
			continue
		delta = diff(sa, sb)
		if comparison == "selfcheck":
			if delta:
				check(
					"INVALID",
					"selfcheck",
					key,
					f"identical builds on base code differ at {list(delta)[:5]}: the baseline is not deterministic",
				)
			continue
		for path, (before, after) in delta.items():
			rule = _match(allowed, comparison, key, path)
			if rule is not None:
				declared_hits.add(rule)
			changes.append(
				{
					"comparison": comparison,
					"variant": key,
					"path": path,
					"before": before,
					"after": after,
					"declared": rule is not None,
					"reason": allowed[rule]["reason"] if rule is not None else None,
				}
			)
			if rule is None:
				check("FAIL", comparison, f"{key} {path}", "undeclared change")
		new = sorted(set(sb.get("invariants", [])) - set(sa.get("invariants", [])))
		if new:
			check("FAIL", "invariant", f"{comparison} {key}", f"new violations under PR code: {new}")

	if run.get("ui"):
		_ui(load("ui:base"), load("ui:head"), allowed, declared_hits, changes, check)

	for v in active:
		base = load(f"T-{v['id']}-built") or {}
		for sid, outcome in sorted(base.get("outcomes", {}).items()):
			if sid.startswith("build-") and outcome != "ok":
				check(
					"WARN",
					"coverage",
					f"{v['id']} {sid}",
					f"fails on base code, gives no coverage: {outcome}",
				)
		for violation in base.get("invariants", []):
			check("WARN", "invariant", f"{v['id']} base", f"pre-existing: {violation}")

	for i, rule in enumerate(allowed):
		if i not in declared_hits:
			check("WARN", "declared", rule["path"], f"declared change not observed ({rule['comparison']})")

	_assertions(expect, active, run.get("skipped_variants", {}), load, check)

	statuses = {c["status"] for c in checks}
	verdict = next((s for s in VERDICT_ORDER[:-1] if s in statuses), "PASS")
	return {"verdict": verdict, "checks": checks, "changes": changes}


def flatten_deep(value, prefix):
	"""Dicts recurse into dotted paths; lists and scalars are leaves."""
	if isinstance(value, dict) and value:
		out = {}
		for key, child in value.items():
			out.update(flatten_deep(child, f"{prefix}.{key}"))
		return out
	return {prefix: value}


def _ui(base, head, allowed, declared_hits, changes, check):
	if base is None or head is None:
		check(
			"INVALID", "ui", "ui", "missing UI results for " + ("base" if base is None else "head") + " code"
		)
		return
	base, head = base["ui"], head["ui"]
	for sid in sorted(set(base) | set(head)):
		b, h = base.get(sid, {}), head.get(sid, {})
		if b.get("error"):
			check("WARN", "coverage", f"ui {sid}", f"UI scenario fails on base code: {b['error']}")
		if h.get("error") and h.get("error") != b.get("error"):
			check("FAIL", "ui", f"ui {sid}", f"UI scenario fails on PR code: {h['error']}")
		for kind in ("console_errors", "failed_requests"):
			new = sorted(set(h.get(kind, [])) - set(b.get(kind, [])))
			gone = sorted(set(b.get(kind, [])) - set(h.get(kind, [])))
			if new:
				check("FAIL", "ui", f"ui {sid}", f"new {kind.replace('_', ' ')} on PR code: {new}")
			if gone:
				check("PASS", "ui", f"ui {sid}", f"{kind.replace('_', ' ')} gone on PR code: {gone}")
		fb = flatten_deep({k: v for k, v in b.get("captures", {}).items()}, f"ui.{sid}")
		fh = flatten_deep({k: v for k, v in h.get("captures", {}).items()}, f"ui.{sid}")
		for path in sorted(set(fb) | set(fh)):
			if _equal(fb.get(path), fh.get(path)):
				continue
			rule = _match(allowed, "ui", "v0", path)
			if rule is not None:
				declared_hits.add(rule)
			changes.append(
				{
					"comparison": "ui",
					"variant": "v0",
					"path": path,
					"before": fb.get(path),
					"after": fh.get(path),
					"declared": rule is not None,
					"reason": allowed[rule]["reason"] if rule is not None else None,
				}
			)
			if rule is None:
				check("FAIL", "ui", f"v0 {path}", "undeclared change")


def _assertions(expect, active, skipped, load, check):
	"""Evaluate every assertion. A required side passes only if one of its assertions ran.

	A variant the run skipped had the same settings as the site default, so its
	assertions run against v0. An unknown variant id makes the review INVALID.
	"""
	order = [v["id"] for v in active]
	ran = {"base": 0, "head": 0}
	for a in expect.get("assertions", []):
		wanted = order if a.get("variants", "*") == "*" else a["variants"]
		targets = set()
		for vid in wanted:
			if vid in order:
				targets.add(vid)
			elif vid in skipped:
				targets.add("v0")
			else:
				check("INVALID", "assertion", a["path"], f"assertion names unknown variant {vid!r}")
		if a["snapshot"].startswith("ui_"):
			targets &= {"v0"}  # the browser runs in the default variant only
		for vid in sorted(targets, key=order.index):
			snap = load(SIDES[a["snapshot"]].format(v=vid))
			if a["snapshot"].startswith("ui_"):
				actual = flatten_deep(snap["ui"], "ui").get(a["path"]) if snap else "<missing UI results>"
			else:
				actual = flatten(snap).get(a["path"]) if snap else "<missing snapshot>"
			side = "base" if a["snapshot"] in ("base", "ui_base") else "head"
			if a["snapshot"] in ("base", "ui_base", "head", "ui_head"):
				ran[side] += 1
			passed = _equal(actual, a["equals"])
			status = (
				"PASS" if passed else ("NOT REPRODUCED" if a["snapshot"] in ("base", "ui_base") else "FAIL")
			)
			detail = (
				f"= {actual!r}" if passed else f"want {a['equals']!r}, got {actual!r} ({a.get('why', '')})"
			)
			check(
				status,
				"assertion",
				f"{vid} {a['snapshot']} {a['path']}",
				detail,
				assertion=a,
				actual=actual,
				variant=vid,
			)

	if expect.get("kind", "bug") == "bug" and not ran["base"]:
		check(
			"INVALID", "assertion", "expect.json", "no 'base' assertion ran: a bug review must show Reported"
		)
	if not ran["head"]:
		check(
			"INVALID",
			"assertion",
			"expect.json",
			"no 'head' or 'ui_head' assertion ran: the review must show Expected",
		)


def _match(allowed, comparison, key, path):
	for i, rule in enumerate(allowed):
		if rule["comparison"] not in ("*", comparison):
			continue
		if rule.get("variants", "*") != "*" and key not in rule["variants"]:
			continue
		if fnmatch.fnmatchcase(path, rule["path"]):
			return i
	return None


def _current_lock(workdir):
	lock = Path(workdir, "lock.json")
	if not lock.exists():
		return None
	from review import file_hashes  # same hashing as the lock command

	return file_hashes(workdir)
