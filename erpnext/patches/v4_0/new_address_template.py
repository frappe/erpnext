from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("utilities", "doctype", "address_template")
	if not frappe.db.sql("select name from `tabAddress Template`"):
		try:
			d = frappe.new_doc("Address Template")
			d.update({"country":frappe.db.get_default("country") or
				frappe.db.get_value("Global Defaults", "Global Defaults", "country")})
			d.insert()
		except:
			print frappe.get_traceback()

