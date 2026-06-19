import frappe


def execute():
	"""Preserve the previous "spread Actual valuation charge across all items" behaviour
	for existing data.

	The new `allocate_full_amount_to_stock_items` field defaults to 1 so that new freight
	(and similar landed cost) rows capitalize the full charge into stock/asset valuation.
	But `bench migrate` sets that default on every existing row as well, which would
	silently change stock valuation on existing draft documents and templates. Reset
	existing "Actual" valuation rows to 0 so they keep the old behaviour; users can opt in
	by ticking the checkbox.
	"""
	frappe.db.set_value(
		"Purchase Taxes and Charges",
		{"charge_type": "Actual"},
		"allocate_full_amount_to_stock_items",
		0,
		update_modified=False,
	)
