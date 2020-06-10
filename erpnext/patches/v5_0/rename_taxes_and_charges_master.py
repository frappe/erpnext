from __future__ import unicode_literals
import frappe


def execute():
	if frappe.db.table_exists("Sales Taxes and Charges Master"):
		frappe.rename_doc("DocType", "Sales Taxes and Charges Master",
			"Sales Taxes and Charges Template")
		frappe.delete_doc("DocType", "Sales Taxes and Charges Master")

	if frappe.db.table_exists("Purchase Taxes and Charges Master"):
		frappe.rename_doc("DocType", "Purchase Taxes and Charges Master",
			"Purchase Taxes and Charges Template")
		frappe.delete_doc("DocType", "Purchase Taxes and Charges Master")
