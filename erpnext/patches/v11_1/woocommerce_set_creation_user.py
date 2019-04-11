from __future__ import unicode_literals
import frappe

def execute():
	woocommerce_settings = frappe.get_single("Woocommerce Settings")
	if woocommerce_settings.enable_sync:
		woocommerce_settings.creation_user = woocommerce_settings.modified_by
		woocommerce_settings.save()