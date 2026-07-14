# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, get_datetime

from erpnext.accounts.services.pricing.pricing_context import LineContext, PricingContext

TREE_SCOPES = {"Item Group", "Customer Group", "Territory", "Supplier Group"}


def item_in_scope(line: LineContext, scope_rows: list, applies_to: str | None = None) -> bool:
	"""OR within a scope type, AND across scope types, then excludes subtract.

	applies_to == "All Items" matches every line (excludes still subtract);
	an explicit All Items include row is the legacy equivalent.
	"""
	includes: dict[str, list] = {}
	for row in scope_rows:
		if row.exclude:
			if _scope_row_matches(line, row):
				return False
		else:
			includes.setdefault(row.scope_type, []).append(row)

	if applies_to == "All Items":
		return True
	if not includes:
		return False
	return all(any(_scope_row_matches(line, row) for row in rows) for rows in includes.values())


def party_in_scope(context: PricingContext, scope_rows: list) -> bool:
	"""Empty table means everyone; group and territory values match their subtree."""
	includes = []
	for row in scope_rows:
		if row.exclude:
			if _party_row_matches(context, row):
				return False
		else:
			includes.append(row)

	if not includes:
		return True
	return any(_party_row_matches(context, row) for row in includes)


def date_in_window(scheme, transaction_date: str) -> bool:
	date = get_datetime(transaction_date)
	if scheme.valid_from and date < get_datetime(scheme.valid_from):
		return False
	if scheme.valid_upto and date > get_datetime(scheme.valid_upto):
		return False
	return True


def select_tier(tiers: list, qty: float, amount: float):
	"""Pick the tier whose half-open bands contain the basis; None if in a gap."""
	for tier in tiers:
		if _band_contains(tier.min_qty, tier.max_qty, qty) and _band_contains(
			tier.min_amount, tier.max_amount, amount
		):
			return tier
	return None


def evaluate_condition(scheme, doc) -> tuple[bool, str | None]:
	"""safe_eval the scheme condition; errors are returned, never swallowed."""
	if not scheme.condition:
		return True, None
	try:
		context = doc.as_dict() if hasattr(doc, "as_dict") else dict(doc or {})
		return bool(frappe.safe_eval(scheme.condition, eval_locals=context)), None
	except Exception as exc:
		frappe.log_error(
			title=f"Pricing Scheme condition failed: {scheme.name}",
			message=f"{scheme.condition}\n\n{exc}",
		)
		return False, str(exc)


def _band_contains(min_value: float, max_value: float, basis: float) -> bool:
	if flt(basis) < flt(min_value):
		return False
	return not flt(max_value) or flt(basis) < flt(max_value)


def _scope_row_matches(line: LineContext, row) -> bool:
	if row.scope_type == "All Items":
		return True
	if row.uom and line.uom and row.uom != line.uom:
		return False
	if row.scope_type == "Item":
		return row.value in (line.item_code, line.variant_of)
	if row.scope_type == "Item Group":
		return _in_subtree("Item Group", row.value, line.item_group)
	if row.scope_type == "Brand":
		return bool(line.brand) and row.value == line.brand
	return False


def _party_row_matches(context: PricingContext, row) -> bool:
	direct = {
		"Customer": context.party if context.party_type == "Customer" else None,
		"Supplier": context.party if context.party_type == "Supplier" else None,
		"Sales Partner": context.sales_partner,
		"Campaign": context.campaign,
	}
	tree = {
		"Customer Group": context.customer_group,
		"Territory": context.territory,
		"Supplier Group": context.supplier_group,
	}
	if row.party_type in direct:
		return bool(direct[row.party_type]) and row.value == direct[row.party_type]
	return _in_subtree(row.party_type, row.value, tree.get(row.party_type))


def _in_subtree(doctype: str, ancestor: str, node: str | None) -> bool:
	if not node:
		return False
	if node == ancestor:
		return True
	bounds = _tree_bounds(doctype, ancestor)
	node_bounds = _tree_bounds(doctype, node)
	if not (bounds and node_bounds):
		return False
	return bounds[0] <= node_bounds[0] and node_bounds[1] <= bounds[1]


def _tree_bounds(doctype: str, name: str) -> tuple[int, int] | None:
	values = frappe.get_cached_value(doctype, name, ("lft", "rgt"))
	return (values[0], values[1]) if values else None
