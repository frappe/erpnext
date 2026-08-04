import frappe


def execute():
	# runs pre_model_sync: field is still a Select, so this returns the raw "Yes"/"No"
	old_value = frappe.db.get_single_value("Global Defaults", "hide_currency_symbol")
	new_value = 1 if old_value == "Yes" else 0
	frappe.db.set_single_value("Global Defaults", "hide_currency_symbol", new_value)
	frappe.db.set_default("hide_currency_symbol", new_value)
