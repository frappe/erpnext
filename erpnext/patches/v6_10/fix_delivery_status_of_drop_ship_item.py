from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Sales Order Item")
	for so_name in frappe.db.sql("""select distinct parent from `tabSales Order Item`
			where delivered_by_supplier=1 and docstatus=1"""):
		so = frappe.get_doc("Sales Order", so_name[0])
		so.update_delivery_status()
		so.set_status(update=True, update_modified=False)