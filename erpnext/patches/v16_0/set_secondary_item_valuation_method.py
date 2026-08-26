import frappe
from frappe.utils import flt


def execute():
	"""Set valuation_method on sites that migrated before the field existed.

	Fresh migrations get it from co_by_product_patch; the legacy columns never
	existed there, so every step below is a no-op.
	"""
	for doctype, legacy_fields in (
		("BOM Secondary Item", ["is_legacy", "use_valuation_rate"]),
		("Stock Entry Detail", ["is_legacy_scrap_item", "use_valuation_rate"]),
		("Subcontracting Receipt Item", ["is_legacy_scrap_item", "use_valuation_rate"]),
	):
		set_valuation_rate_method(doctype, legacy_fields)

	set_percentage_method()
	backfill_cost_from_rate()


def set_valuation_rate_method(doctype, legacy_fields):
	table = frappe.qb.DocType(doctype)
	for field in legacy_fields:
		if not frappe.db.has_column(doctype, field):
			continue

		frappe.qb.update(table).set(table.valuation_method, "Valuation Rate").where(table[field] == 1).run()


def set_percentage_method():
	"""Rows created by the percentage system before the method field existed.

	Only BOM rows need this: the field is mandatory there, and the costing treats
	the percentage method as the default for everything else."""
	rows = frappe.get_all("BOM Secondary Item", filters={"valuation_method": ("is", "not set")}, pluck="name")
	if not rows:
		return

	frappe.db.set_value(
		"BOM Secondary Item",
		{"name": ("in", rows)},
		"valuation_method",
		"% of FG Cost",
		update_modified=False,
	)


def backfill_cost_from_rate():
	"""Earlier v16 builds stored the migrated scrap rate on the removed rate field."""
	if not frappe.db.has_column("BOM Secondary Item", "rate"):
		return

	table = frappe.qb.DocType("BOM Secondary Item")
	rows = (
		frappe.qb.from_(table)
		.select(table.name, table.parent, table.rate, table.stock_qty)
		.where((table.valuation_method == "Valuation Rate") & (table.cost == 0) & (table.rate > 0))
	).run(as_dict=True)
	if not rows:
		return

	conversion_rates = dict(
		frappe.get_all(
			"BOM",
			filters={"name": ("in", {row.parent for row in rows})},
			fields=["name", "conversion_rate"],
			as_list=True,
		)
	)

	for row in rows:
		cost = flt(row.rate) * flt(row.stock_qty)
		frappe.db.set_value(
			"BOM Secondary Item",
			row.name,
			{"cost": cost, "base_cost": cost * flt(conversion_rates.get(row.parent) or 1)},
			update_modified=False,
		)
