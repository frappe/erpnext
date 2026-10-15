"""Static analysis of a PR: changed symbols, callers, settings read, and the generated plan.

Pure function of (app checkout, base sha, head sha, app list): no site, no agent.
Same inputs give byte-identical analysis.json and plan.generated.json.
"""

import ast
import json
import re
import subprocess
from pathlib import Path

# Called by the framework, not by name: report them as lifecycle, do not search callers.
LIFECYCLE = {
	"validate",
	"before_validate",
	"before_save",
	"before_insert",
	"after_insert",
	"on_update",
	"before_submit",
	"on_submit",
	"before_cancel",
	"on_cancel",
	"on_trash",
	"after_delete",
	"on_update_after_submit",
	"before_update_after_submit",
	"autoname",
	"onload",
	"on_change",
	"before_naming",
	"execute",
	"get_data",
	"get_columns",
	"__init__",
	"run",
	"get",
	"set",
}
WIDELY_USED = 150  # more callers than this: report the count, not the list
SETTINGS_SUFFIX = " Settings"
COMPANY_GETTERS = {"get_cached_value", "get_value", "db_get"}
KNOWN_HELPERS = {"is_perpetual_inventory_enabled": ("Company", "enable_perpetual_inventory")}
PRECISION_SETTINGS = {
	("System Settings", "currency_precision"): ["", "2", "4"],
	("System Settings", "float_precision"): ["", "2", "4"],
	("System Settings", "rounding_method"): None,  # None: use the Select options
}
PRECISION_HINT = re.compile(r"precision|round", re.I)
# Files whose change a user sees: client code, templates, styles, and the JSON
# that lays out forms, print formats, reports and workspaces.
UI_EXTENSIONS = (".js", ".ts", ".mjs", ".vue", ".html", ".jinja", ".css", ".scss", ".less")
UI_JSON = re.compile(
	r"/(doctype|print_format|report|workspace|form_tour|dashboard_chart|number_card)/[^/]+/[^/]+\.json$"
)
DEFAULT_PROFILE = {"country": "United States", "currency": "USD", "chart_of_accounts": "Standard"}


def git(app, *args):
	return subprocess.run(["git", "-C", str(app), *args], capture_output=True, text=True, check=True).stdout


# ---------------------------------------------------------------- changed symbols


def changed_lines(app, base, head):
	"""{path: {"base": set(lines), "head": set(lines), "text": [changed line text]}}"""
	out, path = {}, None
	for line in git(app, "diff", "-U0", "--no-color", base, head).splitlines():
		if line.startswith("+++ "):
			path = None if line.endswith("/dev/null") else line[6:]
			if path:
				out.setdefault(path, {"base": set(), "head": set(), "text": []})
		elif line.startswith("--- ") and line.endswith("/dev/null"):
			continue
		elif line.startswith("--- "):
			path = line[6:]
			out.setdefault(path, {"base": set(), "head": set(), "text": []})
		elif line.startswith("@@") and path:
			m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
			b, bn, h, hn = int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)
			out[path]["base"].update(range(b, b + bn))
			out[path]["head"].update(range(h, h + hn))
		elif path and line[:1] in "+-" and not line.startswith(("+++", "---")):
			out[path]["text"].append(line[1:])
	return out


def functions(source):
	"""[(qualname, node)] for every function, nested names joined by '.'."""
	try:
		return functions_from_tree(ast.parse(source))
	except SyntaxError:
		return []


def enclosing(funcs, lines):
	"""Innermost function per changed line; "<module>" for lines outside any function."""
	hit = set()
	for line in lines:
		inner = [(n.end_lineno - n.lineno, q) for q, n in funcs if n.lineno <= line <= n.end_lineno]
		hit.add(min(inner)[1] if inner else "<module>")
	return hit


def show(app, sha, path):
	try:
		return git(app, "show", f"{sha}:{path}")
	except subprocess.CalledProcessError:
		return ""


# ---------------------------------------------------------------- index of all apps


class Index:
	"""Every function in every app: what it calls, and where it is defined."""

	def __init__(self, apps_dir, apps):
		self.calls = []  # (file, qualname, line, called names)
		self.defs = {}  # simple name -> [(module path, qualname, file)]
		self.strings = []  # (file, line, dotted string)
		for app in apps:
			root = Path(apps_dir, app)
			for file in sorted(root.rglob("*.py")):
				if any(part in {"node_modules", ".git", "tests"} for part in file.parts) or "/test_" in str(
					file
				):
					continue
				self._index(file, root.parent)

	def _index(self, file, apps_root):
		try:
			tree = ast.parse(file.read_text(errors="ignore"))
		except (SyntaxError, ValueError):
			return
		rel = str(file.relative_to(apps_root))
		module = _module_path(file, apps_root)
		for qual, node in functions_from_tree(tree):
			names = {_call_name(c) for c in ast.walk(node) if isinstance(c, ast.Call)} - {None}
			self.calls.append((rel, qual, node.lineno, names))
			self.defs.setdefault(qual.split(".")[-1], []).append((module, qual, rel))
		for node in ast.walk(tree):
			if (
				isinstance(node, ast.Constant)
				and isinstance(node.value, str)
				and re.fullmatch(r"[\w.]+\.\w+", node.value)
			):
				self.strings.append((rel, node.lineno, node.value))


def functions_from_tree(tree):
	found = []

	def walk(node, prefix):
		for child in ast.iter_child_nodes(node):
			if isinstance(child, ast.ClassDef):
				walk(child, f"{prefix}{child.name}.")
			elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
				found.append((f"{prefix}{child.name}", child))
				walk(child, f"{prefix}{child.name}.")

	walk(tree, "")
	return found


def _module_path(file, apps_root):
	parts = list(file.relative_to(apps_root).with_suffix("").parts)[1:]  # drop the repo dir
	return ".".join(p for p in parts if p != "__init__")


def _call_name(call):
	f = call.func
	if isinstance(f, ast.Name):
		return f.id
	if isinstance(f, ast.Attribute):
		return f.attr
	return None


def callers(index, simple_name, dotted):
	if simple_name in LIFECYCLE:
		return {"kind": "lifecycle", "callers": []}
	found = sorted(f"{file}:{line} {qual}" for file, qual, line, names in index.calls if simple_name in names)
	found += sorted(f"{file}:{line} (string reference)" for file, line, s in index.strings if s == dotted)
	if len(found) > WIDELY_USED:
		return {"kind": "widely_used", "count": len(found), "callers": []}
	return {"kind": "callers", "count": len(found), "callers": found}


# ---------------------------------------------------------------- settings


def settings_read(node):
	"""{(doctype, field)} read inside a function body."""
	found, settings_vars = set(), {}
	for n in ast.walk(node):
		if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
			dt = _settings_doc(n.value)
			if dt:
				for t in n.targets:
					if isinstance(t, ast.Name):
						settings_vars[t.id] = dt
	for n in ast.walk(node):
		if isinstance(n, ast.Call):
			name, args = _call_name(n), [_const(a) for a in n.args]
			if name == "get_single_value" and len(args) >= 2 and args[0] and args[1]:
				found.add((args[0], args[1]))
			elif name in COMPANY_GETTERS and args and args[0] == "Company" and len(n.args) >= 3:
				for field in _const_list(n.args[2]):
					found.add(("Company", field))
			elif name == "get_system_settings" and args and args[0]:
				found.add(("System Settings", args[0]))
			elif name in KNOWN_HELPERS:
				found.add(KNOWN_HELPERS[name])
		elif isinstance(n, ast.Attribute):
			if isinstance(n.value, ast.Name) and n.value.id in settings_vars:
				found.add((settings_vars[n.value.id], n.attr))
			elif isinstance(n.value, ast.Call) and _settings_doc(n.value):
				found.add((_settings_doc(n.value), n.attr))
	return {
		(dt, f)
		for dt, f in found
		if not f.startswith("_") and f not in {"get", "set", "save", "name", "db_set"}
	}


def _settings_doc(call):
	if _call_name(call) in {"get_cached_doc", "get_single", "get_doc", "get_settings"} and call.args:
		dt = _const(call.args[0])
		if dt and (dt.endswith(SETTINGS_SUFFIX) or (dt == "Company" and len(call.args) > 1)):
			return dt
	return None


def _const(node):
	return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _const_list(node):
	if isinstance(node, ast.List | ast.Tuple):
		return [v for v in (_const(e) for e in node.elts) if v]
	value = _const(node)
	return [value] if value else []


def callees(node, module_funcs, imports, index):
	"""Depth-1 callees resolvable without guessing: same-module functions, self.methods, imports."""
	out = []
	for n in ast.walk(node):
		if not isinstance(n, ast.Call):
			continue
		name = _call_name(n)
		if isinstance(n.func, ast.Name) and name in module_funcs:
			out.append(module_funcs[name])
		elif isinstance(n.func, ast.Name) and name in imports:
			module = imports[name]
			out += [q for q in index_defs(index, name) if q[0] == module]
		elif (
			isinstance(n.func, ast.Attribute)
			and isinstance(n.func.value, ast.Name)
			and n.func.value.id == "self"
		):
			if name in module_funcs:
				out.append(module_funcs[name])
	return out


def index_defs(index, name):
	return index.defs.get(name, [])


SIDES = ("base", "head")


def field_values(apps_dir, app, apps, doctype, field, commits):
	"""Values to test for one setting, and the code sides that support each value.

	Returns (values, kind, label, sides) where sides maps str(value) to the sides
	("base", "head") whose doctype JSON has the field and, for a Select, the option.
	The reviewed app is read at each reviewed commit, so a setting or option that
	the PR adds or removes is known. Other apps are read from their checkouts,
	which the PR does not change, so their values exist on both sides.
	"""
	if PRECISION_SETTINGS.get((doctype, field)):
		values = PRECISION_SETTINGS[(doctype, field)]
		return values, "preset", field.replace("_", " ").title(), {str(v): list(SIDES) for v in values}
	scrub = doctype.lower().replace(" ", "_")
	suffix = f"/doctype/{scrub}/{scrub}.json"
	found = {}
	for side in ("head", "base"):
		sha = commits[side]
		for path in git(Path(apps_dir, app), "ls-tree", "-r", "--name-only", sha).splitlines():
			if path.endswith(suffix):
				found[side] = _docfield(show(Path(apps_dir, app), sha, path), field) or found.get(side)
	if not found.get("head") and not found.get("base"):
		for other in (a for a in apps if a != app):
			for path in sorted(Path(apps_dir, other).glob(f"**{suffix}")):
				df = _docfield(path.read_text(), field)
				if df:
					found = {"head": df, "base": df}
					break
	df = found.get("head") or found.get("base")
	if not df:
		return None, "not found (custom field?)", None, {}
	values = _enumerate(df)
	if values is None:
		return None, df["fieldtype"], df.get("label"), {}
	for extra in _enumerate(found.get("base")) or []:
		if extra not in values:
			values.append(extra)  # an option the PR removes
	sides = {str(v): [s for s in SIDES if v in (_enumerate(found.get(s)) or [])] for v in values}
	return values, df["fieldtype"], df.get("label"), sides


def _docfield(text, field):
	return next(
		(df for df in json.loads(text or "{}").get("fields", []) if df.get("fieldname") == field), None
	)


def _enumerate(df):
	if not df:
		return None
	if df["fieldtype"] == "Check":
		return [0, 1]
	if df["fieldtype"] == "Select":
		return (df.get("options") or "").split("\n")
	return None


# ---------------------------------------------------------------- main


def analyze(apps_dir, app, apps, base, head):
	app_dir = Path(apps_dir, app)
	diff = changed_lines(app_dir, base, head)
	index = Index(apps_dir, apps)

	symbols, settings, json_changes, other_files, tests, hints = [], {}, [], [], [], False
	for path, lines in sorted(diff.items()):
		if PRECISION_HINT.search("\n".join(lines["text"])):
			hints = True
		if path.endswith(".json") and "/doctype/" in path:
			json_changes.append(path)
		if not path.endswith(".py"):
			other_files.append(path)
			continue
		if is_test_file(path):
			tests.append(path)
			continue
		module = ".".join(Path(path).with_suffix("").parts)
		changed = {}
		for side, sha in (("base", base), ("head", head)):
			source = show(app_dir, sha, path)
			funcs = functions(source)
			by_name = {q: n for q, n in funcs}
			module_funcs = {q.split(".")[-1]: (module, q, f"{app}/{path}") for q, _ in funcs}
			imports = _imports(source)
			for qual in enclosing(funcs, lines[side]):
				changed.setdefault(qual, set()).add(side)
				node = by_name.get(qual)
				if node is None:
					continue
				for s in settings_read(node):
					settings.setdefault(s, set()).add(f"{path}:{qual}")
				for _, cq, cfile in callees(node, module_funcs, imports, index):
					for cnode in _find(apps_dir, cfile, cq):
						for s in settings_read(cnode):
							settings.setdefault(s, set()).add(f"{cfile}:{cq} (callee of {qual})")
		for qual, sides in sorted(changed.items()):
			simple = qual.split(".")[-1]
			symbols.append(
				{
					"symbol": f"{path}:{qual}",
					"sides": sorted(sides),
					"callers": callers(index, simple, f"{module}.{simple}")
					if qual != "<module>"
					else {"kind": "module"},
				}
			)

	if hints:
		for key in PRECISION_SETTINGS:
			settings.setdefault(key, set()).add("diff mentions precision or rounding")

	setting_rows = []
	for (dt, field), sources in sorted(settings.items()):
		values, kind, label, sides = field_values(
			apps_dir, app, apps, dt, field, {"head": head, "base": base}
		)
		setting_rows.append(
			{
				"doctype": dt,
				"field": field,
				"label": label,
				"kind": kind,
				"values": values,
				"read_in": sorted(sources),
			}
		)

	return {
		"base": base,
		"head": head,
		"changed_files": sorted(diff),
		"doctype_json_changed": json_changes,
		"needs_migrate": bool(json_changes) or any(p.endswith(("patches.txt", "hooks.py")) for p in diff),
		"symbols": symbols,
		"settings": setting_rows,
		"reports_touched": sorted({m[1] for p in diff if (m := re.search(r"/report/(\w+)/", p))}),
		"ui_files": sorted(p for p in diff if is_ui_file(p)),
		"test_files": sorted(tests),
	}


def is_test_file(path):
	name = Path(path).name
	return name.startswith("test_") or "/tests/" in path


def is_ui_file(path):
	return (
		path.endswith(UI_EXTENSIONS)
		and "/tests/" not in path
		and "/test_" not in path
		or bool(UI_JSON.search(path))
	)


def _imports(source):
	out = {}
	try:
		tree = ast.parse(source)
	except SyntaxError:
		return out
	for node in ast.walk(tree):
		if isinstance(node, ast.ImportFrom) and node.module:
			for alias in node.names:
				out[alias.asname or alias.name] = node.module
	return out


def _find(apps_dir, rel_file, qual):
	path = Path(apps_dir, rel_file)
	if not path.exists():
		return []
	return [n for q, n in functions(path.read_text(errors="ignore")) if q == qual]


def generate_plan(analysis, pr):
	"""Variants: default, then one per (setting, value), sorted. Flips: default -> each Check variant.

	Each variant lists the code sides that support it. A value that only the PR
	code has (a new setting or option) runs on the PR code only; a value that the
	PR removes runs on the base code only. A flip needs both sides.
	"""
	variants = [{"id": "v0", "label": "default", "sides": ["base", "head"], "singles": {}, "company": {}}]
	flips = []
	for row in analysis["settings"]:
		if row["values"] is None:
			continue
		for value in row["values"]:
			vid = f"v{len(variants)}"
			sides = row.get("sides", {}).get(str(value), ["base", "head"])
			variant = {"id": vid, "label": _label(row, value), "sides": sides, "singles": {}, "company": {}}
			if row["doctype"] == "Company":
				variant["company"] = {row["field"]: value}
			else:
				variant["singles"] = {row["doctype"]: {row["field"]: value}}
			variants.append(variant)
			if row["kind"] == "Check" and sides == ["base", "head"]:
				flips.append(["v0", vid])
	return {
		"pr": pr,
		"company_profile": dict(DEFAULT_PROFILE),
		"item_fields": {},
		"ui": bool(analysis["ui_files"]),
		"variants": variants,
		"flips": flips,
	}


def _label(row, value):
	"""Human label, e.g. "Accounts Settings > Unlink Payment on Cancellation of Invoice: on"."""
	if row["kind"] == "Check":
		shown = "on" if str(value) == "1" else "off"
	else:
		shown = repr(value) if value != "" else "(blank)"
	return f"{row['doctype']} > {row.get('label') or row['field']}: {shown}"
