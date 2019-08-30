from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():

	try:
		frappe.db.sql("UPDATE `tabStock Ledger Entry` SET is_cancelled = 0 where is_cancelled in ('', NULL, 'No')")
		frappe.db.sql("UPDATE `tabSerial No` SET is_cancelled = 0 where is_cancelled in ('', NULL, 'No')")

		frappe.db.sql("UPDATE `tabStock Ledger Entry` SET is_cancelled = 1 where is_cancelled = 'Yes'")
		frappe.db.sql("UPDATE `tabSerial No` SET is_cancelled = 1 where is_cancelled = 'Yes'")

		frappe.reload_doc("stock", "doctype", "stock_ledger_entry")
		frappe.reload_doc("stock", "doctype", "serial_no")
	except:
		None