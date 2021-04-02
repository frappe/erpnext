from __future__ import unicode_literals
import frappe

def execute():
	for data in frappe.get_all('Sales Order', fields = ["name"], filters = [["docstatus", "=", "1"], ["grand_total", "=", "0"]]):
		sales_order = frappe.get_doc('Sales Order', data.name)
		sales_order.set_status(update=True, update_modified = False)