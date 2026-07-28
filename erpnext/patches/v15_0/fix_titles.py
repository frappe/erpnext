import frappe


def execute():
	"""
	These doctypes point `title_field` at the party name field, so their `title`
	default was never rendered and got stored as the literal template string.
	"""

	for doctype, source_field in (
		("Purchase Order", "supplier_name"),
		("Subcontracting Order", "supplier_name"),
		("Sales Order", "customer_name"),
	):
		table = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(table)
			.set(table.title, table[source_field])
			.where(table.title == f"{{{source_field}}}")
		).run()
