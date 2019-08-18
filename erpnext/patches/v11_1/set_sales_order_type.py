from __future__ import unicode_literals
import frappe, os
from frappe import _

def execute():
	frappe.reload_doc("stock", "doctype", "delivery_note")
	frappe.reload_doc("accounts", "doctype", "sales_invoice")

	for dt in ['Delivery Note', 'Sales Invoice']:
		frappe.db.sql("""
			update `tab{dt}` t
			left join `tabOrder Type` ot on ot.name = t.order_type_name
			set t.order_type = ifnull(ot.type, 'Sales')
		""".format(dt=dt))