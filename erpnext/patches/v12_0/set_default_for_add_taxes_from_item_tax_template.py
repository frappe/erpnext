import frappe

def execute():
	frappe.db.set_value("Accounts Settings", None, "add_taxes_from_item_tax_template", 1)
	frappe.db.set_default("add_taxes_from_item_tax_template", 1)