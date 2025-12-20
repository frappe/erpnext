import frappe


def execute():
	frappe.db.set_value("Report", "Gross Profit", "add_total_row", 0)
