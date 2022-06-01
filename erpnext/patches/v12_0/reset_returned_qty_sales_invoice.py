import frappe


def execute():
	invoices_with_returns = frappe.db.sql_list("""
		select si.name
		from `tabSales Invoice` si
		where si.docstatus = 1 and exists(select ret.name from `tabSales Invoice` ret where
			ret.return_against = si.name and ret.docstatus = 1)
	""")

	for name in invoices_with_returns:
		doc = frappe.get_doc("Sales Invoice", name)
		doc.set_returned_status(update=True, update_modified=False)
		doc.clear_cache()
