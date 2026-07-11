# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, get_datetime

TREE_PARTY_TYPES = ("Customer Group", "Territory", "Supplier Group")


@frappe.whitelist()
def detect_overlaps(scheme: str | dict) -> list[dict]:
	"""Classify every active scheme that intersects the given (possibly
	unsaved) scheme: conflict / shadowed / wins / stacks.

	Include rows only — excludes are ignored, so results are conservative
	("possible overlap"). Evidence names the intersecting scope pair.
	"""
	doc = frappe.get_doc(frappe.parse_json(scheme)) if isinstance(scheme, str) else scheme
	overlaps = []
	for other_name in _candidate_names(doc):
		other = frappe.get_cached_doc("Pricing Scheme", other_name)
		if entry := _classify(doc, other):
			overlaps.append(entry)
	return sorted(overlaps, key=lambda e: ("conflict", "shadowed", "wins", "stacks").index(e["severity"]))


@frappe.whitelist()
def get_usage(scheme: str) -> dict:
	"""Ledger-driven usage stats for the form dashboard."""
	rows = frappe.get_all(
		"Pricing Scheme Application",
		filters={"scheme": scheme, "is_cancelled": 0},
		fields=[
			"count(name) as applications",
			"sum(discount_amount) as discount_given",
			"sum(free_item_qty) as free_qty",
		],
	)
	row = rows[0] if rows else frappe._dict()
	caps = frappe.get_cached_value(
		"Pricing Scheme", scheme, ("cap_total_applications", "cap_total_discount_amount"), as_dict=True
	)
	return {
		"applications": cint(row.get("applications")),
		"discount_given": float(row.get("discount_given") or 0),
		"free_qty": float(row.get("free_qty") or 0),
		"cap_total_applications": cint(caps.cap_total_applications),
		"cap_total_discount_amount": float(caps.cap_total_discount_amount or 0),
	}


@frappe.whitelist()
def count_scope_items(scheme: str | dict) -> int:
	"""Approximate item count matched by the trigger scope (include rows,
	deduplicated; excludes subtracted without cross-type dedup)."""
	doc = frappe.get_doc(frappe.parse_json(scheme)) if isinstance(scheme, str) else scheme
	includes = [
		row for row in doc.trigger_scope if not row.exclude and row.value or row.scope_type == "All Items"
	]
	excludes = [row for row in doc.trigger_scope if row.exclude and row.value]
	total = _count_items(includes)
	return max(total - _count_items(excludes), 0)


def _candidate_names(doc) -> list[str]:
	return frappe.get_all(
		"Pricing Scheme",
		filters={
			"disabled": 0,
			"transaction_type": doc.transaction_type,
			"name": ("!=", doc.name or ""),
		},
		pluck="name",
	)


def _classify(doc, other) -> dict | None:
	if not _windows_overlap(doc, other):
		return None
	if not _companies_overlap(doc, other):
		return None
	if not _item_scopes_intersect(doc.trigger_scope, other.trigger_scope):
		return None
	if not _party_scopes_intersect(doc.party_scope, other.party_scope):
		return None

	evidence = _intersection_evidence(doc.trigger_scope, other.trigger_scope)
	if doc.stacking_group != other.stacking_group:
		return _entry(other, "stacks", _("combines — different stacking group ({0})").format(evidence))
	if cint(doc.priority) == cint(other.priority):
		return _entry(
			other, "conflict", _("same group and priority ({0}) — saving will be blocked").format(evidence)
		)
	if cint(doc.priority) < cint(other.priority):
		return _entry(other, "shadowed", _("loses to it on priority for {0}").format(evidence))
	return _entry(other, "wins", _("wins over it on priority for {0}").format(evidence))


def _entry(other, severity: str, detail: str) -> dict:
	return {"scheme": other.name, "title": other.title, "severity": severity, "detail": detail}


def _windows_overlap(a, b) -> bool:
	a_from = get_datetime(a.valid_from or "2000-01-01")
	a_upto = get_datetime(a.valid_upto or "2500-12-31")
	b_from = get_datetime(b.valid_from or "2000-01-01")
	b_upto = get_datetime(b.valid_upto or "2500-12-31")
	return a_from <= b_upto and b_from <= a_upto


def _companies_overlap(a, b) -> bool:
	return not a.company or not b.company or a.company == b.company


def _item_scopes_intersect(rows_a: list, rows_b: list) -> bool:
	includes_a = [r for r in rows_a if not r.exclude]
	includes_b = [r for r in rows_b if not r.exclude]
	return any(_scope_rows_intersect(a, b) for a in includes_a for b in includes_b)


def _intersection_evidence(rows_a: list, rows_b: list) -> str:
	for a in (r for r in rows_a if not r.exclude):
		for b in (r for r in rows_b if not r.exclude):
			if _scope_rows_intersect(a, b):
				return f"{a.scope_type}: {a.value or _('All Items')} ∩ {b.scope_type}: {b.value or _('All Items')}"
	return _("shared scope")


def _scope_rows_intersect(a, b) -> bool:
	if "All Items" in (a.scope_type, b.scope_type):
		return True
	pair = {a.scope_type, b.scope_type}
	if pair == {"Item"}:
		return a.value == b.value
	if pair == {"Item Group"}:
		return _subtrees_nest("Item Group", a.value, b.value)
	if pair == {"Brand"}:
		return a.value == b.value
	return _mixed_scope_intersect(a, b)


def _mixed_scope_intersect(a, b) -> bool:
	item_row = a if a.scope_type == "Item" else (b if b.scope_type == "Item" else None)
	other = b if item_row is a else a
	if item_row:
		field = "item_group" if other.scope_type == "Item Group" else "brand"
		value = frappe.get_cached_value("Item", item_row.value, field)
		if other.scope_type == "Item Group":
			return _subtrees_nest("Item Group", other.value, value)
		return value == other.value
	# Item Group x Brand: does any item of the brand live in the group subtree?
	group = a.value if a.scope_type == "Item Group" else b.value
	brand = a.value if a.scope_type == "Brand" else b.value
	groups = _descendants("Item Group", group)
	return bool(frappe.get_all("Item", filters={"brand": brand, "item_group": ("in", groups)}, limit=1))


def _party_scopes_intersect(rows_a: list, rows_b: list) -> bool:
	includes_a = [r for r in rows_a if not r.exclude]
	includes_b = [r for r in rows_b if not r.exclude]
	if not includes_a or not includes_b:
		return True  # empty scope = everyone
	return any(_party_rows_intersect(a, b) for a in includes_a for b in includes_b)


def _party_rows_intersect(a, b) -> bool:
	if a.party_type == b.party_type:
		if a.party_type in TREE_PARTY_TYPES:
			return _subtrees_nest(a.party_type, a.value, b.value)
		return a.value == b.value
	return _cross_party_intersect(a, b) and _cross_party_intersect(b, a)


def _cross_party_intersect(a, b) -> bool:
	"""Customer row vs group/territory row is decidable; other cross pairs
	restrict different dimensions and are conservatively intersecting."""
	if a.party_type != "Customer" or b.party_type not in ("Customer Group", "Territory"):
		return True
	field = "customer_group" if b.party_type == "Customer Group" else "territory"
	value = frappe.get_cached_value("Customer", a.value, field)
	return _subtrees_nest(b.party_type, b.value, value)


def _subtrees_nest(doctype: str, one: str, two: str | None) -> bool:
	if not two:
		return False
	if one == two:
		return True
	a = frappe.get_cached_value(doctype, one, ("lft", "rgt"))
	b = frappe.get_cached_value(doctype, two, ("lft", "rgt"))
	if not (a and b):
		return False
	return (a[0] <= b[0] and b[1] <= a[1]) or (b[0] <= a[0] and a[1] <= b[1])


def _descendants(doctype: str, name: str) -> list[str]:
	bounds = frappe.get_cached_value(doctype, name, ("lft", "rgt"))
	if not bounds:
		return [name]
	return frappe.get_all(doctype, filters={"lft": (">=", bounds[0]), "rgt": ("<=", bounds[1])}, pluck="name")


def _count_items(rows: list) -> int:
	or_filters = []
	for row in rows:
		if row.scope_type == "All Items":
			return frappe.db.count("Item", {"disabled": 0})
		if row.scope_type == "Item":
			or_filters.append(["Item", "name", "=", row.value])
		elif row.scope_type == "Brand":
			or_filters.append(["Item", "brand", "=", row.value])
		elif row.scope_type == "Item Group":
			or_filters.append(["Item", "item_group", "in", _descendants("Item Group", row.value)])
	if not or_filters:
		return 0
	return len(frappe.get_all("Item", filters={"disabled": 0}, or_filters=or_filters, pluck="name"))
