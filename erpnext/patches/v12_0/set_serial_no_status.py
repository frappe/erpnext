from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'serial_no')

	for serial_no in frappe.db.sql("""select name from `tabSerial No`""", as_dict = 1):
		doc = frappe.get_doc("Serial No", serial_no.get("name"))
		if not doc.status:
			doc.set_status()
			frappe.db.set_value("Serial No", serial_no.get("name"), "status", doc.status)