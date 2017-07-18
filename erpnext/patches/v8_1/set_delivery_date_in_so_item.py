import frappe

def execute():
	frappe.reload_doctype("Sales Order")
	frappe.reload_doctype("Sales Order Item")

	frappe.db.sql("""update `tabSales Order` set final_delivery_date = delivery_date where docstatus=1""")

	frappe.db.sql("""
		update `tabSales Order` so, `tabSales Order Item` so_item
		set so_item.delivery_date = so.delivery_date
		where so.name = so_item.parent
	""")