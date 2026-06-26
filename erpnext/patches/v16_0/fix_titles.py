import frappe


def execute():
	"""
	This patch corrects the titles of doctypes set to
	the text strings "{customer_name}" or "{supplier_name}"
	instead of the actual customer or supplier name.
	"""

	customer_doctypes = ["POS Invoice", "Sales Invoice", "Quotation", "Sales Order", "Delivery Note"]
	supplier_doctypes = ["Purchase Invoice", "Purchase Order", "Purchase Receipt"]

	for doctype in customer_doctypes:
		customer_doctype = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(customer_doctype)
			.set(customer_doctype.title, customer_doctype.customer_name)
			.where(customer_doctype.title == "{customer_name}")
		).run()

	for doctype in supplier_doctypes:
		supplier_doctype = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(supplier_doctype)
			.set(supplier_doctype.title, supplier_doctype.supplier_name)
			.where(supplier_doctype.title == "{supplier_name}")
		).run()
