from __future__ import unicode_literals

import frappe


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	irn_cancelled_field = frappe.db.exists(
		"Custom Field", {"dt": "Sales Invoice", "fieldname": "irn_cancelled"}
	)
	if irn_cancelled_field:
		frappe.db.set_value("Custom Field", irn_cancelled_field, "depends_on", "eval: doc.irn")
		frappe.db.set_value("Custom Field", irn_cancelled_field, "read_only", 0)
