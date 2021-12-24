from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doctype("Buying Settings")
	buying_settings = frappe.get_single("Buying Settings")
	buying_settings.bill_for_rejected_quantity_in_purchase_invoice = 0
	buying_settings.save()
