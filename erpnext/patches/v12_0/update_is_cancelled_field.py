import frappe


def execute():
	# handle type casting for is_cancelled field
	module_doctypes = (
		("stock", "Stock Ledger Entry"),
		("stock", "Serial No"),
		("accounts", "GL Entry"),
	)

	for module, doctype in module_doctypes:
		if (
			not frappe.db.has_column(doctype, "is_cancelled")
			or frappe.db.get_column_type(doctype, "is_cancelled").lower() == "int(1)"
		):
			continue

		frappe.db.sql(
			"""
				UPDATE `tab{doctype}`
				SET is_cancelled = 0
				where is_cancelled in ('', 'No') or is_cancelled is NULL""".format(
				doctype=doctype
			)
		)
		frappe.db.sql(
			"""
				UPDATE `tab{doctype}`
				SET is_cancelled = 1
				where is_cancelled = 'Yes'""".format(
				doctype=doctype
			)
		)

		frappe.reload_doc(module, "doctype", frappe.scrub(doctype))
