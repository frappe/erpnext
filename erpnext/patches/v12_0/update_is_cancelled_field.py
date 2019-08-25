from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():

	try:
		frappe.db.sql("UPDATE `tabStock Ledger Entry` SET is_cancelled = IF(is_cancelled='No', 0, 1)")
		frappe.db.sql("UPDATE `tabSerial No` SET is_cancelled = IF(is_cancelled='No', 0, 1)")
	except:
		None