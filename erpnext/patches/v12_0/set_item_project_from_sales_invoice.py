import frappe


def execute():
	frappe.reload_doctype("Sales Invoice Item")
	frappe.reload_doctype("Sales Invoice")

	frappe.db.sql("""
		update `tabSales Invoice Item` item
		inner join `tabSales Invoice` si on si.name = item.parent
		set item.project = si.project
		where ifnull(item.project, '') = ''
			and ifnull(si.project, '') != ''
			and si.claim_billing = 0
	""")
