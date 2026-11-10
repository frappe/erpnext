import frappe

DOCTYPES = ("BOM Secondary Item", "Stock Entry Detail", "Subcontracting Receipt Item")


def execute():
	"""Rename the `% of FG Cost` valuation type: the percentage is of the component cost."""
	for doctype in DOCTYPES:
		frappe.db.set_value(
			doctype,
			{"valuation_type": "% of FG Cost"},
			"valuation_type",
			"% of Component Cost",
			update_modified=False,
		)
