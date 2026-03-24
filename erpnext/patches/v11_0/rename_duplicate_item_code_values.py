import frappe


def execute():
	items = []
	items = frappe.db.sql(
		"""select item_code from `tabItem` group by item_code having count(*) > 1""", as_dict=True
	)
	if items:
		item_doc = frappe.qb.DocType("Item")
		for item in items:
			frappe.qb.update(item_doc).set(item_doc.item_code, item_doc.name).where(
				item_doc.item_code == item.item_code
			).run()
