#!/usr/bin/env python3
"""Static guard against MySQL-only SQL that breaks on PostgreSQL.

The Postgres test job is label-gated, so it does not run on every PR. This pre-commit
hook is the always-on first line of defence: it flags the *mechanical* Postgres breaks
that static analysis can catch reliably with a low false-positive rate.

It deliberately does NOT try to catch the *semantic* divergences (loose GROUP BY,
case-sensitive ==/IN, NULL ordering, ORDER BY ... LIMIT 1 tiebreakers, integer-division
intent, division by a possibly-zero divisor, savepoint discipline) — those genuinely need
the test suite or a human/Greptile reviewer. Run the full suite on a Postgres site for those.

Escape hatch: put `# pg-ok` anywhere on the offending statement's line span (e.g. on a
`SHOW INDEX` query that lives inside an `if frappe.db.db_type == "mariadb":` branch).

Usage: postgres_compat.py <file.py> [<file.py> ...]   (pre-commit passes staged files)
"""

from __future__ import annotations

import ast
import re
import sys

IGNORE = "pg-ok"

# Strings are only scanned for the patterns below when they have real SQL *structure*
# (not just an English word like "select" or "from"), to keep false positives near zero.
SQL_HINT = re.compile(
	r"\bselect\b[\s\S]{0,800}\bfrom\b"        # SELECT ... FROM
	r"|\bupdate\b[\s\S]{0,400}\bset\b"         # UPDATE ... SET
	r"|\bdelete\s+from\b"
	r"|\binsert\s+into\b"
	r"|\bshow\s+(?:index|tables|columns)\b"
	r"|\bfrom\s+[\"'`]?tab",                   # FROM `tabDocType`
	re.I,
)

# MySQL-only constructs with NO frappe auto-translation. (frappe.db.sql already rewrites
# ifnull->coalesce on all engines and backtick/locate/REGEXP on Postgres, and .like()
# renders ILIKE — so those are NOT listed here; flagging them would be false positives.)
SQL_PATTERNS: list[tuple[re.Pattern, str]] = [
	(re.compile(r"\btimestamp\s*\(\s*[^,()]+,", re.I),
	 "timestamp(date, time) is MySQL-only -> use CombineDatetime() or a precomputed datetime column"),
	(re.compile(r"\btimediff\s*\(", re.I),
	 "timediff() is MySQL-only -> compute the delta in Python"),
	(re.compile(r"\bstr_to_date\s*\(", re.I),
	 "str_to_date() is MySQL-only -> parse in Python and pass a real date"),
	(re.compile(r"\bdate_format\s*\(", re.I),
	 "date_format() is MySQL-only -> filter on a date range instead"),
	(re.compile(r"\bdate_(add|sub)\s*\(", re.I),
	 "date_add()/date_sub() are MySQL-only -> use Python date math or interval arithmetic"),
	(re.compile(r"\bgroup_concat\s*\(", re.I),
	 "group_concat() is MySQL-only -> use GroupConcat (string_agg) or aggregate in Python"),
	(re.compile(r"\bperiod_diff\s*\(", re.I),
	 "period_diff() is MySQL-only -> compute in Python"),
	(re.compile(r"\bshow\s+index\b", re.I),
	 "SHOW INDEX is MySQL-only -> use frappe.db.has_index() / get_column_index()"),
	(re.compile(r"\bshow\s+(tables|columns)\b", re.I),
	 "SHOW TABLES/COLUMNS is MySQL-only -> use frappe.db.get_tables()/table_columns / information-schema helpers"),
	(re.compile(r"\bas\s+'[^']+'", re.I),
	 "single-quoted column alias breaks on Postgres -> use a bare or double-quoted alias"),
	(re.compile(r"\bif\s*\(", re.I),
	 "SQL IF() is MySQL-only -> use CASE WHEN ... THEN ... ELSE ... END (frappe.qb.Case())"),
	(re.compile(r"\brlike\b", re.I),
	 "RLIKE is MySQL-only -> frappe rewrites REGEXP->~* on Postgres but NOT RLIKE; use REGEXP / .regexp() / ~"),
	(re.compile(r"\bcast\s*\(.+?\bas\s+char\b", re.I | re.S),  # .+? spans nested parens, e.g. CAST(ABS(x) AS CHAR)
	 "CAST(... AS CHAR) is character(1) on Postgres and truncates -> CAST AS VARCHAR (frappe Cast_(x, 'varchar'))"),
]

# UPDATE ... JOIN: both keywords in the same SQL string.
UPDATE_JOIN = (re.compile(r"\bupdate\b", re.I), re.compile(r"\bjoin\b", re.I))

MYSQL_RESULT_KEYS = {"Column_name", "Key_name", "Seq_in_index", "Non_unique", "Index_type"}

SET_BOOL_FUNCS = {"set_value", "db_set"}

# query-builder cast helpers: pypika Cast / frappe Cast_. A "char" target type is character(1)
# on Postgres (truncates); "varchar" is the full-length cast.
CAST_FUNCS = {"Cast", "Cast_"}

# frappe.get_all / get_list: frappe's db_query SILENTLY drops ORDER BY for `distinct` queries on
# Postgres (the ORDER BY column must appear in the SELECT-DISTINCT list), so `distinct=True` together
# with a literal `order_by` is a no-op on PG and the result comes back unordered.
DISTINCT_ORDER_FUNCS = {"get_all", "get_list"}


def _docstring_ids(tree: ast.AST) -> set[int]:
	"""ids of Constant nodes that are docstrings (so prose describing the rules isn't flagged)."""
	ids: set[int] = set()
	for node in ast.walk(tree):
		if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
			body = getattr(node, "body", None)
			if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
				ids.add(id(body[0].value))
	return ids


class Visitor(ast.NodeVisitor):
	def __init__(self, lines: list[str], docstrings: set[int]):
		self.lines = lines
		self.docstrings = docstrings
		self.violations: list[tuple[int, str]] = []

	def _ignored(self, node: ast.AST) -> bool:
		start = getattr(node, "lineno", 1)
		end = getattr(node, "end_lineno", start) or start
		# honour `# pg-ok` anywhere on the node's line span, the line just above (the enclosing
		# call, e.g. `frappe.db.sql(  # pg-ok`), or the line just below (a multi-line call's `)  # pg-ok`).
		lo = max(0, start - 2)
		return any(IGNORE in self.lines[i] for i in range(lo, min(end + 1, len(self.lines))))

	def _flag(self, node: ast.AST, msg: str) -> None:
		if not self._ignored(node):
			self.violations.append((getattr(node, "lineno", 1), msg))

	def _scan_sql(self, text: str, node: ast.AST) -> None:
		if not SQL_HINT.search(text):
			return
		for pattern, msg in SQL_PATTERNS:
			if pattern.search(text):
				self._flag(node, msg)
		if UPDATE_JOIN[0].search(text) and UPDATE_JOIN[1].search(text):
			self._flag(node, "UPDATE ... JOIN is MySQL-only -> use a correlated subquery (WHERE ... IN/EXISTS)")

	def visit_Constant(self, node: ast.Constant) -> None:
		# plain string literals, incl. `"...".format()` and `"..." % (...)` templates
		if isinstance(node.value, str) and id(node) not in self.docstrings:
			self._scan_sql(node.value, node)
		self.generic_visit(node)

	def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
		# f-string: scan its STATIC text (interpolated values become a placeholder) so MySQL-isms
		# in dynamic SQL are caught, without flagging safe interpolation of identifiers.
		text = "".join(
			v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else " ? "
			for v in node.values
		)
		self._scan_sql(text, node)
		# don't recurse: child literal chunks would otherwise be re-scanned individually

	def visit_Call(self, node: ast.Call) -> None:
		fn = node.func
		name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")

		# row.get("Column_name") — MySQL SHOW INDEX result key
		if name == "get" and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in MYSQL_RESULT_KEYS:
			self._flag(node, f'"{node.args[0].value}" is a MySQL SHOW INDEX result key -> use frappe.db.has_index()/get_column_index()')

		# set_value(..., True) / db_set("field", True) on a Check (int) column.
		# Only the field *value* arg carries bool->smallint risk — NOT trailing flags like
		# update_modified. db_set(field, value, update_modified, ...) -> value at args[1] (or a dict
		# at args[0]); set_value(dt, dn, field, value, ...) -> value at args[3] (or a dict at args[2]).
		if name in SET_BOOL_FUNCS:
			value_idx, dict_idx = (1, 0) if name == "db_set" else (3, 2)
			dict_arg = (
				node.args[dict_idx]
				if len(node.args) > dict_idx and isinstance(node.args[dict_idx], ast.Dict)
				else None
			)
			if dict_arg is not None:
				for v in dict_arg.values:
					if isinstance(v, ast.Constant) and isinstance(v.value, bool):
						self._flag(node, f"{name}(...) sets an int/Check column with a bool in a dict -> pass 1/0 (Postgres rejects bool->smallint)")
			elif len(node.args) > value_idx:
				a = node.args[value_idx]
				if isinstance(a, ast.Constant) and isinstance(a.value, bool):
					self._flag(node, f"{name}(..., {a.value}) sets an int/Check column with a bool -> pass 1/0 (Postgres rejects bool->smallint)")

		# frappe.get_all/get_list(..., distinct=True, order_by="<col>") -> ORDER BY is silently dropped
		# for distinct queries on Postgres, so the result is unordered there. Sort in python instead
		# (e.g. sorted(frappe.get_all(..., distinct=True), key=str.casefold)). An empty order_by="" (the
		# explicit "suppress the injected default" idiom) and a dynamic/variable order_by are not flagged.
		if name in DISTINCT_ORDER_FUNCS:
			has_distinct = any(
				kw.arg == "distinct" and isinstance(kw.value, ast.Constant) and kw.value.value
				for kw in node.keywords
			)
			order_kw = next((kw for kw in node.keywords if kw.arg == "order_by"), None)
			has_literal_order = (
				order_kw is not None
				and isinstance(order_kw.value, ast.Constant)
				and isinstance(order_kw.value.value, str)
				and order_kw.value.value.strip()
			)
			if has_distinct and has_literal_order:
				self._flag(node, f"{name}(distinct=True, order_by=...) -> frappe drops ORDER BY for distinct queries on Postgres; sort in python instead, e.g. sorted(..., key=str.casefold)")

		# query-builder .rlike(...): pypika emits the MySQL-only RLIKE operator, which frappe does
		# NOT translate for Postgres (it rewrites only REGEXP -> ~*).
		if name == "rlike":
			self._flag(node, ".rlike() emits MySQL-only RLIKE (not translated on Postgres) -> use .regexp() (rewritten to ~*) or .like()")

		# Cast(col, "char") / Cast_(col, "char"): on Postgres a bare CHAR is character(1) and truncates
		# (e.g. CAST(12 AS CHAR) -> '1'); use "varchar" for a full-length string cast.
		if name in CAST_FUNCS:
			for arg in (*node.args, *(kw.value for kw in node.keywords)):
				if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.strip().lower() == "char":
					self._flag(node, f"{name}(..., 'char') is character(1) on Postgres and truncates -> use 'varchar'")

		self.generic_visit(node)

	def visit_Subscript(self, node: ast.Subscript) -> None:
		key = node.slice
		if isinstance(key, ast.Constant) and key.value in MYSQL_RESULT_KEYS:
			self._flag(node, f'"{key.value}" is a MySQL SHOW INDEX result key -> use frappe.db.has_index()/get_column_index()')
		self.generic_visit(node)


def check_file(path: str) -> list[str]:
	try:
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal -- dev-only lint tool; `path` is a source file supplied by pre-commit, not user input
		src = open(path, encoding="utf-8").read()
	except (OSError, UnicodeDecodeError):
		return []
	try:
		tree = ast.parse(src, filename=path)
	except SyntaxError:
		return []  # check-ast hook reports real syntax errors
	v = Visitor(src.splitlines(), _docstring_ids(tree))
	v.visit(tree)
	return [f"{path}:{line}: [pg-compat] {msg}" for line, msg in sorted(set(v.violations))]


def main(argv: list[str]) -> int:
	out: list[str] = []
	for path in argv:
		if path.endswith(".py"):
			out.extend(check_file(path))
	if out:
		print("\n".join(out))
		print(
			f"\n{len(out)} PostgreSQL-incompatibility issue(s). Fix them, or add `# pg-ok` to a "
			"line that is intentionally MariaDB-only (e.g. inside an `if frappe.db.db_type == 'mariadb':` branch)."
		)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))
