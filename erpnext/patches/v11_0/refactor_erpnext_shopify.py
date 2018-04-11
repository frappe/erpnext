from __future__ import unicode_literals
import frappe
from frappe.installer import remove_from_installed_apps

def execute():
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_settings')
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_tax_account')
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_log')

	if 'erpnext_shopify' in frappe.get_installed_apps():
		remove_from_installed_apps('erpnext_shopify')

	frappe.db.sql('delete from `tabDesktop Icon` where app="erpnext_shopify" ')
	frappe.delete_doc("Module Def", 'erpnext_shopify')

	frappe.db.commit()

	frappe.db.sql("truncate `tabShopify Log`")
