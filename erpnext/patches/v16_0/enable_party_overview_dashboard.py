import frappe


def execute():
	singles = frappe.qb.DocType("Singles")
	for doctype, fieldname in (
		("Selling Settings", "load_customer_overview"),
		("Buying Settings", "load_supplier_overview"),
	):
		saved = (
			frappe.qb.from_(singles)
			.select(singles.value)
			.where((singles.doctype == doctype) & (singles.field == fieldname))
			.run()
		)
		if not saved:
			frappe.db.set_single_value(doctype, fieldname, 1)
