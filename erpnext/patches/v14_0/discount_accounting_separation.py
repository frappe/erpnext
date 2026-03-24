import frappe


def execute():
	discount_account = int(frappe.db.get_single_value("Accounts Settings", "enable_discount_accounting") or 0)
	if discount_account:
		for doctype in ["Buying Settings", "Selling Settings"]:
			frappe.db.set_single_value(doctype, "enable_discount_accounting", 1, update_modified=False)
