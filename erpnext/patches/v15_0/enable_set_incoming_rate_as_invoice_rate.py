import frappe


def execute():
	frappe.db.set_single_value("Selling Settings", "set_incoming_rate_as_invoice_rate", 1)
