from frappe.model.utils.rename_field import rename_field


def execute():
	"""Rename for sites that migrated before is_legacy was replaced by use_valuation_rate.

	Fresh migrations get use_valuation_rate directly from co_by_product_patch; rename_field
	is a no-op there because the old columns never existed.
	"""
	rename_field("BOM Secondary Item", "is_legacy", "use_valuation_rate")
	rename_field("Stock Entry Detail", "is_legacy_scrap_item", "use_valuation_rate")
	rename_field("Subcontracting Receipt Item", "is_legacy_scrap_item", "use_valuation_rate")
