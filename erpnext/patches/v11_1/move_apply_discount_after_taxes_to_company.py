from __future__ import unicode_literals
import frappe, os
from frappe import _

def execute():
	selling = frappe.db.get_single_value("Selling Settings", "apply_discount_after_taxes")
	buying = frappe.db.get_single_value("Buying Settings", "apply_discount_after_taxes")

	frappe.reload_doc("setup", "doctype", "company")
	frappe.db.sql("""
		update `tabCompany`
		set
			selling_apply_discount_after_taxes = %s,
			buying_apply_discount_after_taxes = %s
	""", (selling, buying))