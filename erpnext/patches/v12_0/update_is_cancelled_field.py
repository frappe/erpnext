import frappe


def execute():
	#handle type casting for is_cancelled field
	module_doctypes = (
		('stock', 'Stock Ledger Entry'),
		('stock', 'Serial No'),
		('accounts', 'GL Entry')
	)

	for module, doctype in module_doctypes:
		if frappe.db.has_column(doctype, "is_cancelled"):
			frappe.db.sql('''UPDATE `tab{doctype}` SET is_cancelled = CASE
					WHEN is_cancelled = 'No' THEN 0
					WHEN is_cancelled = 'Yes' THEN 1
					ELSE 0
				END'''.format(doctype=doctype))

		frappe.reload_doc(module, "doctype", frappe.scrub(doctype))
