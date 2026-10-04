# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors

import frappe


def execute():
	frappe.db.delete("Singles", {"doctype": "Opening Invoice Creation Tool"})
	frappe.db.delete("Opening Invoice Creation Tool Item", {"parent": "Opening Invoice Creation Tool"})

	if frappe.db.exists("DocType", "Opening Invoice Creation Tool"):
		frappe.delete_doc("DocType", "Opening Invoice Creation Tool", force=True)

	frappe.reload_doc("accounts", "doctype", "opening_invoice_creation_tool")
	frappe.reload_doc("accounts", "doctype", "opening_invoice_creation_tool_item")
