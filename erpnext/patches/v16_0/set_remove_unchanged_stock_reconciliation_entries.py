import frappe


def execute():
	frappe.db.set_single_value(
		"Stock Settings",
		"remove_unchanged_stock_reconciliation_entries",
		1,
	)
