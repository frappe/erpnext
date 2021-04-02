from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "payment_entry")

	frappe.db.sql(""" UPDATE `tabPayment Entry` set status = 'Cancelled' WHERE docstatus = 2 """)