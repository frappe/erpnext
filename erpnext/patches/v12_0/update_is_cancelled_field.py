import frappe


def execute():
	#handle type casting for is_cancelled field

	for doc_mapper in (('stock','Stock Ledger Entry'),
		('stock','Serial No'),
		('accounts','GL Entry')):
		try:
			module = doc_mapper[0]
			doctype = doc_mapper[1]

			frappe.db.sql('''UPDATE `tab{doctype}` SET is_cancelled = CASE
					WHEN is_cancelled = 'No' THEN 0
					WHEN is_cancelled = 'Yes' THEN 1
					ELSE 0
				END'''.format(doctype=doctype))

			frappe.reload_doc(module, "doctype", frappe.scrub(doctype))
		except Exception:
			pass