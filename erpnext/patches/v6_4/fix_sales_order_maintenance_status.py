from __future__ import unicode_literals
import frappe

def execute():
	for doc in frappe.get_all("Sales Order", filters={"docstatus": 1,
		"order_type": "Maintenance"}):
		doc = frappe.get_doc("Sales Order", doc.name)
		doc.set_status(update=True)
