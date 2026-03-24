# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	"""`sales_invoice` field from loyalty point entry is splitted into `invoice_type` & `invoice` fields"""

	frappe.reload_doc("Accounts", "doctype", "loyalty_point_entry")

	if not frappe.db.has_column("Loyalty Point Entry", "sales_invoice"):
		return

	loyalty_point_entry = frappe.qb.DocType("Loyalty Point Entry")
	(
		frappe.qb.update(loyalty_point_entry)
		.set(loyalty_point_entry.invoice_type, "Sales Invoice")
		.set(loyalty_point_entry.invoice, loyalty_point_entry.sales_invoice)
		.where(loyalty_point_entry.sales_invoice.isnotnull())
		.where(loyalty_point_entry.invoice.isnull() | (loyalty_point_entry.invoice == ""))
	).run()
