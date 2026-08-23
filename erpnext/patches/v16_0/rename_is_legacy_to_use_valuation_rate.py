import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.utils import flt


def execute():
	"""Rename for sites that migrated before is_legacy was replaced by use_valuation_rate.

	Fresh migrations get use_valuation_rate directly from co_by_product_patch; rename_field
	is a no-op there because the old columns never existed.
	"""
	rename_field("BOM Secondary Item", "is_legacy", "use_valuation_rate")
	rename_field("Stock Entry Detail", "is_legacy_scrap_item", "use_valuation_rate")
	rename_field("Subcontracting Receipt Item", "is_legacy_scrap_item", "use_valuation_rate")
	backfill_cost_from_rate()


def backfill_cost_from_rate():
	"""Earlier v16 builds stored the migrated scrap rate on the removed rate field."""
	if not frappe.db.has_column("BOM Secondary Item", "rate"):
		return

	rows = frappe.db.sql(
		"""select name, parent, rate, stock_qty from `tabBOM Secondary Item`
		where use_valuation_rate = 1 and cost = 0 and rate > 0""",
		as_dict=True,
	)
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
