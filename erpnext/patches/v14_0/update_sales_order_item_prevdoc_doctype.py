import frappe


def execute():
	frappe.db.set_value(
		"Sales Order Item", {"prevdoc_docname": ["!=", ""]}, "prevdoc_doctype", "Quotation"
	)
