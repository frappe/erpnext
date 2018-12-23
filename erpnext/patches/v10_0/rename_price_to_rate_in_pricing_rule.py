from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc("accounting", "doctype", "pricing_rule")

	try:
		rename_field("Pricing Rule", "price_or_discount", "rate_or_discount")
		rename_field("Pricing Rule", "price", "rate")

	except Exception as e:
		if e.args[0]!=1054:
			raise