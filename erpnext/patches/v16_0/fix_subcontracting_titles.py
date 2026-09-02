import frappe


def execute():
	"""
	This patch corrects the titles of the subcontracting order doctypes set to
	the text strings "{customer_name}" or "{supplier_name}" instead of the
	actual customer or supplier name.

	Their `title_field` never pointed at `title`, so the template default was
	stored verbatim instead of being substituted.
	"""

	party_fields = {
		"Subcontracting Order": "supplier_name",
		"Subcontracting Inward Order": "customer_name",
	}

	for doctype, party_field in party_fields.items():
		if not frappe.db.has_column(doctype, "title"):
			continue

		table = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(table)
			.set(table.title, table[party_field])
			.where(table.title == f"{{{party_field}}}")
		).run()
