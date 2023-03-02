import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "batch")

	frappe.db.sql("""
		update `tabBatch`
		set auto_created = 1
		where ifnull(reference_doctype, '') != '' and ifnull(reference_name, '') != ''
	""")

	frappe.db.sql("""
		update `tabBatch` b
		inner join `tabItem` i on i.name = b.item
		set b.item_name = i.item_name
	""")
