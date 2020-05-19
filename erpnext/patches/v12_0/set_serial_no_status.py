from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, nowdate

def execute():
	frappe.reload_doc('stock', 'doctype', 'serial_no')

	for serial_no in frappe.db.sql("""select name, delivery_document_type, warranty_expiry_date from `tabSerial No`
		where (status is NULL OR status='')""", as_dict = 1):
		if serial_no.get("delivery_document_type"):
			status = "Delivered"
		elif serial_no.get("warranty_expiry_date") and getdate(serial_no.get("warranty_expiry_date")) <= getdate(nowdate()):
			status = "Expired"
		else:
			status = "Active"

		frappe.db.set_value("Serial No", serial_no.get("name"), "status", status)