from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, nowdate

def execute():
	frappe.reload_doc('stock', 'doctype', 'serial_no')

	for serial_no in frappe.db.sql("""select name from `tabSerial No`""", as_dict = 1):
		sn_detail = frappe.db.get_value("Serial No", serial_no.get("name"), ["status", "delivery_document_type", "warranty_expiry_date"], as_dict=1)

		if not sn_detail.get("status"):
			if sn_detail.get("delivery_document_type"):
				status = "Delivered"
			elif sn_detail.get("warranty_expiry_date") and getdate(sn_detail.get("warranty_expiry_date")) <= getdate(nowdate()):
				status = "Expired"
			else:
				status = "Active"

		frappe.db.set_value("Serial No", serial_no.get("name"), "status", status)