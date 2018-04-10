from __future__ import unicode_literals
import frappe
from frappe.installer import remove_app, remove_from_installed_apps

def execute():
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_settings')
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_tax_account')

	if 'erpnext_shopify' in frappe.get_installed_apps():
		remove_app('erpnext_shopify', yes=True)

