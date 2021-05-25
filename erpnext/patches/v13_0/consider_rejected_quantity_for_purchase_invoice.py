from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Buying Settings")
	buying_settings = frappe.get_single("Buying Settings")
	buying_settings.consider_rejected_quantity_for_purchase_invoice = 0
	buying_settings.save()
