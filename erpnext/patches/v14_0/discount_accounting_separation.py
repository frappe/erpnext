import frappe


def execute():
	doc = frappe.get_doc("Accounts Settings")
	discount_account = doc.enable_discount_accounting
	if discount_account:
		for doctype in ["Buying Settings", "Selling Settings"]:
			frappe.db.set_value(doctype, doctype, "enable_discount_accounting", 1, update_modified=False)
