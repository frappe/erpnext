import frappe


def execute():
	old_value = frappe.db.get_value(
		"Singles", {"doctype": "Global Defaults", "field": "hide_currency_symbol"}, "value"
	)
	new_value = 1 if old_value == "Yes" else 0
	frappe.db.set_single_value("Global Defaults", "hide_currency_symbol", new_value)
	frappe.db.set_default("hide_currency_symbol", new_value)
