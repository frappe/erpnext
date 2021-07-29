import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "stock_entry")
	frappe.reload_doc("stock", "doctype", "stock_entry_detail")

	stes = frappe.db.sql_list("""
		select name
		from `tabStock Entry`
		where docstatus = 1 and purpose in ('Manufacture', 'Repack')
	""")

	for name in stes:
		doc = frappe.get_doc("Stock Entry", name)
		doc.set_work_order_details()
		doc.set_basic_rate_for_finished_goods()

		for d in doc.items:
			if d.cost_percentage:
				d.db_set('cost_percentage', d.cost_percentage)

		doc.clear_cache()
